"""Pairwise LLM-as-a-judge evaluation (golden fixture)."""

import argparse
import json

from openai import OpenAI


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--judge-model", default="gpt-4o")
    parser.add_argument("--n-trials", type=int, default=1)
    parser.add_argument("--pairs", default="data/pairs.jsonl")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with open("prompts/judge.txt", encoding="utf-8") as handle:
        rubric = handle.read()
    client = OpenAI()
    with open(args.pairs, encoding="utf-8") as handle:
        pairs = [json.loads(line) for line in handle if line.strip()]

    wins = 0
    for pair in pairs:
        response = client.chat.completions.create(
            model=args.judge_model,
            messages=[
                {"role": "system", "content": rubric},
                {"role": "user", "content": f"Prompt: {pair['prompt']}\nA: {pair['a']}\nB: {pair['b']}"},
            ],
        )
        verdict = response.choices[0].message.content or ""
        wins += verdict.strip().upper().startswith("A")
    print("win rate:", wins / len(pairs))


if __name__ == "__main__":
    main()
