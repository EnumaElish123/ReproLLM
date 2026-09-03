"""yaml_io tests: deterministic dump, empty-file handling, UserError conversion."""

from pathlib import Path

import pytest
import yaml

from reprollm.core.errors import UserError
from reprollm.core.yaml_io import dump_yaml, load_manifest, load_yaml
from reprollm.schemas.manifest import Manifest


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_load_yaml_empty_file_returns_empty_dict(tmp_path: Path) -> None:
    assert load_yaml(_write(tmp_path / "x.yaml", "")) == {}
    assert load_yaml(_write(tmp_path / "y.yaml", "\n# only a comment\n")) == {}


def test_load_yaml_missing_file_is_user_error(tmp_path: Path) -> None:
    with pytest.raises(UserError):
        load_yaml(tmp_path / "missing.yaml")


def test_load_yaml_non_mapping_is_user_error(tmp_path: Path) -> None:
    with pytest.raises(UserError, match="mapping"):
        load_yaml(_write(tmp_path / "x.yaml", "- a\n- b\n"))


def test_dump_yaml_keeps_field_order_and_2_space_indent(tmp_path: Path) -> None:
    manifest = Manifest.model_validate(
        {
            "project": {"name": "p"},
            "experiment": {"profiles": ["inference"]},
            "models": {"primary": {"provider": "openai", "id": "gpt-4o"}},
        }
    )
    text = dump_yaml(manifest)
    lines = text.splitlines()
    assert lines[0] == "schema_version: 1"
    assert lines[1] == "project:"
    assert "  name: p" in lines
    assert "models:" in lines
    assert "    provider: openai" in lines


def test_dump_yaml_does_not_fold_long_lines() -> None:
    data = {"fix_hint": "x" * 500}
    text = dump_yaml(data)
    assert "x" * 500 in text
    assert len(text.splitlines()) <= 3


def test_dump_yaml_round_trip(tmp_path: Path) -> None:
    data = {
        "schema_version": 1,
        "project": {"name": "p"},
        "experiment": {"profiles": ["inference", "evaluation"]},
        "custom": {"a": [1, 2, {"b": "c"}]},
    }
    text = dump_yaml(data)
    assert yaml.safe_load(text) == data


def test_load_manifest_invalid_reports_field_path(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "reprollm.yaml",
        "schema_version: 1\nproject:\n  name: p\nexperiment: {}\n",
    )
    with pytest.raises(UserError) as excinfo:
        load_manifest(path)
    assert "experiment.profiles" in str(excinfo.value)


def test_load_manifest_valid(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "reprollm.yaml",
        "project:\n  name: p\nexperiment:\n  profiles: []\n",
    )
    m = load_manifest(path)
    assert m.project.name == "p"


def test_load_yaml_datetimes_as_iso_z(tmp_path: Path) -> None:
    from datetime import datetime, timezone

    from reprollm.schemas.project_rules import ProjectRules

    doc = ProjectRules.model_validate(
        {
            "schema_version": 1,
            "rules": [],
            "ignored_candidates": [{"candidate_id": "c-1", "ignored_at": "2026-09-03T09:00:00Z"}],
        }
    )
    text = dump_yaml(doc)
    assert "ignored_at: '2026-09-03T09:00:00Z'" in text or "2026-09-03T09:00:00Z" in text
    assert doc.ignored_candidates[0].ignored_at == datetime(2026, 9, 3, 9, 0, tzinfo=timezone.utc)
