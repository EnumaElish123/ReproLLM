"""M3-T01: model identity declarations, API exclusions and detection hints."""

from pathlib import Path

import pytest

from reprollm.core.context import AuditContext
from reprollm.core.engine import run_audit
from reprollm.core.yaml_io import dump_yaml
from reprollm.profiles.loader import resolve
from reprollm.rules.model import (
    AdapterDeclaredRule,
    DtypeDeclaredRule,
    PrimaryDeclaredRule,
    ProviderKnownRule,
    QuantizationDeclaredRule,
    TrustRemoteCodeDeclaredRule,
)
from reprollm.schemas.finding import DetectionHints, FindingStatus, Severity
from tests.conftest import materialize_repo
from tests.unit.rules.helpers import context, failures

RULES = (
    PrimaryDeclaredRule,
    ProviderKnownRule,
    DtypeDeclaredRule,
    QuantizationDeclaredRule,
    AdapterDeclaredRule,
    TrustRemoteCodeDeclaredRule,
)


@pytest.mark.parametrize("rule_type", RULES)
def test_no_manifest_is_not_applicable(tmp_path: Path, rule_type) -> None:
    rule = rule_type()
    assert rule.min_level == 1
    assert not rule.applies(AuditContext(tmp_path))


@pytest.mark.parametrize("models", [{}, {"judge": {"id": "judge"}}, {"primary": {}}])
def test_primary_id_missing(tmp_path: Path, models: dict) -> None:
    result = failures(PrimaryDeclaredRule().check(context(tmp_path, models=models)))
    assert len(result) == 1
    assert result[0].severity == Severity.CRITICAL
    assert result[0].evidence[0].field == "models.primary.id"
    assert "models.primary.id" in result[0].fix_hint


def test_primary_id_present(tmp_path: Path) -> None:
    assert not failures(
        PrimaryDeclaredRule().check(context(tmp_path, models={"primary": {"id": "org/model"}}))
    )


def test_provider_checked_for_each_role_in_sorted_order(tmp_path: Path) -> None:
    ctx = context(
        tmp_path,
        models={
            "z_judge": {"provider": "other"},
            "primary": {"provider": "huggingface"},
            "attacker": {"provider": "other"},
        },
    )
    result = ProviderKnownRule().check(ctx)
    assert [f.evidence[0].field for f in result] == [
        "models.attacker.provider",
        "models.primary.provider",
        "models.z_judge.provider",
    ]
    assert [f.status for f in result] == [
        FindingStatus.FAIL,
        FindingStatus.PASS,
        FindingStatus.FAIL,
    ]
    assert all(f.severity == Severity.WARNING for f in failures(result))
    assert all(f.evidence[0].field in f.message for f in result)


@pytest.mark.parametrize("provider", ["huggingface", "openai", "openrouter", "anthropic", "local"])
def test_known_provider_passes(tmp_path: Path, provider: str) -> None:
    ctx = context(tmp_path, models={"primary": {"provider": provider, "id": "model"}})
    assert not failures(ProviderKnownRule().check(ctx))


def test_provider_evidence_distinguishes_unknown_from_undeclared(tmp_path: Path) -> None:
    ctx = context(tmp_path, models={"primary": {"provider": "other"}, "judge": {}})
    result = ProviderKnownRule().check(ctx)
    assert result[0].status == FindingStatus.SKIPPED
    assert "not declared" in result[0].message
    assert result[1].status == FindingStatus.FAIL
    assert result[1].evidence[0].note == "unsupported provider"


@pytest.mark.parametrize(
    "rule_type,field,severity",
    [
        (DtypeDeclaredRule, "dtype", Severity.WARNING),
        (QuantizationDeclaredRule, "quantization", Severity.INFO),
    ],
)
def test_model_field_missing_and_declared(tmp_path: Path, rule_type, field, severity) -> None:
    missing = context(tmp_path, models={"primary": {"provider": "huggingface"}})
    result = failures(rule_type().check(missing))
    assert len(result) == 1
    assert result[0].severity == severity
    assert result[0].evidence[0].field == f"models.primary.{field}"
    present = context(tmp_path, models={"primary": {"provider": "huggingface", field: "none"}})
    assert not failures(rule_type().check(present))


@pytest.mark.parametrize(
    "rule_type,field", [(DtypeDeclaredRule, "dtype"), (QuantizationDeclaredRule, "quantization")]
)
def test_inference_fallback_records_source(tmp_path: Path, rule_type, field) -> None:
    ctx = context(
        tmp_path,
        models={"primary": {"provider": "huggingface"}},
        inference={"backend": "transformers", field: "none"},
    )
    result = rule_type().check(ctx)
    assert len(result) == 1 and result[0].status == FindingStatus.PASS
    assert f"inference.{field}" in [e.field for e in result[0].evidence]


@pytest.mark.parametrize("rule_type", [DtypeDeclaredRule, QuantizationDeclaredRule])
@pytest.mark.parametrize("provider", ["openai", "openrouter", "anthropic"])
def test_api_role_skipped_without_hiding_missing_hf_role(
    tmp_path: Path, rule_type, provider
) -> None:
    ctx = context(
        tmp_path, models={"judge": {"provider": provider}, "primary": {"provider": "huggingface"}}
    )
    result = rule_type().check(ctx)
    assert result[0].status == FindingStatus.SKIPPED
    assert "judge" in result[0].message
    assert result[1].status == FindingStatus.FAIL
    assert "primary" in result[1].message


def test_adapter_only_required_when_detected(tmp_path: Path) -> None:
    rule = AdapterDeclaredRule()
    assert not rule.applies(context(tmp_path))
    ctx = context(tmp_path, hints=DetectionHints(adapter=True), models={"primary": {}})
    assert rule.applies(ctx)
    assert failures(rule.check(ctx))[0].severity == Severity.WARNING
    present = context(
        tmp_path,
        hints=DetectionHints(adapter=True),
        models={"judge": {"adapter": {"provider": "peft", "id": "org/adapter", "type": "lora"}}},
    )
    assert not failures(rule.check(present))


def test_trust_remote_code_requires_explicit_boolean(tmp_path: Path) -> None:
    rule = TrustRemoteCodeDeclaredRule()
    assert not rule.applies(context(tmp_path))
    ctx = context(
        tmp_path,
        hints=DetectionHints(trust_remote_code=True),
        models={"primary": {}},
    )
    assert rule.applies(ctx)
    result = failures(rule.check(ctx))
    assert len(result) == 1
    assert result[0].evidence[0].field == "models.primary.trust_remote_code"
    assert result[0].severity == Severity.WARNING
    for value in (False, True):
        present = context(
            tmp_path,
            hints=DetectionHints(trust_remote_code=True),
            models={"judge": {"trust_remote_code": value}},
        )
        assert not failures(rule.check(present))


def test_model_rules_selected_by_profiles(tmp_path: Path) -> None:
    core = resolve([], tmp_path).rules
    assert {
        "model.primary_declared",
        "model.provider_known",
        "model.dtype_declared",
        "model.trust_remote_code_declared",
    } <= set(core)
    assert "model.quantization_declared" in resolve(["inference"], tmp_path).rules
    assert "model.adapter_declared" in resolve(["finetuning"], tmp_path).rules


def test_privacy_fixture_trust_gap_and_complete(tmp_path: Path) -> None:
    repo = materialize_repo("privacy_custom_params", tmp_path)
    data = {
        "schema_version": 1,
        "project": {"name": "privacy"},
        "experiment": {"profiles": ["privacy"]},
        "models": {"primary": {"provider": "huggingface", "id": "org/model"}},
    }
    for value, expected in [
        (None, FindingStatus.FAIL),
        (False, FindingStatus.PASS),
        (True, FindingStatus.PASS),
    ]:
        if value is None:
            data["models"]["primary"].pop("trust_remote_code", None)
        else:
            data["models"]["primary"]["trust_remote_code"] = value
        (repo / "reprollm.yaml").write_text(dump_yaml(data), encoding="utf-8")
        report = run_audit(repo)
        result = [f for f in report.findings if f.rule_id == "model.trust_remote_code_declared"]
        assert len(result) == 1 and result[0].status == expected
    assert not any(f.rule_id.startswith("model.") for f in run_audit(repo, level=0).findings)
