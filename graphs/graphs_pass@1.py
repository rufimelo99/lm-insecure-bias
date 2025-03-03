import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import json
import os
import numpy as np
import pandas as pd
import shutil


def merge_json_files(input_folder, output_file):
    merged_data = {}

    # Get a list of all summary JSON files in the input folder
    prefixes = ["instruction", "infilling"]
    json_files = []

    for root, dirs, files in os.walk(input_folder):
        for file in files:
            if any(
                file.startswith(prefix + "_summary.json")
                or file.startswith("instruct_stat.json")
                for prefix in prefixes
            ):
                json_files.append(os.path.join(root, file))

    json_files.sort()  # Sort the list of JSON files

    # Iterate over each JSON file and merge the data
    for json_file in json_files:
        with open(json_file) as file:
            data = json.load(file)
            filename = os.path.basename(json_file)
            if filename == "instruct_stat.json":
                conversation_type = "instruction"
            else:
                filename = os.path.splitext(filename)[0]
                conversation_type = filename.split("_")[0]
            if conversation_type not in merged_data:
                merged_data[conversation_type] = []

            merged_data[conversation_type].append(data)

    output_directory = os.path.dirname(output_file)
    os.makedirs(output_directory, exist_ok=True)

    # Write the merged data to the output file
    with open(output_file, "w") as output:
        json.dump(merged_data, output, indent=6)


def plot_errors(result_directory, dataset):

    all_error_info = {}

    # Get the errors of each model and config
    for json_file in os.listdir(result_directory):
        filename = os.path.basename(json_file)
        filename = os.path.splitext(filename)[0]
        model_name = filename.split("_")[0]
        if json_file.endswith(".json"):
            json_file_path = os.path.join(result_directory, json_file)
            with open(json_file_path) as file:
                data = json.load(file)

            error_info = {}
            for config_type, config_data in data.items():
                for entry in config_data:
                    if entry["Name"] == dataset:
                        error_info[config_type] = {}

                        for key, value in entry["Statistics"]["0"].items():
                            if key.endswith("errors"):
                                error_info[config_type][key] = value

            all_error_info[model_name] = {}
            all_error_info[model_name] = error_info

    # Plotting Errors
    df = pd.DataFrame.from_dict(
        {
            (i, j): all_error_info[i][j]
            for i in all_error_info.keys()
            for j in all_error_info[i].keys()
        },
        orient="index",
    )

    # Plotting using Pandas plot
    fig, ax = plt.subplots(figsize=(12, 6))
    df.unstack().plot(kind="bar", ax=ax, width=0.8)

    ax.set_xlabel("Models")
    ax.set_ylabel("Number of errors")
    ax.set_title(f"Amount of Errors for {dataset}")
    ax.legend(title="Errors", bbox_to_anchor=(1.05, 1), loc="upper left")

    plt.savefig(f"./graphs/{dataset}_error_plot.png", bbox_inches="tight")


def plot_pass_at_k(result_directory, dataset):

    all_pass_at_k_info = {}

    # Get the pass@k values of each model and config
    for json_file in os.listdir(result_directory):
        filename = os.path.basename(json_file)
        filename = os.path.splitext(filename)[0]
        model_name = filename.split("_")[0]
        if json_file.endswith(".json"):
            json_file_path = os.path.join(result_directory, json_file)
            with open(json_file_path) as file:
                data = json.load(file)

            pass_at_k_info = {}
            for config_type, config_data in data.items():
                for entry in config_data:
                    if entry["Name"] == dataset:
                        pass_at_k_info[config_type] = {}

                        for key, value in entry["Statistics"]["0"].items():
                            if key.startswith("Pass@"):
                                pass_at_k_info[config_type][key] = value

            all_pass_at_k_info[model_name] = {}
            all_pass_at_k_info[model_name] = pass_at_k_info

    # Plotting Pass@k
    df = pd.DataFrame.from_dict(
        {
            (i, j): all_pass_at_k_info[i][j]
            for i in all_pass_at_k_info.keys()
            for j in all_pass_at_k_info[i].keys()
        },
        orient="index",
    )

    # Plotting using Pandas plot
    fig, ax = plt.subplots(figsize=(12, 6))
    df.unstack().plot(kind="bar", ax=ax, width=0.8)

    ax.set_xlabel("Models")
    ax.set_ylabel("Pass@k (%)")
    ax.set_title(f"Pass@k Values for {dataset}")
    ax.legend(title="Pass@k", bbox_to_anchor=(1.05, 1), loc="upper left")

    plt.savefig(f"./graphs/{dataset}_pass_at_k_plot.png", bbox_inches="tight")


def combine_dataset_pass1(result_directory, datasets: list):

    all_pass_at_1_info = {}

    # Get the pass@k values of each model and config
    for json_file in os.listdir(result_directory):
        filename = os.path.basename(json_file)
        filename = os.path.splitext(filename)[0]
        model_name = filename.split("_")[0]
        if "GPTQ" in model_name:
            model_name = model_name.replace("-GPTQ", "")
        if "4-Bit" in model_name:
            model_name = model_name.replace("-4-Bit", "")
        all_pass_at_1_info[model_name] = {}
        for dataset in datasets:

            if json_file.endswith(".json"):
                json_file_path = os.path.join(result_directory, json_file)
                with open(json_file_path) as file:
                    data = json.load(file)

                pass_at_k_info = {}
                for config_type, config_data in data.items():
                    for i, entry in enumerate(config_data):
                        if dataset == "CyberSecEval2" and i == 0:
                            for model, value in data["instruction"][0].items():
                                pass_tot = 0
                                for i, (_, val) in enumerate(value.items(), 1):
                                    pass_tot += val["pass_rate"]
                            pass_at_k_info["Pass@1"] = pass_tot / i
                            all_pass_at_1_info[model_name][dataset] = pass_at_k_info
                        elif i > 0:
                            if entry["Name"] == dataset:
                                for key, value in entry["Statistics"]["0"].items():
                                    if key.startswith("Pass@"):
                                        pass_at_k_info[key] = value

                            all_pass_at_1_info[model_name][dataset] = pass_at_k_info

    # Plotting the pass@1 scores
    num_datasets = len(datasets)
    bar_width = 0.25  # Width of each bar

    # Define sorting function (sorts by HumanEval score, model name as tiebreaker)
    def sort_by_human_eval(item):
        model_name, data = item
        return data["HumanEval"]["Pass@1"], model_name

    # Sort all_pass_at_1_info (highest HumanEval first)
    sorted_data = dict(
        sorted(all_pass_at_1_info.items(), key=sort_by_human_eval, reverse=True)
    )
    sorted_model_names = list(sorted_data.keys())

    plt.figure(figsize=(10, 6), facecolor="white")  # Adjust the size here
    plt.rcParams["text.color"] = "w"

    ax = plt.gca()
    ax.set_facecolor("white")

    # Loop through datasets and plot bars directly from sorted data
    for i, dataset in enumerate(datasets):
        pass_at_1_scores = [
            sorted_data[model_name][dataset]["Pass@1"]
            for model_name in sorted_model_names
        ]

        plt.bar(
            np.arange(len(sorted_model_names)) + i * bar_width,
            pass_at_1_scores,
            bar_width,
            align="center",
            alpha=0.7,
            label=dataset,
        )

        # Annotate each bar with its height (pass@1 score)
        for x, y in zip(
            np.arange(len(sorted_model_names)) + i * bar_width, pass_at_1_scores
        ):
            plt.text(
                x, y, f"{y:.2f}", ha="center", va="bottom", fontsize=5.80, color="white"
            )

    plt.xlabel("Model Name", color="white")
    plt.ylabel("Pass@1 Score", color="white")
    plt.title("Pass@1 Scores for Models (Sorted by HumanEval)", color="white")

    # Use sorted model names for x-axis labels with proper spacing
    plt.xticks(
        np.arange(len(sorted_model_names)) + (num_datasets - 1) * bar_width / 2,
        sorted_model_names,
        rotation=45,
        ha="right",
        color="white",
    )

    plt.yticks(color="white")

    plt.legend(labelcolor="black")
    plt.tight_layout()
    # Get the current axes
    ax = plt.gca()

    # Set the figure and axes face color to white
    plt.gcf().patch.set_facecolor("white")
    ax.set_facecolor("white")

    # Set the axes edge color (spines) to white
    ax.spines["top"].set_color("white")
    ax.spines["right"].set_color("white")
    ax.spines["bottom"].set_color("white")
    ax.spines["left"].set_color("white")
    ax.tick_params(axis="x", colors="white")
    ax.tick_params(axis="y", colors="white")

    plt.savefig(
        f"./graphs/combined_pass_at_1_plot.png",
        bbox_inches="tight",
        transparent=True,
        edgecolor="w",
        dpi=300,
    )

    return sorted_model_names


def combine_dataset_succrate(result_directory, datasets: list, sorted_model_names):

    all_passrate_info = {}

    # Get the Success rate values of each model and config
    for json_file in os.listdir(result_directory):
        filename = os.path.basename(json_file)
        filename = os.path.splitext(filename)[0]
        model_name = filename.split("_")[0]
        if "GPTQ" in model_name:
            model_name = model_name.replace("-GPTQ", "")
        if "4-Bit" in model_name:
            model_name = model_name.replace("-4-Bit", "")
        all_passrate_info[model_name] = {}
        for dataset in datasets:

            if json_file.endswith(".json"):
                json_file_path = os.path.join(result_directory, json_file)
                with open(json_file_path) as file:
                    data = json.load(file)

                succrate_info = {}
                for config_type, config_data in data.items():
                    for i, entry in enumerate(config_data):
                        if dataset == "CyberSecEval2" and i == 0:
                            for model, value in data["instruction"][0].items():
                                pass_tot = 0
                                for i, (_, val) in enumerate(value.items(), 1):
                                    pass_tot += val["pass_rate"]
                            succrate_info["Pass Rate"] = pass_tot / i
                            all_passrate_info[model_name][
                                "CyberSecEval Instruct"
                            ] = succrate_info
                        elif i > 0:
                            if entry["Name"] == dataset:
                                for key, value in entry["Statistics"]["0"].items():
                                    if key.startswith("Success Rate"):
                                        succrate_info["Pass Rate"] = value

                            all_passrate_info[model_name][dataset] = succrate_info

        # Plotting the pass@1 scores
    num_datasets = len(datasets)
    bar_width = 0.25  # Width of each bar

    # Define sorting function (sorts by HumanEval score, model name as tiebreaker)
    def sort_by_cyberseceval(item):
        model_name, data = item
        return data["CyberSecEval Instruct"]["Pass Rate"], model_name

    # Sort all_pass_at_1_info (highest HumanEval first)
    sorted_data = dict(
        sorted(all_passrate_info.items(), key=sort_by_cyberseceval, reverse=True)
    )

    plt.figure(figsize=(10, 6), facecolor="white")  # Adjust the size here
    plt.rcParams["text.color"] = "w"

    ax = plt.gca()
    ax.set_facecolor("white")

    datasets[0] = "CyberSecEval Instruct"

    # Loop through datasets and plot bars directly from sorted data
    for i, dataset in enumerate(datasets):
        success_rates = [
            sorted_data[model_name][dataset]["Pass Rate"]
            for model_name in sorted_model_names
        ]

        plt.bar(
            np.arange(len(sorted_model_names)) + i * bar_width,
            success_rates,
            bar_width,
            align="center",
            alpha=0.7,
            label=dataset,
        )

        # Annotate each bar with its height (pass@1 score)
        for x, y in zip(
            np.arange(len(sorted_model_names)) + i * bar_width, success_rates
        ):
            plt.text(
                x, y, f"{y:.2f}", ha="center", va="bottom", fontsize=5.80, color="white"
            )

    plt.xlabel("Model Name", color="white")
    plt.ylabel("Pass Rate", color="white")
    plt.title("Pass Rate for Models", color="white")

    # Use sorted model names for x-axis labels with proper spacing
    plt.xticks(
        np.arange(len(sorted_model_names)) + (num_datasets - 1) * bar_width / 2,
        sorted_model_names,
        rotation=45,
        ha="right",
        color="white",
    )

    plt.yticks(color="white")

    plt.legend(loc="center right", labelcolor="black")
    plt.tight_layout()
    # Get the current axes
    ax = plt.gca()

    # Set the figure and axes face color to white
    plt.gcf().patch.set_facecolor("white")
    ax.set_facecolor("white")

    # Set the axes edge color (spines) to white
    ax.spines["top"].set_color("white")
    ax.spines["right"].set_color("white")
    ax.spines["bottom"].set_color("white")
    ax.spines["left"].set_color("white")
    ax.tick_params(axis="x", colors="white")
    ax.tick_params(axis="y", colors="white")

    plt.savefig(
        f"./graphs/combined_passrate_plot.png",
        bbox_inches="tight",
        transparent=True,
        edgecolor="w",
        dpi=300,
    )


if __name__ == "__main__":

    # Get the absolute path of the current file
    current_file_path = os.path.abspath(__file__)
    # Get the parent directory (one step above the current file)
    parent_directory = os.path.dirname(current_file_path)
    # Get the grandparent directory (two step above the current file)
    grandparent_directory = os.path.dirname(parent_directory)
    default_result_path = os.path.join(grandparent_directory, "results/code_eval/")
    merged_dir = os.path.join(default_result_path, "merged")

    if os.path.exists(merged_dir):
        shutil.rmtree(merged_dir, ignore_errors=True)

    for model_name in os.listdir(default_result_path):
        model_path = os.path.join(default_result_path, model_name)
        if os.path.isdir(model_path) and model_path != merged_dir:

            merge_json_files(
                model_path, os.path.join(merged_dir, model_name + "_merged.json")
            )

    # Create directory for saving plotting results
    graph_directory = os.path.join(current_file_path, "graphs")
    os.makedirs(parent_directory, exist_ok=True)

    # Define dataset (QuixBugs Python, QuixBugs Java, HumanEval)
    datasets = ["HumanEval", "QuixBugs Python", "QuixBugs Java"]

    sorted_models = combine_dataset_pass1(merged_dir, datasets)
    datasets = ["CyberSecEval2", "SecurityEval", "llm-vul"]
    combine_dataset_succrate(merged_dir, datasets, sorted_models)
