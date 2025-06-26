from datasets import Dataset, load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.trainer_utils import EvalLoopOutput
from trl import DPOConfig, DPOTrainer

# Dataset
data = [
    {
        "input": "Is this code vulnerable to XXE?\n\npublic void setFeature(final String name, final boolean value) {\n    features.put(name, value ? Boolean.TRUE : Boolean.FALSE);\n    engine = null;\n}",
        "chosen": "Yes, this code is vulnerable to XXE because it does not check or disable external entity resolution.",
        "rejected": "No, this code is safe and does not require any additional checks.",
    },
    {
        "input": "Is this code vulnerable to XXE?\n\npublic void setFeature(final String name, final boolean value) {\n    features.put(name, value ? Boolean.TRUE : Boolean.FALSE);\n    if (JDOMConstants.SAX_FEATURE_EXTERNAL_ENT.equals(name)) {\n        setExpandEntities(value);\n    }\n    engine = null;\n}",
        "chosen": "No, this code mitigates XXE by explicitly handling the SAX external entity feature.",
        "rejected": "Yes, this code is vulnerable because it allows entity expansion without restriction.",
    },
]

dataset = Dataset.from_list(data)

model_to_train = "openai-community/gpt2"
model = AutoModelForCausalLM.from_pretrained(model_to_train)
tokenizer = AutoTokenizer.from_pretrained(model_to_train)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

train_dataset = dataset.map(
    lambda x: tokenizer(
        x["input"], truncation=True, padding="max_length", max_length=512
    ),
    batched=True,
    remove_columns=["input"],
)

training_args = DPOConfig(output_dir="try_dpo")

compute_metrics = EvalLoopOutput(predictions=None, label_ids=None, metrics=None)


trainer = DPOTrainer(
    model=model,
    args=training_args,
    processing_class=tokenizer,
    train_dataset=train_dataset,
    compute_metrics=compute_metrics,
)
trainer.train()
