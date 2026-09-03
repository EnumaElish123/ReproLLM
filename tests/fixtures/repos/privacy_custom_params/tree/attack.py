"""Membership inference attack (golden fixture)."""

import yaml


def load_budget(path: str = "configs/privacy.yaml") -> int:
    with open(path, encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    return int(config["attack"]["query_budget"])


def membership_inference(loss_values, target_loss, budget: int) -> bool:
    observed = loss_values[:budget]
    threshold = sum(sorted(observed)[: len(observed) // 2]) / max(len(observed) // 2, 1)
    return target_loss < threshold


def main() -> None:
    print("query budget:", load_budget())


if __name__ == "__main__":
    main()
