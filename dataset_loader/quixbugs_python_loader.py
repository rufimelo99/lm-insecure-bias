import os
import logging
import subprocess
import re

from dataset_loader.dataset_loader import DatasetLoader
from data_structures.answer import Answer
from data_structures.prompt_store import PromptsStore
from utils.framework_utils import print_progress_bar
from model_loader.model_loader import ModelLoader


class QuixBugsPythonLoader(DatasetLoader):
    """
    Class for loading and testing the dataset QuixBugs Python.
    """

    def __init__(self) -> None:
        """
        Initialize the QuixBugsPythonLoader.
        """
        super().__init__()
        self.name = "QuixBugs Python"
        self.area = "APR"

    def load_prompts(self) -> None:
        """
        Load prompts for QuixBugs Python dataset.

        Returns:
            None
        """
        print(f"Loading {self.name} prompts...")
        prompts = PromptsStore(self.area)

        # Get all python files in QuixBugs
        python_directory = "./datasets/APR/QuixBugs/python_programs_bug"
        python_file_list = os.listdir(python_directory)

        for i, file_name in enumerate(python_file_list):
            if i == 1000:
                break
            try:
                file_path = os.path.join(python_directory, file_name)
                if os.path.isfile(file_path):
                    # Read the content of each Python file and create prompts
                    with open(file_path, "r") as file:
                        file_data = file.read().strip()

                    prompts.add_instruct(file_name, file_data, "Python")

                    lines = file_data.split("\n")

                    # Regular expression pattern to match the end of a docstring
                    docstring_end_pattern = r'"""([^"]*)"""'
                    # Find the end of the docstring
                    docstring_end_match = re.search(
                        docstring_end_pattern, file_data, re.DOTALL
                    )
                    prefix = file_data[: docstring_end_match.end()]

                    prompts.add_completion(file_name, prefix)

                    last_line = "\n".join(lines[len(lines) - 1 :])
                    prompts.add_infilling(file_name, prefix, last_line)
                else:
                    logging.error(f"'{file_path}' is not a file.")
            except Exception as e:
                logging.error(f"Error reading file '{file_name}': {str(e)}")

        print(f"{self.name} prompts loaded.\n")
        self.prompts = prompts

    def run_tests(self, program_path: str, answer: Answer) -> None:
        """
        Run tests for the answer.

        Args:
            program_path (str): Path to the program.
            answer (Answer): Answer object.
        Returns:
            None
        """
        try:
            # Run the pytest command and capture the output
            pytest_command = f"pytest {program_path}"

            timeout = 60
            if answer.id == "knapsack.py" or answer.id == "levenshtein.py":
                # KNAPSACK and LEVEHSHTEIN might need a long time to finish
                timeout = 300

            result = subprocess.run(
                pytest_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if result and result.stdout:
                # Extract the last line from the output
                last_line = result.stdout.strip().splitlines()[-1]

                # Use a regular expression to find the number of failed and passed tests
                passed_match = re.search(r"(\d+) passed", last_line)
                failed_match = re.search(r"(\d+) failed", last_line)

                answer.passed = int(passed_match.group(1)) if passed_match else 0
                answer.failed = int(failed_match.group(1)) if failed_match else 0
            else:
                answer.passed = 0
                answer.failed = 0
                answer.error_message = "Error running pytest subprocess or no output."

        except subprocess.TimeoutExpired as e:
            # Handle timeout and kill the pytest subprocess
            answer.failed = 0
            answer.passed = 0
            answer.other_error = True
            answer.error_message = "Timed out"
            subprocess.run(["pkill", "-f", pytest_command])

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
            # File paths
            dynamic_directory = "./datasets/APR/QuixBugs/python_programs"
            test_module_directory = "./datasets/APR/QuixBugs/python_testcases"
            program_path = os.path.join(test_module_directory, f"test_{answer.id}")
            dynamic_file_path = os.path.join(dynamic_directory, answer.id)

            # Create the directory if it doesn't exist and write answer to file
            os.makedirs(dynamic_directory, exist_ok=True)
            with open(dynamic_file_path, "w") as file:
                file.write(answer.code)

            # Check syntax errors and run tests on the program
            if answer.code != "":
                answer.syntax_error, answer.error_message = super().check_python_syntax(
                    answer.code
                )
            else:
                answer.syntax_error = False
                answer.other_error = True
                answer.error_message = "Empty file, could not extract any code"

            if answer.syntax_error == False:
                self.run_tests(program_path, answer)
            else:
                answer.failed_count, answer.passed_count = 0, 0

            print_progress_bar(i, len(answers))
