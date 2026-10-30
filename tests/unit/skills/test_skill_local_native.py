"""Compare complete local artifacts and read views with the original native CLI."""

from __future__ import annotations

import json
import shutil
from datetime import datetime

import pytest
from tests.unit.skills import test_skill_local_lifecycle as contract


@pytest.fixture(autouse=True)
def native_environment(monkeypatch):
    contract.no_external_effects.__wrapped__(monkeypatch)
    from reprollm.cli import rules
    from reprollm.core import rule_lifecycle
    from reprollm.lock import writer

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 30, 1, 2, 3, tzinfo=tz)

    for module in (rules, rule_lifecycle, writer):
        monkeypatch.setattr(module, "datetime", Clock)


@pytest.fixture
def project(tmp_path):
    return contract.project.__wrapped__(tmp_path)


def native(root, argv):
    from skill_runtime import invoke_cli

    result = invoke_cli(argv, root)
    assert result.exit_code == 0, result.stderr
    return result


def test_offline_lock_complete_native_document_bytes_summary_and_check(project, tmp_path):
    reference = tmp_path / "native"
    shutil.copytree(project, reference)
    expected = native(reference, ["lock", str(reference), "--offline", "--verify-api"])
    reply = contract.call(project, tmp_path / "state", "lock", offline=True, verify_api=True)
    contract.checked(reply)
    assert (project / "reprollm.lock").read_bytes() == (reference / "reprollm.lock").read_bytes()
    assert reply.data["stdout"] == expected.stdout
    expected_check = native(reference, ["lock", str(reference), "--check"])
    checked = contract.call(
        project, tmp_path / "state", "lock", grants=contract.Grants(), check=True
    )
    assert checked.data["stdout"] == expected_check.stdout and checked.data["reasons"] == []


def test_complete_rule_lifecycle_and_archive_match_original_native_bytes(project, tmp_path):
    from reprollm.schemas.rule_archive import RuleArchive

    source = contract.discovery(project)
    reference = tmp_path / "native"
    shutil.copytree(project, reference)
    state = tmp_path / "state"
    steps = [
        (
            "rules.add",
            {
                "field": "custom.beta",
                "severity": "INFO",
                "reason": "Public β",
                "id": "project.beta",
                "cli": "--beta",
                "env": "BETA",
            },
            [
                "rules",
                "add",
                "--field",
                "custom.beta",
                "--severity",
                "INFO",
                "--reason",
                "Public β",
                "--id",
                "project.beta",
                "--cli",
                "--beta",
                "--env",
                "BETA",
            ],
        ),
        (
            "rules.ignore",
            {"candidate_id": "c-000001", "reason": "Public postponed"},
            ["rules", "ignore", "c-000001", "--reason", "Public postponed"],
        ),
        (
            "rules.accept",
            {"candidate_id": "c-000001", "field": "custom.override", "severity": "CRITICAL"},
            ["rules", "accept", "c-000001", "--field", "custom.override", "--severity", "CRITICAL"],
        ),
        (
            "rules.remove",
            {"rule_id": "project.alpha", "reason": "Public retired"},
            ["rules", "remove", "project.alpha", "--reason", "Public retired"],
        ),
    ]
    for action, options, argv in steps:
        native(reference, argv)
        reply = contract.call(
            project,
            state,
            action,
            grants=contract.reviewed(project, source)
            if action in {"rules.accept", "rules.ignore"}
            else contract.Grants(write=True),
            **options,
        )
        contract.checked(reply)
        assert (project / ".reprollm/project-rules.yaml").read_bytes() == (
            reference / ".reprollm/project-rules.yaml"
        ).read_bytes()
    archive = next((project / ".reprollm/rule-archives").glob("*.json"))
    original = next((reference / ".reprollm/rule-archives").glob("*.json"))
    assert archive.name == original.name and archive.read_bytes() == original.read_bytes()
    assert RuleArchive.model_validate_json(archive.read_bytes()).content_id() == archive.stem
    native(reference, ["rules", "restore", archive.stem])
    contract.checked(contract.call(project, state, "rules.restore", archive_id=archive.stem))
    assert (project / ".reprollm/project-rules.yaml").read_bytes() == (
        reference / ".reprollm/project-rules.yaml"
    ).read_bytes()
    assert archive.read_bytes() == original.read_bytes()
    for action, options, argv in [
        ("rules.list", {"json": True}, ["rules", "list", "--json"]),
        ("rules.list", {"json": False}, ["rules", "list"]),
        ("rules.candidates", {"json": True}, ["rules", "list", "--candidates", "--json"]),
        ("rules.candidates", {"json": False}, ["rules", "list", "--candidates"]),
        ("rules.show", {"id": archive.stem}, ["rules", "show", archive.stem]),
        ("rules.show", {"id": "project.alpha"}, ["rules", "show", "project.alpha"]),
    ]:
        expected = native(reference, argv)
        reply = contract.call(project, state, action, grants=contract.Grants(), **options)
        assert reply.data == (
            json.loads(expected.stdout)
            if action == "rules.show" or options["json"]
            else expected.stdout
        )
