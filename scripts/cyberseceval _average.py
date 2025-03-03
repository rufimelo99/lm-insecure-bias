import json
import os


def load_json(file_path):
    json_data = []

    json_data.append(load_json_file(file_path))

    return json_data


def load_json_file(file_path):
    with open(file_path, "r") as file:
        data = json.load(file)
    return data


data = load_json_file(
    "/home/antovis/Documents/ModelEvalKit/results/compare/CodeLlama-34B-Instruct-GPTQ/CyberSecEval2/instruct_stat.json"
)
for model, value in data.items():
    pass_tot = 0
    bleu_tot = 0
    for i, (_, val) in enumerate(value.items(), 1):
        pass_tot += val["pass_rate"]
        bleu_tot += val["bleu"]
    print(f"Model: {model} Average_pass: {pass_tot / i}")
    print(f"Model: {model} Average_bleu: {bleu_tot / i}")
