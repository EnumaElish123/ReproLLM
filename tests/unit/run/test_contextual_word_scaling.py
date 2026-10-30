"""Large ordinary text retains privacy fidelity without repeated suffix scans."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from reprollm.run.privacy import RunPrivacy


@pytest.mark.parametrize("shape", ["plain", "json", "fragment"])
def test_large_plain_scalar_completes_privacy_before_paging(shape: str) -> None:
    code = r"""
import json, sys
from pathlib import Path
from reprollm.run.privacy import RunPrivacy
word = "量" * 200_000
shape = sys.argv[1]
text = json.dumps({"text": word}, ensure_ascii=False) if shape == "json" else word
if shape == "fragment":
    text = "ordinary prose! text=" + word + "; visible=42"
safe, count = RunPrivacy(Path.cwd(), hostname="", username="").text(text)
assert safe == text and count == 0
print(json.dumps({"characters": len(safe), "redactions": count}))
"""
    try:
        result = subprocess.run(
            [sys.executable, "-c", code, shape],
            capture_output=True,
            timeout=10,
            check=False,
        )
    except subprocess.TimeoutExpired:
        pytest.fail("Privacy repeatedly rescanned a large ordinary scalar before pagination.")
    assert result.returncode == 0
    assert json.loads(result.stdout)["characters"] >= 200_000
    assert json.loads(result.stdout)["redactions"] == 0


@pytest.mark.parametrize(
    ("text", "expected", "count"),
    [
        (
            "ordinary prose! api_key=synthetic12345; visible=42",
            "ordinary prose! api_key=<REDACTED:generic_kv>; visible=42",
            1,
        ),
        (
            "ordinary prose! password='synthetic12345' visible=42",
            "ordinary prose! password='<REDACTED:generic_kv>' visible=42",
            1,
        ),
    ],
)
def test_unquoted_context_still_redacts_secret_values(
    tmp_path: Path, text: str, expected: str, count: int
) -> None:
    assert RunPrivacy(tmp_path, hostname="", username="").text(text) == (expected, count)


@pytest.mark.parametrize(
    ("text", "cursor", "key"),
    [
        ("prefixapi_key=synthetic12345", 6, "api_key"),
        ("prefix.api_key:  synthetic12345", 7, "api_key"),
        ("prose! early key=value", 9, "key"),
        ('prefix"api_key": "synthetic12345"', 6, '"api_key"'),
    ],
)
def test_scan_preserves_a_key_suffix_at_the_requested_cursor(
    text: str, cursor: int, key: str
) -> None:
    from reprollm.run.contextual_text import _search_key

    match = _search_key(text, cursor)
    assert match is not None
    assert match["key"] == key
    assert match.start() >= cursor
    assert text[match.end() :].startswith(("synthetic12345", "value", '"synthetic12345"'))
