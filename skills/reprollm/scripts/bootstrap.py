"""Prepare a verified, isolated ReproLLM installation using only the standard library."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import sysconfig
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
import uuid
import venv
import zipfile
from collections.abc import Iterator, Sequence
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
from typing import Any, Protocol, cast

# -I deliberately excludes the working directory and PYTHONPATH. Only this
# trusted Skill directory supplies the bootstrap's sibling catalog module.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from install_catalog import (  # noqa: E402
    Artifact,
    Candidate,
    Catalog,
    CatalogError,
    load_catalog,
    validate_blob,
)

MAX_DOWNLOAD_BYTES = 64 * 1024 * 1024
MAX_EXPANDED_BYTES = 512 * 1024 * 1024
MAX_BUILD_INPUT_BYTES = 64 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 100_000
_OWNER = {"schema_version": 1, "owner": "reprollm-skill"}
_ENV_NAME = re.compile(r"[0-9a-f]{32}")


class BootstrapError(ValueError):
    """An actionable installation error with no raw subprocess or network output."""


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    try:
        if path.is_symlink():
            raise BootstrapError("Skill state must use regular owned files.")
        value = json.loads(path.read_bytes())
        if not isinstance(value, dict) or (
            type(value.get("schema_version")) is not int or value.get("schema_version") != 1
        ):
            raise BootstrapError("Skill state is invalid; restore a verified installation.")
        return cast(dict[str, Any], value)
    except (OSError, ValueError) as error:
        raise BootstrapError(
            "Skill state is unreadable; restore a verified installation."
        ) from error


def _write(path: Path, value: dict[str, Any]) -> None:
    raw = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    temporary = path.with_name("." + path.name + "." + uuid.uuid4().hex)
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _directory(path: Path) -> None:
    if path.is_symlink():
        raise BootstrapError("Skill directories must not be symbolic links.")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not path.is_dir():
        raise BootstrapError("Choose a writable Skill installation directory.")


def environment_python(environment: Path) -> Path:
    return environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def extract_source(blob: bytes, destination: Path) -> Path:
    """Extract regular source files only, with compressed and expanded bounds."""
    if len(blob) > MAX_DOWNLOAD_BYTES:
        raise BootstrapError("Source archive exceeds the installation size limit.")
    _directory(destination)
    roots: set[str] = set()
    total = 0
    selected_total = 0
    names: set[str] = set()
    try:
        with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as archive:
            for count, member in enumerate(archive, 1):
                name = PurePosixPath(member.name)
                if (
                    count > MAX_ARCHIVE_MEMBERS
                    or not name.parts
                    or name.is_absolute()
                    or ".." in name.parts
                    or "\\" in member.name
                    or ":" in member.name
                    or not (member.isfile() or member.isdir())
                ):
                    raise BootstrapError("Source archive contains an unsafe entry.")
                roots.add(name.parts[0])
                total += member.size
                if total > MAX_EXPANDED_BYTES or len(roots) != 1:
                    raise BootstrapError("Source archive exceeds its declared structure or size.")
                relative = PurePosixPath(*name.parts[1:])
                selected = relative.as_posix() in {
                    "pyproject.toml",
                    "README.md",
                    "LICENSE",
                } or relative.parts[:2] == ("src", "reprollm")
                if not selected:
                    continue
                selected_total += member.size
                if selected_total > MAX_BUILD_INPUT_BYTES:
                    raise BootstrapError("Source build inputs exceed the installation disk limit.")
                target = destination.joinpath(*name.parts)
                if member.isdir():
                    _directory(target)
                    continue
                if member.name in names:
                    raise BootstrapError("Source archive contains duplicate files.")
                names.add(member.name)
                _directory(target.parent)
                stream = archive.extractfile(member)
                if stream is None:
                    raise BootstrapError("Source archive contains an unreadable file.")
                with stream, target.open("xb") as output:
                    shutil.copyfileobj(stream, output, length=65536)
                target.chmod(0o700 if member.mode & 0o111 else 0o600)
    except (OSError, tarfile.TarError, EOFError) as error:
        raise BootstrapError(
            "Source archive is invalid; obtain the catalog-pinned archive."
        ) from error
    if len(roots) != 1:
        raise BootstrapError("Source archive is empty.")
    root = destination / next(iter(roots))
    if not (root / "src/reprollm/__init__.py").is_file():
        raise BootstrapError("Source archive has no ReproLLM package.")
    return root


def _wheel_payload(wheel: Path, source: Path, candidate: Candidate) -> dict[str, str]:
    expected = {
        "reprollm/" + item.relative_to(source / "src/reprollm").as_posix(): item.read_bytes()
        for item in (source / "src/reprollm").rglob("*")
        if item.is_file() and "__pycache__" not in item.parts and item.suffix != ".pyc"
    }
    try:
        with zipfile.ZipFile(wheel) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise BootstrapError("Built wheel has duplicate entries.")
            for name in names:
                parts = PurePosixPath(name)
                if parts.is_absolute() or ".." in parts.parts or "\\" in name or ":" in name:
                    raise BootstrapError("Built wheel has unsafe entries.")
            actual = {
                name: archive.read(name)
                for name in names
                if name.startswith("reprollm/") and not name.endswith("/")
            }
            metadata = BytesParser().parsebytes(
                archive.read(f"reprollm-{candidate.version}.dist-info/METADATA")
            )
            if actual != expected or metadata["Version"] != candidate.version:
                raise BootstrapError("Built wheel does not match the pinned source package.")
            return {name: _digest(raw) for name, raw in actual.items()}
    except (OSError, KeyError, zipfile.BadZipFile) as error:
        raise BootstrapError("Built wheel is invalid; rebuild the pinned source.") from error


def compatible_artifacts(artifacts: tuple[Artifact, ...]) -> tuple[Artifact, ...]:
    """Select one catalog wheel per distribution for this interpreter and platform."""
    python = sys.version_info.major, sys.version_info.minor
    machine = platform.machine().lower()
    machine = {"amd64": "x86_64", "aarch64": "aarch64"}.get(machine, machine)
    system = sysconfig.get_platform().replace("-", "_").replace(".", "_")

    def compatible(filename: str) -> bool:
        try:
            interpreter, abi, systems = filename[:-4].rsplit("-", 3)[1:]
        except ValueError:
            return False
        interpreters = interpreter.split(".")
        direct = f"cp{python[0]}{python[1]}"
        if not any(
            tag in {"py3", f"py{python[0]}{python[1]}", direct}
            or (
                abi == "abi3"
                and tag.startswith("cp3")
                and tag[3:].isdigit()
                and int(tag[3:]) <= python[1]
            )
            for tag in interpreters
        ):
            return False
        if abi not in {"none", "abi3", direct}:
            return False
        for tag in systems.split("."):
            if tag == "any" or tag == system:
                return True
            if sys.platform == "linux" and tag.endswith("_" + machine):
                libc, version = platform.libc_ver()
                if tag.startswith("manylinux") and libc == "glibc":
                    parts = tag.split("_")
                    if len(parts) > 2 and parts[0] == "manylinux":
                        required = int(parts[1]), int(parts[2])
                    else:
                        required = {
                            "manylinux1": (2, 5),
                            "manylinux2010": (2, 12),
                            "manylinux2014": (2, 17),
                        }.get(parts[0], (99, 99))
                    try:
                        if tuple(int(part) for part in version.split(".")[:2]) >= required:
                            return True
                    except ValueError:
                        continue
            if sys.platform == "darwin" and tag.startswith("macosx_"):
                parts = tag.split("_")
                arch = "_".join(parts[3:])
                allowed = {machine, "universal2"}
                if machine == "aarch64":
                    allowed.add("arm64")
                try:
                    host = tuple(int(part) for part in platform.mac_ver()[0].split(".")[:2])
                    if arch in allowed and host >= (int(parts[1]), int(parts[2])):
                        return True
                except (ValueError, IndexError):
                    continue
        return False

    groups: dict[tuple[str, str], list[Artifact]] = {}
    for artifact in artifacts:
        groups.setdefault((artifact.name, artifact.version), []).append(artifact)
    selected: list[Artifact] = []
    for group in groups.values():
        matches = [item for item in group if compatible(item.filename)]
        if not matches:
            raise BootstrapError(
                "No pinned wheel supports this Python/platform; use a supported environment."
            )
        selected.append(sorted(matches, key=lambda item: item.filename)[0])
    return tuple(selected)


def environment_hashes(environment: Path) -> dict[str, str]:
    """Attest installed code before any installed interpreter or module executes."""
    root = environment.resolve()
    result: dict[str, str] = {}
    for path in sorted(environment.rglob("*")):
        relative = path.relative_to(environment)
        if relative.parts[0] == "leases" or relative.as_posix() in {"owner.json", "receipt.json"}:
            continue
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode):
            if not path.resolve().is_relative_to(root):
                raise BootstrapError("Installed environment contains an escaping symbolic link.")
            result[relative.as_posix()] = _digest(b"symlink:" + os.readlink(path).encode())
        elif stat.S_ISREG(mode):
            result[relative.as_posix()] = _digest(
                path.read_bytes() + b"\0mode:" + oct(stat.S_IMODE(mode)).encode()
            )
        elif not stat.S_ISDIR(mode):
            raise BootstrapError("Installed environment contains an unsupported file type.")
    if not result:
        raise BootstrapError("Installed environment has no verifiable files.")
    return result


def build_identity(candidate: Candidate) -> dict[str, Any]:
    return {
        "candidate_id": candidate.id,
        "version": candidate.version,
        "capabilities": list(candidate.capabilities),
        "python_min": list(candidate.python_min),
        "python_max": list(candidate.python_max),
        "supported_platforms": list(candidate.platforms),
        "source_sha256": candidate.source_sha256,
        "source_commit": candidate.source_commit,
        "python": list(sys.version_info[:3]),
        "cache_tag": sys.implementation.cache_tag,
        "abi": sysconfig.get_config_var("SOABI"),
        "platform": sys.platform,
        "machine": platform.machine(),
        "build_artifacts": sorted(
            [item.filename, item.sha256] for item in candidate.build_artifacts
        ),
        "runtime_artifacts": sorted(
            [item.filename, item.sha256] for item in candidate.runtime_artifacts
        ),
    }


class Backend(Protocol):
    def fetch(self, url: str) -> bytes: ...
    def create_venv(self, path: Path) -> None: ...
    def build(
        self, source: Path, environment: Path, wheelhouse: Path, output: Path, selected: Candidate
    ) -> Path: ...
    def install(
        self, environment: Path, wheelhouse: Path, requirements: tuple[str, ...]
    ) -> None: ...
    def probe(self, environment: Path, selected: Candidate) -> dict[str, str]: ...


_PROBE = r"""
import hashlib, importlib.metadata, json, os, pathlib, subprocess, sys, tempfile
import reprollm
root = pathlib.Path(sys.prefix).resolve()
assert root == pathlib.Path(sys.argv[2]).resolve()
package = pathlib.Path(reprollm.__file__).resolve().parent
assert package.is_relative_to(root)
assert reprollm.__version__ == sys.argv[1] == importlib.metadata.version('reprollm')
entry = root / ('Scripts/reprollm.exe' if sys.platform == 'win32' else 'bin/reprollm')
assert entry.is_file() and entry.resolve().is_relative_to(root) and os.access(entry, os.X_OK)
command = [sys.executable, '-I', '-B', '-c', 'from reprollm.cli.main import cli; cli()']
with tempfile.TemporaryDirectory(prefix='reprollm-install-probe-') as folder:
    for arguments in [['--version'], ['--help']]:
        console = subprocess.run([str(entry), *arguments], cwd=folder,
                                 capture_output=True, timeout=60)
        assert console.returncode == 0
        if arguments == ['--version']:
            assert sys.argv[1] in console.stdout.decode()
    for args, required in [(['--help'], ['audit', 'init', 'run', 'runs', 'diff',
                                         'export', 'rules', 'discover']),
                           (['run', '--help'], ['--dry-run']),
                           (['init', '--help'], ['--command'])]:
        result = subprocess.run(command + args, cwd=folder, capture_output=True, timeout=60)
        assert result.returncode == 0 and all(word in result.stdout.decode() for word in required)
    audit_args = ['audit', folder, '--level', '0', '--format', 'json', '--fail-on', 'never']
    result = subprocess.run(command + audit_args,
                            cwd=folder, capture_output=True, timeout=60)
    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report['schema_version'] and isinstance(report['findings'], list)
    target = pathlib.Path(folder) / 'schemas'
    result = subprocess.run(command + ['schema', 'export', '--out', str(target)],
                            cwd=folder, capture_output=True, timeout=60)
    assert result.returncode == 0 and len(list(target.glob('*.json'))) == 10
payload = {}
for p in package.rglob('*'):
    if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc':
        key = 'reprollm/' + p.relative_to(package).as_posix()
        payload[key] = hashlib.sha256(p.read_bytes()).hexdigest()
print(json.dumps(payload, sort_keys=True))
"""


def system_curl() -> str | None:
    locations = [Path("/usr/bin/curl"), Path("/bin/curl"), Path("/usr/local/bin/curl")]
    windows = os.environ.get("SYSTEMROOT")
    if windows:
        locations.insert(0, Path(windows) / "System32/curl.exe")
    for path in locations:
        if path.is_absolute() and path.is_file() and os.access(path, os.X_OK):
            return str(path)
    return None


class SystemBackend:
    def fetch(self, url: str) -> bytes:
        if any(
            value.lower().startswith(("socks:", "socks4:", "socks5:", "socks5h:"))
            for key, value in os.environ.items()
            if key.lower().endswith("_proxy")
        ):
            executable = system_curl()
            if executable is not None:
                return self._curl(executable, url)
            raise BootstrapError(
                "Bootstrap needs system curl for this SOCKS proxy; install curl, "
                "use an HTTPS proxy or provide a verified offline wheelhouse."
            )
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "reprollm-skill-bootstrap"}
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read(MAX_DOWNLOAD_BYTES + 1)
            if len(raw) > MAX_DOWNLOAD_BYTES:
                raise BootstrapError("Installation download exceeds the size limit.")
            return cast(bytes, raw)
        except (OSError, ValueError) as error:
            raise BootstrapError(
                "Installation download failed; check network/HTTPS proxy or provide "
                "the catalog-pinned files in an offline wheelhouse."
            ) from error

    def _curl(self, executable: str, url: str) -> bytes:
        try:
            result = subprocess.run(
                [
                    executable,
                    "--disable",
                    "--silent",
                    "--fail",
                    "--location",
                    "--proto",
                    "=https",
                    "--proto-redir",
                    "=https",
                    "--retry",
                    "0",
                    "--max-time",
                    "30",
                    "--connect-timeout",
                    "15",
                    "--max-filesize",
                    str(MAX_DOWNLOAD_BYTES),
                    "--url",
                    url,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=35,
                check=False,
            )
            if result.returncode or len(result.stdout) > MAX_DOWNLOAD_BYTES:
                raise BootstrapError(
                    "Download failed through SOCKS; check the proxy or use an offline wheelhouse."
                )
            return result.stdout
        except (OSError, subprocess.SubprocessError) as error:
            raise BootstrapError(
                "Download failed through SOCKS; check the proxy or use an offline wheelhouse."
            ) from error

    def create_venv(self, path: Path) -> None:
        try:
            venv.EnvBuilder(with_pip=True).create(path)
        except (OSError, subprocess.SubprocessError) as error:
            raise BootstrapError(
                "Install Python with venv/ensurepip support, then retry."
            ) from error

    def _run(self, argv: Sequence[str], *, cwd: Path | None = None) -> str:
        environment = os.environ.copy()
        for key in list(environment):
            if key in {"PYTHONPATH", "PYTHONHOME"} or key.upper().startswith("PIP_"):
                environment.pop(key, None)
        environment.update(
            {
                "PYTHONNOUSERSITE": "1",
                "PIP_CONFIG_FILE": os.devnull,
                "PIP_DISABLE_PIP_VERSION_CHECK": "1",
                "NO_COLOR": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
            }
        )
        try:
            result = subprocess.run(
                list(argv), cwd=cwd, env=environment, capture_output=True, timeout=300, check=False
            )
            if result.returncode or len(result.stdout) > 1024 * 1024:
                raise BootstrapError(
                    "Tool preparation failed; verify Python and the pinned wheelhouse."
                )
            return result.stdout.decode("utf-8")
        except (OSError, UnicodeError, subprocess.SubprocessError) as error:
            raise BootstrapError(
                "Tool preparation failed; verify Python and the pinned wheelhouse."
            ) from error

    def install(self, environment: Path, wheelhouse: Path, requirements: tuple[str, ...]) -> None:
        target = environment / "requirements.install.txt"
        target.write_text("\n".join(requirements) + "\n", encoding="utf-8")
        try:
            self._run(
                [
                    str(environment_python(environment)),
                    "-I",
                    "-m",
                    "pip",
                    "install",
                    "--no-index",
                    "--only-binary=:all:",
                    "--require-hashes",
                    "--no-compile",
                    "--find-links",
                    str(wheelhouse),
                    "-r",
                    str(target),
                ]
            )
        finally:
            target.unlink(missing_ok=True)

    def build(
        self, source: Path, environment: Path, wheelhouse: Path, output: Path, selected: Candidate
    ) -> Path:
        self.create_venv(environment)
        self.install(environment, wheelhouse, selected.requirements("build"))
        _directory(output)
        self._run(
            [
                str(environment_python(environment)),
                "-I",
                "-m",
                "hatchling",
                "build",
                "-t",
                "wheel",
                "-d",
                str(output),
            ],
            cwd=source,
        )
        return output / selected.wheel_filename

    def probe(self, environment: Path, selected: Candidate) -> dict[str, str]:
        entry = environment / ("Scripts/reprollm.exe" if os.name == "nt" else "bin/reprollm")
        if not entry.is_file() or not os.access(entry, os.X_OK):
            raise BootstrapError(
                "Installed console entry is not executable; explicitly repair the tool."
            )
        try:
            output = self._run(
                [
                    str(environment_python(environment)),
                    "-I",
                    "-B",
                    "-c",
                    _PROBE,
                    selected.version,
                    str(environment),
                ],
                cwd=environment,
            )
            value = json.loads(output)
            if not isinstance(value, dict) or not value:
                raise BootstrapError("Installed tool failed its capability probe.")
            if not all(
                isinstance(k, str) and isinstance(v, str) and re.fullmatch(r"[a-f0-9]{64}", v)
                for k, v in value.items()
            ):
                raise BootstrapError("Installed tool returned invalid package evidence.")
            return cast(dict[str, str], value)
        except ValueError as error:
            raise BootstrapError(
                "Installed tool failed its capability probe; repair or roll back."
            ) from error


class Bootstrap:
    def __init__(self, home: Path, catalog: Catalog, *, backend: Backend | None = None) -> None:
        self.home = home.absolute()
        self.catalog = catalog
        self.backend: Backend = backend or SystemBackend()

    def _prepare(self) -> None:
        if self.home.is_symlink():
            raise BootstrapError("Skill installation home must not be a symbolic link.")
        if self.home.exists():
            marker = self.home / "owner.json"
            if not marker.is_file() and any(
                path.name != ".install-lock" for path in self.home.iterdir()
            ):
                raise BootstrapError(
                    "Choose an empty Skill home; existing user files were preserved."
                )
            if marker.is_file() and _read(marker) != _OWNER:
                raise BootstrapError("Installation home belongs to another application.")
        _directory(self.home)
        if not (self.home / "owner.json").exists():
            _write(self.home / "owner.json", _OWNER)
        for child in ("environments", "cache", "cache/blobs", "cache/builds", "work"):
            _directory(self.home / child)

    @contextlib.contextmanager
    def _lock(self, timeout: float = 30) -> Iterator[None]:
        if self.home.is_symlink():
            raise BootstrapError("Skill installation home must not be a symbolic link.")
        _directory(self.home)
        lock = self.home / ".install-lock"
        deadline = time.monotonic() + timeout
        while True:
            try:
                lock.mkdir(mode=0o700)
                break
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise BootstrapError(
                        "Another installation holds the lock; wait for it to finish. "
                        "For an abandoned lock, verify no installer is running before removing it."
                    ) from None
                time.sleep(min(0.05, max(0, deadline - time.monotonic())))
        try:
            self._prepare()
            yield
        finally:
            lock.rmdir()

    def environment_path(self, name: str) -> Path:
        if _ENV_NAME.fullmatch(name) is None:
            raise BootstrapError("Invalid environment identity; restore owned Skill state.")
        path = self.home / "environments" / name
        if path.is_symlink() or (self.home / "environments").is_symlink():
            raise BootstrapError("Environment identity must refer to an owned directory.")
        return path

    def _state(self) -> dict[str, Any]:
        path = self.home / "active.json"
        if not path.exists():
            return {"schema_version": 1, "active": None, "history": []}
        if self.home.is_symlink() or _read(self.home / "owner.json") != _OWNER:
            raise BootstrapError("Skill home ownership could not be verified.")
        state = _read(path)
        if set(state) != {"schema_version", "active", "history"}:
            raise BootstrapError("Skill state fields are invalid; restore owned state.")
        active, history = state.get("active"), state.get("history")
        if not isinstance(history, list) or any(not isinstance(x, str) for x in history):
            raise BootstrapError("Skill history is invalid; restore owned state.")
        for name in history:
            self.environment_path(name)
        if active is not None:
            if not isinstance(active, str):
                raise BootstrapError("Skill active environment is invalid.")
            self.environment_path(active)
        return state

    def _verify(self, name: str) -> dict[str, Any]:
        environment = self.environment_path(name)
        receipt = _read(environment / "receipt.json")
        if receipt.get("owner") != _OWNER["owner"] or receipt.get("environment") != name:
            raise BootstrapError("Environment has no matching ownership receipt.")
        candidate = self.catalog.get_candidate(receipt.get("candidate_id"))
        if (
            receipt.get("source_commit") != candidate.source_commit
            or receipt.get("source_sha256") != candidate.source_sha256
        ):
            raise BootstrapError("Environment source identity differs from the trusted catalog.")
        if receipt.get("candidate_identity") != build_identity(candidate):
            raise BootstrapError(
                "Installed tool catalog identity changed; request an explicit update."
            )
        if _read(environment / "owner.json") != _OWNER:
            raise BootstrapError("Environment ownership could not be verified.")
        if environment_hashes(environment) != receipt.get("environment_hashes"):
            raise BootstrapError("Installed environment changed; explicitly update or roll back.")
        if self.backend.probe(environment, candidate) != receipt.get("package_hashes"):
            raise BootstrapError("Installed package changed; explicitly update or roll back.")
        if environment_hashes(environment) != receipt.get("environment_hashes"):
            raise BootstrapError("Installed environment changed during its probe.")
        return {
            "schema_version": 1,
            "state": "READY",
            "candidate_id": candidate.id,
            "version": candidate.version,
            "environment": name,
            "capabilities": list(candidate.capabilities),
        }

    def status(self) -> dict[str, Any]:
        state = self._state()
        name = state["active"]
        if name is None:
            return {"schema_version": 1, "state": "NOT_INSTALLED"}
        return self._verify(name)

    def _blob(self, item: Artifact | Candidate, wheelhouse: Path | None, offline: bool) -> bytes:
        digest = item.source_sha256 if isinstance(item, Candidate) else item.sha256
        filename = digest + ".tar.gz" if isinstance(item, Candidate) else item.filename
        cached = self.home / "cache/blobs" / digest
        if cached.is_symlink():
            raise BootstrapError("Cached installation artifact must be a regular file.")
        if cached.is_file():
            raw = cached.read_bytes()
        elif wheelhouse is not None and (wheelhouse / filename).is_file():
            raw = (wheelhouse / filename).read_bytes()
        elif offline:
            raise BootstrapError(
                "Required offline artifact is missing from the verified wheelhouse."
            )
        else:
            raw = self.backend.fetch(item.source_url if isinstance(item, Candidate) else item.url)
        try:
            validate_blob(item, raw)
        except CatalogError as error:
            raise BootstrapError(
                "Installation artifact hash differs from the trusted catalog."
            ) from error
        if not cached.exists():
            temporary = cached.with_name("." + digest + "." + uuid.uuid4().hex)
            temporary.write_bytes(raw)
            os.replace(temporary, cached)
        return raw

    def _build_wheel(self, candidate: Candidate, source: Path, wheelhouse: Path) -> Path:
        identity = build_identity(candidate)
        fingerprint = _digest(json.dumps(identity, sort_keys=True).encode())
        key = candidate.source_sha256 + "-" + fingerprint
        cached = self.home / "cache/builds" / key
        _directory(cached)
        wheel = cached / candidate.wheel_filename
        receipt_path = cached / "receipt.json"
        if wheel.exists() or receipt_path.exists():
            receipt = _read(receipt_path)
            if (
                wheel.is_symlink()
                or receipt.get("build_identity") != identity
                or receipt.get("source_sha256") != candidate.source_sha256
                or receipt.get("wheel_sha256") != _digest(wheel.read_bytes())
            ):
                raise BootstrapError(
                    "Cached built wheel changed; remove only this invalid cache entry."
                )
            _wheel_payload(wheel, source, candidate)
            return wheel
        build_root = Path(tempfile.mkdtemp(prefix="build-", dir=self.home / "work"))
        try:
            built = self.backend.build(
                source, build_root / "venv", wheelhouse, build_root / "dist", candidate
            )
            _wheel_payload(built, source, candidate)
            shutil.copyfile(built, wheel)
            _write(
                receipt_path,
                {
                    "schema_version": 1,
                    "source_commit": candidate.source_commit,
                    "source_sha256": candidate.source_sha256,
                    "wheel_sha256": _digest(wheel.read_bytes()),
                    "wheel_filename": candidate.wheel_filename,
                    "build_identity": identity,
                    "origin": "locally-built-pinned-source",
                },
            )
            return wheel
        finally:
            shutil.rmtree(build_root)

    def _install(self, candidate: Candidate, wheelhouse: Path | None, offline: bool) -> str:
        if not candidate.supports((sys.version_info.major, sys.version_info.minor), sys.platform):
            raise BootstrapError("Use a catalog-supported Python version and operating system.")
        work = Path(tempfile.mkdtemp(prefix="install-", dir=self.home / "work"))
        name = uuid.uuid4().hex
        environment = self.environment_path(name)
        try:
            source = extract_source(self._blob(candidate, wheelhouse, offline), work / "source")
            wheels = work / "wheels"
            _directory(wheels)
            for item in compatible_artifacts(
                (*candidate.runtime_artifacts, *candidate.build_artifacts)
            ):
                (wheels / item.filename).write_bytes(self._blob(item, wheelhouse, offline))
            wheel = self._build_wheel(candidate, source, wheels)
            shutil.copyfile(wheel, wheels / wheel.name)
            self.backend.create_venv(environment)
            _write(environment / "owner.json", _OWNER)
            self.backend.install(
                environment,
                wheels,
                (
                    *candidate.requirements("runtime"),
                    f"reprollm=={candidate.version} --hash=sha256:{_digest(wheel.read_bytes())}",
                ),
            )
            hashes = self.backend.probe(environment, candidate)
            expected = _wheel_payload(wheel, source, candidate)
            # The backend probe covers installed package bytes; the receipt binds
            # this observation to the already verified build and immutable source.
            if hashes != expected:
                raise BootstrapError("Installed package bytes differ from the verified wheel.")
            _write(
                environment / "receipt.json",
                {
                    **_OWNER,
                    "environment": name,
                    "candidate_id": candidate.id,
                    "source_commit": candidate.source_commit,
                    "source_sha256": candidate.source_sha256,
                    "wheel_sha256": _digest(wheel.read_bytes()),
                    "package_hashes": hashes,
                    "candidate_identity": build_identity(candidate),
                    "environment_hashes": environment_hashes(environment),
                    "origin": "locally-built-pinned-source",
                },
            )
            return name
        except BaseException:
            if environment.exists() and not environment.is_symlink():
                shutil.rmtree(environment)
            raise
        finally:
            shutil.rmtree(work)

    def ensure(
        self,
        candidate_id: str | None = None,
        *,
        wheelhouse: Path | None = None,
        offline: bool = False,
        lock_timeout: float = 30,
    ) -> dict[str, Any]:
        with self._lock(lock_timeout):
            selected = self.catalog.get_candidate(candidate_id)
            state = self._state()
            if state["active"] is not None:
                current = self._verify(state["active"])
                if current["candidate_id"] != selected.id:
                    raise BootstrapError("A different tool is active; request an explicit update.")
                return current
            name = self._install(selected, wheelhouse, offline)
            result = self._verify(name)
            _write(self.home / "active.json", {**state, "active": name})
            return result

    def update(
        self,
        candidate_id: str | None = None,
        *,
        wheelhouse: Path | None = None,
        offline: bool = False,
    ) -> dict[str, Any]:
        with self._lock():
            selected = self.catalog.get_candidate(candidate_id)
            state = self._state()
            if state["active"] is not None:
                try:
                    current = self._verify(state["active"])
                except BootstrapError:
                    current = None
                if current is not None and current["candidate_id"] == selected.id:
                    return current
            name = self._install(selected, wheelhouse, offline)
            history = [*state["history"]]
            if state["active"] is not None:
                history.append(state["active"])
            result = self._verify(name)
            _write(
                self.home / "active.json", {"schema_version": 1, "active": name, "history": history}
            )
            return result

    def rollback(self) -> dict[str, Any]:
        with self._lock():
            state = self._state()
            if not state["history"]:
                raise BootstrapError("No verified previous installation is available to roll back.")
            history = list(state["history"])
            name = history.pop()
            result = self._verify(name)
            if state["active"] is not None:
                history.insert(0, state["active"])
            _write(
                self.home / "active.json", {"schema_version": 1, "active": name, "history": history}
            )
            return result

    def uninstall(self) -> dict[str, Any]:
        with self._lock():
            state = self._state()
            _write(self.home / "active.json", {"schema_version": 1, "active": None, "history": []})
            names = {*state["history"]}
            if state["active"] is not None:
                names.add(state["active"])
            for name in names:
                environment = self.environment_path(name)
                leases = environment / "leases"
                if leases.exists() and (
                    leases.is_symlink() or not leases.is_dir() or any(leases.iterdir())
                ):
                    # Unknown/stale leases also preserve the environment. Workers
                    # release their own leases; uninstall never guesses liveness.
                    continue
                if _read(environment / "owner.json") == _OWNER:
                    shutil.rmtree(environment)
            return {"schema_version": 1, "state": "NOT_INSTALLED"}


def default_home() -> Path:
    if sys.platform == "win32":
        return (
            Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local")))
            / "reprollm-skill"
        )
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/reprollm-skill"
    return (
        Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "reprollm-skill"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "operation", choices=["ensure", "status", "update", "rollback", "uninstall"]
    )
    parser.add_argument("--home", type=Path, default=default_home())
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "assets/install-catalog.json",
    )
    parser.add_argument("--candidate")
    parser.add_argument("--wheelhouse", type=Path)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)
    try:
        manager = Bootstrap(args.home, load_catalog(args.catalog))
        if args.operation in {"ensure", "update"}:
            action = manager.ensure if args.operation == "ensure" else manager.update
            result = action(args.candidate, wheelhouse=args.wheelhouse, offline=args.offline)
        else:
            result = getattr(manager, args.operation)()
        print(json.dumps(result, sort_keys=True))
        return 0
    except (BootstrapError, CatalogError, OSError) as error:
        message = (
            str(error)
            if isinstance(error, (BootstrapError, CatalogError))
            else (
                "Skill installation could not access its files; "
                "check directory permissions and disk space."
            )
        )
        print(
            json.dumps(
                {"schema_version": 1, "state": "BLOCKED", "message": message}, sort_keys=True
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
