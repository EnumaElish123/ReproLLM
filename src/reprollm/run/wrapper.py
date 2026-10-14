"""Subprocess wrapper that preserves scoped runtime evidence (spec §5.1)."""

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

import yaml

from reprollm import __version__
from reprollm.core import envinfo, proc
from reprollm.core.errors import UserError
from reprollm.core.git import inspect_git
from reprollm.core.hashing import sha256_bytes
from reprollm.core.paths import MANIFEST, PROJECT_RULES, RUNS_DIR, resolve_project_file
from reprollm.core.persistence import redact_keyed_values
from reprollm.core.redaction import redact_env, redact_lines
from reprollm.core.yaml_io import parse_manifest_text
from reprollm.run.capture import collect_outputs
from reprollm.run.contextual_text import CaptureLineContext, shield_contextual_keys
from reprollm.run.hardware import capture_hardware
from reprollm.run.input_capture import capture_inputs, recheck_inputs
from reprollm.run.privacy import RunPrivacy
from reprollm.run.slurm import capture_scheduler
from reprollm.schemas.manifest import Manifest
from reprollm.schemas.project_rules import ProjectRules
from reprollm.schemas.run_record import (
    CodeInfo,
    CommandInfo,
    InputCapture,
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
    _save_record(safe, run_dir)
    return safe


def _save_record(safe: RunRecord, run_dir: Path) -> None:
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


def _safe_load(
    root: Path,
) -> tuple[Manifest | None, ProjectRules | None, dict[str, bytes | None]]:
    manifest = None
    rules = None
    document_data: dict[str, bytes | None] = {MANIFEST: None, PROJECT_RULES: None}
    for name in (MANIFEST, PROJECT_RULES):
        path = root / name
        if not path.exists() and not path.is_symlink():
            continue
        resolved = resolve_project_file(root, name)
        if resolved is None:
            raise UserError(f"{name} must be a readable file inside the repository")
        try:
            data = resolved.read_bytes()
            document_data[name] = data
            if name == MANIFEST:
                manifest = parse_manifest_text(data.decode("utf-8"))
            else:
                rules = ProjectRules.model_validate(yaml.safe_load(data.decode("utf-8")) or {})
        except (OSError, UserError, ValueError, yaml.YAMLError) as exc:
            raise UserError(
                f"cannot load {name} ({type(exc).__name__}); validate its contents"
            ) from None
    return manifest, rules, document_data


def _tee(
    source: TextIO,
    terminal: TextIO,
    log: TextIO,
    privacy: RunPrivacy,
    warnings: list[str],
    label: str,
) -> None:
    originals: dict[str, str] = {}
    context = CaptureLineContext()
    keys: tuple[str, ...] = ()

    def echo(value: str) -> None:
        try:
            terminal.write(value)
            terminal.flush()
        except (OSError, ValueError):
            pass

    def echoed() -> Iterator[str]:
        nonlocal originals, keys
        for line in source:
            echo(line)
            keys = context.keys(line)
            protected, originals, _ = shield_contextual_keys(line)
            yield protected
            originals.clear()

    try:
        for line in redact_lines(echoed()):
            for marker, original in originals.items():
                line = line.replace(marker, original)
            log.write(privacy.text(line, keys=keys)[0])
            log.flush()
    except Exception as exc:
        warnings.append(f"{label} capture failed ({type(exc).__name__})")
        try:
            while chunk := source.read(8192):
                echo(chunk)
        except (OSError, ValueError) as error:
            warnings.append(f"{label} drain failed ({type(error).__name__})")
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


def _collect(
    record: RunRecord,
    *,
    root: Path,
    run_dir: Path,
    env: dict[str, str],
    hostname: str,
    privacy: RunPrivacy,
    manifest: Manifest | None,
    env_capture: Literal["allowlist", "all"],
    extra_allowlist: Sequence[str],
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
    manifest, project_rules, document_data = _safe_load(root)
    hostname, username = socket.gethostname(), getpass.getuser()
    privacy = RunPrivacy(root, hostname=hostname, username=username)
    command, redactions = [], 0
    try:
        for index, token in enumerate(argv):
            if index == 0 and Path(token).is_absolute():
                token = Path(token).name
            context = (argv[index - 1],) if index and argv[index - 1].startswith("-") else ()
            keyed = str(redact_keyed_values(token, context))
            safe, count = privacy.text(keyed)
            command.append(safe)
            redactions += count + (keyed != token)
    except Exception as exc:
        raise UserError(
            f"cannot sanitize recorded command ({type(exc).__name__}); simplify command arguments"
        ) from None
    record = RunRecord(
        schema_version=2,
        input_capture=InputCapture(),
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
        safe_base = _write_record(record, run_dir, privacy)
    except Exception as exc:
        raise UserError(
            f"cannot write run.json ({type(exc).__name__}); check run directory permissions"
        ) from None
    env = dict(os.environ)
    try:
        capture_inputs(
            record,
            root=root,
            cwd=cwd,
            run_dir=run_dir,
            argv=argv,
            env=env,
            privacy=privacy,
            manifest=manifest,
            project_rules=project_rules,
            snapshot=snapshot,
            max_bytes=max_bytes,
            document_data=document_data,
        )
        _write_record(record, run_dir, privacy)
    except Exception as exc:
        record.warnings.append(f"input baseline capture failed ({type(exc).__name__})")
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
            try:
                _write_record(record, run_dir, privacy)
            except Exception as error:
                minimal = safe_base.model_copy(deep=True)
                minimal.status = record.status
                minimal.ended_at = record.ended_at
                minimal.warnings.append(f"command start failed ({type(exc).__name__})")
                minimal.warnings.append(f"capture finalization failed ({type(error).__name__})")
                with suppress(Exception):
                    _save_record(minimal, run_dir)
            raise UserError(
                f"cannot start command ({type(exc).__name__}); check the executable and --cwd"
            ) from None
        record.warnings.append(f"output finalization failed ({type(exc).__name__})")
    record.ended_at = _now()
    record.duration_seconds = round(time.monotonic() - start, 6)
    record.status = RunStatus.INTERRUPTED if record.exit_code < 0 else RunStatus.COMPLETED
    record.warnings.extend(sorted(output_warnings))
    try:
        recheck_inputs(record, root=root)
    except Exception as exc:
        record.warnings.append(f"input final recheck failed ({type(exc).__name__})")
    try:
        _collect(
            record,
            root=root,
            run_dir=run_dir,
            env=env,
            hostname=hostname,
            privacy=privacy,
            manifest=manifest,
            env_capture=env_capture,
            extra_allowlist=extra_allowlist,
        )
    except Exception as exc:
        record.warnings.append(f"capture failed ({type(exc).__name__})")
    try:
        return _write_record(record, run_dir, privacy)
    except Exception as exc:
        record.warnings.append(f"run.json finalization failed ({type(exc).__name__})")
        try:
            return _write_record(record, run_dir, privacy)
        except Exception as error:
            minimal = safe_base.model_copy(deep=True)
            minimal.exit_code = record.exit_code
            minimal.status = record.status
            minimal.ended_at = record.ended_at
            minimal.duration_seconds = record.duration_seconds
            minimal.warnings.append(f"capture finalization failed ({type(error).__name__})")
            try:
                _save_record(minimal, run_dir)
            except Exception as write_error:
                minimal.warnings.append(
                    f"run.json finalization failed ({type(write_error).__name__})"
                )
            return minimal
