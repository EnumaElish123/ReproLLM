"""Generated rule/profile documentation stays complete and deterministic (M3-T09)."""

import subprocess
import sys
from pathlib import Path

from scripts import gen_cli_doc, gen_quickstart
from scripts.gen_profiles_doc import render_profiles_doc
from scripts.gen_rules_doc import render_rules_doc

ROOT = Path(__file__).resolve().parents[2]


def test_rules_document_is_fresh_and_complete() -> None:
    rendered = render_rules_doc()
    assert rendered == (ROOT / "docs/rules.md").read_text(encoding="utf-8")
    assert rendered.count("| `") >= 53
    assert "`model.primary_declared`" in rendered
    assert "`model.revision_pinned`" in rendered
    assert "stub, arrives in 0.3.0" not in rendered
    assert (
        "core, evaluation, finetuning, inference, judge_only, llm_judge, privacy, safety"
        in rendered
    )


def test_profiles_document_is_fresh_and_complete() -> None:
    rendered = render_profiles_doc()
    assert rendered == (ROOT / "docs/profiles.md").read_text(encoding="utf-8")
    for name in (
        "core",
        "inference",
        "evaluation",
        "llm_judge",
        "judge_only",
        "finetuning",
        "safety",
        "privacy",
    ):
        assert f"## `{name}`" in rendered
    judge = rendered.split("## `judge_only`", 1)[1].split("## `llm_judge`", 1)[0]
    required = next(line for line in judge.splitlines() if line.startswith("- Required fields:"))
    assert "models.primary.id" not in required
    assert "models.judge.id" in required and "evaluation.judge.params.max_tokens" in required
    assert "`gen.seed_declared`: CRITICAL" in rendered
    assert "`evaluation.judge.*`: HIGH" in rendered


def test_ci_checks_coverage_and_generated_docs() -> None:
    """Freshness belongs in normal CI as well as the nightly performance gate."""
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "--cov-fail-under=85" in workflow
    nightly = (ROOT / ".github/workflows/nightly.yml").read_text(encoding="utf-8")
    for generator in ("rules_doc", "profiles_doc", "cli_doc", "quickstart"):
        for document in (workflow, nightly):
            assert f"python scripts/gen_{generator}.py --check" in document
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "[rule catalog](docs/rules.md)" in readme
    assert "[profile catalog](docs/profiles.md)" in readme


def test_cli_document_is_fresh() -> None:
    assert gen_cli_doc.main(check=True) == 0


def test_quickstart_document_is_fresh() -> None:
    assert gen_quickstart.main(check=True) == 0


def test_quickstart_scrubs_resolved_tempdir_alias(monkeypatch) -> None:
    work = Path("/var/folders/demo/hf_vllm_eval")
    canonical = Path("/private/var/folders/demo/hf_vllm_eval")
    monkeypatch.setattr(Path, "resolve", lambda self: canonical)
    output = f"Created {canonical}/reprollm.yaml\nScanned {work}/config.yaml"
    assert gen_quickstart.scrub(output, work) == (
        "Created examples/hf_vllm_eval/reprollm.yaml\nScanned examples/hf_vllm_eval/config.yaml"
    )


def test_cli_document_is_plain_in_ci_environment(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.setenv("PY_COLORS", "1")
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.setenv("TERMINAL_WIDTH", "120")
    assert gen_cli_doc.main(check=True) == 0


def test_quickstart_document_is_plain_in_ci_environment(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.setenv("PY_COLORS", "1")
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.setenv("COLUMNS", "120")
    assert gen_quickstart.main(check=True) == 0


def test_quickstart_scrubs_windows_artifact_separator() -> None:
    work = Path(r"D:\a\temp\hf_vllm_eval")
    output = f"Created {work}\\reprollm.yaml (profiles: evaluation, inference)"
    assert gen_quickstart.scrub(output, work) == (
        "Created examples/hf_vllm_eval/reprollm.yaml (profiles: evaluation, inference)"
    )


def test_cli_document_is_fresh_with_legacy_windows_console(monkeypatch) -> None:
    run = subprocess.run
    windows_console = (
        "import sys, rich.console\n"
        "rich.console.detect_legacy_windows = lambda: True\n"
        "sys.argv[0] = 'reprollm.EXE'\n"
    )

    def simulate_windows(command, **kwargs):
        if command[:2] == [sys.executable, "-c"]:
            program = windows_console + command[2]
            arguments = command[3:]
        else:
            program = windows_console + "from reprollm.cli.main import cli\ncli()\n"
            arguments = command[1:]
        return run([sys.executable, "-c", program, *arguments], **kwargs)

    monkeypatch.setattr(gen_cli_doc.subprocess, "run", simulate_windows)
    assert gen_cli_doc.main(check=True) == 0
