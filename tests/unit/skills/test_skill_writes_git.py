"""Native Git observations keep initialization's scientific input view stable."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytest
from tests.conftest import commit_all, make_git_repo, run_git

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/reprollm/scripts"))
import skill_runtime as runtime  # noqa: E402
from skill_request import Grants, Reply, Request  # noqa: E402
from skill_writes import execute_write  # noqa: E402


def _project(path: Path) -> Path:
    root = make_git_repo(path)
    (root / "README.md").write_bytes(b"Public reproducibility fixture.\n")
    commit_all(root)
    return root


def _stale_stat(root: Path) -> None:
    path = root / "README.md"
    original = path.read_bytes()
    info = path.stat()
    os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns + 2_000_000_000))
    assert path.read_bytes() == original


def _init(
    root: Path, state: Path, *, preview: bool = False, profiles: list[str] | None = None
) -> Reply:
    return execute_write(
        Request(
            "init",
            str(root),
            {"profiles": ["inference"] if profiles is None else profiles, "preview": preview},
            Grants(write=True),
        ),
        root=root,
        state_home=state,
        identity="real-git-initialization-regression",
        cli_runner=runtime.invoke_cli,
        source_signature=runtime.input_signature,
    )


@pytest.mark.parametrize("prior", [None, "1"])
def test_init_with_stale_git_stat_cache_matches_native_artifact_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, prior: str | None
) -> None:
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    if prior is None:
        monkeypatch.delenv("GIT_OPTIONAL_LOCKS", raising=False)
    else:
        monkeypatch.setenv("GIT_OPTIONAL_LOCKS", prior)
    root = _project(tmp_path / "skill" / "experiment")
    reference = tmp_path / "native" / "experiment"
    shutil.copytree(root, reference)
    _stale_stat(root)
    _stale_stat(reference)
    source = (root / "README.md").read_bytes()
    index = (root / ".git/index").read_bytes()
    index_mtime = (root / ".git/index").stat().st_mtime_ns
    stage = run_git(root, "ls-files", "--stage", "-z").stdout

    reply = _init(root, tmp_path / "state")

    assert reply.invocation == "handled_result" and reply.cli_exit_code == 0, reply.as_dict()
    assert reply.data["phase"] == "applied"
    assert (root / ".git/index").read_bytes() == index
    assert (root / ".git/index").stat().st_mtime_ns == index_mtime
    assert run_git(root, "ls-files", "--stage", "-z").stdout == stage
    assert (root / "README.md").read_bytes() == source
    assert os.environ.get("GIT_OPTIONAL_LOCKS") == prior

    expected = runtime.invoke_cli(["init", ".", "--profiles", "inference"], reference)
    assert expected.exit_code == 0, expected.stderr
    for path in ("reprollm.yaml", ".reprollm/config.yaml", ".reprollm/project-rules.yaml"):
        assert (root / path).read_bytes() == (reference / path).read_bytes()


@pytest.mark.parametrize("race", ["staging", "content", "index_flag"])
def test_init_keeps_rejecting_real_input_and_index_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, race: str
) -> None:
    from reprollm.core import manifest_scaffold

    monkeypatch.setenv("GIT_OPTIONAL_LOCKS", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    root = _project(tmp_path / "experiment")
    path = root / "README.md"
    if race == "staging":
        path.write_bytes(b"Public already-unstaged fixture value.\n")
    content = path.read_bytes()
    staged = run_git(root, "ls-files", "-v", "--stage", "-z").stdout
    original = manifest_scaffold.plan_init
    changed_stage = []

    def concurrent_change(
        target: Path, *, profiles_override: list[str] | None
    ) -> manifest_scaffold.InitPlan:
        result = original(target, profiles_override=profiles_override)
        assert os.environ.get("GIT_OPTIONAL_LOCKS") == "0"
        if race == "staging":
            run_git(target, "add", "README.md")
        elif race == "index_flag":
            run_git(target, "update-index", "--assume-unchanged", "README.md")
        else:
            path.write_bytes(b"Public concurrently edited fixture value.\n")
        changed_stage.append(run_git(root, "ls-files", "-v", "--stage", "-z").stdout)
        return result

    monkeypatch.setattr(manifest_scaffold, "plan_init", concurrent_change)
    reply = _init(root, tmp_path / "state", preview=True)

    assert reply.invocation == "blocked"
    assert any(d["code"] == "write_inputs_changed_during_prepare" for d in reply.diagnostics)
    assert not (root / "reprollm.yaml").exists() and not (root / ".reprollm").exists()
    assert os.environ.get("GIT_OPTIONAL_LOCKS") == "1"
    if race == "content":
        assert path.read_bytes() == b"Public concurrently edited fixture value.\n"
    else:
        assert path.read_bytes() == content
        actual_stage = run_git(root, "ls-files", "-v", "--stage", "-z").stdout
        assert actual_stage == changed_stage[0] and actual_stage != staged


@pytest.mark.parametrize("prior", [None, "1"])
def test_init_native_error_restores_original_git_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, prior: str | None
) -> None:
    from reprollm.core import manifest_scaffold

    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    if prior is None:
        monkeypatch.delenv("GIT_OPTIONAL_LOCKS", raising=False)
    else:
        monkeypatch.setenv("GIT_OPTIONAL_LOCKS", prior)
    root = _project(tmp_path / "experiment")
    _stale_stat(root)
    original = manifest_scaffold.plan_init
    observed = []

    def observe(target: Path, *, profiles_override: list[str] | None) -> manifest_scaffold.InitPlan:
        observed.append(os.environ.get("GIT_OPTIONAL_LOCKS"))
        return original(target, profiles_override=profiles_override)

    monkeypatch.setattr(manifest_scaffold, "plan_init", observe)
    reply = _init(root, tmp_path / "state", preview=True, profiles=["not-a-profile"])

    assert reply.invocation == "user_error" and reply.cli_exit_code == 2
    assert observed == ["0"]
    assert os.environ.get("GIT_OPTIONAL_LOCKS") == prior
    assert not (root / "reprollm.yaml").exists() and not (root / ".reprollm").exists()
