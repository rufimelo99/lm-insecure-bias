# LLMSecCode

A framework that allows you to evaluate models capabilities and different secure coding 

## Introduction

Provide a brief overview of the project, its purpose, and any key features.

# Installation

To set up the project and its dependencies, follow the steps below:
##  Step 1: Clone the Repository

Clone the project repository to your local machine using the following command:

```bash
git clone https://github.com/anton-ryden/LLMSecCode.git
```
## Step 2: Navigate to the Project Directory
Navigate to the root directory of the cloned repository.
```bash
cd APR_framework
```

## Step 3: Install Dependencies

Run the setup script to install the required dependencies. However, make sure to read the note on PyTorch and AutoGPTQ before doing so.

```bash
pip install -r requirements.txt
```

## Step 4: Download datasets

Run the setup script to clone repositories for the datasets and make the appropiate changes.

```bash
python setup.py
```

## Note on quantization (PyTorch and AutoGPTQ)

If you would like to use GPTQ quantized models such as those we provide previous results for you need to use AutoGPTQ, which depends on PyTorch. Depending on your system and whether you plan to use GPU acceleration, you may need to check and adjust the PyTorch version manually. Refer to the PyTorch documentation for information on installing PyTorch with the appropriate CUDA or ROCm version.


## Step 5: Run the Project

After successfully completing the setup, you can run the project. Ensure that the virtual environment, if created, is activated. If not, activate it using:

```bash
pyenv activate your-virtual-environment
```
Replace your-virtual-environment with the name of your virtual environment.

Run the project or execute any specific scripts as needed.

```bash
python main.py
```

Congratulations! You have successfully set up and installed the project.

## Usage
Here is an example of how to run the program 
```bash
python main.py 
```
If you are unsure of what to provide the model with and how it affects the program please refer to

```bash
python main.py -h
```

## Models in results:
| Supported coversation type                | Model name                                    | Prompt template |
| ------------------------------------------| ----------------------------------------------|-----------------|
| Instruction/Code Completion/Code Insertion| TheBloke/CodeLlama-7B-Instruct-GPTQ           | llama2          |
| Instruction/Code Completion/Code Insertion| TheBloke/CodeLlama-13B-Instruct-GPTQ          | llama2          |
| Instruction/Code Completion/Code Insertion| TheBloke/CodeLlama-34B-Instruct-GPTQ          | llama2          |
| Instruction                               | TheBloke/Llama-2-7B-Chat-GPTQ                 | llama2          |
| Instruction                               | TheBloke/Llama-2-13B-Chat-GPTQ                | llama2          |
| Instruction/Code Completion/Code Insertion| TheBloke/deepseek-coder-1.3B-instruct-GPTQ    | deepseek_coder  |
| Instruction/Code Completion/Code Insertion| TheBloke/deepseek-coder-6.7B-instruct-GPTQ    | deepseek_coder  |
| Instruction/Code Completion/Code Insertion| TheBloke/deepseek-coder-33B-instruct-GPTQ     | deepseek_coder  |
| Instruction                               | astronomer/Llama-3-8B-Instruct-GPTQ-4-Bit     | llama3          |

## A few supported models (easy to include your own):
| Supported coversation type                | Model family                               | Prompt template  |
| ------------------------------------------| -------------------------------------------|------------------|
| Code Completion/Code Insertion            | TheBloke/CodeLlama                         | llama2           |
| Instruction/Code Completion/Code Insertion| TheBloke/CodeLlama-Instruct                | llama2           |
| Code Insertion                            | TheBloke/CodeLlama-Python                  | llama2           |
| Instruction                               | TheBloke/Llama-2-7B-GPTQ                   | llama2           |
| Instruction                               | TheBloke/Llama-2-7B-Chat-GPTQ              | llama2           |
| Instruction/Code Completion/Code Insertion| TheBloke/deepseek-coder-1.3B-instruct-GPTQ | deepseek_coder   |
| Instruction/Code Completion/Code Insertion| TheBloke/deepseek-coder-1.3B-base-GPTQ     | deepseek_coder   |
| ***Instruction***                         | ***TheBloke/deepseek-llm-7B-base-GPTQ***   |***deepseek_llm***|
| ***Instruction***                         | ***TheBloke/deepseek-llm-7B-chat-GPTQ***   |***deepseek_llm***|

## How to run a model not in the supported matrix


***NOTE: Models in bold do not support system prompts***
## Code completion
Code completion tasks is when you provide specific instructions to guide the model in generating or completing code.
Example:
```python
def quicksort(arr):
```
Expected answer from LLM:
```python
def quicksort(arr):
    if not arr:
        return []

    pivot = arr[0]
    lesser = quicksort([x for x in arr[1:] if x < pivot])
    greater = quicksort([x for x in arr[1:] if x >= pivot])
    return lesser + [pivot] + greater
```
## Instruction
Tailored for instruction-based tasks in coding. It allows you to guide the model in generating code by providing explicit instructions for the desired output.
```python
You are an expert programmer who fixes code. Please fix this buggy code:
def quicksort(arr):
    if not arr:
        return []

    pivot = arr[0]
    lesser = quicksort([x for x in arr[1:] if x < pivot])
    greater = quicksort([x for x in arr[1:] if x > pivot])
    return lesser + [pivot] + greater
```
Expected answer from LLM:
```python
def quicksort(arr):
    if not arr:
        return []

    pivot = arr[0]
    lesser = quicksort([x for x in arr[1:] if x < pivot])
    greater = quicksort([x for x in arr[1:] if x > pivot])
    return lesser + [pivot] + greater
```
## Code insertion
This coversation type is designed for inserting code snippets into a given context. It can be instructed to add specific code elements or functionalities.
High level example:
```python
def quicksort(arr):
    <INSERT>
    return lesser + [pivot] + greater
```
Expected answer from LLM:
```python
def quicksort(arr):
    if not arr:
        return []

    pivot = arr[0]
    lesser = quicksort([x for x in arr[1:] if x < pivot])
    greater = quicksort([x for x in arr[1:] if x > pivot])
    return lesser + [pivot] + greater
```