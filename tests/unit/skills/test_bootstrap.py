"""Installation lifecycle preserves existing environments and validates every input."""

from __future__ import annotations

import hashlib
import io
import json
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[3] / "skills/reprollm/scripts"
sys.path.insert(0, str(SCRIPTS))
import bootstrap  # noqa: E402
from install_catalog import Candidate, Catalog  # noqa: E402


def source_blob(name: str = "repo/src/reprollm/__init__.py", kind: str = "file") -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        info = tarfile.TarInfo(name)
        data = b'__version__ = "0.7.0"\n'
        info.size = len(data)
        if kind == "symlink":
            info.type = tarfile.SYMTYPE
            info.linkname = "/tmp/escape"
            info.size = 0
        archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def candidate(identifier: str, blob: bytes) -> Candidate:
    return Candidate(
        identifier,
        "0.7.0",
        "a" * 40,
        "https://codeload.github.com/EnumaElish123/ReproLLM/tar.gz/" + "a" * 40,
        hashlib.sha256(blob).hexdigest(),
        "reprollm-0.7.0-py3-none-any.whl",
        (3, 10),
        (3, 12),
        ("linux", "darwin", "win32"),
        ("audit",),
        (),
        (),
    )


class FakeBackend:
    def __init__(self, blob: bytes):
        self.blob = blob
        self.fetches = 0
        self.installs = 0
        self.fail_install = False

    def fetch(self, url: str) -> bytes:
        self.fetches += 1
        return self.blob

    def create_venv(self, path: Path) -> None:
        (path / "bin").mkdir(parents=True)
        (path / "bin/python").write_text("interpreter")

    def build(
        self, source: Path, environment: Path, wheelhouse: Path, output: Path, selected: Candidate
    ) -> Path:
        output.mkdir(parents=True, exist_ok=True)
        wheel = output / selected.wheel_filename
        with zipfile.ZipFile(wheel, "w") as archive:
            archive.writestr(
                "reprollm/__init__.py", (source / "src/reprollm/__init__.py").read_bytes()
            )
            archive.writestr(
                "reprollm-0.7.0.dist-info/METADATA", "Name: reprollm\nVersion: 0.7.0\n"
            )
        return wheel

    def install(self, environment: Path, wheelhouse: Path, requirements: tuple[str, ...]) -> None:
        self.installs += 1
        if self.fail_install:
            raise bootstrap.BootstrapError(
                "Installation failed; keep the existing tool environment."
            )
        (environment / "installed.txt").write_text("installed")

    def probe(self, environment: Path, selected: Candidate) -> dict[str, str]:
        if not (environment / "installed.txt").is_file():
            raise bootstrap.BootstrapError("Installation probe failed.")
        return {"reprollm/__init__.py": hashlib.sha256(b'__version__ = "0.7.0"\n').hexdigest()}


@pytest.fixture
def setup(tmp_path: Path) -> tuple[bootstrap.Bootstrap, FakeBackend, Candidate, Candidate]:
    blob = source_blob()
    first, second = candidate("first", blob), candidate("second", blob)
    catalog = Catalog(1, "first", (first, second))
    backend = FakeBackend(blob)
    manager = bootstrap.Bootstrap(tmp_path / "tool", catalog, backend=backend)
    return manager, backend, first, second


def test_status_is_read_only(
    setup: tuple[bootstrap.Bootstrap, FakeBackend, Candidate, Candidate],
) -> None:
    manager, backend, _, _ = setup
    assert manager.status()["state"] == "NOT_INSTALLED"
    assert not manager.home.exists()
    assert backend.fetches == backend.installs == 0


def test_install_reuse_and_no_machine_paths(
    setup: tuple[bootstrap.Bootstrap, FakeBackend, Candidate, Candidate],
) -> None:
    manager, backend, _, _ = setup
    first = manager.ensure()
    assert first["state"] == "READY"
    assert manager.ensure() == first
    assert backend.fetches == backend.installs == 1
    for path in manager.home.rglob("*.json"):
        assert str(manager.home.parent) not in path.read_text()
    assert manager.status() == first


def test_explicit_update_rollback_preserve_old_environment(
    setup: tuple[bootstrap.Bootstrap, FakeBackend, Candidate, Candidate],
) -> None:
    manager, backend, _, _ = setup
    first = manager.ensure()
    second = manager.update("second")
    assert second["candidate_id"] == "second"
    assert first["environment"] != second["environment"]
    assert manager.environment_path(str(first["environment"])).is_dir()
    assert manager.rollback()["environment"] == first["environment"]
    assert backend.installs == 2


def test_ensure_does_not_silently_upgrade(
    setup: tuple[bootstrap.Bootstrap, FakeBackend, Candidate, Candidate],
) -> None:
    manager, _, _, _ = setup
    first = manager.ensure()
    with pytest.raises(bootstrap.BootstrapError, match="update"):
        manager.ensure("second")
    assert manager.status() == first


def test_failed_update_keeps_active_environment(
    setup: tuple[bootstrap.Bootstrap, FakeBackend, Candidate, Candidate],
) -> None:
    manager, backend, _, _ = setup
    first = manager.ensure()
    backend.fail_install = True
    with pytest.raises(bootstrap.BootstrapError):
        manager.update("second")
    assert manager.status() == first


def test_cached_source_hash_rechecked(
    setup: tuple[bootstrap.Bootstrap, FakeBackend, Candidate, Candidate],
) -> None:
    manager, _, first, _ = setup
    manager.ensure()
    (manager.home / "cache/blobs" / first.source_sha256).write_bytes(b"tampered")
    with pytest.raises(bootstrap.BootstrapError):
        manager.update("second")
    assert manager.status()["candidate_id"] == "first"


def test_offline_cache_and_missing_source(
    setup: tuple[bootstrap.Bootstrap, FakeBackend, Candidate, Candidate], tmp_path: Path
) -> None:
    manager, backend, first, _ = setup
    house = tmp_path / "wheelhouse"
    house.mkdir()
    with pytest.raises(bootstrap.BootstrapError, match="offline"):
        manager.ensure(wheelhouse=house, offline=True)
    assert backend.fetches == 0
    (house / (first.source_sha256 + ".tar.gz")).write_bytes(backend.blob)
    assert manager.ensure(wheelhouse=house, offline=True)["state"] == "READY"
    assert backend.fetches == 0


@pytest.mark.parametrize(
    "member,kind",
    [
        ("../escape", "file"),
        ("/escape", "file"),
        ("repo/../../escape", "file"),
        ("repo/a", "symlink"),
        ("repo\\escape", "file"),
    ],
)
def test_unsafe_archive_rejected(tmp_path: Path, member: str, kind: str) -> None:
    with pytest.raises(bootstrap.BootstrapError):
        bootstrap.extract_source(source_blob(member, kind), tmp_path / "extract")
    assert not (tmp_path / "escape").exists()


def test_archive_expansion_budget(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bootstrap, "MAX_EXPANDED_BYTES", 1)
    with pytest.raises(bootstrap.BootstrapError):
        bootstrap.extract_source(source_blob(), tmp_path / "extract")


def test_home_with_unrelated_contents_is_preserved(
    setup: tuple[bootstrap.Bootstrap, FakeBackend, Candidate, Candidate],
) -> None:
    manager, _, _, _ = setup
    manager.home.mkdir()
    private = manager.home / "user-file"
    private.write_text("keep")
    with pytest.raises(bootstrap.BootstrapError):
        manager.ensure()
    assert private.read_text() == "keep"


def test_symlink_home_rejected(
    setup: tuple[bootstrap.Bootstrap, FakeBackend, Candidate, Candidate], tmp_path: Path
) -> None:
    manager, _, _, _ = setup
    target = tmp_path / "unrelated"
    target.mkdir()
    try:
        manager.home.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("Symlinks unavailable on this platform")
    with pytest.raises(bootstrap.BootstrapError):
        manager.ensure()
    assert not list(target.iterdir())


def test_foreign_active_pointer_rejected(
    setup: tuple[bootstrap.Bootstrap, FakeBackend, Candidate, Candidate],
) -> None:
    manager, _, _, _ = setup
    manager.ensure()
    path = manager.home / "active.json"
    value = json.loads(path.read_text())
    value["active"] = "../../unrelated"
    path.write_text(json.dumps(value))
    with pytest.raises(bootstrap.BootstrapError):
        manager.status()


def test_lease_prevents_uninstall_deletion(
    setup: tuple[bootstrap.Bootstrap, FakeBackend, Candidate, Candidate],
) -> None:
    manager, _, _, _ = setup
    result = manager.ensure()
    env = manager.environment_path(str(result["environment"]))
    (env / "leases").mkdir()
    (env / "leases/live.json").write_text('{"schema_version":1}')
    assert manager.uninstall()["state"] == "NOT_INSTALLED"
    assert env.exists()
    assert manager.status()["state"] == "NOT_INSTALLED"


def test_uninstall_only_deletes_owned_environments(
    setup: tuple[bootstrap.Bootstrap, FakeBackend, Candidate, Candidate],
) -> None:
    manager, _, _, _ = setup
    manager.ensure()
    unrelated = manager.home / "environments/unrelated"
    unrelated.mkdir()
    (unrelated / "keep").write_text("keep")
    manager.uninstall()
    assert (unrelated / "keep").read_text() == "keep"
    assert manager.home.joinpath("cache").exists()


def test_lock_timeout_is_actionable(
    setup: tuple[bootstrap.Bootstrap, FakeBackend, Candidate, Candidate],
) -> None:
    manager, _, _, _ = setup
    manager.ensure()
    (manager.home / ".install-lock").mkdir()
    with pytest.raises(bootstrap.BootstrapError, match="installation"):
        manager.ensure(lock_timeout=0)


def test_probe_failure_does_not_claim_ready(
    setup: tuple[bootstrap.Bootstrap, FakeBackend, Candidate, Candidate],
) -> None:
    manager, _, _, _ = setup
    result = manager.ensure()
    manager.environment_path(str(result["environment"])).joinpath("installed.txt").unlink()
    with pytest.raises(bootstrap.BootstrapError):
        manager.status()


def test_network_error_is_private(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(bootstrap.os.environ):
        if key.lower().endswith("_proxy"):
            monkeypatch.delenv(key)

    def fail(*args: object, **kwargs: object) -> object:
        raise OSError("secret proxy credentials")

    monkeypatch.setattr(bootstrap.urllib.request, "urlopen", fail)
    backend = bootstrap.SystemBackend()
    with pytest.raises(bootstrap.BootstrapError) as error:
        backend.fetch("https://invalid.invalid/")
    assert "https://" not in str(error.value)


def test_first_install_is_serialized(
    setup: tuple[bootstrap.Bootstrap, FakeBackend, Candidate, Candidate],
) -> None:
    from concurrent.futures import ThreadPoolExecutor

    manager, backend, _, _ = setup
    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(lambda _: manager.ensure(), [0, 1]))
    assert first == second
    assert backend.fetches == backend.installs == 1


def test_true_schema_version_is_rejected(
    setup: tuple[bootstrap.Bootstrap, FakeBackend, Candidate, Candidate],
) -> None:
    manager, _, _, _ = setup
    manager.ensure()
    path = manager.home / "active.json"
    state = json.loads(path.read_text())
    state["schema_version"] = True
    path.write_text(json.dumps(state))
    with pytest.raises(bootstrap.BootstrapError):
        manager.status()


def test_probe_binds_expected_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    backend = bootstrap.SystemBackend()
    entry = (
        tmp_path
        / "tool-env"
        / ("Scripts/reprollm.exe" if bootstrap.os.name == "nt" else "bin/reprollm")
    )
    entry.parent.mkdir(parents=True)
    entry.write_text("entry")
    entry.chmod(0o700)
    calls: list[list[str]] = []

    def invoke(argv: list[str], *, cwd: Path | None = None) -> str:
        calls.append(argv)
        return json.dumps({"reprollm/__init__.py": "a" * 64})

    monkeypatch.setattr(backend, "_run", invoke)
    backend.probe(tmp_path / "tool-env", candidate("probe", source_blob()))
    assert calls[0][-1] == str(tmp_path / "tool-env")
    assert "assert root == pathlib.Path(sys.argv[2]).resolve()" in calls[0][-3]
    assert calls[0][1] == "-I"


@pytest.mark.parametrize("code,raw", [(0, b"archive"), (7, b"proxy-secret"), (0, b"x" * 30)])
def test_socks_uses_system_curl_without_exposing_output(
    monkeypatch: pytest.MonkeyPatch, code: int, raw: bytes
) -> None:
    import subprocess

    calls: list[list[str]] = []
    monkeypatch.setenv("ALL_PROXY", "socks5h://secret:password@proxy.invalid:1080")
    monkeypatch.setattr(bootstrap, "system_curl", lambda: "/usr/bin/curl")
    monkeypatch.setattr(bootstrap, "MAX_DOWNLOAD_BYTES", 20)

    def invoke(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        calls.append(argv)
        assert kwargs["stderr"] == subprocess.DEVNULL
        return subprocess.CompletedProcess(argv, code, raw, b"")

    monkeypatch.setattr(bootstrap.subprocess, "run", invoke)
    backend = bootstrap.SystemBackend()
    if code == 0 and len(raw) <= 20:
        assert backend.fetch("https://files.pythonhosted.org/pinned") == raw
    else:
        with pytest.raises(bootstrap.BootstrapError) as error:
            backend.fetch("https://files.pythonhosted.org/pinned")
        assert "proxy-secret" not in str(error.value)
        assert "password" not in str(error.value)
    assert calls[0][1] == "--disable"
    assert calls[0][calls[0].index("--proto") + 1] == "=https"
    assert calls[0][calls[0].index("--proto-redir") + 1] == "=https"
    assert calls[0][calls[0].index("--retry") + 1] == "0"
    assert "password" not in " ".join(calls[0])


def test_socks_does_not_execute_project_curl(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALL_PROXY", "socks5://proxy.invalid:1080")
    monkeypatch.setattr(bootstrap.shutil, "which", lambda _: "/untrusted/project/curl")
    monkeypatch.setattr(bootstrap, "system_curl", lambda: None)
    with pytest.raises(bootstrap.BootstrapError, match="offline wheelhouse"):
        bootstrap.SystemBackend().fetch("https://files.pythonhosted.org/pinned")


def test_current_catalog_platform_wheel_selection() -> None:
    from install_catalog import load_catalog

    selected = load_catalog(SCRIPTS.parent / "assets/install-catalog.json").get_candidate()
    runtime = bootstrap.compatible_artifacts(selected.runtime_artifacts)
    build = bootstrap.compatible_artifacts(selected.build_artifacts)
    assert len(runtime) == len({item.name for item in selected.runtime_artifacts})
    assert len(build) == len({item.name for item in selected.build_artifacts})
    assert len({item.name for item in runtime}) == len(runtime)
    assert all(item in selected.runtime_artifacts for item in runtime)


@pytest.mark.parametrize("relative", ["installed.txt", "bin/python", "new-code.pth"])
def test_tampered_environment_is_rejected_before_probe(
    setup: tuple[bootstrap.Bootstrap, FakeBackend, Candidate, Candidate],
    monkeypatch: pytest.MonkeyPatch,
    relative: str,
) -> None:
    manager, backend, _, _ = setup
    result = manager.ensure()
    environment = manager.environment_path(str(result["environment"]))
    (environment / relative).write_text("tampered-code")
    probes: list[bool] = []

    def forbidden(*args: object) -> dict[str, str]:
        probes.append(True)
        raise AssertionError("Tampered installed code must never execute")

    monkeypatch.setattr(backend, "probe", forbidden)
    with pytest.raises(bootstrap.BootstrapError, match="changed"):
        manager.status()
    assert not probes


def test_explicit_update_repairs_corrupt_active_installation(
    setup: tuple[bootstrap.Bootstrap, FakeBackend, Candidate, Candidate],
) -> None:
    manager, _, _, _ = setup
    first = manager.ensure()
    old = manager.environment_path(str(first["environment"]))
    (old / "installed.txt").write_text("tampered")
    repaired = manager.update()
    assert repaired["state"] == "READY"
    assert repaired["environment"] != first["environment"]
    assert old.is_dir()
    assert manager.status() == repaired


def test_failed_repair_keeps_original_pointer(
    setup: tuple[bootstrap.Bootstrap, FakeBackend, Candidate, Candidate],
) -> None:
    manager, backend, _, _ = setup
    first = manager.ensure()
    old = manager.environment_path(str(first["environment"]))
    (old / "installed.txt").write_text("tampered")
    previous = (manager.home / "active.json").read_bytes()
    backend.fail_install = True
    with pytest.raises(bootstrap.BootstrapError):
        manager.update()
    assert (manager.home / "active.json").read_bytes() == previous
    assert old.is_dir()


def test_build_identity_binds_dependency_hashes(
    setup: tuple[bootstrap.Bootstrap, FakeBackend, Candidate, Candidate],
) -> None:
    from dataclasses import replace

    from install_catalog import Artifact

    _, _, first, _ = setup
    original = bootstrap.build_identity(first)
    changed = replace(
        first,
        build_artifacts=(
            Artifact(
                "dependency",
                "1",
                "dependency-1-py3-none-any.whl",
                "https://files.pythonhosted.org/file.whl",
                "a" * 64,
            ),
        ),
    )
    altered = bootstrap.build_identity(changed)
    assert original != altered
    assert altered == json.loads(json.dumps(altered))
    assert altered["python"] == list(sys.version_info[:3])


def test_cached_wheel_tamper_does_not_change_active_pointer(
    setup: tuple[bootstrap.Bootstrap, FakeBackend, Candidate, Candidate],
) -> None:
    manager, _, _, _ = setup
    first = manager.ensure()
    environment = manager.environment_path(str(first["environment"]))
    original = (environment / "installed.txt").read_bytes()
    pointer = (manager.home / "active.json").read_bytes()
    (environment / "installed.txt").write_text("requires repair")
    wheel = next(manager.home.glob("cache/builds/*/*.whl"))
    wheel.write_bytes(b"tampered")
    with pytest.raises(bootstrap.BootstrapError, match="Cached built wheel"):
        manager.update()
    assert (manager.home / "active.json").read_bytes() == pointer
    (environment / "installed.txt").write_bytes(original)
    assert manager.status() == first


def test_isolated_entrypoint_rejects_project_module_shadowing(tmp_path: Path) -> None:
    import subprocess

    marker = tmp_path / "executed"
    evil = f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n"
    (tmp_path / "reprollm.py").write_text(evil)
    (tmp_path / "install_catalog.py").write_text(evil)
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            str(SCRIPTS / "bootstrap.py"),
            "status",
            "--home",
            str(tmp_path / "no-install"),
        ],
        cwd=tmp_path,
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["state"] == "NOT_INSTALLED"
    assert not marker.exists()
    assert not (tmp_path / "no-install").exists()


def test_installer_ignores_foreign_pip_targets_and_configuration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import subprocess

    monkeypatch.setenv("PIP_TARGET", str(tmp_path / "training-environment"))
    monkeypatch.setenv("PIP_PREFIX", str(tmp_path / "other-environment"))
    monkeypatch.setenv("PIP_INDEX_URL", "https://secret:password@example.invalid/simple")
    monkeypatch.setenv("PYTHONPATH", str(tmp_path / "project-shadow"))

    def invoke(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        env = kwargs["env"]
        assert isinstance(env, dict)
        assert "PIP_TARGET" not in env and "PIP_PREFIX" not in env
        assert "PIP_INDEX_URL" not in env and "PYTHONPATH" not in env
        assert env["PIP_CONFIG_FILE"] == bootstrap.os.devnull
        return subprocess.CompletedProcess(argv, 0, b"{}", b"")

    monkeypatch.setattr(bootstrap.subprocess, "run", invoke)
    assert bootstrap.SystemBackend()._run(["trusted-python"]) == "{}"
    assert not (tmp_path / "training-environment").exists()


def archive_with_entries(entries: list[tuple[str, bytes]]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, raw in entries:
            info = tarfile.TarInfo(name)
            info.size = len(raw)
            archive.addfile(info, io.BytesIO(raw))
    return buffer.getvalue()


def test_extracts_only_build_inputs_from_large_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    blob = archive_with_entries(
        [
            ("repo/src/reprollm/__init__.py", b"package"),
            ("repo/pyproject.toml", b"[build-system]"),
            ("repo/README.md", b"public package readme"),
            ("repo/LICENSE", b"license"),
            ("repo/docs/large-history.json", b"x" * 100_000),
            ("repo/tests/huge-fixture.json", b"y" * 100_000),
            ("repo/untrusted_build.py", b"not a build input"),
        ]
    )
    monkeypatch.setattr(bootstrap, "MAX_BUILD_INPUT_BYTES", 128)
    root = bootstrap.extract_source(blob, tmp_path / "extract")
    assert sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()) == [
        "LICENSE",
        "README.md",
        "pyproject.toml",
        "src/reprollm/__init__.py",
    ]


def test_selected_build_inputs_have_separate_disk_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bootstrap, "MAX_BUILD_INPUT_BYTES", 1)
    with pytest.raises(bootstrap.BootstrapError, match="build input"):
        bootstrap.extract_source(source_blob(), tmp_path / "extract")


def test_unsafe_skipped_archive_entries_still_rejected(tmp_path: Path) -> None:
    blob = archive_with_entries(
        [
            ("repo/src/reprollm/__init__.py", b"package"),
            ("repo/docs/../../escape", b"not selected but unsafe"),
        ]
    )
    with pytest.raises(bootstrap.BootstrapError, match="unsafe"):
        bootstrap.extract_source(blob, tmp_path / "extract")


@pytest.mark.skipif(bootstrap.os.name == "nt", reason="POSIX executable permission")
def test_console_probe_requires_executable_permission(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = tmp_path / "venv"
    entry = environment / "bin/reprollm"
    entry.parent.mkdir(parents=True)
    entry.write_text("not executable")
    backend = bootstrap.SystemBackend()

    def forbidden(*args: object, **kwargs: object) -> str:
        raise AssertionError("A non-executable entry must fail before launching a probe")

    monkeypatch.setattr(backend, "_run", forbidden)
    with pytest.raises(bootstrap.BootstrapError, match="executable"):
        backend.probe(environment, candidate("entry", source_blob()))


def test_installed_receipt_binds_catalog_dependency_identity(
    setup: tuple[bootstrap.Bootstrap, FakeBackend, Candidate, Candidate],
) -> None:
    from dataclasses import replace

    from install_catalog import Artifact

    manager, backend, first, _ = setup
    manager.ensure()
    changed = replace(
        first,
        runtime_artifacts=(
            Artifact(
                "dependency",
                "1",
                "dependency-1-py3-none-any.whl",
                "https://files.pythonhosted.org/pinned.whl",
                "a" * 64,
            ),
        ),
    )
    changed_manager = bootstrap.Bootstrap(
        manager.home, Catalog(1, "first", (changed,)), backend=backend
    )
    with pytest.raises(bootstrap.BootstrapError, match="catalog"):
        changed_manager.ensure()
    assert backend.installs == 1


def test_state_missing_active_has_private_actionable_error(
    setup: tuple[bootstrap.Bootstrap, FakeBackend, Candidate, Candidate],
) -> None:
    manager, _, _, _ = setup
    manager.ensure()
    path = manager.home / "active.json"
    path.write_text(json.dumps({"schema_version": 1, "history": []}))
    with pytest.raises(bootstrap.BootstrapError, match="state"):
        manager.status()


def test_socks_finds_system_curl_when_an_untrusted_path_entry_shadows_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bootstrap.shutil, "which", lambda _: "/untrusted/project/curl")
    monkeypatch.setattr(Path, "is_file", lambda path: str(path) == "/usr/bin/curl")
    monkeypatch.setattr(bootstrap.os, "access", lambda path, mode: str(path) == "/usr/bin/curl")
    assert bootstrap.system_curl() == "/usr/bin/curl"
