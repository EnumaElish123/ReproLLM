"""SK15 native offline lock and exact reviewed rule lifecycle contracts."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml

from reprollm.core.proc import CmdResult
from reprollm.core.rule_lifecycle import read_rules
from reprollm.core.yaml_io import load_lock
from reprollm.schemas.discover_candidates import (
    Candidate,
    CandidateSuggestedBindings,
    DiscoverCandidates,
)
from reprollm.schemas.rule_archive import RuleArchive

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/reprollm/scripts"))
import skill_local as local  # noqa: E402
from skill_request import Grants, Request  # noqa: E402


@pytest.fixture(autouse=True)
def no_external_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*a: Any, **kw: Any) -> Any:
        pytest.fail("SK15 offline operation constructed an HTTP client")

    monkeypatch.setattr(httpx, "Client", forbidden)
    # Gateway aliases are patched, not arbitrary subprocess/Python imports.
    from reprollm.core import proc

    def unavailable(argv: Any, **kw: Any) -> CmdResult:
        return CmdResult(127, "", "unavailable fixture")

    monkeypatch.setattr(proc, "run_cmd", unavailable)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "research"
    root.mkdir()
    (root / "reprollm.yaml").write_text(
        "schema_version: 1\nproject: {name: lifecycle-fixture}\nexperiment: {profiles: []}\n",
        encoding="utf-8",
    )
    (root / ".reprollm").mkdir()
    (root / "untouched.py").write_text("raise RuntimeError('Never execute project code')\n")
    return root


def digest(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def call(root: Path, state: Path, action: str, *, grants: Grants | None = None, **options: Any):
    execute = local.execute_lock if action == "lock" else local.execute_rules
    return execute(
        Request(action, str(root), options, grants or Grants(write=True)),
        root=root,
        state_home=state / "writes",
        identity="fixed-test-local",
    )


def checked(reply: Any, code: int = 0) -> None:
    assert reply.invocation == "handled_result", reply.as_dict()
    assert reply.cli_exit_code == code, reply.as_dict()
    assert reply.child_exit_code is None
    # check's native 1 is staleness, not a deterministic audit gate.
    assert reply.gate_failed is None


def discovery(root: Path, *, name: str = "alpha", filename: str = "20261030T000000Z.json") -> Path:
    directory = root / ".reprollm/discover"
    directory.mkdir(exist_ok=True)
    path = directory / filename
    document = DiscoverCandidates(
        reprollm_version="0.7.0",
        generated_at=datetime(2026, 10, 30, tzinfo=timezone.utc),
        model="fixture-no-network",
        input_files=["untouched.py"],
        candidates=[
            Candidate(
                id="c-000001",
                kind="parameter",
                name=name,
                suggested_field=f"custom.{name}",
                suggested_severity="WARNING",
                confidence="high",
                rationale=f"Retain {name}.",
                suggested_bindings=CandidateSuggestedBindings(
                    cli=f"--{name}",
                    config=f"config.yaml:{name}",
                    env=name.upper(),
                ),
            )
        ],
    )
    path.write_text(document.model_dump_json(), encoding="utf-8")
    return path


def reviewed(root: Path, source: Path) -> Grants:
    return Grants(
        write=True,
        expected_hashes={
            source.relative_to(root).as_posix(): digest(source),
            ".reprollm/project-rules.yaml": digest(root / ".reprollm/project-rules.yaml"),
        },
    )


@pytest.mark.parametrize("offline", [False, True])
@pytest.mark.parametrize("verify_api", [False, True])
@pytest.mark.parametrize("hash_large_files", [False, True])
def test_check_precedes_all_resolution_and_writes(
    project: Path,
    tmp_path: Path,
    offline: bool,
    verify_api: bool,
    hash_large_files: bool,
) -> None:
    before = {p.relative_to(project): p.read_bytes() for p in project.rglob("*") if p.is_file()}
    result = call(
        project,
        tmp_path / "state",
        "lock",
        grants=Grants(),
        check=True,
        offline=offline,
        verify_api=verify_api,
        hash_large_files=hash_large_files,
    )
    checked(result, 1)
    assert not (project / "reprollm.lock").exists()
    assert before == {
        p.relative_to(project): p.read_bytes() for p in project.rglob("*") if p.is_file()
    }


@pytest.mark.parametrize("verify_api", [False, True])
def test_offline_api_hf_declarations_do_not_construct_client(
    project: Path,
    tmp_path: Path,
    verify_api: bool,
) -> None:
    path = project / "reprollm.yaml"
    data = yaml.safe_load(path.read_text())
    data["models"] = {
        "primary": {"provider": "huggingface", "id": "distilbert/distilgpt2"},
        "judge": {"provider": "openai", "id": "gpt-4o"},
    }
    path.write_text(yaml.safe_dump(data))
    checked(call(project, tmp_path / "state", "lock", offline=True, verify_api=verify_api))
    lock = load_lock(project / "reprollm.lock")
    assert lock.resolution.mode == "offline"
    assert lock.models["primary"].revision.value is None
    assert lock.models["primary"].revision.source == "offline"
    assert lock.models["judge"].pinnability == "unpinnable"
    assert lock.models["judge"].revision.value is None


def test_staleness_native_order_and_no_weight_freshness_invention(
    project: Path, tmp_path: Path
) -> None:
    checked(call(project, tmp_path / "state", "lock", offline=True))
    checked(call(project, tmp_path / "state", "lock", grants=Grants(), check=True))
    manifest = project / "reprollm.yaml"
    manifest.write_bytes(manifest.read_bytes() + b"\n# human edit\n")
    (project / ".reprollm/project-rules.yaml").write_text("schema_version: 1\nrules: []\n")
    result = call(project, tmp_path / "state", "lock", grants=Grants(), check=True)
    checked(result, 1)
    text = json.dumps(result.as_dict())
    assert "reprollm.yaml changed" in text
    assert ".reprollm/project-rules.yaml changed" in text
    assert text.index("reprollm.yaml changed") < text.index(".reprollm/project-rules.yaml changed")


def test_manual_add_preserves_explicit_duplicate_id_suffix_and_bindings(
    project: Path, tmp_path: Path
) -> None:
    untouched = (project / "untouched.py").read_bytes()
    for _ in range(3):
        checked(
            call(
                project,
                tmp_path / "state",
                "rules.add",
                field="custom.alpha",
                severity="WARNING",
                reason="  Keep alpha.  ",
                id="project.alpha",
                cli="--alpha",
                config="config.yaml:alpha",
                env="ALPHA",
            )
        )
    rules = read_rules(project).rules
    assert [item.id for item in rules] == ["project.alpha", "project.alpha_2", "project.alpha_3"]
    assert all(item.reason == "Keep alpha." and item.source == "manual" for item in rules)
    assert all(
        item.bindings.model_dump()
        == {"cli": "--alpha", "config": "config.yaml:alpha", "env": "ALPHA"}
        for item in rules
    )
    assert (project / "untouched.py").read_bytes() == untouched


def test_accept_exact_review_keeps_native_candidate_and_selected_overrides(
    project: Path, tmp_path: Path
) -> None:
    source = discovery(project)
    checked(
        call(
            project,
            tmp_path / "state",
            "rules.accept",
            grants=reviewed(project, source),
            candidate_id="c-000001",
            severity="CRITICAL",
            field="custom.override",
        )
    )
    rule = read_rules(project).rules[0]
    assert (rule.id, rule.field, rule.severity, rule.reason, rule.source, rule.candidate_id) == (
        "project.alpha",
        "custom.override",
        "CRITICAL",
        "Retain alpha.",
        "discover",
        "c-000001",
    )
    assert rule.bindings.model_dump() == {
        "cli": "--alpha",
        "config": "config.yaml:alpha",
        "env": "ALPHA",
    }


@pytest.mark.parametrize("change", ["body", "newer_filename"])
def test_accept_rejects_changed_review_not_same_id_replacement(
    project: Path, tmp_path: Path, change: str
) -> None:
    source = discovery(project)
    grant = reviewed(project, source)
    if change == "body":
        discovery(project, name="replacement")
    else:
        discovery(project, name="replacement", filename="20261030T000001Z.json")
    result = call(
        project, tmp_path / "state", "rules.accept", grants=grant, candidate_id="c-000001"
    )
    assert result.invocation in {"blocked", "user_error"}
    assert "action_unavailable" not in json.dumps(result.as_dict())
    assert "changed" in json.dumps(result.as_dict())
    assert not read_rules(project).rules


def test_ignore_accepted_precedes_missing_discovery(project: Path, tmp_path: Path) -> None:
    source = discovery(project)
    checked(
        call(
            project,
            tmp_path / "state",
            "rules.accept",
            grants=reviewed(project, source),
            candidate_id="c-000001",
        )
    )
    source.unlink()
    before = (project / ".reprollm/project-rules.yaml").read_bytes()
    result = call(project, tmp_path / "state", "rules.ignore", candidate_id="c-000001")
    assert result.cli_exit_code == 2 and result.invocation == "user_error"
    assert "already accepted" in json.dumps(result.as_dict())
    assert (project / ".reprollm/project-rules.yaml").read_bytes() == before


def test_ignore_then_accept_preserves_ignored_entry_active_takes_precedence(
    project: Path, tmp_path: Path
) -> None:
    source = discovery(project)
    checked(
        call(
            project,
            tmp_path / "state",
            "rules.ignore",
            grants=reviewed(project, source),
            candidate_id="c-000001",
            reason="Not now.",
        )
    )
    checked(
        call(
            project,
            tmp_path / "state",
            "rules.accept",
            grants=reviewed(project, source),
            candidate_id="c-000001",
        )
    )
    document = read_rules(project)
    assert document.rules[0].candidate_id == "c-000001"
    assert document.ignored_candidates[0].candidate_id == "c-000001"
    result = call(project, tmp_path / "state", "rules.candidates", grants=Grants(), json=True)
    checked(result)
    assert result.data[0]["status"] == "accepted"


def test_remove_restore_keeps_full_original_and_immutable_archive(
    project: Path, tmp_path: Path
) -> None:
    source = discovery(project)
    checked(
        call(
            project,
            tmp_path / "state",
            "rules.accept",
            grants=reviewed(project, source),
            candidate_id="c-000001",
        )
    )
    original = read_rules(project).rules[0]
    checked(
        call(
            project,
            tmp_path / "state",
            "rules.remove",
            rule_id=original.id,
            reason="Retired experiment.",
        )
    )
    files = sorted((project / ".reprollm/rule-archives").glob("*.json"))
    assert len(files) == 1 and read_rules(project).rules == []
    raw = files[0].read_bytes()
    archive = RuleArchive.model_validate_json(raw)
    assert archive.archive_id == files[0].stem == archive.content_id()
    assert archive.rule == original
    source.unlink()
    checked(call(project, tmp_path / "state", "rules.restore", archive_id=archive.archive_id))
    assert read_rules(project).rules == [original]
    assert files[0].read_bytes() == raw
    result = call(project, tmp_path / "state", "rules.restore", archive_id=archive.archive_id)
    assert result.invocation == "user_error" and result.cli_exit_code == 2
    assert files[0].read_bytes() == raw and read_rules(project).rules == [original]


def test_malformed_latest_discovery_has_no_older_fallback(project: Path, tmp_path: Path) -> None:
    discovery(project)
    latest = project / ".reprollm/discover/20261030T000002Z.json"
    latest.write_text("{invalid latest")
    before = latest.read_bytes()
    result = call(project, tmp_path / "state", "rules.candidates", grants=Grants(), json=True)
    assert result.invocation == "user_error" and result.cli_exit_code == 2
    assert "latest" in json.dumps(result.as_dict()) and latest.read_bytes() == before
