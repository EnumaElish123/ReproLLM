"""M3 first-half integration: the 38 declaration rules form a usable catalog."""

from pathlib import Path

from reprollm.core.engine import run_audit
from reprollm.core.registry import all_rules
from reprollm.core.yaml_io import dump_yaml
from reprollm.profiles.loader import builtin_profile_names, resolve
from reprollm.schemas.finding import FindingStatus
from tests.conftest import materialize_repo
from tests.unit.rules.helpers import context, failures

CATEGORIES = {"model", "dataset", "gen", "prompt", "eval", "judge", "train", "privacy"}


def test_all_38_rules_are_reachable_and_level_one(tmp_path: Path) -> None:
    rules = [rule for rule in all_rules() if rule.category in CATEGORIES and rule.min_level == 1]
    assert len(rules) == 38
    counts = {category: sum(rule.category == category for rule in rules) for category in CATEGORIES}
    assert counts == {
        "model": 6,
        "dataset": 5,
        "gen": 5,
        "prompt": 3,
        "eval": 6,
        "judge": 4,
        "train": 5,
        "privacy": 4,
    }
    profiles = [name for name in builtin_profile_names() if name != "core"]
    assert {rule.id for rule in rules} <= set(resolve(profiles, tmp_path).rules)


def test_complete_declarations_satisfy_every_applicable_llm_rule(tmp_path: Path) -> None:
    ctx = context(
        tmp_path,
        models={
            "primary": {
                "provider": "huggingface",
                "id": "org/model",
                "dtype": "bfloat16",
                "quantization": "none",
                "trust_remote_code": True,
                "adapter": {
                    "provider": "peft",
                    "id": "org/adapter",
                    "type": "lora",
                    "rank": 8,
                    "alpha": 16,
                    "target_modules": ["q_proj"],
                },
            },
            "judge": {"provider": "openai", "id": "judge"},
        },
        datasets={
            "eval": {
                "provider": "huggingface",
                "id": "org/data",
                "split": "test",
                "subset": "default",
                "preprocessing": {"description": "none"},
                "sampling": {"n": 2, "seed": 0},
            }
        },
        prompts={"system": {"text": "input", "few_shot": {"n": 0}}, "judge": {"text": "judge"}},
        generation={"temperature": 0.5, "top_p": 1, "max_tokens": 64, "seed": 0, "stop": []},
        inference={
            "backend": "vllm",
            "dtype": "bfloat16",
            "quantization": "none",
            "tensor_parallel_size": 1,
            "gpu_memory_utilization": 0.8,
        },
        evaluation={
            "metrics": [{"name": "accuracy", "implementation": "evaluate==0.4.0"}],
            "aggregation": "mean",
            "repetitions": 1,
            "definitions": {"asr": "fraction"},
            "query_budget": 10,
            "judge": {"params": {"temperature": 0, "max_tokens": 16}, "repetitions": 1},
        },
        training={
            "method": "lora",
            "learning_rate": 0.0001,
            "batch_size": 1,
            "max_steps": 1,
            "optimizer": "adamw",
            "scheduler": "cosine",
            "precision": "bfloat16",
        },
        privacy={
            "threat_model": "black-box",
            "mechanism": {"name": "dp", "params": {"epsilon": 1}},
            "metrics": ["epsilon"],
            "attack": {"method": "mia", "query_budget": 0},
        },
    )
    ctx.detection.hints.adapter = True
    ctx.detection.hints.trust_remote_code = True
    for rule_type in all_rules():
        if rule_type.category in CATEGORIES and rule_type.min_level == 1:
            rule = rule_type()
            assert rule.applies(ctx), rule.id
            assert not failures(rule.check(ctx)), rule.id


def test_llm_findings_are_deterministic_and_level_zero_is_unchanged(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    data = {
        "project": {"name": "gaps"},
        "experiment": {
            "profiles": ["inference", "evaluation", "finetuning", "privacy", "llm_judge"]
        },
    }
    (repo / "reprollm.yaml").write_text(dump_yaml(data), encoding="utf-8")
    first = run_audit(repo)
    second = run_audit(repo)
    assert first.findings == second.findings
    assert first.summary == second.summary
    assert any(f.category in CATEGORIES and f.status == FindingStatus.FAIL for f in first.findings)
    lower = run_audit(repo, level=0)
    assert not any(f.category in CATEGORIES for f in lower.findings)
