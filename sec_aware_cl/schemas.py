from enum import Enum


class AvailableModels(str, Enum):
    GPT2 = "openai-community/gpt2"
    LLAMA_INSTRUCT = "meta-llama/Llama-3.2-3B-Instruct"
    codet5 = "WizardLMTeam/WizardCoder-15B-V1.0"
    code_llama = "meta-llama/CodeLlama-7b-hf"
    vicuna7 = "lmsys/vicuna-7b-v1.5"
    vicuna13 = "lmsys/vicuna-13b-v1.5"
    dscoder7 = "deepseek-ai/deepseek-coder-6.7b-base"
    dscoder7_inst = "deepseek-ai/deepseek-coder-6.7b-instruct"
    codet5_plus = "Salesforce/codet5p-16b"
    codet5_plus_inst = "Salesforce/codet5p-16b-instruct"


class CLSecurityDataset(str, Enum):
    GBUG_JAVA = "rufimelo/gbug-java"
