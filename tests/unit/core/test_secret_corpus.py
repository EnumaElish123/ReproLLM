"""M2F-T08: the normative secret fixture corpus (F-09).

`file_cases.yaml` is consumed now (the forbidden-file matcher exists in M2);
`positive.txt`/`negative.txt`/`env_cases.yaml` are validated structurally and
become normative inputs for the M5-T01 redaction classifiers.
"""

from pathlib import Path

import yaml

from reprollm.core.redaction import is_forbidden_file

CORPUS = Path(__file__).resolve().parents[2] / "fixtures" / "secrets"


def _load(name: str) -> dict:
    return yaml.safe_load((CORPUS / name).read_text(encoding="utf-8"))


def test_file_cases_forbidden() -> None:
    for path in _load("file_cases.yaml")["forbidden"]:
        assert is_forbidden_file(path), path


def test_file_cases_allowed() -> None:
    for path in _load("file_cases.yaml")["allowed"]:
        assert not is_forbidden_file(path), path


def test_file_cases_case_insensitive() -> None:
    for path in _load("file_cases.yaml")["case_insensitive_forbidden"]:
        assert is_forbidden_file(path), path


def test_every_spec_glob_is_represented() -> None:
    from reprollm.core.redaction import FORBIDDEN_GLOBS

    corpus_paths = [
        *_load("file_cases.yaml")["forbidden"],
        *_load("file_cases.yaml")["case_insensitive_forbidden"],
    ]
    from fnmatch import fnmatch

    for glob in FORBIDDEN_GLOBS:
        assert any(fnmatch(Path(p).name.lower(), glob.lower()) for p in corpus_paths), glob


def test_positive_corpus_min_three_per_kind() -> None:
    lines = [
        line
        for line in (CORPUS / "positive.txt").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    import re

    kinds = {
        "openai": r"sk-(?:proj-)?[A-Za-z0-9_-]{16,}",
        "huggingface": r"hf_[A-Za-z0-9]{20,}",
        "github": r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}",
        "aws": r"AKIA[0-9A-Z]{16}",
        "slack": r"xox[baprs]-[A-Za-z0-9-]{10,}",
        "jwt": r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}",
        "pem": r"BEGIN [A-Z ]*PRIVATE KEY",
        "url_cred": r"://[^/\s:@]+:[^/\s@]+@",
        "generic_kv": r"(?i)(api[_-]?key|access[_-]?token|auth[_-]?token|secret|password|passwd)"
        r"\b\s*[:=]\s*[\"']?[^\s\"']{8,}",
    }
    for kind, pattern in kinds.items():
        matches = [line for line in lines if re.search(pattern, line)]
        assert len(matches) >= 3, f"{kind}: only {len(matches)} samples"


def test_env_corpus_covers_required_names() -> None:
    data = _load("env_cases.yaml")
    entries = {**data["is_secret"], **data["is_not_secret"]}
    assert len(entries) >= 30
    assert all(isinstance(value, bool) for value in entries.values())
    required = (
        "HF_TOKEN",
        "MAX_TOKENS",
        "TOKENIZERS_PARALLELISM",
        "SSH_AUTH_SOCK",
        "KEY_FRAMES",
        "CUDA_VISIBLE_DEVICES",
        "DATABASE_URL",
    )
    for name in required:
        assert name in entries, name
    assert entries["HF_TOKEN"] and entries["MAX_TOKENS"] is False
    assert entries["TOKENIZERS_PARALLELISM"] is False
    assert entries["SSH_AUTH_SOCK"] and entries["KEY_FRAMES"]


def test_negative_corpus_has_no_lookalike_secrets() -> None:
    """Every negative line must stay unredacted — the M5 classifier contract;
    in M2 we at least pin the spec's explicit negative examples."""
    text = (CORPUS / "negative.txt").read_text(encoding="utf-8")
    for required in (
        "MAX_TOKENS=2048",
        "TOKENIZERS_PARALLELISM=false",
        "Qwen/Qwen3-32B",
        "secret_santa.py",
        "token_count: 512",
    ):
        assert required in text, required


def test_corpus_files_exist_with_readmes() -> None:
    """The corpus directory documents itself (fake values only)."""
    names = {entry.name for entry in CORPUS.iterdir()}
    expected = {"positive.txt", "negative.txt", "env_cases.yaml", "file_cases.yaml", "README.md"}
    assert expected <= names
    readme = (CORPUS / "README.md").read_text(encoding="utf-8")
    assert "fake" in readme.lower()
