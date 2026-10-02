"""UX-T06: only the explicit shipped judge-only policy relaxes primary intent."""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.core.context import AuditContext
from reprollm.core.engine import run_audit
from reprollm.core.manifest_scaffold import parse_scalar, plan_init, render_manifest
from reprollm.core.yaml_io import dump_yaml, load_manifest
from reprollm.profiles.loader import load_builtin, resolve, user_profile_path
from reprollm.rules.judge import ModelDeclaredRule, PromptDeclaredRule
from reprollm.rules.model import PrimaryDeclaredRule
from reprollm.schemas.finding import FindingStatus, Severity
from reprollm.schemas.manifest import Manifest
from tests.conftest import materialize_repo
from tests.unit.profiles.test_builtin_catalog import OVERRIDES, OWN_RULES
from tests.unit.rules.helpers import context

FIXTURES = Path(__file__).parents[2] / "fixtures" / "judge_only"
JUDGE_FIELDS = [
    "datasets.eval.id",
    "evaluation.metrics",
    "models.judge.id",
    "prompts.judge.path",
    "evaluation.judge.params.temperature",
    "evaluation.judge.params.max_tokens",
]
LEVEL2_RULES = {
    "model.revision_pinned",
    "model.tokenizer_pinned",
    "dataset.revision_pinned",
    "dataset.local_files_hashed",
    "prompt.hashed",
    "gen.backend_version_locked",
    "consistency.lock_fresh",
    "consistency.file_hashes",
    "consistency.generation_params",
    "consistency.model_identity",
    "consistency.env_vs_lock",
    "consistency.custom_fields",
    "judge.prompt_hashed",
    "judge.pinnability_recorded",
}


def _override(root: Path, name: str) -> None:
    profile = load_builtin(name) if name != "custom" else load_builtin("privacy")
    profile.name = name
    path = user_profile_path(root, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_yaml(profile), encoding="utf-8")


def _context(root: Path, profiles: list[str], **fields) -> AuditContext:
    ctx = context(root, experiment={"profiles": profiles}, **fields)
    ctx.declared_profiles = profiles
    ctx.resolved_profiles = resolve(profiles, root).names
    return ctx


def _fixture_repo(tmp_path: Path, name: str) -> Path:
    root = materialize_repo("openai_judge_eval", tmp_path)
    (root / "reprollm.yaml").write_text((FIXTURES / name).read_text(), encoding="utf-8")
    return root


def test_exact_judge_only_policy_and_core_rule_closure(tmp_path: Path) -> None:
    profile = load_builtin("judge_only")
    selected = resolve(["judge_only"], tmp_path)
    assert profile.extends == ["core"]
    assert profile.required_fields == JUDGE_FIELDS
    assert selected.names == ["core", "judge_only"]
    assert set(selected.rules) == OWN_RULES["core"] | OWN_RULES["judge_only"]
    assert selected.severity_overrides == OVERRIDES["judge_only"]
    assert selected.required_fields == ["project.name", "models.primary.id", *JUDGE_FIELDS]
    assert profile.detect.model_dump() == {
        "imports": [],
        "dependencies": [],
        "keywords": [],
        "files": [],
    }
    assert selected.drift_overrides == {"evaluation.judge.*": "HIGH"}


def test_complete_fixture_has_no_unrelated_critical_and_keeps_all_selected_rules(
    tmp_path: Path,
) -> None:
    root = _fixture_repo(tmp_path, "complete.yaml")
    manifest = load_manifest(root / "reprollm.yaml")
    assert "primary" not in manifest.models
    assert manifest.generation is None and manifest.inference is None
    report = run_audit(root)
    assert {f.rule_id for f in report.findings} == (
        OWN_RULES["core"] | OWN_RULES["judge_only"]
    ) - LEVEL2_RULES
    assert not [f for f in report.findings if f.severity == Severity.CRITICAL]
    (primary,) = [f for f in report.findings if f.rule_id == "model.primary_declared"]
    assert primary.status == FindingStatus.SKIPPED
    assert all(
        f.status == FindingStatus.PASS
        for f in report.findings
        if f.rule_id
        in {
            "judge.model_declared",
            "judge.prompt_declared",
            "judge.params_declared",
            "dataset.declared",
            "eval.metrics_declared",
            "exec.seed_declared",
        }
    )


def test_negative_fixture_has_exact_intent_critical_set(tmp_path: Path) -> None:
    root = _fixture_repo(tmp_path, "missing_intent.yaml")
    report = run_audit(root)
    assert {f.rule_id for f in report.findings} == (
        OWN_RULES["core"] | OWN_RULES["judge_only"]
    ) - LEVEL2_RULES
    assert {f.rule_id for f in report.findings if f.severity == Severity.CRITICAL} == {
        "judge.model_declared",
        "judge.prompt_declared",
        "judge.params_declared",
        "dataset.declared",
        "eval.metrics_declared",
        "exec.seed_declared",
    }


@pytest.mark.parametrize("profiles", [["judge_only"], ["judge_only", "privacy"]])
def test_primary_skips_only_explicit_shipped_judge_only_closure(
    tmp_path: Path, profiles: list[str]
) -> None:
    (finding,) = PrimaryDeclaredRule().check(_context(tmp_path, profiles))
    assert finding.status == FindingStatus.SKIPPED
    assert "judge_only" in finding.message


@pytest.mark.parametrize(
    "extra", ["inference", "evaluation", "llm_judge", "safety", "finetuning", "custom"]
)
def test_composition_restores_primary_and_existing_task_rules(tmp_path: Path, extra: str) -> None:
    if extra == "custom":
        _override(tmp_path, extra)
    ctx = _context(tmp_path, ["judge_only", extra])
    (primary,) = PrimaryDeclaredRule().check(ctx)
    assert primary.status == FindingStatus.FAIL and primary.severity == Severity.CRITICAL
    rules = set(resolve(ctx.declared_profiles, tmp_path).rules)
    assert ("gen.params_declared" in rules) == (
        extra in {"inference", "evaluation", "llm_judge", "safety"}
    )
    assert ("train.hyperparameters_declared" in rules) == (extra == "finetuning")


@pytest.mark.parametrize("override", ["core", "judge_only", "privacy"])
def test_any_applicable_profile_override_prevents_exception(tmp_path: Path, override: str) -> None:
    _override(tmp_path, override)
    ctx = _context(tmp_path, ["judge_only", "privacy"])
    assert PrimaryDeclaredRule().check(ctx)[0].status == FindingStatus.FAIL
    plan = plan_init(tmp_path, profiles_override=ctx.declared_profiles)
    assert "models.primary.id" in plan.required_fields
    assert "primary" in yaml.safe_load(render_manifest(plan, {}))["models"]


def test_unrelated_override_does_not_prevent_the_exact_exception(tmp_path: Path) -> None:
    _override(tmp_path, "inference")
    ctx = _context(tmp_path, ["judge_only"])
    assert PrimaryDeclaredRule().check(ctx)[0].status == FindingStatus.SKIPPED


def test_inherited_or_unresolved_judge_only_is_not_explicit_opt_in(tmp_path: Path) -> None:
    ctx = context(tmp_path, experiment={"profiles": []})
    ctx.declared_profiles = ["custom"]
    ctx.resolved_profiles = ["core", "judge_only"]
    assert PrimaryDeclaredRule().check(ctx)[0].status == FindingStatus.FAIL
    ctx.declared_profiles = ["judge_only"]
    ctx.resolved_profiles = []
    assert PrimaryDeclaredRule().check(ctx)[0].status == FindingStatus.FAIL


@pytest.mark.parametrize(
    "profiles",
    [[], ["inference"], ["evaluation"], ["llm_judge"], ["finetuning"], ["privacy"], ["safety"]],
)
def test_existing_profiles_keep_primary_and_released_empty_judge_role_behavior(
    tmp_path: Path, profiles: list[str]
) -> None:
    ctx = _context(tmp_path, profiles, models={"judge": {}}, prompts={"judge": {}})
    assert PrimaryDeclaredRule().check(ctx)[0].status == FindingStatus.FAIL
    assert ModelDeclaredRule().check(ctx)[0].status == FindingStatus.PASS
    assert PromptDeclaredRule().check(ctx)[0].status == FindingStatus.PASS


@pytest.mark.parametrize("model", [{}, {"id": None}, {"id": ""}, {"id": " \t "}])
def test_empty_referenced_model_id_is_critical_only_in_narrow_mode(
    tmp_path: Path, model: dict
) -> None:
    ctx = _context(
        tmp_path,
        ["judge_only"],
        models={"grader": model},
        prompts={"rubric": {"text": ""}},
        evaluation={"judge": {"model_ref": "grader", "prompt_ref": "rubric"}},
    )
    (finding,) = ModelDeclaredRule().check(ctx)
    assert finding.severity == Severity.CRITICAL
    assert finding.evidence[0].field == "models.grader.id"
    ctx.declared_profiles = ["judge_only", "inference"]
    ctx.resolved_profiles.append("inference")
    assert ModelDeclaredRule().check(ctx)[0].status == FindingStatus.PASS


@pytest.mark.parametrize(
    "prompt,present", [({}, False), ({"path": "prompts/judge.txt"}, True), ({"text": ""}, True)]
)
def test_scoped_prompt_declaration_distinguishes_missing_content_from_empty_inline(
    tmp_path: Path, prompt: dict, present: bool
) -> None:
    ctx = _context(
        tmp_path,
        ["judge_only"],
        models={"grader": {"id": "model"}},
        prompts={"rubric": prompt},
        evaluation={"judge": {"model_ref": "grader", "prompt_ref": "rubric"}},
    )
    assert ModelDeclaredRule().check(ctx)[0].status == FindingStatus.PASS
    (finding,) = PromptDeclaredRule().check(ctx)
    assert finding.status == (FindingStatus.PASS if present else FindingStatus.FAIL)
    if not present:
        assert finding.severity == Severity.CRITICAL
    assert finding.evidence[0].field == "prompts.rubric"


def test_absent_default_roles_still_fail_without_judge_block(tmp_path: Path) -> None:
    ctx = _context(tmp_path, ["judge_only"])
    assert ModelDeclaredRule().check(ctx)[0].severity == Severity.CRITICAL
    assert PromptDeclaredRule().check(ctx)[0].severity == Severity.CRITICAL


@pytest.mark.parametrize("profiles", [["judge_only"], ["judge_only", "privacy"]])
def test_init_omits_only_primary_field_and_keeps_unassigned_model_candidates(
    tmp_path: Path, profiles: list[str]
) -> None:
    root = materialize_repo("hf_vllm_eval", tmp_path)
    plan = plan_init(root, profiles_override=profiles)
    selected = resolve(profiles, root)
    assert plan.required_fields == [
        field for field in selected.required_fields if field != "models.primary.id"
    ]
    assert plan.primary_detection is None
    assert plan.detection.hints.hf_ids
    text = render_manifest(plan, {})
    data = yaml.safe_load(text)
    assert set(data["models"]) == {"judge"}
    assert "generation" not in data and "inference" not in data
    assert "detected model candidate (unassigned): Qwen/Qwen3-32B" in text
    Manifest.model_validate(data)


@pytest.mark.parametrize("extra", ["inference", "finetuning", "custom"])
def test_init_compositions_keep_normal_required_union_and_primary_prefill(
    tmp_path: Path, extra: str
) -> None:
    root = materialize_repo("hf_vllm_eval", tmp_path)
    if extra == "custom":
        _override(root, extra)
    profiles = ["judge_only", extra]
    plan = plan_init(root, profiles_override=profiles)
    assert plan.required_fields == resolve(profiles, root).required_fields
    data = yaml.safe_load(render_manifest(plan, {}))
    assert data["models"]["primary"]["id"] == "Qwen/Qwen3-32B"


def test_detection_never_selects_judge_only(tmp_path: Path) -> None:
    root = materialize_repo("openai_judge_eval", tmp_path)
    (root / "README.md").write_text(
        "judge_only judging stored outputs llm-as-a-judge rubric", encoding="utf-8"
    )
    plan = plan_init(root, profiles_override=None)
    assert "judge_only" not in plan.profiles
    assert "judge_only" not in [item.profile for item in plan.detection.profiles]
    assert "models.primary.id" in plan.required_fields


def test_cli_profiles_override_is_an_explicit_judge_only_selection(tmp_path: Path) -> None:
    root = _fixture_repo(tmp_path, "complete.yaml")
    document = load_manifest(root / "reprollm.yaml")
    document.experiment.profiles = ["llm_judge"]
    (root / "reprollm.yaml").write_text(dump_yaml(document), encoding="utf-8")
    normal = run_audit(root)
    explicit = run_audit(root, profile_names=["judge_only"])
    assert (
        next(f for f in normal.findings if f.rule_id == "model.primary_declared").status
        == FindingStatus.FAIL
    )
    assert (
        next(f for f in explicit.findings if f.rule_id == "model.primary_declared").status
        == FindingStatus.SKIPPED
    )
    assert "gen.params_declared" not in {f.rule_id for f in explicit.findings}


def test_interactive_judge_max_tokens_is_numeric_and_accepted(tmp_path: Path) -> None:
    assert parse_scalar("evaluation.judge.params.max_tokens", "256") == 256
    result = CliRunner().invoke(
        app,
        ["init", str(tmp_path), "--profiles", "judge_only", "--interactive"],
        input="\ndata/pairs.jsonl\nmodel-id\nprompts/judge.txt\n0\n256\n",
    )
    assert result.exit_code == 0, result.output
    manifest = load_manifest(tmp_path / "reprollm.yaml")
    assert manifest.evaluation is not None and manifest.evaluation.judge is not None
    assert manifest.evaluation.judge.params.max_tokens == 256
    assert manifest.evaluation.judge.params.temperature == 0
    assert "primary" not in manifest.models


def test_existing_reference_and_numeric_validation_are_unchanged(tmp_path: Path) -> None:
    data = yaml.safe_load((FIXTURES / "complete.yaml").read_text())
    data["evaluation"]["judge"]["params"]["max_tokens"] = 0
    with pytest.raises(ValidationError):
        Manifest.model_validate(data)
    data["evaluation"]["judge"]["params"]["max_tokens"] = 1
    data["evaluation"]["judge"]["repetitions"] = 0
    assert Manifest.model_validate(data).evaluation.judge.repetitions == 0
    data["evaluation"]["judge"]["model_ref"] = "missing"
    with pytest.raises(ValidationError, match="model_ref"):
        Manifest.model_validate(data)
    data["evaluation"]["judge"]["model_ref"] = "judge"
    data["evaluation"]["judge"]["prompt_ref"] = "missing"
    with pytest.raises(ValidationError, match="prompt_ref"):
        Manifest.model_validate(data)


def test_profiles_show_explains_primary_applicability_and_field_intent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["profiles", "show", "judge_only"])
    assert result.exit_code == 0, result.output
    assert "chain:  judge_only → core" in result.output
    assert "model.primary_declared" in result.output
    assert "models.primary.id (not required for this shipped judge_only selection)" in result.output
    assert "evaluation.judge.params.max_tokens" in result.output
    assert "user profile overrides" in result.output
    _override(tmp_path, "core")
    result = CliRunner().invoke(app, ["profiles", "show", "judge_only"])
    assert "not required for this shipped judge_only selection" not in result.output
