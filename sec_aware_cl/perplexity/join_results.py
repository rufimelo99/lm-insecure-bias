## This a script to merge the files from 2 different "resilts" folders
import argparse
import json
import os

from tqdm import tqdm

from sec_aware_cl.perplexity.perplexity import write_jsonl


def merge_results(directory1, directory2, output_dir):
    for folder in os.listdir(directory1):
        if folder not in ["data"]:
            continue

        for file in tqdm(os.listdir(os.path.join(directory1, folder)), total=144):

            cwe = file.split(".")[0]
            vulnerable_perplexities = []
            safe_perplexities = []

            with open(os.path.join(directory1, folder, file), "r") as f:
                for line in f:
                    data = json.loads(line)

                    vulnerable_perplexities.extend(data["vulnerable"])
                    safe_perplexities.extend(data["safe"])

            with open(os.path.join(directory2, folder, file), "r") as f:
                for line in f:
                    data = json.loads(line)

                    vulnerable_perplexities.extend(data["vulnerable"])
                    safe_perplexities.extend(data["safe"])

            results = {
                "cwe": cwe,
                "vulnerable": vulnerable_perplexities,
                "safe": safe_perplexities,
            }
            write_jsonl(results, os.path.join(output_dir, f"{cwe}.jsonl"), append=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Merge results from 2 different directories"
    )

    parser.add_argument(
        "--directory1",
        type=str,
        help="The first directory to merge",
        required=True,
    )

    parser.add_argument(
        "--directory2",
        type=str,
        help="The second directory to merge",
        required=True,
    )

    parser.add_argument(
        "--output_dir",
        type=str,
        help="The output directory",
        required=True,
    )

    args = parser.parse_args()

    merge_results(args.directory1, args.directory2, args.output_dir)
