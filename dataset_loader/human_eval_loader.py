import os

from human_eval_infilling.execution import (
    check_correctness as check_correctness_infilling,
)
from human_eval_infilling.data import (
    read_problems as read_problems_infilling,
)
from human_eval.execution import check_correctness as check_correctness_instruct
from human_eval.data import (
    read_problems as read_problems_instruct,
    HUMAN_EVAL as HUMAN_EVAL_INSTRUCT,
)
from human_eval_infilling.execution import (
    check_correctness as check_correctness_infilling,
)
from human_eval_infilling.data import (
    read_problems as read_problems_infilling,
)
from human_eval.execution import check_correctness as check_correctness_instruct
from human_eval.data import (
    read_problems as read_problems_instruct,
    HUMAN_EVAL as HUMAN_EVAL_INSTRUCT,
)
from collections import defaultdict
from dataset_loader.dataset_loader import DatasetLoader
from data_structures.answer import Answer
from data_structures.prompt_store import PromptsStore
from utils.framework_utils import print_progress_bar
from model_loader.model_loader import ModelLoader


class HumanEvalLoader(DatasetLoader):
    """
    Class for loading and testing the dataset HumanEval.

    Attributes:
        name (str): The name of the dataset.
        area (str): The area of the dataset.

    Methods:
        __init__: Initialize the HumanEvalLoader.
        load_prompts: Load prompts for HumanEval dataset.
        test_code: Test the provided answer.
    """

    def __init__(self) -> None:
        """
        Initialize the HumanEvalLoader.
        """
        super().__init__()
        self.name = "HumanEval"
        self.area = "CodeGen"

    def load_prompts(self) -> None:
        """
        Load prompts for HumanEval dataset.
        """
        print(f"Loading {self.name} prompts...")
        prompts = PromptsStore(self.area)

        # Fetch all problems from HumanEval normal aka instruct
        instruct_problems = [read_problems_instruct(HUMAN_EVAL_INSTRUCT)]
        for i, (task_id, entry) in enumerate(instruct_problems[0].items()):
            if i == 1000:
                break
            prompts.add_instruct(task_id, entry["prompt"], "Python")

        # Fetch all problems from HumanEval infilling
        infilling_problems = [read_problems_infilling("single-line")]

        for i, (task_id, entry) in enumerate(infilling_problems[0].items()):
            if i == 1000:
                break
            prompts.add_infilling(task_id, entry["prompt"], entry["suffix"])

        print(f"{self.name} prompts loaded.\n")
        self.prompts = prompts

    def test_code(self, answers: list[Answer], model: ModelLoader) -> None:
        """
        Test the provided answer.

        Args:
            answer (Answer): Answer object.
            model  (ModelLoader): Model that created the answer.
        Return:
            None
        """
        for i, answer in enumerate(answers, start=1):
            os.environ["TOKENIZERS_PARALLELISM"] = "false"

            code = ""
            if answer.id.split("/")[0] == "SingleLineInfilling":
                code = answer.infill_piece
            else:
                code = answer.code
            run_eval_list = defaultdict(list)
            run_eval_list = run_eval(answer.id, code, run_eval_list)

            if run_eval_list[answer.id][0][1]["passed"]:
                answer.passed = 1
            else:
                answer.failed = 1

            # If it contains anything other than this it is a syntax error
            result = run_eval_list[answer.id][0][1]["result"]
            if result == "failed: " or result == "passed":
                answer.syntax_error = False

            else:
                if result == "timed out":
                    answer.other_error = True
                else:
                    answer.syntax_error = True

                answer.error_message = result

            print_progress_bar(i, len(answers))


def run_eval(task_id, answer, results):
    """
    Evaluate an answer for a task using human evaluation.

    Args:
        task_id (str): ID of the task being evaluated.
        answer (Any): Answer or completion to be evaluated.
        results (Dict[str, List[Any]]): Dictionar y storing evaluation results.

    Returns:
        Dict[str, List[Any]]: Updated evaluation results.

    Evaluates the given answer against problems from HUMAN_EVAL, checks correctness with a timeout,
    and updates the results dictionary accordingly.
    """
    timeout = 5.0

    if task_id.split("/")[0] == "SingleLineInfilling":
        problem = read_problems_infilling("single-line")[task_id]
        correctness_result = check_correctness_infilling(problem, answer, timeout)

    else:
        problem = read_problems_instruct(HUMAN_EVAL_INSTRUCT)[task_id]
        correctness_result = check_correctness_instruct(problem, answer, timeout)

    results[correctness_result["task_id"]].append(
        (correctness_result["completion_id"], correctness_result)
    )

    return results
