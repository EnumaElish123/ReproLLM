"""Hardware capture via nvidia-smi parsing."""

from __future__ import annotations

import csv
import io
import os
import re
import time

from reprollm.core import proc
from reprollm.core.hashing import sha256_text
from reprollm.schemas.run_record import GpuInfo, HardwareInfo

_COMMANDS = (
    ("nvidia-smi", "--query-gpu=index,name,memory.total,uuid", "--format=csv,noheader,nounits"),
    ("nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"),
    ("nvidia-smi",),
)
_CUDA_VERSION = re.compile(r"CUDA Version:\s*([\d.]+)")


def capture_hardware() -> HardwareInfo:
    """Return complete GPU metadata or an explicit unavailable result within five seconds."""
    unavailable = HardwareInfo(cpu_count=os.cpu_count() or 0)
    deadline = time.monotonic() + 5.0
    output: list[str] = []
    try:
        for argv in _COMMANDS:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return unavailable
            result = proc.run_cmd(argv, timeout=remaining)
            if result.returncode != 0:
                return unavailable
            output.append(result.stdout)
        gpus = _parse_gpus(output[0])
        drivers = [line.strip() for line in output[1].splitlines() if line.strip()]
        cuda = _CUDA_VERSION.search(output[2])
        if (
            len(drivers) != len(gpus)
            or len(set(drivers)) != 1
            or re.fullmatch(r"\d+(?:\.\d+)+", drivers[0]) is None
            or cuda is None
        ):
            return unavailable
        return HardwareInfo(
            cpu_count=unavailable.cpu_count,
            gpus=gpus,
            driver=drivers[0],
            cuda_driver_max=cuda.group(1),
            source="nvidia_smi",
        )
    except (OSError, ValueError, csv.Error):
        return unavailable


def _parse_gpus(text: str) -> list[GpuInfo]:
    gpus = []
    seen = set()
    for row in csv.reader(io.StringIO(text), skipinitialspace=True, strict=True):
        if len(row) != 4:
            raise ValueError("invalid GPU metadata columns")
        index, name, memory, uuid = (value.strip() for value in row)
        gpu_index, memory_mib = int(index), int(memory)
        if gpu_index < 0 or memory_mib < 0 or not name or not uuid or gpu_index in seen:
            raise ValueError("invalid GPU metadata values")
        seen.add(gpu_index)
        gpus.append(
            GpuInfo(
                index=gpu_index, name=name, memory_mib=memory_mib, uuid_sha256=sha256_text(uuid)
            )
        )
    if not gpus:
        raise ValueError("no GPU metadata")
    return sorted(gpus, key=lambda gpu: gpu.index)
