"""Run-specific machine privacy leaves portable experiment identities intact."""

from pathlib import Path

from reprollm.run.privacy import RunPrivacy


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
