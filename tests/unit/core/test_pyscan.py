"""pyscan + redaction file-matcher tests (M2-T03)."""

from pathlib import Path

from reprollm.core.git import inspect_git
from reprollm.core.pyscan import scan_python
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
