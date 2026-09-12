"""Generated rule/profile documentation stays complete and deterministic (M3-T09)."""

from pathlib import Path

from scripts.gen_profiles_doc import render_profiles_doc
from scripts.gen_rules_doc import render_rules_doc

ROOT = Path(__file__).resolve().parents[2]


def test_rules_document_is_fresh_and_complete() -> None:
    rendered = render_rules_doc()
    assert rendered == (ROOT / "docs/rules.md").read_text(encoding="utf-8")
    assert rendered.count("| `") >= 53
    assert "`model.primary_declared`" in rendered
    assert "`model.revision_pinned`" in rendered
    assert "stub, arrives in 0.2.0" in rendered
    assert "core, evaluation, finetuning, inference, llm_judge, privacy, safety" in rendered


def test_profiles_document_is_fresh_and_complete() -> None:
    rendered = render_profiles_doc()
    assert rendered == (ROOT / "docs/profiles.md").read_text(encoding="utf-8")
    for name in ("core", "inference", "evaluation", "llm_judge", "finetuning", "safety", "privacy"):
        assert f"## `{name}`" in rendered
    assert "`gen.seed_declared`: CRITICAL" in rendered
    assert "`evaluation.judge.*`: HIGH" in rendered


def test_ci_checks_coverage_and_generated_docs() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "--cov-fail-under=85" in workflow
    assert "python scripts/gen_rules_doc.py --check" in workflow
    assert "python scripts/gen_profiles_doc.py --check" in workflow
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "[rule catalog](docs/rules.md)" in readme
    assert "[profile catalog](docs/profiles.md)" in readme
