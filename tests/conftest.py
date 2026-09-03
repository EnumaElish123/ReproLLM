"""Shared test infrastructure (spec §22).

- session-wide ``respx`` guard: any unmocked HTTP request fails the suite (T-04)
- ``stub_run_cmd``: canned ``CmdResult`` responses for git / nvidia-smi (T-05)
- ``materialize_repo``: golden fixture repositories with deterministic commit
  SHAs (T-03) — fixed identity, dates, and isolated git config
- ``assert_json_snapshot``: golden-output comparison with REPROLLM_UPDATE_SNAPSHOTS
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
import respx
import yaml

from reprollm.core import proc
from reprollm.core.proc import CmdResult

FIXTURES_ROOT = Path(__file__).resolve().parent / "fixtures"

#: Fields ignored by default when comparing snapshots (spec §22 T-02).
SNAPSHOT_IGNORE: tuple[str, ...] = (
    "generated_at",
    "reprollm_version",
    "resolved_at",
    "observed_at",
)

#: Fixed identity/dates so fixture commits are byte-deterministic (spec §22 T-03).
GIT_TEST_ENV: Mapping[str, str] = {
    "GIT_AUTHOR_NAME": "ReproLLM Test",
    "GIT_AUTHOR_EMAIL": "test@reprollm.dev",
    "GIT_COMMITTER_NAME": "ReproLLM Test",
    "GIT_COMMITTER_EMAIL": "test@reprollm.dev",
    "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
    "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z",
}

#: Isolate from the developer's global/system git config (hooks, signing, autocrlf).
#: os.devnull works on POSIX ("/dev/null") and Windows ("nul").
_GIT_ISOLATION: dict[str, str] = {
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
}


# ---------------------------------------------------------------------------
# Network guard (T-04)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True, scope="session")
def _clean_proxy_env() -> Iterator[None]:
    """Drop proxy env vars: tests never touch the network (T-04) and a local
    SOCKS proxy would make unmocked calls fail for the wrong reason."""
    keys = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")
    saved = {key: os.environ.pop(key) for key in keys if key in os.environ}
    yield
    os.environ.update(saved)


@pytest.fixture(autouse=True, scope="session")
def fail_unmocked_http() -> Iterator[None]:
    # Bare ``respx.mock`` activates the *global* router so tests can register
    # routes with the module-level API (``respx.get(...)``); its default
    # ``assert_all_mocked`` makes any unmocked request fail the suite (T-04).
    with respx.mock:
        yield


# ---------------------------------------------------------------------------
# git helpers
# ---------------------------------------------------------------------------


def _git_env() -> dict[str, str]:
    return {**os.environ, **GIT_TEST_ENV, **_GIT_ISOLATION}


def run_git(cwd: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        check=True,
        env=_git_env(),
    )


def make_git_repo(path: Path, *, branch: str = "main") -> Path:
    """Create an empty git repository on ``branch`` (works on git < 2.28)."""
    path.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, **_GIT_ISOLATION}
    subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True, env=env)
    subprocess.run(
        ["git", "symbolic-ref", "HEAD", f"refs/heads/{branch}"],
        cwd=path,
        capture_output=True,
        check=True,
        env=env,
    )
    return path


def commit_all(repo: Path, message: str = "fixture") -> str:
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "--allow-empty", "-m", message)
    return run_git(repo, "rev-parse", "HEAD").stdout.decode().strip()


# ---------------------------------------------------------------------------
# run_cmd stub (T-05)
# ---------------------------------------------------------------------------


@dataclass
class CmdStub:
    """Replaces ``reprollm.core.proc.run_cmd``; returns canned CmdResults.

    Register with :meth:`on` by argv prefix (longest prefix wins). Any call
    matching no rule raises ``AssertionError`` — tests must not shell out.
    """

    calls: list[tuple[str, ...]] = field(default_factory=list)
    _rules: list[tuple[tuple[str, ...], CmdResult | Exception]] = field(default_factory=list)

    def on(
        self,
        *prefix: str,
        returncode: int = 0,
        stdout: str = "",
        stderr: str = "",
    ) -> CmdStub:
        self._rules.append((prefix, CmdResult(returncode, stdout, stderr)))
        return self

    def raise_on(self, *prefix: str, exc: Exception) -> CmdStub:
        self._rules.append((prefix, exc))
        return self

    def __call__(
        self,
        argv: Sequence[str],
        *,
        cwd: Path | None = None,
        timeout: float = 30,
        env: Mapping[str, str] | None = None,
    ) -> CmdResult:
        del cwd, timeout, env
        key = tuple(argv)
        self.calls.append(key)
        match: tuple[tuple[str, ...], CmdResult | Exception] | None = None
        for rule in self._rules:
            prefix = rule[0]
            if key[: len(prefix)] == prefix and (match is None or len(prefix) > len(match[0])):
                match = rule
        if match is None:
            raise AssertionError(f"unmocked run_cmd call: {list(argv)}")
        if isinstance(match[1], Exception):
            raise match[1]
        return match[1]


@pytest.fixture
def stub_run_cmd(monkeypatch: pytest.MonkeyPatch) -> Iterator[CmdStub]:
    stub = CmdStub()
    monkeypatch.setattr(proc, "run_cmd", stub)
    yield stub


# ---------------------------------------------------------------------------
# Golden fixture repositories (T-02, T-03)
# ---------------------------------------------------------------------------


def materialize_repo(
    name: str,
    dest: Path,
    *,
    manifest: str | None = None,
) -> Path:
    """Copy ``tests/fixtures/repos/<name>/tree`` to ``dest/<name>`` and turn it
    into a git repository with deterministic SHAs (when ``fixture.yaml`` says so).

    ``manifest`` optionally copies ``manifests/<manifest>.yaml`` to
    ``reprollm.yaml`` before committing (used from M3 for Level 1 fixtures).
    """
    source = FIXTURES_ROOT / "repos" / name
    tree = source / "tree"
    if not tree.is_dir():
        raise FileNotFoundError(f"unknown fixture repo: {source}")
    repo = dest / name
    shutil.copytree(tree, repo)

    if manifest is not None:
        manifest_src = source / "manifests" / f"{manifest}.yaml"
        shutil.copyfile(manifest_src, repo / "reprollm.yaml")

    meta: dict[str, Any] = {}
    meta_path = source / "fixture.yaml"
    if meta_path.is_file():
        loaded = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
        if loaded is not None:
            meta = loaded

    if meta.get("git", True):
        make_git_repo(repo)
        commit_all(repo)

    for op in meta.get("post_commit", []):
        _apply_post_commit(repo, op)
    return repo


def _apply_post_commit(repo: Path, op: Mapping[str, Any]) -> None:
    target = repo / str(op["path"])
    kind = op["op"]
    content = str(op.get("content", ""))
    if kind == "write":
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    elif kind == "append":
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as handle:
            handle.write(content)
    elif kind == "delete":
        target.unlink(missing_ok=True)
    else:
        raise ValueError(f"unknown post_commit op {kind!r} in fixture")


@pytest.fixture
def materialize(tmp_path: Path) -> Callable[..., Path]:
    def _make(name: str, *, manifest: str | None = None) -> Path:
        return materialize_repo(name, tmp_path, manifest=manifest)

    return _make


# ---------------------------------------------------------------------------
# Snapshot assertion (T-02)
# ---------------------------------------------------------------------------


def _strip_ignored(obj: Any, ignore: Sequence[str]) -> Any:
    if isinstance(obj, dict):
        return {k: _strip_ignored(v, ignore) for k, v in obj.items() if k not in ignore}
    if isinstance(obj, list):
        return [_strip_ignored(item, ignore) for item in obj]
    return obj


def assert_json_snapshot(
    actual: Any,
    expected_path: Path,
    ignore: Sequence[str] = SNAPSHOT_IGNORE,
) -> None:
    """Compare ``actual`` against a golden JSON file, ignoring volatile fields.

    Set ``REPROLLM_UPDATE_SNAPSHOTS=1`` to (re)write the golden file with the
    *cleaned* actual value; review the diff before committing (AGENTS.md §6).
    """
    cleaned = _strip_ignored(actual, ignore)
    if os.environ.get("REPROLLM_UPDATE_SNAPSHOTS") == "1":
        expected_path.parent.mkdir(parents=True, exist_ok=True)
        expected_path.write_text(
            json.dumps(cleaned, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return
    if not expected_path.exists():
        raise AssertionError(
            f"snapshot missing: {expected_path} "
            "(run once with REPROLLM_UPDATE_SNAPSHOTS=1 and review the result)"
        )
    expected = _strip_ignored(json.loads(expected_path.read_text(encoding="utf-8")), ignore)
    assert cleaned == expected, f"snapshot mismatch: {expected_path}"


# ---------------------------------------------------------------------------
# Plain fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """An empty git repository on ``main``."""
    return make_git_repo(tmp_path / "repo")


def _ensure_importable() -> None:
    """Allow ``from tests.conftest import ...`` regardless of invocation dir."""
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


_ensure_importable()
