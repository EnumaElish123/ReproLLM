"""M3-T05: training presence, alternative duration and same-adapter completeness."""

from pathlib import Path

import pytest

from reprollm.core.context import AuditContext
from reprollm.profiles.loader import resolve
from reprollm.rules.train import (
    HyperparametersDeclaredRule,
    LoraConfigCompleteRule,
    MethodDeclaredRule,
    OptimizerDeclaredRule,
    PrecisionDeclaredRule,
)
from reprollm.schemas.finding import Severity
from tests.unit.rules.helpers import context, failures

ADAPTER = {
    "provider": "peft",
    "id": "org/adapter",
    "type": "lora",
    "rank": 0,
    "alpha": 0,
    "target_modules": ["q_proj"],
}


@pytest.mark.parametrize(
    "rule_type",
    [
        HyperparametersDeclaredRule,
        LoraConfigCompleteRule,
        MethodDeclaredRule,
        OptimizerDeclaredRule,
        PrecisionDeclaredRule,
    ],
)
def test_no_manifest_skips_training(tmp_path: Path, rule_type) -> None:
    assert rule_type.min_level == 1
    assert not rule_type().applies(AuditContext(tmp_path))


@pytest.mark.parametrize(
    "rule_type,field,value",
    [(MethodDeclaredRule, "method", "full"), (PrecisionDeclaredRule, "precision", "bfloat16")],
)
def test_training_field_missing_and_present(tmp_path: Path, rule_type, field, value) -> None:
    result = failures(rule_type().check(context(tmp_path)))
    assert result[0].severity == Severity.WARNING
    assert result[0].evidence[0].field == f"training.{field}"
    assert not failures(rule_type().check(context(tmp_path, training={field: value})))


@pytest.mark.parametrize(
    "duration", [{"epochs": 0}, {"max_steps": 0}, {"epochs": 1, "max_steps": 1}]
)
def test_hyperparameters_allow_either_duration_and_zero_values(tmp_path: Path, duration) -> None:
    ctx = context(tmp_path, training={"learning_rate": 0, "batch_size": 0, **duration})
    assert not failures(HyperparametersDeclaredRule().check(ctx))


@pytest.mark.parametrize("missing", ["learning_rate", "batch_size", "epochs"])
def test_hyperparameters_report_missing_requirements(tmp_path: Path, missing: str) -> None:
    training = {"learning_rate": 0.0001, "batch_size": 1, "epochs": 1}
    del training[missing]
    result = failures(HyperparametersDeclaredRule().check(context(tmp_path, training=training)))
    assert len(result) == 1 and result[0].severity == Severity.CRITICAL
    assert f"training.{missing}" in [e.field for e in result[0].evidence]
    if missing == "epochs":
        assert "training.epochs or training.max_steps" in result[0].fix_hint


def test_absent_training_reports_all_hyperparameter_requirements(tmp_path: Path) -> None:
    result = failures(HyperparametersDeclaredRule().check(context(tmp_path)))
    assert len(result) == 1
    assert {e.field for e in result[0].evidence} == {
        "training.learning_rate",
        "training.batch_size",
        "training.epochs",
        "training.max_steps",
    }


@pytest.mark.parametrize("training", [None, {}, {"optimizer": "adamw"}, {"scheduler": "cosine"}])
def test_optimizer_and_scheduler_both_required(tmp_path: Path, training) -> None:
    result = failures(OptimizerDeclaredRule().check(context(tmp_path, training=training)))
    assert len(result) == 1 and result[0].severity == Severity.WARNING


def test_optimizer_and_scheduler_declared(tmp_path: Path) -> None:
    ctx = context(tmp_path, training={"optimizer": "adamw", "scheduler": "cosine"})
    assert not failures(OptimizerDeclaredRule().check(ctx))


@pytest.mark.parametrize("method", [None, "full", "other"])
def test_non_lora_training_skips_adapter_completeness(tmp_path: Path, method) -> None:
    assert not LoraConfigCompleteRule().applies(context(tmp_path, training={"method": method}))


@pytest.mark.parametrize("method", ["lora", "qlora"])
@pytest.mark.parametrize("missing", ["rank", "alpha", "target_modules"])
def test_lora_requires_all_fields_in_one_adapter(tmp_path: Path, method: str, missing: str) -> None:
    adapter = {k: v for k, v in ADAPTER.items() if k != missing}
    ctx = context(tmp_path, training={"method": method}, models={"primary": {"adapter": adapter}})
    rule = LoraConfigCompleteRule()
    assert rule.applies(ctx)
    result = failures(rule.check(ctx))
    assert len(result) == 1 and result[0].severity == Severity.CRITICAL
    assert f"models.primary.adapter.{missing}" in [e.field for e in result[0].evidence]


def test_lora_does_not_merge_fields_across_adapters(tmp_path: Path) -> None:
    ctx = context(
        tmp_path,
        training={"method": "lora"},
        models={
            "primary": {"adapter": {k: v for k, v in ADAPTER.items() if k != "target_modules"}},
            "secondary": {
                "adapter": {k: v for k, v in ADAPTER.items() if k not in {"rank", "alpha"}}
            },
        },
    )
    assert failures(LoraConfigCompleteRule().check(ctx))


def test_any_single_complete_adapter_is_sufficient(tmp_path: Path) -> None:
    ctx = context(
        tmp_path,
        training={"method": "lora"},
        models={"primary": {}, "secondary": {"adapter": ADAPTER}},
    )
    assert not failures(LoraConfigCompleteRule().check(ctx))
    empty_targets = context(
        tmp_path,
        training={"method": "lora"},
        models={"primary": {"adapter": {**ADAPTER, "target_modules": []}}},
    )
    assert not failures(LoraConfigCompleteRule().check(empty_targets))


def test_lora_with_no_adapter_fails(tmp_path: Path) -> None:
    ctx = context(tmp_path, training={"method": "lora"})
    assert failures(LoraConfigCompleteRule().check(ctx))[0].severity == Severity.CRITICAL


def test_training_profile_selection(tmp_path: Path) -> None:
    assert {
        "train.method_declared",
        "train.hyperparameters_declared",
        "train.optimizer_declared",
        "train.precision_declared",
        "train.lora_config_complete",
    } <= set(resolve(["finetuning"], tmp_path).rules)
