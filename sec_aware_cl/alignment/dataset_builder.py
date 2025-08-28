import argparse
import json
import os

import pandas as pd

from sec_aware_cl.logger import logger


def write_jsonl(data: json, file_path, append=False):
    mode = "a" if append else "w"

    if not os.path.exists(file_path):
        mode = "w"

    with open(file_path, mode) as f:
        f.write(json.dumps(data) + "\n")


def treat_seccomit_osv_dataset(
    file_path: str,
    directory: str,
):
    # {"vuln_id": "GHSA-2363-cqg2-863c", "cwe_id": "{'CWE-611'}", "score": 7.5, "chain": "{'https://github.com/hunterhacker/jdom/commit/dd4f3c2fc7893edd914954c73eb577f925a7d361'}", "dataset": "osv", "summary": "XML External Entity (XXE) Injection in JDOM An XXE issue in SAXBuilder in JDOM through 2.0.6 allows attackers to cause a denial of service via a crafted HTTP request.  At this time there is not released fixed version of JDOM.  As a workaround, to avoid external entities being expanded, one can call `builder.setExpandEntities(false)` and they won't be expanded.", "published_date": "2021-07-27", "chain_len": 1, "project": "https://github.com/hunterhacker/jdom", "commit_href": "https://github.com/hunterhacker/jdom/commit/dd4f3c2fc7893edd914954c73eb577f925a7d361", "commit_sha": "dd4f3c2fc7893edd914954c73eb577f925a7d361", "patch": "SINGLE", "chain_ord": "['dd4f3c2fc7893edd914954c73eb577f925a7d361']", "before_first_fix_commit": "{'1f81562b5cc813bfbacb7e2842b5be17eb34896b'}", "last_fix_commit": "dd4f3c2fc7893edd914954c73eb577f925a7d361", "chain_ord_pos": 1, "commit_datetime": "07/02/2021, 03:42:05", "message": "Addresses #189 - synchronizes external entity expansion setting", "author": "Rolf Lear", "comments": null, "stats": "{'additions': 6, 'deletions': 0, 'total': 6}", "files": {"core/src/java/org/jdom2/input/SAXBuilder.java": {"additions": 6, "deletions": 0, "changes": 6, "status": "modified", "raw_url": "https://github.com/hunterhacker/jdom/raw/dd4f3c2fc7893edd914954c73eb577f925a7d361/core%2Fsrc%2Fjava%2Forg%2Fjdom2%2Finput%2FSAXBuilder.java", "patch": "@@ -82,6 +82,7 @@ OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT\n import org.jdom2.DocType;\n import org.jdom2.Document;\n import org.jdom2.EntityRef;\n+import org.jdom2.JDOMConstants;\n import org.jdom2.JDOMException;\n import org.jdom2.JDOMFactory;\n import org.jdom2.Verifier;\n@@ -797,6 +798,11 @@ public void setFastReconfigure(final boolean fastReconfigure) {\n \tpublic void setFeature(final String name, final boolean value) {\n \t\t// Save the specified feature for later.\n \t\tfeatures.put(name, value ? Boolean.TRUE : Boolean.FALSE);\n+\t\tif (JDOMConstants.SAX_FEATURE_EXTERNAL_ENT.equals(name)) {\n+\t\t\t// See issue https://github.com/hunterhacker/jdom/issues/189\n+\t\t\t// And PR https://github.com/hunterhacker/jdom/pull/188\n+\t\t\tsetExpandEntities(value);\n+\t\t}\n \t\tengine = null;\n \t}"}}, "prior_version": " OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT import org.jdom2.DocType; import org.jdom2.Document; import org.jdom2.EntityRef; import org.jdom2.JDOMException; import org.jdom2.JDOMFactory; import org.jdom2.Verifier; public void setFastReconfigure(final boolean fastReconfigure) { \tpublic void setFeature(final String name, final boolean value) { \t\t// Save the specified feature for later. \t\tfeatures.put(name, value ? Boolean.TRUE : Boolean.FALSE); \t\tengine = null; \t} ", "after_version": " OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT import org.jdom2.DocType; import org.jdom2.Document; import org.jdom2.EntityRef; import org.jdom2.JDOMConstants; import org.jdom2.JDOMException; import org.jdom2.JDOMFactory; import org.jdom2.Verifier; public void setFastReconfigure(final boolean fastReconfigure) { \tpublic void setFeature(final String name, final boolean value) { \t\t// Save the specified feature for later. \t\tfeatures.put(name, value ? Boolean.TRUE : Boolean.FALSE); \t\tif (JDOMConstants.SAX_FEATURE_EXTERNAL_ENT.equals(name)) { \t\t\t// See issue https://github.com/hunterhacker/jdom/issues/189 \t\t\t// And PR https://github.com/hunterhacker/jdom/pull/188 \t\t\tsetExpandEntities(value); \t\t} \t\tengine = null; \t} "}
    if not os.path.exists(directory):
        os.makedirs(directory)

    if not os.path.exists(os.path.join(directory, "data")):
        os.makedirs(os.path.join(directory, "data"))

    df = pd.read_json(os.path.join(file_path), lines=True)
    print(f"Initial shape: {df.shape}")
    counter = 0
    for index, row in df.iterrows():
        cwe = row["cwe"]
        if not cwe:
            logger.warning(f"Row with vuln_id {row['vuln_id']} has no cwe, skipping.")
            continue

        if (
            row["prior_version"]
            and len(row["prior_version"]) > 0
            and row["after_version"]
            and len(row["after_version"]) > 0
        ):

            stats = eval(row["stats"])
            data = {
                "cwe": [cwe],
                "rejected": row["prior_version"],
                "chosen": row["after_version"],
                "additions": stats["additions"],
                "deletions": stats["deletions"],
                "total": stats["total"],
                "vuln_id": row["vuln_id"],
                "score": row["score"],
                "published_date": row["published_date"],
                "commit_href": row["commit_href"],
            }
            write_jsonl(
                data,
                os.path.join(directory + "/" + "data", cwe + ".jsonl"),
                append=True,
            )
            counter += 1

    print(f"Total samples written: {counter}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create DPO dataset from SecCommits")

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

    treat_seccomit_osv_dataset(args.seccommit_osv, args.directory)

    logger.info("Dataset downloaded and treated.", directory=args.directory)
