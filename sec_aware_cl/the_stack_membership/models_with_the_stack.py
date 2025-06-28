import json

import requests

# Define the Hugging Face API endpoint with the specific dataset filter
API_URL = "https://huggingface.co/api/models?filter=dataset:bigcode/the-stack-v2"

# Send a GET request to the API
response = requests.get(API_URL)

# Check if the request was successful
if response.status_code == 200:
    models = response.json()

    # Extract relevant information from each model
    model_data = []
    for model in models:
        model_info = {
            "model_id": model.get("modelId"),
            "author": model.get("author"),
            "sha": model.get("sha"),
            "lastModified": model.get("lastModified"),
            "tags": model.get("tags"),
            "downloads": model.get("downloads"),
            "likes": model.get("likes"),
            "pipeline_tag": model.get("pipeline_tag"),
            "private": model.get("private"),
            "gated": model.get("gated"),
            "disabled": model.get("disabled"),
            "model_card": model.get("model_card"),
            "siblings": model.get("siblings"),
            "config": model.get("config"),
            "cardData": model.get("cardData"),
            "spaces": model.get("spaces"),
            "datasets": model.get("datasets"),
            "metrics": model.get("metrics"),
            "library_name": model.get("library_name"),
            "model_name": model.get("model_name"),
            "model_type": model.get("model_type"),
            "language": model.get("language"),
            "license": model.get("license"),
            "tags": model.get("tags"),
            "downloads": model.get("downloads"),
            "likes": model.get("likes"),
            "pipeline_tag": model.get("pipeline_tag"),
            "createdAt": model.get("createdAt"),
        }
        model_data.append(model_info)

    # Save the extracted data to a JSON file
    with open("models_using_the_stack_v2.json", "w") as json_file:
        json.dump(model_data, json_file, indent=4)

    print("Model data has been saved to 'models_using_the_stack_v2.json'")
else:
    print(
        f"Failed to fetch data from Hugging Face API. Status code: {response.status_code}"
    )
