"""M10-T01: export --template neurips|acl|acm checklist mappings."""

import pytest
from typer.testing import CliRunner

from reprollm.cli.main import app
from tests.conftest import materialize_repo

runner = CliRunner()


@pytest.mark.parametrize("venue", ["neurips", "acl", "acm"])
def test_template_appends_checklist_section(tmp_path, venue):
    from tests.conftest import commit_all

    repo = materialize_repo("hf_vllm_eval", tmp_path)
    manifest = (
        Path(__file__).resolve().parents[2] / "fixtures/repos/hf_vllm_eval/manifests/complete.yaml"
    ).read_text()
    (repo / "reprollm.yaml").write_text(manifest, encoding="utf-8")
    commit_all(repo)

    result = runner.invoke(app, ["export", str(repo), "--template", venue])
    assert result.exit_code == 0, result.output
    doc = (repo / "REPRODUCIBILITY.md").read_text(encoding="utf-8")

    assert "Checklist" in doc, venue
    assert venue.lower() in doc.lower(), venue
    assert "not covered" in doc, "honest not-covered items must be listed"
    assert "Qwen/Qwen3-32B" in doc, "model identity must appear in the mapping"


def test_template_rejects_unknown(tmp_path):
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    result = runner.invoke(app, ["export", str(repo), "--template", "icml"])
    assert result.exit_code == 2
    assert "unknown template" in result.output


def test_default_template_has_no_checklist(tmp_path):
    from tests.conftest import commit_all

    repo = materialize_repo("hf_vllm_eval", tmp_path)
    manifest = (
        Path(__file__).resolve().parents[2] / "fixtures/repos/hf_vllm_eval/manifests/complete.yaml"
    ).read_text()
    (repo / "reprollm.yaml").write_text(manifest, encoding="utf-8")
    commit_all(repo)

    result = runner.invoke(app, ["export", str(repo)])
    assert result.exit_code == 0
    doc = (repo / "REPRODUCIBILITY.md").read_text(encoding="utf-8")
    assert "NeurIPS" not in doc
    assert "ACM" not in doc


def test_neurips_mapping_covers_judge_and_privacy_honestly(tmp_path):
    from tests.conftest import commit_all

    repo = materialize_repo("openai_judge_eval", tmp_path)
    manifest = (
        Path(__file__).resolve().parents[2]
        / "fixtures/repos/openai_judge_eval/manifests/complete.yaml"
    ).read_text()
    (repo / "reprollm.yaml").write_text(manifest, encoding="utf-8")
    commit_all(repo)

    assert runner.invoke(app, ["export", str(repo), "--template", "neurips"]).exit_code == 0
    doc = (repo / "REPRODUCIBILITY.md").read_text(encoding="utf-8")
    assert "gpt-4o" in doc, "judge model identity must appear"
    assert "Attack/defense" in doc
    assert "not covered" in doc, "privacy is absent — must be honest"


from pathlib import Path  # noqa: E402
