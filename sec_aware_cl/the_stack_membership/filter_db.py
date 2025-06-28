# Iterate over the dataset
import argparse

from datasets import IterableDataset, load_dataset
from tqdm import tqdm


def parse_args():
    parser = argparse.ArgumentParser(description="Filter the dataset")
    parser.add_argument(
        "--project_txt",
        type=str,
        default="security_projects.txt",
    )

    parser.add_argument(
        "--output_projects_txt",
        type=str,
        default="all_projects.txt",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    project_txt = args.project_txt
    output_projects_txt = args.output_projects_txt

    with open(project_txt, "r") as f:
        projects = set(f.read().splitlines())

    # Convert to lowercase
    projects = {project.lower() for project in projects}

    # Load the dataset in streaming mode
    dataset = load_dataset("bigcode/the-stack-v2", split="train", streaming=True)
    dataset = dataset.take(10)

    # Collect all repo names
    repo_names = set()
    for example in tqdm(dataset, total=2_800_000_000):
        repo_name = example["repo_name"].lower()
        with open(output_projects_txt, "a") as f:
            f.write(repo_name + "\n")

    # Filter based on "repo_name"
    dataset: IterableDataset = dataset.filter(
        lambda x: x["repo_name"].lower() in projects,
    )

    # convert to dataset and push to hub
    dataset = dataset.to_dataset()
    dataset.push_to_hub("rufimelo/test")
