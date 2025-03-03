from data_structures.task import Task
import numpy as np

from configurator import Configurator
from utils.framework_utils import get_pass_k


class DatasetStore:
    """
    Represents a dataset store containing dataset data.
    """

    def __init__(
        self, name: str, max_chain_depth: int, tasks: list[Task], area: str
    ) -> None:
        """
        Initializes a DatasetStore object.

        Args:
            name (str): Name of the dataset.
            max_chain_depth (int): Maximum chain depth.
            tasks (List[Task]): List of task objects.
            area (str): Name of the area
        """
        self.name = name
        self.max_chain_depth = max_chain_depth
        self.max_memory = 0
        self.tasks = tasks
        self.area = area
        self.stat = {depth: None for depth in range(max_chain_depth)}
        self.syntax_errors = {depth: 0 for depth in range(max_chain_depth)}
        self.other_errors = {depth: 0 for depth in range(max_chain_depth)}
        self.gen_time = {depth: 0 for depth in range(max_chain_depth)}
        self.tokens_generated = {depth: 0 for depth in range(max_chain_depth)}
        self.passed = {depth: 0 for depth in range(max_chain_depth)}
        self.failed = {depth: 0 for depth in range(max_chain_depth)}
        self.num_answers = {depth: 0 for depth in range(max_chain_depth)}
        self.correct = {depth: 0 for depth in range(max_chain_depth)}
        self.pass_at_1 = np.array([])
        self.pass_at_k = np.array([])

    def add_stat(self, depth: int, stat: dict):
        self.stat[depth] = stat

    def update_stats(self):
        """
        Updates statistics for each task in the dataset.
        """
        total_answers, correct_answers = [], []
        for task in self.tasks:
            task.update_stats()
            for depth in range(task.max_chain_depth):
                self.syntax_errors[depth] += task.syntax_errors[depth]
                self.other_errors[depth] += task.other_errors[depth]
                self.gen_time[depth] += task.time_to_gen[depth]
                self.tokens_generated[depth] += task.tokens_generated[depth]
                self.passed[depth] += task.passed[depth]
                self.failed[depth] += task.failed[depth]
                self.num_answers[depth] += task.num_answers[depth]
                self.correct[depth] += task.correct[depth]
                if task.max_memory > self.max_memory:
                    self.max_memory = task.max_memory
                if task.answers[depth] and depth == 0:
                    total_answers.append(task.num_answers[depth])
                    correct_answers.append(task.correct[depth])

        k = max(total_answers)
        self.pass_at_1 = self.estimate_pass_at_1()
        self.pass_at_k = get_pass_k(total_answers, correct_answers, k)

    def estimate_pass_at_1(self):
        """
        Estimates the Pass@1 score.

        Returns:
            float: Pass@1 value.
        """
        total_answers, correct_answers = [], []
        for task in self.tasks:
            for i, answer in enumerate(task.answers[0]):
                if i == 0:
                    correct = 1 if answer.failed == 0 and answer.passed > 0 else 0
                    total_answers.append(1)
                    correct_answers.append(correct)

        return get_pass_k(total_answers, correct_answers, 1)

    def to_detailed_json(self):
        """
        Convert the dataset store to a detailed JSON format.

        Returns:
            dict: Detailed JSON representation of the dataset store.
        """
        return {
            "Name": self.name,
            "Tasks": [task.detailed_json() for task in self.tasks],
        }

    def to_summary_json(
        self,
        conf: Configurator,
        conversation_type: str,
        model_name: str,
        run_time: float,
    ):
        """
        Convert the dataset store to a brief summary JSON format.

        Args:
            conf: Configuration object.
            conversation_type (str): Type of conversation (conversation, completion, infilling).
            model_name (str): The name of the model.
            run_time (float): The time it takes to run both the tests and generation.

        Returns:
            dict: Brief summary JSON representation of the dataset store.
        """
        statistics = {
            depth: {
                "Syntax errors": self.syntax_errors[depth],
                "Other errors": self.other_errors[depth],
                "Generation time (sec)": round(self.gen_time[depth], 1),
                "Tokens generated": round(self.tokens_generated[depth], 1),
                "Average tokens per answer": self.tokens_generated[depth]
                / self.num_answers[depth],
                "Passed": self.passed[depth],
                "Failed": self.failed[depth],
                "Correct": self.correct[depth],
                "Amount of answers": self.num_answers[depth],
                "Success Rate": (
                    round((self.correct[depth] / self.num_answers[depth]) * 100, 1)
                ),
                **(
                    {
                        f"Pass@{conf.answers_per_task}": (
                            round(self.pass_at_k * 100, 1)
                        ),
                        "Pass@1": round(self.pass_at_1 * 100, 1),
                    }
                    if depth == 0
                    else {}
                ),
                "Stat": self.stat[depth],
            }
            for depth in range(self.max_chain_depth)
            if any(
                [
                    self.syntax_errors[depth],
                    self.other_errors[depth],
                    self.gen_time[depth],
                    self.tokens_generated[depth],
                    self.passed[depth],
                    self.failed[depth],
                    self.correct[depth],
                    self.num_answers[depth],
                    self.pass_at_1 is not None,
                    self.pass_at_k is not None,
                    self.stat[depth],
                ]
            )
        }

        statistics = {
            depth: {k: v for k, v in stats.items() if v is not None}
            for depth, stats in statistics.items()
        }

        return {
            "Name": self.name,
            "Model name": model_name,
            "Area": self.area,
            "Total time": round(run_time, 1),
            "Maximum memory usage (GB)": round(self.max_memory, 2),
            "Statistics": statistics,
            "Configurations": {
                "Answers per task": conf.answers_per_task,
                "Conversation type": conversation_type,
                **conf.generation_config,
            },
        }

    def to_brief_summary_json(
        self,
        conf: Configurator,
        conversation_type: str,
        model_name: str,
        run_time: float,
    ):
        """
        Convert the dataset store to a brief summary JSON format.

        Args:
            conf: Configuration object.
            conversation_type (str): Type of conversation (conversation, completion, infilling).
            model_name (str): The name of the model.
            run_time (float): The time it takes to run both the tests and generation.

        Returns:
            dict: Brief summary JSON representation of the dataset store.
        """
        total_syntax_errors = sum(self.syntax_errors.values())
        total_other_errors = sum(self.other_errors.values())
        gen_time = sum(self.gen_time.values())
        total_tokens_generated = sum(self.tokens_generated.values())
        total_passed = sum(self.passed.values())
        total_failed = sum(self.failed.values())
        total_correct = sum(self.correct.values())
        amount_of_answers = sum(self.num_answers.values())
        pass_at_1 = round(self.pass_at_1 * 100, 1)

        total_stat = self.stat[0]
        for i in range(1, len(self.stat)):
            if self.stat[i] == None:
                continue
            for key in self.stat[i]:
                if key in self.stat[i]:
                    total_stat[key] = total_stat[key] * self.stat[i][key]

        return_dict = {
            "Name": self.name,
            "Model name": model_name,
            "Area": self.area,
            "Maximum memory usage (GB)": round(self.max_memory, 2),
            "Syntax errors": total_syntax_errors,
            "Other errors": total_other_errors,
            "Total time (sec)": round(run_time, 1),
            "Testing time (sec)": round(run_time - gen_time, 1),
            "Generation time (sec)": round(gen_time, 1),
            "Tokens generated": total_tokens_generated,
            "Average tokens per answer": round(
                total_tokens_generated / amount_of_answers, 1
            ),
            "Tokens/Sec": round(total_tokens_generated / gen_time, 1),
            "Passed": total_passed,
            "Failed": total_failed,
            "Correct": total_correct,
            "Amount of answers": amount_of_answers,
            "Pass@1": pass_at_1,
            f"Pass@{conf.answers_per_task}": (round(self.pass_at_k * 100, 1)),
            "Total stat": total_stat,
            "Configurations": {
                "Answers per task": conf.answers_per_task,
                "Conversation type": conversation_type,
                **conf.generation_config,
            },
        }
        return_dict = {k: v for k, v in return_dict.items() if v is not None}
        return return_dict
