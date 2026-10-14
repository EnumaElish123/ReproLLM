"""Confirmed writer contracts qualify observations without probing a child."""

from __future__ import annotations

from typing import Literal

from reprollm.schemas.lock import Lock
from reprollm.schemas.run_record import RunRecord
from reprollm.schemas.state import EvidenceContext

# Run and lock were independently checked against their historical writers.
# A declared producer contract is not authentication of a fork's implementation.
RUN_PRODUCERS = frozenset(
    {"0.1.1", "0.4.0", "0.5.0a1", "0.5.0", "0.5.1", "0.5.2", "0.5.3", "0.6.0", "0.6.1", "0.6.2"}
)
LOCK_PRODUCERS = frozenset(
    {"0.1.1", "0.4.0", "0.5.0a1", "0.5.0", "0.5.1", "0.5.2", "0.5.3", "0.6.0", "0.6.1", "0.6.2"}
)


def unknown_context() -> EvidenceContext:
    return EvidenceContext(subject="unknown", phase="unknown")


def run_context(run: RunRecord, path: str) -> EvidenceContext:
    if run.reprollm_version not in RUN_PRODUCERS:
        return unknown_context()
    if path == "environment.python" or path.startswith("environment.packages."):
        return EvidenceContext(subject="recorder", phase="post_child")
    if path == "environment.env_capture" or path.startswith("environment.env."):
        return EvidenceContext(subject="inherited_environment", phase="pre_child")
    if path == "environment.hostname_sha256":
        return EvidenceContext(subject="host", phase="pre_child")
    if path.startswith(("environment.", "hardware.")):
        return EvidenceContext(subject="host", phase="post_child")
    return EvidenceContext(subject="recorder", phase="pre_child")


def lock_context(lock: Lock, path: str) -> EvidenceContext:
    if lock.reprollm_version not in LOCK_PRODUCERS:
        return unknown_context()
    subject: Literal["recorder", "host"] = (
        "recorder"
        if path == "environment.python" or path.startswith("environment.packages.")
        else "host"
    )
    return EvidenceContext(subject=subject, phase="lock_resolution")


def input_context(run: RunRecord, kind: str = "config") -> EvidenceContext:
    """Legacy input bytes have no persisted baseline/consumption contract."""
    if kind == "config" or kind == "file":
        return EvidenceContext(subject="input_file", phase="unknown")
    if run.reprollm_version not in RUN_PRODUCERS:
        return unknown_context()
    subject: Literal["inherited_environment", "recorder"] = (
        "inherited_environment" if kind == "env" else "recorder"
    )
    return EvidenceContext(subject=subject, phase="pre_child")


def context_label(context: EvidenceContext | None) -> str:
    if context is None:
        context = unknown_context()
    return f"{context.subject}/{context.phase}; child unverified"
