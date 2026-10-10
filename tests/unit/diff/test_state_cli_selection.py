"""R03: effective CLI values follow actual argv while every source remains evidence."""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
import yaml
from tests.conftest import CmdStub
from typer.testing import CliRunner

from reprollm import __version__
from reprollm.cli.main import app
from reprollm.core.audit_state import audit_state
from reprollm.core.bindings import observe
from reprollm.core.context import AuditContext
from reprollm.core.yaml_io import load_manifest
from reprollm.export.exporter import build_input
from reprollm.rules.consistency import GenerationParamsRule
from reprollm.run import wrapper
from reprollm.schemas.finding import Severity
from reprollm.schemas.lock import Lock
from reprollm.schemas.manifest import BindingSpec, Manifest
from reprollm.schemas.run_record import HardwareInfo, RunRecord
from reprollm.schemas.state import Leaf, State

FIELD = "generation.temperature"
NOW = datetime(2026, 10, 10, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def bounded_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stub_run_cmd: CmdStub
) -> None:
    monkeypatch.chdir(tmp_path)
    stub_run_cmd.on("git", returncode=128)
    monkeypatch.setattr(wrapper, "capture_hardware", lambda: HardwareInfo(cpu_count=2))
    monkeypatch.setattr(wrapper.envinfo, "installed_versions", lambda: {})
    monkeypatch.setenv("R03_TEMPERATURE", "0.3")


@pytest.fixture
def child_project(tmp_path: Path) -> Path:
    manifest = {
        "schema_version": 1,
        "project": {"name": "oracle"},
        "experiment": {"profiles": ["inference"]},
        "generation": {"temperature": 0.9},
        "execution": {"config_files": ["config.json"]},
        "bindings": {
            FIELD: {
                "cli": "--temperature",
                "config": "config.json:temperature",
                "env": "R03_TEMPERATURE",
            }
        },
    }
    (tmp_path / "reprollm.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    (tmp_path / "config.json").write_text('{"temperature": 0.2}', encoding="utf-8")
    (tmp_path / ".reprollm").mkdir()
    (tmp_path / ".reprollm/project-rules.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "rules": [
                    {
                        "id": "project.temperature",
                        "field": FIELD,
                        "severity": "WARNING",
                        "reason": "Observe the child alias",
                        "source": "manual",
                        "accepted_at": "2026-10-10T00:00:00Z",
                        "bindings": {"cli": "--temp"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "child.py").write_text(
        "import argparse,json,pathlib\n"
        "p=argparse.ArgumentParser()\n"
        "p.add_argument('--temperature','--temp',type=float)\n"
        "value=p.parse_args().temperature\n"
        "pathlib.Path('consumed.json').write_text(json.dumps(value))\n"
        "print(value)\n",
        encoding="utf-8",
    )
    return tmp_path


def wrapped(root: Path, argv: list[str]) -> tuple[RunRecord, Path, float]:
    directory = wrapper.create_run_dir(root)
    record = wrapper.execute(
        [sys.executable, "child.py", *argv],
        root=root,
        cwd=root,
        run_dir=directory,
        capture_output=True,
        env_capture="allowlist",
        extra_allowlist=[],
        snapshot=True,
    )
    consumed = json.loads((root / "consumed.json").read_text(encoding="utf-8"))
    assert record.exit_code == 0
    return record, directory, consumed


def all_evidence(leaf: Leaf) -> list[Leaf]:
    return [leaf, *(item for child in leaf.alternatives for item in all_evidence(child))]


def evidence_counts(leaf: Leaf) -> Counter[str]:
    return Counter(
        json.dumps(item.model_dump(mode="json", exclude={"alternatives"}), sort_keys=True)
        for item in all_evidence(leaf)
    )


def run_record(observations: list[dict[str, Any]]) -> RunRecord:
    return RunRecord.model_validate(
        {
            "schema_version": 1,
            "reprollm_version": "0.1.1",
            "run_id": "20261010T000000Z-abc123",
            "status": "completed",
            "command": {"argv": ["python", "child.py"], "cwd": "."},
            "bindings_observed": {FIELD: observations},
        }
    )


def observation(
    value: Any, *, kind: str = "cli", key: str = "--temperature", path: str | None = None
) -> dict[str, Any]:
    return {"value": value, "source": {"type": kind, "key": key, "path": path}}


def test_argparse_last_wins_drives_diff_audit_and_export(child_project: Path) -> None:
    root = child_project
    a, a_dir, actual_a = wrapped(root, ["--temperature", "0.1", "--temperature", "0.9"])
    b, b_dir, actual_b = wrapped(root, ["--temperature", "0.9", "--temperature", "0.1"])
    assert (actual_a, actual_b) == (0.9, 0.1)
    declared = load_manifest(root / "reprollm.yaml")
    for run, directory, expected, ordered in (
        (a, a_dir, actual_a, [0.1, 0.9, 0.2, 0.3]),
        (b, b_dir, actual_b, [0.9, 0.1, 0.2, 0.3]),
    ):
        original = run.model_dump_json()
        assert [item.value for item in run.bindings_observed[FIELD]] == ordered
        state = State.from_run(run, run_dir=directory)
        assert state.flatten()[FIELD].value == expected
        assert state.flatten()[FIELD].detail == "cli:--temperature"
        assert audit_state(root, declared, None, run).flatten()[FIELD].value == expected
        exported = build_input(declared, None, run, state, reprollm_version=__version__)
        assert exported.generation["temperature"] == expected
        assert State.from_run(run, run_dir=directory).model_dump_json() == state.model_dump_json()
        assert run.model_dump_json() == original
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "diff",
            str(a_dir / "run.json"),
            str(b_dir / "run.json"),
            "--format",
            "json",
            "--fail-on",
            "HIGH",
        ],
    )
    assert result.exit_code == 1, result.output
    report = json.loads(result.stdout)
    drift = next(change for change in report["changes"] if change["path"] == FIELD)
    assert (drift["a"], drift["b"], drift["severity"]) == (actual_a, actual_b, "HIGH")
    same = runner.invoke(
        app,
        [
            "diff",
            str(a_dir / "run.json"),
            str(a_dir / "run.json"),
            "--format",
            "json",
            "--fail-on",
            "HIGH",
        ],
    )
    assert same.exit_code == 0
    assert json.loads(same.stdout)["changes"] == []


@pytest.mark.parametrize(
    "argv,ordered,expected",
    [
        (["--temp=0.1", "--temperature", "0.9"], [0.1, 0.9], 0.9),
        (["--temperature=0.1", "--temp", "0.9"], [0.1, 0.9], 0.9),
        (["--temp=0.9", "--temperature", "0.1"], [0.9, 0.1], 0.1),
        (["--temperature=0.9", "--temperature=0.9"], [0.9, 0.9], 0.9),
        (["--temperature=0"], [0], 0.0),
        (["--temperature=0.10", "--temperature=0.9"], [0.1, 0.9], 0.9),
        (["--temperature=-1", "--temperature=2"], [-1, 2], 2.0),
    ],
)
def test_argparse_aliases_duplicates_and_numeric_values(
    child_project: Path, argv: list[str], ordered: list[int | float], expected: float
) -> None:
    run, directory, consumed = wrapped(child_project, argv)
    assert consumed == expected
    observations = run.bindings_observed[FIELD]
    assert [item.value for item in observations if item.source.type == "cli"] == ordered
    assert [item.source.key for item in observations if item.source.type == "cli"] == [
        token.split("=", 1)[0] for token in argv if token.startswith("--")
    ]
    state = State.from_run(run, run_dir=directory)
    assert state.flatten()[FIELD].value == consumed
    assert sum(
        item.detail.startswith("cli:")
        for item in all_evidence(state.flatten()[FIELD])
        if item.detail
    ) == len(ordered)


def test_legacy_v1_strings_keep_selection_and_bounded_evidence_through_merges() -> None:
    run = run_record(
        [
            observation("0.1"),
            observation("0.9"),
            observation("0.9"),
            observation(0.2, kind="config", key="temperature", path="config.json"),
            observation("0.3", kind="env", key="TEMPERATURE"),
        ]
    )
    declared = Manifest.model_validate(
        {
            "project": {"name": "test"},
            "experiment": {"profiles": []},
            "generation": {"temperature": 0.9},
        }
    )
    locked = Lock.model_validate(
        {
            "reprollm_version": "0.1.1",
            "generated_at": NOW,
            "manifest_sha256": "sha256:manifest",
            "resolution": {"mode": "offline"},
            "generation": {"temperature": 0.7},
        }
    )
    original = run.model_dump_json()
    observed = State.from_run(run)
    state = State.merge(declared, locked, observed)
    leaf = state.flatten()[FIELD]
    assert (leaf.value, leaf.source, leaf.detail) == ("0.9", "run", "cli:--temperature")
    expected = evidence_counts(leaf)
    assert sum(expected.values()) == 7
    assert (
        sum(
            item.value == "0.9" and item.detail == "cli:--temperature"
            for item in all_evidence(leaf)
        )
        == 2
    )
    for merged in (
        State.merge(declared, locked, state),
        State.merge(declared, locked, State.merge(declared, locked, state)),
        State.merge(state, state, observed),
        State.merge(declared, locked, State.model_validate_json(state.model_dump_json())),
        State.merge(State.merge(declared, locked), None, observed),
        State.merge(declared, None, State.merge(None, locked, observed)),
    ):
        assert merged.flatten() == state.flatten()
        assert evidence_counts(merged.flatten()[FIELD]) == expected
    assert run.model_dump_json() == original
    assert run.schema_version == 1


@pytest.mark.parametrize("reverse", [False, True])
def test_config_and_env_keep_existing_lexical_selection_and_source_priority(reverse: bool) -> None:
    config = [
        observation(8, kind="config", key="temperature", path="z.json"),
        observation(9, kind="config", key="temperature", path="a.json"),
    ]
    env = [observation(1, kind="env", key="Z"), observation(2, kind="env", key="A")]
    ordered = [*config, *env]
    if reverse:
        ordered.reverse()
    assert State.from_run(run_record(ordered)).flatten()[FIELD].value == 9
    if reverse:
        env.reverse()
    assert State.from_run(run_record(env)).flatten()[FIELD].value == 2


def test_final_cli_matching_manifest_does_not_remove_an_earlier_consistency_conflict(
    tmp_path: Path,
) -> None:
    run = run_record([observation(0.1), observation(0.9)])
    declared = Manifest.model_validate(
        {
            "project": {"name": "test"},
            "experiment": {"profiles": []},
            "generation": {"temperature": 0.9},
        }
    )
    assert audit_state(tmp_path, declared, None, run).flatten()[FIELD].value == 0.9
    findings = GenerationParamsRule().check(
        AuditContext(tmp_path, level=2, manifest=declared, runs=[run])
    )
    assert len(findings) == 1 and findings[0].severity == Severity.CRITICAL
    assert Counter(item.value for item in findings[0].evidence) == Counter([0.9, 0.9, 0.1])


@pytest.mark.parametrize(
    "argv,expected",
    [(["--count=-1"], [-1]), (["--count", "-1"], [True]), (["--count=-1", "--count=2"], [-1, 2])],
)
def test_documented_negative_cli_boundary_remains_unchanged(
    tmp_path: Path, argv: list[str], expected: list[Any]
) -> None:
    observed = observe({"custom.count": BindingSpec(cli="--count")}, argv, {}, tmp_path)
    assert [item.value for item in observed["custom.count"]] == expected
    run = run_record([]).model_copy(update={"bindings_observed": observed})
    assert State.from_run(run).flatten()["custom.count"].value == expected[-1]
