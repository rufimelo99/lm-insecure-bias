from typing import Tuple
import os
import copy
import logging
import re
import subprocess

from dataset_loader.dataset_loader import DatasetLoader
from data_structures.answer import Answer
from data_structures.prompt_store import PromptsStore
from utils.framework_utils import print_progress_bar
from model_loader.model_loader import ModelLoader


class QuixBugsJavaLoader(DatasetLoader):
    """
    Class for loading and testing the QuixBugs Java dataset.
    """

    def __init__(self) -> None:
        """
        Initializes the QuixBugsJavaLoader.
        """
        super().__init__()
        self.name = "QuixBugs Java"
        self.area = "APR"

    def load_prompts(self) -> None:
        """
        Loads prompts for the QuixBugs Java dataset.
        """
        print(f"Loading {self.name} prompts...")
        prompts = PromptsStore(self.area)

        # Get all Java files in QuixBugs director
        java_directory = "./datasets/APR/QuixBugs/java_programs_bug"
        java_file_list = os.listdir(java_directory)

        for i, file_name in enumerate(java_file_list):
            if i == 1000:
                break
            try:
                file_path_full = os.path.join(java_directory, file_name)
                if os.path.isfile(file_path_full):
                    # Read the content of each Java file and create prompts
                    with open(file_path_full, "r") as file:
                        file_data = file.read().strip()

                    prompts.add_instruct(file_name, file_data, "Java")

                    # Split the Java file content into lines
                    lines = file_data.split("\n")

                    count = 0
                    second_index = None

                    for i, line in enumerate(lines):
                        if "{" in line:
                            count += 1
                            if count == 2:
                                second_index = i
                                break
                    # Create a new list containing lines up to that index, otherwise containing all lines
                    result_lines = (
                        lines[: second_index + 1] if second_index is not None else lines
                    )
                    prefix = "\n".join(result_lines)

                    prompts.add_completion(file_name, prefix)

                    last_lines = "\n".join(lines[len(lines) - 3 :])
                    prompts.add_infilling(file_name, prefix, last_lines)
                else:
                    logging.error(f"'{file_path_full}' is not a file.")
            except Exception as e:
                logging.error(f"Error reading file '{file_name}': {str(e)}")

        print(f"{self.name} prompts loaded\n")
        self.prompts = prompts

    def run_gradle_test(self, class_name: str) -> Tuple[int, int, bool]:
        """
        Runs Gradle tests for a specified Java class.

        Args:
            class_name (str): The name of the Java class to run tests for.

        Returns:
            Tuple[int, int, bool]: A tuple containing the number of passed tests, the number of failed tests and if a syntax error occured.
        """
        original_dir = os.getcwd()
        quixbugs_dir = "./datasets/APR/QuixBugs/"
        failed_tests = 0
        passed_tests = 0

        try:
            if "QuixBugs" not in os.getcwd():
                os.chdir(quixbugs_dir)
            else:
                logging.error(f"Current working directory {os.getcwd()}")

            # Run Gradle test command and capture the output
            gradle_command = f"gradle test --tests {class_name}_TEST"

            timeout = 60
            if class_name == "KNAPSACK" or class_name == "LEVENSHTEIN":
                # KNAPSACK and LEVEHSHTEIN might need a long time to finish
                timeout = 300

            result = subprocess.run(
                gradle_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            os.chdir(original_dir)
            if result:
                output_content = result.stdout + result.stderr

                # Use regular expression to find lines containing test results
                pattern = re.compile(r"(\d+) tests completed, (\d+) failed")
                match = pattern.search(output_content)
                pattern2 = re.compile(r"BUILD SUCCESSFUL")
                match2 = pattern2.search(output_content)

                if match:
                    tests_completed = int(match.group(1))
                    failed_tests = int(match.group(2))
                    passed_tests = tests_completed - failed_tests

                elif match2:
                    # If the second pattern is found, open the corresponding JSON file
                    json_file_path = f"./datasets/APR/QuixBugs/json_testcases/{class_name.lower()}.json"
                    if os.path.exists(json_file_path):
                        with open(json_file_path, "r") as json_file:
                            # Read the number of lines in the JSON file thats not empty
                            passed_tests = sum(1 for line in json_file if line.strip())
                    else:
                        test_file_path = f"./datasets/APR/QuixBugs/java_testcases/junit/{class_name}_TEST.java"
                        with open(test_file_path, "r") as file:
                            java_code = file.read()

                        # Get the number of @Test in test code
                        test_instances = re.findall(r"@Test", java_code)
                        passed_tests = len(test_instances)
                else:
                    return 0, 0, True
        except subprocess.TimeoutExpired:
            subprocess.run(["pkill", "-f", gradle_command])
        except Exception as e:
            # Handle any other unexpected exceptions
            logging.error(e)
            subprocess.run(["pkill", "-f", gradle_command])

        os.chdir(original_dir)
        return passed_tests, failed_tests, False

    def test_code(self, answers: list[Answer], model: ModelLoader) -> None:
        """
        Tests the provided answer.

        Args:
            answer (Answer): Answer object.
            model  (ModelLoader): Model that created the answer.
        """
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        dynamic_directory = "./datasets/APR/QuixBugs/java_programs"
        print_progress_bar(0, len(answers))

        for i, answer in enumerate(answers, start=1):
            try:
                dynamic_file_path = os.path.join(
                    dynamic_directory, answer.id.replace(".txt", ".java")
                )

                with open(dynamic_file_path, "w") as file:
                    file.write(answer.code)

                if answer.code != "":
                    answer.syntax_error, answer.error_message = check_java_syntax(
                        dynamic_file_path
                    )
                else:
                    answer.other_error = True
                    answer.error_message = "Empty file, could not extract any code"

                if answer.syntax_error != True and answer.other_error != True:
                    class_name = answer.id.split(".")[0]
                    answer.passed, answer.failed, answer.syntax_error = (
                        self.run_gradle_test(class_name)
                    )

                before = ""
                file_path = os.path.join(
                    "./datasets/APR/QuixBugs/java_programs_bug", answer.id
                )

                # Overwrite to original state, if this is not done is could introduce errors for other answers.
                with open(file_path, "r") as file:
                    before = file.read()

                with open(dynamic_file_path, "w") as file:
                    file.write(before)

            except Exception as e:
                print(f"An unexpected error occurred: {e}")

            print_progress_bar(i, len(answers))


def check_java_syntax(file_path: str) -> Tuple[bool, str]:
    """
    Check Java syntax errors in code.

    Args:
        file_path (str): The location of the java code.
    Returns:
        Tuple[bool, str]: Tuple indicating whether a syntax error occurred (bool) and the corresponding error message (str).
    """
    error_message = ""
    syntax_error = False
    file_name = [
        "SHORTEST_PATH_LENGTH.java",
        "SHORTEST_PATHS.java",
        "BREADTH_FIRST_SEARCH.java",
        "TOPOLOGICAL_ORDERING.java",
        "DETECT_CYCLE.java",
        "MINIMUM_SPANNING_TREE.java",
        "REVERSE_LINKED_LIST.java",
        "DEPTH_FIRST_SEARCH.java",
    ]

    try:
        if file_path is not None:
            if os.path.basename(file_path) in file_name:
                command = [
                    "javac",
                    file_path,
                    "./datasets/APR/QuixBugs/java_programs/Node.java",
                    "./datasets/APR/QuixBugs/java_programs/WeightedEdge.java",
                ]
                # Use subprocess to invoke the Java compiler directly on the file
                result = subprocess.run(
                    command, check=True, stderr=subprocess.PIPE, text=True
                )
            else:
                result = subprocess.run(
                    ["javac", file_path],
                    check=True,
                    stderr=subprocess.PIPE,
                    text=True,
                )
        else:
            syntax_error = True

    except subprocess.CalledProcessError as e:
        syntax_error = True
        error_message = "JavaSyntaxError:\n"

        # Check if stderr is not None before decoding
        if e.stderr is not None:
            error_message += e.stderr
        else:
            error_message += "No stderr output available."
    return syntax_error, error_message
