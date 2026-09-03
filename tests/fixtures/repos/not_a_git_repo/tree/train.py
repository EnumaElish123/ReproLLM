"""Minimal training script (golden fixture: not a git repository)."""

import torch


def main() -> None:
    model = torch.nn.Linear(4, 2)
    print("params:", sum(p.numel() for p in model.parameters()))


if __name__ == "__main__":
    main()
