import copy

from data_structures.answer import Answer
from data_structures.prompt import Prompt


class Task:
    """
    Class for storing tasks along with their statistics and answers.
    """

    def __init__(
        self,
        id: str,
        prompt_instance: Prompt,
        conversation_type: str,
        max_chain_depth: int,
        answers_per_task: int,
    ) -> None:
        """
        Initializes a Task object.

        Args:
            id (str): Unique identifier for the task.
            prompt_instance (Prompt): Prompt for generating answers.
            conversation_type (str): Type of conversation.
            max_chain_depth (int): Maximum chain depth.
            answers_per_task (int): Number of answers per task.
        """
        self.id = id
        self.prompt_instance = prompt_instance
        self.max_chain_depth = max_chain_depth
        self.max_memory = 0
        self.syntax_errors = {depth: 0 for depth in range(max_chain_depth)}
        self.other_errors = {depth: 0 for depth in range(max_chain_depth)}
        self.time_to_gen = {depth: 0 for depth in range(max_chain_depth)}
        self.tokens_generated = {depth: 0 for depth in range(max_chain_depth)}
        self.passed = {depth: 0 for depth in range(max_chain_depth)}
        self.failed = {depth: 0 for depth in range(max_chain_depth)}
        self.answers = [[] for _ in range(max_chain_depth)]
        self.num_answers = {depth: 0 for depth in range(max_chain_depth)}
        self.correct = {depth: 0 for depth in range(max_chain_depth)}

        p = Answer(id, prompt_instance, conversation_type, 0)
        for _ in range(answers_per_task):
            self.add_answer(copy.copy(p))

    def add_answer(self, answer: Answer):
        """
        Add an answer to the task.

        Args:
            answer (Answer): Answer object to be added.
        """
        depth = answer.chain_depth
        self.answers[depth].append(answer)

    def update_stats(self):
        """
        Update statistics for the task.
        """
        for i in range(self.max_chain_depth):
            for answer in self.answers[i]:
                self.time_to_gen[i] += answer.time_to_gen
                self.tokens_generated[i] += answer.tokens_generated
                self.passed[i] += answer.passed
                self.failed[i] += answer.failed
                self.syntax_errors[i] += 1 if answer.syntax_error else 0
                self.other_errors[i] += 1 if answer.other_error else 0
                self.num_answers[i] += 1
                self.correct[i] += 1 if answer.failed == 0 and answer.passed > 0 else 0
                if answer.memory > self.max_memory:
                    self.max_memory = answer.memory

    def detailed_json(self):
        """
        Convert the task to a detailed JSON format.

        Returns:
            dict: Detailed JSON representation of the task.
        """
        answers = []
        for depth in range(self.max_chain_depth):
            for answer in self.answers[depth]:
                if answer != []:
                    answers.append(answer.detailed_json())

        return {
            "Id": self.id,
            "Prompt": self.prompt_instance.prompt,
            "Answers": answers,
        }

    def summary_json(self):
        """
        Convert the task to a summary JSON format.

        Returns:
            dict: Summary JSON representation of the task.
        """
        statistics = {
            depth: {
                "Syntax errors": self.syntax_errors[depth],
                "Other errors": self.other_errors[depth],
                "Time(sec)": self.time_to_gen[depth],
                "Tokens generated": self.tokens_generated[depth],
                "Passed": self.passed[depth],
                "Failed": self.failed[depth],
                "Correct": self.correct[depth],
            }
            for depth in range(self.max_chain_depth)
            if any(
                [
                    self.syntax_errors[depth],
                    self.other_errors[depth],
                    self.time_to_gen[depth],
                    self.tokens_generated[depth],
                    self.passed[depth],
                    self.failed[depth],
                    self.correct[depth],
                ]
            )
        }
        return {
            "Id": self.id,
            "Prompt": self.prompt_instance.prompt,
            "Statistics": statistics,
        }
