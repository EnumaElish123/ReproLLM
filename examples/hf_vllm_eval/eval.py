"""MMLU evaluation with vLLM (golden fixture)."""

import argparse

import yaml
from datasets import load_dataset
from transformers import AutoTokenizer
from vllm import LLM, SamplingParams


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/eval.yaml")
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--max-tokens", type=int)
    parser.add_argument("--seed", type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with open(args.config, encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3-32B")
    dataset = load_dataset("cais/mmlu", "abstract_algebra", split="test")
    llm = LLM(model=config["model"])
    params = SamplingParams(
        temperature=args.temperature,
        top_p=config["sampling"]["top_p"],
        max_tokens=args.max_tokens,
    )
    prompts = [
        tokenizer.apply_chat_template([{"role": "user", "content": question}])
        for question in dataset["question"]
    ]
    outputs = llm.generate(prompts, params)
    correct = sum(
        1
        for output, answer in zip(outputs, dataset["answer"])
        if output.outputs[0].text.strip() == str(answer)
    )
    print("accuracy:", correct / len(prompts))


if __name__ == "__main__":
    main()
