"""Independent-review regressions: explicit source proofs and decoded mapping context."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from tests.unit.skills.test_skill_discover_content import native_messages, worker

SCRIPTS = Path(__file__).resolve().parents[3] / "skills/reprollm/scripts"
sys.path.insert(0, str(SCRIPTS))
import skill_discover as discover  # noqa: E402
from skill_request import Request  # noqa: E402
from skill_runtime_frame import validate_frame  # noqa: E402

UNPROVED = [
    ("readme", "{base}/home/foreign-person/private.yaml"),
    ("readme", "{base}/tmp/private-output"),
    ("readme", "{base}/unknown-root/private.yaml"),
    ("python", 'f"{base}/nested/results"'),
    ("python", 'f"{base}/home/foreign-person/private.yaml"'),
    ("python", 'f"/tmp/{base}/nested/results"'),
]
KEYED = [
    r'f"/tmp/{call({\'pass\u0077ord\': \'SyntheticNestedSecretValue123\'})}"'.replace("\\'", "'"),
    r'f"{call({\'pass\u0077ord\': \'SyntheticNestedSecretValue123\'})}/results"'.replace(
        "\\'", "'"
    ),
    r'f"/tmp/{call({\'outer\': {\'pass\u0077ord\': \'SyntheticNestedSecretValue123\'}})}"'.replace(
        "\\'", "'"
    ),
    r'f"/tmp/{call({\'pass\u0077ord\': [\'SyntheticNestedSecretValue123\']})}"'.replace("\\'", "'"),
    r'f"/tmp/{call({\'pass\' + \'word\': \'SyntheticNestedSecretValue123\'})}"'.replace("\\'", "'"),
    r'f"/tmp/{call({\'pass\u0077ord\': \'Syn\' + \'the\' + \'tic\' + \'123\'})}"'.replace(
        "\\'", "'"
    ),
    r'f"/tmp/{base:{call({\'pass\u0077ord\': \'SyntheticNestedSecretValue123\'})}}"'.replace(
        "\\'", "'"
    ),
    r'f"/tmp/{dict([(\'pass\u0077ord\', \'SyntheticNestedSecretValue123\')])}"'.replace("\\'", "'"),
    "f\"/tmp/{call({'pass' 'word': 'SyntheticNestedSecretValue123'})}\"",
    "f\"/tmp/{base:{call({'pass' + 'word': 'SyntheticNestedSecretValue123'})}}\"",
    "f\"/tmp/{call({**{'pass' 'word': 'SyntheticNestedSecretValue123'}})}\"",
    "f\"/tmp/{call({unknown_key: 'SyntheticNestedSecretValue123'})}\"",
]


def write_source(root: Path, kind: str, content: str) -> None:
    if kind == "readme":
        (root / "README.md").write_text(content + "\n", encoding="utf-8")
    else:
        (root / "train.py").write_text(
            "from dataclasses import dataclass\n@dataclass\nclass Args:\n"
            "    path: str = " + content + "\n",
            encoding="utf-8",
        )


@pytest.mark.parametrize("kind,content", UNPROVED + [("python", text) for text in KEYED])
def test_real_worker_refuses_unproven_template_and_decoded_keyed_values(
    tmp_path: Path, kind: str, content: str
) -> None:
    if kind == "python" and "\\" in content and sys.version_info < (3, 12):
        pytest.skip("Python <3.12 does not collect backslashes in f-string expressions")
    root = tmp_path / "research"
    root.mkdir()
    write_source(root, kind, content)
    expected = native_messages(root)
    assert content in expected[1]["content"]
    request = Request("discover.preview", str(root), {"experimental": True, "show_content": True})
    raw = worker(request, tmp_path / "cache")
    result = validate_frame(raw, expected_action=request.action)
    assert result.invocation == "blocked" and not result.complete
    assert result.data is None
    assert result.diagnostics == [{"code": "discover_review_content_unsafe"}]
    assert b"approval_requirements" not in raw and b"SyntheticNestedSecretValue123" not in raw
    assert not (tmp_path / "cache").exists()


@pytest.mark.parametrize("kind,content", [UNPROVED[0], ("python", KEYED[4])])
def test_unsafe_source_is_refused_before_credential_ledger_or_send(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str, content: str
) -> None:
    import httpx
    from tests.unit.skills.test_skill_discover import Context, approved

    import reprollm.cli.discover as native

    root = tmp_path / "research"
    root.mkdir()
    (root / "README.md").write_text("Public experiment\n")
    context = Context(root, tmp_path / "home")
    request = approved(root, context.home)
    write_source(root, kind, content)
    monkeypatch.setattr(
        native, "_endpoint_credentials", lambda *args: pytest.fail("credentials accessed")
    )
    monkeypatch.setattr(discover.Ledger, "__init__", lambda *args: pytest.fail("ledger created"))
    monkeypatch.setattr(
        httpx.Client, "__init__", lambda *args, **kwargs: pytest.fail("Client created")
    )
    result = discover.execute(request, context)
    assert result.invocation == "blocked" and not result.complete
    assert result.diagnostics == [{"code": "discover_review_content_unsafe"}]
    assert "approval_requirements" not in json.dumps(result.as_dict())
    assert not (context.home / "operations/discovery-budgets").exists()


def test_literal_public_mapping_keeps_exact_source_and_closing_tokens(tmp_path: Path) -> None:
    root = tmp_path / "research"
    root.mkdir()
    (root / "README.md").write_text("Original model token [/INST]\n", encoding="utf-8")
    write_source(root, "python", "f\"/tmp/{call({'public': {'count': 2}})}\"")
    expected = native_messages(root)
    request = Request("discover.preview", str(root), {"experimental": True, "show_content": True})
    result = validate_frame(worker(request, tmp_path / "cache"), expected_action=request.action)
    assert result.invocation == "handled_result" and result.complete
    assert result.data["messages"] == expected
