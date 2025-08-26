import argparse
import json
import os
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List

import torch
import torch.nn.functional as F
import yaml
from longppl.longppl import compute_longppl  # (kept as in your original)
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
    device = model.device
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model(
            **inputs, labels=inputs["input_ids"], output_hidden_states=hidden_states
        )
    return outputs


def compute_perplexity(outputs):
    return (
        torch.exp(outputs.loss).cpu().numpy(),
        outputs.hidden_states[-1][:, -1, :].cpu().numpy(),
    )


@torch.no_grad()
def compute_logprob(outputs, inputs):
    logits = outputs.logits[:, :-1, :]
    log_probs = F.log_softmax(logits, dim=-1)

    target_ids = inputs["input_ids"][:, 1:]
    token_log_probs = log_probs.gather(2, target_ids.unsqueeze(-1)).squeeze(-1)
    total_logprob = token_log_probs.sum(dim=1)
    return total_logprob.cpu().item()


def compute_uncertainty(outputs):
    """
    Shannon entropy over tokens; lower is better (more confident).
    """
    logits = outputs.logits[:, :-1, :]
    log_probs = F.log_softmax(logits, dim=-1)
    probs = torch.exp(log_probs)
    entropy = -torch.sum(probs * log_probs, dim=-1)
    avg_entropy = entropy.mean(dim=1)
    return avg_entropy.cpu().item()


@torch.no_grad()
def compute_framework(model, tokenizer, prompt, continuation):
    input_text = prompt + continuation
    inputs = tokenizer(input_text, return_tensors="pt").to(model.device)
    outputs = forward_pass(input_text, model, tokenizer, hidden_states=True)

    ppl = compute_perplexity(outputs)[0].item()
    logprob = compute_logprob(outputs, inputs)
    uncertainty = compute_uncertainty(outputs)

    return ppl, logprob, uncertainty


def dpo_loss(chosen_logprob, rejected_logprob, beta=1.0):
    delta_logprob = beta * (chosen_logprob - rejected_logprob)
    return -torch.log(torch.sigmoid(delta_logprob))


def write_jsonl(data: json, file_path, append=False):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    mode = "a" if append and os.path.exists(file_path) else "w"
    with open(file_path, mode) as f:
        f.write(json.dumps(data) + "\n")


def run_job(model_name: str, directory: str, output_dir: str):
    device_map = "auto"

    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        trust_remote_code=True,
        add_eos_token=True,
        use_fast=True,
    )
    tokenizer.pad_token = tokenizer.eos_token

    if torch.cuda.is_bf16_supported():
        compute_dtype = torch.bfloat16  # noqa: F841 (kept for clarity)
        attn_implementation = "flash_attention_2"  # noqa: F841
    else:
        compute_dtype = torch.float16  # noqa: F841
        attn_implementation = "sdpa"  # noqa: F841

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
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

    os.makedirs(output_dir, exist_ok=True)

    alignemnt_dict = defaultdict(list)

    # Expecting a folder "data" under `directory`
    data_root = os.path.join(directory, "data")
    if not os.path.isdir(data_root):
        logger.warning(f"No 'data' subfolder found in {directory}. Skipping.")
        return

    file_list = sorted(os.listdir(data_root))
    n_files = len(file_list)

    for file in tqdm(file_list, total=n_files, desc=f"Files ({model_name})"):
        cwe = file.split(".")[0]
        snippets = []
        dpo_losses = []

        cwe_aligned_count = 0
        in_path = os.path.join(data_root, file)
        if not os.path.isfile(in_path):
            continue

        with open(in_path, "r") as f:
            n_lines = sum(1 for _ in f)
            f.seek(0)
            for line in tqdm(f, total=n_lines, desc=f"Processing {file}", leave=False):
                data = json.loads(line)

                user_input = ""
                chosen = data["chosen"]
                rejected = data["rejected"]

                chosen_ppl, chosen_logprob, chosen_uncertainty = compute_framework(
                    model, tokenizer, user_input, chosen
                )
                rejected_ppl, rejected_logprob, rejected_uncertainty = (
                    compute_framework(model, tokenizer, user_input, rejected)
                )

                chosen_logprob_tensor = torch.tensor(
                    chosen_logprob, dtype=torch.float32
                )
                rejected_logprob_tensor = torch.tensor(
                    rejected_logprob, dtype=torch.float32
                )
                loss = dpo_loss(chosen_logprob_tensor, rejected_logprob_tensor)
                dpo_losses.append(loss.item())

                preferenced_aligned = chosen_logprob > rejected_logprob
                ppl_diff = rejected_ppl - chosen_ppl
                uncertainty_diff = rejected_uncertainty - chosen_uncertainty

                if preferenced_aligned:
                    cwe_aligned_count += 1

                data["dpo_loss"] = loss.item()
                data["aligned"] = preferenced_aligned
                data["ppl_diff"] = ppl_diff
                data["uncertainty_diff"] = uncertainty_diff

                snippets.append(data)

        alignemnt_dict[cwe].append(
            {"aligned_count": cwe_aligned_count, "total_count": len(snippets)}
        )

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
            os.path.join(output_dir, "alignment_stats.jsonl"),
            append=True,
        )


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r") as f:
        cfg = yaml.safe_load(f) or {}
    if "directory" not in cfg or "models" not in cfg:
        raise ValueError("Config must contain top-level keys 'directory' and 'models'.")
    if not isinstance(cfg["models"], list) or not cfg["models"]:
        raise ValueError("'models' must be a non-empty list.")
    return cfg


def run_from_config(cfg: Dict[str, Any]):
    global_directory = cfg["directory"]
    models: List[Dict[str, Any]] = cfg["models"]

    for i, job in enumerate(models, start=1):
        model_name = job.get("model")
        output_dir = job.get("output_dir")
        directory = job.get("directory", global_directory)
        name = job.get("name", model_name)

        if not model_name or not output_dir:
            raise ValueError(f"Model entry #{i} missing 'model' or 'output_dir'.")

        logger.info(f"Starting job {i}/{len(models)}: {name}")
        run_job(model_name=model_name, directory=directory, output_dir=output_dir)
        logger.info(f"Finished job {i}/{len(models)}: {name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run Security Alignment from YAML config"
    )
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to YAML config with 'directory' and 'models' list",
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    run_from_config(cfg)
