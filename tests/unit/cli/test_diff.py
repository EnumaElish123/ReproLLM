"""M6-T04 input combinations, safe reports, exit/filter behavior and text contract."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import jsonschema
import pytest
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.schemas.manifest import Manifest
from reprollm.schemas.run_record import RunRecord
from tests.conftest import CmdStub
from tests.unit.diff.test_state import saved_run, snapshot_dir

runner = CliRunner()
SCHEMA = Path(__file__).resolve().parents[3] / "schemas/diff_report.schema.json"


@pytest.fixture(autouse=True)
def local_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stub_run_cmd: CmdStub) -> None:
    monkeypatch.chdir(tmp_path)
    stub_run_cmd.on("git", returncode=128)


def lock_pair(tmp_path: Path) -> tuple[str, str]:
    paths = []
    for name, revision in (("a", "a" * 40), ("b", "b" * 40)):
        folder = snapshot_dir(tmp_path, name="hf_vllm_eval")
        folder.rename(tmp_path / name)
        folder = tmp_path / name
        path = folder / "reprollm.lock"
        text = (folder / "lock.yaml").read_text()
        # Change only the primary revision; tokenizer revision stays fixed.
        text = text.replace("8fa23e7c1a0000000000000000000000000000aa", revision, 1)
        path.write_text(text)
        (folder / "manifest.yaml").rename(folder / "reprollm.yaml")
        paths.append(f"{name}/reprollm.lock")
    return paths[0], paths[1]


def run_pair(tmp_path: Path) -> tuple[str, str]:
    ids = ("20261001T100000Z-abcdef", "20261001T100001Z-abcdef")
    for run_id, temperature in zip(ids, (1.0, 0.7), strict=True):
        folder = tmp_path / ".reprollm/runs" / run_id
        folder.parent.mkdir(parents=True, exist_ok=True)
        fixture = snapshot_dir(tmp_path)
        fixture.rename(folder)
        data = saved_run().model_dump(mode="json")
        data["run_id"] = run_id
        data["bindings_observed"]["generation.temperature"][0]["value"] = temperature
        (folder / "run.json").write_text(json.dumps(data))
    return ids


def json_report(arguments: list[str], *, exit_code: int = 0) -> dict:
    result = runner.invoke(app, ["diff", *arguments, "--format", "json"])
    assert result.exit_code == exit_code, (result.output, result.exception)
    assert result.stderr == ""
    data = json.loads(result.stdout)
    jsonschema.validate(data, json.loads(SCHEMA.read_text()))
    return data


def test_lock_vs_lock_json_and_text_snapshot(tmp_path: Path) -> None:
    a, b = lock_pair(tmp_path)
    data = json_report([a, b])
    assert data["a"] == {"kind": "lock", "ref": a}
    assert data["b"] == {"kind": "lock", "ref": b}
    assert data["summary"]["highest"] == "HIGH"
    assert data["changes"] == [
        {
            "path": "models.primary.revision",
            "status": "changed",
            "a": "a" * 40,
            "b": "b" * 40,
            "severity": "HIGH",
            "note": None,
        }
    ]
    result = runner.invoke(app, ["--no-color", "diff", a, b])
    assert result.exit_code == 0, result.output
    assert result.stdout == (Path(__file__).parent / "snapshots/diff_lock.txt").read_text(
        encoding="utf-8"
    )
    assert "a" * 40 not in result.stdout and "a" * 12 in result.stdout


def test_run_vs_run_accepts_full_id_unique_prefix_file_and_directory(tmp_path: Path) -> None:
    a, b = run_pair(tmp_path)
    for left, right in [
        (a, b[:16]),
        (f".reprollm/runs/{a}/run.json", f".reprollm/runs/{b}"),
    ]:
        data = json_report([left, right])
        assert data["a"]["kind"] == data["b"]["kind"] == "run"
        assert {c["path"] for c in data["changes"]} == {"generation.temperature", "run_id"}
        assert data["summary"]["counts"]["HIGH"] == 1
        assert data["summary"]["counts"]["NONE"] == 1
        assert json_report([left, right]) == data


def test_run_vs_lock_uses_snapshots_not_live_manifest(tmp_path: Path) -> None:
    a, _ = run_pair(tmp_path)
    lock, _ = lock_pair(tmp_path)
    (tmp_path / "reprollm.yaml").write_text("broken: [")
    data = json_report([a, lock])
    assert data["a"]["kind"] == "run" and data["b"]["kind"] == "lock"
    change = next(c for c in data["changes"] if c["path"] == "generation.temperature")
    assert (change["a"], change["b"]) == (1.0, 0.0)


def test_filter_preserves_complete_summary_and_fail_on(tmp_path: Path) -> None:
    a, b = run_pair(tmp_path)
    whole = json_report([a, b])
    filtered = json_report([a, b, "--min-severity", "HIGH", "--fail-on", "HIGH"], exit_code=1)
    assert filtered["summary"] == whole["summary"]
    assert filtered["filtered_below"] == "HIGH"
    assert [c["path"] for c in filtered["changes"]] == ["generation.temperature"]
    same = json_report([a, a, "--fail-on", "LOW"])
    assert same["changes"] == [] and same["summary"]["highest"] == "NONE"
    # Filtering cannot hide a lower-than-display change from the exit policy.
    path = tmp_path / f".reprollm/runs/{b}/run.json"
    value = json.loads(path.read_text())
    value["bindings_observed"]["generation.temperature"][0]["value"] = 1.0
    value["environment"]["packages"]["torch"] = "2.8.1"
    path.write_text(json.dumps(value))
    report = json_report([a, b, "--min-severity", "HIGH", "--fail-on", "MEDIUM"], exit_code=1)
    assert report["changes"] == [] and report["summary"]["highest"] == "MEDIUM"


def test_ambiguous_prefix_lists_candidates_as_usage_error(tmp_path: Path) -> None:
    ids = run_pair(tmp_path)
    result = runner.invoke(app, ["diff", "20261001", ids[0]])
    assert result.exit_code == 2
    assert all(run_id in result.stderr for run_id in ids)
    assert "ambiguous" in result.stderr and "Traceback" not in result.stderr


@pytest.mark.parametrize(
    "extra", [["--format", "xml"], ["--min-severity", "CRITICAL"], ["--fail-on", "maybe"]]
)
def test_bad_options(tmp_path: Path, extra: list[str]) -> None:
    a, b = lock_pair(tmp_path)
    assert runner.invoke(app, ["diff", a, b, *extra]).exit_code == 2


@pytest.mark.parametrize("problem", ["missing", "corrupt", "snapshot", "new_schema"])
def test_invalid_inputs_are_safe_usage_errors(tmp_path: Path, problem: str) -> None:
    a, b = run_pair(tmp_path)
    path = tmp_path / f".reprollm/runs/{a}/run.json"
    if problem == "missing":
        path.unlink()
    elif problem == "corrupt":
        path.write_text('{"password":"PRIVATE_CORRUPT_SECRET",')
    elif problem == "snapshot":
        (path.parent / "manifest.yaml").unlink()
    else:
        data = json.loads(path.read_text())
        data["schema_version"] = 999
        path.write_text(json.dumps(data))
    result = runner.invoke(app, ["diff", str(path), b])
    assert result.exit_code == 2, (result.output, result.exception)
    assert "PRIVATE_CORRUPT_SECRET" not in result.output
    assert str(tmp_path) not in result.output and "Traceback" not in result.output
    assert result.stdout == ""


def test_relative_external_input_refs_and_redacted_values(tmp_path: Path) -> None:
    a, b = lock_pair(tmp_path)
    secret = "sk-" + "A" * 32
    path = tmp_path / "b/reprollm.yaml"
    path.write_text(
        path.read_text() + f"custom:\n  credential: {secret}\n  path: /private/other/home\n"
    )
    data = json_report([str(tmp_path / a), str(tmp_path / b)])
    rendered = json.dumps(data)
    assert secret not in rendered and "/private/other/home" not in rendered
    assert "<REDACTED:" in rendered and str(tmp_path) not in rendered
    assert data["summary"]["counts"]["MEDIUM"] == 2


def test_adjacent_manifest_optional_and_profile_override(tmp_path: Path) -> None:
    a, b = lock_pair(tmp_path)
    for folder in ("a", "b"):
        path = tmp_path / folder / "reprollm.yaml"
        path.write_text(path.read_text().replace("[inference, evaluation]", "[custom_policy]"))
    profiles = tmp_path / ".reprollm/profiles"
    profiles.mkdir(parents=True)
    (profiles / "custom_policy.yaml").write_text(
        "schema_version: 1\nname: custom_policy\ndescription: test\n"
        'drift_overrides: {"models.*.revision": LOW}\n'
    )
    report = json_report([a, b])
    assert report["summary"]["highest"] == "LOW"
    text = runner.invoke(app, ["diff", a, b]).stdout
    assert text.endswith("No reproducibility-relevant drift in recorded values.\n")
    assert "Child environment and input consumption are unverified." in text
    for folder in ("a", "b"):
        (tmp_path / folder / "reprollm.yaml").unlink()
    assert json_report([a, b])["summary"]["highest"] == "HIGH"


def test_standalone_run_works_outside_current_project(tmp_path: Path) -> None:
    a, _ = run_pair(tmp_path)
    source = tmp_path / ".reprollm/runs" / a
    external = tmp_path.parent / "external-captured-run"
    shutil.copytree(source, external)
    report = json_report([str(source), str(external)])
    assert report["changes"] == []
    assert str(tmp_path.parent) not in json.dumps(report)


def test_secret_field_values_and_nested_payloads_are_masked_after_comparison(
    tmp_path: Path,
) -> None:
    a, b = lock_pair(tmp_path)
    for folder, secret in (("a", "FAKE_BEFORE_PASSWORD"), ("b", "FAKE_AFTER_PASSWORD")):
        path = tmp_path / folder / "reprollm.yaml"
        path.write_text(
            path.read_text()
            + f"custom:\n  password: {secret}\n  payload: [{{api_key: {secret}}}]\n"
        )
    report = json_report([a, b])
    text = json.dumps(report)
    assert "FAKE_BEFORE_PASSWORD" not in text and "FAKE_AFTER_PASSWORD" not in text
    assert {c["path"] for c in report["changes"]} == {
        "models.primary.revision",
        "custom.password",
        "custom.payload",
    }
    assert all(c["status"] == "changed" for c in report["changes"])


def test_medium_verdict_and_display_filter_are_honest(tmp_path: Path) -> None:
    a, b = run_pair(tmp_path)
    path = tmp_path / f".reprollm/runs/{b}/run.json"
    data = json.loads(path.read_text())
    data["bindings_observed"]["generation.temperature"][0]["value"] = 1.0
    data["environment"]["packages"]["torch"] = "2.8.1"
    path.write_text(json.dumps(data))
    result = runner.invoke(app, ["diff", a, b, "--min-severity", "HIGH"])
    assert result.exit_code == 0
    assert "summary includes all changes" in result.stdout
    assert "Highest drift: MEDIUM (1 changes)" in result.stdout
    assert "Results may differ; review the changes above." in result.stdout


def test_symlink_snapshot_escape_is_rejected(tmp_path: Path) -> None:
    a, b = run_pair(tmp_path)
    path = tmp_path / f".reprollm/runs/{a}/manifest.yaml"
    outside = tmp_path / "outside.yaml"
    path.rename(outside)
    try:
        path.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation unavailable on this platform")
    result = runner.invoke(app, ["diff", a, b])
    assert result.exit_code == 2 and "snapshot" in result.stderr


def test_no_input_or_report_files_are_modified(tmp_path: Path) -> None:
    a, b = run_pair(tmp_path)
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    json_report([a, b])
    after = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert after == before


R08B_BINDINGS = [
    ("privacy.mechanism.params.target_epsilon", 8.0, 4.0),
    ("privacy.mechanism.params.target_delta", 0.001, 0.0001),
    ("privacy.mechanism.params.max_grad_norm", 1.0, 0.5),
    ("training.params.num_train_epochs", 0.125, 0.25),
]


def r08b_binding_pair(
    tmp_path: Path, path: str, a: object, b: object, *, profile: str | None = None
) -> tuple[str, str]:
    # Standard synthetic v2 input evidence; this does not claim a child consumed it.
    manifest = Manifest.model_validate(
        {
            "schema_version": 1,
            "project": {"name": "r08b-synthetic"},
            "experiment": {"profiles": [profile] if profile else []},
        }
    )
    payload = json.dumps(manifest.model_dump(mode="json"), sort_keys=True).encode()
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    refs = []
    for side, value in (("a", a), ("b", b)):
        folder = tmp_path / side
        folder.mkdir()
        (folder / "manifest.yaml").write_bytes(payload)
        record = RunRecord.model_validate(
            {
                "schema_version": 2,
                "reprollm_version": "0.7.0",
                "run_id": "20261020T000000Z-abcdef",
                "status": "completed",
                "exit_code": 0,
                "command": {"argv": ["python", "-c", "pass"], "cwd": "."},
                "code": {"commit": "a" * 40, "dirty": False},
                "manifest": {
                    "path": "reprollm.yaml",
                    "sha256": digest,
                    "snapshot": "manifest.yaml",
                },
                "bindings_observed": {
                    path: [{"value": value, "source": {"type": "cli", "key": "--value"}}]
                }
                if value is not None
                else {},
                "input_capture": {
                    "checks": [
                        {
                            "path": "reprollm.yaml",
                            "origin": "manifest",
                            "before": {
                                "availability": "present",
                                "sha256": digest,
                                "size_bytes": len(payload),
                            },
                            "after": {
                                "availability": "present",
                                "sha256": digest,
                                "size_bytes": len(payload),
                            },
                            "change": "unchanged",
                        }
                    ]
                },
            }
        )
        (folder / "run.json").write_text(record.model_dump_json())
        refs.append(f"{side}/run.json")
    return refs[0], refs[1]


@pytest.mark.parametrize(("path", "before", "after"), R08B_BINDINGS)
@pytest.mark.parametrize("status", ["changed", "added", "removed"])
def test_r08b_cli_isolated_binding_default_is_high(
    tmp_path: Path, path: str, before: object, after: object, status: str
) -> None:
    a = None if status == "added" else before
    b = None if status == "removed" else after
    refs = r08b_binding_pair(tmp_path, path, a, b)
    inputs = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    report = json_report([*refs])
    notes = {
        "changed": (
            "a: recorder/pre_child; child unverified; b: recorder/pre_child; child unverified"
        ),
        "added": "b: recorder/pre_child; child unverified",
        "removed": "a: recorder/pre_child; child unverified",
    }
    assert report["changes"] == [
        {"path": path, "status": status, "a": a, "b": b, "severity": "HIGH", "note": notes[status]}
    ]
    assert report["summary"]["highest"] == "HIGH"
    assert report["summary"]["counts"] == {
        "HIGH": 1,
        "MEDIUM_HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0,
        "NONE": 0,
    }
    assert json_report([*refs, "--fail-on", "HIGH"], exit_code=1) == report
    filtered = json_report([*refs, "--min-severity", "HIGH", "--fail-on", "HIGH"], exit_code=1)
    assert filtered["changes"] == report["changes"]
    assert filtered["summary"] == report["summary"]
    assert filtered["filtered_below"] == "HIGH"
    first = runner.invoke(app, ["diff", *refs, "--format", "json"])
    second = runner.invoke(app, ["diff", *refs, "--format", "json"])
    assert first.exit_code == second.exit_code == 0
    assert first.stdout == second.stdout
    same = json_report([refs[0], refs[0], "--fail-on", "HIGH"])
    assert same["changes"] == [] and same["summary"]["highest"] == "NONE"
    assert all(value == 0 for value in same["summary"]["counts"].values())
    assert {
        p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()
    } == inputs


@pytest.mark.parametrize(("path", "before", "after"), R08B_BINDINGS)
@pytest.mark.parametrize("override", ["LOW", "NONE"])
def test_r08b_cli_precise_override_and_complete_filtered_policy(
    tmp_path: Path, path: str, before: object, after: object, override: str
) -> None:
    profiles = tmp_path / ".reprollm/profiles"
    profiles.mkdir(parents=True)
    (profiles / "r08b_policy.yaml").write_text(
        "schema_version: 1\nname: r08b_policy\ndescription: synthetic override\n"
        f"drift_overrides:\n  {path}: {override}\n"
    )
    refs = r08b_binding_pair(tmp_path, path, before, after, profile="r08b_policy")
    report = json_report([*refs, "--fail-on", "HIGH"])
    assert len(report["changes"]) == 1
    assert report["changes"][0]["path"] == path
    assert report["changes"][0]["severity"] == override
    assert report["summary"]["highest"] == override
    assert report["summary"]["counts"][override] == 1
    assert sum(report["summary"]["counts"].values()) == 1
    filtered = json_report(
        [*refs, "--min-severity", "HIGH", "--fail-on", "LOW"],
        exit_code=1 if override == "LOW" else 0,
    )
    assert filtered["changes"] == []
    assert filtered["summary"] == report["summary"]
    assert filtered["filtered_below"] == "HIGH"


@pytest.mark.parametrize(
    "path",
    [
        "privacy.mechanism.params.target_epsilon.nested",
        "privacy.mechanism.params.noise_multiplier",
        "privacy.mechanism.params.logging.steps",
        "training.params.num_train_epochs.nested",
        "training.params.custom_option",
        "custom.target_epsilon",
    ],
)
def test_r08b_cli_neighbors_keep_medium(tmp_path: Path, path: str) -> None:
    refs = r08b_binding_pair(tmp_path, path, 1, 2)
    report = json_report([*refs, "--fail-on", "HIGH"])
    assert len(report["changes"]) == 1
    assert report["changes"][0]["path"] == path
    assert report["changes"][0]["severity"] == "MEDIUM"
    assert report["summary"]["highest"] == "MEDIUM"
    assert report["summary"]["counts"] == {
        "HIGH": 0,
        "MEDIUM_HIGH": 0,
        "MEDIUM": 1,
        "LOW": 0,
        "NONE": 0,
    }
