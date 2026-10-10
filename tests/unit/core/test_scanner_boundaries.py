"""Public static content boundaries (R06-G, spec §§13/20)."""

import os
from importlib.resources import files
from pathlib import Path
from typing import IO, Any

import pytest

from reprollm.cli.main import cli
from reprollm.core import proc
from reprollm.core.context import AuditContext
from reprollm.core.deps import scan_dependencies
from reprollm.core.errors import UserError
from reprollm.core.git import GitInfo, inspect_git
from reprollm.core.pyscan import scan_python
from reprollm.core.scanner import MAX_READ_BYTES, RepoScanner
from reprollm.discover.collector import collect
from reprollm.integrations._static import cli_evidence, task_mapping
from reprollm.profiles import loader
from reprollm.profiles.detect import run_detection
from reprollm.rules.env import SecretFilesIgnoredRule
from reprollm.schemas.config import DiscoverConfig
from reprollm.schemas.finding import Severity

pytestmark = pytest.mark.security


def _symlink(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=target.is_dir())
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlinks unavailable: {type(exc).__name__}")


def test_external_requirements_is_never_opened(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    sentinel = tmp_path / "sentinel.txt"
    sentinel.write_bytes(b"outside-canary==1.2.3\n")
    _symlink(repo / "requirements.txt", sentinel)
    opened: list[str] = []
    original_open = Path.open

    def spy_open(path: Path, *args: Any, **kwargs: Any) -> IO[Any]:
        if path.resolve() == sentinel:
            opened.append("sentinel")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", spy_open)
    scanner = RepoScanner(repo, GitInfo(is_repo=False))
    assert scanner.read_text("requirements.txt") is None
    assert opened == []
    with original_open(sentinel, "rb") as stream:
        assert stream.read() == b"outside-canary==1.2.3\n"


@pytest.mark.parametrize("external", [True, False], ids=["outside", "inside"])
def test_cached_alias_is_revalidated_after_retarget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, external: bool
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    initial = repo / "initial.txt"
    initial.write_text("initial internal content\n")
    replacement = (tmp_path if external else repo) / "replacement.txt"
    replacement.write_text("replacement content\n")
    alias = repo / "alias.txt"
    _symlink(alias, initial)
    scanner = RepoScanner(repo, GitInfo(is_repo=False))
    assert scanner.read_text("alias.txt") == "initial internal content\n"
    alias.unlink()
    _symlink(alias, replacement)
    opened: list[str] = []
    original_open = Path.open

    def spy_open(path: Path, *args: Any, **kwargs: Any) -> IO[Any]:
        if path.resolve() == replacement and external:
            opened.append("outside")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", spy_open)
    expected = None if external else "replacement content\n"
    assert scanner.read_text("alias.txt") == expected
    assert scanner.read_text("alias.txt") == expected
    assert opened == []


@pytest.mark.parametrize("directory_link", [False, True], ids=["file", "directory"])
def test_user_profile_external_target_is_never_opened(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, directory_link: bool
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside-profiles"
    outside.mkdir()
    sentinel = outside / "custom.yaml"
    sentinel.write_text("schema_version: 1\nname: custom\ndescription: outside profile canary\n")
    user_profiles = repo / ".reprollm" / "profiles"
    user_profiles.parent.mkdir()
    if directory_link:
        _symlink(user_profiles, outside)
    else:
        user_profiles.mkdir()
        _symlink(user_profiles / "custom.yaml", sentinel)
    opened: list[str] = []
    original_open = Path.open

    def spy_open(path: Path, *args: Any, **kwargs: Any) -> IO[Any]:
        if path.resolve() == sentinel:
            opened.append("sentinel")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", spy_open)
    with pytest.raises(UserError, match="outside project root") as error:
        loader.load_profile(repo, "custom")
    assert opened == []
    assert str(tmp_path) not in str(error.value)
    assert "outside profile canary" not in str(error.value)


@pytest.mark.parametrize("absolute", [False, True], ids=["relative", "absolute"])
def test_external_include_diagnostic_uses_including_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, absolute: bool
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    sentinel = tmp_path / "outside-requirements.txt"
    sentinel.write_text("outside-canary==1.2.3\n")
    reference = str(sentinel) if absolute else "../outside-requirements.txt"
    (repo / "requirements.txt").write_text(f"-r {reference}\n")
    opened: list[str] = []
    original_open = Path.open

    def spy_open(path: Path, *args: Any, **kwargs: Any) -> IO[Any]:
        if path.resolve() == sentinel:
            opened.append("sentinel")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", spy_open)
    scanner = RepoScanner(repo, GitInfo(is_repo=False))
    result = scan_dependencies(scanner)
    assert result.declarations == []
    assert opened == []
    assert result.unparsed == ["requirements.txt:1: include unreadable"]
    assert str(tmp_path) not in "\n".join(scanner.warnings)
    assert "outside-requirements.txt" not in "\n".join(scanner.warnings)


def test_permission_failure_has_safe_stable_diagnostic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "settings.yaml"
    target.write_text("batch_size: 2\n")
    original_open = Path.open

    def denied_open(path: Path, *args: Any, **kwargs: Any) -> IO[Any]:
        if path == target:
            raise PermissionError(f"synthetic machine path {tmp_path}")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", denied_open)
    scanner = RepoScanner(tmp_path, GitInfo(is_repo=False))
    assert scanner.read_text("settings.yaml") is None
    assert scanner.read_text("settings.yaml", max_bytes=64) is None
    assert scanner.warnings == ["settings.yaml: cannot read file; skipped"]


def test_text_read_remains_bounded_when_file_grows_after_stat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "settings.yaml"
    target.write_bytes(b"a: 1")
    original_open = Path.open
    replaced = False

    def grow_before_open(path: Path, *args: Any, **kwargs: Any) -> IO[Any]:
        nonlocal replaced
        if path == target and not replaced:
            replaced = True
            with original_open(path, "wb") as stream:
                stream.write(b"a: 12345")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", grow_before_open)
    scanner = RepoScanner(tmp_path, GitInfo(is_repo=False))
    assert scanner.read_text("settings.yaml", max_bytes=4) is None
    assert replaced


@pytest.mark.parametrize("kind", ["missing", "broken", "loop", "directory"])
def test_unavailable_content_has_stable_relative_diagnostic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    path = "entry.txt"
    if kind == "broken":
        _symlink(tmp_path / path, tmp_path / "missing.txt")
    elif kind == "loop":
        _symlink(tmp_path / path, tmp_path / "other.txt")
        _symlink(tmp_path / "other.txt", tmp_path / path)
    elif kind == "directory":
        (tmp_path / path).mkdir()
    opened: list[str] = []
    original_open = Path.open

    def spy_open(target: Path, *args: Any, **kwargs: Any) -> IO[Any]:
        opened.append("content")
        return original_open(target, *args, **kwargs)

    monkeypatch.setattr(Path, "open", spy_open)
    scanner = RepoScanner(tmp_path, GitInfo(is_repo=False))
    assert scanner.read_text(path) is None
    assert scanner.read_text(path, max_bytes=64) is None
    reason = "cannot resolve path" if kind == "loop" else "not a regular file"
    assert scanner.warnings == [f"entry.txt: {reason}; skipped"]
    assert opened == []


@pytest.mark.parametrize("data", [b"a: 1\r\nb: 2\r\n", b"a: 1\rb: 2\r"])
def test_internal_text_keeps_universal_newline_behavior(tmp_path: Path, data: bytes) -> None:
    (tmp_path / "settings.yaml").write_bytes(data)
    scanner = RepoScanner(tmp_path, GitInfo(is_repo=False))
    assert scanner.read_text("settings.yaml") == "a: 1\nb: 2\n"


@pytest.mark.parametrize("use_git", [False, True], ids=["walk", "git"])
def test_all_static_consumers_skip_external_content_and_keep_file_facts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, use_git: bool
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    contents = {
        "requirements.txt": "outside-canary==1.2.3\n",
        "linked.py": (
            "import vllm\nModel.from_pretrained('outside/model-canary', trust_remote_code=True)\n"
            "parser.add_argument('--outside-canary')\n"
        ),
        "README.md": "judge rubric differential privacy\n",
        "settings.yaml": "judge: rubric\n",
        "sample.yaml": "task: outside_canary\ndataset_path: outside/dataset\n",
        "launch.sh": "lm-eval --tasks outside_canary\n",
        ".env.local": "OUTSIDE_CANARY=synthetic_value\n",
    }
    for name, text in contents.items():
        sentinel = outside / name
        sentinel.write_text(text)
        _symlink(repo / name, sentinel)
    (repo / "local.txt").write_text("local content\n")
    if use_git:
        for args in (["init"], ["add", "--", *contents]):
            result = proc.run_cmd(["git", *args], cwd=repo)
            assert result.returncode == 0, result.stderr
    git = inspect_git(repo)
    assert git.is_repo is use_git
    if use_git:
        assert ".env.local" in git.modified
        assert git.untracked == ["local.txt"]
    opened: list[str] = []
    original_open = Path.open
    sentinels = {outside / name for name in contents}

    def spy_open(path: Path, *args: Any, **kwargs: Any) -> IO[Any]:
        if path.resolve() in sentinels:
            opened.append(path.name)
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", spy_open)
    scanner = RepoScanner(repo, git)
    assert set(contents) <= set(scanner.files())
    assert scanner.exists("requirements.txt")
    dependencies = scan_dependencies(scanner)
    assert dependencies.manifest_present
    assert dependencies.declarations == []
    assert dependencies.lockfiles == []
    python = scan_python(scanner)
    assert python.imports == []
    assert python.hf_ids == []
    detection = run_detection(scanner, python, dependencies)
    assert detection.profiles == []
    assert detection.hints.providers == []
    assert detection.hints.backends == []
    assert detection.hints.hf_ids == []
    assert not detection.hints.trust_remote_code
    assert task_mapping(scanner, "sample.yaml") is None
    assert cli_evidence(scanner, (("lm-eval",),)) == []
    payload = collect(repo, scanner, DiscoverConfig())
    assert payload.files == []
    assert payload.tree == ["local.txt"]
    findings = SecretFilesIgnoredRule().check(AuditContext(repo))
    assert len(findings) == 1
    assert findings[0].severity == (Severity.CRITICAL if use_git else Severity.WARNING)
    assert [item.path for item in findings[0].evidence] == [".env.local"]
    assert opened == []
    for name, text in contents.items():
        with original_open(outside / name, "rb") as stream:
            assert stream.read() == text.encode()
    diagnostics = "\n".join(scanner.warnings + python.warnings + dependencies.unparsed)
    assert str(tmp_path) not in diagnostics
    assert "outside-canary" not in diagnostics
    assert "outside/model-canary" not in payload.render()


@pytest.mark.parametrize("max_bytes", [MAX_READ_BYTES, 64])
@pytest.mark.parametrize("reference", ["absolute", "relative", "symlink", "windows-drive", "unc"])
def test_direct_unsafe_paths_cannot_bypass_explicit_limit_or_repeated_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reference: str, max_bytes: int
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    sentinel = tmp_path / "outside.txt"
    sentinel.write_bytes(b"outside canary\n")
    if reference == "absolute":
        path = str(sentinel)
    elif reference == "relative":
        path = "../outside.txt"
    elif reference == "symlink":
        path = "alias.txt"
        _symlink(repo / path, sentinel)
    elif reference == "windows-drive":
        path = "C:\\outside\\sentinel.txt"
    else:
        path = "\\\\server\\outside\\sentinel.txt"
    opened: list[str] = []
    original_open = Path.open

    def spy_open(target: Path, *args: Any, **kwargs: Any) -> IO[Any]:
        opened.append("content")
        return original_open(target, *args, **kwargs)

    monkeypatch.setattr(Path, "open", spy_open)
    scanner = RepoScanner(repo, GitInfo(is_repo=False))
    assert scanner.read_text(path, max_bytes=max_bytes) is None
    assert scanner.read_text(path, max_bytes=max_bytes) is None
    assert opened == []
    assert len(scanner.warnings) == 1
    warning = scanner.warnings[0]
    assert str(tmp_path) not in warning
    assert "outside.txt" not in warning
    assert "sentinel.txt" not in warning


def test_internal_alias_and_normalized_parent_path_keep_relative_evidence(tmp_path: Path) -> None:
    (tmp_path / "sources").mkdir()
    source = tmp_path / "sources" / "source.txt"
    source.write_text(
        "import vllm\nModel.from_pretrained('inside/model', trust_remote_code=True)\n"
    )
    _symlink(tmp_path / "linked.py", source)
    scanner = RepoScanner(tmp_path, GitInfo(is_repo=False))
    assert scanner.read_text("sources/../linked.py") == source.read_text()
    assert scanner.read_text("linked.py", max_bytes=256) == source.read_text()
    result = scan_python(scanner)
    assert [(item.module, item.path, item.line) for item in result.imports] == [
        ("vllm", "linked.py", 1)
    ]
    assert [(item.value, item.path, item.line) for item in result.hf_ids] == [
        ("inside/model", "linked.py", 2)
    ]
    assert result.trust_remote_code
    assert scanner.warnings == []


def test_binary_size_and_cache_limits_are_preserved(tmp_path: Path) -> None:
    target = tmp_path / "text.txt"
    target.write_bytes(b"abc")
    scanner = RepoScanner(tmp_path, GitInfo(is_repo=False))
    assert scanner.read_text("text.txt") == "abc"
    assert scanner.read_text("text.txt", max_bytes=2) is None
    assert scanner.read_text("text.txt", max_bytes=3) == "abc"
    target.write_bytes(b"a" * (MAX_READ_BYTES + 1))
    assert scanner.read_text("text.txt") is None
    for name, data in (("nul.bin", b"a\x00b"), ("invalid.txt", b"\xff")):
        (tmp_path / name).write_bytes(data)
        assert scanner.read_text(name) is None
    target.write_bytes(b"")
    assert scanner.read_text("text.txt", max_bytes=0) == ""


def test_user_profile_internal_directory_alias_is_allowed(tmp_path: Path) -> None:
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    (profiles / "custom.yaml").write_text("name: custom\ndescription: local profile\n")
    (tmp_path / ".reprollm").mkdir()
    _symlink(tmp_path / ".reprollm" / "profiles", profiles)
    assert loader.load_profile(tmp_path, "custom").description == "local profile"


@pytest.mark.parametrize(
    "consumer", ["dependencies", "python", "readme", "config", "task", "shell"]
)
def test_each_static_consumer_never_opens_external_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, consumer: str
) -> None:
    cases = {
        "dependencies": ("requirements.txt", "outside-canary==1.2.3\n"),
        "python": ("linked.py", "import vllm\nModel.from_pretrained('outside/model')\n"),
        "readme": ("README.md", "judge rubric\n"),
        "config": ("settings.yaml", "judge: rubric\n"),
        "task": ("sample.yaml", "task: outside_canary\ndataset_path: outside/dataset\n"),
        "shell": ("launch.sh", "lm-eval --tasks outside_canary\n"),
    }
    name, content = cases[consumer]
    repo = tmp_path / "repo"
    repo.mkdir()
    sentinel = tmp_path / "sentinel"
    sentinel.write_text(content)
    _symlink(repo / name, sentinel)
    opened: list[str] = []
    original_open = Path.open

    def spy_open(path: Path, *args: Any, **kwargs: Any) -> IO[Any]:
        if path.resolve() == sentinel:
            opened.append("sentinel")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", spy_open)
    scanner = RepoScanner(repo, GitInfo(is_repo=False))
    if consumer == "dependencies":
        result = scan_dependencies(scanner)
        assert opened == []
        assert result.declarations == []
    elif consumer == "python":
        python = scan_python(scanner)
        assert opened == []
        assert python.imports == []
        assert python.hf_ids == []
    elif consumer in {"readme", "config"}:
        detection = run_detection(scanner, scan_python(scanner), scan_dependencies(scanner))
        assert opened == []
        assert detection.profiles == []
    elif consumer == "task":
        task = task_mapping(scanner, name)
        assert opened == []
        assert task is None
    else:
        evidence = cli_evidence(scanner, (("lm-eval",),))
        assert opened == []
        assert evidence == []


@pytest.mark.parametrize("max_bytes", [MAX_READ_BYTES, 64])
def test_invalid_path_is_unreadable_without_unsafe_diagnostics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, max_bytes: int
) -> None:
    opened: list[str] = []
    original_open = Path.open

    def spy_open(path: Path, *args: Any, **kwargs: Any) -> IO[Any]:
        opened.append("content")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", spy_open)
    scanner = RepoScanner(tmp_path, GitInfo(is_repo=False))
    assert scanner.read_text("bad\x00path.txt", max_bytes=max_bytes) is None
    assert scanner.warnings == ["repository content: invalid path; skipped"]
    assert opened == []


@pytest.mark.parametrize("entry", ["builtin", "inheritance", "cli"])
def test_profile_name_cannot_escape_packaged_resource_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    entry: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    sentinel = tmp_path / "foreign.yaml"
    sentinel.write_text("name: foreign\ndescription: outside profile canary\n")
    package = tmp_path / "package" / "profiles"
    package.mkdir(parents=True)
    resource_root = files("reprollm.profiles")
    for name in loader.builtin_profile_names():
        (package / f"{name}.yaml").write_text(
            str((resource_root / f"{name}.yaml").read_text(encoding="utf-8"))
        )
    monkeypatch.setattr(loader, "files", lambda package_name: package)
    traversal = os.path.relpath(sentinel.with_suffix(""), package).replace(os.sep, "/")
    repo = tmp_path / "repo"
    repo.mkdir()
    profiles = repo / ".reprollm" / "profiles"
    profiles.mkdir(parents=True)
    (profiles / "custom.yaml").write_text(
        f"name: custom\ndescription: local profile\nextends: ['{traversal}']\n"
    )
    opened: list[str] = []
    original_open = Path.open

    def spy_open(path: Path, *args: Any, **kwargs: Any) -> IO[Any]:
        if path.resolve() == sentinel:
            opened.append("sentinel")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", spy_open)
    if entry == "cli":
        monkeypatch.chdir(repo)
        monkeypatch.setattr("sys.argv", ["reprollm", "profiles", "show", "custom"])
        with pytest.raises(SystemExit) as exit_info:
            cli()
        assert exit_info.value.code == 2
        diagnostic = capsys.readouterr().err
    else:
        with pytest.raises(UserError, match="invalid profile name") as error:
            if entry == "builtin":
                loader.load_builtin(traversal)
            else:
                loader.resolve(["custom"], repo)
        diagnostic = str(error.value)
    assert opened == []
    assert str(tmp_path) not in diagnostic
    assert traversal not in diagnostic
    assert "outside profile canary" not in diagnostic


def test_valid_custom_inheritance_still_resolves_builtin_parent(tmp_path: Path) -> None:
    profiles = tmp_path / ".reprollm" / "profiles"
    profiles.mkdir(parents=True)
    (profiles / "custom.yaml").write_text(
        "name: custom\ndescription: local profile\nextends: [inference]\n"
    )
    assert loader.resolve(["custom"], tmp_path).names == ["core", "inference", "custom"]
