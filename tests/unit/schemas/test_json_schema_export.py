"""Schema export tests: validity (Draft 2020-12), $id, determinism, freshness."""

import json
from pathlib import Path

import jsonschema
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.cli.schema import SCHEMA_MODELS, model_schema_text

EXPECTED_FILES = sorted(f"{name}.schema.json" for name in SCHEMA_MODELS)

#: tests/unit/schemas/x.py → repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]


def test_nine_schema_files_exist() -> None:
    repo_root = _REPO_ROOT
    exported = sorted(p.name for p in (repo_root / "schemas").glob("*.schema.json"))
    assert exported == [
        "audit_report.schema.json",
        "config.schema.json",
        "diff_report.schema.json",
        "discover_candidates.schema.json",
        "lock.schema.json",
        "manifest.schema.json",
        "profile.schema.json",
        "project_rules.schema.json",
        "run_record.schema.json",
    ]


def test_every_exported_schema_is_valid_draft202012() -> None:
    repo_root = _REPO_ROOT
    for path in sorted((repo_root / "schemas").glob("*.schema.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        assert schema["$id"] == f"https://reprollm.dev/schemas/{path.name}"


def test_export_is_deterministic() -> None:
    for name, model in SCHEMA_MODELS.items():
        assert model_schema_text(model, name) == model_schema_text(model, name)
    first = {n: model_schema_text(m, n) for n, m in SCHEMA_MODELS.items()}
    second = {n: model_schema_text(m, n) for n, m in SCHEMA_MODELS.items()}
    assert first == second


def test_committed_schemas_are_fresh(tmp_path: Path) -> None:
    repo_root = _REPO_ROOT
    runner = CliRunner()
    result = runner.invoke(app, ["schema", "export", "--out", str(tmp_path)])
    assert result.exit_code == 0, result.output
    for path in sorted((repo_root / "schemas").glob("*.schema.json")):
        fresh = tmp_path / path.name
        assert fresh.exists(), f"{path.name} missing from fresh export"
        assert path.read_text(encoding="utf-8") == fresh.read_text(encoding="utf-8"), (
            f"{path.name} is stale; run `reprollm schema export --out schemas/` and commit"
        )


def test_cli_export_writes_files(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["schema", "export", "--out", str(tmp_path / "out")])
    assert result.exit_code == 0, result.output
    written = sorted(p.name for p in (tmp_path / "out").glob("*.schema.json"))
    assert written == EXPECTED_FILES
