import argparse
import json
import os
from dataclasses import dataclass

import torch
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


def forward_pass(sentence: str, model, tokenizer):
    inputs = tokenizer(sentence, return_tensors="pt", truncation=True)
    # move to the correct device
    inputs = {name: tensor.to(model.device) for name, tensor in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs, labels=inputs["input_ids"], output_hidden_states=True)
    return outputs


def get_perplexity_hidden_state(sentence, model, tokenizer):
    outputs = forward_pass(sentence, model, tokenizer)
    return (
        torch.exp(outputs.loss).cpu().numpy(),
        # `outputs.hidden_states` is a list of the outputs per layer.
        # Each output is [batch, seq_length, hidden].
        outputs.hidden_states[-1][:, -1, :].cpu().numpy(),
    )


def write_jsonl(data: json, file_path, append=False):
    mode = "a" if append else "w"

    if not os.path.exists(file_path):
        mode = "w"

    with open(file_path, mode) as f:
        f.write(json.dumps(data) + "\n")


def main(model, directory, output_dir):
    model_name = model
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.padding_side = "right"  # to prevent warnings
    device_map = "auto"

    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        trust_remote_code=True,
        add_eos_token=True,
        use_fast=False,
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

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        trust_remote_code=True,
        quantization_config=bnb_config,
        device_map=device_map,
        # attn_implementation=attn_implementation,
    )

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Open directory. It has either safe or vulnerable folders
    for folder in os.listdir(directory):
        if folder not in ["data"]:
            continue

        for file in tqdm(os.listdir(os.path.join(directory, folder)), total=144):

            cwe = file.split(".")[0]
            vulnerable_perplexities = []
            safe_perplexities = []

            with open(os.path.join(directory, folder, file), "r") as f:
                logger.info("Processing file", file=file)
                for line in f:
                    # dict_keys(['idx', 'project', 'commit_id', 'project_url', 'commit_url', 'commit_message', 'target', 'func', 'func_hash', 'file_name', 'file_hash', 'cwe', 'cve', 'cve_desc', 'nvd_url'])
                    data = json.loads(line)

                    perplexity, hidden_state = get_perplexity_hidden_state(
                        data["func"], model, tokenizer
                    )
                    perplexity = perplexity.item()
                    logger.info(
                        "Perplexity and hidden state calculated",
                        perplexity=perplexity,
                    )

                    is_vulnerable = data["target"] == 1

                    if is_vulnerable:
                        vulnerable_perplexities.append(perplexity)
                    else:
                        safe_perplexities.append(perplexity)

            # Save the results. # TODO: Create a basemodel for this
            results = {
                "cwe": cwe,
                "model": model_name,
                "vulnerable": vulnerable_perplexities,
                "safe": safe_perplexities,
            }
            write_jsonl(results, os.path.join(output_dir, f"{cwe}.jsonl"), append=True)


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
