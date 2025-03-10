from enum import Enum


class AvailableModels(str, Enum):
    GPT2 = "openai-community/gpt2"


class CLSecurityDataset(str, Enum):
    GBUG_JAVA = "rufimelo/gbug-java"
