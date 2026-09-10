"""M2F-T11: exactly one canonical repository identity (D-43).

Every normative and public file carries `github.com/EnumaElish123/ReproLLM`
wherever a repository URL appears, and the legacy organization path appears
nowhere in them. Historical records (sprint documents M*.md, the corrective
sprint M2-fix, docs/research) may mention the old identity when describing
past plans or the conflict itself; they are excluded on purpose.
"""

from pathlib import Path

import tomllib

REPO_ROOT = Path(__file__).resolve().parents[2]

CANONICAL = "github.com/EnumaElish123/ReproLLM"
LEGACY = "reprollm/reprollm"

#: Files whose identity must be exactly canonical.
NORMATIVE_AND_PUBLIC = [
    "pyproject.toml",
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "CHANGELOG.md",
    "AGENTS.md",
    "docs/index.md",
    "docs/adoption.md",
    "docs/plan/00_architecture_and_decisions.md",
    "docs/plan/01_specification.md",
    "val.md",
    ".github/workflows/ci.yml",
    ".github/workflows/release.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/ISSUE_TEMPLATE/spec_change.yml",
    ".github/ISSUE_TEMPLATE/new_rule.yml",
]


def _text(relative: str) -> str:
    path = REPO_ROOT / relative
    assert path.is_file(), f"expected file missing: {relative}"
    return path.read_text(encoding="utf-8")


def test_legacy_identity_absent_from_normative_files() -> None:
    for relative in NORMATIVE_AND_PUBLIC:
        assert LEGACY not in _text(relative), relative


def test_pyproject_urls_are_canonical() -> None:
    doc = tomllib.loads(_text("pyproject.toml"))
    urls = doc["project"]["urls"]
    assert urls, "project.urls must exist"
    for name, url in urls.items():
        assert url.startswith("https://"), (name, url)
        if "github.com" in url:
            assert CANONICAL in url, (name, url)


def test_readme_badges_and_links_are_canonical() -> None:
    text = _text("README.md")
    assert text.count(CANONICAL) >= 2  # CI badge + badge link target
    assert "img.shields.io/pypi/v/reprollm" in text  # PyPI badge stays package-level


def test_security_links_are_canonical() -> None:
    text = _text("SECURITY.md")
    assert f"https://{CANONICAL}/security/advisories/new" in text


def test_changelog_compare_links_are_canonical() -> None:
    text = _text("CHANGELOG.md")
    assert f"https://{CANONICAL}/compare/" in text


def test_contributing_clone_url_is_canonical() -> None:
    text = _text("CONTRIBUTING.md")
    assert f"git clone https://{CANONICAL}.git" in text


def test_decision_register_records_the_supersession() -> None:
    text = _text("docs/plan/00_architecture_and_decisions.md")
    assert "D-43 Canonical repository identity" in text
    assert "superseded by D-43" in text
    assert CANONICAL in text
