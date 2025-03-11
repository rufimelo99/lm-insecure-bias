from enum import Enum


class AvailableModels(str, Enum):
    GPT2 = "openai-community/gpt2"
    LLAMA_INSTRUCT = "meta-llama/Llama-3.2-3B-Instruct"


class CLSecurityDataset(str, Enum):
    GBUG_JAVA = "rufimelo/gbug-java"
