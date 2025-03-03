python3 main.py \
    --datasets \
    HumanEval \
    --model_configs \
    TheBloke/CodeLlama-7B-Instruct-GPTQ:llama2:instruction \
    TheBloke/CodeLlama-13B-Instruct-GPTQ:llama2:instruction \
    TheBloke/CodeLlama-34B-Instruct-GPTQ:llama2:instruction \
    TheBloke/deepseek-coder-1.3B-instruct-GPTQ:deepseek_coder:instruction \
    TheBloke/deepseek-coder-6.7B-instruct-GPTQ:deepseek_coder:instruction \
    TheBloke/deepseek-coder-33B-instruct-GPTQ:deepseek_coder:instruction \
    TheBloke/Llama-2-7B-Chat-GPTQ:llama2:instruction \
    TheBloke/Llama-2-13B-Chat-GPTQ:llama2:instruction \
    astronomer/Llama-3-8B-Instruct-GPTQ-4-Bit:llama3:instruction \
    --answers_per_task 1 \
    --results_dir code_eval \
    --params max_new_tokens=400 do_sample=false;
python3 main.py \
    --datasets \
    HumanEval \
    --model_configs \
    TheBloke/CodeLlama-7B-Instruct-GPTQ:llama2:instruction \
    TheBloke/CodeLlama-13B-Instruct-GPTQ:llama2:instruction \
    TheBloke/CodeLlama-34B-Instruct-GPTQ:llama2:instruction \
    TheBloke/deepseek-coder-1.3B-instruct-GPTQ:deepseek_coder:instruction \
    TheBloke/deepseek-coder-6.7B-instruct-GPTQ:deepseek_coder:instruction \
    TheBloke/deepseek-coder-33B-instruct-GPTQ:deepseek_coder:instruction \
    TheBloke/Llama-2-7B-Chat-GPTQ:llama2:instruction \
    TheBloke/Llama-2-13B-Chat-GPTQ:llama2:instruction \
    astronomer/Llama-3-8B-Instruct-GPTQ-4-Bit:llama3:instruction \
    --answers_per_task 1 \
    --results_dir code_eval \
    --params max_new_tokens=400 do_sample=false;
python3 main.py \
    --datasets \
    QuixBugsPython \
    --model_configs \
    TheBloke/CodeLlama-7B-Instruct-GPTQ:llama2:instruction \
    TheBloke/CodeLlama-13B-Instruct-GPTQ:llama2:instruction \
    TheBloke/CodeLlama-34B-Instruct-GPTQ:llama2:instruction \
    TheBloke/deepseek-coder-1.3B-instruct-GPTQ:deepseek_coder:instruction \
    TheBloke/deepseek-coder-6.7B-instruct-GPTQ:deepseek_coder:instruction \
    TheBloke/deepseek-coder-33B-instruct-GPTQ:deepseek_coder:instruction \
    TheBloke/Llama-2-7B-Chat-GPTQ:llama2:instruction \
    TheBloke/Llama-2-13B-Chat-GPTQ:llama2:instruction \
    astronomer/Llama-3-8B-Instruct-GPTQ-4-Bit:llama3:instruction \
    --answers_per_task 1 \
    --results_dir code_eval \
    --params max_new_tokens=1000 do_sample=false;
python3 main.py \
    --datasets \
    QuixBugsJava \
    --model_configs \
    TheBloke/CodeLlama-7B-Instruct-GPTQ:llama2:instruction \
    TheBloke/CodeLlama-13B-Instruct-GPTQ:llama2:instruction \
    TheBloke/CodeLlama-34B-Instruct-GPTQ:llama2:instruction \
    TheBloke/deepseek-coder-1.3B-instruct-GPTQ:deepseek_coder:instruction \
    TheBloke/deepseek-coder-6.7B-instruct-GPTQ:deepseek_coder:instruction \
    TheBloke/deepseek-coder-33B-instruct-GPTQ:deepseek_coder:instruction \
    TheBloke/Llama-2-7B-Chat-GPTQ:llama2:instruction \
    TheBloke/Llama-2-13B-Chat-GPTQ:llama2:instruction \
    astronomer/Llama-3-8B-Instruct-GPTQ-4-Bit:llama3:instruction \
    --answers_per_task 1 \
    --results_dir code_eval \
    --params max_new_tokens=1000 do_sample=false;
python3 main.py \
    --datasets \
    LlmVul \
    --model_configs \
    TheBloke/CodeLlama-7B-Instruct-GPTQ:llama2:instruction \
    TheBloke/CodeLlama-13B-Instruct-GPTQ:llama2:instruction \
    TheBloke/CodeLlama-34B-Instruct-GPTQ:llama2:instruction \
    TheBloke/deepseek-coder-1.3B-instruct-GPTQ:deepseek_coder:instruction \
    TheBloke/deepseek-coder-6.7B-instruct-GPTQ:deepseek_coder:instruction \
    TheBloke/deepseek-coder-33B-instruct-GPTQ:deepseek_coder:instruction \
    TheBloke/Llama-2-7B-Chat-GPTQ:llama2:instruction \
    TheBloke/Llama-2-13B-Chat-GPTQ:llama2:instruction \
    astronomer/Llama-3-8B-Instruct-GPTQ-4-Bit:llama3:instruction \
    --answers_per_task 1 \
    --results_dir code_eval \
    --params max_new_tokens=2000 do_sample=false;
python3 main.py \
    --datasets \
    SecurityEval \
    --model_configs \
    TheBloke/CodeLlama-7B-Instruct-GPTQ:llama2:instruction \
    TheBloke/CodeLlama-13B-Instruct-GPTQ:llama2:instruction \
    TheBloke/CodeLlama-34B-Instruct-GPTQ:llama2:instruction \
    TheBloke/deepseek-coder-1.3B-instruct-GPTQ:deepseek_coder:instruction \
    TheBloke/deepseek-coder-6.7B-instruct-GPTQ:deepseek_coder:instruction \
    TheBloke/deepseek-coder-33B-instruct-GPTQ:deepseek_coder:instruction \
    TheBloke/Llama-2-7B-Chat-GPTQ:llama2:instruction \
    TheBloke/Llama-2-13B-Chat-GPTQ:llama2:instruction \
    astronomer/Llama-3-8B-Instruct-GPTQ-4-Bit:llama3:instruction \
    --answers_per_task 1 \
    --results_dir code_eval \
    --params max_new_tokens=400 do_sample=false;
