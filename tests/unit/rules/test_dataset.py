"""M3-T02: dataset declarations and conditional metadata requirements."""

from pathlib import Path

import pytest

from reprollm.core.context import AuditContext
from reprollm.profiles.loader import resolve
from reprollm.rules.dataset import (
    DeclaredRule,
    PreprocessingDeclaredRule,
    SamplingSeedDeclaredRule,
    SplitDeclaredRule,
    SubsetDeclaredRule,
)
from reprollm.schemas.finding import FindingStatus, Severity
from tests.unit.rules.helpers import context, failures


@pytest.mark.parametrize(
    "rule_type",
    [
        DeclaredRule,
        PreprocessingDeclaredRule,
        SamplingSeedDeclaredRule,
        SplitDeclaredRule,
        SubsetDeclaredRule,
    ],
)
def test_no_manifest_skips_dataset_rules(tmp_path: Path, rule_type) -> None:
    assert rule_type.min_level == 1
    assert not rule_type().applies(AuditContext(tmp_path))


def test_dataset_map_presence(tmp_path: Path) -> None:
    rule = DeclaredRule()
    missing = failures(rule.check(context(tmp_path)))
    assert len(missing) == 1 and missing[0].severity == Severity.INFO
    assert missing[0].evidence[0].field == "datasets"
    assert not failures(rule.check(context(tmp_path, datasets={"eval": {}})))


@pytest.mark.parametrize(
    "rule_type,field,severity",
    [
        (SplitDeclaredRule, "split", Severity.WARNING),
        (SubsetDeclaredRule, "subset", Severity.INFO),
    ],
)
def test_hf_metadata_per_role_and_local_exclusion(
    tmp_path: Path, rule_type, field, severity
) -> None:
    ctx = context(
        tmp_path,
        datasets={
            "train": {"provider": "huggingface"},
            "eval": {"provider": "huggingface", field: "test"},
            "local": {"provider": "local"},
        },
    )
    result = rule_type().check(ctx)
    assert [f.evidence[0].field for f in result] == [
        f"datasets.eval.{field}",
        f"datasets.local.{field}",
        f"datasets.train.{field}",
    ]
    assert [f.status for f in result] == [
        FindingStatus.PASS,
        FindingStatus.SKIPPED,
        FindingStatus.FAIL,
    ]
    assert failures(result)[0].severity == severity
    assert all(f.evidence[0].field in f.message for f in result)


@pytest.mark.parametrize(
    "preprocessing,expected",
    [
        (None, FindingStatus.FAIL),
        ({}, FindingStatus.PASS),
        ({"description": "none"}, FindingStatus.PASS),
    ],
)
def test_preprocessing_object_presence(tmp_path: Path, preprocessing, expected) -> None:
    ctx = context(tmp_path, datasets={"eval": {"preprocessing": preprocessing}})
    result = PreprocessingDeclaredRule().check(ctx)
    assert len(result) == 1 and result[0].status == expected
    assert result[0].evidence[0].field == "datasets.eval.preprocessing"


@pytest.mark.parametrize("sampling", [None, {}, {"seed": 0}])
def test_no_sample_count_needs_no_sampling_seed(tmp_path: Path, sampling) -> None:
    ctx = context(tmp_path, datasets={"eval": {"sampling": sampling}})
    result = SamplingSeedDeclaredRule().check(ctx)
    assert result[0].status == FindingStatus.SKIPPED


@pytest.mark.parametrize("n", [0, 100])
def test_sampling_count_requires_its_own_seed(tmp_path: Path, n: int) -> None:
    rule = SamplingSeedDeclaredRule()
    ctx = context(
        tmp_path,
        generation={"seed": 0},
        execution={"seed": 0},
        datasets={"eval": {"sampling": {"n": n}}},
    )
    result = failures(rule.check(ctx))
    assert len(result) == 1 and result[0].severity == Severity.WARNING
    assert result[0].evidence[0].field == "datasets.eval.sampling.seed"
    seeded = context(tmp_path, datasets={"eval": {"sampling": {"n": n, "seed": 0}}})
    assert not failures(rule.check(seeded))


def test_preprocessing_and_sampling_do_not_share_values_between_roles(tmp_path: Path) -> None:
    ctx = context(tmp_path, datasets={"train": {}, "eval": {"preprocessing": {}}})
    result = failures(PreprocessingDeclaredRule().check(ctx))
    assert [f.evidence[0].field for f in result] == ["datasets.train.preprocessing"]
    ctx = context(
        tmp_path,
        datasets={"train": {"sampling": {"n": 2}}, "eval": {"sampling": {"n": 2, "seed": 0}}},
    )
    result = failures(SamplingSeedDeclaredRule().check(ctx))
    assert [f.evidence[0].field for f in result] == ["datasets.train.sampling.seed"]


@pytest.mark.parametrize(
    "rule_type",
    [PreprocessingDeclaredRule, SamplingSeedDeclaredRule, SplitDeclaredRule, SubsetDeclaredRule],
)
def test_empty_dataset_map_skips_per_role_rules(tmp_path: Path, rule_type) -> None:
    assert not rule_type().applies(context(tmp_path))


def test_dataset_profile_selection(tmp_path: Path) -> None:
    assert "dataset.split_declared" in resolve([], tmp_path).rules
    assert {"dataset.declared", "dataset.preprocessing_declared"} <= set(
        resolve(["finetuning"], tmp_path).rules
    )
    assert {
        "dataset.declared",
        "dataset.preprocessing_declared",
        "dataset.sampling_seed_declared",
        "dataset.subset_declared",
    } <= set(resolve(["evaluation"], tmp_path).rules)
