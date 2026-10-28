"""Deep decoded configuration keys through the public audit command."""

import json
import sys
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


def test_audit_keeps_keys_from_deep_decoded_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "depth-audit"
    repo.mkdir()
    source = '{"plain":"SyntheticConfigDepthDecodedFixture"}\n'
    (repo / "config.json").write_text(source, encoding="utf-8")
    before = _input_bytes(repo)
    monkeypatch.chdir(repo)

    # This portable decoded-data fixture does not claim the shallow source decodes this way.
    decoded: object = {"judge": 1, "rubric": 1}
    for _ in range(sys.getrecursionlimit() + 100):
        decoded = [decoded]
    original_loads = json.loads

    def decoded_fixture(text: str | bytes | bytearray, *args: Any, **kwargs: Any) -> Any:
        if text == source:
            return decoded
        return original_loads(text, *args, **kwargs)

    monkeypatch.setattr(json, "loads", decoded_fixture)

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
        ("detection", "config.json", "keyword 'judge' in config key"),
        ("detection", "config.json", "keyword 'rubric' in config key"),
    ]
    assert str(repo) not in result.stdout + result.stderr
    assert "SyntheticConfigDepthDecodedFixture" not in result.stdout + result.stderr
    assert "RecursionError" not in result.stdout + result.stderr
    assert "maximum recursion depth" not in result.stdout + result.stderr
    assert _input_bytes(repo) == before
    assert not (repo / "reprollm.yaml").exists()
    assert not (repo / ".reprollm").exists()


def _deep_chain(leaf: object, shape: str) -> object:
    node = leaf
    for index in range(sys.getrecursionlimit() + 100):
        node = {"plain": node} if shape == "mapping" or index % 2 else [node]
    return node


def _decoded_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, decoded: object) -> Path:
    """Provide decoded data, independently of the shallow marker's JSON meaning."""
    repo = tmp_path / "depth-audit"
    repo.mkdir()
    source = '{"plain":"SyntheticConfigDepthDecodedFixture"}\n'
    (repo / "config.json").write_text(source, encoding="utf-8")
    original_loads = json.loads

    def decoded_fixture(text: str | bytes | bytearray, *args: Any, **kwargs: Any) -> Any:
        if text == source:
            return decoded
        return original_loads(text, *args, **kwargs)

    monkeypatch.setattr(json, "loads", decoded_fixture)
    monkeypatch.chdir(repo)
    return repo


def _judge_profile(report: dict[str, Any]) -> dict[str, Any]:
    judges = [entry for entry in report["profiles"]["detected"] if entry["profile"] == "llm_judge"]
    assert len(judges) == 1
    assert judges[0]["confidence"] == "medium"
    return judges[0]


@pytest.mark.parametrize("shape", ["mapping", "mixed", "cycle"])
def test_audit_keeps_deep_and_later_keys_plus_healthy_sibling_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, shape: str
) -> None:
    leaf: dict[str, object] = {}
    decoded: dict[str, object] = {"plain": _deep_chain(leaf, shape), "rubric": 1}
    if shape == "cycle":
        leaf["back"] = decoded
    leaf["judge"] = 1
    repo = _decoded_project(tmp_path, monkeypatch, decoded)
    (repo / "sibling.json").write_text('{"jailbreak":1,"refusal":1}\n', encoding="utf-8")
    before = _input_bytes(repo)

    result = runner.invoke(app, ["audit", ".", "--format", "json", "--fail-on", "never"])

    assert result.exit_code == 0, result.output
    assert result.stderr == ""
    report = json.loads(result.stdout)
    assert [
        (entry["profile"], entry["confidence"]) for entry in report["profiles"]["detected"]
    ] == [
        ("llm_judge", "medium"),
        ("safety", "medium"),
    ]
    assert [(item["path"], item["note"]) for item in _judge_profile(report)["evidence"]] == [
        ("config.json", "keyword 'judge' in config key"),
        ("config.json", "keyword 'rubric' in config key"),
    ]
    safety = next(entry for entry in report["profiles"]["detected"] if entry["profile"] == "safety")
    assert [(item["path"], item["note"]) for item in safety["evidence"]] == [
        ("sibling.json", "keyword 'jailbreak' in config key"),
        ("sibling.json", "keyword 'refusal' in config key"),
    ]
    assert _input_bytes(repo) == before


def test_deep_scalar_values_do_not_become_configuration_key_signals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    decoded = _deep_chain({"description": "judge rubric"}, "mixed")
    repo = _decoded_project(tmp_path, monkeypatch, decoded)
    before = _input_bytes(repo)

    result = runner.invoke(app, ["audit", ".", "--format", "json", "--fail-on", "never"])

    assert result.exit_code == 0, result.output
    assert result.stderr == ""
    assert json.loads(result.stdout)["profiles"]["detected"] == []
    assert "judge rubric" not in result.stdout + result.stderr
    assert _input_bytes(repo) == before


@pytest.mark.security
def test_json_decoder_recursion_keeps_existing_skip_and_healthy_sibling_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "depth-audit"
    repo.mkdir()
    source = '{"plain":"SyntheticConfigDepthDecoderFailure"}\n'
    (repo / "config.json").write_text(source, encoding="utf-8")
    (repo / "sibling.json").write_text('{"judge":1,"rubric":1}\n', encoding="utf-8")
    before = _input_bytes(repo)
    monkeypatch.chdir(repo)
    original_loads = json.loads
    canary = f"SyntheticConfigDepthDecoderFailure {repo / 'private-input.json'}"

    def failed_decoder(text: str | bytes | bytearray, *args: Any, **kwargs: Any) -> Any:
        if text == source:
            raise RecursionError(canary)
        return original_loads(text, *args, **kwargs)

    monkeypatch.setattr(json, "loads", failed_decoder)

    result = runner.invoke(app, ["audit", ".", "--format", "json", "--fail-on", "never"])

    assert result.exit_code == 0, result.output
    assert result.stderr == ""
    profile = _judge_profile(json.loads(result.stdout))
    assert [(item["path"], item["note"]) for item in profile["evidence"]] == [
        ("sibling.json", "keyword 'judge' in config key"),
        ("sibling.json", "keyword 'rubric' in config key"),
    ]
    assert canary not in result.stdout + result.stderr
    assert "RecursionError" not in result.stdout + result.stderr
    assert _input_bytes(repo) == before


@pytest.mark.parametrize("stage", ["construct", "next"])
def test_unexpected_decoded_iterator_errors_are_not_silently_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    failure = (
        RuntimeError("controlled decoded iterator construction failure")
        if stage == "construct"
        else RecursionError("controlled decoded iterator advancement failure")
    )

    class FailedMapping(dict[str, object]):
        def items(self) -> Any:
            if stage == "construct":
                raise failure

            def entries() -> Any:
                yield "judge", 1
                raise failure

            return entries()

    # This external decoded-object fixture deliberately exceeds ordinary JSON object semantics.
    repo = _decoded_project(tmp_path, monkeypatch, FailedMapping({"judge": 1, "rubric": 1}))
    before = _input_bytes(repo)

    result = runner.invoke(app, ["audit", ".", "--format", "json", "--fail-on", "never"])

    assert result.exit_code != 0
    assert result.exception is failure
    assert result.stdout == result.stderr == ""
    assert _input_bytes(repo) == before


def test_decoded_live_list_keeps_a_sibling_added_while_visiting_its_first_item(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    decoded: list[object] = []

    class AppendSiblingMapping(dict[str, object]):
        def items(self) -> Any:
            decoded.append({"rubric": 1})
            return super().items()

    # This external mutable fixture checks live iteration, not literal JSON decoding semantics.
    decoded.append(AppendSiblingMapping({"judge": 1}))
    repo = _decoded_project(tmp_path, monkeypatch, decoded)
    before = _input_bytes(repo)

    result = runner.invoke(app, ["audit", ".", "--format", "json", "--fail-on", "never"])

    assert result.exit_code == 0, result.output
    assert result.stderr == ""
    profile = _judge_profile(json.loads(result.stdout))
    assert [(item["path"], item["note"]) for item in profile["evidence"]] == [
        ("config.json", "keyword 'judge' in config key"),
        ("config.json", "keyword 'rubric' in config key"),
    ]
    assert _input_bytes(repo) == before


def test_init_and_task_listing_keep_deep_inputs_and_owned_scaffold_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _decoded_project(tmp_path, monkeypatch, _deep_chain({"judge": 1, "rubric": 1}, "mixed"))
    (repo / "run.sh").write_text("inspect eval tasks.py\n", encoding="utf-8")
    (repo / "tasks.py").write_text(
        "from inspect_ai import task\n@task\ndef zeta():\n    return None\n"
        "@task\ndef alpha():\n    return None\n",
        encoding="utf-8",
    )
    before = _input_bytes(repo)

    listed = runner.invoke(app, ["init", ".", "--list-tasks"])

    assert listed.exit_code == 0, listed.output
    assert listed.stdout == "alpha\nzeta\n"
    assert listed.stderr == ""
    assert _input_bytes(repo) == before
    assert not (repo / ".reprollm").exists()
    initialized = runner.invoke(app, ["init", "."])
    assert initialized.exit_code == 0, initialized.output
    assert initialized.stderr == ""
    original_manifest = (repo / "reprollm.yaml").read_bytes()
    manifest = yaml.safe_load(original_manifest)
    assert manifest["experiment"]["profiles"] == ["evaluation", "llm_judge"]
    assert manifest["evaluation"]["metrics"] == []
    assert "Task candidates: 2; selected: 0" in initialized.stdout
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


def test_export_with_deep_decoded_keys_matches_repeat_and_shallow_embedded_audit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _decoded_project(tmp_path, monkeypatch, _deep_chain({"judge": 1, "rubric": 1}, "mixed"))
    (repo / "reprollm.yaml").write_text(
        "schema_version: 1\nproject: {name: depth-audit}\nexperiment: {profiles: [llm_judge]}\n",
        encoding="utf-8",
    )
    before = _input_bytes(repo)

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
    (repo / "config.json").write_text('{"plain":[{"judge":1}],"rubric":1}\n', encoding="utf-8")
    shallow_before = _input_bytes(repo)
    shallow = runner.invoke(app, ["export", "."])
    assert shallow.exit_code == 0, shallow.output
    assert shallow.stderr == ""
    assert output.read_bytes() == original_document
    output.unlink()
    assert _input_bytes(repo) == shallow_before


def test_deep_detection_preserves_independent_warning_and_fail_on_thresholds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _coverage_cli_repo(tmp_path)
    source = '{"plain":"SyntheticConfigDepthDecodedFixture"}\n'
    (repo / "config.json").write_text(source, encoding="utf-8")
    (repo / "requirements.txt").write_text("torch>=2.5.1\nvllm==0.6.0\n", encoding="utf-8")
    commit_all(repo)
    before = _input_bytes(repo)
    monkeypatch.chdir(repo)
    decoded = _deep_chain({"judge": 1, "rubric": 1}, "mixed")
    original_loads = json.loads

    def decoded_fixture(text: str | bytes | bytearray, *args: Any, **kwargs: Any) -> Any:
        if text == source:
            return decoded
        return original_loads(text, *args, **kwargs)

    monkeypatch.setattr(json, "loads", decoded_fixture)

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


def test_native_deep_json_keeps_keys_when_the_cli_decoder_accepts_the_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "depth-audit"
    repo.mkdir()
    depth = 1000
    source = '{"plain":' + "[" * depth + '{"judge":1,"rubric":1}' + "]" * depth + "}\n"
    (repo / "config.json").write_text(source, encoding="utf-8")
    before = _input_bytes(repo)
    monkeypatch.chdir(repo)
    original_limit = sys.getrecursionlimit()
    original_loads = json.loads
    decoded: list[Any] = []
    refused: list[Exception] = []

    def observed_decoder(text: str | bytes | bytearray, *args: Any, **kwargs: Any) -> Any:
        if text != source:
            return original_loads(text, *args, **kwargs)
        try:
            value = original_loads(text, *args, **kwargs)
        except (RecursionError, json.JSONDecodeError) as exc:
            refused.append(exc)
            raise
        decoded.append(value)
        return value

    # This real-parser observer adds a frame; unmodified console proof is retained separately.
    monkeypatch.setattr(json, "loads", observed_decoder)

    result = runner.invoke(app, ["audit", ".", "--format", "json", "--fail-on", "never"])

    assert sys.getrecursionlimit() == original_limit
    assert _input_bytes(repo) == before
    assert not (repo / "reprollm.yaml").exists()
    assert not (repo / ".reprollm").exists()
    if not decoded:
        assert refused, "the actual CLI never completed or rejected this configuration decode"
        assert result.exit_code == 0, result.output
        assert result.stderr == ""
        pytest.skip("the actual CLI decoder rejected this runtime's native deep JSON input")
    assert not refused
    cursor = decoded[0]
    assert isinstance(cursor, dict)
    assert list(cursor) == ["plain"]
    cursor = cursor["plain"]
    for _ in range(depth):
        assert isinstance(cursor, list)
        assert len(cursor) == 1
        cursor = cursor[0]
    assert cursor == {"judge": 1, "rubric": 1}
    assert result.exit_code == 0, result.output
    assert result.stderr == ""
    profile = _judge_profile(json.loads(result.stdout))
    assert [(item["path"], item["note"]) for item in profile["evidence"]] == [
        ("config.json", "keyword 'judge' in config key"),
        ("config.json", "keyword 'rubric' in config key"),
    ]
    assert str(repo) not in result.stdout + result.stderr
    assert "RecursionError" not in result.stdout + result.stderr
