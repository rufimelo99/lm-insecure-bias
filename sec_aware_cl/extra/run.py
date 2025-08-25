import argparse

import torch
from datasets import load_dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
    set_seed,
)

from sec_aware_cl.extra.cl_trainer import OurCLTrainer
from sec_aware_cl.logger import logger
from sec_aware_cl.schemas import AvailableModels, CLSecurityDataset

set_seed(1234)


def create_constractive_learning_dataset(row):
    return {
        "code_0": f"{row['func_before']}",
        "code_1": f"{row['func_after']}",
        "label": 0,
    }


def main(model, dataset):
    model_name = model
    dataset_name = dataset
    dataset_split = "train"

    device_map = {"": 0}
    # device_map={'':torch.cuda.current_device()}

    dataset = load_dataset(dataset_name, split=dataset_split)
    tokenizer_id = model_name
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_id)
    tokenizer.padding_side = "right"  # to prevent warnings

    # You can use a different max length if your custom dataset has shorter/longer input sequences.
    MAX_LENGTH = 256

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

    # TODO: Crop the dataset to 4 entries for testing
    dataset = dataset.select(range(2))
    dataset_cl = dataset.map(create_constractive_learning_dataset)
    dataset_cl = dataset_cl.train_test_split(test_size=0.5, seed=1234)

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

    model.gradient_checkpointing_enable()
    model = prepare_model_for_kbit_training(model)

    peft_config = LoraConfig(
        task_type="CAUSAL_LM",
        # This is the rank of the decomposed matrices A and B to be learned during fine-tuning. A smaller number will save more GPU memory but might result in worse performance.
        r=32,
        # This is the coefficient for the learned ΔW factor, so the larger number will typically result in a larger behavior change after fine-tuning.
        lora_alpha=64,
        # Drop out ratio for the layers in LoRA adaptors A and B.
        lora_dropout=0.1,
        # We fine-tune all linear layers in the model. It might sound a bit large, but the trainable adapter size is still only **1.16%** of the whole model.
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
            "lm_head",
        ],
        # Bias parameters to train. 'none' is recommended to keep the original model performing equally when turning off the adapter.
        bias="none",
    )

    peft_model = get_peft_model(model, peft_config)
    peft_model.print_trainable_parameters()

    args = TrainingArguments(
        output_dir="./our_cool_model",
        evaluation_strategy="steps",
        do_eval=True,
        # For the following arguments, refer to https://huggingface.co/docs/transformers/main_classes/trainer
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        gradient_checkpointing=True,
        optim="paged_adamw_8bit",
        bf16=True,
        learning_rate=2e-5,
        lr_scheduler_type="constant",
        max_steps=500,
        save_steps=100,
        logging_steps=100,
        warmup_steps=5,
        # https://discuss.huggingface.co/t/training-llama-with-lora-on-multiple-gpus-may-exist-bug/47005/3
        ddp_find_unused_parameters=False,
    )

    trainer = OurCLTrainer(
        model=peft_model,
        train_dataset=dataset_cl["train"],
        eval_dataset=dataset_cl["test"],
        # Use constrative loss for feature extraction task
        # compute_loss_func = lambda x, y: constrative_loss(x, y),
        tokenizer=tokenizer,
        args=args,
    )
    # use_cache=True is incompatible with gradient checkpointing.
    peft_model.config.use_cache = False

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
