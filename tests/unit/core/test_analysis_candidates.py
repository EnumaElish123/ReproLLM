"""R07-A static candidates preserve business analysis and repository facts."""

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.core import scanner as scanner_mod
from reprollm.core.context import AuditContext
from reprollm.core.proc import run_cmd
from reprollm.core.yaml_io import load_manifest
from reprollm.discover.collector import collect
from reprollm.integrations._static import task_mapping
from reprollm.integrations.lighteval import LightEvalIntegration
from reprollm.integrations.lm_eval import LmEvalIntegration
from reprollm.rules.env import PythonVersionDeclaredRule, SecretFilesIgnoredRule
from reprollm.schemas.config import DiscoverConfig
from reprollm.schemas.finding import Severity


def _write(root: Path, path: str, text: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(text.encode("utf-8"))


def _git(root: Path, *args: str) -> None:
    result = run_cmd(["git", *args], cwd=root)
    assert result.returncode == 0, result.stderr


def test_git_venv_files_do_not_consume_business_python_budget(tmp_path: Path) -> None:
    _write(tmp_path, "train.py", "import openai\n")
    _write(tmp_path, "requirements.txt", "openai==1.50.0\n")
    _git(tmp_path, "init")
    _git(tmp_path, "add", "--", "train.py", "requirements.txt")
    for index in range(501):
        _write(tmp_path, f".venv/lib/f{index:04}.py", "import vllm\n")
    _git(tmp_path, "add", "--", ".venv")

    context = AuditContext(tmp_path)
    assert context.fs.python_files() == ["train.py"]
    assert [(item.module, item.path) for item in context.pyscan.imports] == [("openai", "train.py")]
    assert context.detection.hints.providers == ["openai"]
    assert context.detection.hints.backends == []
    assert context.fs.warnings == []
    assert ".venv/lib/f0000.py" in context.fs.files()


@pytest.mark.parametrize(
    ("directory", "marker"),
    [
        (".venv", False),
        ("node_modules", False),
        ("__pycache__", False),
        ("package.egg-info", False),
        ("custom_environment", True),
        ("tasks/custom_environment", True),
    ],
)
def test_excluded_environment_signals_do_not_enter_any_static_consumer(
    tmp_path: Path, directory: str, marker: bool
) -> None:
    _write(tmp_path, "train.py", "import openai\n")
    _write(tmp_path, "requirements.txt", "openai==1.50.0\n")
    _write(tmp_path, "README.md", "A research experiment.\n")
    _write(tmp_path, "tasks/business.yaml", "task: business\ndataset_path: demo/corpus\n")
    polluted = {
        "README.md": "judge rubric differential privacy\n",
        "requirements.txt": "vllm==0.6.1\n",
        "uv.lock": '[[package]]\nname = "vllm"\nversion = "0.6.1"\n',
        ".python-version": "9.9\n",
        "judge_rubric.yaml": "task: environment_canary\njudge: rubric\nprivacy: epsilon\n",
        "launch.sh": "lighteval --tasks environment_canary\n",
        "evaluation/privacy/attack.py": "import vllm\nimport inspect_ai\n",
        ".env.local": "SYNTHETIC_CANARY=value\n",
    }
    for relative, text in polluted.items():
        _write(tmp_path, f"{directory}/{relative}", text)
    if marker:
        _write(tmp_path, f"{directory}/pyvenv.cfg", "home = synthetic\n")
    _git(tmp_path, "init")
    _git(tmp_path, "add", "--", ".")
    _write(tmp_path, f"{directory}/untracked.txt", "new file fact\n")

    context = AuditContext(tmp_path)
    assert [(d.name, d.source_file) for d in context.deps.declarations] == [
        ("openai", "requirements.txt")
    ]
    assert [lock.path for lock in context.deps.lockfiles] == ["requirements.txt"]
    assert context.detection.hints.providers == ["openai"]
    assert context.detection.hints.backends == []
    assert [item.profile for item in context.detection.profiles] == ["evaluation"]
    assert len(PythonVersionDeclaredRule().check(context)) == 1
    assert LightEvalIntegration().detect(context.fs) == []
    assert LightEvalIntegration().extract_task_hints(context.fs).task_names == ["business"]
    assert LmEvalIntegration().extract_task_hints(context.fs).task_names == ["business"]
    payload = collect(tmp_path, context.fs, DiscoverConfig())
    assert all(not item.path.startswith(directory + "/") for item in payload.files)
    assert all(not path.startswith(directory + "/") for path in payload.tree)
    assert "environment_canary" not in payload.render()
    assert f"{directory}/requirements.txt" in context.fs.files()
    assert f"{directory}/untracked.txt" in context.git.untracked
    findings = SecretFilesIgnoredRule().check(context)
    assert len(findings) == 1
    assert findings[0].severity == Severity.CRITICAL
    assert findings[0].evidence[0].path == f"{directory}/.env.local"


@pytest.mark.parametrize("directory", [".venv", "marked_environment"])
def test_explicit_requirement_and_task_paths_cannot_bypass_candidate_exclusions(
    tmp_path: Path, directory: str
) -> None:
    _write(tmp_path, "requirements.txt", f"-r {directory}/pins.txt\n")
    _write(tmp_path, f"{directory}/pins.txt", "vllm==0.6.1\n")
    _write(tmp_path, f"{directory}/task.yaml", "task: environment_canary\n")
    if directory == "marked_environment":
        _write(tmp_path, f"{directory}/pyvenv.cfg", "home = synthetic\n")
    context = AuditContext(tmp_path)
    assert context.deps.manifest_present
    assert context.deps.declarations == []
    assert context.deps.lockfiles == []
    assert context.deps.unparsed == ["requirements.txt:1: include unreadable"]
    assert task_mapping(context.fs, f"{directory}/task.yaml") is None


@pytest.mark.parametrize("directory", [".venv", "marked_environment", ".reprollm/runs/one"])
def test_internal_aliases_cannot_restore_excluded_environment_content(
    tmp_path: Path, directory: str
) -> None:
    _write(tmp_path, "requirements.txt", "-r alias-pins.txt\n")
    _write(tmp_path, f"{directory}/pins.txt", "vllm==0.6.1\n")
    _write(tmp_path, f"{directory}/implementation.py", "import vllm\n")
    if directory == "marked_environment":
        _write(tmp_path, f"{directory}/pyvenv.cfg", "home = synthetic\n")
    try:
        (tmp_path / "alias-pins.txt").symlink_to(tmp_path / directory / "pins.txt")
        (tmp_path / "alias.py").symlink_to(tmp_path / directory / "implementation.py")
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlinks unavailable: {type(exc).__name__}")
    context = AuditContext(tmp_path)
    assert context.deps.declarations == []
    assert context.deps.lockfiles == []
    assert context.deps.unparsed == ["requirements.txt:1: include unreadable"]
    assert context.pyscan.imports == []
    assert context.detection.hints.backends == []
    assert "alias.py" in context.fs.files()
    assert "alias.py" not in context.fs.analysis_files()


def test_uninspectable_marker_skips_candidate_without_crashing_or_hiding_git_facts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, "train.py", "import openai\n")
    _write(tmp_path, "restricted/implementation.py", "import vllm\n")
    _git(tmp_path, "init")
    _git(tmp_path, "add", "--", ".")
    original_exists = Path.exists

    def guarded_exists(path: Path) -> bool:
        if path == tmp_path / "restricted/pyvenv.cfg":
            raise PermissionError("synthetic inaccessible marker")
        return original_exists(path)

    monkeypatch.setattr(Path, "exists", guarded_exists)
    context = AuditContext(tmp_path)
    assert [item.module for item in context.pyscan.imports] == ["openai"]
    assert "restricted/implementation.py" in context.fs.files()
    assert context.fs.warnings == ["restricted: cannot inspect environment marker; skipped"]
    assert context.fs.analysis_files() == ["train.py"]
    assert len(context.fs.warnings) == 1


def test_run_directory_names_and_explicit_inputs_do_not_create_static_signals(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "requirements.txt", "-r .reprollm/runs/one/pins.txt\n")
    _write(tmp_path, ".reprollm/runs/one/pins.txt", "vllm==0.6.1\n")
    (tmp_path / ".reprollm/runs/one/evaluation/privacy").mkdir(parents=True)
    context = AuditContext(tmp_path)
    assert "evaluation" not in context.fs.dir_names()
    assert "privacy" not in context.fs.dir_names()
    assert context.detection.profiles == []
    assert context.deps.declarations == []
    assert context.deps.unparsed == ["requirements.txt:1: include unreadable"]
    (tmp_path / "evaluation").mkdir()
    assert "evaluation" in AuditContext(tmp_path).fs.dir_names()


@pytest.mark.parametrize("git_mode", [False, True], ids=["walk", "git"])
@pytest.mark.parametrize(
    "directory",
    [
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        "__pycache__",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        ".tox",
        "dist",
        "build",
        ".eggs",
        ".venv",
        "venv",
        "research.egg-info",
        "marked_environment",
    ],
)
def test_known_directory_exclusions_apply_before_static_analysis_in_both_modes(
    tmp_path: Path, git_mode: bool, directory: str
) -> None:
    _write(tmp_path, "train.py", "import openai\n")
    if git_mode:
        _git(tmp_path, "init")
    # A Git repository's own .git directory cannot be staged as user content.
    nested = f"nested/{directory}"
    _write(tmp_path, f"{nested}/evaluation/implementation.py", "import vllm\n")
    if directory == "marked_environment":
        _write(tmp_path, f"{nested}/pyvenv.cfg", "home = synthetic\n")
    if git_mode:
        _git(tmp_path, "add", "--", ".")
    context = AuditContext(tmp_path)
    assert context.fs.python_files() == ["train.py"]
    assert [item.module for item in context.pyscan.imports] == ["openai"]
    assert "evaluation" not in context.fs.dir_names()
    assert context.detection.profiles == []


@pytest.mark.parametrize("git_mode", [False, True], ids=["walk", "git"])
def test_real_nested_projects_and_root_marker_remain_candidates(
    tmp_path: Path, git_mode: bool
) -> None:
    _write(tmp_path, "pyvenv.cfg", "home = audit root remains in scope\n")
    _write(tmp_path, "vendor/research/implementation.py", "import openai\n")
    _write(tmp_path, "third_party/research/requirements.txt", "openai==1.50.0\n")
    _write(tmp_path, "tasks/business.yaml", "task: business\ndataset_path: demo/corpus\n")
    if git_mode:
        _git(tmp_path, "init")
        _git(tmp_path, "add", "--", ".")
    context = AuditContext(tmp_path)
    assert context.fs.python_files() == ["vendor/research/implementation.py"]
    assert [(item.name, item.source_file) for item in context.deps.declarations] == [
        ("openai", "third_party/research/requirements.txt")
    ]
    assert context.detection.hints.providers == ["openai"]
    assert LmEvalIntegration().extract_task_hints(context.fs).task_names == ["business"]


def test_internal_business_aliases_and_explicit_normalized_include_remain_safe(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "requirements.txt", "-r configs/../pins.txt\n")
    _write(tmp_path, "pins.txt", "openai==1.50.0\n")
    _write(tmp_path, "research/implementation.py", "import openai\n")
    (tmp_path / "configs").mkdir()
    try:
        (tmp_path / "alias.py").symlink_to(tmp_path / "research/implementation.py")
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlinks unavailable: {type(exc).__name__}")
    context = AuditContext(tmp_path)
    assert context.deps.unparsed == []
    assert [(item.name, item.source_file) for item in context.deps.declarations] == [
        ("openai", "pins.txt")
    ]
    assert context.fs.python_files() == ["alias.py", "research/implementation.py"]
    assert context.detection.hints.providers == ["openai"]


def test_external_aliases_do_not_inspect_external_environment_markers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "project"
    outside = tmp_path / "outside"
    _write(root, "requirements.txt", "-r alias/pins.txt\n")
    _write(outside, "pins.txt", "vllm==0.6.1\n")
    _write(outside, "pyvenv.cfg", "home = external\n")
    try:
        (root / "alias").symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlinks unavailable: {type(exc).__name__}")
    _git(root, "init")
    _git(root, "add", "--", ".")
    original_exists = Path.exists
    inspected: list[str] = []

    def guarded_exists(path: Path) -> bool:
        if path.name == "pyvenv.cfg" and path.parent.resolve() == outside.resolve():
            inspected.append(path.name)
            raise AssertionError("external marker inspected")
        return original_exists(path)

    monkeypatch.setattr(Path, "exists", guarded_exists)
    context = AuditContext(root)
    assert context.deps.declarations == []
    assert context.deps.unparsed == ["requirements.txt:1: include unreadable"]
    assert inspected == []
    assert context.fs.warnings == ["alias/pins.txt: path resolves outside project root; skipped"]


@pytest.mark.parametrize("git_mode", [False, True], ids=["walk", "git"])
def test_audit_and_init_cli_ignore_environment_code_and_task_inventory(
    tmp_path: Path, git_mode: bool
) -> None:
    _write(tmp_path, "train.py", "import openai\n")
    _write(tmp_path, "requirements.txt", "openai==1.50.0\n")
    _write(tmp_path, "tasks/business.yaml", "task: business\ndataset_path: demo/corpus\n")
    if git_mode:
        _git(tmp_path, "init")
        _git(tmp_path, "add", "--", ".")
    runner = CliRunner()
    before = runner.invoke(app, ["audit", str(tmp_path), "--format", "json"])
    assert before.exit_code in (0, 1), before.output
    expected_detection = json.loads(before.output)["profiles"]["detected"]
    expected_inventory = runner.invoke(app, ["init", str(tmp_path), "--list-tasks"])
    assert expected_inventory.exit_code == 0 and expected_inventory.output == "business\n"
    for index in range(501):
        _write(tmp_path, f".venv/lib/f{index:04}.py", "import vllm\nimport inspect_ai\n")
    _write(tmp_path, ".venv/tasks/canary.yaml", "task: environment_canary\n")
    _write(tmp_path, ".venv/README.md", "judge rubric differential privacy\n")
    if git_mode:
        _git(tmp_path, "add", "--", ".venv")
    after = runner.invoke(app, ["audit", str(tmp_path), "--format", "json"])
    assert after.exit_code in (0, 1), after.output
    assert json.loads(after.output)["profiles"]["detected"] == expected_detection
    inventory = runner.invoke(app, ["init", str(tmp_path), "--list-tasks"])
    assert inventory.exit_code == 0 and inventory.output == expected_inventory.output
    initialized = runner.invoke(app, ["init", str(tmp_path), "--task", "business"])
    assert initialized.exit_code == 0, initialized.output
    manifest = load_manifest(tmp_path / "reprollm.yaml")
    assert manifest.experiment.profiles == ["evaluation"]
    assert manifest.evaluation is not None
    assert [item.name for item in manifest.evaluation.metrics] == ["business"]
    assert manifest.inference is not None and manifest.inference.backend is None


def test_business_python_cap_and_text_limit_are_preserved(tmp_path: Path) -> None:
    for index in range(501):
        _write(tmp_path, f"research/f{index:04}.py", "import openai\n")
    _write(tmp_path, "oversize.py", "#" + "x" * (512 * 1024) + "\nimport vllm\n")
    context = AuditContext(tmp_path)
    assert len(context.fs.python_files()) == 500
    assert context.fs.python_files()[-1] == "research/f0498.py"
    assert context.fs.warnings == ["python file scan truncated to 500 of 502 files"]
    assert context.fs.read_text("oversize.py") is None
    assert len(context.pyscan.imports) == 499
    assert context.detection.hints.backends == []


@pytest.mark.parametrize("count", [1, 8])
def test_analysis_snapshot_canonicalizes_root_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, count: int
) -> None:
    for index in range(count):
        _write(tmp_path, f"business{index:02}.py", "import os\n")
    context = AuditContext(tmp_path)
    scanner = context.fs
    original_resolve = Path.resolve
    root_calls = 0

    def counted_resolve(path: Path, strict: bool = False) -> Path:
        nonlocal root_calls
        if path == tmp_path:
            root_calls += 1
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", counted_resolve)
    expected = [f"business{index:02}.py" for index in range(count)]
    assert scanner.analysis_files() == expected
    assert scanner.analysis_files() == scanner.python_files() == expected
    assert root_calls == 1
    root_calls = 0
    assert scanner.is_analysis_candidate("business00.py")
    assert scanner.is_analysis_candidate("business00.py")
    assert root_calls == 2
    root_calls = 0
    assert scanner.read_text("business00.py") == "import os\n"
    assert scanner.read_text("business00.py") == "import os\n"
    assert root_calls == 2


@pytest.mark.security
@pytest.mark.parametrize("error", [OSError, RuntimeError, ValueError])
def test_failed_candidate_root_capture_keeps_read_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: type[Exception]
) -> None:
    _write(tmp_path, "business.py", "import os\n")
    scanner = AuditContext(tmp_path).fs
    assert scanner.files() == ["business.py"]
    original_resolve = Path.resolve
    marker_calls = 0

    def fail_root(path: Path, strict: bool = False) -> Path:
        if path == tmp_path:
            raise error("SyntheticRootResolveCanary")
        return original_resolve(path, strict=strict)

    def fail_marker(path: Path, name: str) -> bool:
        nonlocal marker_calls
        marker_calls += 1
        raise AssertionError("An unresolved root must not permit marker inspection")

    monkeypatch.setattr(Path, "resolve", fail_root)
    monkeypatch.setattr(scanner, "_skip_dir", fail_marker)
    assert scanner.analysis_files() == ["business.py"]
    assert scanner.is_analysis_candidate("business.py")
    assert not scanner.is_analysis_candidate(".venv/business.py")
    assert not scanner.is_analysis_candidate(".reprollm/runs/business.py")
    assert marker_calls == 0
    assert scanner.read_text("business.py") is None
    assert scanner.warnings == ["business.py: cannot resolve path; skipped"]
    assert "SyntheticRootResolveCanary" not in "\n".join(scanner.warnings)


@pytest.mark.parametrize("mode", ["view", "explicit"])
def test_flat_candidates_do_not_repeat_path_normalization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    names = ["business.py", "with space.py", "数据.py", ".hidden.py", "many...dots.py"]
    for name in names:
        _write(tmp_path, name, "import os\n")
    scanner = AuditContext(tmp_path).fs
    assert scanner.files() == sorted(names)
    original_source_path = scanner_mod.content_source_path
    normalized: list[str] = []

    def count_normalization(raw: str) -> str | None:
        normalized.append(raw)
        return original_source_path(raw)

    monkeypatch.setattr(scanner_mod, "content_source_path", count_normalization)
    if mode == "view":
        assert scanner.analysis_files() == sorted(names)
    else:
        assert all(scanner.is_analysis_candidate(name) for name in names)
        assert scanner.is_analysis_candidate("...")
    assert normalized == []


@pytest.mark.security
@pytest.mark.parametrize(
    ("raw", "reason"),
    [
        ("C:relative.py", "absolute paths are not allowed"),
        ("C:bar/x", "absolute paths are not allowed"),
        (r"\\server\share\entry.py", "absolute paths are not allowed"),
        ("bad\x00path", "invalid path"),
        ("C:\x00payload", "absolute paths are not allowed"),
    ],
)
def test_candidate_resolver_keeps_public_lexical_rejection_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, raw: str, reason: str
) -> None:
    resolve_calls = 0

    def unexpected_resolve(path: Path, strict: bool = False) -> Path:
        nonlocal resolve_calls
        resolve_calls += 1
        raise AssertionError("Invalid lexical paths must be rejected before resolution")

    monkeypatch.setattr(Path, "resolve", unexpected_resolve)
    with pytest.raises(scanner_mod.ContentPathError) as public:
        scanner_mod.resolve_content_path(tmp_path, raw)
    assert str(public.value) == reason
    with pytest.raises(scanner_mod.ContentPathError) as candidate:
        scanner_mod.RepoScanner._resolve_analysis_path(tmp_path, raw)
    assert str(candidate.value) == reason
    assert resolve_calls == 0


@pytest.mark.security
def test_nonflat_explicit_candidates_keep_native_source_normalization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scanner = AuditContext(tmp_path).fs
    original_source_path = scanner_mod.content_source_path
    normalized: list[str] = []

    def count_normalization(raw: str) -> str | None:
        normalized.append(raw)
        return original_source_path(raw)

    monkeypatch.setattr(scanner_mod, "content_source_path", count_normalization)
    rejected = [
        "",
        ".",
        "..",
        "../outside",
        "C:relative.py",
        r"\\server\share\entry.py",
        "bad\x00path",
    ]
    accepted = [
        "normal//file.py",
        "normal/../file.py",
        "./normal/file.py",
        r"normal\file.py",
        "normal:file.py",
        "foo/C:bar/x",
    ]
    for raw in rejected:
        assert not scanner.is_analysis_candidate(raw), raw
    for raw in accepted:
        assert scanner.is_analysis_candidate(raw), raw
    assert normalized == rejected + accepted


@pytest.mark.parametrize("count", [1, 8])
def test_flat_regular_candidates_reuse_canonical_leaf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, count: int
) -> None:
    names = [f"business{index:02}.py" for index in range(count)]
    for name in names:
        _write(tmp_path, name, "import os\n")
    scanner = AuditContext(tmp_path).fs
    assert scanner.files() == names
    original_resolve = Path.resolve
    root_calls = 0
    leaf_calls: list[str] = []

    def counted_resolve(path: Path, strict: bool = False) -> Path:
        nonlocal root_calls
        if path == tmp_path:
            root_calls += 1
        elif path.parent == tmp_path and path.name in names:
            leaf_calls.append(path.name)
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", counted_resolve)
    assert scanner.analysis_files() == names
    assert root_calls == 1
    expected_view_calls = names if os.name == "nt" else []
    assert leaf_calls == expected_view_calls
    leaf_calls.clear()
    root_calls = 0
    assert scanner.is_analysis_candidate(names[0])
    assert scanner.is_analysis_candidate(names[0])
    assert root_calls == 2
    expected_explicit_calls = [names[0], names[0]] if os.name == "nt" else []
    assert leaf_calls == expected_explicit_calls


@pytest.mark.security
def test_flat_leaf_reparse_or_lstat_failure_uses_full_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, "business.py", "import os\n")
    scanner = AuditContext(tmp_path).fs
    leaf = tmp_path / "business.py"
    original_lstat = Path.lstat
    original_resolve = Path.resolve
    mode: int | type[Exception] = 0x400
    leaf_calls = 0
    lstat_calls = 0

    def guarded_lstat(path: Path) -> object:
        nonlocal lstat_calls
        if path != leaf:
            return original_lstat(path)
        lstat_calls += 1
        if isinstance(mode, type):
            raise mode("SyntheticLeafMetadataCanary")
        result = original_lstat(path)
        return SimpleNamespace(st_mode=result.st_mode, st_file_attributes=mode)

    def counted_resolve(path: Path, strict: bool = False) -> Path:
        nonlocal leaf_calls
        if path == leaf:
            leaf_calls += 1
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "lstat", guarded_lstat)
    monkeypatch.setattr(Path, "resolve", counted_resolve)
    for case in [0x400, PermissionError, RuntimeError, ValueError]:
        mode = case
        leaf_calls = 0
        lstat_calls = 0
        assert scanner.is_analysis_candidate("business.py")
        assert leaf_calls == 1
        assert lstat_calls == (0 if os.name == "nt" else 1)
    mode = 0
    leaf_calls = 0
    lstat_calls = 0
    assert scanner.is_analysis_candidate("business.py")
    assert leaf_calls == (1 if os.name == "nt" else 0)
    assert lstat_calls == (0 if os.name == "nt" else 1)


@pytest.mark.security
def test_candidate_leaf_snapshot_keeps_retargeted_cached_reads_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "project"
    leaf = root / "business.py"
    outside = tmp_path / "outside.py"
    _write(root, "business.py", "import os\n")
    outside.write_bytes(b"import vllm\n")
    probe = root / "symlink-probe"
    try:
        probe.symlink_to(outside)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlinks unavailable: {type(exc).__name__}")
    probe.unlink()
    scanner = AuditContext(root).fs
    assert scanner.files() == ["business.py"]
    assert scanner.read_text("business.py") == "import os\n"
    original_lstat = Path.lstat
    original_open = Path.open
    retargeted = False
    external_opens = 0

    def retarget_after_lstat(path: Path) -> object:
        nonlocal retargeted
        result = original_lstat(path)
        if path == leaf and not retargeted:
            leaf.unlink()
            leaf.symlink_to(outside)
            retargeted = True
        return result

    def guarded_open(path: Path, *args: object, **kwargs: object) -> object:
        nonlocal external_opens
        if path == outside:
            external_opens += 1
            raise AssertionError("External contents must not be opened")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", retarget_after_lstat)
    monkeypatch.setattr(Path, "open", guarded_open)
    assert scanner.analysis_files() == ["business.py"]
    if os.name == "nt":
        assert not retargeted
        leaf.unlink()
        leaf.symlink_to(outside)
    else:
        assert retargeted
    assert scanner.read_text("business.py") is None
    assert scanner.warnings == ["business.py: path resolves outside project root; skipped"]
    assert external_opens == 0
