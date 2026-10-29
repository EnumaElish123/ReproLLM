"""Keep Makefile comment continuation separate from standalone shell comments."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.core.context import AuditContext
from reprollm.integrations.lm_eval import LmEvalIntegration

runner = CliRunner()


def _source(root: Path, path: str, text: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")


def _evidence(root: Path) -> list[dict[str, object]]:
    return [
        item.model_dump(exclude_none=True)
        for item in LmEvalIntegration().detect(AuditContext(root).fs)
    ]


@pytest.mark.parametrize("path", ["Makefile", "recipes/Makefile"])
def test_makefile_continued_comment_does_not_invent_a_framework_command(
    tmp_path: Path, path: str
) -> None:
    _source(tmp_path, path, "# ignored \\\nlm_eval --tasks fake\nall:\n\t@printf observed\n")

    assert _evidence(tmp_path) == []


@pytest.mark.parametrize("path", ["run.sh", "recipes/run.sh"])
def test_shell_comment_still_ends_before_the_next_physical_command(
    tmp_path: Path, path: str
) -> None:
    _source(tmp_path, path, "# ignored \\\nlm_eval --tasks real\n")

    assert _evidence(tmp_path) == [
        {"kind": "detection", "path": path, "line": 2, "note": "CLI: lm_eval"}
    ]


@pytest.mark.parametrize(
    "text",
    [
        "all:\n\tlm_eval --tasks real\n",
        "all:\n\tpython3 \\\n\t  -m lm_eval --tasks real\n",
    ],
)
def test_makefile_real_recipe_and_existing_command_continuation_keep_evidence(
    tmp_path: Path, text: str
) -> None:
    _source(tmp_path, "Makefile", text)

    assert _evidence(tmp_path) == [
        {"kind": "detection", "path": "Makefile", "line": 2, "note": "CLI: lm_eval"}
    ]


def test_makefile_comment_and_later_real_recipe_do_not_duplicate_evidence(tmp_path: Path) -> None:
    _source(
        tmp_path,
        "Makefile",
        "# ignored \\\nlm_eval --tasks fake\nall:\n\tlm_eval --tasks real\n",
    )

    assert _evidence(tmp_path) == [
        {"kind": "detection", "path": "Makefile", "line": 4, "note": "CLI: lm_eval"}
    ]


@pytest.mark.parametrize("path", ["Makefile", "run.sh"])
def test_public_audit_uses_the_file_specific_comment_boundary(tmp_path: Path, path: str) -> None:
    text = "# ignored \\\nlm_eval --tasks example\n"
    if path == "Makefile":
        text += "all:\n\t@printf observed\n"
    _source(tmp_path, path, text)
    before = (tmp_path / path).read_bytes()

    result = runner.invoke(app, ["audit", str(tmp_path), "--format", "json", "--fail-on", "never"])

    assert result.exit_code == 0, result.output
    high = [
        entry
        for entry in json.loads(result.stdout)["profiles"]["detected"]
        if entry["profile"] == "evaluation" and entry["confidence"] == "high"
    ]
    if path == "Makefile":
        assert high == []
    else:
        assert len(high) == 1
        assert [(item["path"], item["line"]) for item in high[0]["evidence"]] == [(path, 2)]
    assert result.stderr == ""
    assert (tmp_path / path).read_bytes() == before
