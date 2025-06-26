import argparse
import json
import os
from collections import defaultdict
from dataclasses import dataclass

import torch
import torch.nn.functional as F
from longppl.longppl import compute_longppl
from tqdm import tqdm
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
    set_seed,
)

from sec_aware_cl.logger import logger
from sec_aware_cl.schemas import AvailableModels

set_seed(1234)


def forward_pass(sentence: str, model, tokenizer, hidden_states=False):
    inputs = tokenizer(sentence, return_tensors="pt", truncation=True)

    if isinstance(model, torch.nn.DataParallel):
        model = model.module
    device = model.device  # Access the model's device directly
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model(
            **inputs, labels=inputs["input_ids"], output_hidden_states=hidden_states
        )
    return outputs


@torch.no_grad()
def compute_logprob(model, tokenizer, prompt, continuation):
    input_text = prompt + continuation
    inputs = tokenizer(input_text, return_tensors="pt").to(model.device)

    outputs = forward_pass(input_text, model, tokenizer, hidden_states=False)

    logits = outputs.logits[:, :-1, :]
    target_ids = inputs["input_ids"][:, 1:]
    log_probs = F.log_softmax(logits, dim=-1)
    token_log_probs = log_probs.gather(2, target_ids.unsqueeze(-1)).squeeze(-1)
    total_logprob = token_log_probs.sum(dim=1)  # shape: (batch_size,)
    return total_logprob.cpu().item()  # return scalar float


# DPO loss function (uses scalar torch floats)
def dpo_loss(chosen_logprob, rejected_logprob, beta=1.0):
    delta_logprob = beta * (chosen_logprob - rejected_logprob)
    return torch.nn.functional.softplus(
        -delta_logprob
    )  # Equivalent to -log(sigmoid(...))


def write_jsonl(data: json, file_path, append=False):
    mode = "a" if append else "w"

    if not os.path.exists(file_path):
        mode = "w"

    with open(file_path, mode) as f:
        f.write(json.dumps(data) + "\n")


def main(model, directory, output_dir):
    model_name = model
    device_map = "auto"

    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        trust_remote_code=True,
        add_eos_token=True,
        use_fast=True,
    )
    tokenizer.pad_token = tokenizer.eos_token

    if torch.cuda.is_bf16_supported():
        compute_dtype = torch.bfloat16
        attn_implementation = "flash_attention_2"
    else:
        compute_dtype = torch.float16
        attn_implementation = "sdpa"

    bnb_config = BitsAndBytesConfig(
        # Load the model with 4-bit quantization
        load_in_4bit=True,
        # Use double quantization
        bnb_4bit_use_double_quant=True,
        # Use 4-bit Normal Float for storing the base model weights in GPU memory
        bnb_4bit_quant_type="nf4",
        # De-quantize the weights to 16-bit (Brain) float before the forward/backward pass
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    if model_name == AvailableModels.codesage.value:
        from transformers import CodeSage

        model = CodeSage.from_pretrained(model_name, trust_remote_code=True)
    else:
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            trust_remote_code=True,
            quantization_config=bnb_config,
            device_map=device_map,
            # attn_implementation=attn_implementation,
        )

    if torch.cuda.device_count() > 1:
        logger.info("Using GPUs", count=torch.cuda.device_count())
        model = torch.nn.DataParallel(model)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    alignemnt_dict = defaultdict(list)

    # Open directory. It has either safe or vulnerable folders
    for folder in os.listdir(directory):
        if folder not in ["data"]:
            continue

        for file in tqdm(os.listdir(os.path.join(directory, folder)), total=144):

            cwe = file.split(".")[0]
            snippets = []
            dpo_losses = []

            cwe_aligned_count = 0
            with open(os.path.join(directory, folder, file), "r") as f:
                logger.info("Processing file", file=file)

                for line in f:
                    # dict_keys(['idx', 'project', 'commit_id', 'project_url', 'commit_url', 'commit_message', 'target', 'func', 'func_hash', 'file_name', 'file_hash', 'cwe', 'cve', 'cve_desc', 'nvd_url'])
                    data = json.loads(line)

                    user_input = ""
                    chosen = data["chosen"]
                    rejected = data["rejected"]
                    chosen_logprob = compute_logprob(
                        model, tokenizer, user_input, chosen
                    )
                    rejected_logprob = compute_logprob(
                        model, tokenizer, user_input, rejected
                    )

                    # Convert to torch float32 scalar tensors
                    chosen_logprob_tensor = torch.tensor(
                        chosen_logprob, dtype=torch.float32
                    )
                    rejected_logprob_tensor = torch.tensor(
                        rejected_logprob, dtype=torch.float32
                    )

                    loss = dpo_loss(chosen_logprob_tensor, rejected_logprob_tensor)

                    logger.debug(
                        "DPO Loss calculated",
                        loss=loss,
                    )
                    dpo_losses.append(loss.item())

                    in_the_stack = None
                    if model_name not in data["model_names"]:
                        logger.warning(
                            "Model was not preprocessed to know if it has seen this data prior or not",
                            model=model_name,
                        )
                    else:
                        model_name_idx = data["model_names"].index(model_name)
                        in_the_stack = data["in_the_stack"][model_name_idx]

                    # remove the model_names and in_the_stack keys from the data
                    del data["model_names"]
                    del data["in_the_stack"]

                    data["in_the_stack"] = in_the_stack

                    if chosen_logprob > rejected_logprob:
                        cwe_aligned_count += 1

                    data["dpo_loss"] = loss.item()
                    data["aligned"] = chosen_logprob > rejected_logprob

                    snippets.append(data)
            alignemnt_dict[cwe].append(
                {
                    "aligned_count": cwe_aligned_count,
                    "total_count": len(snippets),
                }
            )

            # Save the results. # TODO: Create a basemodel for this
            results = {
                "cwe": cwe,
                "model": model_name,
                "dpo_losses": dpo_losses,
                "snippets": snippets,
                "alignment_stats": alignemnt_dict[cwe],
            }
            write_jsonl(results, os.path.join(output_dir, f"{cwe}.jsonl"), append=True)
            write_jsonl(
                {"cwe": cwe, "stats": alignemnt_dict[cwe]},
                os.path.join(output_dir, f"alignment_stats.jsonl"),
                append=True,
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Constrative Learning with QLoRa")

    model_options = [
        model.value for model in list(AvailableModels.__members__.values())
    ]
    parser.add_argument(
        "--model",
        type=str,
        help="The model to analyse",
        choices=model_options,
        default=AvailableModels.GPT2.value,
        required=True,
    )

    parser.add_argument(
        "--directory",
        type=str,
        help="The dataset to use",
        default="dataset",
        required=True,
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        help="The dataset to use",
        default="dataset",
        required=True,
    )

    args = parser.parse_args()
    main(args.model, args.directory, args.output_dir)
