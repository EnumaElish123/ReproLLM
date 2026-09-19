"""Scheduler environment capture (SLURM, PBS, LSF)."""

from __future__ import annotations

from collections.abc import Mapping

from reprollm.core.redaction import is_secret_env_name, redact_text
from reprollm.schemas.run_record import SchedulerInfo


def capture_scheduler(env: Mapping[str, str]) -> SchedulerInfo | None:
    """Capture only scheduler namespaces, omitting secret names entirely (§5.1 R-08)."""
    groups = {
        prefix: {
            name: redact_text(env[name])[0]
            for name in sorted(env)
            if name.startswith(prefix) and not is_secret_env_name(name)
        }
        for prefix in ("SLURM_", "PBS_", "LSB_")
    }
    if not any(groups.values()):
        return None
    return SchedulerInfo(
        slurm=groups["SLURM_"] or None,
        pbs=groups["PBS_"] or None,
        lsf=groups["LSB_"] or None,
    )
