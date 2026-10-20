"""pyscan + redaction file-matcher tests (M2-T03)."""

from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import IO, Any

import pytest

from reprollm.core import scanner as scanner_mod
from reprollm.core.git import GitInfo, inspect_git
from reprollm.core.pyscan import PyScanResult, PythonCandidateCoverage, scan_python
from reprollm.core.redaction import is_forbidden_file
from reprollm.core.scanner import RepoScanner


def _scan(repo: Path):
    return scan_python(RepoScanner(repo, inspect_git(repo)))


def test_imports_collected_with_locations(tmp_path: Path) -> None:
    repo = tmp_path / "pys"
    repo.mkdir()
    (repo / "a.py").write_text("import torch\nfrom datasets import load_dataset\n")
    (repo / "b.py").write_text("from vllm import LLM, SamplingParams\nimport yaml\n")
    result = _scan(repo)
    modules = result.module_names()
    assert {"torch", "datasets", "vllm", "yaml"} <= modules
    assert "load_dataset" not in modules  # only module names, not symbols


def test_syntax_error_recorded_not_raised(tmp_path: Path) -> None:
    repo = tmp_path / "bad"
    repo.mkdir()
    (repo / "broken.py").write_text("def f(:\n")
    (repo / "ok.py").write_text("import os\n")
    result = _scan(repo)
    assert any("syntax error" in w for w in result.warnings)
    assert "os" in result.module_names()


def test_syntax_skip_prevents_complete_coverage_below_file_limit(tmp_path: Path) -> None:
    repo = tmp_path / "parse_gap"
    repo.mkdir()
    (repo / "broken.py").write_text("def f(:\n", encoding="utf-8")
    (repo / "ok.py").write_text("import os\n", encoding="utf-8")

    result = _scan(repo)

    assert result.file_limit_diagnostic() is None
    assert result.coverage().pass_skip_reason() == (
        "Python candidate analysis incomplete: parsed 1 of 2 candidate files; "
        "selected 2 (limit 500); no rule-wide PASS is established."
    )


def test_real_empty_scan_is_observed_while_default_result_is_unavailable(tmp_path: Path) -> None:
    unobserved = PyScanResult().coverage()
    assert unobserved.observed is False
    assert unobserved.pass_skip_reason() == (
        "Python candidate coverage is unavailable; no rule-wide PASS is established."
    )

    observed = scan_python(RepoScanner(tmp_path, GitInfo(is_repo=False))).coverage()

    assert observed.observed is True
    assert observed.candidate_count == 0
    assert observed.selected_count == 0
    assert observed.parsed_count == 0
    assert observed.file_limit == 500
    assert observed.pass_skip_reason() is None


def test_zero_file_budget_is_an_observed_gap_not_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "hidden.py").write_text("import vllm\n", encoding="utf-8")
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 0)

    result = scan_python(RepoScanner(tmp_path, GitInfo(is_repo=False)))
    coverage = result.coverage()

    assert coverage.observed is True
    assert coverage.candidate_count == 1
    assert coverage.selected_count == 0
    assert coverage.parsed_count == 0
    assert coverage.file_limit == 0
    assert result.imports == []
    assert coverage.pass_skip_reason() == (
        "Python candidate analysis incomplete: parsed 0 of 1 candidate files; "
        "selected 0 (limit 0); no rule-wide PASS is established."
    )


def test_count_budget_coverage_distinguishes_selected_from_parsed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "a.py").write_text("import os\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("def f(:\n", encoding="utf-8")
    (tmp_path / "c.py").write_text("import vllm\n", encoding="utf-8")
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 2)

    result = scan_python(RepoScanner(tmp_path, GitInfo(is_repo=False)))

    assert result.module_names() == {"os"}
    assert result.coverage().pass_skip_reason() == (
        "Python candidate analysis incomplete: parsed 1 of 3 candidate files; "
        "selected 2 (limit 2); no rule-wide PASS is established."
    )


def test_read_and_parse_gaps_reduce_aggregate_coverage_without_count_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a_ok.py").write_text("import os\n", encoding="utf-8")
    (repo / "b_at_read_limit.py").write_bytes(b"#" + b" " * (512 * 1024 - 1))
    (repo / "c_over_read_limit.py").write_bytes(b"#" + b" " * (512 * 1024))
    (repo / "d_binary.py").write_bytes(b"import torch\n\x00")
    (repo / "e_decode.py").write_bytes(b"import datasets\n\xff")
    denied = repo / "f_denied.py"
    denied.write_text("import peft\n", encoding="utf-8")
    unsafe = repo / "g_unsafe.py"
    unsafe.write_text("import transformers\n", encoding="utf-8")
    (repo / "h_syntax.py").write_text("def f(:\n", encoding="utf-8")
    outside = tmp_path / "outside.py"
    outside.write_text("import vllm\n", encoding="utf-8")
    original_open = Path.open
    original_resolve = Path.resolve

    def guarded_open(path: Path, *args: Any, **kwargs: Any) -> IO[Any]:
        assert path != outside, "An unsafe target must not be opened."
        if path == denied:
            raise PermissionError("injected file read failure")
        return original_open(path, *args, **kwargs)

    def unsafe_resolution(path: Path, *args: Any, **kwargs: Any) -> Path:
        if path == unsafe:
            return outside
        return original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    monkeypatch.setattr(Path, "resolve", unsafe_resolution)

    result = scan_python(RepoScanner(repo, GitInfo(is_repo=False)))

    assert result.module_names() == {"os"}
    assert result.file_limit_diagnostic() is None
    assert result.coverage().observed is True
    assert result.coverage().pass_skip_reason() == (
        "Python candidate analysis incomplete: parsed 2 of 8 candidate files; "
        "selected 8 (limit 500); no rule-wide PASS is established."
    )


@pytest.mark.parametrize(
    ("candidate", "selected", "parsed", "limit"),
    [
        (-1, 0, 0, 500),
        (1, -1, 0, 500),
        (1, 1, -1, 500),
        (1, 1, 2, 500),
        (1, 2, 0, 500),
        (0, 0, 0, -1),
        (1, 1, 1, 0),
    ],
    ids=[
        "negative-candidates",
        "negative-selected",
        "negative-parsed",
        "parsed-exceeds-selected",
        "selected-exceeds-candidates",
        "negative-budget",
        "selected-exceeds-budget",
    ],
)
def test_inconsistent_coverage_is_unavailable(
    candidate: int, selected: int, parsed: int, limit: int
) -> None:
    coverage = PythonCandidateCoverage(
        observed=True,
        candidate_count=candidate,
        selected_count=selected,
        parsed_count=parsed,
        file_limit=limit,
    )

    assert coverage.pass_skip_reason() == (
        "Python candidate coverage is unavailable; no rule-wide PASS is established."
    )


def test_observed_empty_coverage_allows_a_zero_budget() -> None:
    coverage = PythonCandidateCoverage(
        observed=True, candidate_count=0, selected_count=0, parsed_count=0, file_limit=0
    )

    assert coverage.pass_skip_reason() is None


@pytest.mark.parametrize(
    "warning",
    [
        "分析不完整；消息文本不能决定覆盖状态。",
        "Python analysis incomplete: parsed 0 of 500 candidate files",
        "No candidates were skipped; analysis is complete.",
    ],
    ids=["localized-warning", "misleading-gap-warning", "misleading-complete-warning"],
)
def test_coverage_does_not_infer_facts_from_warning_text(warning: str) -> None:
    complete = PyScanResult(
        python_candidate_count=1,
        python_selected_count=1,
        python_parsed_count=1,
        python_file_limit=500,
        coverage_observed=True,
        warnings=[warning],
    )
    gap = PyScanResult(
        python_candidate_count=2,
        python_selected_count=1,
        python_parsed_count=1,
        python_file_limit=1,
        coverage_observed=True,
        warnings=[warning],
    )
    unobserved = PyScanResult(warnings=[warning])

    assert complete.coverage().pass_skip_reason() is None
    assert gap.coverage().pass_skip_reason() == (
        "Python candidate analysis incomplete: parsed 1 of 2 candidate files; "
        "selected 1 (limit 1); no rule-wide PASS is established."
    )
    assert unobserved.coverage().pass_skip_reason() == (
        "Python candidate coverage is unavailable; no rule-wide PASS is established."
    )


def test_coverage_is_a_frozen_snapshot_of_scan_facts() -> None:
    result = PyScanResult(
        python_candidate_count=2,
        python_selected_count=2,
        python_parsed_count=1,
        python_file_limit=500,
        coverage_observed=True,
    )
    coverage = result.coverage()

    result.python_parsed_count = 2
    result.coverage_observed = False

    assert coverage.observed is True
    assert coverage.parsed_count == 1
    assert coverage.pass_skip_reason() == (
        "Python candidate analysis incomplete: parsed 1 of 2 candidate files; "
        "selected 2 (limit 500); no rule-wide PASS is established."
    )
    with pytest.raises(FrozenInstanceError):
        coverage.parsed_count = 2


def test_hf_ids_from_from_pretrained_and_llm(tmp_path: Path) -> None:
    repo = tmp_path / "hfid"
    repo.mkdir()
    (repo / "eval.py").write_text(
        "from transformers import AutoTokenizer\n"
        "AutoTokenizer.from_pretrained('Qwen/Qwen3-32B')\n"
        "from vllm import LLM\n"
        "llm = LLM(model='meta-llama/Llama-3.1-8B-Instruct')\n"
        "x = AutoTokenizer.from_pretrained('not-a-repo-id')\n"
    )
    result = _scan(repo)
    values = {hint.value for hint in result.hf_ids}
    assert values == {"Qwen/Qwen3-32B", "meta-llama/Llama-3.1-8B-Instruct"}


def test_load_dataset_string_not_extracted(tmp_path: Path) -> None:
    repo = tmp_path / "ds"
    repo.mkdir()
    (repo / "d.py").write_text(
        "from datasets import load_dataset\nload_dataset('cais/mmlu', 'test')\n"
    )
    assert _scan(repo).hf_ids == []


def test_trust_remote_code_and_trainer_import(tmp_path: Path) -> None:
    repo = tmp_path / "trc"
    repo.mkdir()
    (repo / "train.py").write_text(
        "import torch\n"
        "from transformers import AutoModelForCausalLM, Trainer, TrainingArguments\n"
        "model = AutoModelForCausalLM.from_pretrained('org/m', trust_remote_code=True)\n"
    )
    result = _scan(repo)
    assert result.trust_remote_code is True
    assert result.trainer_import is True


# --- forbidden file matcher (§16.4) ------------------------------------------


def test_forbidden_file_patterns() -> None:
    for path in [
        ".env",
        ".env.local",
        "config/.env",
        "server.pem",
        "id_rsa",
        "id_ed25519_git",
        "credentials.json",
        "cert.p12",
        "bundle.pfx",
        "keystore.jks",
        "host_rsa",
        ".netrc",
        ".npmrc",
        ".pypirc",
        "secrets/api.key",
    ]:
        assert is_forbidden_file(path), path


def test_exempt_and_benign_files() -> None:
    for path in [
        ".env.example",
        ".env.sample",
        ".env.template",
        "main.py",
        "README.md",
        "environment.yml",
        "keynote.md",
    ]:
        assert not is_forbidden_file(path), path


def test_case_insensitive_match() -> None:
    assert is_forbidden_file("SERVER.PEM")
    assert is_forbidden_file(".ENV")


def test_syntax_warnings_from_target_code_are_suppressed(tmp_path, capsys) -> None:
    repo = tmp_path / "warny"
    repo.mkdir()
    (repo / "legacy.py").write_text("pattern = '\\%s'\n")  # invalid escape
    result = _scan(repo)
    assert result.imports == []  # parsed fine, nothing imported
    captured = capsys.readouterr()
    assert "SyntaxWarning" not in captured.out + captured.err
