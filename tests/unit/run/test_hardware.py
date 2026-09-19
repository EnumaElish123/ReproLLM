"""M5-T02: canned GPU capture and one shared timeout budget."""

import hashlib
from collections.abc import Sequence

import pytest

from reprollm.core import proc
from reprollm.core.proc import NOT_FOUND, TIMEOUT, CmdResult
from reprollm.run import hardware
from tests.conftest import FIXTURES_ROOT, CmdStub

CORPUS = FIXTURES_ROOT / "nvidia_smi"
GPU_QUERY = [
    "nvidia-smi",
    "--query-gpu=index,name,memory.total,uuid",
    "--format=csv,noheader,nounits",
]
DRIVER_QUERY = ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"]


def stub_gpu(stub: CmdStub) -> None:
    stub.on("nvidia-smi", stdout=(CORPUS / "header.txt").read_text())
    stub.on(*GPU_QUERY, stdout=(CORPUS / "query_gpu_2x.csv").read_text())
    stub.on(*DRIVER_QUERY, stdout=(CORPUS / "driver.csv").read_text())


def test_two_gpus_with_hashed_uuids(stub_run_cmd: CmdStub, monkeypatch: pytest.MonkeyPatch) -> None:
    stub_gpu(stub_run_cmd)
    monkeypatch.setattr(hardware.os, "cpu_count", lambda: 32)
    result = hardware.capture_hardware()
    assert result.cpu_count == 32
    assert result.source == "nvidia_smi"
    assert result.driver == "560.35.03"
    assert result.cuda_driver_max == "12.6"
    assert [(g.index, g.name, g.memory_mib) for g in result.gpus] == [
        (0, "NVIDIA H100 80GB HBM3", 81559),
        (1, "NVIDIA H100 80GB HBM3", 81559),
    ]
    for gpu, value in zip(result.gpus, ("GPU-synthetic-one", "GPU-synthetic-two"), strict=True):
        assert gpu.uuid_sha256 == "sha256:" + hashlib.sha256(value.encode()).hexdigest()
        assert value not in result.model_dump_json()
    assert stub_run_cmd.calls == [tuple(GPU_QUERY), tuple(DRIVER_QUERY), ("nvidia-smi",)]


def test_csv_quoting_and_index_order(stub_run_cmd: CmdStub) -> None:
    stub_run_cmd.on("nvidia-smi", stdout=(CORPUS / "header.txt").read_text())
    stub_run_cmd.on(*GPU_QUERY, stdout='1, "GPU, second", 42, b\n0, GPU first, 41, a\n')
    stub_run_cmd.on(*DRIVER_QUERY, stdout=(CORPUS / "driver.csv").read_text())
    captured = hardware.capture_hardware()
    assert captured.source == "nvidia_smi"
    assert [(gpu.index, gpu.name) for gpu in captured.gpus] == [
        (0, "GPU first"),
        (1, "GPU, second"),
    ]


@pytest.mark.parametrize("failure", [NOT_FOUND, TIMEOUT, 1])
def test_gpu_query_failures_are_unavailable(
    failure: int, stub_run_cmd: CmdStub, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(hardware.os, "cpu_count", lambda: None)
    stub_run_cmd.on("nvidia-smi", returncode=failure, stderr=(CORPUS / "missing.txt").read_text())
    result = hardware.capture_hardware()
    assert result.model_dump() == {
        "cpu_count": 0,
        "gpus": [],
        "driver": None,
        "cuda_driver_max": None,
        "source": "unavailable",
    }
    assert len(stub_run_cmd.calls) == 1


@pytest.mark.parametrize(
    "csv",
    [
        "",
        "bad row",
        "x, GPU, 42, uuid",
        "0, GPU, N/A, uuid",
        "0, GPU, 42,",
        "-1, GPU, 42, uuid",
        "0, GPU, -1, uuid",
        "0, , 42, uuid",
        "0, GPU, 42, a\n0, GPU, 42, b",
    ],
)
def test_malformed_gpu_data_does_not_claim_partial_capture(csv: str, stub_run_cmd: CmdStub) -> None:
    stub_gpu(stub_run_cmd)
    # The test stub chooses the first matching prefix; replace the response in place.
    stub_run_cmd._rules = [rule for rule in stub_run_cmd._rules if rule[0] != tuple(GPU_QUERY)]
    stub_run_cmd.on(*GPU_QUERY, stdout=csv)
    result = hardware.capture_hardware()
    assert result.source == "unavailable"
    assert result.gpus == [] and result.driver is None and result.cuda_driver_max is None


@pytest.mark.parametrize("command", [DRIVER_QUERY, ["nvidia-smi"]])
def test_later_command_failure_discards_partial_result(
    command: list[str], stub_run_cmd: CmdStub
) -> None:
    stub_gpu(stub_run_cmd)
    stub_run_cmd._rules = [rule for rule in stub_run_cmd._rules if rule[0] != tuple(command)]
    stub_run_cmd.on(*command, returncode=1)
    assert hardware.capture_hardware().source == "unavailable"


@pytest.mark.parametrize(
    "driver,header",
    [
        ("", "CUDA Version: 12.6"),
        ("a\nb", "CUDA Version: 12.6"),
        ("560.35.03\n560.35.03", "missing CUDA"),
    ],
)
def test_invalid_driver_or_header_is_unavailable(
    driver: str, header: str, stub_run_cmd: CmdStub
) -> None:
    stub_run_cmd.on("nvidia-smi", stdout=header)
    stub_run_cmd.on(*GPU_QUERY, stdout=(CORPUS / "query_gpu_2x.csv").read_text())
    stub_run_cmd.on(*DRIVER_QUERY, stdout=driver)
    assert hardware.capture_hardware().source == "unavailable"


def test_capture_has_one_five_second_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = iter([0.0, 0.0, 3.0, 5.5])
    monkeypatch.setattr(hardware.time, "monotonic", lambda: next(clock))
    timeouts = []

    def command(argv: Sequence[str], *, timeout: float) -> CmdResult:
        timeouts.append(timeout)
        filename = (
            "query_gpu_2x.csv"
            if "--query-gpu=index,name,memory.total,uuid" in argv
            else "driver.csv"
        )
        return CmdResult(0, (CORPUS / filename).read_text(), "")

    monkeypatch.setattr(proc, "run_cmd", command)
    assert hardware.capture_hardware().source == "unavailable"
    assert timeouts == [5.0, 2.0]


def test_os_failure_is_unavailable(stub_run_cmd: CmdStub) -> None:
    stub_run_cmd.raise_on("nvidia-smi", exc=PermissionError("unavailable"))
    assert hardware.capture_hardware().source == "unavailable"
