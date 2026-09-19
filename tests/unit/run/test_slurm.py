"""M5-T02 scheduler namespace and secret boundaries."""

from reprollm.run import slurm


def test_scheduler_namespaces_are_sorted_and_secret_names_are_omitted() -> None:
    captured = slurm.capture_scheduler(
        {
            "SLURM_NNODES": "2",
            "SLURM_JOB_ID": "123",
            "SLURM_JOB_ACCOUNT_TOKEN": "hidden",
            "PBS_JOBID": "456",
            "PBS_AUTH": "hidden",
            "LSB_JOBID": "789",
            "LSB_NAME": "hf_01234567890123456789",
            "PATH": "/not/scheduler",
            "OTHER": "private",
        }
    )
    assert captured is not None
    assert captured.model_dump() == {
        "slurm": {"SLURM_JOB_ID": "123", "SLURM_NNODES": "2"},
        "pbs": {"PBS_JOBID": "456"},
        "lsf": {"LSB_JOBID": "789", "LSB_NAME": "<REDACTED:huggingface>"},
    }
    assert list(captured.slurm or {}) == ["SLURM_JOB_ID", "SLURM_NNODES"]


def test_no_scheduler_or_only_secret_values_produces_no_scheduler() -> None:
    assert slurm.capture_scheduler({}) is None
    assert slurm.capture_scheduler({"PATH": "value", "SLURM_TOKEN": "hidden"}) is None
    result = slurm.capture_scheduler({"SLURM_JOB_ID": "123"})
    assert result is not None and result.pbs is None and result.lsf is None
