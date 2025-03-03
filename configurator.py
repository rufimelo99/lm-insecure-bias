import argparse
import os
import json
import importlib
import ast
from typing import List
from dataset_loader.dataset_loader import DatasetLoader

from model_loader.model_loader import ModelLoader
from utils.framework_utils import ROOT_PATH


class Configurator:
    def __init__(self):
        """Initialize the Configurator with default configurations."""
        # Set default configuration values
        config_file = os.path.join(ROOT_PATH, "config", "config.json")
        with open(config_file, "r") as f:
            testing_configs = json.load(f)["testing_configs"]

        for key, value in testing_configs.items():
            setattr(self, key, value)
            if isinstance(value, dict):
                for dict_key, dict_value in value.items():
                    setattr(self, dict_key, dict_value)

        self.available_loaders = self.get_available_loaders()

        # Parse command line arguments and check model configurations
        self.parse_args()

        self.check_model_configs()

    def parse_args(self):
        """Parse command line arguments."""
        parser = argparse.ArgumentParser(description="This is option of arguments.")
        parser.add_argument(
            "--model_configs",
            type=str,
            nargs="+",
            default=self.model_configs,
            help="Specify one or more model configurations in the format 'model_id:template_name:conversation_type', separated by spaces.\n Default is %(default)s.",
        )
        parser.add_argument(
            "--model_path",
            type=str,
            default=self.model_dir,
            help="Specify where to look and save models to.\n Default is %(default)s.",
        )
        parser.add_argument(
            "--answers_per_task",
            type=int,
            default=self.answers_per_task,
            help="The number of answers to generate per task.\n Default is %(default)s.",
        )
        parser.add_argument(
            "--max_chain_depth",
            type=int,
            default=self.max_chain_depth,
            help="The maximum number of tries per answer. If a answer is not correct the model gets a new try. The amount of tries is specified by this value. Value should be >= 1\n Default is %(default)s.",
        )
        parser.add_argument(
            "--datasets",
            nargs="+",
            default=self.datasets,
            choices=self.available_loaders,
            help="Choose one or more datasets Default is %(default)s",
        )
        parser.add_argument(
            "--run_cyberseceval",
            type=bool,
            default=self.run_cyberseceval,
            help="Choose if you want to run CyberSecEval Default is %(default)s",
        )
        parser.add_argument(
            "--results_dir",
            type=str,
            default=self.results_dir,
            help="Specify name of folder to save results to.\n Default is %(default)s.",
        )
        parser.add_argument(
            "--device",
            type=str,
            default=self.device,
            help="Specify what device to run on, cpu or cuda for example.\n Default is %(default)s.",
        )
        parser.add_argument(
            "--remote_code",
            type=bool,
            default=self.remote_code,
            help="If you want to run remote code or not. Running remote code is a security risk so make sure you are in a sandbox/safe enviroment.",
        )
        parser.add_argument(
            "--params",
            nargs="*",
            help="This will change the huggingface generation List of parameters in the form key=value",
        )

        args = parser.parse_args()

        # Set attributes based on parsed arguments
        for attr, value in vars(args).items():
            setattr(self, attr, value)

        if args.params:
            for param in args.params:
                key, value = param.split("=")
                typed_value = self.infer_type(value)
                self.generation_config.update({key: typed_value})

    def infer_type(self, value):
        """
        Infer the type of the given value.
        Try converting to int, float, and bool, in that order.
        Default to str if none of the conversions are successful.
        """
        if value.lower() in {"true", "false"}:
            return value.lower() == "true"

        try:
            int_value = int(value)
            return int_value
        except ValueError:
            pass

        try:
            float_value = float(value)
            return float_value
        except ValueError:
            pass

        return value

    def check_model_configs(self):
        """Check if specified template sets exist."""
        for model_config in self.model_configs:
            parts = model_config.split(":")
            files = os.listdir(f"{ROOT_PATH}/chat_templates")
            if parts[1] not in files:
                raise ValueError(f"Template not found: chat_templates/{parts[1]}")
            elif parts[2] not in ["instruction", "infilling", "completion"]:
                raise ValueError(f"The converation type '{parts[2]}' is not supported.")
            elif f"{parts[1]}.json" not in files and parts[2] == "infilling":
                raise ValueError(
                    f"If conversation type infilling is used a {parts[1]}.json need to be created."
                )

    def _get_loader_files(self) -> List[str]:
        """Get list of loader files from dataset_loader directory."""
        dataset_loader_path = os.path.join(ROOT_PATH, "dataset_loader")
        loader_files = os.listdir(dataset_loader_path)
        loader_files = [
            file
            for file in loader_files
            if file.endswith(".py")
            and not file.startswith("__")
            and not file == "dataset_loader.py"
        ]
        return loader_files

    def _get_available_loaders_from_file(self, file_content: str) -> List[str]:
        """Get available loaders from file content."""
        available_loaders = []
        try:
            tree = ast.parse(file_content)
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    available_loaders.append(node.name.replace("Loader", ""))
        except Exception as e:
            print(e)

        return available_loaders

    def get_available_loaders(self) -> List[str]:
        """Get available loaders."""
        available_loaders = []
        loader_files = self._get_loader_files()
        for loader_file in loader_files:
            try:
                with open(f"{ROOT_PATH}/dataset_loader/{loader_file}") as file:
                    content = file.read()
                available_loaders.extend(self._get_available_loaders_from_file(content))
            except Exception as e:
                raise Exception(e)
        return available_loaders

    def get_dataset_loaders(self) -> List[DatasetLoader]:
        """Get dataset loaders based on specified datasets."""
        dataset_loaders = []
        loader_files = self._get_loader_files()
        for loader_file in loader_files:
            for dataset in self.datasets:
                try:
                    with open(f"{ROOT_PATH}/dataset_loader/{loader_file}") as file:
                        content = file.read()
                    tree = ast.parse(content)
                    for node in tree.body:
                        if isinstance(node, ast.ClassDef):
                            class_name = f"{dataset}Loader"
                            if node.name == class_name:
                                module_name = f"dataset_loader.{loader_file[:-3]}"  # Remove the ".py" extension
                                module = importlib.import_module(module_name)
                                dataset_loaders.append(getattr(module, class_name)())
                except Exception as e:
                    raise Exception(e)
        return dataset_loaders

    def get_model_loaders(self) -> List[ModelLoader]:
        """Get model loaders based on specified model configurations.

        Returns:
            List[ModelLoader]: List of model loaders.
        """
        model_loaders = []

        for model_config in self.model_configs:
            model_id, template_name, conversation_type = model_config.split(":")
            model_loaders.append(
                ModelLoader(self, model_id, template_name, conversation_type)
            )
        return model_loaders
