python3 main.py --model_configs \
    TheBloke/CodeLlama-7B-Instruct-GPTQ:llama2:instruction \
    TheBloke/deepseek-coder-6.7B-instruct-GPTQ:deepseek_coder:instruction \
    --datasets "HumanEval" \
    --answers_per_task 10 \
    --results_dir temp_0.8-top_p_0.95 \
    --params do_sample=true max_new_tokens=400 temperature=0.8 top_p=0.95;
python3 main.py --model_configs \
    TheBloke/CodeLlama-7B-Instruct-GPTQ:llama2:instruction \
    TheBloke/deepseek-coder-6.7B-instruct-GPTQ:deepseek_coder:instruction \
    --datasets "HumanEval" \
    --answers_per_task 10 \
    --results_dir temp_0.56-top_p_0.95 \
    --params do_sample=true max_new_tokens=400 temperature=0.56 top_p=0.95;
python3 main.py --model_configs \
    TheBloke/CodeLlama-7B-Instruct-GPTQ:llama2:instruction \
    TheBloke/deepseek-coder-6.7B-instruct-GPTQ:deepseek_coder:instruction \
    --datasets "HumanEval" \
    --answers_per_task 10 \
    --results_dir temp_0.32-top_p_0.95 \
    --params do_sample=true max_new_tokens=400 temperature=0.32 top_p=0.95;
python3 main.py --model_configs \
    TheBloke/CodeLlama-7B-Instruct-GPTQ:llama2:instruction \
    TheBloke/deepseek-coder-6.7B-instruct-GPTQ:deepseek_coder:instruction \
    --datasets "HumanEval" \
    --answers_per_task 10 \
    --results_dir temp_0.8-top_p_0.665 \
    --params do_sample=true max_new_tokens=400 temperature=0.8 top_p=0.665;
python3 main.py --model_configs \
    TheBloke/CodeLlama-7B-Instruct-GPTQ:llama2:instruction \
    TheBloke/deepseek-coder-6.7B-instruct-GPTQ:deepseek_coder:instruction \
    --datasets "HumanEval" \
    --answers_per_task 10 \
    --results_dir temp_0.8-top_p_0.38 \
    --params do_sample=true max_new_tokens=400 temperature=0.8 top_p=0.38