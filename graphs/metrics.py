import matplotlib.pyplot as plt
import json
import os
import numpy as np
import pandas as pd


def load_json_brief_summary(input_folder):
    merged_data = {}

    # Find each summary file
    json_files = find_files(input_folder, "brief_summary.json")

    json_data = []

    for file in json_files:
        json_data.append(load_json_file(file))

    return json_data


def find_files(path, extension):
    found_files = []
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(extension):
                found_files.append(os.path.join(root, file))
    return found_files


def load_json_file(file_path):
    with open(file_path, "r") as file:
        data = json.load(file)
    return data


def all_models_and_datasets(json_data, key, save_name, y_label, title, exclude=[]):
    # Extract relevant data and calculate speed difference
    model_data = {}  # Store data for each model
    for data in json_data:
        model_name = data["Model name"]
        dataset_name = data["Name"]
        if dataset_name in exclude:
            continue
        speed = data[key]

        if model_name not in model_data:
            model_data[model_name] = {"datasets": [], "speeds": []}

        model_data[model_name]["datasets"].append(dataset_name)
        model_data[model_name]["speeds"].append(speed)

    # Plotting
    plt.figure(figsize=(10, 6))  # Adjust the figure size as per your preference

    for model_name, data in model_data.items():
        plt.plot(data["datasets"], data["speeds"], label=model_name)

    plt.xlabel("Dataset Name")
    plt.ylabel(y_label)
    plt.title(title)
    plt.xticks(rotation=45)  # Rotate x-axis labels for better readability
    plt.legend()  # Show legend with model names
    plt.tight_layout()  # Adjust layout to prevent overlapping labels
    plt.savefig(f"graphs/{save_name}")


def table(stats):
    table_data = []
    dataset_names = ""
    for _, model_stat in stats.items():
        model_row = []
        dataset_names = list(model_stat["Datasets summary"].keys())
        dataset_names.append("Combined")
        for _, dataset_stat in model_stat["Datasets summary"].items():
            model_row.append(dataset_stat["new pass@1"])
        model_row.append(model_stat["new pass@1"])
        table_data.append(model_row)

    # Create a DataFrame from the data
    column_labels = dataset_names
    df = pd.DataFrame(table_data, columns=column_labels)
    df = df.round(2)

    # Create a new column to store the original row labels
    df["Model"] = list(stats.keys())

    # Sort rows based on the "Combined" column
    df = df.sort_values(by="Combined", ascending=False)

    # Reset index to maintain the original row labels
    df = df.set_index("Model")

    # Plotting the table
    fig, ax = plt.subplots(1, 1)
    fig.patch.set_visible(False)
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)
    ax.axis("tight")
    ax.axis("off")

    plt.subplots_adjust(left=0.35, right=0.98)

    # Plotting data
    table = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        rowLabels=df.index,  # Use sorted row index
        rowColours=["royalblue"] * len(df.index),
        colColours=["orange"] * len(df.columns),
        loc="center",
    )

    table.scale(1, 1)

    plt.show()


if __name__ == "__main__":
    # Get the absolute path of the current file
    current_file_path = os.path.abspath(__file__)
    # Get the parent directory (one step above the current file)
    grandparent_directory = os.path.dirname(os.path.dirname(current_file_path))

    json_data = load_json_brief_summary(grandparent_directory + "/results/code_eval")

    all_models_and_datasets(
        json_data,
        "Maximum memory usage (GB)",
        "Maximum_memory_usage",
        "Max memory usage (GB)",
        "Example",
        [],
    )

    all_models_and_datasets(
        json_data,
        "Tokens/Sec",
        "Tokens_sec",
        "Tokens/Sec",
        "Example",
        ["SecurityEval"],
    )

    all_models_and_datasets(
        json_data,
        "Tokens generated",
        "Tokens_generated",
        "Tokens",
        "Example",
        ["SecurityEval"],
    )

    all_models_and_datasets(
        json_data,
        "Pass@1",
        "Pass@1",
        "Pass@1",
        "Pass@1 multiple models",
        ["SecurityEval"],
    )
