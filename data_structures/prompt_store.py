import json

from data_structures.task import Task
from data_structures.prompt import Prompt


class PromptsStore:
    """
    Represents a prompts store containing prompts data.
    """

    def __init__(self, area: str):
        """
        Initializes a PromptsStore object.

        Args:
            area (str): Area of the prompts store.
        """
        self.area = area
        self.conversation = []
        self.completion = []
        self.infilling = []

    def add_instruct(self, id: str, code: str, language: str):
        """
        Adds a instruct prompt to the prompts store.

        Args:
            id (str): Unique identifier for the prompt.
            code (str): Code snippet for the conversation prompt.
            language (str): Language of the code snippet.
        """
        if self.area == "APR":
            prompt = Prompt.from_apr(code, language)
        elif self.area == "CodeGen":
            prompt = Prompt.from_code_gen(code, language)
        self.conversation.append((id, prompt))

    def add_completion(self, id: str, code: str):
        """
        Adds a completion prompt to the prompts store.

        Args:
            id (str): Unique identifier for the prompt.
            code (str): Code snippet for the completion prompt.
        """
        prompt = Prompt.from_completion(code)
        self.completion.append((id, prompt))

    def add_infilling(self, id: str, prefix: str, suffix: str):
        """
        Adds an infilling prompt to the prompts store.

        Args:
            id (str): Unique identifier for the prompt.
            prefix (str): Prefix for the infilling prompt.
            suffix (str): Suffix for the infilling prompt.
        """
        prompt = Prompt.from_infilling(prefix, suffix)
        self.infilling.append((id, prompt))

    def get_tasks(
        self,
        conversation_mode: str,
        template_name: str,
        max_chain_depth: int,
        answers_per_task: int,
    ):
        """
        Get tasks based on the conversation mode, template name, maximum chain depth, and answers per task.

        Args:
            conversation_mode (str): Mode of the conversation (conversation, completion, infilling).
            template_name (str): Name of the template.
            max_chain_depth (int): Maximum chain depth.
            answers_per_task (int): Number of answers per task.

        Returns:
            List[Task]: List of task objects.
        """
        tasks = []
        list = []
        if conversation_mode == "instruction":
            list = self.conversation
        elif conversation_mode == "completion":
            list = self.completion
        elif conversation_mode == "infilling":
            for id, prompt in self.infilling:
                new_prompt = create_infilling_prompt(prompt, template_name)
                list.append((id, new_prompt))
        else:
            raise NotImplemented("This mode is not supported.")

        for id, prompt in list:
            tasks.append(
                Task(
                    id,
                    prompt,
                    conversation_mode,
                    max_chain_depth,
                    answers_per_task,
                )
            )
        return tasks


def create_infilling_prompt(prompt: Prompt, template_name: str):
    """
    Create an infilling prompt based on the provided prompt and template name.

    Args:
        prompt (Prompt): Prompt object.
        template_name (str): Name of the template.

    Returns:
        Prompt: Updated infilling prompt.
    """
    try:
        with open(f"./chat_templates/{template_name}.json", "r") as file:
            tokens = json.load(file)
    except FileNotFoundError:
        raise Exception(
            "File not found. Make sure the file exists and contains valid JSON data."
        )

    message = tokens["prompt_template"].format(
        prefix=prompt.prefix, suffix=prompt.suffix
    )

    with open("./prompts/system_infilling") as system_file:
        system_role = {"role": "system", "content": system_file.read()}

    user_role = {
        "role": "user",
        "content": message,
    }

    if tokens["use_system_message"]:
        prompt.prompt = [system_role, user_role]
    else:
        prompt.prompt = [user_role]
    return prompt
