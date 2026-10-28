"""Configuration graph cycles through the public audit, init and export commands."""

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from reprollm.cli.main import app
from tests.conftest import commit_all
from tests.unit.cli.test_audit import _coverage_cli_repo

runner = CliRunner()


def _input_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(root).parts
    }


def test_audit_keeps_healthy_config_keys_after_yaml_mapping_self_cycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "cycle-audit"
    repo.mkdir()
    (repo / "config.yaml").write_text(
        "plain: &loop\n  link: *loop\njudge: 1\nrubric: 1\n", encoding="utf-8"
    )
    before = _input_bytes(repo)
    monkeypatch.chdir(repo)

    result = runner.invoke(app, ["audit", ".", "--format", "json", "--fail-on", "never"])

    assert result.exit_code == 0, result.output
    assert result.stderr == ""
    report = json.loads(result.stdout)
    assert report["target"] == "."
    assert report["level"] == 0
    judges = [entry for entry in report["profiles"]["detected"] if entry["profile"] == "llm_judge"]
    assert len(judges) == 1
    assert judges[0]["confidence"] == "medium"
    assert [
        (evidence["kind"], evidence["path"], evidence["note"]) for evidence in judges[0]["evidence"]
    ] == [
        ("detection", "config.yaml", "keyword 'judge' in config key"),
        ("detection", "config.yaml", "keyword 'rubric' in config key"),
    ]
    assert str(repo) not in result.stdout + result.stderr
    assert "RecursionError" not in result.stdout + result.stderr
    assert "maximum recursion depth" not in result.stdout + result.stderr
    assert _input_bytes(repo) == before
    assert not (repo / "reprollm.yaml").exists()
    assert not (repo / ".reprollm").exists()


def _config_project(tmp_path: Path, text: str, *, filename: str = "config.yaml") -> Path:
    repo = tmp_path / "cycle-audit"
    repo.mkdir()
    (repo / filename).write_text(text, encoding="utf-8")
    return repo


def _judge_profile(report: dict[str, Any]) -> dict[str, Any]:
    judges = [entry for entry in report["profiles"]["detected"] if entry["profile"] == "llm_judge"]
    assert len(judges) == 1
    assert judges[0]["confidence"] == "medium"
    return judges[0]


@pytest.mark.parametrize(
    ("text", "sibling", "rubric_path"),
    [
        pytest.param(
            "plain: &loop\n  - *loop\n  - {judge: 1}\nrubric: 1\n",
            None,
            "config.yaml",
            id="list-self-cycle",
        ),
        pytest.param(
            "plain: &outer\n  items:\n    - *outer\n    - {judge: 1}\nrubric: 1\n",
            None,
            "config.yaml",
            id="mapping-list-cycle",
        ),
        pytest.param(
            "plain: &outer\n  other: &inner\n    rubric: *outer\n    judge: 1\n",
            None,
            "config.yaml",
            id="mutual-mappings",
        ),
        pytest.param(
            "judge: 1\nplain: &loop\n  back: *loop\n",
            "rubric: 1\n",
            "sibling.yaml",
            id="healthy-before-cycle-and-sibling-file",
        ),
    ],
)
def test_audit_keeps_healthy_keys_around_yaml_container_cycles(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    text: str,
    sibling: str | None,
    rubric_path: str,
) -> None:
    repo = _config_project(tmp_path, text)
    if sibling is not None:
        (repo / "sibling.yaml").write_text(sibling, encoding="utf-8")
    before = _input_bytes(repo)
    monkeypatch.chdir(repo)

    result = runner.invoke(app, ["audit", ".", "--format", "json", "--fail-on", "never"])

    assert result.exit_code == 0, result.output
    assert result.stderr == ""
    profile = _judge_profile(json.loads(result.stdout))
    assert [(item["path"], item["note"]) for item in profile["evidence"]] == [
        ("config.yaml", "keyword 'judge' in config key"),
        (rubric_path, "keyword 'rubric' in config key"),
    ]
    assert _input_bytes(repo) == before


def test_cycle_does_not_turn_scalar_configuration_values_into_detection_signals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _config_project(
        tmp_path,
        "plain: &loop [*loop]\ndescription: judge rubric refusal red_team accuracy\n",
    )
    before = _input_bytes(repo)
    monkeypatch.chdir(repo)

    result = runner.invoke(app, ["audit", ".", "--format", "json", "--fail-on", "never"])

    assert result.exit_code == 0, result.output
    assert result.stderr == ""
    assert json.loads(result.stdout)["profiles"]["detected"] == []
    assert _input_bytes(repo) == before


def test_shared_aliases_and_keyword_spellings_remain_one_canonical_concept(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _config_project(
        tmp_path, "first: &shared\n  red_team: 1\nsecond: *shared\nred-team: 1\n"
    )
    before = _input_bytes(repo)
    monkeypatch.chdir(repo)

    result = runner.invoke(app, ["audit", ".", "--format", "json", "--fail-on", "never"])

    assert result.exit_code == 0, result.output
    assert result.stderr == ""
    detected = json.loads(result.stdout)["profiles"]["detected"]
    assert [(entry["profile"], entry["confidence"]) for entry in detected] == [("safety", "low")]
    assert [(item["path"], item["note"]) for item in detected[0]["evidence"]] == [
        ("config.yaml", "keyword 'red team' in config key")
    ]
    assert _input_bytes(repo) == before


def test_acyclic_shared_aliases_keep_the_existing_public_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _config_project(
        tmp_path,
        "first: &shared\n  judge: 1\n  rubric: 1\nsecond: *shared\nitems: [*shared, *shared]\n",
    )
    monkeypatch.chdir(repo)
    before = _input_bytes(repo)

    aliased = runner.invoke(app, ["audit", ".", "--format", "json", "--fail-on", "never"])

    assert aliased.exit_code == 0, aliased.output
    assert aliased.stderr == ""
    assert _input_bytes(repo) == before
    original = json.loads(aliased.stdout)
    _judge_profile(original)
    (repo / "config.yaml").write_text(
        "first: {judge: 1, rubric: 1}\nsecond: {judge: 1, rubric: 1}\n"
        "items: [{judge: 1, rubric: 1}, {judge: 1, rubric: 1}]\n",
        encoding="utf-8",
    )
    expanded_before = _input_bytes(repo)
    expanded = runner.invoke(app, ["audit", ".", "--format", "json", "--fail-on", "never"])

    assert expanded.exit_code == 0, expanded.output
    assert expanded.stderr == ""
    repeated = json.loads(expanded.stdout)
    original.pop("generated_at")
    repeated.pop("generated_at")
    assert original == repeated
    assert _input_bytes(repo) == expanded_before


@pytest.mark.parametrize(
    ("filename", "text"),
    [
        pytest.param(
            "config.json",
            '{"outer": [{"judge": 1}, {"rubric": 1}], "description": "refusal"}\n',
            id="json",
        ),
        pytest.param(
            "config.toml",
            '[outer]\njudge = 1\nrubric = 1\ndescription = "refusal"\n',
            id="toml",
        ),
    ],
)
def test_normal_json_and_toml_configuration_keys_keep_existing_detection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, filename: str, text: str
) -> None:
    repo = _config_project(tmp_path, text, filename=filename)
    before = _input_bytes(repo)
    monkeypatch.chdir(repo)

    result = runner.invoke(app, ["audit", ".", "--format", "json", "--fail-on", "never"])

    assert result.exit_code == 0, result.output
    assert result.stderr == ""
    report = json.loads(result.stdout)
    assert [
        (entry["profile"], entry["confidence"]) for entry in report["profiles"]["detected"]
    ] == [("llm_judge", "medium")]
    assert [(item["path"], item["note"]) for item in _judge_profile(report)["evidence"]] == [
        (filename, "keyword 'judge' in config key"),
        (filename, "keyword 'rubric' in config key"),
    ]
    assert _input_bytes(repo) == before


@pytest.mark.security
@pytest.mark.parametrize(
    "text",
    [
        pytest.param("plain: [  # SyntheticYamlKeySecretCanary\n", id="malformed-yaml"),
        pytest.param(
            "plain: !unknown SyntheticYamlKeySecretCanary\njudge: 1\nrubric: 1\n",
            id="unknown-tag",
        ),
    ],
)
def test_unreadable_yaml_keeps_existing_silent_skip_and_healthy_sibling_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, text: str
) -> None:
    repo = _config_project(tmp_path, text)
    (repo / "sibling.yaml").write_text("judge: 1\nrubric: 1\n", encoding="utf-8")
    before = _input_bytes(repo)
    monkeypatch.chdir(repo)

    result = runner.invoke(app, ["audit", ".", "--format", "json", "--fail-on", "never"])

    assert result.exit_code == 0, result.output
    assert result.stderr == ""
    profile = _judge_profile(json.loads(result.stdout))
    assert [(item["path"], item["note"]) for item in profile["evidence"]] == [
        ("sibling.yaml", "keyword 'judge' in config key"),
        ("sibling.yaml", "keyword 'rubric' in config key"),
    ]
    assert "SyntheticYamlKeySecretCanary" not in result.stdout + result.stderr
    assert _input_bytes(repo) == before


def test_init_and_task_listing_keep_cycle_inputs_and_existing_scaffold_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _config_project(tmp_path, "plain: &loop\n  link: *loop\njudge: 1\nrubric: 1\n")
    before = _input_bytes(repo)
    monkeypatch.chdir(repo)

    listed = runner.invoke(app, ["init", ".", "--list-tasks"])

    assert listed.exit_code == 0, listed.output
    assert listed.stdout == listed.stderr == ""
    assert _input_bytes(repo) == before
    assert not (repo / ".reprollm").exists()
    initialized = runner.invoke(app, ["init", "."])
    assert initialized.exit_code == 0, initialized.output
    assert initialized.stderr == ""
    original_manifest = (repo / "reprollm.yaml").read_bytes()
    manifest = yaml.safe_load(original_manifest)
    assert manifest["experiment"]["profiles"] == ["llm_judge"]
    assert manifest["evaluation"]["metrics"] == []
    assert "Task candidates: 0; selected: 0" in initialized.stdout
    assert {name: _input_bytes(repo)[name] for name in before} == before
    assert set(_input_bytes(repo)) - set(before) == {
        "reprollm.yaml",
        ".reprollm/config.yaml",
        ".reprollm/project-rules.yaml",
    }
    repeated = runner.invoke(app, ["init", ".", "--force"])
    assert repeated.exit_code == 0, repeated.output
    assert repeated.stderr == ""
    assert (repo / "reprollm.yaml").read_bytes() == original_manifest
    assert {name: _input_bytes(repo)[name] for name in before} == before


def test_export_after_config_cycle_matches_repeated_and_acyclic_embedded_audit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _config_project(tmp_path, "plain: &loop\n  link: *loop\njudge: 1\nrubric: 1\n")
    (repo / "reprollm.yaml").write_text(
        "schema_version: 1\nproject: {name: cycle-audit}\nexperiment: {profiles: [llm_judge]}\n",
        encoding="utf-8",
    )
    before = _input_bytes(repo)
    monkeypatch.chdir(repo)

    first = runner.invoke(app, ["export", "."])

    assert first.exit_code == 0, first.output
    assert first.stderr == ""
    output = repo / "REPRODUCIBILITY.md"
    original_document = output.read_bytes()
    text = original_document.decode("utf-8")
    assert "Declared profiles: llm&#95;judge." in text
    assert "## Audit summary" in text
    assert "No audit was embedded" not in text
    assert str(repo) not in text
    output.unlink()
    assert _input_bytes(repo) == before
    repeated = runner.invoke(app, ["export", "."])
    assert repeated.exit_code == 0, repeated.output
    assert repeated.stderr == ""
    assert output.read_bytes() == original_document
    output.unlink()
    assert _input_bytes(repo) == before
    (repo / "config.yaml").write_text(
        "plain: {link: null}\njudge: 1\nrubric: 1\n", encoding="utf-8"
    )
    acyclic_before = _input_bytes(repo)
    acyclic = runner.invoke(app, ["export", "."])
    assert acyclic.exit_code == 0, acyclic.output
    assert acyclic.stderr == ""
    assert output.read_bytes() == original_document
    output.unlink()
    assert _input_bytes(repo) == acyclic_before


def test_config_cycle_preserves_independent_warning_and_fail_on_thresholds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _coverage_cli_repo(tmp_path)
    (repo / "config.yaml").write_text(
        "plain: &loop\n  link: *loop\njudge: 1\nrubric: 1\n", encoding="utf-8"
    )
    (repo / "requirements.txt").write_text("torch>=2.5.1\nvllm==0.6.0\n", encoding="utf-8")
    commit_all(repo)
    before = _input_bytes(repo)
    monkeypatch.chdir(repo)

    warning_gate = runner.invoke(app, ["audit", ".", "--format", "json", "--fail-on", "warning"])
    critical_gate = runner.invoke(app, ["audit", ".", "--format", "json", "--fail-on", "critical"])

    assert warning_gate.exit_code == 1, warning_gate.output
    assert critical_gate.exit_code == 0, critical_gate.output
    assert warning_gate.stderr == critical_gate.stderr == ""
    report = json.loads(warning_gate.stdout)
    _judge_profile(report)
    assert report["summary"]["critical"] == 0
    assert report["summary"]["warning"] == 1
    warning = next(
        item for item in report["findings"] if item["rule_id"] == "env.llm_critical_deps_pinned"
    )
    assert (warning["status"], warning["severity"]) == ("fail", "WARNING")
    assert [(item["path"], item["line"], item["value"]) for item in warning["evidence"]] == [
        ("requirements.txt", 1, ">=2.5.1")
    ]
    repeated = json.loads(critical_gate.stdout)
    report.pop("generated_at")
    repeated.pop("generated_at")
    assert report == repeated
    assert _input_bytes(repo) == before


def test_config_cycle_preserves_positive_high_confidence_profile_violation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _coverage_cli_repo(tmp_path)
    (repo / "config.yaml").write_text(
        "plain: &loop\n  link: *loop\njudge: 1\nrubric: 1\n", encoding="utf-8"
    )
    (repo / "requirements.txt").write_text("torch==2.5.1\nvllm==0.6.0\n", encoding="utf-8")
    core = repo / ".reprollm/profiles/core.yaml"
    core.write_text(
        core.read_text(encoding="utf-8")
        + "severity_overrides: {exec.profile_detection_mismatch: CRITICAL}\n",
        encoding="utf-8",
    )
    commit_all(repo)
    before = _input_bytes(repo)
    monkeypatch.chdir(repo)

    result = runner.invoke(app, ["audit", ".", "--format", "json", "--fail-on", "critical"])

    assert result.exit_code == 1, result.output
    assert result.stderr == ""
    assert result.stdout.startswith("{")
    report = json.loads(result.stdout)
    _judge_profile(report)
    assert report["summary"]["critical"] == 1
    assert report["summary"]["warning"] == 0
    positive = next(
        item for item in report["findings"] if item["rule_id"] == "exec.profile_detection_mismatch"
    )
    assert (positive["status"], positive["severity"]) == ("fail", "CRITICAL")
    assert positive["message"] == (
        "detected profile 'inference' (high confidence) is not declared in experiment.profiles"
    )
    assert [(item["path"], item["line"], item["note"]) for item in positive["evidence"]] == [
        ("z.py", 1, "import vllm")
    ]
    assert _input_bytes(repo) == before


@pytest.mark.security
def test_yaml_decoder_memory_error_keeps_existing_silent_skip_and_sibling_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _config_project(tmp_path, "plain: decoder-boundary\n")
    (repo / "sibling.yaml").write_text("judge: 1\nrubric: 1\n", encoding="utf-8")
    before = _input_bytes(repo)
    monkeypatch.chdir(repo)
    original_load = yaml.safe_load
    canary = f"SyntheticYamlKeySecretCanary {repo / 'private-input.yaml'}"

    def failed_decoder(stream: Any) -> Any:
        if stream == "plain: decoder-boundary\n":
            raise MemoryError(canary)
        return original_load(stream)

    monkeypatch.setattr(yaml, "safe_load", failed_decoder)

    result = runner.invoke(app, ["audit", ".", "--format", "json", "--fail-on", "never"])

    assert result.exit_code == 0, result.output
    assert result.stderr == ""
    profile = _judge_profile(json.loads(result.stdout))
    assert [(item["path"], item["note"]) for item in profile["evidence"]] == [
        ("sibling.yaml", "keyword 'judge' in config key"),
        ("sibling.yaml", "keyword 'rubric' in config key"),
    ]
    assert canary not in result.stdout + result.stderr
    assert str(repo) not in result.stdout + result.stderr
    assert _input_bytes(repo) == before


def test_unexpected_walk_recursion_is_not_silently_treated_as_a_yaml_cycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _config_project(tmp_path, "plain: traversal-boundary\n")
    before = _input_bytes(repo)
    monkeypatch.chdir(repo)
    original_load = yaml.safe_load
    failure = RecursionError("controlled external mapping iteration failure")

    class FailedMapping(dict[str, object]):
        def items(self) -> Any:
            raise failure

    def unusual_decoder_result(stream: Any) -> Any:
        if stream == "plain: traversal-boundary\n":
            return FailedMapping({"judge": 1, "rubric": 1})
        return original_load(stream)

    monkeypatch.setattr(yaml, "safe_load", unusual_decoder_result)

    result = runner.invoke(app, ["audit", ".", "--format", "json", "--fail-on", "never"])

    assert result.exit_code != 0
    assert result.exception is failure
    assert result.stdout == result.stderr == ""
    assert _input_bytes(repo) == before
