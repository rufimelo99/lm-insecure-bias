from typing import Tuple
import os
import logging
import csv

from dataset_loader.dataset_loader import DatasetLoader
from data_structures.answer import Answer
from data_structures.prompt_store import PromptsStore
from utils.llm_vul_utils import *
from utils.framework_utils import print_progress_bar
from model_loader.model_loader import ModelLoader


class LlmVulLoader(DatasetLoader):
    """
    Class for loading and testing the dataset llm-vul.

    Attributes:
        name (str): The name of the dataset.
        area (str): The area of the dataset.

    Methods:
        __init__: Initialize the HumanEvalLoader.
        load_prompts: Load prompts for llm-vul dataset.
        test_code: Test the provided answer.
    """

    def __init__(self) -> None:
        """
        Initialize the llmvulLoader.
        """
        super().__init__()
        self.name = "llm-vul"
        self.area = "APR"

    def load_prompts(self) -> None:
        """
        Load prompts for llm-vul dataset.
        """
        print(f"Loading {self.name} prompts...")
        prompts = PromptsStore(self.area)

        java_directory = os.path.join(LLM_VUL_DIR, "VJBench-trans")
        entries = os.listdir(java_directory)
        java_dir_list = [
            entry
            for entry in entries
            if os.path.isdir(os.path.join(java_directory, entry))
        ]

        for i, dir in enumerate(java_dir_list):
            dir = os.path.join(java_directory, dir)
            if i == 1000:
                break
            for file_name in os.listdir(dir):
                if file_name.endswith("transformation.java") or file_name.endswith(
                    "original_method.java"
                ):
                    try:
                        trans = file_name.split("_")[1]
                        with open(
                            os.path.join(dir, "buggyline_location.json"), "r"
                        ) as f:
                            buggyline_data = json.load(f)

                        if trans == "full":
                            trans = "rename+code_structure"
                        bug_start = buggyline_data[f"{trans}"][0][0]
                        bug_end = buggyline_data[f"{trans}"][0][1]

                        file_path_full = os.path.join(dir, file_name)
                        if os.path.isfile(file_path_full):
                            # Read the content of each Java file and create prompts
                            with open(file_path_full, "r") as file:
                                file_data = file.read().strip()

                            prompts.add_instruct(file_name, file_data, "Java")

                            # Split the Java file content into lines
                            lines = file_data.split("\n")

                            # Create a new list containing lines up to that index, otherwise containing all lines
                            prefix_lines = (
                                lines[: bug_start - 1]
                                if bug_start is not None
                                else lines
                            )
                            suffix_lines = lines[bug_end:]
                            prefix = "\n".join(prefix_lines)
                            suffix = "\n".join(suffix_lines)

                            prompts.add_completion(file_name, prefix)
                            prompts.add_infilling(file_name, prefix, suffix)
                        else:
                            print(f"'{file_path_full}' is not a file.")
                    except Exception as e:
                        print(f"Error reading file '{file_name}': {str(e)}")

        print(f"{self.name} prompts loaded\n")
        self.prompts = prompts

    def test_code(self, answers: list[Answer], model: ModelLoader) -> None:
        """
        Test the provided answer.

        Args:
            answer (Answer): Answer object.
            model  (ModelLoader): Model that created the answer.
        Returns:
            None
        """
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        print_progress_bar(0, len(answers))
        for i, answer in enumerate(answers, start=1):
            try:
                vul_id = answer.id.split("_")[0]
                trans = answer.id.split("_")[1]
                if vul_id.startswith("VUL"):
                    vul_raw_id = vul_id
                elif isinstance(vul_id, str):
                    vul_raw_id = f"VUL4J-{cve_name_to_int[vul_id]}"
                else:
                    print(f"{vul_id} is Not a valid Bug ID")
                    return

                if trans == "full":
                    trans = "rename+code_structure"

                with open(info_json, "r") as f:
                    all_info_list = json.load(f)

                for info in all_info_list:
                    if info["vul_id"] == vul_raw_id:

                        is_vul4j = vul_id.startswith("VUL")
                        buggy_file_path = info["buggy_file"]

                        buggy_method_start = info["buggy_method_with_comment"][0][0]
                        buggy_method_end = info["buggy_method_with_comment"][0][1]

                        if is_vul4j:
                            project_path = os.path.join(VUL4J_DIR, vul_id)
                            compile_cmd = f"vul4j compile -d {project_path}"
                            test_cmd = f"vul4j test -d {project_path}"
                        else:
                            project_path = os.path.join(VJBENCH_DIR, vul_id)
                            with open(vjbench_json, "r") as f:
                                vjbench_info = json.load(f)
                            compile_cmd = vjbench_info[vul_id]["compile_cmd"]
                            test_cmd = vjbench_info[vul_id]["test_cmd"]
                            b_path = vjbench_info[vul_id]["buggy_file_path"]
                            restore_cmd = f"git checkout HEAD {b_path}"
                            p = subprocess.Popen(
                                restore_cmd.split(),
                                cwd=project_path,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                            )
                            p.wait()

                        buggy_file_path = os.path.join(project_path, buggy_file_path)

                        with open(buggy_file_path, "r") as f:
                            lines = f.readlines()

                        generated_code = answer.code

                        if trans != "original" and trans != "structure_change_only":
                            generated_code = translate_code(generated_code, vul_id)

                        with open(buggy_file_path, "w") as f:
                            f.writelines(lines[: buggy_method_start - 1])
                            f.write(generated_code)
                            f.writelines(lines[buggy_method_end:])

                        res = 0
                        vjbench_res = 0

                        if is_vul4j:
                            succ = vul4j_compile_java_file(project_path, compile_cmd)
                        else:
                            succ = cve_compile_java_file(project_path, compile_cmd)

                        if succ:
                            if is_vul4j:
                                res = vul4j_test_java_file(project_path, test_cmd)
                                if res == 2:
                                    answer.other_error = True
                                    answer.error_message = "test_timeout"
                                    answer.failed = 1
                                    continue
                                testlog_file = os.path.join(
                                    VUL4J_DIR, vul_id, "VUL4J", "testing_results.json"
                                )
                                with open(testlog_file, "r") as file:
                                    result_data = json.load(file)

                            else:
                                vjbench_res = cve_test_java_file(project_path, test_cmd)

                                if vjbench_res == 2:
                                    answer.other_error = True
                                    answer.error_message = "test_timeout"
                                    answer.failed = 1
                                    continue

                                if test_cmd.startswith("./gradle"):
                                    result_data = read_test_results_gradle(
                                        vul_id, project_path
                                    )
                                else:
                                    result_data = read_test_results_maven(
                                        vul_id, project_path
                                    )

                            answer.passed = result_data["tests"]["overall_metrics"][
                                "number_passing"
                            ]
                            answer.failed = result_data["tests"]["overall_metrics"][
                                "number_failing"
                            ]

                        else:
                            answer.error_message = "compile failed"
                            answer.other_error = True

                        with open(buggy_file_path, "w") as f:
                            f.writelines(lines)

                print_progress_bar(i, len(answers))
            except Exception as e:
                print(e)
