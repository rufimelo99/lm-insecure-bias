import argparse
import json
import os
from urllib.parse import urlparse

import pandas as pd
import requests
from tqdm import tqdm

from sec_aware_cl.logger import logger

GITHUB_BEARER_TOKEN = os.getenv("GITHUB_BEARER_TOKEN")

tqdm.pandas()


def get_cwe(x):
    try:
        cwe_set = eval(x)
        if len(cwe_set) > 1:
            print(f"Warning: multiple CWEs found for {x}")
            return None
        else:
            return cwe_set.pop()
    except:
        return None


def get_cwes(x):
    cwe_set = eval(x)
    return list(cwe_set)


def get_file_extension(files: set):
    files = list(files.keys())
    file = files[0]
    return file.split(".")[-1] if "." in file else None


def filter_by_file_extension(df, supported_file_extensions):
    return df[df["file_extension"].isin(supported_file_extensions)]


def get_github_api_url(project, commit_hash):
    # Extract the project name from the URL
    try:
        project_name = project.split("https://github.com/")[1]
    except IndexError:
        try:
            project_name = project.split("http://github.com/")[1]
        except IndexError:
            logger.error("Invalid project URL format.")
            return None

    # Construct the API URL for the diff
    api_url = f"https://api.github.com/repos/{project_name}/commits/{commit_hash}"

    return api_url


def get_commit_info(api_url):
    # Set the headers for the request
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {GITHUB_BEARER_TOKEN}",
    }

    # Send the GET request to the GitHub API
    response = requests.get(api_url, headers=headers)
    # Check if the request was successful
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        return None


def get_file_info(api_response, specific_file):
    if "files" not in api_response:
        logger.error("No files found in the API response.")
        return None

    file_info = next(
        (file for file in api_response["files"] if file["filename"] == specific_file),
        None,
    )

    if not file_info:
        logger.error(f"File {specific_file} not found in the API response.")
        return None

    return {
        "filename": file_info["filename"],
        "additions": file_info["additions"],
        "deletions": file_info["deletions"],
        "changes": file_info["changes"],
        "status": file_info["status"],
        "patch": file_info["patch"],
    }


def normalize_patch(lines) -> str:
    out = []
    for line in lines:
        if line.startswith("@@"):
            # Remove the line number information
            line = line.split("@@")[-1]
        elif line.startswith("+") or line.startswith("-"):
            # Remove the leading "+" or "-" and any trailing whitespace
            line = " " + line[1:]
        out.append(line)
    return "".join(out)


def get_diff_versions_from_commit(commit, write_to_file=False):
    if "files" not in commit:
        logger.error("No files found in the commit.")
        return None, None
    for f in commit.get("files", []):
        # filename = f["filename"].replace("/", "_")
        patch = f.get("patch", "")

        prior_output = []
        after_output = []
        for line in patch.splitlines():
            if not line.startswith("+"):
                prior_output.append(line)
            if not line.startswith("-"):
                after_output.append(line)

        # Normalize the patch lines
        prior_output = normalize_patch(prior_output)
        after_output = normalize_patch(after_output)

        return prior_output, after_output


def main(json_path, output_path, final_output_path):
    df_csv = pd.read_json(
        json_path,
        orient="table",
    )
    print(f"Initial shape: {df_csv.shape}")
    df_csv = df_csv[df_csv["chain_len"] == 1]
    print(f"Shape after filtering chain_len == 1: {df_csv.shape}")
    df_csv["files"] = df_csv["files"].progress_apply(lambda x: eval(x))
    df_csv = df_csv[df_csv["files"].apply(lambda x: len(x) == 1)]
    print(f"Shape after filtering files with length == 1: {df_csv.shape}")

    logger.info("Processing the data to extract vulnerable information.")
    df_csv = df_csv.reset_index(drop=True)
    # Iterate over the DataFrame rows and extract vulnerable information
    for index, row in tqdm(df_csv.iterrows(), total=df_csv.shape[0]):
        commit_href = get_github_api_url(row["project"], row["commit_sha"])
        res = get_commit_info(commit_href)
        # specific_file = list(row["files"].keys())[0]
        # file_info = get_file_info(res, specific_file)
        if not res:
            logger.error(f"Failed to retrieve commit info for {row['commit_sha']}")
            continue

        prior_version, after_version = get_diff_versions_from_commit(res)
        df_csv.at[index, "prior_version"] = prior_version
        df_csv.at[index, "after_version"] = after_version

        row_json = row.to_dict()
        row_json["prior_version"] = prior_version
        row_json["after_version"] = after_version

        # Append to the jsonl file
        with open(output_path, "a") as f:
            f.write(json.dumps(row_json) + "\n")

    logger.info("Processing completed.")

    df = pd.read_json(output_path, lines=True)
    print(f"Initial shape: {df.shape}")
    df = df.drop_duplicates(subset=["vuln_id"])
    print(f"Shape after dropping duplicates: {df.shape}")
    df = df[~df["cwe_id"].isna()]
    print(f"Shape after dropping rows with NaN cwe_id: {df.shape}")
    df = df[~df["score"].isna()]
    print(f"Shape after dropping rows with NaN score: {df.shape}")

    df["file_extension"] = df["files"].apply(lambda x: get_file_extension(x))
    df = filter_by_file_extension(
        df,
        [
            "java",
            "ts",
            "php",
            "js",
            "cc",
            "py",
            "go",
            "kt",
            "rb",
            "rs",
            "cs",
            "cpp",
            "c",
            "html",
            "xml",
        ],
    )
    print(f"Shape after filtering by file extension: {df.shape}")

    new_df = pd.DataFrame(columns=list(df.columns) + ["cwe"])

    for i in df.iterrows():
        cwes = get_cwes(i[1]["cwe_id"])
        row = i[1].to_dict()
        for cwe in cwes:
            if cwe in ["NVD-CWE-noinfo", "NVD-CWE-Other"]:
                continue
            row["cwe"] = cwe
            new_df = pd.concat([new_df, pd.DataFrame([row])], ignore_index=True)

    print(f"Shape after expanding CWEs: {new_df.shape}")
    new_df = new_df.groupby("cwe").filter(lambda x: len(x) >= 10)
    print(f"Shape after filtering by CWE count >= 10: {new_df.shape}")

    with open(final_output_path, "w") as f:
        for record in new_df.to_dict(orient="records"):
            json.dump(record, f)
            f.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process JSON files.")
    parser.add_argument(
        "--json_path",
        type=str,
        required=True,
        help="Path to the input JSON file.",
        default="secommits-raw.json",
    )

    parser.add_argument(
        "--output_path",
        type=str,
        help="Path to the output JSONL file.",
        default="secommits_filtered.jsonl",
    )
    parser.add_argument(
        "--final_output_path",
        type=str,
        help="Path to the output JSONL file.",
        default="secommits_filtered_final.jsonl",
    )

    args = parser.parse_args()
    json_path = args.json_path
    output_path = args.output_path
    final_output_path = args.final_output_path

    main(json_path, output_path, final_output_path)
