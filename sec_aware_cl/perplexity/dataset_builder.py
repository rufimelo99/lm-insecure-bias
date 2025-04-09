import argparse
import json
import os
from collections import defaultdict
from dataclasses import dataclass

import gdown
import pandas as pd
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
    if not os.path.exists(directory):
        os.makedirs(directory)

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


def treat_seccomit_osv_dataset(file_path: str, directory: str):
    # {"vuln_id": "GHSA-2363-cqg2-863c", "cwe_id": "{'CWE-611'}", "score": 7.5, "chain": "{'https://github.com/hunterhacker/jdom/commit/dd4f3c2fc7893edd914954c73eb577f925a7d361'}", "dataset": "osv", "summary": "XML External Entity (XXE) Injection in JDOM An XXE issue in SAXBuilder in JDOM through 2.0.6 allows attackers to cause a denial of service via a crafted HTTP request.  At this time there is not released fixed version of JDOM.  As a workaround, to avoid external entities being expanded, one can call `builder.setExpandEntities(false)` and they won't be expanded.", "published_date": "2021-07-27", "chain_len": 1, "project": "https://github.com/hunterhacker/jdom", "commit_href": "https://github.com/hunterhacker/jdom/commit/dd4f3c2fc7893edd914954c73eb577f925a7d361", "commit_sha": "dd4f3c2fc7893edd914954c73eb577f925a7d361", "patch": "SINGLE", "chain_ord": "['dd4f3c2fc7893edd914954c73eb577f925a7d361']", "before_first_fix_commit": "{'1f81562b5cc813bfbacb7e2842b5be17eb34896b'}", "last_fix_commit": "dd4f3c2fc7893edd914954c73eb577f925a7d361", "chain_ord_pos": 1, "commit_datetime": "07/02/2021, 03:42:05", "message": "Addresses #189 - synchronizes external entity expansion setting", "author": "Rolf Lear", "comments": null, "stats": "{'additions': 6, 'deletions': 0, 'total': 6}", "files": {"core/src/java/org/jdom2/input/SAXBuilder.java": {"additions": 6, "deletions": 0, "changes": 6, "status": "modified", "raw_url": "https://github.com/hunterhacker/jdom/raw/dd4f3c2fc7893edd914954c73eb577f925a7d361/core%2Fsrc%2Fjava%2Forg%2Fjdom2%2Finput%2FSAXBuilder.java", "patch": "@@ -82,6 +82,7 @@ OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT\n import org.jdom2.DocType;\n import org.jdom2.Document;\n import org.jdom2.EntityRef;\n+import org.jdom2.JDOMConstants;\n import org.jdom2.JDOMException;\n import org.jdom2.JDOMFactory;\n import org.jdom2.Verifier;\n@@ -797,6 +798,11 @@ public void setFastReconfigure(final boolean fastReconfigure) {\n \tpublic void setFeature(final String name, final boolean value) {\n \t\t// Save the specified feature for later.\n \t\tfeatures.put(name, value ? Boolean.TRUE : Boolean.FALSE);\n+\t\tif (JDOMConstants.SAX_FEATURE_EXTERNAL_ENT.equals(name)) {\n+\t\t\t// See issue https://github.com/hunterhacker/jdom/issues/189\n+\t\t\t// And PR https://github.com/hunterhacker/jdom/pull/188\n+\t\t\tsetExpandEntities(value);\n+\t\t}\n \t\tengine = null;\n \t}"}}, "prior_version": " OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT import org.jdom2.DocType; import org.jdom2.Document; import org.jdom2.EntityRef; import org.jdom2.JDOMException; import org.jdom2.JDOMFactory; import org.jdom2.Verifier; public void setFastReconfigure(final boolean fastReconfigure) { \tpublic void setFeature(final String name, final boolean value) { \t\t// Save the specified feature for later. \t\tfeatures.put(name, value ? Boolean.TRUE : Boolean.FALSE); \t\tengine = null; \t} ", "after_version": " OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT import org.jdom2.DocType; import org.jdom2.Document; import org.jdom2.EntityRef; import org.jdom2.JDOMConstants; import org.jdom2.JDOMException; import org.jdom2.JDOMFactory; import org.jdom2.Verifier; public void setFastReconfigure(final boolean fastReconfigure) { \tpublic void setFeature(final String name, final boolean value) { \t\t// Save the specified feature for later. \t\tfeatures.put(name, value ? Boolean.TRUE : Boolean.FALSE); \t\tif (JDOMConstants.SAX_FEATURE_EXTERNAL_ENT.equals(name)) { \t\t\t// See issue https://github.com/hunterhacker/jdom/issues/189 \t\t\t// And PR https://github.com/hunterhacker/jdom/pull/188 \t\t\tsetExpandEntities(value); \t\t} \t\tengine = null; \t} "}
    if not os.path.exists(directory):
        os.makedirs(directory)

    if not os.path.exists(os.path.join(directory, "data")):
        os.makedirs(os.path.join(directory, "data"))

    df = pd.read_json(os.path.join(file_path), lines=True)

    for index, row in df.iterrows():
        cwe = row["cwe_id"]
        if not cwe:
            continue
        cwe_set = eval(cwe)
        for cwe in cwe_set:
            data = {
                "cwe": [cwe],
                "func": row["prior_version"],
                "target": 1,
            }
            write_jsonl(
                data,
                os.path.join(directory + "/" + "data", cwe + ".jsonl"),
                append=True,
            )

            data = {
                "cwe": [cwe],
                "func": row["after_version"],
                "target": 0,
            }

            write_jsonl(
                data,
                os.path.join(directory + "/" + "data", cwe + ".jsonl"),
                append=True,
            )


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

    parser.add_argument(
        "--seccommit_osv",
        type=str,
        help="The jsonl file to retrieve the seccommit_osv dataset",
        default="our_sec_cleaned.jsonl",
    )

    args = parser.parse_args()

    # dataset = PrimeVul()  # Create an instance of PrimeVul
    # download_dataset(dataset, args.directory)
    # treat_dataset(args.directory)

    # treat_asleep_dataset(args.directory)

    # treat_security_eval_dataset(args.directory)

    treat_seccomit_osv_dataset(args.seccommit_osv, args.directory)

    logger.info("Dataset downloaded and treated.", directory=args.directory)
