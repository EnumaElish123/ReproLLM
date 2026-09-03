"""Profile schema tests (spec §6)."""

import pytest
from pydantic import ValidationError

from reprollm.schemas.profile import Profile


def valid_profile() -> dict:
    return {
        "schema_version": 1,
        "name": "llm_judge",
        "description": "LLM-as-a-judge evaluation",
        "extends": ["evaluation"],
        "rules": ["judge.model_declared", "judge.prompt_declared"],
        "required_fields": ["models.judge.id", "evaluation.judge.prompt_ref"],
        "severity_overrides": {"gen.seed_declared": "CRITICAL"},
        "drift_overrides": {"evaluation.judge.*": "HIGH"},
        "detect": {
            "imports": ["openai"],
            "dependencies": ["openai"],
            "keywords": ["judge", "rubric"],
            "files": ["judge.py"],
        },
    }


def test_valid_profile_loads() -> None:
    p = Profile.model_validate(valid_profile())
    assert p.name == "llm_judge"
    assert p.extends == ["evaluation"]
    assert p.detect.keywords == ["judge", "rubric"]


def test_name_pattern_enforced() -> None:
    with pytest.raises(ValidationError):
        Profile.model_validate({**valid_profile(), "name": "LLM-Judge"})
    with pytest.raises(ValidationError):
        Profile.model_validate({**valid_profile(), "name": "1judge"})


def test_description_required() -> None:
    data = valid_profile()
    del data["description"]
    with pytest.raises(ValidationError):
        Profile.model_validate(data)


def test_unknown_key_rejected() -> None:
    with pytest.raises(ValidationError):
        Profile.model_validate({**valid_profile(), "rulez": []})


def test_bad_severity_override_rejected() -> None:
    with pytest.raises(ValidationError):
        Profile.model_validate({**valid_profile(), "severity_overrides": {"x.y": "FATAL"}})


def test_bad_drift_override_rejected() -> None:
    with pytest.raises(ValidationError):
        Profile.model_validate({**valid_profile(), "drift_overrides": {"a.*": "EXTREME"}})


def test_minimal_profile_with_defaults() -> None:
    p = Profile.model_validate(
        {"name": "inference", "description": "inference experiments", "rules": []}
    )
    assert p.extends == []
    assert p.required_fields == []
    assert p.severity_overrides == {}
    assert p.detect.imports == []
