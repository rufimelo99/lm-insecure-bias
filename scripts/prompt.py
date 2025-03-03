from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
)

model = AutoModelForCausalLM.from_pretrained(
    "astronomer/Llama-3-8B-Instruct-GPTQ-4-Bit",
    device_map="cuda",
    trust_remote_code=True,
    cache_dir="./models",
).eval()

tokenizer = AutoTokenizer.from_pretrained(
    "astronomer/Llama-3-8B-Instruct-GPTQ-4-Bit",
    use_fast=True,
    device_map="cuda",
    cache_dir="./models",
)

inputs = tokenizer(
    [""],
    return_tensors="pt",
)

out = model.generate(
    inputs,
    do_sample=False,
)
