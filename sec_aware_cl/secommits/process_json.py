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


def get_github_api_url(project_url, commit_hash):
    """
    Construct the GitHub API URL for a specific commit.

    Args:
        project_url (str): The GitHub repository URL.
        commit_hash (str): The commit SHA.

    Returns:
        str or None: GitHub API URL or None if the input URL is invalid.
    """
    try:
        parsed = urlparse(project_url)
        if parsed.netloc not in ("github.com", "www.github.com"):
            raise ValueError("Not a GitHub URL.")

        # Remove leading/trailing slashes and extract user/repo
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) < 2:
            raise ValueError("Incomplete GitHub repo path.")

        user_repo = "/".join(path_parts[:2])
        return f"https://api.github.com/repos/{user_repo}/commits/{commit_hash}"

    except Exception as e:
        logger.error(f"Invalid project URL format: {e}")
        return None


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

        for line in patch.splitlines():
            if not line.startswith("-"):
                after_output.append(line)

        # Normalize the patch lines
        prior_output = normalize_patch(prior_output)
        after_output = normalize_patch(after_output)

        return prior_output, after_output


def main(json_path, output_path):
    df_csv = pd.read_json(
        json_path,
        orient="table",
    )

    df_csv = df_csv[df_csv["chain_len"] == 1]
    df_csv["files"] = df_csv["files"].progress_apply(lambda x: eval(x))
    df_csv = df_csv[df_csv["files"].apply(lambda x: len(x) == 1)]

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
        required=True,
        help="Path to the output JSONL file.",
    )

    args = parser.parse_args()
    json_path = args.json_path
    output_path = args.output_path

    main(json_path, output_path)
