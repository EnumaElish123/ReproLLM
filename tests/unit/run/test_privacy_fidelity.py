"""Path-recognition fidelity at the run persistence boundary.

Regression for the snapshot-fidelity defect found in the 2026-09-27 lm-eval
real-run review: ``_ABSOLUTE_PATH`` swallowed literal closing tokens
(``</s>``) and relative glob suffixes (``**/*.json``) as absolute paths.
These cases pin the boundary — experiment values survive untouched while
real absolute paths and machine identities are still removed.
"""

from pathlib import Path

import pytest

from reprollm.run.privacy import RunPrivacy


@pytest.fixture
def privacy(tmp_path: Path) -> RunPrivacy:
    return RunPrivacy(tmp_path, hostname="gpu-node-7", username="czy")


# --- literal closing tokens and tag-like experiment values ------------------


@pytest.mark.parametrize(
    "value",
    [
        'generation: {stop: ["</s>"]}',
        "</think>",
        "chat template ends with </think> then output",
        "im_end: <|im_end|>",
        "<answer>42</answer>",
        "endtoken: <｜end▁of▁sentence｜>",  # deepseek-style closing marker
    ],
)
def test_closing_tokens_survive(privacy: RunPrivacy, value: str) -> None:
    assert privacy.text(value) == (value, 0)


# --- relative globs stay intact ----------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        "outputs/current/**/*.json",
        "outputs/current/**/*.jsonl",
        "**/*.jsonl",
        "data/**",
        "runs/*/metrics.json",
        "artifacts/2026*/*.parquet",
        "outputs/*.txt",
    ],
)
def test_relative_globs_survive(privacy: RunPrivacy, value: str) -> None:
    assert privacy.text(value) == (value, 0)


# --- real absolute paths are still recognized --------------------------------


def test_root_paths_relativized(privacy: RunPrivacy, tmp_path: Path) -> None:
    inside = tmp_path / "configs" / "eval.yaml"
    assert privacy.text(str(inside)) == ("configs/eval.yaml", 1)


@pytest.mark.parametrize(
    "value",
    [
        "/etc/passwd",
        "--cache=/opt/private",
        "/mnt/share_data/czy/weights",
        "C:\\Users\\czy\\file.txt",
        "\\\\private-server\\share\\file",
    ],
)
def test_outside_paths_redacted(privacy: RunPrivacy, value: str) -> None:
    redacted, count = privacy.text(value)
    assert count >= 1
    assert "<REDACTED:path>" in redacted
    for fragment in ("/etc/passwd", "/opt/private", "/mnt/", "Users", "private-server"):
        assert fragment not in redacted, (value, fragment)


def test_mixed_sentence_only_absolute_part_changes(privacy: RunPrivacy, tmp_path: Path) -> None:
    sentence = f"model at {tmp_path / 'model'} stops at </s> writes outputs/**/*.json"
    redacted, count = privacy.text(sentence)
    assert redacted == "model at model stops at </s> writes outputs/**/*.json"
    assert count == 1


# --- machine identity removal unchanged ---------------------------------------


def test_identities_still_removed(privacy: RunPrivacy) -> None:
    assert privacy.text("run on gpu-node-7 by czy")[0] == (
        "run on <REDACTED:hostname> by <REDACTED:username>"
    )


def test_identity_inside_path_context(privacy: RunPrivacy) -> None:
    redacted, _ = privacy.text("cache /home/czy/hf and host gpu-node-7")
    assert "<REDACTED:hostname>" in redacted
    assert "<REDACTED:path>" in redacted  # /home/czy/hf is outside the root


def test_url_paths_not_treated_as_local(privacy: RunPrivacy) -> None:
    value = "endpoint https://api.deepseek.com/v1/chat"
    redacted, count = privacy.text(value)
    assert "api.deepseek.com" in redacted
    assert "<REDACTED:path>" not in redacted
    assert count == 0


def test_idempotent_on_its_own_output(privacy: RunPrivacy, tmp_path: Path) -> None:
    first, _ = privacy.text(f"cfg {tmp_path / 'a.yaml'} at gpu-node-7")
    second, count = privacy.text(first)
    assert second == first
    assert count == 0
