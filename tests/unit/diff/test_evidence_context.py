"""Recorded metadata keeps its actual subject and phase through State projection."""

from __future__ import annotations

import pytest

from reprollm.schemas.lock import Lock
from reprollm.schemas.run_record import CommandInfo, RunEnvironment, RunRecord, RunStatus
from reprollm.schemas.state import State


def record(version: str = "0.6.1") -> RunRecord:
    return RunRecord(
        reprollm_version=version,
        run_id="20261014T010000Z-abcdef",
        status=RunStatus.COMPLETED,
        command=CommandInfo(argv=["python"], cwd="."),
        environment=RunEnvironment(
            os="Linux",
            platform="linux",
            python="3.12",
            hostname_sha256="sha256:host",
            packages={"torch": "2.8.0"},
            env={"OMP_NUM_THREADS": "2"},
        ),
    )


@pytest.mark.parametrize(
    ("path", "subject", "phase"),
    [
        ("environment.python", "recorder", "post_child"),
        ("environment.packages.torch", "recorder", "post_child"),
        ("environment.platform", "host", "post_child"),
        ("environment.hostname_sha256", "host", "pre_child"),
        ("environment.env.OMP_NUM_THREADS", "inherited_environment", "pre_child"),
    ],
)
def test_known_run_context_survives_roundtrip(path: str, subject: str, phase: str) -> None:
    state = State.from_run(record())
    restored = State.model_validate_json(state.model_dump_json())
    for projected in (state, restored, State.merge(run=restored)):
        context = projected.flatten()[path].context
        assert context is not None
        assert (context.subject, context.phase, context.verification) == (
            subject,
            phase,
            "unverified",
        )


@pytest.mark.parametrize("version", ["0.3.0", "0.6.1+custom", "9.0.0", "unknown"])
def test_unregistered_producer_keeps_values_with_unknown_context(version: str) -> None:
    leaf = State.from_run(record(version)).flatten()["environment.packages.torch"]
    assert leaf.value == "2.8.0"
    assert leaf.context is not None
    assert (leaf.context.subject, leaf.context.phase) == ("unknown", "unknown")


def test_lock_context_is_resolution_recorder_not_runtime_child() -> None:
    lock = Lock.model_validate(
        {
            "reprollm_version": "0.6.1",
            "manifest_sha256": "sha256:manifest",
            "generated_at": "2026-10-14T01:00:00Z",
            "resolution": {"mode": "offline"},
            "environment": {
                "python": "3.12",
                "platform": "linux",
                "packages": {"torch": "2.8.0"},
                "gpu": {"source": "unavailable"},
            },
        }
    )
    leaf = State.from_lock(lock).flatten()["environment.packages.torch"]
    assert leaf.context is not None
    assert (leaf.context.subject, leaf.context.phase, leaf.context.verification) == (
        "recorder",
        "lock_resolution",
        "unverified",
    )
