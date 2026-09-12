"""M3-T04: judge role defaults and explicit judge sampling configuration."""

from pathlib import Path

import pytest

from reprollm.core.context import AuditContext
from reprollm.core.engine import run_audit
from reprollm.core.yaml_io import dump_yaml
from reprollm.profiles.loader import resolve
from reprollm.rules.judge import (
    ModelDeclaredRule,
    ParamsDeclaredRule,
    PromptDeclaredRule,
    RepetitionsDeclaredRule,
)
from reprollm.schemas.finding import FindingStatus, Severity
from tests.conftest import materialize_repo
from tests.unit.rules.helpers import context, failures


@pytest.mark.parametrize(
    "rule_type",
    [ModelDeclaredRule, ParamsDeclaredRule, PromptDeclaredRule, RepetitionsDeclaredRule],
)
def test_no_manifest_skips_judge(tmp_path: Path, rule_type) -> None:
    assert rule_type.min_level == 1
    assert not rule_type().applies(AuditContext(tmp_path))


@pytest.mark.parametrize(
    "rule_type,field", [(ModelDeclaredRule, "models.judge"), (PromptDeclaredRule, "prompts.judge")]
)
def test_missing_judge_block_still_requires_default_role(
    tmp_path: Path, rule_type, field: str
) -> None:
    ctx = context(tmp_path, models={"primary": {"id": "primary"}}, prompts={"system": {"text": ""}})
    result = failures(rule_type().check(ctx))
    assert len(result) == 1 and result[0].severity == Severity.CRITICAL
    assert result[0].evidence[0].field == field
    assert field in result[0].message


def test_default_judge_roles_present_without_judge_block(tmp_path: Path) -> None:
    ctx = context(tmp_path, models={"judge": {}}, prompts={"judge": {"text": ""}})
    assert not failures(ModelDeclaredRule().check(ctx))
    assert not failures(PromptDeclaredRule().check(ctx))


def test_custom_judge_references_are_used(tmp_path: Path) -> None:
    ctx = context(
        tmp_path,
        models={"grader": {"id": "model"}},
        prompts={"rubric": {"text": ""}},
        evaluation={"judge": {"model_ref": "grader", "prompt_ref": "rubric"}},
    )
    model = ModelDeclaredRule().check(ctx)[0]
    prompt = PromptDeclaredRule().check(ctx)[0]
    assert model.status == prompt.status == FindingStatus.PASS
    assert model.evidence[0].field == "models.grader"
    assert prompt.evidence[0].field == "prompts.rubric"


@pytest.mark.parametrize("params", [{}, {"temperature": 0}, {"max_tokens": 1}])
def test_judge_params_require_temperature_and_max_tokens(tmp_path: Path, params: dict) -> None:
    ctx = context(
        tmp_path,
        models={"judge": {}},
        prompts={"judge": {"text": ""}},
        generation={"temperature": 0, "max_tokens": 1},
        evaluation={"judge": {"params": params}},
    )
    result = failures(ParamsDeclaredRule().check(ctx))
    assert len(result) == 1 and result[0].severity == Severity.CRITICAL
    assert {e.field for e in result[0].evidence} == {
        "evaluation.judge.params." + key
        for key in ("temperature", "max_tokens")
        if key not in params
    }


def test_judge_params_zero_temperature_passes(tmp_path: Path) -> None:
    ctx = context(
        tmp_path,
        models={"judge": {}},
        prompts={"judge": {"text": ""}},
        evaluation={"judge": {"params": {"temperature": 0, "max_tokens": 1}}},
    )
    assert not failures(ParamsDeclaredRule().check(ctx))


def test_judge_repetitions_are_separate_from_evaluation_repetitions(tmp_path: Path) -> None:
    ctx = context(tmp_path, evaluation={"repetitions": 3})
    result = failures(RepetitionsDeclaredRule().check(ctx))
    assert result[0].severity == Severity.WARNING
    assert result[0].evidence[0].field == "evaluation.judge.repetitions"
    full = context(
        tmp_path,
        models={"judge": {}},
        prompts={"judge": {"text": ""}},
        evaluation={"judge": {"repetitions": 0}},
    )
    assert not failures(RepetitionsDeclaredRule().check(full))


def test_openai_fixture_judge_gap_and_complete(tmp_path: Path) -> None:
    repo = materialize_repo("openai_judge_eval", tmp_path)
    data = {
        "project": {"name": "judge"},
        "experiment": {"profiles": ["llm_judge"]},
        "models": {
            "primary": {"provider": "openai", "id": "primary"},
            "judge": {"provider": "openai", "id": "judge"},
        },
        "prompts": {"judge": {"path": "prompts/judge.txt"}},
    }
    (repo / "reprollm.yaml").write_text(dump_yaml(data), encoding="utf-8")
    result = [f for f in run_audit(repo).findings if f.rule_id == "judge.params_declared"]
    assert result[0].status == FindingStatus.FAIL and result[0].severity == Severity.CRITICAL
    data["evaluation"] = {
        "judge": {"params": {"temperature": 0, "max_tokens": 16}, "repetitions": 1}
    }
    (repo / "reprollm.yaml").write_text(dump_yaml(data), encoding="utf-8")
    report = run_audit(repo)
    assert not failures([f for f in report.findings if f.rule_id.startswith("judge.")])
    assert all(
        f.status == FindingStatus.SKIPPED
        for f in report.findings
        if f.rule_id == "model.dtype_declared"
    )
    assert {
        "judge.model_declared",
        "judge.prompt_declared",
        "judge.params_declared",
        "judge.repetitions_declared",
    } <= set(resolve(["llm_judge"], repo).rules)
