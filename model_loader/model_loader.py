from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
)

from transformers.generation import GenerationConfig
from typing import List, Tuple
import torch
import time
import json
import psutil

if "cuda" in dir(torch):
    import torch.cuda as cuda


class ModelLoader:
    """
    Class for loading and managing language model instances.
    """

    def __init__(
        self, conf, model_id: str, template_name: str, conversation_type: str
    ) -> None:
        """
        Initialize the ModelLoader.

        Args:
            conf: Configuration object.
            model_id (str): Identifier for the model.
            template_name (str): Name of the template file.
            conversation_type (str): Type of conversation.
        """
        self.model_id = model_id
        self.template_name = template_name
        self.conversation_type = conversation_type

        self.generation_config = conf.generation_config
        self.cache_dir = conf.model_dir
        self.max_new_tokens = conf.max_new_tokens
        self.answer_size = conf.answers_per_task
        self.device = conf.device
        self.batch_size = 1
        self.chat_template = ""
        self.remote_code = conf.remote_code
        self.terminators = []
        self.name = model_id.split("/")[1]

    def load_model_tokenizer(self):
        """
        Load the model and tokenizer.
        """
        print(f"Loading {self.name} model for {self.conversation_type} conversation...")
        # Load model and tokenizer on GPU
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            device_map=self.device,
            trust_remote_code=self.remote_code,
            cache_dir=self.cache_dir,
        ).eval()

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_id,
            use_fast=True,
            device_map=self.device,
            cache_dir=self.cache_dir,
            chat_template=self.set_chat_template(self.template_name),
        )

        self.set_terminators()

        print(
            f"Done loading {self.name} model for {self.conversation_type} conversation!"
        )

    def unload_model_tokenizer(self):
        """
        Unload the model and tokenizer.
        """
        del self.model
        del self.tokenizer
        torch.cuda.empty_cache()

    def set_chat_template(self, template_name: str) -> str:
        """
        Set the chat template.

        Args:
            template_name (str): Name of the template file.
        Returns:
            str: Content of the template file.
        """
        content = ""
        with open(f"./chat_templates/{template_name}", "r") as file:
            for line in file:
                content += line.rstrip().lstrip()
        return content

    def set_terminators(self):
        with open(f"./chat_templates/{self.template_name}.json") as file:
            tokens = json.load(file)

        self.terminators.append(self.tokenizer.eos_token_id)
        if "terminators" in tokens:
            for terminator in tokens["terminators"]:
                self.terminators.append(
                    self.tokenizer.convert_tokens_to_ids(terminator)
                )

    def remove_special_tokens(self, no_inst: str) -> str:
        """
        Remove special tokens from the provided string.

        Args:
            no_inst (str): The string from which to remove special tokens.
        Returns:
            str: The string without special tokens.
        """
        with open(f"./chat_templates/{self.template_name}.json") as file:
            tokens = json.load(file)

        for token in tokens["tokens_to_remove"]:
            no_inst = no_inst.replace(token, "")

        for token in self.tokenizer.all_special_tokens:
            no_inst = no_inst.replace(token, "")
        return no_inst

    def remove_inst(
        self,
        prompt: List[dict],
        answer: str,
    ) -> str:
        """
        Remove instruction from the provided string.

        Args:
            prompt (List[dict]): List of dictionaries representing the prompt.
            answer (str): The string from which to remove instruction.
        Returns:
            str: The string without instruction.
        """
        inst_enc = self.tokenizer.apply_chat_template(prompt, return_tensors="pt").to(
            self.device
        )
        inst = self.tokenizer.decode(inst_enc[0])
        updated_responses = answer.replace(inst, "")
        return updated_responses

    def replace_tokens(self, no_inst: str) -> str:
        """
        Replaces token if specified in the json file for the model.

        Args:
            no_inst (str): The string from which to replace tokens.
        Returns:
            str: The new string.
        """
        with open(f"./chat_templates/{self.template_name}.json") as file:
            tokens = json.load(file)

        if "replace_tokens" in tokens:
            for replace_this, replace_with in tokens["replace_tokens"].items():
                no_inst = no_inst.replace(replace_this, replace_with)

        return no_inst

    def clean_response(self, prompt: List[dict], llm_resp: str) -> str:
        """
        Clean the model response.

        Args:
            prompt (List[dict]): List of dictionaries representing the prompt.
            llm_resp (str): Model response.
        Returns:
            str: Cleaned response.
        """
        no_inst = self.remove_inst(prompt, llm_resp)
        no_inst = self.remove_special_tokens(no_inst)
        no_inst = self.replace_tokens(no_inst)
        no_inst = no_inst.replace("\t", "    ")
        no_inst = no_inst.replace("\\n", "\n")
        no_inst = no_inst.rstrip(" ")

        if not no_inst:
            no_inst = "No response"
        return no_inst

    def get_tokens_generated(self, clean_resp: str) -> int:
        """
        Get the number of tokens generated.

        Args:
            clean_resp (str): The cleaned model response.
        Returns:
            int: Number of tokens generated.
        """
        return len(self.tokenizer.encode(clean_resp, add_special_tokens=False))

    @torch.inference_mode()
    def prompt_llm(
        self,
        prompt: List[dict],
    ) -> Tuple[str, float]:
        """
        Prompt the language model.

        Args:
            prompt (List[dict]): List of dictionaries representing the prompt.
        Returns:
            Tuple[str, float, float]: Tuple containing the model response, total time taken and vram usage.
        """
        tot_time = 0
        batch_completions = []
        gen_cfg = GenerationConfig.from_model_config(self.model.config)

        input = self.tokenizer.apply_chat_template(prompt, return_tensors="pt").to(
            self.device
        )
        memory_usage = 0
        try:
            with torch.no_grad():
                start = time.time()
                generated_ids = self.model.generate(
                    input,
                    use_cache=True,
                    generation_config=gen_cfg,
                    eos_token_id=self.terminators,
                    pad_token_id=self.tokenizer.eos_token_id,
                    **self.generation_config,
                )
                tot_time += time.time() - start
                batch_completions.extend(generated_ids)
                if self.device == "cuda":
                    # Measure VRAM usage
                    memory_usage = cuda.max_memory_allocated() / (
                        1024 * 1024 * 1024
                    )  # GB
                    torch.cuda.reset_peak_memory_stats()
                    torch.cuda.empty_cache()
                else:
                    memory_usage = psutil.virtual_memory().used / (
                        1024 * 1024 * 1024
                    )  # GB

        except Exception as e:
            print("ERROR: " + str(e))

        response = self.tokenizer.decode(batch_completions[0])

        return response, tot_time, memory_usage
