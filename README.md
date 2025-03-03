How to run the code:

cd PurpleLlama
python -m CybersecurityBenchmarks.benchmark.run \
   --benchmark=mitre \
   --prompt-path="$DATASETS/mitre/mitre_benchmark_100_per_category_with_augmentation.json" \
   --response-path="$DATASETS/mitre_responses.json" \
   --judge-response-path="$DATASETS/mitre_judge_responses.json" \
   --stat-path="$DATASETS/mitre_stat.json" \
   --judge-llm="SELFHOSTED::gpt2::something" \
   --expansion-llm="SELFHOSTED::openai-community/gpt2::something" \
   --llm-under-test=SELFHOSTED::openai-community/gpt2::something