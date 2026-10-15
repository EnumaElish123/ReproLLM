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


@pytest.mark.security
@pytest.mark.parametrize(
    "value",
    [
        "ratio = count / total\nsteps = count // 2\n",
        'message = f"rate {count / total}"\n',
        'target = Path("outputs") / "result.json"\nseparator = "/"\n',
        r'pattern: "\\$|\\.|(\\-?[0-9.,]+)"',
        r'pattern = r"\d+\.\d+"',
    ],
)
def test_source_operators_and_regex_escapes_survive(privacy: RunPrivacy, value: str) -> None:
    assert privacy.text(value) == (value, 0)


@pytest.mark.security
@pytest.mark.parametrize(
    "value",
    [
        r"\\private-server\share\file",
        "//private-server/share/file",
        "file:///private-owner/file",
        "file://private-server/share/file",
        r"C:\private-owner\file",
        "/private-owner/file",
    ],
)
def test_paths_remain_private_when_next_to_source_operators(
    privacy: RunPrivacy, value: str
) -> None:
    text = f'ratio = count / total\ncache = "{value}"\n'
    safe, count = privacy.text(text)
    assert "ratio = count / total\n" in safe
    assert "private-server" not in safe and "private-owner" not in safe
    assert count == 1
    assert privacy.text(safe) == (safe, 0)


@pytest.mark.security
@pytest.mark.parametrize(
    "value",
    [
        "ratio = count /2\nsteps = count //2\n",
        "ratio = count /(total + 1)\n",
        'message = f"rate {count /2}"\n',
        "分母 = 2\nratio = 分母 /2\n",
        "count /=2\nsteps //=2\n",
        "ratio = (count  # /private-owner/cache\n /2)\n",
    ],
)
def test_python_snapshot_preserves_parsed_division_only(privacy: RunPrivacy, value: str) -> None:
    expected = value.replace("/private-owner/cache", "<REDACTED:path>")
    assert privacy.text(value, python_source=True)[0] == expected


@pytest.mark.security
@pytest.mark.parametrize(
    "value", ["///private-owner/cache", "//private-owner", "\\\\private-server\\"]
)
def test_repeated_path_separators_do_not_leak(privacy: RunPrivacy, value: str) -> None:
    safe, count = privacy.text(value)
    assert safe == "<REDACTED:path>" and count == 1


@pytest.mark.security
def test_python_strings_and_non_source_values_remain_private(privacy: RunPrivacy) -> None:
    value = 'ratio = count /2\ncache = "/private-owner/cache"\n'
    safe = privacy.text(value, python_source=True)[0]
    assert safe == 'ratio = count /2\ncache = "<REDACTED:path>"\n'
    assert privacy.text("count /private-owner/cache")[0] == "count <REDACTED:path>"


@pytest.mark.security
@pytest.mark.parametrize(
    "value",
    [
        'path = f"data/{args.bench_name}/question.jsonl"\n',
        'path = f"data/{args.bench_name}/model_answer/{args.model_id}.jsonl"\n',
        '"""Save {save_dir}/test_cases.json and {save_dir}/method_config.json."""\n',
        'prompt = "[INST] question [/INST]"\n',
    ],
)
def test_native_template_suffixes_and_instruction_tokens_survive(
    privacy: RunPrivacy, value: str
) -> None:
    assert privacy.text(value, python_source=True) == (value, 0)
    assert privacy.text(value) == (value, 0)


@pytest.mark.security
def test_instruction_token_exception_does_not_hide_other_bracketed_paths(
    privacy: RunPrivacy,
) -> None:
    value = "[/INST] [/private-owner/cache] }/private-owner/cache"
    assert privacy.text(value)[0] == "[/INST] [<REDACTED:path>] }<REDACTED:path>"


@pytest.mark.security
def test_absolute_template_paths_remain_private_and_idempotent(privacy: RunPrivacy) -> None:
    value = 'value = f"/private-owner/cache/{name}/suffix"\n'
    safe, count = privacy.text(value, python_source=True)
    assert "private-owner" not in safe and count > 0
    assert privacy.text(safe, python_source=True) == (safe, 0)


@pytest.mark.security
@pytest.mark.parametrize(
    "value", [r"\\-private-server\share\file", r"\\$private-server\share\file"]
)
def test_unc_server_punctuation_does_not_create_a_privacy_bypass(
    privacy: RunPrivacy, value: str
) -> None:
    assert privacy.text(value) == ("<REDACTED:path>", 1)
