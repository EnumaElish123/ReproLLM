"""env.* rule tests (spec §12.2) — one PASS and one FAIL per rule."""

from pathlib import Path
from typing import IO, Any

import pytest

from reprollm.core import scanner as scanner_mod
from reprollm.core.context import AuditContext
from reprollm.core.git import GitInfo
from reprollm.core.pyscan import PyScanResult
from reprollm.rules.env import (
    DependencyManifestPresentRule,
    LlmCriticalDepsPinnedRule,
    LockfilePresentRule,
    PythonVersionDeclaredRule,
    ReprollmInitializedRule,
    SecretFilesIgnoredRule,
)
from reprollm.schemas.finding import Finding, FindingStatus, Severity
from tests.conftest import materialize_repo


def _ctx(repo: Path, level: int = 0) -> AuditContext:
    return AuditContext(repo, level=level)


# --- env.dependency_manifest_present ----------------------------------------


def test_manifest_present_pass_on_fixture(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    assert DependencyManifestPresentRule().check(_ctx(repo)) == []


def test_manifest_missing_fails_on_no_deps_file(tmp_path: Path) -> None:
    repo = materialize_repo("no_deps_file", tmp_path)
    finding = DependencyManifestPresentRule().check(_ctx(repo))[0]
    assert finding.severity == Severity.CRITICAL
    assert "no dependency manifest" in finding.message


# --- env.lockfile_present ----------------------------------------------------


def test_lockfile_present_warning_when_loose(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    finding = LockfilePresentRule().check(_ctx(repo))[0]
    assert finding.severity == Severity.WARNING


def test_lockfile_present_pass_when_all_pinned(tmp_path: Path) -> None:
    repo = materialize_repo("not_a_git_repo", tmp_path)
    assert LockfilePresentRule().check(_ctx(repo)) == []


def test_lockfile_skipped_without_manifest(tmp_path: Path) -> None:
    repo = materialize_repo("no_deps_file", tmp_path)
    ctx = _ctx(repo)
    assert LockfilePresentRule().applies(ctx) is False


# --- env.llm_critical_deps_pinned -------------------------------------------


def test_llm_deps_unpinned_vllm_on_hf_fixture(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    findings = LlmCriticalDepsPinnedRule().check(_ctx(repo))
    assert [f.message.split(" ")[0] for f in findings] == ["vllm"]
    assert findings[0].severity == Severity.WARNING
    assert "==" in findings[0].fix_hint


def test_llm_deps_warn_when_conda_version_is_prefix(tmp_path: Path) -> None:
    repo = materialize_repo("privacy_custom_params", tmp_path)
    findings = LlmCriticalDepsPinnedRule().check(_ctx(repo))
    assert len(findings) == 1
    finding = findings[0]
    assert finding.message.startswith("torch is used but not pinned")
    assert finding.status == FindingStatus.FAIL
    assert finding.severity == Severity.WARNING
    assert finding.evidence[0].path == "environment.yml"
    assert finding.evidence[0].line == 2
    assert finding.evidence[0].value == "=2.8.0"


def test_llm_deps_import_without_declaration(tmp_path: Path) -> None:
    repo = materialize_repo("not_a_git_repo", tmp_path)
    # train.py imports torch; requirements.txt pins torch==2.8.0 → PASS
    assert LlmCriticalDepsPinnedRule().check(_ctx(repo)) == []


def test_llm_deps_skipped_when_no_critical(tmp_path: Path) -> None:
    repo = materialize_repo("no_deps_file", tmp_path)
    ctx = _ctx(repo)
    assert LlmCriticalDepsPinnedRule().applies(ctx) is False
    assert "no LLM-critical" in (LlmCriticalDepsPinnedRule().skip_reason(ctx) or "")


# --- env.python_version_declared --------------------------------------------


def test_python_version_warning_without_declaration(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    finding = PythonVersionDeclaredRule().check(_ctx(repo))[0]
    assert finding.severity == Severity.WARNING


def test_python_version_pass_via_requires_python(tmp_path: Path) -> None:
    repo = materialize_repo("openai_judge_eval", tmp_path)
    assert PythonVersionDeclaredRule().check(_ctx(repo)) == []


def test_python_version_pass_via_conda_python(tmp_path: Path) -> None:
    repo = materialize_repo("privacy_custom_params", tmp_path)
    assert PythonVersionDeclaredRule().check(_ctx(repo)) == []


# --- env.secret_files_ignored ------------------------------------------------


def test_secret_files_critical_on_tracked_env(tmp_path: Path) -> None:
    repo = materialize_repo("privacy_custom_params", tmp_path)
    finding = SecretFilesIgnoredRule().check(_ctx(repo))[0]
    assert finding.severity == Severity.CRITICAL
    assert finding.evidence[0].path == ".env"


def test_secret_files_pass_with_example_exempt(tmp_path: Path) -> None:
    repo = materialize_repo("openai_judge_eval", tmp_path)
    assert SecretFilesIgnoredRule().check(_ctx(repo)) == []


def test_secret_files_ignored_stays_silent_when_gitignored(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    (repo / ".env").write_text("OPENAI_API_KEY=x\n")
    (repo / ".gitignore").write_text("outputs/\n__pycache__/\n.env\n")
    from tests.conftest import commit_all

    commit_all(repo)  # commit .gitignore; .env is ignored → not listed
    assert SecretFilesIgnoredRule().check(_ctx(repo)) == []


def test_secret_files_downgraded_outside_git(tmp_path: Path) -> None:
    repo = materialize_repo("not_a_git_repo", tmp_path)
    (repo / "creds.pem").write_text("-----BEGIN PRIVATE KEY-----")
    finding = SecretFilesIgnoredRule().check(_ctx(repo))[0]
    assert finding.severity == Severity.WARNING  # CRITICAL downgraded, not a git repo
    assert "not a git repo" in finding.message


# --- env.reprollm_initialized ------------------------------------------------


def test_reprollm_initialized_info_at_level0(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    ctx = _ctx(repo)
    finding = ReprollmInitializedRule().check(ctx)[0]
    assert finding.severity == Severity.INFO
    assert "reprollm init" in finding.message


def test_reprollm_initialized_passes_when_initialized(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    (repo / "reprollm.yaml").write_text("project:\n  name: p\n")
    assert ReprollmInitializedRule().check(_ctx(repo)) == []


def test_reprollm_initialized_skipped_above_level0(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    ctx = _ctx(repo, level=1)
    assert ReprollmInitializedRule().applies(ctx) is False


# --- R07-C D-L: possible import-origin format-lock credit -------------------


_FORMAT_CREDIT_MESSAGE = (
    "torch is used; Python analysis is incomplete or unavailable and a captured format "
    "lock lists the package, so missing pin evidence is not established"
)
_FORMAT_CREDIT_HINT = (
    "Review torch declarations and format-lock origins; complete Python analysis "
    "before deciding that exact pin evidence is absent."
)


def _format_credit_files(root: Path, lock_name: str = "uv.lock") -> str:
    (root / "requirements.txt").write_text("torch>=2\n", encoding="utf-8")
    (root / "a.py").write_text("value = 1\n", encoding="utf-8")
    nested = root / "nested"
    nested.mkdir()
    (nested / "z.py").write_text("import torch\n", encoding="utf-8")
    if lock_name in {"uv.lock", "poetry.lock"}:
        (nested / "pyproject.toml").write_text(
            '[project]\nname = "nested"\nversion = "0.1"\n', encoding="utf-8"
        )
        content = '[[package]]\nname = "torch"\nversion = "2.5.1"\n'
    elif lock_name == "Pipfile.lock":
        (nested / "Pipfile").write_text("[packages]\n", encoding="utf-8")
        content = '{"default": {"torch": {"version": "==2.5.1"}}}\n'
    else:
        (nested / "environment.yml").write_text("dependencies: []\n", encoding="utf-8")
        content = "package:\n  - name: pytorch\n    version: 2.5.1\n"
    (nested / lock_name).write_text(content, encoding="utf-8")
    return f"nested/{lock_name}"


def _format_credit_context(root: Path) -> AuditContext:
    ctx = AuditContext(root)
    ctx._git = GitInfo(is_repo=False)
    return ctx


def _assert_format_credit_skip(finding: Finding, lock_paths: list[str]) -> None:
    assert finding.model_dump(mode="json") == {
        "rule_id": "env.llm_critical_deps_pinned",
        "aliases": [],
        "category": "env",
        "severity": "INFO",
        "status": "skipped",
        "level": 0,
        "message": _FORMAT_CREDIT_MESSAGE,
        "evidence": [
            {
                "kind": "file",
                "path": "requirements.txt",
                "field": None,
                "line": 1,
                "value": ">=2",
                "expected": None,
                "note": "declared as >=2",
            },
            *[
                {
                    "kind": "file",
                    "path": path,
                    "field": None,
                    "line": None,
                    "value": None,
                    "expected": None,
                    "note": "torch listed; import-origin credit unverified",
                }
                for path in lock_paths
            ],
        ],
        "fix_hint": _FORMAT_CREDIT_HINT,
        "profile_origin": [],
        "severity_origin": "default",
        "suppressed_reason": None,
    }


@pytest.mark.parametrize("lock_name", ["uv.lock", "poetry.lock", "Pipfile.lock", "conda-lock.yml"])
def test_missing_import_can_change_format_lock_credit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, lock_name: str
) -> None:
    lock_path = _format_credit_files(tmp_path, lock_name)
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 1)
    capped = _format_credit_context(tmp_path)
    assert capped.pyscan.python_candidate_count == 2
    assert capped.pyscan.python_selected_count == capped.pyscan.python_parsed_count == 1
    assert capped.deps.qualified_lock_packages([]) == frozenset()

    (finding,) = LlmCriticalDepsPinnedRule().check(capped)

    _assert_format_credit_skip(finding, [lock_path])
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 2)
    complete = _format_credit_context(tmp_path)
    assert complete.pyscan.coverage().pass_skip_reason() is None
    assert complete.deps.qualified_lock_packages(
        ("torch", info.path) for info in complete.pyscan.imports
    ) == frozenset({"torch"})
    assert LlmCriticalDepsPinnedRule().check(complete) == []


@pytest.mark.parametrize("lock_case", ["absent", "other-package", "malformed", "unreadable"])
def test_python_gap_preserves_warning_without_captured_format_member(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, lock_case: str
) -> None:
    lock_path = tmp_path / _format_credit_files(tmp_path)
    if lock_case == "absent":
        lock_path.unlink()
    elif lock_case == "other-package":
        lock_path.write_text('[[package]]\nname = "numpy"\n', encoding="utf-8")
    elif lock_case == "malformed":
        lock_path.write_text("[invalid\n", encoding="utf-8")
    else:
        original_open = Path.open

        def deny_lock(path: Path, *args: Any, **kwargs: Any) -> IO[Any]:
            if path == lock_path:
                raise PermissionError("synthetic unreadable lock")
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr(Path, "open", deny_lock)
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 1)
    monkeypatch.setattr("reprollm.rules.env.installed_versions", lambda: {})
    ctx = _format_credit_context(tmp_path)
    assert ctx.pyscan.coverage().pass_skip_reason() is not None

    (finding,) = LlmCriticalDepsPinnedRule().check(ctx)

    assert finding.status == FindingStatus.FAIL
    assert finding.severity == Severity.WARNING
    assert finding.message == (
        "torch is used but not pinned to an exact version (suggestion: torch==<version>)"
    )
    assert len(finding.evidence) == 1
    assert finding.evidence[0].path == "requirements.txt"
    assert finding.evidence[0].note == "declared as >=2"


@pytest.mark.parametrize(
    "pin_source", ["exact-declaration", "qualified-declaration", "requirements"]
)
def test_known_pin_credit_precedes_possible_credit_skip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, pin_source: str
) -> None:
    _format_credit_files(tmp_path)
    if pin_source == "exact-declaration":
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "root"\ndependencies = ["torch==2.5.1"]\n', encoding="utf-8"
        )
    elif pin_source == "qualified-declaration":
        (tmp_path / "nested" / "pyproject.toml").write_text(
            '[project]\nname = "nested"\ndependencies = ["torch>=2"]\n', encoding="utf-8"
        )
    else:
        (tmp_path / "requirements.txt").write_text("-r pins.txt\n", encoding="utf-8")
        (tmp_path / "pins.txt").write_text("torch==2.5.1\n", encoding="utf-8")
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 1)
    ctx = _format_credit_context(tmp_path)

    assert LlmCriticalDepsPinnedRule().check(ctx) == []
    assert LlmCriticalDepsPinnedRule().pass_skip_reason(ctx) is not None


@pytest.mark.parametrize(
    ("observed", "candidate", "selected", "parsed", "limit"),
    [(False, 0, 0, 0, 0), (True, 2, 1, 2, 2)],
    ids=["unobserved", "parsed-over-selected"],
)
def test_unavailable_python_view_keeps_format_credit_unverified(
    tmp_path: Path, observed: bool, candidate: int, selected: int, parsed: int, limit: int
) -> None:
    lock_path = _format_credit_files(tmp_path)
    ctx = _format_credit_context(tmp_path)
    ctx._pyscan = PyScanResult(
        coverage_observed=observed,
        python_candidate_count=candidate,
        python_selected_count=selected,
        python_parsed_count=parsed,
        python_file_limit=limit,
    )

    (finding,) = LlmCriticalDepsPinnedRule().check(ctx)

    _assert_format_credit_skip(finding, [lock_path])


@pytest.mark.parametrize("failure", ["syntax", "binary", "read-cap", "unreadable"])
def test_selected_python_failure_keeps_format_credit_unverified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    lock_path = _format_credit_files(tmp_path)
    bad = tmp_path / "a.py"
    if failure == "syntax":
        bad.write_text("def broken(:\n", encoding="utf-8")
    elif failure == "binary":
        bad.write_bytes(b"value = 1\x00\n")
    elif failure == "read-cap":
        bad.write_text("#" + "x" * scanner_mod.MAX_READ_BYTES, encoding="utf-8")
    else:
        original_open = Path.open

        def deny_python(path: Path, *args: Any, **kwargs: Any) -> IO[Any]:
            if path == bad:
                raise PermissionError("synthetic unreadable Python source")
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr(Path, "open", deny_python)
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 1)
    ctx = _format_credit_context(tmp_path)
    assert ctx.pyscan.python_candidate_count == 2
    assert ctx.pyscan.python_selected_count == 1
    assert ctx.pyscan.python_parsed_count == 0

    (finding,) = LlmCriticalDepsPinnedRule().check(ctx)

    _assert_format_credit_skip(finding, [lock_path])


@pytest.mark.parametrize("barrier", ["unpaired", "nearer-project", "uncertain-project"])
def test_possible_credit_is_deliberately_conservative_but_complete_view_is_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, barrier: str
) -> None:
    lock_path = _format_credit_files(tmp_path)
    nested = tmp_path / "nested"
    if barrier == "unpaired":
        (nested / "pyproject.toml").unlink()
    else:
        deeper = nested / "deeper"
        deeper.mkdir()
        (nested / "z.py").unlink()
        (deeper / "z.py").write_text("import torch\n", encoding="utf-8")
        (deeper / "pyproject.toml").write_text(
            '[project]\nname = "deeper"\n' if barrier == "nearer-project" else "[invalid\n",
            encoding="utf-8",
        )
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 1)
    capped = _format_credit_context(tmp_path)

    (finding,) = LlmCriticalDepsPinnedRule().check(capped)

    _assert_format_credit_skip(finding, [lock_path])
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 2)
    complete = _format_credit_context(tmp_path)
    assert complete.pyscan.coverage().pass_skip_reason() is None
    complete.pyscan.warnings.append("Python candidate analysis incomplete: SyntheticCoverageCanary")
    assert "torch" not in complete.deps.qualified_lock_packages(
        ("torch", info.path) for info in complete.pyscan.imports
    )
    (unchanged,) = LlmCriticalDepsPinnedRule().check(complete)
    assert (unchanged.status, unchanged.severity) == (FindingStatus.FAIL, Severity.WARNING)
    assert unchanged.message.startswith("torch is used but not pinned to an exact version")
    assert len(unchanged.evidence) == 1


def test_format_lock_entries_do_not_create_package_usage(tmp_path: Path) -> None:
    _format_credit_files(tmp_path)
    (tmp_path / "requirements.txt").write_text("# no package declaration\n", encoding="utf-8")
    (tmp_path / "nested" / "z.py").write_text("value = 1\n", encoding="utf-8")
    ctx = _format_credit_context(tmp_path)
    assert any("torch" in lock.packages for lock in ctx.deps.lockfiles)
    assert LlmCriticalDepsPinnedRule().applies(ctx) is False
    assert LlmCriticalDepsPinnedRule().check(ctx) == []


def test_format_credit_skip_coexists_with_unpinned_warning_and_sorted_lock_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lock_path = tmp_path / _format_credit_files(tmp_path)
    content = lock_path.read_text(encoding="utf-8")
    lock_path.unlink()
    for directory, name in [("z", "uv.lock"), ("a", "poetry.lock")]:
        (tmp_path / directory).mkdir()
        (tmp_path / directory / name).write_text(content, encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("torch>=2\nnumpy>=1\n", encoding="utf-8")
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 1)
    monkeypatch.setattr("reprollm.rules.env.installed_versions", lambda: {})

    warning, skipped = LlmCriticalDepsPinnedRule().check(_format_credit_context(tmp_path))

    assert warning.message == (
        "numpy is used but not pinned to an exact version (suggestion: numpy==<version>)"
    )
    assert (warning.status, warning.severity) == (FindingStatus.FAIL, Severity.WARNING)
    _assert_format_credit_skip(skipped, ["a/poetry.lock", "z/uv.lock"])


# --- R07-C D-F: associated format-lock contents could not be captured -------


_LOCK_CONTENT_MESSAGE = (
    "torch is used; an associated format lock could not be read or parsed, "
    "so missing pin evidence is not established"
)
_LOCK_CONTENT_HINT = (
    "Review torch declarations and associated format-lock files; restore readable, "
    "valid lock contents before deciding that exact pin evidence is absent."
)


def _failed_format_files(root: Path, lock_name: str = "uv.lock") -> tuple[str, int]:
    if lock_name in {"uv.lock", "poetry.lock"}:
        manifest, line = "pyproject.toml", 3
        content = '[project]\nname = "failed-lock"\ndependencies = ["torch>=2"]\n'
    elif lock_name == "Pipfile.lock":
        manifest, line = "Pipfile", 2
        content = '[packages]\ntorch = ">=2"\n'
    else:
        manifest, line = "environment.yml", 1
        content = "dependencies:\n  - pytorch>=2\n"
    (root / manifest).write_text(content, encoding="utf-8")
    (root / lock_name).write_text("[broken\n", encoding="utf-8")
    return manifest, line


def _assert_lock_contents_skip(
    finding: Finding, use_path: str, use_line: int, lock_paths: list[str]
) -> None:
    assert finding.model_dump(mode="json") == {
        "rule_id": "env.llm_critical_deps_pinned",
        "aliases": [],
        "category": "env",
        "severity": "INFO",
        "status": "skipped",
        "level": 0,
        "message": _LOCK_CONTENT_MESSAGE,
        "evidence": [
            {
                "kind": "file",
                "path": use_path,
                "field": None,
                "line": use_line,
                "value": ">=2",
                "expected": None,
                "note": "declared as >=2",
            },
            *[
                {
                    "kind": "file",
                    "path": path,
                    "field": None,
                    "line": None,
                    "value": None,
                    "expected": None,
                    "note": "torch associated; lock package contents unverified",
                }
                for path in lock_paths
            ],
        ],
        "fix_hint": _LOCK_CONTENT_HINT,
        "profile_origin": [],
        "severity_origin": "default",
        "suppressed_reason": None,
    }


@pytest.mark.parametrize("lock_name", ["uv.lock", "poetry.lock", "Pipfile.lock", "conda-lock.yml"])
@pytest.mark.parametrize("failure", ["syntax", "unreadable"])
def test_associated_failed_lock_contents_do_not_establish_missing_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, lock_name: str, failure: str
) -> None:
    manifest, line = _failed_format_files(tmp_path, lock_name)
    if failure == "unreadable":
        original_open = Path.open

        def deny_lock(path: Path, *args: Any, **kwargs: Any) -> IO[Any]:
            if path == tmp_path / lock_name:
                raise PermissionError("synthetic lock read denial")
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr(Path, "open", deny_lock)
    ctx = _format_credit_context(tmp_path)
    assert ctx.pyscan.coverage().pass_skip_reason() is None
    assert ctx.deps.qualified_lock_packages([]) == frozenset()

    (finding,) = LlmCriticalDepsPinnedRule().check(ctx)

    _assert_lock_contents_skip(finding, manifest, line, [lock_name])
    assert LockfilePresentRule().check(ctx) == []


@pytest.mark.parametrize("failure", ["read-cap", "binary", "invalid-utf8"])
def test_associated_unreadable_lock_keeps_the_existing_read_boundary(
    tmp_path: Path, failure: str
) -> None:
    manifest, line = _failed_format_files(tmp_path)
    if failure == "read-cap":
        (tmp_path / "uv.lock").write_text("#" * (scanner_mod.MAX_READ_BYTES + 1), encoding="utf-8")
    elif failure == "binary":
        (tmp_path / "uv.lock").write_bytes(b"\x00synthetic binary lock\n")
    else:
        (tmp_path / "uv.lock").write_bytes(b"\xff\xfe\n")

    (finding,) = LlmCriticalDepsPinnedRule().check(_format_credit_context(tmp_path))

    _assert_lock_contents_skip(finding, manifest, line, ["uv.lock"])


@pytest.mark.parametrize("lock_name", ["uv.lock", "poetry.lock", "Pipfile.lock", "conda-lock.yml"])
@pytest.mark.parametrize("restored", ["member", "empty", "other-package"])
def test_restoring_lock_contents_restores_the_existing_membership_decision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, lock_name: str, restored: str
) -> None:
    _failed_format_files(tmp_path, lock_name)
    monkeypatch.setattr("reprollm.rules.env.installed_versions", lambda: {})
    (unknown,) = LlmCriticalDepsPinnedRule().check(_format_credit_context(tmp_path))
    assert (unknown.status, unknown.severity) == (FindingStatus.SKIPPED, Severity.INFO)
    name = "torch" if restored == "member" else "numpy"
    if lock_name in {"uv.lock", "poetry.lock"}:
        content = "" if restored == "empty" else f'[[package]]\nname = "{name}"\n'
    elif lock_name == "Pipfile.lock":
        content = "{}\n" if restored == "empty" else f'{{"default": {{"{name}": {{}}}}}}\n'
    else:
        content = "package: []\n" if restored == "empty" else f"package:\n  - name: {name}\n"
    (tmp_path / lock_name).write_text(content, encoding="utf-8")

    findings = LlmCriticalDepsPinnedRule().check(_format_credit_context(tmp_path))

    if restored == "member":
        assert findings == []
    else:
        (finding,) = findings
        assert (finding.status, finding.severity) == (FindingStatus.FAIL, Severity.WARNING)
        assert finding.message == (
            "torch is used but not pinned to an exact version (suggestion: torch==<version>)"
        )
        assert len(finding.evidence) == 1


@pytest.mark.parametrize("credit", ["root-exact", "nested-exact", "requirements", "other-lock"])
def test_known_pin_credit_precedes_failed_associated_lock_contents(
    tmp_path: Path, credit: str
) -> None:
    _failed_format_files(tmp_path)
    if credit == "root-exact":
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "root"\ndependencies = ["torch==2.5.1"]\n', encoding="utf-8"
        )
    elif credit == "nested-exact":
        (tmp_path / "nested").mkdir()
        (tmp_path / "nested" / "requirements.txt").write_text("torch==2.5.1\n", encoding="utf-8")
    elif credit == "requirements":
        (tmp_path / "requirements.txt").write_text("-r pins.txt\n", encoding="utf-8")
        (tmp_path / "pins.txt").write_text("torch==2.5.1\n", encoding="utf-8")
    else:
        (tmp_path / "poetry.lock").write_text('[[package]]\nname = "torch"\n', encoding="utf-8")

    assert LlmCriticalDepsPinnedRule().check(_format_credit_context(tmp_path)) == []


@pytest.mark.parametrize(
    "origin_case",
    [
        "paired-import",
        "unpaired",
        "tool-only",
        "wrong-manager",
        "poetry-only",
        "nearer-project",
        "barrier",
        "sibling",
    ],
)
def test_failed_lock_uncertainty_uses_existing_captured_origin_association(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, origin_case: str
) -> None:
    (tmp_path / "requirements.txt").write_text("torch>=2\n", encoding="utf-8")
    (tmp_path / "a.py").write_text("import torch\n", encoding="utf-8")
    (tmp_path / "uv.lock").write_text("[broken\n", encoding="utf-8")
    project = tmp_path / "pyproject.toml"
    if origin_case == "tool-only":
        project.write_text("[tool.ruff]\n", encoding="utf-8")
    elif origin_case == "wrong-manager":
        (tmp_path / "Pipfile").write_text("[packages]\n", encoding="utf-8")
    elif origin_case == "poetry-only":
        project.write_text('[tool.poetry]\nname = "owner"\n', encoding="utf-8")
    elif origin_case not in {"unpaired", "sibling"}:
        project.write_text('[project]\nname = "owner"\n', encoding="utf-8")
    if origin_case in {"nearer-project", "barrier", "sibling"}:
        nested = tmp_path / "nested"
        nested.mkdir()
        (nested / "pyproject.toml").write_text(
            "[broken\n" if origin_case == "barrier" else '[project]\nname = "nested"\n',
            encoding="utf-8",
        )
        if origin_case == "sibling":
            (tmp_path / "uv.lock").rename(nested / "uv.lock")
        else:
            (tmp_path / "a.py").rename(nested / "a.py")
    monkeypatch.setattr("reprollm.rules.env.installed_versions", lambda: {})
    ctx = _format_credit_context(tmp_path)
    assert ctx.pyscan.coverage().pass_skip_reason() is None

    (finding,) = LlmCriticalDepsPinnedRule().check(ctx)

    if origin_case == "paired-import":
        _assert_lock_contents_skip(finding, "requirements.txt", 1, ["uv.lock"])
    else:
        assert (finding.status, finding.severity) == (FindingStatus.FAIL, Severity.WARNING)
        assert finding.message == (
            "torch is used but not pinned to an exact version (suggestion: torch==<version>)"
        )
        assert len(finding.evidence) == 1


def test_failed_locks_do_not_create_package_usage(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "unused"\n', encoding="utf-8")
    (tmp_path / "uv.lock").write_text("[broken\n", encoding="utf-8")
    ctx = _format_credit_context(tmp_path)

    assert LlmCriticalDepsPinnedRule().applies(ctx) is False
    assert LlmCriticalDepsPinnedRule().check(ctx) == []


def test_ambiguous_conda_manifests_do_not_create_an_association_to_a_failed_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for manifest in ("environment.yml", "environment.yaml"):
        (tmp_path / manifest).write_text("dependencies:\n  - pytorch>=2\n", encoding="utf-8")
    (tmp_path / "conda-lock.yml").write_text("[broken\n", encoding="utf-8")
    monkeypatch.setattr("reprollm.rules.env.installed_versions", lambda: {})

    (finding,) = LlmCriticalDepsPinnedRule().check(_format_credit_context(tmp_path))

    assert (finding.status, finding.severity) == (FindingStatus.FAIL, Severity.WARNING)
    assert finding.message == (
        "torch is used but not pinned to an exact version (suggestion: torch==<version>)"
    )


def test_unlisted_oversize_format_lock_is_not_a_captured_failed_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _failed_format_files(tmp_path)
    (tmp_path / "uv.lock").write_text("#" * (scanner_mod.MAX_FILE_BYTES + 1), encoding="utf-8")
    monkeypatch.setattr("reprollm.rules.env.installed_versions", lambda: {})
    ctx = _format_credit_context(tmp_path)
    assert ctx.deps.lockfiles == []

    (finding,) = LlmCriticalDepsPinnedRule().check(ctx)

    assert (finding.status, finding.severity) == (FindingStatus.FAIL, Severity.WARNING)
    assert len(finding.evidence) == 1


@pytest.mark.parametrize("python_view", ["capped", "unavailable"])
def test_failed_associated_lock_uncertainty_is_independent_of_python_coverage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, python_view: str
) -> None:
    manifest, line = _failed_format_files(tmp_path)
    (tmp_path / "a.py").write_text("value = 1\n", encoding="utf-8")
    (tmp_path / "z.py").write_text("value = 2\n", encoding="utf-8")
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 1)
    ctx = _format_credit_context(tmp_path)
    if python_view == "unavailable":
        ctx._pyscan = PyScanResult()
    assert ctx.pyscan.coverage().pass_skip_reason() is not None

    (finding,) = LlmCriticalDepsPinnedRule().check(ctx)

    _assert_lock_contents_skip(finding, manifest, line, ["uv.lock"])


def test_failed_lock_contents_skip_coexists_with_stable_warning_and_sorted_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "requirements.txt").write_text("torch>=2\nnumpy>=1\n", encoding="utf-8")
    for directory, lock_name in [("z", "uv.lock"), ("a", "poetry.lock")]:
        project = tmp_path / directory
        project.mkdir()
        (project / "pyproject.toml").write_text('[project]\nname = "paired"\n', encoding="utf-8")
        (project / lock_name).write_text("[broken\n", encoding="utf-8")
        (project / "a.py").write_text("import torch\n", encoding="utf-8")
    monkeypatch.setattr("reprollm.rules.env.installed_versions", lambda: {})

    warning, skipped = LlmCriticalDepsPinnedRule().check(_format_credit_context(tmp_path))

    assert (warning.status, warning.severity) == (FindingStatus.FAIL, Severity.WARNING)
    assert warning.message == (
        "numpy is used but not pinned to an exact version (suggestion: numpy==<version>)"
    )
    _assert_lock_contents_skip(skipped, "requirements.txt", 1, ["a/poetry.lock", "z/uv.lock"])


# --- R07-C D-S: known decoded structure failure uses the D-F policy --------


@pytest.mark.parametrize(
    ("lock_name", "body"),
    [
        ("uv.lock", "package = false\n"),
        ("poetry.lock", 'package = [{name = ""}]\n'),
        ("Pipfile.lock", '{"default": null}\n'),
        ("conda-lock.yml", "package: [null]\n"),
    ],
)
def test_associated_structurally_invalid_lock_keeps_missing_pin_unverified(
    tmp_path: Path, lock_name: str, body: str
) -> None:
    manifest, line = _failed_format_files(tmp_path, lock_name)
    (tmp_path / lock_name).write_text(body, encoding="utf-8")
    ctx = _format_credit_context(tmp_path)
    assert ctx.pyscan.coverage().pass_skip_reason() is None

    (finding,) = LlmCriticalDepsPinnedRule().check(ctx)

    _assert_lock_contents_skip(finding, manifest, line, [lock_name])
    assert LockfilePresentRule().check(ctx) == []


@pytest.mark.parametrize("view", ["zero", "complete", "capped", "unavailable"])
def test_structural_lock_failure_is_independent_of_primary_python_analysis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, view: str
) -> None:
    manifest, line = _failed_format_files(tmp_path)
    (tmp_path / "uv.lock").write_text("package = [{}]\n", encoding="utf-8")
    if view != "zero":
        (tmp_path / "a.py").write_text("value = 1\n", encoding="utf-8")
        (tmp_path / "z.py").write_text("value = 2\n", encoding="utf-8")
    if view == "capped":
        monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 1)
    ctx = _format_credit_context(tmp_path)
    if view == "unavailable":
        ctx._pyscan = PyScanResult()

    (finding,) = LlmCriticalDepsPinnedRule().check(ctx)

    _assert_lock_contents_skip(finding, manifest, line, ["uv.lock"])


@pytest.mark.parametrize("credit", ["exact", "nested-exact", "other-lock", "partial-member"])
def test_structural_lock_failure_does_not_revoke_positive_pin_credit(
    tmp_path: Path, credit: str
) -> None:
    _failed_format_files(tmp_path)
    (tmp_path / "uv.lock").write_text("package = [{}]\n", encoding="utf-8")
    if credit == "exact":
        (tmp_path / "pyproject.toml").write_text(
            '[project]\ndependencies = ["torch==2.5.1"]\n', encoding="utf-8"
        )
    elif credit == "nested-exact":
        (tmp_path / "nested").mkdir()
        (tmp_path / "nested" / "requirements.txt").write_text("torch==2.5.1\n", encoding="utf-8")
    elif credit == "other-lock":
        (tmp_path / "poetry.lock").write_text('[[package]]\nname = "torch"\n', encoding="utf-8")
    else:
        (tmp_path / "uv.lock").write_text('package = [{name = "torch"}, {}]\n', encoding="utf-8")

    assert LlmCriticalDepsPinnedRule().check(_format_credit_context(tmp_path)) == []


@pytest.mark.parametrize("origin_case", ["unpaired", "wrong-manager", "nearer-project", "barrier"])
def test_unassociated_structural_lock_failure_keeps_existing_package_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, origin_case: str
) -> None:
    (tmp_path / "requirements.txt").write_text("torch>=2\n", encoding="utf-8")
    (tmp_path / "a.py").write_text("import torch\n", encoding="utf-8")
    (tmp_path / "uv.lock").write_text("package = [{}]\n", encoding="utf-8")
    if origin_case == "wrong-manager":
        (tmp_path / "Pipfile").write_text("[packages]\n", encoding="utf-8")
    elif origin_case in {"nearer-project", "barrier"}:
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "outer"\n', encoding="utf-8")
        nested = tmp_path / "nested"
        nested.mkdir()
        (nested / "pyproject.toml").write_text(
            "[broken\n" if origin_case == "barrier" else '[project]\nname = "inner"\n',
            encoding="utf-8",
        )
        (tmp_path / "a.py").rename(nested / "a.py")
    monkeypatch.setattr("reprollm.rules.env.installed_versions", lambda: {})

    (finding,) = LlmCriticalDepsPinnedRule().check(_format_credit_context(tmp_path))

    assert (finding.status, finding.severity) == (FindingStatus.FAIL, Severity.WARNING)
    assert finding.message == (
        "torch is used but not pinned to an exact version (suggestion: torch==<version>)"
    )
    assert len(finding.evidence) == 1


@pytest.mark.parametrize("lock_name", ["uv.lock", "poetry.lock", "Pipfile.lock", "conda-lock.yml"])
def test_partial_lock_members_keep_credit_while_other_associated_usage_remains_unverified(
    tmp_path: Path, lock_name: str
) -> None:
    if lock_name in {"uv.lock", "poetry.lock"}:
        manifest, line = "pyproject.toml", 2
        declaration = '[project]\ndependencies = ["numpy>=1", "torch>=2"]\n'
        body = 'package = [{name = "numpy"}, {}]\n'
    elif lock_name == "Pipfile.lock":
        manifest, line = "Pipfile", 3
        declaration = '[packages]\nnumpy = ">=1"\ntorch = ">=2"\n'
        body = '{"default": {"numpy": {}}, "develop": false}\n'
    else:
        manifest, line = "environment.yml", 2
        declaration = "dependencies:\n  - numpy>=1\n  - pytorch>=2\n"
        body = "package: [{name: numpy}, {}]\n"
    (tmp_path / manifest).write_text(declaration, encoding="utf-8")
    (tmp_path / lock_name).write_text(body, encoding="utf-8")

    (finding,) = LlmCriticalDepsPinnedRule().check(_format_credit_context(tmp_path))

    _assert_lock_contents_skip(finding, manifest, line, [lock_name])


def test_structural_lock_failure_does_not_create_critical_package_usage(
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "no-use"\n', encoding="utf-8")
    (tmp_path / "uv.lock").write_text('package = [{name = "torch"}, {}]\n', encoding="utf-8")
    ctx = _format_credit_context(tmp_path)

    assert LlmCriticalDepsPinnedRule().applies(ctx) is False
    assert LlmCriticalDepsPinnedRule().check(ctx) == []


def test_structural_and_syntax_failures_share_sorted_evidence_and_preserve_other_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "requirements.txt").write_text("torch>=2\nnumpy>=1\n", encoding="utf-8")
    for directory, lock_name, body in [
        ("a", "poetry.lock", "package = [{}]\n"),
        ("z", "uv.lock", "[broken\n"),
    ]:
        project = tmp_path / directory
        project.mkdir()
        (project / "pyproject.toml").write_text('[project]\nname = "owner"\n', encoding="utf-8")
        (project / lock_name).write_text(body, encoding="utf-8")
        (project / "a.py").write_text("import torch\n", encoding="utf-8")
    monkeypatch.setattr("reprollm.rules.env.installed_versions", lambda: {})

    warning, skipped = LlmCriticalDepsPinnedRule().check(_format_credit_context(tmp_path))

    assert (warning.status, warning.severity) == (FindingStatus.FAIL, Severity.WARNING)
    assert warning.message == (
        "numpy is used but not pinned to an exact version (suggestion: numpy==<version>)"
    )
    _assert_lock_contents_skip(skipped, "requirements.txt", 1, ["a/poetry.lock", "z/uv.lock"])
