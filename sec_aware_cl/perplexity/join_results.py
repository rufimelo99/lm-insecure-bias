## This a script to merge the files from 2 different "resilts" folders
import argparse
import json
import os

from tqdm import tqdm

from sec_aware_cl.perplexity.perplexity import write_jsonl


def merge_results(directory1, directory2, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for file in tqdm(os.listdir(os.path.join(directory1)), total=144):

        cwe = file.split(".")[0]

        with open(os.path.join(directory1, file), "r") as f:
            for line in f:
                data = json.loads(line)

                write_jsonl(data, os.path.join(output_dir, f"{cwe}.jsonl"), append=True)

        with open(os.path.join(directory2, file), "r") as f:
            for line in f:
                data = json.loads(line)

                write_jsonl(data, os.path.join(output_dir, f"{cwe}.jsonl"), append=True)


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
