import os
import subprocess
import json
import csv
import shutil

from dataset_loader.dataset_loader import DatasetLoader
from data_structures.answer import Answer
from data_structures.prompt_store import PromptsStore
from datasets import load_dataset
from utils.framework_utils import print_progress_bar, ROOT_PATH
from model_loader.model_loader import ModelLoader


with open(os.path.join(ROOT_PATH, "config/config.json"), "r") as f:
    CODEQL_PATH = json.load(f)["paths"]["CODEQL_PATH"]


class SecurityEvalLoader(DatasetLoader):
    """
    Class for loading and testing the dataset SecurityEval.

    Attributes:
        name (str): The name of the dataset.
        area (str): The area of the dataset.

    Methods:
        __init__: Initialize the SecurityEvalLoader.
        load_prompts: Load prompts for SecurityEval dataset.
        test_code: Test the provided answer.
    """

    def __init__(self) -> None:
        """
        Initialize the SecurityEvalLoader.
        """
        super().__init__()
        self.name = "SecurityEval"
        self.area = "CodeGen"

    def load_prompts(self) -> None:
        """
        Load prompts for SecurityEval dataset.
        """
        print(f"Loading {self.name} prompts...")
        prompts = PromptsStore(self.area)

        # Fetch all problems from SecurityEval
        dataset = load_dataset("s2e-lab/SecurityEval")
        data = dataset["train"]

        for i, item in enumerate(data):
            if i == 1000:
                break
            prompts.add_instruct(item["ID"], item["Prompt"], "Python")

        print(f"{self.name} prompts loaded.\n")
        self.prompts = prompts

    def test_code(self, answers: list[Answer], model: ModelLoader) -> None:
        """
        Test the provided answers.

        Args:
            answers (Answer): Answer object.
            model  (ModelLoader): Model that created the answer.
        Returns:
            Return dict of stats of cwe
        """
        seceval_dir = os.path.join(ROOT_PATH, "datasets", "CG", "security_eval")
        model_dir = os.path.join(seceval_dir, "Testcases" + "_" + model.name)
        db_dir = os.path.join(
            seceval_dir, "Databases", "Testcases" + "_" + model.name + "_" + "DB"
        )
        db_dir = os.path.join(
            seceval_dir, "Databases", "Testcases" + "_" + model.name + "_" + "DB"
        )
        results_dir = os.path.join(seceval_dir, "results")

        codeql_ver_path = os.path.join(
            CODEQL_PATH, "qlpacks", "codeql", "python-queries"
        )
        codeql_ver = os.listdir(codeql_ver_path)

        codeql_cwe_directory = os.path.join(
            codeql_ver_path,
            codeql_ver[0],
            "Security",
        )
        codeql_cwe = os.listdir(codeql_cwe_directory)

        if not os.path.exists(seceval_dir):
            os.makedirs(seceval_dir)
            os.makedirs(results_dir)
            os.makedirs(db_dir)

        if not os.path.exists(model_dir):
            os.makedirs(model_dir)

        # Clean all previous answers
        for i, answer in enumerate(answers):
            cwe_id = answer.id.split("_")[0]
            cwe_path = os.path.join(model_dir, cwe_id)
            if os.path.exists(cwe_path):
                shutil.rmtree(cwe_path)

        # Write all answers to a file
        for i, answer in enumerate(answers):
            cwe_id = answer.id.split("_")[0]
            source_id = answer.id.split("_")[1]
            serial_id = answer.id.split("_")[2].split(".")[0]

            cwe_path = os.path.join(model_dir, cwe_id)
            if answers[i].id == answers[i - 1].id and i > 0:
                file_path = os.path.join(
                    cwe_path, source_id + "_" + serial_id + f"_{i}" + ".py"
                )
            if answers[i].id == answers[i - 1].id and i > 0:
                file_path = os.path.join(
                    cwe_path, source_id + "_" + serial_id + f"_{i}" + ".py"
                )
            else:
                file_path = os.path.join(cwe_path, source_id + "_" + serial_id + ".py")
            if not os.path.exists(cwe_path):
                os.makedirs(cwe_path)

            with open(file_path, "w") as file:
                file.write(answer.code)

        # Remove database if it already exists
        if os.path.exists(db_dir):
            shutil.rmtree(db_dir)

        # Create database from answers
        print("\n Creating database for testing...")
        cmd = f"export PATH={CODEQL_PATH}:$PATH && cd {model_dir} && codeql database create --language=python '{db_dir}'"
        res = subprocess.run(cmd, shell=True)

        # Testing Bandit
        print("\n Testing answers with Bandit...")
        cmd = f"bandit -r {model_dir} -f json -o {results_dir}/testcases_{model.name}.json"
        res = subprocess.run(cmd, shell=True)
        print("\nDone!")

        # Testing CodeQL
        print("\n Testing answers with CodeQL...")
        codeql_res_path = os.path.join(results_dir, f"testcases_{model.name}")
        if not os.path.exists(codeql_res_path):
            os.makedirs(codeql_res_path)
        print_progress_bar(0, len(codeql_cwe))
        for i, cwe in enumerate(codeql_cwe, start=1):
            cwe_res_path = os.path.join(codeql_res_path, f"results_{cwe}.csv")
            cmd = f"export PATH={CODEQL_PATH}:$PATH && cd {seceval_dir}/Databases && codeql database analyze '{db_dir}' {codeql_cwe_directory}/{cwe} --format=csv --output='{cwe_res_path}'"
            res = subprocess.run(
                cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            res = subprocess.run(
                cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            print_progress_bar(i, len(codeql_cwe))
        print("\nDone!")

        # Retrieve results
        print("\n Retrieving results...")

        with open(f"{results_dir}/testcases_{model.name}.json", "r") as file:
            bandit_data = json.load(file)

        amount_of_cwe = 0

        for i, answer in enumerate(answers):
            cwe_id = answer.id.split("_")[0]
            source_id = answer.id.split("_")[1]
            serial_id = answer.id.split("_")[2].split(".")[0]
            if answers[i].id == answers[i - 1].id and i > 0:
                file_name = source_id + "_" + serial_id + f"_{i}" + ".py"
            else:
                file_name = source_id + "_" + serial_id + ".py"
            cwe_path = os.path.join(model_dir, cwe_id)
            file_cwe = cwe_path.split("/")[-1]
            file_cwe = cwe_path.split("/")[-1]
            file_path = os.path.join(cwe_path, file_name)

            for result in bandit_data["results"]:
                if result["filename"] == file_path:
                    if result["issue_confidence"] == "HIGH":
                        cwe_nr = result["issue_cwe"]["id"]
                        if cwe_nr < 100:
                            cwe = "CWE-0" + f"{cwe_nr}"
                        else:
                            cwe = "CWE-" + f"{cwe_nr}"
                        if cwe not in answer.error_message:
                            answer.error_message += ", " + cwe
                            answer.failed = 1
                            amount_of_cwe += 1

            for cwe in codeql_cwe:
                if not cwe == "CWE-020-ExternalAPIs":
                    cwe_res_path = os.path.join(
                        results_dir, f"testcases_{model.name}", f"results_{cwe}.csv"
                    )
                    cwe_res_path = os.path.join(
                        results_dir, f"testcases_{model.name}", f"results_{cwe}.csv"
                    )
                    with open(cwe_res_path, "r") as file:
                        cwe_res = csv.reader(file)
                        for row in cwe_res:
                            if len(row) >= 5:
                                filename_with_path = row[4]
                                if (
                                    filename_with_path
                                    == "/" + file_cwe + "/" + file_name
                                ):
                                    if cwe not in answer.error_message:
                                        answer.error_message += ", " + cwe
                                        answer.failed = 1
                                        amount_of_cwe += 1

            if answer.failed == 0:
                answer.passed = 1
            answer.error_message = answer.error_message.strip(",").strip()
        print("\nDone!")

        atleast_one = sum([answer.failed for answer in answers])

        return {
            "Amount of cwe": amount_of_cwe,
            "Amount of respones with atleast one cwe": atleast_one,
            "Successful rate(%)": round(
                ((len(answers) - atleast_one) / len(answers)) * 100, 1
            ),
            "Unsuccessful rate(%)": round((atleast_one / len(answers)) * 100, 1),
        }
