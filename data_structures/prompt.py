import re


class Prompt:
    """
    Represents a prompt object containing prompt data.
    """

    def __init__(self, prompt: list[dict]):
        """
        Initializes a Prompt object.

        Args:
            prompt (list[dict]): List of dictionary representing the prompt.
        """
        self.prompt = prompt

    @classmethod
    def from_apr(cls, code: str, language: str):
        """
        Create a prompt object from the APR mode.

        Args:
            code (str): Code snippet for the APR prompt.
            language (str): Language of the code snippet.

        Returns:
            Prompt: Prompt object.
        """
        with open("./prompts/system_APR") as system_file:
            system_role = {"role": "system", "content": system_file.read()}
        with open("./prompts/instruction_APR") as instruction_file:
            content = instruction_file.read()
        # Replace the first occurrence with capital letter, the rest lower
        content = re.sub(r"\{language\}", language, content, count=1)
        content = content.replace("{language}", language.lower())
        content = content.replace("{language}", language)
        content = content.replace("{code}", code)
        user_role = {"role": "user", "content": content}
        return cls([system_role, user_role])

    @classmethod
    def from_code_gen(cls, problem: str, language: str):
        """
        Create a prompt object from the code generation mode.

        Args:
            problem (str): Code snippet for the code generation prompt.
            language (str): Language of the code snippet.

        Returns:
            Prompt: Prompt object.
        """
        with open("./prompts/system_code_gen") as system_file:
            system_role = {"role": "system", "content": system_file.read()}
        with open("./prompts/instruction_code_gen") as instruction_file:
            content = instruction_file.read()

        # Replace the first occurrence with capital letter, the rest lower
        content = re.sub(r"\{language\}", language, content, count=1)
        content = content.replace("{language}", language.lower())
        content = content.replace("{code}", problem)
        user_role = {"role": "user", "content": content}
        return cls([system_role, user_role])

    @classmethod
    def from_completion(cls, code: str):
        """
        Create a prompt object from the completion mode.

        Args:
            code (str): Code snippet for the completion prompt.

        Returns:
            Prompt: Prompt object.
        """
        user_role = {"role": "user", "content": code}
        return cls([user_role])

    @classmethod
    def from_infilling(cls, prefix: str, suffix: str):
        """
        Create a prompt object from the infilling mode.

        Args:
            prefix (str): Prefix for the infilling prompt.
            suffix (str): Suffix for the infilling prompt.

        Returns:
            Prompt: Prompt object.
        """
        prompt = Prompt({})
        prompt.prefix = prefix.rstrip("\n")
        prompt.suffix = suffix
        return prompt
