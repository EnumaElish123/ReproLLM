"""OpenRouter endpoint hints are bounded AST signals, never persisted URLs (§14)."""

from __future__ import annotations

from pathlib import Path

import pytest

from reprollm.core import scanner as scanner_mod
from reprollm.core.context import AuditContext
from reprollm.core.pyscan import scan_python
from reprollm.integrations.openai_ import OpenAIIntegration
from reprollm.profiles.detect import run_detection


@pytest.mark.parametrize(
    "call",
    [
        'OpenAI(base_url="https://openrouter.ai/api/v1")',
        'openai.OpenAI(base_url="https://openrouter.ai/api/v1")',
        'AsyncOpenAI(base_url="https://openrouter.ai/api/v1")',
        'OpenAI(base_url="https://openrouter.ai/api/v1?api_key=fake-test-key")',
        'OpenAI(base_url="https://\\x6fpenrouter.ai/api/v1")',
    ],
)
def test_endpoint_adds_openrouter_after_existing_provider_hints(tmp_path: Path, call: str) -> None:
    (tmp_path / "client.py").write_text(
        "import openai, anthropic\nclient = " + call + "\n", encoding="utf-8"
    )
    ctx = AuditContext(tmp_path, level=0)
    scanned = scan_python(ctx.fs)

    evidence = OpenAIIntegration().detect(ctx.fs, pyscan=scanned)
    result = run_detection(ctx.fs, scanned, ctx.deps)

    assert result.hints.providers == ["openai", "anthropic", "openrouter"]
    assert result.profiles == [], "an endpoint hint must not add a profile"
    endpoint = next(item for item in evidence if item.note == "provider openrouter")
    assert endpoint.path == "client.py" and endpoint.line == 2
    assert endpoint.value is None and endpoint.field is None and endpoint.expected is None
    assert "https://" not in str(evidence)
    assert "fake-test-key" not in str(evidence)


@pytest.mark.parametrize(
    "source",
    [
        '# OpenAI(base_url="https://openrouter.ai/api/v1")\n',
        "'''OpenAI(base_url=\"https://openrouter.ai/api/v1\")'''\n",
        'url = "https://openrouter.ai/api/v1"\n',
        'base_url = "https://openrouter.ai/api/v1"\nOpenAI(base_url=base_url)\n',
        'OpenAI(url="https://openrouter.ai/api/v1")\n',
        'OpenAI(base_url=f"https://openrouter.ai/api/v1")\n',
        'OpenAI(base_url="https://api.openai.com/v1")\n',
        'config = {"base_url": "https://openrouter.ai/api/v1"}\n',
    ],
)
def test_non_endpoint_text_does_not_add_openrouter(tmp_path: Path, source: str) -> None:
    (tmp_path / "client.py").write_text(source, encoding="utf-8")
    ctx = AuditContext(tmp_path, level=0)

    result = run_detection(ctx.fs, scan_python(ctx.fs), ctx.deps)

    assert result.hints.providers == []


def test_cached_detection_does_not_rescan_endpoint_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "client.py").write_text(
        'OpenAI(base_url="https://openrouter.ai/api/v1")\n', encoding="utf-8"
    )
    ctx = AuditContext(tmp_path, level=0)
    scanned = scan_python(ctx.fs)

    def forbid_scan(*args, **kwargs):
        raise AssertionError("provider detection must reuse the bounded scan")

    monkeypatch.setattr("reprollm.integrations.openai_.scan_python", forbid_scan)

    assert any(
        item.note == "provider openrouter"
        for item in OpenAIIntegration().detect(ctx.fs, pyscan=scanned)
    )


def test_endpoint_detection_respects_python_file_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "a.py").write_text("pass\n", encoding="utf-8")
    (tmp_path / "z.py").write_text(
        'OpenAI(base_url="https://openrouter.ai/api/v1")\n', encoding="utf-8"
    )
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 1)
    ctx = AuditContext(tmp_path, level=0)

    result = run_detection(ctx.fs, scan_python(ctx.fs), ctx.deps)

    assert "openrouter" not in result.hints.providers
    assert ctx.fs.warnings == ["python file scan truncated to 1 of 2 files"]


def test_endpoint_detection_respects_python_read_cap(tmp_path: Path) -> None:
    (tmp_path / "client.py").write_text(
        "#"
        + "x" * scanner_mod.MAX_READ_BYTES
        + '\nOpenAI(base_url="https://openrouter.ai/api/v1")\n',
        encoding="utf-8",
    )
    ctx = AuditContext(tmp_path, level=0)

    result = run_detection(ctx.fs, scan_python(ctx.fs), ctx.deps)

    assert "openrouter" not in result.hints.providers


@pytest.mark.parametrize("identity", ["unsafe-user", "unsafe-host"])
def test_identity_bearing_endpoint_source_is_not_returned_as_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, identity: str
) -> None:
    source = tmp_path / identity / "client.py"
    source.parent.mkdir()
    source.write_text('OpenAI(base_url="https://openrouter.ai/api/v1")\n', encoding="utf-8")
    monkeypatch.setattr("getpass.getuser", lambda: "unsafe-user")
    monkeypatch.setattr("socket.gethostname", lambda: "unsafe-host")
    ctx = AuditContext(tmp_path, level=0)

    assert OpenAIIntegration().detect(ctx.fs, pyscan=scan_python(ctx.fs)) == []


def test_symlink_escape_is_not_returned_as_endpoint_evidence(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_text('OpenAI(base_url="https://openrouter.ai/api/v1")\n', encoding="utf-8")
    try:
        (root / "escaped.py").symlink_to(outside)
    except OSError:
        pytest.skip("symbolic links unavailable on this runner")
    ctx = AuditContext(root, level=0)

    assert OpenAIIntegration().detect(ctx.fs, pyscan=scan_python(ctx.fs)) == []
