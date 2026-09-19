"""Observe only declared runtime locations, preserving every CLI occurrence."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from reprollm.core.bindings import normalize, observe, values_equal
from reprollm.schemas.manifest import BindingSpec
from reprollm.schemas.project_rules import ProjectRules


def test_all_declared_sources_and_repeated_flags(tmp_path: Path) -> None:
    (tmp_path / "config.yaml").write_text("sampling: {temperature: 0.0}\n")
    result = observe(
        {
            "generation.temperature": BindingSpec(
                cli="--temperature", config="config.yaml:sampling.temperature", env="TEMPERATURE"
            )
        },
        ["python", "script.py", "--unbound", "9", "--temperature", "0.5", "--temperature=1.0"],
        {"TEMPERATURE": "0.25"},
        tmp_path,
    )
    observations = result["generation.temperature"]
    assert [(x.value, x.source.type, x.source.key, x.source.path) for x in observations] == [
        (0.5, "cli", "--temperature", None),
        (1.0, "cli", "--temperature", None),
        (0.0, "config", "sampling.temperature", "config.yaml"),
        (0.25, "env", "TEMPERATURE", None),
    ]
    assert set(result) == {"generation.temperature"}


@pytest.mark.parametrize(
    "argv,expected",
    [
        ([], []),
        (["--flag"], [True]),
        (["--flag", "--other"], [True]),
        (["--flag="], [""]),
        (["--flag=-1"], [-1]),
        (["--flag", "-1"], [True]),
        (["--flag", "False"], [False]),
    ],
)
def test_cli_binding_boundaries(tmp_path: Path, argv: list[str], expected: list) -> None:
    found = observe({"custom.flag": BindingSpec(cli="--flag")}, argv, {}, tmp_path)
    assert [o.value for o in found.get("custom.flag", [])] == expected


def test_missing_config_keys_and_secret_env_bindings_warn_without_values(tmp_path: Path) -> None:
    (tmp_path / "c.json").write_text('{"value":1}')
    warnings = []
    found = observe(
        {
            "custom.missing": BindingSpec(config="c.json:absent"),
            "custom.credential": BindingSpec(env="HF_TOKEN"),
            "custom.absent": BindingSpec(env="MISSING"),
        },
        [],
        {"HF_TOKEN": "must-never-appear"},
        tmp_path,
        warnings=warnings,
    )
    assert found == {}
    assert any("custom.missing: config key not found" in warning for warning in warnings)
    assert any("custom.credential" in warning and "secret" in warning for warning in warnings)
    assert "must-never-appear" not in str(warnings)


@pytest.mark.parametrize(
    "location",
    [
        "../outside.yaml:x",
        "/tmp/outside.yaml:x",
        "C:/outside.yaml:x",
        "no-colon",
        "c.json:",
        "missing.yaml:x",
    ],
)
def test_invalid_config_locations_warn_without_reading_outside(
    tmp_path: Path, location: str
) -> None:
    warnings = []
    assert (
        observe({"custom.x": BindingSpec(config=location)}, [], {}, tmp_path, warnings=warnings)
        == {}
    )
    assert len(warnings) == 1
    assert "/tmp/outside" not in warnings[0]


def test_project_rule_bindings_extend_manifest_locations_without_duplicate_sources(
    tmp_path: Path,
) -> None:
    rules = ProjectRules.model_validate(
        {
            "schema_version": 1,
            "rules": [
                {
                    "id": "project.custom_x",
                    "field": "custom.x",
                    "severity": "WARNING",
                    "reason": "required",
                    "source": "manual",
                    "accepted_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
                    "bindings": {"cli": "--x", "env": "CUSTOM_X"},
                },
            ],
        }
    )
    found = observe(
        {"custom.x": BindingSpec(cli="--x")},
        ["--x=1"],
        {"CUSTOM_X": "2"},
        tmp_path,
        project_rules=rules,
    )
    assert [(o.source.type, o.value) for o in found["custom.x"]] == [("cli", 1), ("env", 2)]


def test_observed_value_patterns_are_redacted(tmp_path: Path) -> None:
    found = observe(
        {"custom.note": BindingSpec(cli="--note", env="NOTE")},
        ["--note=hf_01234567890123456789"],
        {"NOTE": "sk-0123456789abcdef"},
        tmp_path,
    )
    assert [o.value for o in found["custom.note"]] == [
        "<REDACTED:huggingface>",
        "<REDACTED:openai>",
    ]


def test_merged_cli_aliases_preserve_argv_order(tmp_path: Path) -> None:
    rules = ProjectRules.model_validate(
        {
            "schema_version": 1,
            "rules": [
                {
                    "id": "project.custom_x",
                    "field": "custom.x",
                    "severity": "WARNING",
                    "reason": "required",
                    "source": "manual",
                    "accepted_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
                    "bindings": {"cli": "--alternative"},
                }
            ],
        }
    )
    found = observe(
        {"custom.x": BindingSpec(cli="--x")},
        ["--x=1", "--alternative=2", "--x=3"],
        {},
        tmp_path,
        project_rules=rules,
    )
    assert [o.value for o in found["custom.x"]] == [1, 2, 3]


def test_invalid_and_forbidden_configs_never_expose_parser_payload(tmp_path: Path) -> None:
    (tmp_path / "broken.yaml").write_text("secret: [must-not-appear")
    (tmp_path / ".env").write_text("secret: must-not-appear")
    warnings = []
    assert (
        observe(
            {
                "custom.x": BindingSpec(config="broken.yaml:secret"),
                "custom.y": BindingSpec(config=".env:secret"),
            },
            [],
            {},
            tmp_path,
            warnings=warnings,
        )
        == {}
    )
    assert len(warnings) == 2
    assert "must-not-appear" not in str(warnings)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("0", 0),
        ("0.0", 0.0),
        ("True", True),
        ("false", False),
        (["1", "TRUE", ["0.0"]], [1, True, [0.0]]),
        (" unchanged ", " unchanged "),
        (None, None),
    ],
)
def test_normalization(value: object, expected: object) -> None:
    assert normalize(value) == expected


@pytest.mark.parametrize(
    "a,b,expected",
    [
        ("0", 0.0, True),
        ("True", True, True),
        (["1", "false"], [1.0, False], True),
        (1.0, 1.0 + 1e-10, True),
        (1.0, 1.01, False),
        ("X", "x", False),
        ([1], [1, 2], False),
        (True, 1, False),
    ],
)
def test_values_equal(a: object, b: object, expected: bool) -> None:
    assert values_equal(a, b) is expected
