"""UXR04 presence counts use actual declarations, not truthiness or model defaults."""

from pathlib import Path

import pytest

from reprollm.core.errors import UserError
from reprollm.core.init_guidance import field_guidance, field_label, missing_required_fields
from reprollm.core.manifest_scaffold import InitPlan, plan_init
from reprollm.schemas.finding import DetectionResult


def _plan(fields: list[str]) -> InitPlan:
    return InitPlan("trial", [], fields, DetectionResult(), None, [])


def test_missing_count_distinguishes_zero_false_empty_and_absent() -> None:
    fields = [
        "project.name",
        "execution.seed",
        "generation.do_sample",
        "custom.empty_text",
        "custom.empty_list",
        "custom.empty_map",
        "custom.null",
        "custom.absent",
        "custom.filled",
    ]
    text = """schema_version: 1
project: {name: trial}
experiment: {profiles: []}
execution: {seed: 0}
generation: {do_sample: false}
custom: {empty_text: '', empty_list: [], empty_map: {}, 'null': null, filled: present}
"""
    assert missing_required_fields(_plan(fields), text) == fields[3:8]


def test_implicit_model_defaults_do_not_fill_a_required_declaration() -> None:
    text = """schema_version: 1
project: {name: trial}
experiment: {profiles: []}
models: {judge: {id: judge-model}}
prompts: {judge: {path: rubric.txt}}
evaluation: {judge: {}}
"""
    assert missing_required_fields(_plan(["evaluation.judge.model_ref"]), text) == [
        "evaluation.judge.model_ref"
    ]


@pytest.mark.parametrize(
    "text", ["CANARY_PRIVATE: [", "project: {name: /private/CANARY_PRIVATE}", "project: {}"]
)
def test_invalid_count_input_has_private_usage_error(text: str) -> None:
    with pytest.raises(UserError) as raised:
        missing_required_fields(_plan(["project.name"]), text)
    assert "CANARY_PRIVATE" not in str(raised.value)
    assert "reprollm.yaml failed validation" in str(raised.value)


@pytest.mark.parametrize(
    "profile",
    ["inference", "evaluation", "finetuning", "safety", "privacy", "llm_judge", "judge_only"],
)
def test_all_shipped_research_fields_have_specific_help(tmp_path: Path, profile: str) -> None:
    plan = plan_init(tmp_path, profiles_override=[profile])
    for field in plan.required_fields:
        if field != "project.name":
            assert not field_guidance(field).startswith("Enter the value used by this experiment")


def test_custom_field_labels_are_bounded_and_safe() -> None:
    assert len(field_label("custom." + "x" * 500)) <= 160
    assert "\x1b" not in field_label("custom.\x1bfield")
    assert "sk-" + "a" * 40 not in field_label("custom.sk-" + "a" * 40)
