"""Finite positive expression proofs reject opaque computed-mapping contexts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from tests.unit.skills.test_skill_discover_content import native_messages, worker
from tests.unit.skills.test_skill_discover_content_review import write_source

SCRIPTS = Path(__file__).resolve().parents[3] / "skills/reprollm/scripts"
sys.path.insert(0, str(SCRIPTS))
import skill_discover as discover  # noqa: E402
from skill_request import Request  # noqa: E402
from skill_runtime_frame import validate_frame  # noqa: E402

OPAQUE = [
    "f\"/tmp/{builtins.dict([('pass' 'word', 'SyntheticNestedSecretValue123')])}\"",
    "f\"/tmp/{dict.__call__([('pass' 'word', 'SyntheticNestedSecretValue123')])}\"",
    "f\"{builtins.dict([('pass' 'word', 'SyntheticNestedSecretValue123')])}/results\"",
    "f\"/tmp/{OrderedDict([('pass' 'word', 'SyntheticNestedSecretValue123')])}\"",
    "f\"/tmp/{factory('pass' 'word', 'SyntheticNestedSecretValue123')}\"",
    "f\"/tmp/{getattr(builtins, 'dict')([('pass' 'word', 'SyntheticNestedSecretValue123')])}\"",
    "f\"/tmp/{[('pass' 'word', 'SyntheticNestedSecretValue123')]}\"",
    "f\"/tmp/{random.randint(0, int('SyntheticNestedSecretValue123'))}\"",
    'f"/tmp/{random.randint(a=0, b=99)}"',
    'f"/tmp/{os.getcwd(*[])}"',
    "f\"/tmp/{name:{'computed'}}\"",
    'f"/tmp/{public_factory()}"',
]


@pytest.mark.parametrize("expression", OPAQUE)
def test_actual_worker_rejects_every_unproven_expression_without_approval(
    tmp_path: Path, expression: str
) -> None:
    root = tmp_path / "research"
    root.mkdir()
    write_source(root, "python", expression)
    assert expression in native_messages(root)[1]["content"]
    request = Request("discover.preview", str(root), {"experimental": True, "show_content": True})
    raw = worker(request, tmp_path / "cache")
    result = validate_frame(raw, expected_action=request.action)
    assert result.invocation == "blocked" and result.data is None
    assert result.diagnostics == [{"code": "discover_review_content_unsafe"}]
    assert b"approval_requirements" not in raw and b"SyntheticNestedSecretValue123" not in raw
    assert not (tmp_path / "cache").exists()


@pytest.mark.parametrize("expression", OPAQUE[:3])
def test_opaque_factory_with_old_grant_never_reads_credentials_or_starts_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, expression: str
) -> None:
    import httpx
    from tests.unit.skills.test_skill_discover import Context, approved

    import reprollm.cli.discover as native

    root = tmp_path / "research"
    root.mkdir()
    (root / "README.md").write_text("Public experiment\n")
    context = Context(root, tmp_path / "home")
    request = approved(root, context.home)
    write_source(root, "python", expression)
    monkeypatch.setattr(
        native, "_endpoint_credentials", lambda *a: pytest.fail("credentials accessed")
    )
    monkeypatch.setattr(discover.Ledger, "__init__", lambda *a: pytest.fail("ledger created"))
    monkeypatch.setattr(httpx.Client, "__init__", lambda *a, **kw: pytest.fail("Client created"))
    result = discover.execute(request, context)
    assert result.invocation == "blocked"
    assert result.diagnostics == [{"code": "discover_review_content_unsafe"}]
    assert "SyntheticNestedSecretValue123" not in json.dumps(result.as_dict())


@pytest.mark.parametrize("prefix", ["/api/", "/usr/local/", "~/models/"])
def test_portable_literal_prefix_is_not_a_proof_for_readme_computation(
    tmp_path: Path, prefix: str
) -> None:
    root = tmp_path / "research"
    root.mkdir()
    source = 'f"' + prefix + "{factory('pass' 'word', 'SyntheticNestedSecretValue123')}\""
    (root / "README.md").write_text(source + "\n", encoding="utf-8")
    assert source in native_messages(root)[1]["content"]
    request = Request("discover.preview", str(root), {"experimental": True, "show_content": True})
    result = validate_frame(worker(request, tmp_path / "cache"), expected_action=request.action)
    assert result.invocation == "blocked" and result.data is None
    assert result.diagnostics == [{"code": "discover_review_content_unsafe"}]


@pytest.mark.parametrize(
    "expression",
    [
        'f"/tmp/{base}"',
        'f"/tmp/{self.name}"',
        "f\"/tmp/{names['public']}\"",
        'f"/tmp/{names[0]}"',
        'f"/tmp/{random.randint(0, 99 ** 10)}"',
        'f"{os.getcwd()}/results"',
        'f"/tmp/{count:04d}"',
    ],
)
def test_actual_worker_keeps_only_supported_expression_grammar_exact(
    tmp_path: Path, expression: str
) -> None:
    root = tmp_path / "research"
    root.mkdir()
    (root / "README.md").write_text("Model boundary [/INST]\n", encoding="utf-8")
    write_source(root, "python", expression)
    expected = native_messages(root)
    request = Request("discover.preview", str(root), {"experimental": True, "show_content": True})
    result = validate_frame(worker(request, tmp_path / "cache"), expected_action=request.action)
    assert result.invocation == "handled_result" and result.complete
    assert result.data["messages"] == expected


@pytest.mark.parametrize(
    "path", ["~/datasets/reference", "/api/completions", "/usr/local/tool/env.sh"]
)
def test_paired_inline_code_delimiter_is_outside_the_portable_literal(
    tmp_path: Path, path: str
) -> None:
    root = tmp_path / "research"
    root.mkdir()
    (root / "README.md").write_text("Use `" + path + "`\n", encoding="utf-8")
    expected = native_messages(root)
    request = Request("discover.preview", str(root), {"experimental": True, "show_content": True})
    result = validate_frame(worker(request, tmp_path / "cache"), expected_action=request.action)
    assert result.invocation == "handled_result" and result.complete
    assert result.data["messages"] == expected


@pytest.mark.parametrize(
    "text",
    [
        "~/models/reference`",
        "``~/models/reference`",
        "`~/models/reference``",
        "`~/models/ref`actory()`",
        "`~/models/{factory()} `",
        "`/api/{factory()}`",
        "`~/../private`",
        "`/home/foreign-person/private`",
    ],
)
def test_inline_code_delimiters_never_prove_computed_or_private_paths(
    tmp_path: Path, text: str
) -> None:
    root = tmp_path / "research"
    root.mkdir()
    (root / "README.md").write_text(text + "\n", encoding="utf-8")
    request = Request("discover.preview", str(root), {"experimental": True, "show_content": True})
    result = validate_frame(worker(request, tmp_path / "cache"), expected_action=request.action)
    assert result.invocation == "blocked" and result.data is None
    assert result.diagnostics == [{"code": "discover_review_content_unsafe"}]
