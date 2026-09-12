"""M3-T04: evaluation declarations and safe metric file references."""

from pathlib import Path

import pytest

from reprollm.core.context import AuditContext
from reprollm.profiles.loader import resolve
from reprollm.rules.eval_ import (
    AggregationDeclaredRule,
    DefinitionsDeclaredRule,
    MetricImplementationReferencedRule,
    MetricsDeclaredRule,
    QueryBudgetDeclaredRule,
    RepetitionsDeclaredRule,
)
from reprollm.schemas.finding import FindingStatus, Severity
from tests.unit.rules.helpers import context, failures


@pytest.mark.parametrize(
    "rule_type",
    [
        AggregationDeclaredRule,
        DefinitionsDeclaredRule,
        MetricImplementationReferencedRule,
        MetricsDeclaredRule,
        QueryBudgetDeclaredRule,
        RepetitionsDeclaredRule,
    ],
)
def test_no_manifest_skips_eval(tmp_path: Path, rule_type) -> None:
    assert rule_type.min_level == 1
    assert not rule_type().applies(AuditContext(tmp_path))


@pytest.mark.parametrize("evaluation", [None, {}, {"metrics": []}])
def test_metrics_missing(tmp_path: Path, evaluation) -> None:
    result = failures(MetricsDeclaredRule().check(context(tmp_path, evaluation=evaluation)))
    assert len(result) == 1 and result[0].severity == Severity.WARNING
    assert result[0].evidence[0].field == "evaluation.metrics"


def test_metrics_present(tmp_path: Path) -> None:
    assert not failures(
        MetricsDeclaredRule().check(
            context(tmp_path, evaluation={"metrics": [{"name": "accuracy"}]})
        )
    )


@pytest.mark.parametrize(
    "rule_type",
    [MetricImplementationReferencedRule, AggregationDeclaredRule, RepetitionsDeclaredRule],
)
@pytest.mark.parametrize("evaluation", [None, {}])
def test_metric_dependents_skip_when_no_metrics(tmp_path: Path, rule_type, evaluation) -> None:
    assert not rule_type().applies(context(tmp_path, evaluation=evaluation))


def test_metric_implementation_missing_and_reference_missing_differ(tmp_path: Path) -> None:
    ctx = context(
        tmp_path,
        evaluation={
            "metrics": [
                {"name": "accuracy"},
                {"name": "accuracy", "implementation": "metrics/missing.py"},
            ]
        },
    )
    result = MetricImplementationReferencedRule().check(ctx)
    assert len(failures(result)) == 2
    assert result[0].evidence[0].field == "evaluation.metrics.0.implementation"
    assert result[0].evidence[0].note == "absent"
    assert result[1].evidence[0].field == "evaluation.metrics.1.implementation"
    assert result[1].evidence[0].note == "referenced file missing"
    assert result[0].message != result[1].message
    assert any(e.path == "metrics/missing.py" for e in result[1].evidence)


@pytest.mark.parametrize(
    "implementation", ["evaluate==0.4.0", "metric-package==1.2.3", "pkg==1.0rc1"]
)
def test_package_reference_is_declaration_only(tmp_path: Path, implementation: str) -> None:
    ctx = context(
        tmp_path, evaluation={"metrics": [{"name": "accuracy", "implementation": implementation}]}
    )
    result = MetricImplementationReferencedRule().check(ctx)
    assert len(result) == 1 and result[0].status == FindingStatus.PASS
    assert result[0].evidence[0].note == "package reference declared"


@pytest.mark.parametrize("name", ["metric.py", "metric", "pkg==1.0"])
def test_relative_file_reference_exists(tmp_path: Path, name: str) -> None:
    (tmp_path / name).write_text("do not execute this file", encoding="utf-8")
    ctx = context(tmp_path, evaluation={"metrics": [{"name": "metric", "implementation": name}]})
    result = MetricImplementationReferencedRule().check(ctx)
    assert result[0].status == FindingStatus.PASS
    assert any(e.path == name for e in result[0].evidence)


def test_directory_does_not_satisfy_metric_file_reference(tmp_path: Path) -> None:
    (tmp_path / "metrics").mkdir()
    ctx = context(
        tmp_path, evaluation={"metrics": [{"name": "metric", "implementation": "metrics"}]}
    )
    assert failures(MetricImplementationReferencedRule().check(ctx))


@pytest.mark.parametrize("reference", ["metric", "pkg==invalid-version", "pkg==1.*"])
def test_only_valid_package_pins_bypass_missing_file_check(tmp_path: Path, reference: str) -> None:
    ctx = context(
        tmp_path, evaluation={"metrics": [{"name": "metric", "implementation": reference}]}
    )
    result = failures(MetricImplementationReferencedRule().check(ctx))
    assert len(result) == 1
    assert result[0].evidence[0].note == "referenced file missing"


@pytest.mark.parametrize(
    "unsafe",
    [
        "/home/private/metric.py",
        "../metric.py",
        r"C:\private\metric.py",
        "https://user:password@example.invalid/metric.py",
    ],
)
def test_unsafe_metric_reference_does_not_leak_into_findings(tmp_path: Path, unsafe: str) -> None:
    ctx = context(tmp_path, evaluation={"metrics": [{"name": unsafe, "implementation": unsafe}]})
    result = MetricImplementationReferencedRule().check(ctx)
    assert len(failures(result)) == 1
    assert all(e.path is None for e in result[0].evidence)
    assert unsafe not in result[0].model_dump_json()
    assert "private" not in result[0].model_dump_json()


@pytest.mark.parametrize(
    "rule_type,field,value",
    [(AggregationDeclaredRule, "aggregation", "mean"), (RepetitionsDeclaredRule, "repetitions", 0)],
)
def test_metric_metadata_missing_and_present(tmp_path: Path, rule_type, field, value) -> None:
    ctx = context(tmp_path, evaluation={"metrics": [{"name": "accuracy"}]})
    assert rule_type().applies(ctx)
    result = failures(rule_type().check(ctx))
    assert result[0].evidence[0].field == f"evaluation.{field}"
    assert result[0].severity == Severity.WARNING
    full = context(tmp_path, evaluation={"metrics": [{"name": "accuracy"}], field: value})
    assert not failures(rule_type().check(full))


@pytest.mark.parametrize(
    "definitions,passes",
    [
        (None, False),
        ({}, False),
        ({"utility": "x"}, False),
        ({"refusal": "x"}, True),
        ({"asr": "x"}, True),
    ],
)
def test_safety_definitions_require_refusal_or_asr(
    tmp_path: Path, definitions, passes: bool
) -> None:
    ctx = context(tmp_path, evaluation={"definitions": definitions})
    assert (not failures(DefinitionsDeclaredRule().check(ctx))) is passes


def test_query_budget_zero_is_declared(tmp_path: Path) -> None:
    assert (
        failures(QueryBudgetDeclaredRule().check(context(tmp_path)))[0].severity == Severity.WARNING
    )
    assert not failures(
        QueryBudgetDeclaredRule().check(context(tmp_path, evaluation={"query_budget": 0}))
    )


def test_eval_profile_selection(tmp_path: Path) -> None:
    assert {
        "eval.metrics_declared",
        "eval.metric_implementation_referenced",
        "eval.aggregation_declared",
        "eval.repetitions_declared",
    } <= set(resolve(["evaluation"], tmp_path).rules)
    assert {"eval.definitions_declared", "eval.query_budget_declared"} <= set(
        resolve(["safety"], tmp_path).rules
    )
