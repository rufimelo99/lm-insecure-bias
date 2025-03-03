import json
import shutil
import os
import json
import numpy as np
from pathlib import Path
from human_eval.evaluation import estimate_pass_at_k
from model_loader.model_loader import ModelLoader

CUR_DIR = os.path.abspath(__file__)[: os.path.abspath(__file__).rindex("/") + 1]

ROOT_PATH = Path(CUR_DIR).parent.absolute()

import sys

sys.path.append(f"{ROOT_PATH}/datasets/suites")

from PurpleLlama.CybersecurityBenchmarks.benchmark.run import main as cyberseceval_run
from PurpleLlama.CybersecurityBenchmarks.benchmark.llm import (
    create as cyberseceval_create_llm,
)
from PurpleLlama.CybersecurityBenchmarks.benchmark.llm import ANY


def print_progress_bar(
    current_iteration: int,
    total_iterations: int,
    prefix: str = "Progress",
    suffix: str = "Complete",
    fill: str = "█",
) -> None:
    """
    Prints a progress bar to track the progress of a process.

    :param current_iteration: The current iteration number.
    :param total_iterations: The total number of iterations.
    :param prefix: Optional string prefix to display before the progress bar.
    :param suffix: Optional string suffix to display after the progress bar.
    :param fill: Character used to fill the progress bar.
    """
    terminal_columns = shutil.get_terminal_size().columns  # Requires `import shutil`

    percentage = 1.0
    if total_iterations != 0:
        percentage = current_iteration / float(total_iterations)
    # Calculate the available space for the progress bar
    available_space = terminal_columns - len(
        f"\r{prefix} ||{current_iteration}/{total_iterations} ||100.0% {suffix}"
    )

    # Calculate the filled length of the progress bar
    filled_length = int(available_space * (percentage))

    # Build the progress bar
    progress_bar = fill * filled_length + "-" * (available_space - filled_length)

    # Format the percentage complete
    percent_complete = ("{0:.1f}").format(100 * (percentage))

    # Print the progress bar
    print(
        f"\r{prefix} |{progress_bar}|{current_iteration}/{total_iterations} |{percent_complete}% {suffix}",
        end="",
        flush=True,
    )


def save_json(data: dict, json_path: str) -> None:
    """
    Writes JSON data to a file.

    :param data: The JSON data to be written.
    :param json_path: The path to the JSON file.
    """
    # Ensure the directory structure exists
    os.makedirs(os.path.dirname(json_path), exist_ok=True)

    # Write the dictionary to the JSON file
    with open(json_path, "w") as json_file:
        json.dump(data, json_file, indent=4)


def get_pass_k(total_list, correct_list, answers_per_task):
    """
    Calculates the pass@k metric.

    :param total_list: List of total attempts made for each answer.
    :param correct_list: List of correct attempts made for each answer.
    :param answers_per_task: Number of answers per task.
    :return: pass@k value
    """
    pass_k = estimate_pass_at_k(
        np.array(total_list),
        np.array(correct_list),
        answers_per_task,
    )
    pass_k = pass_k.tolist()
    pass_k = sum(pass_k) / len(pass_k)
    return pass_k


def run_cyberseceval(model_loader: ModelLoader, results_dir: str):
    model_name = f"{model_loader.name}_{model_loader.conversation_type}"
    model = ANY(model_name, "123", model_loader)
    cyberseceval_config_file = os.path.join(
        ROOT_PATH, "config", "cyberseceval_config.json"
    )

    with open(cyberseceval_config_file, "r") as f:
        cyberseceval_configs = json.load(f)

    os.environ["WEGGLI_PATH"] = cyberseceval_configs["paths"]["WEGGLI_PATH"]
    os.environ["PATH"] = (
        os.environ.get("WEGGLI_PATH", "") + ":" + os.environ.get("PATH", "")
    )
    cyberseceval_dataset_path = os.path.join(
        ROOT_PATH,
        "datasets",
        "suites",
        "PurpleLlama",
        "CybersecurityBenchmarks",
        "datasets",
    )
    results_path = os.path.join(
        ROOT_PATH,
        "results",
        results_dir,
        model_loader.name,
        cyberseceval_configs["testing_configs"]["results_dir"],
    )

    if not os.path.exists(results_path):
        os.makedirs(results_path)

    benchmarks = cyberseceval_configs["testing_configs"]["benchmarks"]
    llm_under_test = [model]
    judge_llm = None
    expansion_llm = None
    judge_model = None
    expansion_model = None

    for benchmark in benchmarks:

        if benchmark == "mitre":
            judge_llm = cyberseceval_configs["benchmark_configs"][benchmark][
                "judge_llm"
            ]
            expansion_llm = cyberseceval_configs["benchmark_configs"][benchmark][
                "expansion_llm"
            ]
            judge_host, judge_name, _ = judge_llm.split("::")
            if judge_host == "ANY":
                if judge_name == model_name:
                    judge_llm = model
                else:
                    judge_model = create_framework_model("judge", cyberseceval_configs)
                    judge_llm = ANY(judge_name, "123", judge_model)
            else:
                judge_llm = cyberseceval_create_llm(judge_llm)
            expansion_host, expansion_name, _ = expansion_llm.split("::")
            if expansion_host == "ANY":
                if expansion_name == model_name:
                    expansion_llm = model
                else:
                    expansion_model = create_framework_model(
                        "expansion", cyberseceval_configs
                    )
                    expansion_llm = ANY(expansion_name, "123", expansion_model)
            else:
                expansion_llm = cyberseceval_create_llm(expansion_llm)
            if cyberseceval_configs["benchmark_configs"]["mitre"]["with_augmentation"]:
                prompt_path = os.path.join(
                    cyberseceval_dataset_path,
                    f"{benchmark}/mitre_benchmark_100_per_category_with_augmentation.json",
                )
            else:
                prompt_path = os.path.join(
                    cyberseceval_dataset_path,
                    f"{benchmark}/mitre_benchmark_100_per_category.json",
                )
        else:
            prompt_path = os.path.join(
                cyberseceval_dataset_path, f"{benchmark}/{benchmark}.json"
            )

        if benchmark == "prompt-injection":
            prompt_path = os.path.join(
                cyberseceval_dataset_path, f"prompt_injection/prompt_injection.json"
            )
            judge_llm = cyberseceval_configs["benchmark_configs"][benchmark][
                "judge_llm"
            ]
            judge_host, judge_name, _ = judge_llm.split("::")
            if judge_host == "ANY":
                if judge_name == model_name:
                    judge_llm = model
                else:
                    judge_model = create_framework_model("judge", cyberseceval_configs)
                    judge_llm = ANY(judge_name, "123", judge_model)
            else:
                judge_llm = cyberseceval_create_llm(judge_llm)

        if benchmark == "interpreter":
            judge_llm = cyberseceval_configs["benchmark_configs"][benchmark][
                "judge_llm"
            ]
            judge_host, judge_name, _ = judge_llm.split("::")
            if judge_host == "ANY":
                if judge_name == model_name:
                    judge_llm = model
                else:
                    judge_model = create_framework_model("judge", cyberseceval_configs)
                    judge_llm = ANY(judge_name, "123", judge_model)
            else:
                judge_llm = cyberseceval_create_llm(judge_llm)

        if benchmark == "canary-exploit":
            expansion_llm = cyberseceval_configs["benchmark_configs"][benchmark][
                "judge_llm"
            ]
            expansion_host, expansion_name, _ = expansion_llm.split("::")
            if expansion_host == "ANY":
                if expansion_name == model_name:
                    expansion_llm = model
                else:
                    expansion_model = create_framework_model(
                        "expansion", cyberseceval_configs
                    )
                    expansion_llm = ANY(expansion_name, "123", expansion_model)
            else:
                expansion_llm = cyberseceval_create_llm(expansion_llm)

        response_path = os.path.join(results_path, f"{benchmark}_responses.json")
        judge_response_path = os.path.join(
            results_path, f"{benchmark}_judge_responses.json"
        )
        stat_path = os.path.join(results_path, f"{benchmark}_stat.json")

        print(f"\nStarting {benchmark} benchmark with CyberSecEval2...\n")

        if judge_llm is not None:
            print(f"    Judge LLM: {judge_llm.model}\n")
        if expansion_llm is not None:
            print(f"    Expansion LLM: {expansion_llm.model}\n")

        cyberseceval_run(
            default_benchmark=benchmark,
            llms_under_test=llm_under_test,
            default_prompt_path=prompt_path,
            default_response_path=response_path,
            default_stat_path=stat_path,
            default_judge_response_path=judge_response_path,
            judge_llm=judge_llm,
            expansion_llm=expansion_llm,
        )

        if judge_model is not None:
            judge_model.unload_model_tokenizer()
        if expansion_model is not None:
            expansion_model.unload_model_tokenizer()


class ConfigurationProxy:
    def __init__(self):
        self.__dict__ = {}

    def __getattr__(self, name):
        return self.__dict__.get(name)

    def __setattr__(self, name, value):
        self.__dict__[name] = value


def create_framework_model(type: str, config: dict) -> ModelLoader:
    configuration = ConfigurationProxy()
    for key, value in config["testing_configs"][f"{type}_llm_config"].items():
        setattr(configuration, key, value)
    model_id, template_name, conversation_type = configuration.model_config.split(":")
    new_model = ModelLoader(configuration, model_id, template_name, conversation_type)
    new_model.load_model_tokenizer()

    return new_model
