import os
import subprocess
import shutil
from pathlib import Path
import re
import csv
import fileinput
import json

from utils.llm_vul_utils import (
    LLM_VUL_DIR,
    VJBENCH_DIR,
    VUL4J_DIR,
    SCRIPTS_DIR,
    vul4j_bug_id_list,
)

ROOT_DIR = Path(__file__).resolve().parent
FNULL = open(os.devnull, "w")


def install_dependencies() -> None:
    """Install dependencies from requirements.txt."""
    requirements_file = ROOT_DIR / "requirements.txt"
    print(f"Installing dependencies from {requirements_file}...")
    subprocess.run(["pip", "install", "-r", str(requirements_file)], check=True)


def clone_repository(repo_url: str, dir_name: str) -> None:
    """Clone a repository into the specified directory.

    Args:
        repo_url (str): The URL of the repository to clone.
        dir_name (str): The name of the destination directory.

    Raises:
        Exception: If an error occurs during cloning or directory removal.
    """
    destination_path = ROOT_DIR / dir_name

    if destination_path.exists():
        overwrite = input(
            f"Destination directory {destination_path} already exists. Do you want to overwrite? (y/n): "
        ).lower()
        if overwrite != "y":
            print("Skipping cloning.")
            return
        else:
            print(f"Overwriting existing directory at {destination_path}...")
            try:
                shutil.rmtree(destination_path)
                subprocess.run(
                    ["git", "clone", repo_url, str(destination_path)], check=True
                )
            except Exception as e:
                raise Exception(f"Error removing existing directory: {e}")
    else:
        clone = input(f"Do you want to clone repo {repo_url}? (y/n): ").lower()
        if clone == "y":
            print(f"Cloning repository from {repo_url} to {destination_path}...")
            subprocess.run(
                ["git", "clone", repo_url, str(destination_path)], check=True
            )
        else:
            print(f"Skipping downloading: {dir_name}")

    if os.path.exists(f"{destination_path}/git"):
        shutil.rmtree(f"{destination_path}/git")
        print(f"Deleted git directory: {destination_path}/git")


def prepare_llm_vul(path: str) -> None:
    """Prepare llm_vul directory by fetching all vulnerabilities studied in the project.

    Args:
        path (str): Path to the quixbugs repo.
    """
    if not os.path.exists(path):
        return

    with open(f"{ROOT_DIR}/config/config.json", "r") as file:
        tokens = json.load(file)

    studied_vuls = []
    util_path = os.path.join(SCRIPTS_DIR, "util.py")
    csv_file = os.path.join(LLM_VUL_DIR, "VJBench_dataset.csv")
    succ_vul_file = os.path.join(
        tokens["paths"]["VUL4J_ROOT"], "reproduction", "successful_vulns.txt"
    )

    with open(succ_vul_file, "r") as file:
        succ_vuls = file.read().splitlines()

    with fileinput.FileInput(util_path, inplace=True) as file:
        for i, line in enumerate(file, start=1):
            if i == 19:
                print(f'VUL4J_DIR = "{VUL4J_DIR}"')
            elif i == 21:
                print(f'VJBENCH_DIR = "{VJBENCH_DIR}"')
            else:
                print(line, end="")

    if os.path.exists(LLM_VUL_DIR):
        if not os.path.exists(VJBENCH_DIR):
            os.makedirs(VJBENCH_DIR)
        if not os.path.exists(VUL4J_DIR):
            os.makedirs(VUL4J_DIR)

    # Cleaup
    paths = [
        f"{LLM_VUL_DIR}/jasper",
        f"{LLM_VUL_DIR}/Model_patches",
        f"{SCRIPTS_DIR}/APR",
        f"{SCRIPTS_DIR}/CodeGen",
        f"{SCRIPTS_DIR}/CodeT5",
        f"{SCRIPTS_DIR}/Codex",
        f"{SCRIPTS_DIR}/fine-tuned_CodeGen",
        f"{SCRIPTS_DIR}/fine-tuned_CodeT5",
        f"{SCRIPTS_DIR}/fine-tuned_InCoder",
        f"{SCRIPTS_DIR}/fine-tuned_PLBART",
        f"{SCRIPTS_DIR}/InCoder",
        f"{SCRIPTS_DIR}/PLBART",
    ]

    for path in paths:
        if os.path.exists(path):
            shutil.rmtree(path)

    vul_dir = os.path.join(LLM_VUL_DIR, "VJBench-trans")
    entries = os.listdir(vul_dir)
    java_dir_list = [
        entry for entry in entries if os.path.isdir(os.path.join(vul_dir, entry))
    ]

    for dir in java_dir_list:
        if dir.startswith("VUL") and dir not in succ_vuls:
            dir = os.path.join(vul_dir, dir)
            shutil.rmtree(dir)

    with open(csv_file, "r") as file:
        csv_reader = csv.DictReader(file)

        for row in csv_reader:
            study_value = row["Used in the study"]

            if study_value == "Yes":
                studied_vuls.append(row["Vulnerability IDs"])

    print("Downloading VJBench vulnerabilities...")
    for vul in studied_vuls:
        cmd = [
            "python3",
            os.path.join(SCRIPTS_DIR, "build_vjbench.py"),
            "checkout",
            vul,
        ]
        proccess = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        outp = proccess.stdout

        print(f"Downloading vulnerability: {vul}...")

    print("Downloading VUL4J vulnerabilities...")
    for i in vul4j_bug_id_list:
        if f"VUL4J-{i}" in succ_vuls:
            print(f"Downloading vulnerability: VUL4J-{i}...")
            cmd = f"vul4j checkout --id VUL4J-{i} -d {VUL4J_DIR}/VUL4J-{i}"
            cmd = cmd.split()
            p3 = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            out3, err = p3.communicate()


def prepare_quixbugs_python(path: str) -> None:
    """Prepare QuixBugs directory by copying, renaming, and excluding specific files.

    Args:
        path (str): Path to the quixbugs repo.
    """
    if not os.path.exists(path):
        return

    original_path = f"{ROOT_DIR}/{path}/python_programs"
    new_path = f"{ROOT_DIR}/{path}/python_programs_bug"

    print(f"Copying and renaming directory from {original_path} to {new_path}...")
    shutil.copytree(original_path, new_path, dirs_exist_ok=True)
    files_to_exclude = [
        "node.py",
        "breadth_first_search_test.py",
        "depth_first_search_test.py",
        "detect_cycle_test.py",
        "minimum_spanning_tree_test.py",
        "reverse_linked_list_test.py",
        "shortest_path_lengths_test.py",
        "shortest_path_length_test.py",
        "shortest_paths_test.py",
        "topological_ordering_test.py",
    ]

    for file_name in files_to_exclude:
        file_path = f"{new_path}/{file_name}"
        try:
            os.remove(file_path)
            print(f"File {file_name} deleted successfully.")
        except Exception as e:
            raise Exception(f"Error deleting file {file_name}: {e}")

    for file in os.scandir(new_path):
        with open(file, "r") as f:
            content = f.read()
        # Regular expression patterns to match function and docstring
        function_pattern = r"def\s+\w+\s*\([^)]*\)\s*:"
        docstring_pattern = r'"""[^"]*"""'

        # Find function definition and its associated docstring
        function_match = re.search(function_pattern, content)
        docstring_match = re.search(docstring_pattern, content)

        if function_match and docstring_match:
            function_start = function_match.start()
            function_end = function_match.end()
            docstring_start = docstring_match.start()
            docstring_end = docstring_match.end()

            function_str = content[function_start:function_end]
            docstring_str = content[docstring_start:docstring_end]

            # Indent each line in the docstring
            indented_docstring = "\n" + "\n".join(
                ["    " + line.strip() for line in docstring_str.split("\n")]
            )

            # Rearrange content
            rearranged_content = (
                content[:function_start]
                + function_str
                + indented_docstring
                + content[function_end:docstring_start]
                + content[docstring_end:]
            )
            rearranged_content = rearranged_content.strip()

        # Write cleaned data back to file
        with open(file, "w") as f:
            f.write(rearranged_content)

    print("Python files cleaned successfully.")


def prepare_quixbugs_java(path: str) -> None:
    """Prepare QuixBugs directory by copying, renaming, and excluding specific files.

    Args:
        path (str): Path to the quixbugs repo.
    """

    if not os.path.exists(path):
        return

    original_path = f"{ROOT_DIR}/{path}/java_programs"
    new_folder_name = f"{path}/java_programs_bug"
    new_path = f"{ROOT_DIR}/{new_folder_name}"

    exclude_files = [
        "Node.java",
        "WeightedEdge.java",
        "Node.class",
        "WeightedEdge.class",
    ]

    try:
        # Create the destination directory if it doesn't exist
        os.makedirs(new_path, exist_ok=True)

        # Move .java files to the destination directory
        java_files = [
            os.path.join(original_path, filename)
            for filename in os.listdir(original_path)
            if filename.endswith(".java") and filename not in exclude_files
        ]
        for file in java_files:
            source_path = file
            destination_path = (
                f"{new_path}/{os.path.splitext(os.path.basename(source_path))[0]}.txt"
            )
            shutil.copy(source_path, destination_path)

        # Remove comments in java files
        for file in os.listdir(new_path):
            if file.endswith(".txt"):
                with open(f"{new_path}/{file}", "r") as f:
                    data = f.read()
                # Remove single-line comments
                cleaned_data = re.sub(r"//.*?\n", "\n", data)
                # Remove comments from the data
                cleaned_data = re.sub(r"/\*(.*?)\*/", "", cleaned_data, flags=re.DOTALL)
                # Reduce excessive newlines
                cleaned_data = re.sub(r"\n([ \t]*\n)+", "\n", cleaned_data)
                # cleaned_data = re.sub(r"(\n[ \t]*){3,}", "\n\n", cleaned_data)
                # Write cleaned data back to file
                with open(f"{new_path}/{file}", "w") as f:
                    f.write(cleaned_data)

    except Exception as e:
        raise Exception(f"An error occurred: {e}")


def prepare_human_eval_infilling(path: str):
    """Prepare human-eval-infilling repo by changing files and installing.

    Args:
        path (str): Path to the human-eval-infilling repo.
    """
    if not os.path.exists(path):
        return

    aware = input(
        "This program exists to execute untrusted model-generated code. Although it is highly unlikely that model-generated code will do something overtly malicious in response to this test suite, model-generated code may act destructively due to a lack of model capability or alignment. Users are strongly encouraged to sandbox this evaluation suite so that it does not perform destructive actions on their host or network. For more information on how OpenAI sandboxes its code, see the their paper. Once you have read this disclaimer, take the appropriate precautions. Are you aware of the risks? And want to install human-eval-infilling?(yes/no)"
    ).lower()

    if aware == "yes":
        with open(f"{path}/human_eval_infilling/execution.py", "r") as file:
            content = file.readlines()

        for i, line in enumerate(content):
            if line == "#                     exec(check_program, exec_globals)\n":
                content[i] = "                    exec(check_program, exec_globals)\n"

        with open(f"{path}/human_eval_infilling/execution.py", "w") as file:
            file.write("".join(content))
        os.system(f"cd {ROOT_DIR}/datasets/CG; pip install -e human-eval-infilling")


def prepare_vul4j(path: str):
    """Prepare vul4j repo by changing files and installing.

    Args:
        path (str): Path to the vul4j repo.
    """
    if not os.path.exists(path):
        return

    with open(f"{ROOT_DIR}/config/config.json", "r") as file:
        tokens = json.load(file)

    vul4j_root = tokens["paths"]["VUL4J_ROOT"]

    with open(f"{ROOT_DIR}/utils/vul4j_config.py", "r") as file:
        vul4j_config = file.read()

    vul4j_config = vul4j_config.replace("{VUL4J_ROOT}", tokens["paths"]["VUL4J_ROOT"])
    vul4j_config = vul4j_config.replace("{JAVA7_PATH}", tokens["paths"]["JAVA7_PATH"])
    vul4j_config = vul4j_config.replace("{JAVA8_PATH}", tokens["paths"]["JAVA8_PATH"])

    with open(f"{vul4j_root}vul4j/config.py", "w") as file:
        file.write(vul4j_config)

    with open(f"{ROOT_DIR}/utils/vul4j_main.py", "r") as file:
        vul4j_main = file.read()

    with open(f"{vul4j_root}vul4j/main.py", "w") as file:
        file.write(vul4j_main)

    os.system("cd ./datasets/APR/vul4j; python3 setup.py install")

def prepare_cyberseceval(path: str):
    """Prepare PurpleLlama repo by changing files and installing.

    Args:
        path (str): Path to the PurpleLlama repo.
    """
    if not os.path.exists(path):
        return
    
    source_file = os.path.join(ROOT_DIR, "utils", "cyberseceval_llm_py_changes.py")
    dest_file = os.path.join(ROOT_DIR, path, "CybersecurityBenchmarks", "benchmark", "llm.py")

    try:
        with open(source_file, 'r') as source:
            data = source.read()
        
        with open(dest_file, 'w') as dest:
            dest.write(data)
        
        print("llm.py successfully updated.")
    
    except FileNotFoundError:
        print("One of the files doesn't exist.")


if __name__ == "__main__":
    # Dataset Repository URL
    quixbugs_url = "https://github.com/jkoppel/QuixBugs"
    human_infilling = "https://github.com/openai/human-eval-infilling"
    vul4j = "https://github.com/tuhh-softsec/vul4j"
    llmvul_url = "https://github.com/lin-tan/llm-vul"
    purple_llama = "https://github.com/meta-llama/PurpleLlama.git"

    # Clone Datasets
    clone_repository(quixbugs_url, "datasets/APR/QuixBugs")
    clone_repository(human_infilling, "datasets/CG/human-eval-infilling")
    clone_repository(vul4j, "datasets/APR/vul4j")
    clone_repository(llmvul_url, "datasets/APR/llm_vul")
    
    # Clone Purple Llama
    clone_repository(purple_llama, "datasets/suites/PurpleLlama")

    # Make changes to Dataset Folder
    prepare_quixbugs_python("datasets/APR/QuixBugs")
    prepare_quixbugs_java("datasets/APR/QuixBugs")
    prepare_human_eval_infilling("datasets/CG/human-eval-infilling")
    prepare_vul4j("datasets/APR/vul4j")
    prepare_llm_vul("datasets/APR/llm_vul")
    prepare_cyberseceval("datasets/suites/PurpleLlama")

    print("Setup completed successfully.")
