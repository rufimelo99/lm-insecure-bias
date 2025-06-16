from datetime import datetime
from enum import Enum


class AvailableModels(str, Enum):
    GPT2 = "openai-community/gpt2"
    LLAMA_INSTRUCT = "meta-llama/Llama-3.2-3B-Instruct"
    code_llama = "meta-llama/CodeLlama-7b-hf"
    vicuna7 = "lmsys/vicuna-7b-v1.5"
    vicuna13 = "lmsys/vicuna-13b-v1.5"
    dscoder7 = "deepseek-ai/deepseek-coder-6.7b-base"
    dscoder7_inst = "deepseek-ai/deepseek-coder-6.7b-instruct"
    codet5_plus = "Salesforce/codet5p-16b"
    codet5_plus_inst = "Salesforce/codet5p-16b-instruct"
    wizardcoder = "WizardLMTeam/WizardCoder-15B-V1.0"
    codegen = "Salesforce/codegen-6B-multi"
    mellum = "JetBrains/Mellum-4b-base"
    codesage = "codesage/codesage-large-v2"
    parscale = "ParScale/ParScale-Qwen-3B-P8-Python"
    yulan = "yulan-team/YuLan-Mini"
    starcoder3b = "bigcode/starcoder2-3b"
    starcoder7b = "bigcode/starcoder2-7b"


class CLSecurityDataset(str, Enum):
    GBUG_JAVA = "rufimelo/gbug-java"


MODEL_INFO = {
    AvailableModels.wizardcoder: datetime(2024, 1, 4),
    AvailableModels.codegen: datetime(2022, 3, 22),
    AvailableModels.vicuna7: datetime(2023, 5, 9),
    AvailableModels.vicuna13: datetime(2023, 5, 9),
    AvailableModels.mellum: datetime(3000, 1, 1),  # Mellum does not have a clear release date
    AvailableModels.codesage: datetime(3000, 1, 1),  # CodeSage does not have a clear release date
    AvailableModels.parscale: datetime(3000, 1, 1),  # ParScale does not have a clear release date
    AvailableModels.yulan: datetime(3000, 1, 1),  # YuLan does not have a clear release date
    AvailableModels.starcoder3b: datetime(3000, 1, 1),  # YuLan does not have a clear release date
    AvailableModels.starcoder7b: datetime(3000, 1, 1),  # YuLan does not have a clear release date
}
