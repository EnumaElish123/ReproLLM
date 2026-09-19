"""M6-T02 severity policy: independently listed normative rows and edge cases."""

from __future__ import annotations

import pytest

from reprollm.diff.severity import SeverityResolver, matches

CASES = [
    ("models.primary.id", "HIGH"),
    ("models.judge.revision", "HIGH"),
    ("models.primary.tokenizer.revision", "HIGH"),
    ("models.primary.chat_template.sha256", "HIGH"),
    ("models.primary.quantization", "HIGH"),
    ("models.primary.adapter.rank", "HIGH"),
    ("models.primary.dtype", "MEDIUM"),
    ("models.judge.pinnability", "MEDIUM"),
    ("datasets.eval.id", "HIGH"),
    ("datasets.eval.revision", "HIGH"),
    ("datasets.eval.subset", "HIGH"),
    ("datasets.eval.split", "HIGH"),
    ("datasets.eval.sampling.seed", "HIGH"),
    ("datasets.eval.preprocessing.script", "MEDIUM_HIGH"),
    ("prompts.system.sha256", "HIGH"),
    ("prompts.judge.text_sha256", "HIGH"),
    ("generation.temperature", "HIGH"),
    ("inference.backend", "HIGH"),
    ("inference.version", "MEDIUM_HIGH"),
    ("inference.quantization", "HIGH"),
    ("inference.dtype", "MEDIUM"),
    ("inference.tensor_parallel_size", "MEDIUM"),
    ("inference.max_model_len", "MEDIUM"),
    ("inference.gpu_memory_utilization", "LOW"),
    ("training.learning_rate", "HIGH"),
    ("evaluation.judge.model_ref", "HIGH"),
    ("evaluation.metrics", "HIGH"),
    ("evaluation.definitions.asr", "HIGH"),
    ("evaluation.aggregation", "MEDIUM_HIGH"),
    ("privacy.threat_model", "HIGH"),
    ("custom.alpha", "MEDIUM"),
    ("files.configs/eval.v2.yaml.sha256", "HIGH"),
    ("environment.packages.torch", "MEDIUM_HIGH"),
    ("environment.packages.transformers", "MEDIUM_HIGH"),
    ("environment.packages.vllm", "MEDIUM_HIGH"),
    ("environment.packages.tokenizers", "MEDIUM_HIGH"),
    ("environment.packages.other", "MEDIUM"),
    ("environment.python", "MEDIUM"),
    ("environment.platform", "MEDIUM"),
    ("hardware.gpus.0.name", "MEDIUM"),
    ("hardware.driver", "LOW"),
    ("hardware.cuda_driver_max", "MEDIUM"),
    ("code.commit", "MEDIUM"),
    ("code.dirty", "HIGH"),
    ("code.branch", "LOW"),
    ("command.argv", "MEDIUM"),
    ("run_id", "NONE"),
    ("started_at", "NONE"),
    ("ended_at", "NONE"),
    ("duration_seconds", "NONE"),
    ("environment.hostname_sha256", "NONE"),
]


@pytest.mark.parametrize(("path", "severity"), CASES)
@pytest.mark.parametrize(("a", "b"), [("before", "after"), (None, "added"), ("removed", None)])
def test_every_normative_row(path: str, severity: str, a: object, b: object) -> None:
    assert SeverityResolver().resolve(path, a, b).severity == severity


@pytest.mark.parametrize(
    ("path", "a", "b", "severity"),
    [
        ("environment.packages.torch", "2.8.0", "2.8.1", "MEDIUM"),
        ("environment.packages.torch", "2.8.0", "2.9.0", "MEDIUM_HIGH"),
        ("environment.packages.torch", "2.8.0", "3.0.0", "MEDIUM_HIGH"),
        ("environment.packages.vllm", "0.10.0", "0.11.0", "MEDIUM_HIGH"),
        ("environment.packages.vllm", "0.10.0", "0.10.1", "MEDIUM"),
        ("environment.packages.other", "1.2.0", "1.2.1", "LOW"),
        ("inference.version", "0.10.0rc1", "0.10.0rc2", "MEDIUM"),
        ("inference.version", "0.10.0", "0.10.0+local", "MEDIUM"),
        ("inference.version", "0.10.0", "0.10.0.post1", "MEDIUM"),
        ("inference.version", "0.10.0", "1!0.10.0", "MEDIUM_HIGH"),
        ("inference.version", "unknown", "0.10.1", "MEDIUM_HIGH"),
        ("inference.version", None, "0.10.1", "MEDIUM_HIGH"),
        ("environment.python", "3.12.1", "3.12.2", "MEDIUM"),
    ],
)
def test_version_components(path: str, a: object, b: object, severity: str) -> None:
    # Spec §18.1 wins over M6's contradictory LOW example for torch patch drift.
    assert SeverityResolver().resolve(path, a, b).severity == severity


@pytest.mark.parametrize(
    ("a", "b", "severity", "note"),
    [
        (False, False, "MEDIUM", "code changed"),
        (True, False, "HIGH", "working tree was dirty on a"),
        (False, True, "HIGH", "working tree was dirty on b"),
        (True, True, "HIGH", "working tree was dirty on both"),
    ],
)
def test_dirty_commits(a: bool, b: bool, severity: str, note: str) -> None:
    found = SeverityResolver().resolve("code.commit", "aaa", "bbb", dirty_a=a, dirty_b=b)
    assert (found.severity, found.note) == (severity, note)


def test_profiles_precede_table_and_matching_is_first_wins() -> None:
    resolver = SeverityResolver(
        profile_overrides={"generation.*": "LOW", "generation.seed": "HIGH"}
    )
    assert resolver.resolve("generation.seed", 1, 2).severity == "LOW"
    assert resolver.resolve("not.in.table", 1, 2).severity == "MEDIUM"
    for declared, expected in [
        ("HIGH", "MEDIUM_HIGH"),
        ("MEDIUM_HIGH", "MEDIUM"),
        ("MEDIUM", "LOW"),
        ("LOW", "LOW"),
        ("NONE", "NONE"),
    ]:
        resolver = SeverityResolver(profile_overrides={"inference.version": declared})
        assert resolver.resolve("inference.version", "1.2.0", "1.2.1").severity == expected


@pytest.mark.parametrize(
    ("pattern", "path", "expected"),
    [
        ("generation.*", "generation.seed", True),
        ("generation.*", "generation.params.seed", False),
        ("models.*.adapter.*", "models.primary.adapter.rank", True),
        ("models.*.adapter.*", "models.primary.adapter.params.rank", False),
        ("files.*.sha256", "files.configs/eval.v2.yaml.sha256", True),
        ("files.*.sha256", "files.configs/eval.v2.yaml.size_bytes", False),
        ("files.configs/eval.v2.yaml.sha256", "files.configs/evalXv2.yaml.sha256", False),
        ("files.*.sha256", "files..sha256", False),
    ],
)
def test_single_segment_globs(pattern: str, path: str, expected: bool) -> None:
    assert matches(pattern, path) is expected
