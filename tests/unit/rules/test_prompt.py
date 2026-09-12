"""M3-T03: prompt declarations and explicit file references."""

from pathlib import Path

import pytest

from reprollm.core.context import AuditContext
from reprollm.profiles.loader import resolve
from reprollm.rules.prompt import DeclaredRule, FewShotDeclaredRule, FileExistsRule
from reprollm.schemas.finding import FindingStatus, Severity
from tests.unit.rules.helpers import context, failures


@pytest.mark.parametrize("rule_type", [DeclaredRule, FewShotDeclaredRule, FileExistsRule])
def test_no_manifest_skips_prompts(tmp_path: Path, rule_type) -> None:
    assert rule_type.min_level == 1
    assert not rule_type().applies(AuditContext(tmp_path))


def test_prompt_map_declaration(tmp_path: Path) -> None:
    assert failures(DeclaredRule().check(context(tmp_path)))[0].severity == Severity.WARNING
    assert not failures(DeclaredRule().check(context(tmp_path, prompts={"system": {"text": ""}})))


def test_each_file_reference_checked_without_reading_content(tmp_path: Path) -> None:
    secret_like_text = "sk-not-a-real-secret-token-12345"
    (tmp_path / "prompt.txt").write_text(secret_like_text, encoding="utf-8")
    ctx = context(
        tmp_path,
        prompts={
            "system": {"path": "missing.txt"},
            "judge": {"path": "prompt.txt"},
            "inline": {"text": secret_like_text},
        },
    )
    result = FileExistsRule().check(ctx)
    assert [f.status for f in result] == [
        FindingStatus.PASS,
        FindingStatus.PASS,
        FindingStatus.FAIL,
    ]
    missing = failures(result)[0]
    assert missing.severity == Severity.CRITICAL
    assert missing.evidence[0].field == "prompts.system.path"
    assert missing.evidence[0].note == "referenced file missing"
    assert any(e.path == "missing.txt" for e in missing.evidence)
    assert secret_like_text not in "".join(f.model_dump_json() for f in result)
    assert (tmp_path / "prompt.txt").read_text() == secret_like_text


def test_directory_is_not_a_prompt_file(tmp_path: Path) -> None:
    (tmp_path / "prompts").mkdir()
    ctx = context(tmp_path, prompts={"system": {"path": "prompts"}})
    assert failures(FileExistsRule().check(ctx))


def test_large_explicit_prompt_is_not_limited_by_scanner_caps(tmp_path: Path) -> None:
    (tmp_path / "large.txt").write_bytes(b"x" * (2 * 1024 * 1024 + 1))
    ctx = context(tmp_path, prompts={"system": {"path": "large.txt"}})
    assert not failures(FileExistsRule().check(ctx))


def test_inline_empty_prompt_exists_and_todo_source_skips(tmp_path: Path) -> None:
    ctx = context(tmp_path, prompts={"system": {"text": ""}, "judge": {}})
    result = FileExistsRule().check(ctx)
    assert result[0].status == FindingStatus.SKIPPED
    assert result[1].status == FindingStatus.PASS
    assert not FileExistsRule().applies(context(tmp_path))


def test_few_shot_is_explicit_even_when_count_is_zero(tmp_path: Path) -> None:
    rule = FewShotDeclaredRule()
    assert (
        failures(rule.check(context(tmp_path, prompts={"system": {"text": ""}})))[0].severity
        == Severity.INFO
    )
    for few_shot in [{}, {"n": 0}, {"path": "examples.txt"}]:
        ctx = context(
            tmp_path, prompts={"system": {"text": ""}, "judge": {"text": "", "few_shot": few_shot}}
        )
        assert not failures(rule.check(ctx))


def test_prompt_profile_selection(tmp_path: Path) -> None:
    assert "prompt.file_exists" in resolve([], tmp_path).rules
    assert {"prompt.declared", "prompt.few_shot_declared"} <= set(
        resolve(["inference"], tmp_path).rules
    )
