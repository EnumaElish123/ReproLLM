"""Profile severity ownership and unfinished-rule boundaries (M3-T06)."""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.core import registry
from reprollm.core.context import AuditContext
from reprollm.core.engine import run_audit
from reprollm.core.errors import UserError
from reprollm.core.hashing import sha256_file
from reprollm.core.yaml_io import dump_yaml
from reprollm.profiles import loader
from reprollm.rules.gen import ParamsDeclaredRule
from reprollm.schemas.finding import Finding, FindingStatus, Severity
from reprollm.schemas.lock import Lock, ResolutionMode


def manifest(root: Path, profiles: list[str], **sections: object) -> None:
    (root / "reprollm.yaml").write_text(
        dump_yaml(
            {"project": {"name": "severity"}, "experiment": {"profiles": profiles}, **sections}
        ),
        encoding="utf-8",
    )


def profile(root: Path, name: str, parents: list[str], **fields: object) -> None:
    folder = root / ".reprollm" / "profiles"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}.yaml").write_text(
        dump_yaml({"name": name, "description": name, "extends": parents, **fields}),
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    ("selected", "severity", "origin"),
    [
        ("evaluation", Severity.CRITICAL, "profile:evaluation"),
        ("inference", Severity.WARNING, "default"),
    ],
)
def test_sampling_seed_severity_depends_on_profile(
    tmp_path: Path, selected: str, severity: Severity, origin: str
) -> None:
    manifest(tmp_path, [selected], generation={"temperature": 0.7})
    finding = next(f for f in run_audit(tmp_path).findings if f.rule_id == "gen.seed_declared")
    assert finding.status == FindingStatus.FAIL
    assert finding.severity == severity
    assert finding.severity_origin == origin


def test_override_replaces_rule_emitted_downgrade(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def downgraded(self: ParamsDeclaredRule, ctx: AuditContext) -> list[Finding]:
        return [self.finding(ctx, message="provider-specific case", severity=Severity.INFO)]

    monkeypatch.setattr(ParamsDeclaredRule, "check", downgraded)
    manifest(tmp_path, ["inference"])
    finding = next(f for f in run_audit(tmp_path).findings if f.rule_id == "gen.params_declared")
    assert (finding.severity, finding.severity_origin) == (Severity.CRITICAL, "profile:inference")
    profile(tmp_path, "plain", [], rules=["gen.params_declared"])
    finding = next(
        f
        for f in run_audit(tmp_path, profile_names=["plain"]).findings
        if f.rule_id == "gen.params_declared"
    )
    assert (finding.severity, finding.severity_origin) == (Severity.INFO, "default")


def test_override_does_not_relabel_pass_or_skipped(tmp_path: Path) -> None:
    manifest(
        tmp_path,
        ["evaluation"],
        generation={"temperature": 0, "top_p": 1, "max_tokens": 8},
    )
    findings = {f.rule_id: f for f in run_audit(tmp_path).findings}
    assert findings["gen.params_declared"].status == FindingStatus.PASS
    assert findings["gen.params_declared"].severity == Severity.PASS
    assert findings["gen.seed_declared"].status == FindingStatus.SKIPPED
    assert findings["gen.seed_declared"].severity == Severity.INFO


def test_project_owned_severity_is_not_replaced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def project_owned(self: ParamsDeclaredRule, ctx: AuditContext) -> list[Finding]:
        finding = self.finding(ctx, message="project-owned field", severity=Severity.WARNING)
        finding.severity_origin = "project_rule"
        return [finding]

    monkeypatch.setattr(ParamsDeclaredRule, "check", project_owned)
    manifest(tmp_path, ["inference"])
    finding = next(f for f in run_audit(tmp_path).findings if f.rule_id == "gen.params_declared")
    assert (finding.severity, finding.severity_origin) == (Severity.WARNING, "project_rule")


def test_override_origin_tracks_most_derived_profile(tmp_path: Path) -> None:
    profile(tmp_path, "parent", [], severity_overrides={"gen.seed_declared": "INFO"})
    profile(tmp_path, "child", ["parent"], severity_overrides={"gen.seed_declared": "WARNING"})
    resolved = loader.resolve(["child", "parent"], tmp_path)
    assert resolved.severity_overrides["gen.seed_declared"] == "WARNING"
    assert resolved.severity_origins["gen.seed_declared"] == "child"


def test_multiple_inheritance_uses_rightmost_parent_then_child(tmp_path: Path) -> None:
    profile(tmp_path, "left", [], severity_overrides={"gen.seed_declared": "INFO"})
    profile(tmp_path, "right", [], severity_overrides={"gen.seed_declared": "CRITICAL"})
    profile(tmp_path, "child", ["left", "right"])
    resolved = loader.resolve(["child"], tmp_path)
    assert resolved.severity_overrides["gen.seed_declared"] == "CRITICAL"
    assert resolved.severity_origins["gen.seed_declared"] == "right"


def test_alias_rule_and_override_resolve_to_one_canonical_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(registry._ALIASES, "gen.old_seed", "gen.seed_declared")
    profile(
        tmp_path,
        "alias",
        [],
        rules=["gen.old_seed", "gen.seed_declared"],
        severity_overrides={"gen.old_seed": "CRITICAL"},
    )
    resolved = loader.resolve(["alias"], tmp_path)
    assert resolved.rules.count("gen.seed_declared") == 1
    assert "gen.old_seed" not in resolved.rules
    assert resolved.severity_overrides["gen.seed_declared"] == "CRITICAL"
    assert resolved.severity_origins["gen.seed_declared"] == "alias"


def test_unknown_override_id_is_user_error(tmp_path: Path) -> None:
    profile(tmp_path, "broken", [], severity_overrides={"model.typo": "CRITICAL"})
    with pytest.raises(UserError, match="model.typo"):
        loader.resolve(["broken"], tmp_path)


def test_stubs_never_run_or_synthesize_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rule = registry.get_rule("model.revision_pinned")
    assert rule is not None

    def unexpected(*args: object) -> list[Finding]:
        pytest.fail("stub checks must never run")

    monkeypatch.setattr(rule, "check", unexpected)
    manifest(tmp_path, [])
    assert not any(f.rule_id == rule.id for f in run_audit(tmp_path).findings)
    lock = Lock(
        reprollm_version="0.1.1",
        generated_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        manifest_sha256=sha256_file(tmp_path / "reprollm.yaml"),
        resolution=ResolutionMode(mode="offline"),
    )
    (tmp_path / "reprollm.lock").write_text(dump_yaml(lock), encoding="utf-8")
    finding = next(f for f in run_audit(tmp_path).findings if f.rule_id == rule.id)
    assert finding.status == FindingStatus.SKIPPED
    assert finding.severity == Severity.INFO
    assert any(e.note == "not implemented yet" for e in finding.evidence)
    assert not any(f.rule_id == rule.id for f in run_audit(tmp_path, level=0).findings)


def test_show_core_and_override_columns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    core = runner.invoke(app, ["profiles", "show", "core"])
    assert core.exit_code == 0, core.output
    assert "model.revision_pinned" in core.output
    assert "(stub, arrives in 0.2.0)" in core.output
    custom_row = next(
        line for line in core.output.splitlines() if "consistency.custom_fields" in line
    )
    assert "(project rule)" in custom_row
    assert "INFO" not in custom_row
    evaluation = runner.invoke(app, ["profiles", "show", "evaluation"])
    assert evaluation.exit_code == 0, evaluation.output
    assert "override" in evaluation.output
    row = next(line for line in evaluation.output.splitlines() if "gen.seed_declared" in line)
    assert "WARNING" in row and "CRITICAL" in row and "profile:evaluation" in row
