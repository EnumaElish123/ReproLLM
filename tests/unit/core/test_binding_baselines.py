"""Config binding bytes are bounded and can be frozen independently of disk changes."""

from __future__ import annotations

from pathlib import Path

import pytest

from reprollm.core.bindings import observe
from reprollm.core.configread import read_config_value
from reprollm.schemas.manifest import BindingSpec


def test_config_binding_uses_frozen_original_bytes(tmp_path: Path) -> None:
    (tmp_path / "config.json").write_bytes(b'{"temperature": 0.9}\n')
    observed = observe(
        {"generation.temperature": BindingSpec(config="config.json:temperature")},
        [],
        {},
        tmp_path,
        config_data={"config.json": b'{"temperature": 0.1}\n'},
    )
    assert observed["generation.temperature"][0].value == 0.1
    assert observed["generation.temperature"][0].source.path == "config.json"


@pytest.mark.parametrize("extra_byte", [False, True])
def test_config_read_limit_counts_original_bytes(tmp_path: Path, extra_byte: bool) -> None:
    prefix = b'{"value": 0.1}'
    data = prefix + b" " * (2 * 1024 * 1024 - len(prefix) + int(extra_byte))
    path = tmp_path / "config.json"
    path.write_bytes(data)
    if extra_byte:
        with pytest.raises(ValueError, match="2 MiB"):
            read_config_value(path, "value")
    else:
        assert read_config_value(path, "value") == 0.1
