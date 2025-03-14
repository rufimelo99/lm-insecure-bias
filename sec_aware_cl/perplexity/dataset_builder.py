import argparse
import os
import gdown

from dataclasses import dataclass

@dataclass
class PrimeVul:
    training_link: str = "https://drive.google.com/uc?id=1yqMzbjB7Apo3E1lOmLbhQxvSkpS8r-hk"
    testing_link: str = "https://drive.google.com/uc?id=1yv-lTCbcwRmmYFzkk6PSnJNpxR9KxA0z"
    validation_link: str = "https://drive.google.com/uc?id=1aI7pGuMOgq3dn9w6g_QAv7cjDmWU1vKt"

def download_dataset(dataset: PrimeVul, directory: str):
    if not os.path.exists(directory):
        os.makedirs(directory)

    files = {
        "training.jsonl": dataset.training_link,
        "testing.jsonl": dataset.testing_link,
        "validation.jsonl": dataset.validation_link
    }

    for filename, url in files.items():
        file_path = os.path.join(directory, filename)

        if not os.path.exists(file_path):
            print(f"Downloading {filename}...")
            gdown.download(url, file_path, quiet=False)
        else:
            print(f"{filename} already exists. Skipping download.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download PrimeVul dataset")

    parser.add_argument(
        "--directory",
        type=str,
        help="The directory to store the dataset",
        default="dataset",
    )

    args = parser.parse_args()

    dataset = PrimeVul()  # Create an instance of PrimeVul
    download_dataset(dataset, args.directory)

    print(f"Downloaded dataset to {args.directory}")
