python3 main.py \
    --datasets \
    HumanEval \
    --model_configs \
    TheBloke/CodeLlama-7B-Instruct-GPTQ:llama2:instruction \
    TheBloke/CodeLlama-13B-Instruct-GPTQ:llama2:instruction \
    TheBloke/CodeLlama-34B-Instruct-GPTQ:llama2:instruction \
    --answers_per_task 1 \
    --results_dir compare \
    --params max_new_tokens=400 do_sample=false;