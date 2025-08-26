import argparse
import json
import os
from json import JSONDecodeError

from tqdm import tqdm

from sec_aware_cl.logger import logger
from sec_aware_cl.perplexity.perplexity import write_jsonl

SKIP_FILES = {"alignment_stats.jsonl"}


def list_files(directory: str):
    try:
        return set(os.listdir(directory))
    except FileNotFoundError:
        logger.warning(f"Input directory not found, skipping: {directory}")
        return set()


def merge_results(directories, output_dir):
    """
    Merge JSONL files from multiple 'results' directories into one output directory.
    For each CWE (derived from filename stem), deduplicate by `model` key.
    """
    if not directories:
        logger.error("No input directories provided.")
        return

    os.makedirs(output_dir, exist_ok=True)

    # Build the union of filenames across all input directories (minus files to skip)
    all_files = set()
    for d in directories:
        files = {f for f in list_files(d) if f not in SKIP_FILES}
        all_files.update(files)

    for file in tqdm(sorted(all_files), desc="Merging files"):
        cwe = file.split(".")[0]
        seen_models = set()
        out_path = os.path.join(output_dir, f"{cwe}.jsonl")

        for d in directories:
            in_path = os.path.join(d, file)
            if not os.path.isfile(in_path):
                continue

            with open(in_path, "r") as f:
                for i, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except JSONDecodeError:
                        logger.warning(f"Bad JSON in {in_path}:{i}, skipping line.")
                        continue

                    model = data.get("model")
                    if model is None:
                        logger.warning(
                            f"No 'model' key in {in_path}:{i}, skipping line."
                        )
                        continue

                    if model in seen_models:
                        logger.warning(
                            f"Model {model} already seen for {cwe}, skipping duplicate."
                        )
                        continue

                    seen_models.add(model)
                    write_jsonl(data, out_path, append=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Merge results from multiple directories (JSONL files), "
        "deduplicating by 'model' within each file group."
    )

    parser.add_argument(
        "--directories",
        type=str,
        nargs="+",
        required=True,
        help="One or more input directories to merge (space-separated).",
    )

    parser.add_argument(
        "--output_dir",
        type=str,
        required=True,
        help="The output directory where merged files will be written.",
    )

    args = parser.parse_args()
    merge_results(args.directories, args.output_dir)
