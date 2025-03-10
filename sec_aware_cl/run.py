import argparse

import torch
from datasets import load_dataset
from peft import LoraConfig, TaskType, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
    set_seed,
)

from sec_aware_cl.logger import logger
from sec_aware_cl.cl_trainer import OurCLTrainer
from sec_aware_cl.schemas import AvailableModels, CLSecurityDataset

set_seed(1234)


def main(model, dataset):
    model_name = model
    dataset_name = dataset
    dataset_split = "train"

    device_map = {"": 0}
    # TODO: change this. map to cpu
    #device_map = {"": "cpu"}

    use_4bit = True
    bnb_4bit_compute_dtype = "bfloat16"

    # 'bnb_4bit_quant_type' is the type of quantization that should be used for the 4-bit base model. In this case, it is set to 'nf4'.
    bnb_4bit_quant_type = "nf4"

    # 'use_double_quant' is a boolean that controls whether nested quantization should be used for the 4-bit base model.
    use_double_quant = True

    # LoRA configuration for the model

    # 'lora_r' is the dimension of the LoRA attention.
    lora_r = 16

    # 'lora_alpha' is the alpha parameter for LoRA scaling.
    lora_alpha = 16

    # 'lora_dropout' is the dropout probability for LoRA layers.
    lora_dropout = 0.05

    # 'target_modules' is a list of the modules that should be targeted by LoRA.
    target_modules = [
        "k_proj",
        "q_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "down_proj",
        "up_proj",
    ]
    dataset = load_dataset(dataset_name, split=dataset_split)
    tokenizer_id = model_name
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_id)
    tokenizer.padding_side = "right"  # to prevent warnings

    if torch.cuda.is_bf16_supported():
        compute_dtype = torch.bfloat16
        attn_implementation = "flash_attention_2"
    else:
        compute_dtype = torch.float16
        attn_implementation = "sdpa"

    def create_constractive_learning_dataset(row):
        return {
            "code_0": f"{row['func_before']}",
            "code_1": f"{row['func_after']}",
            "label": 0,
        }

    # TODO: Crop the dataset to 4 entries for testing
    dataset = dataset.select(range(2))

    dataset_cl = dataset.map(create_constractive_learning_dataset)
    dataset_cl = dataset_cl.train_test_split(test_size=0.5, seed=1234)

    tokenizer = AutoTokenizer.from_pretrained(
        model_name, trust_remote_code=True, add_eos_token=True, use_fast=True
    )
    tokenizer.pad_token = tokenizer.unk_token
    tokenizer.pad_token_id = tokenizer.convert_tokens_to_ids(tokenizer.pad_token)
    tokenizer.padding_side = "left"

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=use_4bit,
        bnb_4bit_quant_type=bnb_4bit_quant_type,
        bnb_4bit_compute_dtype=compute_dtype,
        bnb_4bit_use_double_quant=use_double_quant,
    )

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=compute_dtype,
        trust_remote_code=True,
        quantization_config=bnb_config,
        device_map=device_map,
        attn_implementation=attn_implementation,
    )

    model = prepare_model_for_kbit_training(model)
    args = TrainingArguments(
        output_dir="./our_cool_model",
        evaluation_strategy="steps",
        do_eval=True,
        optim="adamw_torch",
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        per_device_eval_batch_size=1,
        log_level="debug",
        save_strategy="epoch",
        logging_steps=100,
        learning_rate=1e-4,
        fp16 = not torch.cuda.is_bf16_supported(),
        bf16 = torch.cuda.is_bf16_supported(),
        # fp16=False,
        # bf16=True,
        eval_steps=100,
        num_train_epochs=3,
        warmup_ratio=0.1,
        lr_scheduler_type="linear",
        # report_to="wandb",
        seed=42,
    )

    peft_config = LoraConfig(
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        task_type=TaskType.FEATURE_EXTRACTION,
        target_modules=target_modules,
    )

    trainer = OurCLTrainer(
        model=model,
        train_dataset=dataset_cl["train"],
        eval_dataset=dataset_cl["test"],
        # Use constrative loss for feature extraction task
        # compute_loss_func = lambda x, y: constrative_loss(x, y),
        peft_config=peft_config,
        tokenizer=tokenizer,
        args=args,
    )
    logger.info("Training model")
    trainer.train()
    logger.info("Saving model")
    trainer.save_model()


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

    dataset_options = [
        dataset.value for dataset in list(CLSecurityDataset.__members__.values())
    ]
    parser.add_argument(
        "--dataset",
        type=str,
        help="The dataset to use",
        choices=dataset_options,
        default=CLSecurityDataset.GBUG_JAVA.value,
        required=True,
    )

    args = parser.parse_args()
    main(args.model, args.dataset)
