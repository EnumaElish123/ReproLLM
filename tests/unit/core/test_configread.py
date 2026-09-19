"""Declared structured configuration lookups (M5-T03, spec §15.1)."""

from pathlib import Path

import pytest
import yaml

from reprollm.core.configread import read_config_value


@pytest.mark.parametrize(
    "suffix,text",
    [
        (".yaml", "sampling:\n  temperature: 0.0\n  stops: [one, two]\n"),
        (".yml", "sampling: {temperature: 0.0, stops: [one, two]}"),
        (".json", '{"sampling":{"temperature":0.0,"stops":["one","two"]}}'),
        (".toml", '[sampling]\ntemperature = 0.0\nstops = ["one", "two"]\n'),
    ],
)
def test_config_values_and_list_indices(tmp_path: Path, suffix: str, text: str) -> None:
    path = tmp_path / f"config{suffix}"
    path.write_text(text)
    assert read_config_value(path, "sampling.temperature") == 0.0
    assert read_config_value(path, "sampling.stops.1") == "two"
    for key in (
        "missing",
        "sampling.stops.2",
        "sampling.stops.bad",
        "sampling.temperature.child",
        "",
    ):
        with pytest.raises(KeyError):
            read_config_value(path, key)


@pytest.mark.parametrize("suffix,text", [(".json", "{"), (".yaml", "value: ["), (".toml", "v = [")])
def test_invalid_config_is_not_silently_interpreted(tmp_path: Path, suffix: str, text: str) -> None:
    path = tmp_path / f"bad{suffix}"
    path.write_text(text)
    with pytest.raises((ValueError, yaml.YAMLError)):
        read_config_value(path, "value")


def test_unknown_format_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "config.txt"
    path.write_text("value=1")
    with pytest.raises(ValueError, match="YAML|JSON|TOML"):
        read_config_value(path, "value")
