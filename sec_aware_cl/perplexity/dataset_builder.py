import argparse
import json
import os
from collections import defaultdict
from dataclasses import dataclass

import gdown
from datasets import load_dataset
from tqdm import tqdm

from sec_aware_cl.logger import logger


@dataclass
class PrimeVul:
    training_link: str = (
        "https://drive.google.com/uc?id=1yqMzbjB7Apo3E1lOmLbhQxvSkpS8r-hk"
    )
    testing_link: str = (
        "https://drive.google.com/uc?id=1yv-lTCbcwRmmYFzkk6PSnJNpxR9KxA0z"
    )
    validation_link: str = (
        "https://drive.google.com/uc?id=1aI7pGuMOgq3dn9w6g_QAv7cjDmWU1vKt"
    )


def download_dataset(dataset: PrimeVul, directory: str):
    if not os.path.exists(directory):
        os.makedirs(directory)

    files = {
        "training.jsonl": dataset.training_link,
        "testing.jsonl": dataset.testing_link,
        "validation.jsonl": dataset.validation_link,
    }

    for filename, url in files.items():
        file_path = os.path.join(directory, filename)

        if not os.path.exists(file_path):
            logger.info("Downloading file.", filename=filename)
            gdown.download(url, file_path, quiet=False)
        else:
            logger.warning("File already exists. Skipping download.", filename=filename)


def write_jsonl(data: json, file_path, append=False):
    mode = "a" if append else "w"

    if not os.path.exists(file_path):
        mode = "w"

    with open(file_path, mode) as f:
        f.write(json.dumps(data) + "\n")


def treat_dataset(directory: str):
    # dict_keys(['idx', 'project', 'commit_id', 'project_url', 'commit_url', 'commit_message', 'target', 'func', 'func_hash', 'file_name', 'file_hash', 'cwe', 'cve', 'cve_desc', 'nvd_url'])
    cwe_dict = defaultdict(str)

    if not os.path.exists(os.path.join(directory, "data")):
        os.makedirs(os.path.join(directory, "data"))

    def analyse_line_and_write(line, cwe_dict):
        data = json.loads(line)

        data = {
            "cwe": data["cwe"],
            "func": data["func"],
            "target": data["target"],
        }

        cwe_key = data["cwe"]

        if len(cwe_key) > 1:
            logger.warning("Multiple CWEs found.", cwe=cwe_key)

        cwe_key = cwe_key[0]

        if cwe_key not in cwe_dict:
            cwe_dict[cwe_key] = cwe_key + ".jsonl"
        write_jsonl(
            data, os.path.join(directory + "/" + "data", cwe_dict[cwe_key]), append=True
        )

    with open(os.path.join(directory, "training.jsonl"), "r") as f:
        for line in tqdm(f, total=7578, desc="Processing training dataset"):
            analyse_line_and_write(line, cwe_dict)

    with open(os.path.join(directory, "testing.jsonl"), "r") as f:
        for line in tqdm(f, total=870, desc="Processing testing dataset"):
            analyse_line_and_write(line, cwe_dict)

    with open(os.path.join(directory, "validation.jsonl"), "r") as f:
        for line in tqdm(f, total=960, desc="Processing validation dataset"):
            analyse_line_and_write(line, cwe_dict)


def get_asleep_cwe_label(asleep_entry):
    check_ql = asleep_entry["check_ql"]
    if not check_ql:
        return

    check_ql = check_ql.lower()
    try:
        cwe = int(check_ql.split("cwe-")[1].split("/")[0])
        cwe = f"CWE-{cwe}"
        return cwe
    except:
        return None


def treat_asleep_dataset(directory: str):
    asleep_data = load_dataset("moyix/asleep_keyboard", "DoW")

    for entry in asleep_data["test"]:
        cwe = get_asleep_cwe_label(entry)
        if not cwe:
            continue

        data = {"cwe": [cwe], "func": entry["prompt"], "target": 1}
        filename = cwe + ".jsonl"
        write_jsonl(data, os.path.join(directory + "/" + "data", filename), append=True)


def get_security_eval_cwe_label(asleep_entry):
    id = asleep_entry["ID"]

    id = id.lower()
    try:
        cwe = int(id.split("cwe-")[1].split("_")[0])
        cwe = f"CWE-{cwe}"
        return cwe
    except:
        return


def treat_security_eval_dataset(directory: str):
    ds = load_dataset("s2e-lab/SecurityEval")
    for entry in ds["train"]:
        cwe = get_security_eval_cwe_label(entry)
        if not cwe:
            continue

        data = {"cwe": cwe, "func": entry["Insecure_code"], "target": 1}
        filename = cwe + ".jsonl"
        logger.info("Writing data to file.", filename=filename)
        write_jsonl(data, os.path.join(directory + "/" + "data", filename), append=True)


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
    treat_dataset(args.directory)

    treat_asleep_dataset(args.directory)

    treat_security_eval_dataset(args.directory)

    logger.info("Dataset downloaded and treated.", directory=args.directory)
