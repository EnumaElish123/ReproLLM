"""Subprocess wrapper that records runtime truth (spec §5.1)."""

from __future__ import annotations

import getpass
import json
import os
import secrets
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import ExitStack, contextmanager, suppress
from datetime import datetime, timezone
from pathlib import Path
from types import FrameType
from typing import Any, Literal, TextIO

from reprollm import __version__
from reprollm.core import envinfo, proc
from reprollm.core.bindings import observe
from reprollm.core.errors import UserError
from reprollm.core.git import inspect_git
from reprollm.core.hashing import sha256_bytes
from reprollm.core.paths import LOCK, MANIFEST, PROJECT_RULES, RUNS_DIR, resolve_project_file
from reprollm.core.redaction import redact_env, redact_lines
from reprollm.core.yaml_io import load_manifest, load_yaml
from reprollm.run.capture import (
    collect_outputs,
    declared_files,
    hash_and_snapshot,
    resolve_argv_files,
)
from reprollm.run.hardware import capture_hardware
from reprollm.run.privacy import RunPrivacy
from reprollm.run.slurm import capture_scheduler
from reprollm.schemas.manifest import Manifest
from reprollm.schemas.project_rules import ProjectRules
from reprollm.schemas.run_record import (
    CodeInfo,
    CommandInfo,
    DocumentRef,
    RunEnvironment,
    RunRecord,
    RunStatus,
)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def create_run_dir(root: Path) -> Path:
    root = root.resolve()
    parent = root / RUNS_DIR
    if (root / ".reprollm").is_symlink() or parent.is_symlink():
        raise UserError("run directory must not be a symlink; check .reprollm/runs")
    try:
        parent.mkdir(parents=True, exist_ok=True)
        while True:
            run_id = f"{_now():%Y%m%dT%H%M%SZ}-{secrets.token_hex(3)}"
            destination = parent / run_id
            try:
                destination.mkdir()
            except FileExistsError:
                continue
            return destination
    except OSError as exc:
        raise UserError(
            f"cannot create run directory ({type(exc).__name__}); check .reprollm/runs permissions"
        ) from None


def _destination(run_dir: Path, name: str) -> Path:
    path = run_dir / name
    if run_dir.is_symlink() or path.is_symlink() or not path.resolve().is_relative_to(run_dir):
        raise UserError("run artifact destination must remain inside the run directory")
    return path


def _write_record(record: RunRecord, run_dir: Path, privacy: RunPrivacy) -> RunRecord:
    safe = RunRecord.model_validate(privacy.value(record))
    text = json.dumps(safe.model_dump(mode="json"), indent=2, sort_keys=True, ensure_ascii=False)
    destination = _destination(run_dir, "run.json")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", dir=run_dir, suffix=".tmp", delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(text + "\n")
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return safe


def _safe_load(root: Path) -> tuple[Manifest | None, ProjectRules | None]:
    manifest = None
    rules = None
    for name in (MANIFEST, PROJECT_RULES):
        path = root / name
        if not path.exists() and not path.is_symlink():
            continue
        resolved = resolve_project_file(root, name)
        if resolved is None:
            raise UserError(f"{name} must be a readable file inside the repository")
        try:
            if name == MANIFEST:
                manifest = load_manifest(resolved)
            else:
                rules = ProjectRules.model_validate(load_yaml(resolved))
        except (UserError, ValueError) as exc:
            raise UserError(
                f"cannot load {name} ({type(exc).__name__}); validate its contents"
            ) from None
    return manifest, rules


def _tee(
    source: TextIO,
    terminal: TextIO,
    log: TextIO,
    privacy: RunPrivacy,
    warnings: list[str],
    label: str,
) -> None:
    def echoed() -> Iterator[str]:
        for line in source:
            try:
                terminal.write(line)
                terminal.flush()
            except (OSError, ValueError):
                pass
            yield line

    failed = False
    try:
        for line in redact_lines(echoed()):
            if not failed:
                try:
                    log.write(privacy.text(line)[0])
                    log.flush()
                except (OSError, ValueError) as exc:
                    warnings.append(f"{label} capture failed ({type(exc).__name__})")
                    failed = True
    except Exception as exc:
        warnings.append(f"{label} capture failed ({type(exc).__name__})")
    finally:
        source.close()


@contextmanager
def _forward_signals(child: subprocess.Popen[str]) -> Iterator[None]:
    if threading.current_thread() is not threading.main_thread():
        yield
        return
    signals = [signal.SIGINT] if os.name == "nt" else [signal.SIGINT, signal.SIGTERM]
    previous = {sig: signal.getsignal(sig) for sig in signals}
    forwarded: set[int] = set()

    def forward(number: int, frame: FrameType | None) -> None:
        if number not in forwarded and child.poll() is None:
            forwarded.add(number)
            with suppress(ProcessLookupError):
                child.send_signal(getattr(signal, "CTRL_C_EVENT", 0) if os.name == "nt" else number)

    try:
        for sig in signals:
            signal.signal(sig, forward)
        yield
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def _capture_code(root: Path, run_dir: Path, privacy: RunPrivacy) -> CodeInfo:
    git = inspect_git(root)
    code = CodeInfo(
        commit=git.commit,
        branch=git.branch,
        dirty=git.dirty,
        modified_count=len(git.modified),
        untracked_count=len(git.untracked),
        remote=git.remote_origin,
    )
    if git.dirty:
        patch = proc.run_cmd(
            ["git", "diff", "HEAD", "--no-ext-diff", "--no-textconv", "--"], cwd=root
        )
        if patch.returncode != 0:
            raise OSError("git diff failed")
        data = privacy.text(patch.stdout)[0].encode("utf-8")
        _destination(run_dir, "patch.diff").write_bytes(data)
        code.patch_file = "patch.diff"
        code.patch_sha256 = sha256_bytes(data)
    return code


def _snapshot_document(
    root: Path,
    run_dir: Path,
    name: str,
    snapshot: str,
    privacy: RunPrivacy,
) -> DocumentRef | None:
    source = root / name
    if not source.exists() and not source.is_symlink():
        return None
    resolved = resolve_project_file(root, name)
    if resolved is None:
        raise UserError(f"{name} must remain inside the repository")
    data = resolved.read_bytes()
    safe = privacy.text(data.decode("utf-8"))[0]
    _destination(run_dir, snapshot).write_text(safe, encoding="utf-8", newline="")
    return DocumentRef(path=name, sha256=sha256_bytes(data), snapshot=snapshot)


def _collect(
    record: RunRecord,
    *,
    root: Path,
    cwd: Path,
    run_dir: Path,
    argv: Sequence[str],
    env: dict[str, str],
    hostname: str,
    privacy: RunPrivacy,
    manifest: Manifest | None,
    project_rules: ProjectRules | None,
    env_capture: Literal["allowlist", "all"],
    extra_allowlist: Sequence[str],
    snapshot: bool,
    max_bytes: int,
) -> None:
    def field(name: str, capture: Callable[[], Any]) -> None:
        try:
            setattr(record, name, capture())
        except Exception as exc:
            record.warnings.append(f"{name} capture failed ({type(exc).__name__})")

    field("code", lambda: _capture_code(root, run_dir, privacy))
    field(
        "environment",
        lambda: RunEnvironment.model_validate(
            {
                "os": envinfo.os_description(),
                "platform": envinfo.platform_name(),
                "python": envinfo.python_version(),
                "hostname_sha256": sha256_bytes(hostname.encode()),
                "packages": envinfo.installed_versions(),
                "env": redact_env(env, env_capture, extra_allowlist),
                "env_capture": env_capture,
            }
        ),
    )
    field("hardware", capture_hardware)
    field("scheduler", lambda: capture_scheduler(env))
    field("manifest", lambda: _snapshot_document(root, run_dir, MANIFEST, "manifest.yaml", privacy))
    field("lock", lambda: _snapshot_document(root, run_dir, LOCK, "lock.yaml", privacy))
    field(
        "files",
        lambda: hash_and_snapshot(
            resolve_argv_files(argv, root, cwd) + declared_files(manifest, project_rules),
            run_dir,
            root=root,
            snapshot=snapshot,
            max_bytes=max_bytes,
            warnings=record.warnings,
            sanitize=privacy.text,
        ),
    )
    field(
        "bindings_observed",
        lambda: observe(
            manifest.bindings if manifest else {},
            argv,
            env,
            root,
            project_rules=project_rules,
            warnings=record.warnings,
        ),
    )
    if manifest is not None and manifest.artifacts is not None:
        outputs = manifest.artifacts.outputs or []
        field("artifacts", lambda: collect_outputs(root, outputs))


def execute(
    argv: Sequence[str],
    *,
    root: Path,
    cwd: Path,
    run_dir: Path,
    capture_output: bool,
    env_capture: Literal["allowlist", "all"],
    extra_allowlist: Sequence[str],
    snapshot: bool,
    name: str | None = None,
    max_bytes: int = 1_048_576,
) -> RunRecord:
    """Execute unchanged argv; capture failures never replace a completed child's exit code."""
    root, cwd = root.resolve(), cwd.resolve()
    if not argv:
        raise UserError("run requires a command after --")
    if not cwd.is_dir() or not cwd.is_relative_to(root):
        raise UserError("--cwd must be a directory inside the repository")
    if run_dir.is_symlink() or not run_dir.resolve().is_relative_to(root / RUNS_DIR):
        raise UserError("run directory must remain inside .reprollm/runs")
    run_dir = run_dir.resolve()
    if not run_dir.is_dir() or any(run_dir.iterdir()):
        raise UserError("run directory must be a new empty directory")
    manifest, project_rules = _safe_load(root)
    hostname, username = socket.gethostname(), getpass.getuser()
    privacy = RunPrivacy(root, hostname=hostname, username=username)
    command, redactions = [], 0
    for index, token in enumerate(argv):
        if index == 0 and Path(token).is_absolute():
            token = Path(token).name
        safe, count = privacy.text(token)
        command.append(safe)
        redactions += count
    record = RunRecord(
        reprollm_version=__version__,
        run_id=run_dir.name,
        name=name,
        status=RunStatus.RUNNING,
        started_at=_now(),
        command=CommandInfo(
            argv=command,
            cwd=cwd.relative_to(root).as_posix(),
            redactions=redactions,
        ),
    )
    if manifest is None:
        record.warnings.append("no reprollm.yaml; bindings and declared files unavailable")
    try:
        _write_record(record, run_dir, privacy)
    except OSError as exc:
        raise UserError(
            f"cannot write run.json ({type(exc).__name__}); check run directory permissions"
        ) from None
    env = dict(os.environ)
    child_env = {**env, "REPROLLM_RUN_ID": record.run_id, "REPROLLM_RUN_DIR": str(run_dir)}
    start = time.monotonic()
    output_warnings: list[str] = []
    try:
        with ExitStack() as stack:
            logs = (
                [
                    stack.enter_context(
                        _destination(run_dir, f"{label}.log").open(
                            "w",
                            encoding="utf-8",
                            newline="",
                        )
                    )
                    for label in ("stdout", "stderr")
                ]
                if capture_output
                else []
            )
            child = subprocess.Popen(
                list(argv),
                cwd=cwd,
                env=child_env,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE if capture_output else None,
                stderr=subprocess.PIPE if capture_output else None,
                creationflags=(
                    getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
                ),
            )
            with child, _forward_signals(child):
                threads = []
                if capture_output:
                    for source, terminal, log, label in zip(
                        [child.stdout, child.stderr],
                        [sys.stdout, sys.stderr],
                        logs,
                        ["stdout", "stderr"],
                        strict=True,
                    ):
                        assert source is not None
                        thread = threading.Thread(
                            target=_tee,
                            args=(source, terminal, log, privacy, output_warnings, label),
                            daemon=True,
                        )
                        threads.append(thread)
                        thread.start()
                record.exit_code = child.wait()
                for thread in threads:
                    thread.join()
    except OSError as exc:
        if record.exit_code is None:
            record.status = RunStatus.FAILED
            record.ended_at = _now()
            record.warnings.append(f"command start failed ({type(exc).__name__})")
            _write_record(record, run_dir, privacy)
            raise UserError(
                f"cannot start command ({type(exc).__name__}); check the executable and --cwd"
            ) from None
        record.warnings.append(f"output finalization failed ({type(exc).__name__})")
    record.ended_at = _now()
    record.duration_seconds = round(time.monotonic() - start, 6)
    record.status = RunStatus.INTERRUPTED if record.exit_code < 0 else RunStatus.COMPLETED
    record.warnings.extend(sorted(output_warnings))
    try:
        _collect(
            record,
            root=root,
            cwd=cwd,
            run_dir=run_dir,
            argv=argv,
            env=env,
            hostname=hostname,
            privacy=privacy,
            manifest=manifest,
            project_rules=project_rules,
            env_capture=env_capture,
            extra_allowlist=extra_allowlist,
            snapshot=snapshot,
            max_bytes=max_bytes,
        )
    except Exception as exc:
        record.warnings.append(f"capture failed ({type(exc).__name__})")
    try:
        return _write_record(record, run_dir, privacy)
    except Exception as exc:
        record.warnings.append(f"run.json finalization failed ({type(exc).__name__})")
        try:
            return _write_record(record, run_dir, privacy)
        except Exception:
            return RunRecord.model_validate(privacy.value(record))
