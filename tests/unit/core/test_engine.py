"""Audit engine tests (spec §11) — M1 subset (Level 0, core profile)."""

from pathlib import Path
from typing import IO, Any

import pytest

from reprollm.core.engine import run_audit
from reprollm.core.errors import UserError
from tests.conftest import CmdStub, materialize_repo


def test_level0_clean_repo_full_core(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    report = run_audit(repo)
    assert report.level == 0
    assert report.profiles.resolved == ["core"]
    assert report.profiles.declared == []
    by_id = {f.rule_id: (f.status.value, f.severity.value) for f in report.findings}
    assert by_id == {
        "code.git_repo": ("pass", "PASS"),
        "code.git_commit": ("pass", "PASS"),
        "code.clean_tree": ("pass", "PASS"),
        "code.no_untracked": ("pass", "PASS"),
        "code.submodules_initialized": ("skipped", "INFO"),
        "code.remote_recorded": ("fail", "INFO"),
        "env.dependency_manifest_present": ("pass", "PASS"),
        "env.lockfile_present": ("fail", "WARNING"),
        "env.llm_critical_deps_pinned": ("fail", "WARNING"),
        "env.python_version_declared": ("fail", "WARNING"),
        "env.secret_files_ignored": ("pass", "PASS"),
        "env.reprollm_initialized": ("fail", "INFO"),
    }
    assert report.summary.pass_ == 6
    assert report.summary.warning == 3
    assert report.summary.info == 2
    assert report.summary.skipped == 1
    assert report.summary.critical == 0


def test_report_is_deterministic_modulo_timestamp(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    first = run_audit(repo).model_dump(mode="json")
    second = run_audit(repo).model_dump(mode="json")
    first.pop("generated_at")
    second.pop("generated_at")
    assert first == second


def test_level0_not_a_git_repo(tmp_path: Path) -> None:
    repo = materialize_repo("not_a_git_repo", tmp_path)
    report = run_audit(repo)
    assert report.level == 0
    by_id = {f.rule_id: (f.status.value, f.severity.value) for f in report.findings}
    assert by_id["code.git_repo"] == ("fail", "CRITICAL")
    assert by_id["code.git_commit"] == ("skipped", "INFO")
    assert by_id["code.clean_tree"] == ("skipped", "INFO")
    assert by_id["env.dependency_manifest_present"] == ("pass", "PASS")
    assert by_id["env.lockfile_present"] == ("pass", "PASS")  # all-== requirements
    assert by_id["env.llm_critical_deps_pinned"] == ("pass", "PASS")
    assert by_id["env.python_version_declared"] == ("fail", "WARNING")
    assert report.summary.critical == 1
    assert report.summary.skipped == 5


def test_unknown_profile_is_user_error(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    with pytest.raises(UserError, match="unknown profile"):
        run_audit(repo, profile_names=["made_up"])


def test_core_may_not_be_declared(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    with pytest.raises(UserError, match="core"):
        run_audit(repo, profile_names=["core"])


def test_documents_section_hashes(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    report = run_audit(repo)
    assert report.documents.manifest is None
    assert report.documents.lock is None
    assert report.documents.runs == 0


def test_capped_python_view_cannot_pass_rules_that_depend_on_unseen_imports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stub_run_cmd: CmdStub
) -> None:
    from reprollm.core import scanner

    repo = tmp_path / "incomplete"
    repo.mkdir()
    (repo / "reprollm.yaml").write_text(
        "schema_version: 1\nproject: {name: incomplete}\nexperiment: {profiles: []}\n",
        encoding="utf-8",
    )
    (repo / "requirements.txt").write_text("torch==1.0\n", encoding="utf-8")
    (repo / "a.py").write_text("import torch\n", encoding="utf-8")
    (repo / "z.py").write_text("import vllm\n", encoding="utf-8")
    stub_run_cmd.on("git", returncode=1)
    monkeypatch.setattr(scanner, "MAX_PYTHON_FILES", 1)

    report = run_audit(repo, level=1, target=".")
    selected = [
        finding
        for finding in report.findings
        if finding.rule_id in {"env.llm_critical_deps_pinned", "exec.profile_detection_mismatch"}
    ]
    assert len(selected) == 2
    assert {(finding.status.value, finding.severity.value) for finding in selected} == {
        ("skipped", "INFO")
    }
    assert all(
        finding.message
        == "Python candidate analysis incomplete: parsed 1 of 2 candidate files; "
        "selected 1 (limit 1); no rule-wide PASS is established."
        and finding.evidence == []
        for finding in selected
    )


@pytest.mark.parametrize(
    ("first", "last", "profiles", "unreadable", "expected_status", "expected_message"),
    [
        (
            "import vllm\n",
            "value = 1\n",
            "[]",
            False,
            "fail",
            "detected profile 'inference' (high confidence) is not declared in experiment.profiles",
        ),
        (
            "value = 1\n",
            "import vllm\n",
            "[]",
            False,
            "skipped",
            "Python candidate analysis incomplete: parsed 1 of 2 candidate files; "
            "selected 1 (limit 1); no rule-wide PASS is established.",
        ),
        (
            "value = 1\n",
            None,
            "[]",
            False,
            "pass",
            "Declared profiles and detected signals agree.",
        ),
        (
            "import vllm\n",
            None,
            "[]",
            True,
            "skipped",
            "Python candidate analysis incomplete: parsed 0 of 1 candidate files; "
            "selected 1 (limit 1); no rule-wide PASS is established.",
        ),
        (
            "value = 1\n",
            "import vllm\n",
            "[inference]",
            False,
            "fail",
            "declared profile 'inference' has no detection evidence in this repository",
        ),
    ],
    ids=["inside-cap", "outside-cap", "truly-absent", "unreadable", "legacy-absence-finding"],
)
def test_profile_conclusions_use_only_the_approved_empty_result_policy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stub_run_cmd: CmdStub,
    first: str,
    last: str | None,
    profiles: str,
    unreadable: bool,
    expected_status: str,
    expected_message: str,
) -> None:
    from reprollm.core import scanner

    (tmp_path / "reprollm.yaml").write_text(
        "project: {name: coverage}\nexperiment: {profiles: " + profiles + "}\n",
        encoding="utf-8",
    )
    first_path = tmp_path / "a.py"
    first_path.write_text(first, encoding="utf-8")
    if last is not None:
        (tmp_path / "z.py").write_text(last, encoding="utf-8")
    if unreadable:
        original_open = Path.open

        def deny_selected(path: Path, *args: Any, **kwargs: Any) -> IO[Any]:
            if path == first_path:
                raise PermissionError("synthetic unreadable candidate")
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr(Path, "open", deny_selected)
    stub_run_cmd.on("git", returncode=1)
    monkeypatch.setattr(scanner, "MAX_PYTHON_FILES", 1)

    report = run_audit(tmp_path, target=".")
    (finding,) = [f for f in report.findings if f.rule_id == "exec.profile_detection_mismatch"]
    assert finding.status.value == expected_status
    assert finding.severity.value == ("PASS" if expected_status == "pass" else "INFO")
    assert finding.message == expected_message
    if expected_status == "skipped":
        assert finding.evidence == []
    if first == "import vllm\n" and not unreadable:
        (package,) = [f for f in report.findings if f.rule_id == "env.llm_critical_deps_pinned"]
        assert package.status.value == "fail" and package.severity.value == "WARNING"
        assert package.evidence[0].path == "a.py"


def test_incomplete_python_preserves_independent_rules_and_explicit_role_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import yaml

    from reprollm.core import scanner

    repo = materialize_repo("hf_vllm_eval", tmp_path)
    fixture = Path(__file__).resolve().parents[2] / "fixtures/repos/hf_vllm_eval"
    manifest = yaml.safe_load((fixture / "manifests/complete.yaml").read_text(encoding="utf-8"))
    manifest["models"]["auxiliary"] = {"id": "org/auxiliary", "provider": "huggingface"}
    manifest["inference"].pop("dtype")
    manifest["custom"] = {"alpha": 0}
    (repo / "reprollm.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    (repo / "reprollm.lock").write_bytes((fixture / "expected/lock.yaml").read_bytes())
    (repo / "a.py").write_bytes((repo / "eval.py").read_bytes())
    dotdir = repo / ".reprollm"
    dotdir.mkdir()
    (dotdir / "project-rules.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "rules": [
                    {
                        "id": "project.alpha",
                        "field": "custom.alpha",
                        "severity": "WARNING",
                        "reason": "controls the selected experiment",
                        "source": "manual",
                        "accepted_at": "2026-10-20T00:00:00Z",
                    },
                    {
                        "id": "project.beta",
                        "field": "custom.beta",
                        "severity": "WARNING",
                        "reason": "records a second independent setting",
                        "source": "manual",
                        "accepted_at": "2026-10-20T00:00:00Z",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    profiles = ["evaluation", "finetuning", "llm_judge", "privacy", "safety"]
    full = run_audit(repo, profile_names=profiles, target=".")
    monkeypatch.setattr(scanner, "MAX_PYTHON_FILES", 1)
    limited = run_audit(repo, profile_names=profiles, target=".")
    opt_in = {"env.llm_critical_deps_pinned", "exec.profile_detection_mismatch"}
    assert len({f.rule_id for f in full.findings if not f.rule_id.startswith("project.")}) == 69
    assert [f.model_dump() for f in limited.findings if f.rule_id not in opt_in] == [
        f.model_dump() for f in full.findings if f.rule_id not in opt_in
    ]
    assert {f.status.value for f in limited.findings if f.rule_id == "model.dtype_declared"} == {
        "pass",
        "fail",
    }
    assert {
        f.rule_id: f.status.value for f in limited.findings if f.rule_id.startswith("project.")
    } == {"project.alpha": "pass", "project.beta": "fail"}


def test_pass_hook_is_not_queried_for_failures_or_inapplicable_rules(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stub_run_cmd: CmdStub
) -> None:
    from reprollm.core.context import AuditContext
    from reprollm.core.registry import Rule, get_rule

    (tmp_path / "reprollm.yaml").write_text(
        "project: {name: lifecycle}\nexperiment: {profiles: []}\n", encoding="utf-8"
    )
    (tmp_path / "main.py").write_text("import vllm\n", encoding="utf-8")
    stub_run_cmd.on("git", returncode=1)

    def forbidden_hook(self: Rule, ctx: AuditContext) -> str | None:
        pytest.fail(f"{self.id}: a nonempty or inapplicable rule must not query its PASS hook")

    for rule_id in (
        "env.llm_critical_deps_pinned",
        "exec.profile_detection_mismatch",
        "model.trust_remote_code_declared",
    ):
        rule = get_rule(rule_id)
        assert rule is not None
        monkeypatch.setattr(rule, "pass_skip_reason", forbidden_hook)

    report = run_audit(tmp_path, target=".")
    by_id = {f.rule_id: f.status.value for f in report.findings}
    assert by_id["env.llm_critical_deps_pinned"] == "fail"
    assert by_id["exec.profile_detection_mismatch"] == "fail"
    assert by_id["model.trust_remote_code_declared"] == "skipped"
