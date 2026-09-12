"""Config schema tests (spec §8)."""

import pytest
from pydantic import ValidationError

from reprollm.schemas.config import Config


def test_defaults() -> None:
    c = Config.model_validate({"schema_version": 1})
    assert c.audit.fail_on == "critical"
    assert c.audit.ignore == []
    assert c.audit.show_passed is False
    assert c.run.env_capture == "allowlist"
    assert c.run.snapshot_max_bytes == 1_048_576
    assert c.discover.enabled is False
    assert c.discover.max_chars == 60_000


def test_ignore_requires_reason() -> None:
    ok = Config.model_validate(
        {
            "schema_version": 1,
            "audit": {"ignore": [{"rule": "code.no_untracked", "reason": "generated"}]},
        }
    )
    assert ok.audit.ignore[0].rule == "code.no_untracked"
    with pytest.raises(ValidationError):
        Config.model_validate(
            {"schema_version": 1, "audit": {"ignore": [{"rule": "code.no_untracked"}]}}
        )
    with pytest.raises(ValidationError):
        Config.model_validate(
            {
                "schema_version": 1,
                "audit": {"ignore": [{"rule": "x", "reason": ""}]},
            }
        )


def test_enum_values_enforced() -> None:
    with pytest.raises(ValidationError):
        Config.model_validate({"schema_version": 1, "audit": {"fail_on": "info"}})
    with pytest.raises(ValidationError):
        Config.model_validate({"schema_version": 1, "run": {"env_capture": "everything"}})


def test_unknown_keys_rejected() -> None:
    with pytest.raises(ValidationError):
        Config.model_validate({"schema_version": 1, "audits": {}})


def test_discover_env_var_names_overridable() -> None:
    c = Config.model_validate({"schema_version": 1, "discover": {"base_url_env": "MY_BASE_URL"}})
    assert c.discover.base_url_env == "MY_BASE_URL"


@pytest.mark.parametrize("reason", [" ", "\t\n", "\u3000"])
def test_ignore_rejects_whitespace_only_reason(reason: str) -> None:
    with pytest.raises(ValidationError) as excinfo:
        Config.model_validate(
            {"audit": {"ignore": [{"rule": "code.no_untracked", "reason": reason}]}}
        )
    assert excinfo.value.errors()[0]["loc"] == ("audit", "ignore", 0, "reason")


def test_ignore_does_not_rewrite_a_nonblank_reason() -> None:
    reason = "  generated notebooks  "
    config = Config.model_validate(
        {"audit": {"ignore": [{"rule": "code.no_untracked", "reason": reason}]}}
    )
    assert config.audit.ignore[0].reason == reason
