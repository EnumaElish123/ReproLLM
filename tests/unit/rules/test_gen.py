"""M3-T03: generation and inference declaration acceptance cases."""

from pathlib import Path

import pytest

from reprollm.core.context import AuditContext
from reprollm.core.engine import run_audit
from reprollm.core.yaml_io import dump_yaml
from reprollm.profiles.loader import resolve
from reprollm.rules.gen import (
    BackendConfigDeclaredRule,
    BackendDeclaredRule,
    ParamsDeclaredRule,
    SeedDeclaredRule,
    StopDeclaredRule,
)
from reprollm.schemas.finding import FindingStatus, Severity
from tests.conftest import materialize_repo
from tests.unit.rules.helpers import context, failures


@pytest.mark.parametrize(
    "rule_type",
    [
        BackendConfigDeclaredRule,
        BackendDeclaredRule,
        ParamsDeclaredRule,
        SeedDeclaredRule,
        StopDeclaredRule,
    ],
)
def test_no_manifest_skips_generation(tmp_path: Path, rule_type) -> None:
    assert rule_type.min_level == 1
    assert not rule_type().applies(AuditContext(tmp_path))


def test_params_missing_fields_aggregated(tmp_path: Path) -> None:
    result = failures(ParamsDeclaredRule().check(context(tmp_path, generation={"temperature": 0})))
    assert len(result) == 1 and result[0].severity == Severity.WARNING
    assert {e.field for e in result[0].evidence} == {"generation.top_p", "generation.max_tokens"}
    assert "generation.top_p" in result[0].message
    assert "generation.max_tokens" in result[0].message
    assert "temperature" not in result[0].message
    full = context(tmp_path, generation={"temperature": 0, "top_p": 1, "max_tokens": 1})
    assert not failures(ParamsDeclaredRule().check(full))


def test_missing_generation_section_reports_all_required_parameters(tmp_path: Path) -> None:
    result = failures(ParamsDeclaredRule().check(context(tmp_path)))
    assert len(result) == 1
    assert {e.field for e in result[0].evidence} == {
        "generation.temperature",
        "generation.top_p",
        "generation.max_tokens",
    }


@pytest.mark.parametrize(
    "generation,applies",
    [
        (None, False),
        ({}, False),
        ({"temperature": 0}, False),
        ({"do_sample": False}, False),
        ({"temperature": 0.7}, True),
        ({"temperature": 0, "do_sample": True}, True),
        ({"do_sample": True}, True),
        ({"temperature": 0.7, "do_sample": False}, True),
    ],
)
def test_sampling_seed_condition(tmp_path: Path, generation, applies: bool) -> None:
    ctx = context(tmp_path, generation=generation)
    assert SeedDeclaredRule().applies(ctx) is applies
    if applies:
        assert failures(SeedDeclaredRule().check(ctx))[0].severity == Severity.WARNING


def test_generation_seed_zero_and_other_sections(tmp_path: Path) -> None:
    rule = SeedDeclaredRule()
    assert not failures(rule.check(context(tmp_path, generation={"temperature": 1, "seed": 0})))
    result = failures(
        rule.check(
            context(
                tmp_path, generation={"temperature": 1}, execution={"seed": 0}, training={"seed": 0}
            )
        )
    )
    assert result[0].evidence[0].field == "generation.seed"


@pytest.mark.parametrize("inference", [None, {}])
def test_backend_missing(tmp_path: Path, inference) -> None:
    result = failures(BackendDeclaredRule().check(context(tmp_path, inference=inference)))
    assert result[0].evidence[0].field == "inference.backend"
    assert result[0].severity == Severity.WARNING


@pytest.mark.parametrize("backend", ["vllm", "transformers", "sglang", "openai", "other"])
def test_declared_backend_passes(tmp_path: Path, backend: str) -> None:
    assert not failures(
        BackendDeclaredRule().check(context(tmp_path, inference={"backend": backend}))
    )


@pytest.mark.parametrize("backend", [None, "transformers", "sglang", "openai", "other"])
def test_non_vllm_skips_backend_config(tmp_path: Path, backend) -> None:
    assert not BackendConfigDeclaredRule().applies(
        context(tmp_path, inference={"backend": backend})
    )


def test_vllm_config_reports_each_missing_field_without_model_fallback(tmp_path: Path) -> None:
    rule = BackendConfigDeclaredRule()
    ctx = context(
        tmp_path,
        inference={"backend": "vllm"},
        models={"primary": {"dtype": "bfloat16", "quantization": "none"}},
    )
    assert rule.applies(ctx)
    result = failures(rule.check(ctx))
    assert [f.evidence[0].field for f in result] == [
        "inference.dtype",
        "inference.gpu_memory_utilization",
        "inference.quantization",
        "inference.tensor_parallel_size",
    ]
    full = context(
        tmp_path,
        inference={
            "backend": "vllm",
            "dtype": "bfloat16",
            "quantization": "none",
            "tensor_parallel_size": 1,
            "gpu_memory_utilization": 1,
        },
    )
    assert not failures(rule.check(full))


def test_stop_empty_list_is_an_explicit_declaration(tmp_path: Path) -> None:
    rule = StopDeclaredRule()
    assert failures(rule.check(context(tmp_path)))[0].severity == Severity.INFO
    assert not failures(rule.check(context(tmp_path, generation={"stop": []})))


def test_hf_fixture_generation_gaps_and_complete(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    data = {
        "project": {"name": "eval"},
        "experiment": {"profiles": ["inference"]},
        "generation": {"temperature": 0},
    }
    (repo / "reprollm.yaml").write_text(dump_yaml(data), encoding="utf-8")
    report = run_audit(repo)
    by_id = {f.rule_id: f for f in report.findings if f.rule_id.startswith("gen.")}
    assert by_id["gen.seed_declared"].status == FindingStatus.SKIPPED
    assert by_id["gen.params_declared"].status == FindingStatus.FAIL
    data["generation"].update(top_p=1, max_tokens=64, stop=[])
    data["inference"] = {
        "backend": "vllm",
        "dtype": "bfloat16",
        "quantization": "none",
        "tensor_parallel_size": 1,
        "gpu_memory_utilization": 0.8,
    }
    (repo / "reprollm.yaml").write_text(dump_yaml(data), encoding="utf-8")
    result = [f for f in run_audit(repo).findings if f.rule_id.startswith("gen.")]
    assert not failures(result)
    assert {
        "gen.params_declared",
        "gen.seed_declared",
        "gen.backend_declared",
        "gen.backend_config_declared",
        "gen.stop_declared",
    } <= set(resolve(["inference"], repo).rules)
