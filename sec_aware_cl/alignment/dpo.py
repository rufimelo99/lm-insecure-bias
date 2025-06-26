import torch
import torch.nn.functional as F
from datasets import Dataset
from tqdm import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer

# Sample dataset
data = [
    {
        "input": "",
        "rejected": "\n\npublic void setFeature(final String name, final boolean value) {\n    features.put(name, value ? Boolean.TRUE : Boolean.FALSE);\n    engine = null;\n}",
        "chosen": "\n\npublic void setFeature(final String name, final boolean value) {\n    features.put(name, value ? Boolean.TRUE : Boolean.FALSE);\n    if (JDOMConstants.SAX_FEATURE_EXTERNAL_ENT.equals(name)) {\n        setExpandEntities(value);\n    }\n    engine = null;\n}",
    },
]

# Load model and tokenizer
model_name = "openai-community/gpt2"
model = AutoModelForCausalLM.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)
model.eval()

if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token


# Function to compute log probability of a continuation
def compute_logprob(prompt, continuation):
    input_text = prompt + continuation
    inputs = tokenizer(input_text, return_tensors="pt").to(model.device)
    with torch.no_grad():
        outputs = model(**inputs)
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


# Evaluate alignment
aligned_count = 0
total = len(data)

for item in tqdm(data, desc="Evaluating model alignment"):
    input_prompt = item["input"]
    chosen = item["chosen"]
    rejected = item["rejected"]

    chosen_logprob = compute_logprob(input_prompt, chosen)
    rejected_logprob = compute_logprob(input_prompt, rejected)

    # Convert to torch float32 scalar tensors
    chosen_logprob_tensor = torch.tensor(chosen_logprob, dtype=torch.float32)
    rejected_logprob_tensor = torch.tensor(rejected_logprob, dtype=torch.float32)

    loss = dpo_loss(chosen_logprob_tensor, rejected_logprob_tensor)
    print(f"DPO Loss: {loss.item():.4f}")

    if chosen_logprob > rejected_logprob:
        aligned_count += 1

alignment_score = aligned_count / total
print(f"\nAlignment Score: {alignment_score * 100:.2f}% ({aligned_count}/{total})")
