"""Cold-start documentation and shipped examples obey M8-T02/T03."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from scripts import gen_quickstart, refresh_examples

ROOT = Path(__file__).resolve().parents[2]
NAMES = ("hf_vllm_eval", "openai_judge_eval", "privacy_custom_params")


@pytest.mark.parametrize("name", NAMES)
def test_shipped_manifest_is_complete_and_existing_real_lock_is_fresh(name: str) -> None:
    example = ROOT / "examples" / name
    expected = (ROOT / "tests/fixtures/repos" / name / "manifests/complete.yaml").read_bytes()
    manifest = (example / "reprollm.yaml").read_bytes()
    assert manifest == expected + b"\n"
    lock = yaml.safe_load((example / "reprollm.lock").read_text(encoding="utf-8"))
    assert lock["manifest_sha256"] == "sha256:" + hashlib.sha256(manifest).hexdigest()
    rules = example / ".reprollm/project-rules.yaml"
    expected_rules = (
        "sha256:" + hashlib.sha256(rules.read_bytes()).hexdigest() if rules.is_file() else None
    )
    assert lock["project_rules_sha256"] == expected_rules
    for metric in (lock.get("evaluation") or {}).get("metrics", []):
        if metric["implementation_sha256"]:
            implementation = example / metric["implementation"]
            assert (
                metric["implementation_sha256"]
                == "sha256:" + hashlib.sha256(implementation.read_bytes()).hexdigest()
            )


def test_refresh_preserves_reviewed_locks_and_exports(tmp_path: Path, monkeypatch) -> None:
    examples = tmp_path / "examples"
    example = examples / "hf_vllm_eval"
    example.mkdir(parents=True)
    preserved = {
        "reprollm.lock": b"reviewed online lock\n",
        "REPRODUCIBILITY.acl.md": b"reviewed export\n",
    }
    for name, content in preserved.items():
        (example / name).write_bytes(content)
    monkeypatch.setattr(refresh_examples, "EXAMPLES", examples)

    refresh_examples.main()
    refresh_examples.main()

    for name, content in preserved.items():
        assert (example / name).read_bytes() == content


def test_quickstart_covers_real_levels_and_resource_free_workflow(tmp_path: Path) -> None:
    records = gen_quickstart.run_workflow(tmp_path / "hf_vllm_eval")
    audits = [row for row in records if row.command[:1] == ["audit"]]
    assert [json.loads(row.report_json)["level"] for row in audits] == [0, 1, 1, 2]
    assert all(row.exit_code in (0, 1) for row in records)
    assert [row.command[:1] for row in records].count(["lock"]) == 3
    assert all(
        "--offline" in row.command or "--check" in row.command
        for row in records
        if row.command[0] == "lock"
    )
    runs = [row for row in records if row.command[:1] == ["run"]]
    assert len(runs) == 2
    assert all("capture_probe.py" in row.command and "eval.py" not in row.command for row in runs)
    diff = next(row for row in records if row.command[:1] == ["diff"])
    assert diff.exit_code == 1
    delta = json.loads(diff.report_json)
    cap = next(change for change in delta["changes"] if change["path"] == "generation.max_tokens")
    assert cap["severity"] == "HIGH"
    assert cap["a"] == 32 and cap["b"] == 48
    assert records[-1].command[:1] == ["export"] and records[-1].exit_code == 0
    assert (tmp_path / "hf_vllm_eval/REPRODUCIBILITY.md").is_file()


def test_user_guides_do_not_reinitialize_shipped_intent() -> None:
    for name in NAMES:
        text = (ROOT / "examples" / name / "README.md").read_text(encoding="utf-8")
        assert "reprollm init . --force" not in text
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert 'reprollm lock --check "$example" || true' not in workflow


def test_faq_uses_online_resolution_and_explicit_discover_gate() -> None:
    text = (ROOT / "docs/faq.md").read_text(encoding="utf-8")
    assert "Run `reprollm lock --offline` on the machine with network access" not in text
    assert "reprollm discover --experimental --dry-run" in text
    assert "model-author" in text
    assert "interactive confirmation" in text


def test_quickstart_subprocesses_do_not_inherit_credentials(monkeypatch) -> None:
    monkeypatch.setenv("HF_TOKEN", "synthetic-not-a-real-token")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-not-a-real-token")
    monkeypatch.setenv("REPROLLM_DISCOVER_API_KEY", "synthetic-not-a-real-token")
    env = gen_quickstart._env()
    assert not {"HF_TOKEN", "OPENAI_API_KEY", "REPROLLM_DISCOVER_API_KEY"} & env.keys()


def test_readme_install_starts_with_supported_public_package() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Python 3.10 or newer" in text
    assert "python -m pip install reprollm" in text
    assert "Status: beta (0.5.0)" not in text


@pytest.mark.parametrize("identity_variable", ["USERNAME", "USER", "LOGNAME", "LNAME"])
def test_quickstart_preserves_identity_for_redaction_without_pwd(
    monkeypatch: pytest.MonkeyPatch, identity_variable: str
) -> None:
    # Windows has no pwd module: getpass must retain an environment fallback.
    for name in ("USERNAME", "USER", "LOGNAME", "LNAME"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(identity_variable, "fake-user")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import getpass,sys; sys.modules['pwd']=None; print(getpass.getuser())",
        ],
        env=gen_quickstart._env(),
        capture_output=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "fake-user"
