from typing import Callable, Optional, Union

import datasets
import torch
from datasets import Dataset, IterableDataset
from jaxtyping import Float, Integer
from torch.utils.data import DataLoader
from transformers import (
    BaseImageProcessor,
    FeatureExtractionMixin,
    PreTrainedTokenizerBase,
    ProcessorMixin,
)
from transformers.trainer import seed_worker
from transformers.utils import is_datasets_available
from trl import SFTTrainer
from trl.trainer.sft_config import SFTConfig

from sec_aware_cl.logger import logger

MAX_LENGTH = 518


class OurCLTrainer(SFTTrainer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._signature_columns = ["code_0", "code_1", "sim"]

    # We need to change the preprocessing slightly to handle the new inputs
    def _prepare_dataset(
        self,
        dataset: Union[Dataset, IterableDataset],
        processing_class: Union[
            PreTrainedTokenizerBase,
            BaseImageProcessor,
            FeatureExtractionMixin,
            ProcessorMixin,
        ],
        args: SFTConfig,
        packing: bool,
        formatting_func: Optional[Callable[[dict], str]],
        dataset_name: str,
    ) -> Union[Dataset, IterableDataset]:
        logger.info(f"Preparing dataset {dataset_name}")
        # We need to map so we have "code_0", "code_1", and "label" keys

        def tokenize(example, processing_class, dataset_text_field):
            return processing_class(
                example[dataset_text_field],
                truncation=True,
                max_length=MAX_LENGTH,
                padding="max_length",
            )

        def tokenize_function(examples: dict):
            # Currently they have different shapes because I am yet to padd. Their sequence lengths are different.
            tokenized_0: Integer[torch.Tensor, "seq_len1"] = tokenize(
                examples,
                processing_class,
                "code_0",
            )
            tokenized_1: Integer[torch.Tensor, "seq_len2"] = tokenize(
                examples,
                processing_class,
                "code_1",
            )
            assert len(tokenized_0["input_ids"][0]) == MAX_LENGTH
            assert len(tokenized_1["input_ids"][0]) == MAX_LENGTH
            return {
                "code_0": tokenized_0["input_ids"],  # Extracting as a list
                "code_1": tokenized_1["input_ids"],  # Extracting as a list
                "sim": [1] * len(examples["code_0"]),  # Ensuring `label` is a list
            }

        dataset = dataset.map(
            tokenize_function,
            batched=True,
            remove_columns=dataset.column_names,
        )
        return dataset

    def get_train_dataloader(self) -> DataLoader:
        """
        Returns the training [`~torch.utils.data.DataLoader`].

        Will use no sampler if `train_dataset` does not implement `__len__`, a random sampler (adapted to distributed
        training if necessary) otherwise.

        Subclass and override this method if you want to inject some custom behavior.
        """
        logger.info("Creating dataloader")
        if self.train_dataset is None:
            raise ValueError("Trainer: training requires a train_dataset.")

        train_dataset = self.train_dataset
        data_collator = self.data_collator
        if is_datasets_available() and isinstance(train_dataset, datasets.Dataset):
            train_dataset = self._remove_unused_columns(
                train_dataset, description="training"
            )
        else:
            data_collator = self._get_collator_with_removed_columns(
                data_collator, description="training"
            )

        dataloader_params = {
            "batch_size": self._train_batch_size,
            "collate_fn": data_collator,
            "num_workers": self.args.dataloader_num_workers,
            "pin_memory": self.args.dataloader_pin_memory,
            "persistent_workers": self.args.dataloader_persistent_workers,
        }

        if not isinstance(train_dataset, torch.utils.data.IterableDataset):
            dataloader_params["sampler"] = self._get_train_sampler()
            dataloader_params["drop_last"] = self.args.dataloader_drop_last
            dataloader_params["worker_init_fn"] = seed_worker
            dataloader_params["prefetch_factor"] = self.args.dataloader_prefetch_factor
        return train_dataset

    def compute_loss(
        self, model, inputs, return_outputs=False, num_items_in_batch=None
    ):
        """
        How the loss is computed by Trainer. By default, all models return the loss in the first element.

        Subclass and override for custom behavior.
        """
        logger.info("Computing loss")
        if self.model_accepts_loss_kwargs:
            loss_kwargs = {}
            if num_items_in_batch is not None:
                loss_kwargs["num_items_in_batch"] = num_items_in_batch
            inputs = {**inputs, **loss_kwargs}

        # Computes the constrative loss.
        labels: Float[torch.Tensor, ""] = inputs.pop("sim")
        labels: Float[torch.Tensor, "batch"] = torch.tensor(
            [labels],
            dtype=torch.long,
        )

        code_0: Integer[torch.Tensor, "seq_len1"] = inputs.pop("code_0")
        code_1: Integer[torch.Tensor, "seq_len1"] = inputs.pop("code_1")

        from transformers.modeling_outputs import CausalLMOutputWithCrossAttentions

        # TODO: We might want to look into padding, so we can have a single tensor
        outputs_0: CausalLMOutputWithCrossAttentions = model(
            input_ids=torch.tensor(
                [code_0],
                dtype=torch.long,
            ),
            output_hidden_states=True,
        )
        outputs_1: CausalLMOutputWithCrossAttentions = model(
            input_ids=torch.tensor([code_1], dtype=torch.long),
            output_hidden_states=True,
        )

        # Retrive the last hidden state.
        outputs_0: Float[torch.Tensor, "seq_len1, hidden_size"] = (
            outputs_0.hidden_states[-1]
        )
        outputs_1: Float[torch.Tensor, "seq_len2, hidden_size"] = (
            outputs_1.hidden_states[-1]
        )

        mean_pooled_embeddings_0: Float[torch.Tensor, "hidden_size"] = torch.mean(
            outputs_0, dim=0
        )
        mean_pooled_embeddings_1: Float[torch.Tensor, "hidden_size"] = torch.mean(
            outputs_1, dim=0
        )

        def constrative_loss(outputs_0, outputs_1, labels):
            # Compute constrative loss
            # https://arxiv.org/abs/2002.05709

            # Compute similarity
            sim = torch.nn.functional.cosine_similarity(
                outputs_0, outputs_1, dim=0
            ).unsqueeze(0)
            # Compute constrative loss
            labels = labels.to(sim.device)
            loss = torch.nn.functional.cross_entropy(sim, labels)
            return loss

        loss = constrative_loss(
            mean_pooled_embeddings_0, mean_pooled_embeddings_1, labels
        )

        if (
            self.args.average_tokens_across_devices
            and (self.model_accepts_loss_kwargs)
            and num_items_in_batch is not None
        ):
            loss *= self.accelerator.num_processes

        return (loss, [outputs_0, outputs_1]) if return_outputs else loss
