"""Run-specific machine privacy leaves portable experiment identities intact."""

from pathlib import Path

import pytest

from reprollm.run.privacy import RunPrivacy

pytestmark = pytest.mark.security


def test_relative_paths_ids_urls_and_environment_controls_are_preserved(tmp_path: Path) -> None:
    privacy = RunPrivacy(tmp_path, hostname="test-node", username="researcher")
    value = "configs/eval.yaml Qwen/Qwen3-32B https://example.org/models/a MAX_TOKENS=2048"
    assert privacy.text(value) == (value, 0)


def test_absolute_paths_and_machine_identity_are_removed(tmp_path: Path) -> None:
    privacy = RunPrivacy(tmp_path, hostname="test-node", username="researcher")
    assert privacy.text(str(tmp_path / "config.yaml")) == ("config.yaml", 1)
    for value in (
        "/opt/data/input",
        "--cache=/opt/private",
        "C:\\Users\\researcher\\file.txt",
        "\\\\private-server\\share\\file",
        str(tmp_path / ".." / "outside"),
        "test-node researcher",
    ):
        redacted, count = privacy.text(value)
        assert count > 0 and value not in redacted
    assert privacy.text("a-researcher-b")[0] == "a-<REDACTED:username>-b"


def test_mapping_keys_and_nested_values_are_also_captured_text(tmp_path: Path) -> None:
    privacy = RunPrivacy(tmp_path, hostname="", username="")
    safe = privacy.value({"hf_01234567890123456789": [{"path": "/private/file"}]})
    assert safe == {"<REDACTED:huggingface>": [{"path": "<REDACTED:path>"}]}


@pytest.mark.parametrize(
    "value",
    [
        "./configs/eval.yaml",
        "../shared/eval.yaml",
        "Use ./configs/eval.yaml and ../shared/eval.yaml.",
    ],
)
def test_dot_relative_posix_paths_are_not_absolute(tmp_path: Path, value: str) -> None:
    privacy = RunPrivacy(tmp_path, hostname="privacy-node", username="privacy-owner")
    assert privacy.text(value) == (value, 0)


@pytest.mark.parametrize(
    "value", [r".C:\private-owner\file", r".\\private-node\share\file", "/home/private-owner/file"]
)
def test_true_absolute_paths_still_redact_after_punctuation(tmp_path: Path, value: str) -> None:
    privacy = RunPrivacy(tmp_path, hostname="privacy-node", username="privacy-owner")
    result, count = privacy.text(value)
    assert "<REDACTED:path>" in result and count > 0
    assert "private-owner" not in result and "private-node" not in result


def test_dot_relative_paths_still_redact_embedded_secrets_and_current_identity(
    tmp_path: Path,
) -> None:
    fake_key = "sk-" + "a" * 40
    privacy = RunPrivacy(tmp_path, hostname="privacy-node", username="privacy-owner")
    value = f"./configs/privacy-owner/privacy-node/{fake_key} ../public/eval.yaml"
    result, count = privacy.text(value)
    assert (
        result
        == "./configs/<REDACTED:username>/<REDACTED:hostname>/<REDACTED:openai> ../public/eval.yaml"
    )
    assert count == 3
