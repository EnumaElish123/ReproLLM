"""Decode JSON syntax before sanitizing scalar text without rewriting safe bytes."""

import json

import pytest

from reprollm.run import json_text


def _unchanged(value: str) -> tuple[str, int]:
    return value, 0


@pytest.mark.security
@pytest.mark.parametrize(
    "text",
    [
        '  {"prompt" : "### Assistant A:\\n{answer_a}", "unicode": "\\u4e2d"}\r\n',
        '{\n  "prompt": "### Assistant A:\\n{answer_a}",\n  "other": []\n}\n',
        '{"prompt":"### Assistant A:\\n{answer_a}"}\r\n'
        '{"prompt":"### Assistant B:\\n{answer_b}"}\r\n',
        '[true, null, 42, "a\\/b", {"\\u006bey": "value"}]',
        '"### Assistant A:\\n{answer_a}"',
        '{"surrogate":"\\ud800"}',
    ],
)
def test_safe_json_and_jsonl_keep_original_bytes(text: str) -> None:
    assert json_text.redact_json_strings(text, _unchanged) == (text, 0)


@pytest.mark.security
def test_callback_receives_decoded_scalars_including_keys() -> None:
    paths = [
        r"C:\new\file.json",
        r"A:\new",
        r"\\private-server\share\file",
        "/private-owner/file",
        "file:///private-owner/file",
    ]
    original: dict[str, object] = {
        "prompt": "### Assistant A:\n{answer_a}",
        **dict.fromkeys(paths, "safe"),
        "values": paths,
    }
    text = json.dumps(original) + "\n"
    seen: list[str] = []

    def sanitize(value: str) -> tuple[str, int]:
        seen.append(value)
        return ("<REDACTED:path>", 1) if value in paths else (value, 0)

    result = json_text.redact_json_strings(text, sanitize)
    assert result is not None
    safe, count = result
    assert "### Assistant A:\n{answer_a}" in seen
    assert all(path in seen for path in paths)
    assert count == 10
    data = json.loads(safe)
    assert data["prompt"] == original["prompt"]
    assert data["values"] == ["<REDACTED:path>"] * len(paths)
    assert all(path not in data for path in paths)


def test_only_changed_token_is_reencoded() -> None:
    text = '{ "preserved" : "\\u4e2d\\/x", "path": "\\/private-owner\\/file" }\r\n'
    seen: list[str] = []

    def sanitize(value: str) -> tuple[str, int]:
        seen.append(value)
        return ("<REDACTED:path>", 1) if value == "/private-owner/file" else (value, 0)

    assert json_text.redact_json_strings(text, sanitize) == (
        '{ "preserved" : "\\u4e2d\\/x", "path": "<REDACTED:path>" }\r\n',
        1,
    )
    assert "/private-owner/file" in seen


@pytest.mark.security
def test_duplicate_keys_do_not_hide_earlier_scalar_tokens() -> None:
    text = '{"same":"/private-owner/first", "same":"safe"}'

    def sanitize(value: str) -> tuple[str, int]:
        return ("<REDACTED:path>", 1) if value.startswith("/private-owner/") else (value, 0)

    assert json_text.redact_json_strings(text, sanitize) == (
        '{"same":"<REDACTED:path>", "same":"safe"}',
        1,
    )


@pytest.mark.parametrize(
    "text",
    [
        "",
        " \n ",
        "message: value",
        "{'prompt': 'single quoted'}",
        '{"prompt":"safe",}',
        '{"prompt":"safe"}\n{"prompt":',
        '{"prompt":"safe"} {"prompt":"second"}',
        '{"prompt":"safe"}\n\n{"prompt":"second"}',
        '{"value":NaN}',
        '{"value":Infinity}',
        '{"value":-Infinity}',
        '{"value":"unterminated}',
    ],
)
def test_unrecognized_or_malformed_json_never_uses_partial_exemptions(text: str) -> None:
    seen: list[str] = []

    def sanitize(value: str) -> tuple[str, int]:
        seen.append(value)
        return value, 0

    assert json_text.redact_json_strings(text, sanitize) is None
    assert seen == []


@pytest.mark.parametrize("text", ["null", "true", "42", "[1, 2, 3]"])
def test_non_string_json_leaves_remain_typed_and_unchanged(text: str) -> None:
    assert json_text.redact_json_strings(text, _unchanged) == (text, 0)


@pytest.mark.security
@pytest.mark.parametrize(
    ("constant", "limit", "text"),
    [
        ("_LIMIT", 16, '{"value":"ééé"}'),
        ("_NODE_LIMIT", 4, '{"key":"a", "key":"b"}'),
        ("_NODE_LIMIT", 3, "[0, 1]\n[2, 3]\n"),
        ("_DEPTH_LIMIT", 2, '[[["value"]]]'),
    ],
)
def test_recognized_structure_limits_fail_closed(
    monkeypatch: pytest.MonkeyPatch, constant: str, limit: int, text: str
) -> None:
    monkeypatch.setattr(json_text, constant, limit)
    with pytest.raises(ValueError, match="capture structure.*limit exceeded"):
        json_text.redact_json_strings(text, _unchanged)


def test_python_json_parser_recursion_limit_fails_closed() -> None:
    text = "[" * 2_000 + "0" + "]" * 2_000
    with pytest.raises(ValueError, match="capture structure.*limit exceeded"):
        json_text.redact_json_strings(text, _unchanged)


def test_callback_failure_is_not_converted_into_raw_text_fallback() -> None:
    def sanitize(value: str) -> tuple[str, int]:
        raise ValueError("cannot safely transform scalar")

    with pytest.raises(ValueError, match="cannot safely transform scalar"):
        json_text.redact_json_strings('{"key":"value"}', sanitize)
