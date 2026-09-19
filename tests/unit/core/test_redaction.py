"""Executable secret policy and streaming boundaries (M5-T01, spec §16)."""

from collections.abc import Iterator

import pytest
import yaml

from reprollm.core import redaction
from tests.unit.core.test_secret_corpus import CORPUS


@pytest.mark.parametrize("sample", (CORPUS / "positive.txt").read_text().splitlines())
def test_positive_corpus_is_redacted(sample: str) -> None:
    result, count = redaction.redact_text(sample)
    assert count >= 1
    assert result != sample
    assert "<REDACTED:" in result
    assert redaction.redact_text(result)[0] == result


@pytest.mark.parametrize("sample", (CORPUS / "negative.txt").read_text().splitlines())
def test_negative_corpus_is_unchanged(sample: str) -> None:
    assert redaction.redact_text(sample) == (sample, 0)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        (name, expected)
        for group in yaml.safe_load((CORPUS / "env_cases.yaml").read_text()).values()
        for name, expected in group.items()
    ],
)
def test_environment_name_corpus(name: str, expected: bool) -> None:
    assert redaction.is_secret_env_name(name) is expected
    assert redaction.is_secret_env_name(name.lower()) is expected


def test_generic_redaction_preserves_the_key_separator_and_quotes() -> None:
    assert redaction.redact_text('api_key: "abcdefgh1234"') == (
        'api_key: "<REDACTED:generic_kv>"',
        1,
    )
    assert redaction.redact_text("password='abcdefgh1234' trailing") == (
        "password='<REDACTED:generic_kv>' trailing",
        1,
    )


@pytest.mark.parametrize("header_padding", ["", "=", "=="])
@pytest.mark.parametrize("payload_padding", ["", "=", "=="])
@pytest.mark.parametrize("signature_padding", ["", "=", "=="])
def test_jwt_padding_is_consumed_completely(
    header_padding: str, payload_padding: str, signature_padding: str
) -> None:
    sample = (
        f"eyJhbGciOiAiSFMyNTYifQ{header_padding}."
        f"eyJzdWIiOiIxMjM0NTY3ODkwIn0{payload_padding}."
        f"c2lnbmF0dXJlMTIzNA{signature_padding}"
    )
    assert redaction.redact_text(sample) == ("<REDACTED:jwt>", 1)
    assert list(redaction.redact_lines(iter([sample]))) == ["<REDACTED:jwt>"]


def test_pattern_order_and_per_artifact_count() -> None:
    assert redaction.redact_text("api_key=sk-0123456789abcdef") == (
        "api_key=<REDACTED:generic_kv>",
        2,
    )
    assert redaction.redact_text("hf_01234567890123456789 sk-0123456789abcdef") == (
        "<REDACTED:huggingface> <REDACTED:openai>",
        2,
    )
    assert redaction.redact_text("") == ("", 0)


@pytest.mark.parametrize("kind", ["RSA", "EC", "OPENSSH", ""])
def test_multiline_private_keys_are_removed_as_a_whole(kind: str) -> None:
    label = f"{kind} PRIVATE KEY".strip()
    sample = f"before -----BEGIN {label}-----\nprivate material\n-----END {label}----- after\n"
    assert redaction.redact_text(sample) == ("before <REDACTED:pem> after\n", 1)
    assert "".join(redaction.redact_lines(iter(sample.splitlines(keepends=True)))) == (
        "before <REDACTED:pem> after\n"
    )


def test_stream_handles_inline_and_adjacent_pem_blocks() -> None:
    sample = (
        "-----BEGIN EC PRIVATE KEY-----one-----END EC PRIVATE KEY-----"
        "-----BEGIN RSA PRIVATE KEY-----two-----END RSA PRIVATE KEY-----\n"
        "https://user:p%40ss@host\r\n"
    )
    assert "".join(redaction.redact_lines(iter(sample.splitlines(keepends=True)))) == (
        "<REDACTED:pem><REDACTED:pem>\nhttps://<REDACTED:url_cred>@host\r\n"
    )


def test_unterminated_private_key_never_leaks_or_buffers_the_body() -> None:
    consumed = []

    def lines() -> Iterator[str]:
        for line in ("prefix -----BEGIN OPENSSH PRIVATE KEY-----\n", "private material\n", ""):
            consumed.append(line)
            yield line

    stream = redaction.redact_lines(lines())
    assert next(stream) == "prefix <REDACTED:pem>"
    assert len(consumed) == 1
    assert list(stream) == []
    assert len(consumed) == 3
    assert list(redaction.redact_lines(iter([]))) == []
    assert "".join(redaction.redact_lines(iter(["", "plain\n"]))) == "plain\n"


def test_environment_allowlist_omits_unlisted_names_and_never_records_secrets() -> None:
    env = {
        "OPENAI_API_KEY": "must-not-leak",
        "HF_TOKEN": "also-must-not-leak",
        "DATABASE_URL": "database-credential",
        "MY_SERVICE_PASSWORD": "custom-secret",
        "UNLISTED": "private-value",
        "CUDA_VISIBLE_DEVICES": "0",
        "TOKENIZERS_PARALLELISM": "false",
        "SLURM_JOB_ACCOUNT_TOKEN": "scheduler-secret",
        "VLLM_TEST": "hf_01234567890123456789",
        "CUSTOM_VISIBLE": "benign",
        "CUSTOM_SECRET": "still-secret",
    }
    result = redaction.redact_env(env, "allowlist", ["CUSTOM_"])
    assert result == {
        "CUDA_VISIBLE_DEVICES": "0",
        "CUSTOM_SECRET": {"present": True},
        "CUSTOM_VISIBLE": "benign",
        "DATABASE_URL": {"present": True},
        "HF_TOKEN": {"present": True},
        "OPENAI_API_KEY": {"present": True},
        "SLURM_JOB_ACCOUNT_TOKEN": {"present": True},
        "TOKENIZERS_PARALLELISM": "false",
        "VLLM_TEST": "<REDACTED:huggingface>",
    }
    assert list(result) == sorted(result)
    assert env["VLLM_TEST"] == "hf_01234567890123456789"


def test_environment_all_captures_every_name_with_redacted_values() -> None:
    assert redaction.redact_env(
        {"MY_SERVICE_PASSWORD": "hidden", "OTHER": "sk-0123456789abcdef", "EMPTY": ""},
        "all",
        [],
    ) == {
        "EMPTY": "",
        "MY_SERVICE_PASSWORD": {"present": True},
        "OTHER": "<REDACTED:openai>",
    }
    assert redaction.redact_env({}, "allowlist", []) == {}


def test_secret_name_precedes_explicit_allowlist() -> None:
    assert redaction.redact_env({"KEY_FRAMES": "secret"}, "allowlist", ["KEY_FRAMES"]) == {
        "KEY_FRAMES": {"present": True}
    }


def test_environment_rejects_unknown_capture_mode() -> None:
    with pytest.raises(ValueError, match="env_capture"):
        redaction.redact_env({}, "unknown", [])  # type: ignore[arg-type]
