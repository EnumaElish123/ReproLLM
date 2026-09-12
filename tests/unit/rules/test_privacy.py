"""M3-T05: privacy declarations and scoped attack configuration."""

from pathlib import Path

import pytest

from reprollm.core.context import AuditContext
from reprollm.core.engine import run_audit
from reprollm.core.yaml_io import dump_yaml
from reprollm.profiles.loader import resolve
from reprollm.rules.privacy import (
    AttackConfigDeclaredRule,
    MechanismDeclaredRule,
    MetricsDeclaredRule,
    ThreatModelDeclaredRule,
)
from reprollm.schemas.finding import FindingStatus, Severity
from tests.conftest import materialize_repo
from tests.unit.rules.helpers import context, failures


@pytest.mark.parametrize(
    "rule_type",
    [AttackConfigDeclaredRule, MechanismDeclaredRule, MetricsDeclaredRule, ThreatModelDeclaredRule],
)
def test_no_manifest_skips_privacy(tmp_path: Path, rule_type) -> None:
    assert rule_type.min_level == 1
    assert not rule_type().applies(AuditContext(tmp_path))


def test_threat_model_presence(tmp_path: Path) -> None:
    result = failures(ThreatModelDeclaredRule().check(context(tmp_path)))
    assert result[0].severity == Severity.CRITICAL
    assert result[0].evidence[0].field == "privacy.threat_model"
    ctx = context(tmp_path, privacy={"threat_model": "black-box membership inference"})
    assert not failures(ThreatModelDeclaredRule().check(ctx))


@pytest.mark.parametrize(
    "privacy",
    [None, {}, {"mechanism": {"name": "dp"}}, {"mechanism": {"name": "dp", "params": {}}}],
)
def test_mechanism_needs_nonempty_parameters(tmp_path: Path, privacy) -> None:
    result = failures(MechanismDeclaredRule().check(context(tmp_path, privacy=privacy)))
    assert len(result) == 1 and result[0].severity == Severity.CRITICAL
    assert "privacy.mechanism.params" in [e.field for e in result[0].evidence]


def test_mechanism_zero_parameter_is_preserved_without_emitting_values(tmp_path: Path) -> None:
    ctx = context(tmp_path, privacy={"mechanism": {"name": "dp", "params": {"epsilon": 0}}})
    assert not failures(MechanismDeclaredRule().check(ctx))


@pytest.mark.parametrize("metrics", [None, []])
def test_empty_privacy_metrics_fail(tmp_path: Path, metrics) -> None:
    result = failures(MetricsDeclaredRule().check(context(tmp_path, privacy={"metrics": metrics})))
    assert result[0].severity == Severity.WARNING


def test_privacy_metrics_declared(tmp_path: Path) -> None:
    ctx = context(tmp_path, privacy={"metrics": ["epsilon", "utility"]})
    assert not failures(MetricsDeclaredRule().check(ctx))


@pytest.mark.parametrize("privacy", [None, {}, {"attack": None}])
def test_absent_attack_is_not_applicable(tmp_path: Path, privacy) -> None:
    assert not AttackConfigDeclaredRule().applies(context(tmp_path, privacy=privacy))


@pytest.mark.parametrize("attack", [{}, {"method": "mia"}, {"query_budget": 0}])
def test_declared_attack_needs_own_method_and_query_budget(tmp_path: Path, attack: dict) -> None:
    ctx = context(tmp_path, privacy={"attack": attack}, evaluation={"query_budget": 100})
    rule = AttackConfigDeclaredRule()
    assert rule.applies(ctx)
    result = failures(rule.check(ctx))
    assert len(result) == 1 and result[0].severity == Severity.WARNING
    assert {e.field for e in result[0].evidence} == {
        "privacy.attack." + key for key in ("method", "query_budget") if key not in attack
    }


def test_attack_zero_budget_passes_without_params_requirement(tmp_path: Path) -> None:
    ctx = context(tmp_path, privacy={"attack": {"method": "mia", "query_budget": 0}})
    assert not failures(AttackConfigDeclaredRule().check(ctx))


def test_privacy_fixture_gap_and_complete(tmp_path: Path) -> None:
    repo = materialize_repo("privacy_custom_params", tmp_path)
    data = {
        "project": {"name": "privacy"},
        "experiment": {"profiles": ["privacy"]},
        "privacy": {
            "threat_model": "black-box",
            "mechanism": {"name": "dp", "params": {}},
            "metrics": ["epsilon"],
            "attack": {"method": "mia", "query_budget": 100},
        },
    }
    (repo / "reprollm.yaml").write_text(dump_yaml(data), encoding="utf-8")
    result = [f for f in run_audit(repo).findings if f.rule_id == "privacy.mechanism_declared"]
    assert result[0].status == FindingStatus.FAIL and result[0].severity == Severity.CRITICAL
    data["privacy"]["mechanism"]["params"] = {"epsilon": 0}
    (repo / "reprollm.yaml").write_text(dump_yaml(data), encoding="utf-8")
    assert not failures([f for f in run_audit(repo).findings if f.rule_id.startswith("privacy.")])
    assert {
        "privacy.threat_model_declared",
        "privacy.mechanism_declared",
        "privacy.metrics_declared",
        "privacy.attack_config_declared",
    } <= set(resolve(["privacy"], repo).rules)
