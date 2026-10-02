"""UX2-T06: review, archive first, and restore accepted rules without discovery."""

from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest

from reprollm.cli.main import app, cli
from reprollm.core.errors import UserError
from reprollm.core.project_rules import load_project_rules
from reprollm.core.yaml_io import dump_yaml
from reprollm.schemas.discover_candidates import Candidate, DiscoverCandidates
from reprollm.schemas.project_rules import ProjectRule, ProjectRuleBindings, ProjectRules


@dataclass
class Result:
    exit_code: int
    output: str


class BoundaryRunner:
    """Exercise the same UserError boundary as the installed console script."""

    def invoke(self, _app: object, argv: list[str]) -> Result:
        stream = io.StringIO()
        original = sys.argv
        sys.argv = ["reprollm", *argv]
        try:
            with redirect_stdout(stream), redirect_stderr(stream):
                try:
                    cli()
                except SystemExit as exc:
                    code = int(exc.code or 0)
                else:
                    code = 0
        finally:
            sys.argv = original
        return Result(code, stream.getvalue())


runner = BoundaryRunner()


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "reprollm.yaml").write_text(
        "schema_version: 1\nproject: {name: lifecycle}\nexperiment: {profiles: []}\n"
    )
    (tmp_path / ".reprollm").mkdir()
    (tmp_path / ".reprollm/config.yaml").write_text("schema_version: 1\n")
    original = ProjectRule(
        id="project.alpha",
        field="custom.alpha",
        severity="CRITICAL",
        reason="Keep alpha.",
        source="discover",
        candidate_id="c-000001",
        accepted_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        bindings=ProjectRuleBindings(cli="--alpha", config="config.yaml:alpha", env="ALPHA"),
    )
    write_rules(tmp_path, ProjectRules(rules=[original]))
    monkeypatch.chdir(tmp_path)
    return tmp_path


def write_rules(root: Path, document: ProjectRules) -> None:
    (root / ".reprollm/project-rules.yaml").write_text(dump_yaml(document.model_dump(mode="json")))


def rules_bytes(root: Path) -> bytes:
    return (root / ".reprollm/project-rules.yaml").read_bytes()


def archives(root: Path) -> list[Path]:
    return sorted((root / ".reprollm/rule-archives").glob("*.json"))


def remove(root: Path) -> dict:
    result = runner.invoke(
        app, ["rules", "remove", "project.alpha", "--reason", "Experiment retired."]
    )
    assert result.exit_code == 0, result.output
    assert "lock" in result.output
    return json.loads(archives(root)[0].read_text())


def discovery(root: Path) -> Path:
    directory = root / ".reprollm/discover"
    directory.mkdir(exist_ok=True)
    document = DiscoverCandidates(
        reprollm_version="0.6.1",
        generated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        model="local-fixture",
        input_files=["config.yaml"],
        candidates=[
            Candidate(
                id=f"c-{index:06d}",
                kind="parameter",
                name=name,
                suggested_field=f"custom.{name}",
                suggested_severity="WARNING",
                confidence="high",
                rationale=f"Retain {name}.",
            )
            for index, name in enumerate(("alpha", "beta"), 1)
        ],
    )
    path = directory / "20260102T000000Z.json"
    path.write_text(document.model_dump_json())
    return path


def test_remove_archives_original_then_deactivates_and_preserves_owned_files(repo: Path) -> None:
    original = load_project_rules(repo).rules[0].model_dump(mode="json")
    config = (repo / ".reprollm/config.yaml").read_bytes()
    manifest = (repo / "reprollm.yaml").read_bytes()
    archive = remove(repo)
    assert archive["schema_version"] == 1
    assert archive["rule"] == original
    assert archive["reason"] == "Experiment retired."
    assert archive["archived_at"].endswith("Z")
    assert archive["archive_id"] == archives(repo)[0].stem
    assert not load_project_rules(repo).rules
    assert (repo / ".reprollm/config.yaml").read_bytes() == config
    assert (repo / "reprollm.yaml").read_bytes() == manifest
    assert (
        json.loads(runner.invoke(app, ["rules", "show", archive["archive_id"]]).output)["state"]
        == "inactive"
    )


def test_restore_without_discovery_keeps_complete_original_and_archive(repo: Path) -> None:
    original = load_project_rules(repo).rules[0]
    archive = remove(repo)
    retained = archives(repo)[0].read_bytes()
    result = runner.invoke(app, ["rules", "restore", archive["archive_id"]])
    assert result.exit_code == 0, result.output
    assert load_project_rules(repo).rules == [original]
    assert archives(repo)[0].read_bytes() == retained
    assert "lock" in result.output
    state = runner.invoke(app, ["rules", "show", archive["archive_id"]])
    assert json.loads(state.output)["state"] == "active-identical"


@pytest.mark.parametrize("reason", ["", "   "])
def test_remove_requires_nonempty_reason_before_writes(repo: Path, reason: str) -> None:
    original = rules_bytes(repo)
    result = runner.invoke(app, ["rules", "remove", "project.alpha", "--reason", reason])
    assert result.exit_code == 2
    assert rules_bytes(repo) == original and not archives(repo)


def test_unknown_rule_and_archive_do_not_write(repo: Path) -> None:
    original = rules_bytes(repo)
    assert (
        runner.invoke(app, ["rules", "remove", "project.absent", "--reason", "Unused"]).exit_code
        == 2
    )
    assert runner.invoke(app, ["rules", "restore", "ra-" + "0" * 16]).exit_code == 2
    assert rules_bytes(repo) == original and not archives(repo)


def test_failure_after_archive_keeps_active_rule_and_reports_truth(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from reprollm.core import rule_lifecycle

    original = rules_bytes(repo)

    def fail(*args: object, **kwargs: object) -> None:
        raise UserError("simulated write failure")

    monkeypatch.setattr(rule_lifecycle, "write_rules", fail)
    result = runner.invoke(app, ["rules", "remove", "project.alpha", "--reason", "Retired"])
    assert result.exit_code == 2, result.output
    assert "not removed" in result.output
    assert rules_bytes(repo) == original and len(archives(repo)) == 1
    archive = json.loads(archives(repo)[0].read_text())
    assert archive["archive_id"] in result.output
    result = runner.invoke(app, ["rules", "show", archive["archive_id"]])
    assert json.loads(result.output)["state"] == "active-identical"


def test_archive_failure_does_not_deactivate(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from reprollm.core import rule_lifecycle

    original = rules_bytes(repo)

    def fail(*args: object, **kwargs: object) -> None:
        raise UserError("archive unavailable")

    monkeypatch.setattr(rule_lifecycle, "save_archive", fail)
    result = runner.invoke(app, ["rules", "remove", "project.alpha", "--reason", "Retired"])
    assert result.exit_code == 2 and rules_bytes(repo) == original


@pytest.mark.parametrize("conflict", ["id", "candidate"])
def test_restore_conflicts_never_overwrite(repo: Path, conflict: str) -> None:
    original = load_project_rules(repo).rules[0]
    archive = remove(repo)
    altered = original.model_copy(
        update={"reason": "Changed", **({"id": "project.beta"} if conflict == "candidate" else {})}
    )
    write_rules(repo, ProjectRules(rules=[altered]))
    before = rules_bytes(repo)
    result = runner.invoke(app, ["rules", "restore", archive["archive_id"]])
    assert result.exit_code == 2 and rules_bytes(repo) == before
    assert archives(repo)
    assert (
        json.loads(runner.invoke(app, ["rules", "show", archive["archive_id"]]).output)["state"]
        == "conflict"
    )


@pytest.mark.parametrize("original_first", [True, False])
def test_candidate_conflict_takes_priority_over_identical_active_rule(
    repo: Path, original_first: bool
) -> None:
    original = load_project_rules(repo).rules[0]
    archive = remove(repo)
    retained = archives(repo)[0].read_bytes()
    conflicting = original.model_copy(update={"id": "project.beta", "reason": "Different rule."})
    active = [original, conflicting] if original_first else [conflicting, original]
    write_rules(repo, ProjectRules(rules=active))
    before = rules_bytes(repo)

    result = runner.invoke(app, ["rules", "show", archive["archive_id"]])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["state"] == "conflict"
    listing = runner.invoke(app, ["rules", "list"])
    assert listing.exit_code == 0 and "conflict" in listing.output
    assert runner.invoke(app, ["rules", "restore", archive["archive_id"]]).exit_code == 2
    assert rules_bytes(repo) == before and archives(repo)[0].read_bytes() == retained


def test_ignore_accepted_candidate_directs_to_remove_without_discovery(repo: Path) -> None:
    original = rules_bytes(repo)
    result = runner.invoke(app, ["rules", "ignore", "c-000001"])
    assert result.exit_code == 2 and "rules remove project.alpha" in result.output
    assert rules_bytes(repo) == original


def test_show_complete_rule_and_full_candidate_list(repo: Path) -> None:
    path = discovery(repo)
    original = load_project_rules(repo).rules[0].model_dump(mode="json")
    shown = runner.invoke(app, ["rules", "show", "project.alpha"])
    assert shown.exit_code == 0, shown.output
    assert json.loads(shown.output)["rule"] == original
    result = runner.invoke(app, ["rules", "list", "--candidates", "--json"])
    assert result.exit_code == 0, result.output
    rows = json.loads(result.output)
    assert [row["status"] for row in rows] == ["accepted", "pending"]
    assert rows[0]["candidate"]["rationale"] == "Retain alpha."
    assert rows[0]["source"] == path.relative_to(repo).as_posix()
    candidate = runner.invoke(app, ["rules", "show", "c-000002"])
    assert json.loads(candidate.output)["candidate"]["suggested_field"] == "custom.beta"
    # The established list --json remains an array of active rule objects.
    assert json.loads(runner.invoke(app, ["rules", "list", "--json"]).output) == [original]


def test_candidate_inspection_sanitizes_secrets_without_altering_source(repo: Path) -> None:
    path = discovery(repo)
    payload = json.loads(path.read_text())
    secret = "sk-" + "x" * 24
    payload["candidates"][0]["rationale"] = secret
    path.write_text(json.dumps(payload))
    before = path.read_bytes()
    for command in (["rules", "show", "c-000001"], ["rules", "list", "--candidates", "--json"]):
        result = runner.invoke(app, command)
        assert result.exit_code == 0 and secret not in result.output
    assert path.read_bytes() == before


@pytest.mark.parametrize("location", ["rule", "reason"])
def test_unsafe_archival_rejected_without_redacting_original(repo: Path, location: str) -> None:
    secret = "sk-" + "x" * 24
    reason = secret if location == "reason" else "Retired"
    if location == "rule":
        current = load_project_rules(repo)
        current.rules[0].reason = secret
        write_rules(repo, current)
    before = rules_bytes(repo)
    result = runner.invoke(app, ["rules", "remove", "project.alpha", "--reason", reason])
    assert result.exit_code == 2 and secret not in result.output
    assert rules_bytes(repo) == before and not archives(repo)


def test_archive_symlink_refused_without_reading_target(repo: Path, tmp_path: Path) -> None:
    outside = tmp_path / "external"
    outside.mkdir()
    (repo / ".reprollm/rule-archives").symlink_to(outside, target_is_directory=True)
    before = rules_bytes(repo)
    result = runner.invoke(app, ["rules", "remove", "project.alpha", "--reason", "Retired"])
    assert result.exit_code == 2 and not list(outside.iterdir()) and rules_bytes(repo) == before


def test_future_archive_schema_and_tampered_id_fail_closed(repo: Path) -> None:
    archive = remove(repo)
    path = archives(repo)[0]
    before = rules_bytes(repo)
    archive["schema_version"] = 2
    path.write_text(json.dumps(archive))
    result = runner.invoke(app, ["rules", "restore", path.stem])
    assert result.exit_code == 2 and "upgrade" in result.output
    assert rules_bytes(repo) == before
    archive["schema_version"] = 1
    archive["rule"]["reason"] = "Tampered"
    path.write_text(json.dumps(archive))
    assert runner.invoke(app, ["rules", "restore", path.stem]).exit_code == 2
    assert rules_bytes(repo) == before


def test_identical_archive_is_reused_without_overwriting(repo: Path) -> None:
    from reprollm.core.rule_lifecycle import load_archive, save_archive

    archive = remove(repo)
    path = archives(repo)[0]
    before = path.read_bytes()
    inode = path.stat().st_ino
    save_archive(repo, load_archive(repo, archive["archive_id"]))
    assert path.read_bytes() == before and path.stat().st_ino == inode


def test_publication_failure_keeps_rule_and_removes_temporary_copy(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from reprollm.core import rule_lifecycle

    before = rules_bytes(repo)

    def fail(*args: object, **kwargs: object) -> None:
        raise OSError("simulated publication failure")

    monkeypatch.setattr(rule_lifecycle.os, "link", fail)
    result = runner.invoke(app, ["rules", "remove", "project.alpha", "--reason", "Retired"])
    assert result.exit_code == 2 and "not removed" in result.output
    assert rules_bytes(repo) == before
    assert not list((repo / ".reprollm/rule-archives").iterdir())


def test_archive_file_symlink_is_rejected_before_read(repo: Path) -> None:
    archive = remove(repo)
    path = archives(repo)[0]
    retained = path.read_bytes()
    protected = repo / ".env"
    protected.write_bytes(retained)
    path.unlink()
    path.symlink_to(protected)
    before = rules_bytes(repo)
    result = runner.invoke(app, ["rules", "restore", archive["archive_id"]])
    assert result.exit_code == 2 and "symlink" in result.output
    assert rules_bytes(repo) == before and protected.read_bytes() == retained


def test_inspection_has_no_side_effects_and_empty_candidates_are_empty(repo: Path) -> None:
    original = rules_bytes(repo)
    (repo / ".reprollm/discover").mkdir()
    result = runner.invoke(app, ["rules", "list", "--candidates", "--json"])
    assert result.exit_code == 0 and json.loads(result.output) == []
    result = runner.invoke(app, ["rules", "show", "project.alpha"])
    assert result.exit_code == 0
    assert rules_bytes(repo) == original and not archives(repo)


def test_rule_source_symlink_is_rejected_before_archival(repo: Path) -> None:
    original = rules_bytes(repo)
    target = repo / ".reprollm/project-rules.yaml"
    protected = repo / ".env"
    protected.write_bytes(original)
    target.unlink()
    target.symlink_to(protected)
    result = runner.invoke(app, ["rules", "remove", "project.alpha", "--reason", "Retired"])
    assert result.exit_code == 2 and "symlink" in result.output
    assert protected.read_bytes() == original and not archives(repo)


@pytest.mark.parametrize("username", ["rule", "status", "discover"])
def test_machine_identity_filter_preserves_fixed_schema_and_source(
    repo: Path, monkeypatch: pytest.MonkeyPatch, username: str
) -> None:
    from reprollm.core import rule_lifecycle

    discovery(repo)
    monkeypatch.setattr(rule_lifecycle.getpass, "getuser", lambda: username)
    result = runner.invoke(app, ["rules", "list", "--candidates", "--json"])
    records = json.loads(result.output)
    assert records[0]["status"] == "accepted"
    shown = json.loads(runner.invoke(app, ["rules", "show", "project.alpha"]).output)
    assert shown["rule"]["source"] == "discover"
    assert shown["source"] == ".reprollm/project-rules.yaml"
    archive = remove(repo)
    shown = json.loads(runner.invoke(app, ["rules", "show", archive["archive_id"]]).output)
    assert shown["archive"]["rule"]["source"] == "discover"
    assert shown["source"] == f".reprollm/rule-archives/{archive['archive_id']}.json"


@pytest.mark.parametrize("identity", ["username", "hostname"])
def test_archive_id_prefix_is_not_treated_as_machine_identity(
    repo: Path, monkeypatch: pytest.MonkeyPatch, identity: str
) -> None:
    from reprollm.core import rule_lifecycle

    monkeypatch.setattr(
        rule_lifecycle.getpass, "getuser", lambda: "ra" if identity == "username" else "test-user"
    )
    monkeypatch.setattr(
        rule_lifecycle.socket,
        "gethostname",
        lambda: "ra" if identity == "hostname" else "test-host",
    )
    original = load_project_rules(repo).rules[0]
    archive = remove(repo)
    retained = archives(repo)[0].read_bytes()
    result = runner.invoke(app, ["rules", "show", archive["archive_id"]])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["archive"] == archive
    result = runner.invoke(app, ["rules", "restore", archive["archive_id"]])
    assert result.exit_code == 0, result.output
    assert load_project_rules(repo).rules == [original]
    assert archives(repo)[0].read_bytes() == retained


@pytest.mark.parametrize("identity", ["username", "hostname"])
@pytest.mark.parametrize("field", ["reason", "rule", "binding"])
def test_archive_id_exception_does_not_allow_machine_identity_in_variable_fields(
    repo: Path, monkeypatch: pytest.MonkeyPatch, identity: str, field: str
) -> None:
    from reprollm.core import rule_lifecycle

    monkeypatch.setattr(
        rule_lifecycle.getpass, "getuser", lambda: "ra" if identity == "username" else "test-user"
    )
    monkeypatch.setattr(
        rule_lifecycle.socket,
        "gethostname",
        lambda: "ra" if identity == "hostname" else "test-host",
    )
    current = load_project_rules(repo)
    if field == "rule":
        current.rules[0].reason = "Recorded by ra."
    elif field == "binding":
        current.rules[0].bindings = ProjectRuleBindings(cli="--ra")
    write_rules(repo, current)
    before = rules_bytes(repo)
    reason = "Recorded by ra." if field == "reason" else "Retired"
    result = runner.invoke(app, ["rules", "remove", "project.alpha", "--reason", reason])
    assert result.exit_code == 2 and "unsafe rule content" in result.output
    assert rules_bytes(repo) == before and not archives(repo)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("reason", "ra-" + "a" * 16),
        ("archive_id", "ra-not-a-content-id"),
        ("archive_id", "ra-" + "a" * 16 + "-extra"),
        ("archive_id", "ra-" + "A" * 16),
    ],
)
def test_archive_id_exception_is_limited_to_its_exact_field_and_format(
    repo: Path, monkeypatch: pytest.MonkeyPatch, key: str, value: str
) -> None:
    from reprollm.core import rule_lifecycle

    monkeypatch.setattr(rule_lifecycle.getpass, "getuser", lambda: "ra")
    assert rule_lifecycle.display_value(repo, {key: value}) != {key: value}


@pytest.mark.parametrize("operation", ["remove", "restore"])
def test_interposed_source_edit_is_preserved(
    repo: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    from reprollm.core import rule_lifecycle

    archive = remove(repo) if operation == "restore" else None
    read = rule_lifecycle._read_rules_bytes
    first = True
    changed: bytes | None = None

    def interpose(root: Path) -> bytes | None:
        nonlocal first, changed
        original = read(root)
        if first:
            first = False
            current = load_project_rules(root)
            if current.rules:
                current.rules[0].reason = "A concurrent edit."
            else:
                current.rules.append(
                    ProjectRule(
                        id="project.other",
                        field="custom.other",
                        severity="INFO",
                        reason="New rule.",
                        source="manual",
                        accepted_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
                    )
                )
            write_rules(root, current)
            changed = rules_bytes(root)
        return original

    monkeypatch.setattr(rule_lifecycle, "_read_rules_bytes", interpose)
    args = (
        ["remove", "project.alpha", "--reason", "Retired"]
        if archive is None
        else ["restore", archive["archive_id"]]
    )
    result = runner.invoke(app, ["rules", *args])
    assert result.exit_code == 2, result.output
    assert rules_bytes(repo) == changed
    assert len(archives(repo)) == 1


@pytest.mark.parametrize("operation", ["remove", "restore"])
def test_disappearance_after_snapshot_does_not_overwrite_recovery(
    repo: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    from reprollm.core import rule_lifecycle

    original = load_project_rules(repo).rules[0].model_dump(mode="json")
    archive = remove(repo) if operation == "restore" else None
    read = rule_lifecycle._read_rules_bytes
    first = True

    def interpose(root: Path) -> bytes | None:
        nonlocal first
        content = read(root)
        if first:
            first = False
            (root / ".reprollm/project-rules.yaml").unlink()
        return content

    monkeypatch.setattr(rule_lifecycle, "_read_rules_bytes", interpose)
    args = (
        ["remove", "project.alpha", "--reason", "Retired"]
        if archive is None
        else ["restore", archive["archive_id"]]
    )
    result = runner.invoke(app, ["rules", *args])
    assert result.exit_code == 2
    assert not (repo / ".reprollm/project-rules.yaml").exists()
    assert json.loads(archives(repo)[0].read_text())["rule"] == original


@pytest.mark.parametrize("operation", ["remove", "restore"])
def test_source_read_failure_is_exit_two_before_archival(
    repo: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    archive = remove(repo) if operation == "restore" else None
    before = rules_bytes(repo)
    prior_archives = archives(repo)
    read = Path.read_bytes

    def fail(path: Path) -> bytes:
        if path == repo / ".reprollm/project-rules.yaml":
            raise PermissionError("simulated unreadable source")
        return read(path)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_bytes", fail)
        args = (
            ["remove", "project.alpha", "--reason", "Retired"]
            if archive is None
            else ["restore", archive["archive_id"]]
        )
        result = runner.invoke(app, ["rules", *args])
    assert (
        result.exit_code == 2 and rules_bytes(repo) == before and archives(repo) == prior_archives
    )
