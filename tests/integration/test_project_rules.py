"""M7-T02: project rules end-to-end — add, audit, consistency, lock freshness."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from tests.conftest import commit_all, materialize_repo
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.core.yaml_io import load_yaml

runner = CliRunner()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    repo = materialize_repo("privacy_custom_params", tmp_path)
    (repo / "reprollm.yaml").write_text(
        (
            Path(__file__).resolve().parents[2]
            / "tests"
            / "fixtures"
            / "repos"
            / "privacy_custom_params"
            / "manifests"
            / "complete.yaml"
        ).read_text(encoding="utf-8"),
        encoding="utf-8",
        newline="\n",
    )
    commit_all(repo)
    return repo


def _add_rules(repo: Path, monkeypatch=None) -> None:
    if monkeypatch is not None:
        monkeypatch.chdir(repo)
    for args in (
        [
            "--field",
            "custom.privacy_method.alpha",
            "--severity",
            "CRITICAL",
            "--reason",
            "controls noise scale",
            "--config",
            "configs/privacy.yaml:method.alpha",
        ],
        ["--field", "custom.privacy_method.delta", "--severity", "WARNING", "--reason", "shift"],
    ):
        result = runner.invoke(app, ["rules", "add", *args])
        assert result.exit_code == 0, result.output


def test_accepted_rules_pass_on_complete_manifest(repo: Path, monkeypatch) -> None:
    _add_rules(repo, monkeypatch)
    result = runner.invoke(app, ["audit", str(repo), "--format", "json", "--fail-on", "never"])
    assert result.exit_code == 0
    findings = json.loads(result.output)["findings"]
    project = {f["rule_id"]: f["status"] for f in findings if f["rule_id"].startswith("project.")}
    assert project == {"project.alpha": "pass", "project.delta": "pass"}
    origins = {
        f["rule_id"]: f["severity_origin"] for f in findings if f["rule_id"].startswith("project.")
    }
    assert set(origins.values()) == {"project_rule"}


def test_missing_field_fails_with_declared_severity(repo: Path, monkeypatch) -> None:
    _add_rules(repo, monkeypatch)
    manifest_path = repo / "reprollm.yaml"
    text = manifest_path.read_text(encoding="utf-8")
    # remove only the custom-block delta (privacy params share the field name)
    custom_block = "  privacy_method:\n    alpha: 0.25\n    delta: 1.5\n"
    assert custom_block in text
    manifest_path.write_text(
        text.replace(custom_block, "  privacy_method:\n    alpha: 0.25\n"), encoding="utf-8"
    )
    result = runner.invoke(app, ["audit", str(repo), "--format", "json", "--fail-on", "never"])
    findings = json.loads(result.output)["findings"]
    delta = next(f for f in findings if f["rule_id"] == "project.delta")
    assert delta["status"] == "fail"
    assert delta["severity"] == "WARNING"
    assert "custom.privacy_method.delta" in delta["message"]
    assert "shift" in delta["fix_hint"]


def test_custom_fields_consistency_after_config_change(repo: Path, monkeypatch) -> None:
    _add_rules(repo, monkeypatch)
    # a run binds the config file; then the config value drifts.
    # `run` takes no PATH (spec §1); it locates the repository from cwd.
    monkeypatch.chdir(repo)
    record = runner.invoke(
        app,
        ["run", "--", sys.executable, "-c", "pass", "--config", "configs/privacy.yaml"],
    )
    assert record.exit_code == 0, record.output
    # consistency.custom_fields compares the run's observed binding value
    # with the manifest declaration (spec §12.12): editing the config file
    # after the run is file drift (consistency.file_hashes), not a value
    # conflict. Declare a drifted manifest value instead.
    manifest_path = repo / "reprollm.yaml"
    manifest_path.write_text(
        manifest_path.read_text(encoding="utf-8").replace("alpha: 0.25", "alpha: 9.9"),
        encoding="utf-8",
    )
    result = runner.invoke(app, ["audit", str(repo), "--format", "json", "--fail-on", "never"])
    findings = json.loads(result.output)["findings"]
    custom = [f for f in findings if f["rule_id"] == "consistency.custom_fields"]
    assert custom, "the accepted binding must be compared"
    assert custom[0]["status"] == "fail"
    assert custom[0]["severity"] == "CRITICAL"
    assert "alpha" in custom[0]["message"]


def test_lock_fresh_second_branch_triggers(repo: Path, monkeypatch) -> None:
    lock_result = runner.invoke(app, ["lock", str(repo), "--offline"])
    assert lock_result.exit_code == 0, lock_result.output
    result = runner.invoke(app, ["audit", str(repo), "--format", "json", "--fail-on", "never"])
    fresh = [
        f
        for f in json.loads(result.output)["findings"]
        if f["rule_id"] == "consistency.lock_fresh" and f["status"] == "pass"
    ]
    assert fresh  # baseline: lock matches manifest and (empty) project rules

    _add_rules(repo, monkeypatch)  # project-rules.yaml now differs from the locked hash
    result = runner.invoke(app, ["audit", str(repo), "--format", "json", "--fail-on", "never"])
    fresh = [
        f for f in json.loads(result.output)["findings"] if f["rule_id"] == "consistency.lock_fresh"
    ]
    assert fresh and fresh[0]["status"] == "fail"
    assert "project_rules_sha256" in json.dumps(fresh[0])


def test_rules_add_unique_ids_and_list(repo: Path, monkeypatch) -> None:
    monkeypatch.chdir(repo)
    for _ in range(2):
        result = runner.invoke(
            app,
            ["rules", "add", "--field", "custom.scale", "--severity", "INFO", "--reason", "r"],
        )
        assert result.exit_code == 0, result.output
    document = load_yaml(repo / ".reprollm" / "project-rules.yaml")
    ids = [rule["id"] for rule in document["rules"]]
    assert ids == ["project.scale", "project.scale_2"]

    listing = runner.invoke(app, ["rules", "list"])
    assert listing.exit_code == 0
    assert "project.scale" in listing.output
    assert "INFO" in listing.output
    assert "reason: r" in listing.output


def test_rules_add_rejects_bad_input(repo: Path, monkeypatch) -> None:
    import pytest

    from reprollm.cli.main import cli

    monkeypatch.chdir(repo)
    monkeypatch.setattr(
        "sys.argv",
        ["reprollm", "rules", "add", "--field", "x", "--severity", "FATAL", "--reason", "r"],
    )
    with pytest.raises(SystemExit) as excinfo:
        cli()
    assert excinfo.value.code == 2
    monkeypatch.setattr(
        "sys.argv",
        ["reprollm", "rules", "add", "--field", "custom.x", "--severity", "INFO", "--reason", " "],
    )
    with pytest.raises(SystemExit) as excinfo:
        cli()
    assert excinfo.value.code == 2


def test_audit_l2_project_rules_snapshot(repo: Path, monkeypatch) -> None:
    import os

    # Fixed inputs for determinism: the pre-generated expected lock (already
    # hashed against this manifest) plus hand-written rules with a pinned
    # accepted_at. A live `lock` here would embed generated_at and make the
    # documents.lock hash untestable.
    fixture_root = (
        Path(__file__).resolve().parents[2]
        / "tests"
        / "fixtures"
        / "repos"
        / "privacy_custom_params"
        / "expected"
    )
    (repo / "reprollm.lock").write_text(
        (fixture_root / "lock.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
        newline="\n",
    )
    (repo / ".reprollm").mkdir(exist_ok=True)
    (repo / ".reprollm" / "project-rules.yaml").write_text(
        """schema_version: 1
rules:
- id: project.alpha
  field: custom.privacy_method.alpha
  severity: CRITICAL
  reason: controls noise scale
  source: manual
  accepted_at: 2026-09-28T00:00:00Z
  bindings:
    cli: null
    config: configs/privacy.yaml:method.alpha
    env: null
- id: project.delta
  field: custom.privacy_method.delta
  severity: WARNING
  reason: shift
  source: manual
  accepted_at: 2026-09-28T00:00:00Z
""",
        encoding="utf-8",
    )
    monkeypatch.chdir(repo)
    result = runner.invoke(app, ["audit", ".", "--format", "json", "--fail-on", "never"])
    document = json.loads(result.output)
    expected_path = (
        Path(__file__).resolve().parents[2]
        / "tests"
        / "fixtures"
        / "repos"
        / "privacy_custom_params"
        / "expected"
        / "audit_L2_project_rules.json"
    )
    if os.environ.get("REPROLLM_UPDATE_SNAPSHOTS") == "1":
        expected_path.write_text(
            json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    else:
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        for volatile in ("generated_at", "reprollm_version"):
            document.pop(volatile, None)
            expected.pop(volatile, None)
        assert _canonical(document) == _canonical(expected), _delta(document, expected)


def _canonical(node: object) -> str:
    """Byte-exact canonical form: bool/int aliasing and key order cannot hide."""
    return json.dumps(_typed(node), sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def _typed(node: object) -> object:
    """Wrap bools so true and 1 canonicalize differently (Python == aliases them)."""
    if isinstance(node, bool):
        return {"__bool__": str(node)}
    if isinstance(node, dict):
        return {key: _typed(value) for key, value in node.items()}
    if isinstance(node, list):
        return [_typed(item) for item in node]
    return node


def _delta(actual: object, expected: object) -> str:
    """Hex-dump the first differing canonical byte — unambiguous on any runner."""
    sa = _canonical(actual).encode("utf-8")
    sb = _canonical(expected).encode("utf-8")
    pairs = enumerate(zip(sa, sb, strict=False))
    i = next((k for k, (x, y) in pairs if x != y), min(len(sa), len(sb)))
    lo = max(0, i - 24)
    return (
        f"canonical bytes differ at {i} (lengths {len(sa)}/{len(sb)}): "
        f"actual={sa[lo : i + 24].hex(' ')} expected={sb[lo : i + 24].hex(' ')}"
    )
