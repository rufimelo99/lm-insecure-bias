import urllib
from dataclasses import dataclass
from datetime import datetime

import duckdb

from sec_aware_cl.schemas import MODEL_INFO

text = (
    """\
![](https://huggingface.co/spaces/lvwerra/in-the-stack-gr/resolve/main/banner.png)
**_The Stack is an open governance interface between the AI community and the open source community._**
# Am I in The Stack?
As part of the BigCode project, we released and maintain [The Stack V2](https://huggingface.co/datasets/bigcode/the-stack-v2), a 67 TB dataset of source code over 600 programming languages. One of our goals in this project is to give people agency over their source code by letting them decide whether or not it should be used to develop and evaluate machine learning models, as we acknowledge that not all developers may wish to have their data used for that purpose.
"""
    + """\
This tool lets you check if a repository under a given username is part of The Stack dataset. Would you like to have your data removed from future versions of The Stack? You can opt-out following the instructions [here](https://www.bigcode-project.org/docs/about/the-stack/#how-can-i-request-that-my-data-be-removed-from-the-stack). Note that previous opt-outs might still be displayed in the release candidate (denoted with "-rc"), which will be removed for the release.
**Note:** The Stack v2.0 is built from public GitHub code provided by the [Software Heriage Archive](https://archive.softwareheritage.org/). It may include repositories that are no longer present on GitHub but were archived by Software Heritage. Before training the StarCoder 1 and 2 models an additional PII pipeline was run to remove names, emails, passwords and API keys from the code files. For more information see the [paper](https://arxiv.org/abs/2402.19173).
**Data source**:\
<img src="https://annex.softwareheritage.org/public/logo/software-heritage-logo-title.2048px.png" alt="Logo" style="height: 3em; vertical-align: middle;" />
**Model training**:\
- StarCoder1 was trained on repos listed in `v1.2`.
- StarCoder2 was trained on repos listed in `v2.0.1`.
"""
)
opt_out_text_template = """\
### Opt-out
If you want your data to be removed from the stack and model training \
open an issue with <a href="https://github.com/bigcode-project/opt-out-v2/issues/new?title={title}&body={body}" target="_blank">this link</a> \
(if the link doesn't work try right a right click and open it in a new tab) or visit [https://github.com/bigcode-project/opt-out-v2/issues/new?&template=opt-out-request.md](https://github.com/bigcode-project/opt-out-v2/issues/new?&template=opt-out-request.md) .\
"""

opt_out_issue_title = """Opt-out request for {username}"""
opt_out_issue_body = """\
I request that the following data is removed from The Stack and StackOverflow:
 - Commits
 - GitHub issue
 - StackOverflow: <INSERT_STACKOVERFLOW_USERNAME_HERE>
{repo_list}
_Note_: If you don't want all resources to be included just remove the elements from the list above. If you would like to exclude all repositories and resources just add a single element "all" to the list.
"""


def issue_url(username, repos):
    title = urllib.parse.quote(opt_out_issue_title.format(username=username))
    body = urllib.parse.quote(
        opt_out_issue_body.format(repo_list=" - " + "\n - ".join(repos))
    )

    opt_out_text = opt_out_text_template.format(title=title, body=body)

    return opt_out_text


def check_username(username, version, db=None):
    username = username.lower()
    output_md = ""
    repos = db.sql(
        f"SELECT repo FROM repos WHERE user='{username}' AND version='{version}' ORDER BY repo"
    ).fetchall()
    repos = [repo[0] for repo in repos]

    if repos:
        repo_word = "repository" if len(repos) == 1 else "repositories"
        if version[:2] == "v2":
            output_md += f"**Yes**, there is code from **{len(repos)} {repo_word}** in The Stack. Check the links to see when it was archived by Software Heritage:\n\n"
        else:
            output_md += f"**Yes**, there is code from **{len(repos)} {repo_word}** in The Stack:\n\n"
        for repo in repos:
            if version[:2] == "v2":
                output_md += f"[{repo}](https://archive.softwareheritage.org/browse/origin/visits/?origin_url=https://github.com/{repo})\n\n"
            else:
                output_md += f"_{repo}_\n\n"

        return output_md.strip(), issue_url(username, repos)
    else:
        output_md += "**No**, your code is not in The Stack."
        return output_md.strip(), ""


def access_db(path="repos.duckdb"):
    db = duckdb.connect(path)
    return db


def check_all_info(username, version, db):
    username = username.lower()
    output_md = ""
    repos = db.sql(
        f"SELECT * FROM repos WHERE user='{username}' AND version='{version}' ORDER BY repo"
    ).fetchall()
    repos = [repo[0] for repo in repos]

    if repos:
        repo_word = "repository" if len(repos) == 1 else "repositories"
        if version[:2] == "v2":
            output_md += f"**Yes**, there is code from **{len(repos)} {repo_word}** in The Stack. Check the links to see when it was archived by Software Heritage:\n\n"
        else:
            output_md += f"**Yes**, there is code from **{len(repos)} {repo_word}** in The Stack:\n\n"
        for repo in repos:
            if version[:2] == "v2":
                output_md += f"[{repo}](https://archive.softwareheritage.org/browse/origin/visits/?origin_url=https://github.com/{repo})\n\n"
            else:
                output_md += f"_{repo}_\n\n"

        return output_md.strip(), issue_url(username, repos)
    else:
        output_md += "**No**, your code is not in The Stack."
        return output_md.strip(), ""


def find_repo(repo, version="v2.1.0", db=None):
    username = repo.split("/")[0]

    repo = "[" + repo + "]"

    md, _ = check_username(username, version, db)

    lines = md.splitlines()
    # print(lines[0])

    # repos
    repos = [x for x in md.splitlines() if x.startswith("[") and x.endswith(")")]
    print(len(repos), "repos")

    seen = False
    for r in repos:
        if repo in r:
            seen = True
            print("Found it!")
            break

    return seen


@dataclass
class Version:
    version: str
    date: datetime

    def __str__(self):
        return f"Version {self.version} ({self.date})"


VERSIONS = [
    Version("v1.0", datetime(2022, 3, 21)),
    Version("v1.1", datetime(2022, 11, 15)),
    Version("v1.2", datetime(2023, 2, 9)),
    Version("v2.0", datetime(2023, 9, 14)),
    Version("v2.0.1", datetime(2023, 10, 20)),
    Version("v2.1.0", datetime(2024, 4, 9)),
]


def find_last_suitable_version(date):

    sorted_versions = sorted(VERSIONS, key=lambda x: x.date)
    last_version = None
    for version in sorted_versions:
        if version.date > date:
            break
        last_version = version

    if last_version is None:
        raise ValueError("No suitable version found. Model likely is too old.")
    return last_version


def check_stack_membership(snippet, model, is_patch, db_path="repos.duckdb"):
    """
    Check if a snippet is in the stack.
    """
    vulnerable_version = is_patch

    stack_version = find_last_suitable_version(MODEL_INFO[model])
    commit_date = datetime.strptime(snippet["published_date"], "%Y-%m-%d")

    href = snippet["commit_href"]

    # get the repo name from the href
    repo = href.split("/")[3] + "/" + href.split("/")[4]

    db = access_db(db_path)
    in_repo = find_repo(repo, stack_version.version, db=db)

    # check if the commit date is before the stack version
    # if commit_date < stack_version.date:
    #     if not vulnerable_version:
    #         is_stack_member = in_repo
    #     else:
    #         is_stack_member = False
    # else:
    #     if vulnerable_version:
    #         is_stack_member = in_repo
    #     else:
    #         is_stack_member = False
    is_stack_member = in_repo
    print(
        f"Commit date after stack version: {commit_date > stack_version.date}; Vulnerable version: {vulnerable_version}; Is stack member: {is_stack_member}; In repo: {in_repo}"
    )
    return is_stack_member
