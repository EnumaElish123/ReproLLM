"""Orthogonal-noise privacy mechanism (golden fixture)."""

import yaml
import torch
from transformers import AutoModelForCausalLM


def load_config(path: str = "configs/privacy.yaml") -> dict:
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def protect_hidden_state(hidden, alpha, delta, safe_interval, orth_loss):
    noise = torch.randn_like(hidden) * alpha
    floor, ceiling = safe_interval
    clipped = torch.clamp(hidden, floor, ceiling)
    return clipped + noise * (1.0 - orth_loss) + delta


def main() -> None:
    config = load_config()
    method = config["method"]
    model = AutoModelForCausalLM.from_pretrained(
        "meta-llama/Llama-3.1-8B-Instruct", trust_remote_code=True
    )
    hidden = torch.zeros(8, 64)
    protected = protect_hidden_state(
        hidden,
        alpha=method["alpha"],
        delta=method["delta"],
        safe_interval=method["safe_interval"],
        orth_loss=method["orth_loss"],
    )
    parameter_count = sum(p.numel() for p in model.parameters())
    print("protected shape:", tuple(protected.shape), "parameters:", parameter_count)


if __name__ == "__main__":
    main()
