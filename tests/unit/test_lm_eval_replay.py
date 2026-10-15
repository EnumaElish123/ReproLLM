"""D01: fixed native inputs and independent stdlib consumption evidence."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import yaml
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.core.bindings import observe
from reprollm.run.wrapper import create_run_dir, execute
from reprollm.schemas.manifest import Manifest
from reprollm.schemas.run_record import RunRecord
from reprollm.schemas.state import State
from tests.conftest import CmdStub

RECIPE = Path(__file__).parents[2] / "examples/lm_eval_replay"


def test_formal_recipe_inputs_match_independent_hashes_and_task_contract() -> None:
    expected = json.loads((RECIPE / "expected.json").read_text())
    assert expected["framework"]["commit"] == "b954108c9baaaa934b4ad842033b31a97ee30816"
    for relative, checksum in expected["sha256"].items():
        assert hashlib.sha256((RECIPE / relative).read_bytes()).hexdigest() == checksum
    task = yaml.safe_load((RECIPE / "upstream/gsm8k.yaml").read_bytes())
    assert task["dataset_path"] == "openai/gsm8k" and task["dataset_name"] == "main"
    assert task["test_split"] == "test" and task["fewshot_split"] == "train"
    assert task["num_fewshot"] == 5
    assert task["metric_list"][0]["metric"] == "exact_match"
    assert task["metric_list"][0]["aggregation"] == "mean"
    overlay = yaml.safe_load((RECIPE / "validation/tasks/gsm8k_validation.yaml").read_bytes())
    assert overlay == {
        "include": "../../lm_eval/tasks/gsm8k/gsm8k.yaml",
        "task": "gsm8k_validation",
        "dataset_kwargs": {"revision": "740312add88f781978c0658806c59bc2815b9866"},
    }
    configs = []
    for variant, cap in (("a", 32), ("b", 48)):
        manifest_path = expected["variants"][variant]["manifest"]
        config_path = expected["variants"][variant]["config"]
        manifest = Manifest.model_validate(yaml.safe_load((RECIPE / manifest_path).read_bytes()))
        config = yaml.safe_load((RECIPE / config_path).read_bytes())
        configs.append(config)
        assert config["gen_kwargs"]["max_gen_toks"] == manifest.generation.max_tokens == cap
        assert config["model_args"]["pretrained"] == manifest.models["primary"].id
        assert config["model_args"]["revision"] == manifest.models["primary"].revision
        assert config["model_args"]["tokenizer_revision"] == manifest.models["primary"].revision
        assert config["seed"] == config["model_args"]["seed"] == manifest.generation.seed == 42
        assert config["limit"] == 100 and config["num_fewshot"] == 5
        assert config["tasks"] == ["gsm8k_validation"]
        assert manifest.datasets["eval"].revision == overlay["dataset_kwargs"]["revision"]
        assert manifest.datasets["eval"].id == task["dataset_path"]
        assert manifest.datasets["eval"].subset == task["dataset_name"]
        assert manifest.datasets["eval"].split == task["test_split"]
        assert manifest.evaluation.metrics[0].name == task["metric_list"][0]["metric"]
        assert manifest.evaluation.aggregation == task["metric_list"][0]["aggregation"]
        assert manifest.execution.command == ("python -m lm_eval run --config validation/eval.yaml")
        assert manifest.bindings["generation.max_tokens"].config == (
            "validation/eval.yaml:gen_kwargs.max_gen_toks"
        )
        observations = observe(
            manifest.bindings,
            [],
            {},
            RECIPE,
            config_data={"validation/eval.yaml": (RECIPE / config_path).read_bytes()},
        )
        assert observations["generation.max_tokens"][0].value == cap
    configs[0]["gen_kwargs"]["max_gen_toks"] = 48
    assert configs[0] == configs[1]


def _prepare(root: Path) -> None:
    shutil.copytree(RECIPE, root, dirs_exist_ok=True)
    task = root / "lm_eval/tasks/gsm8k/gsm8k.yaml"
    task.parent.mkdir(parents=True)
    shutil.copyfile(root / "upstream/gsm8k.yaml", task)


def _probe(root: Path, *, rewrite: bool = False) -> tuple[RunRecord, Path, dict[str, Any]]:
    argv = [sys.executable, "probe.py", "--config", "validation/eval.yaml"]
    if rewrite:
        argv.extend(["--rewrite-cap", "96"])
    run_dir = create_run_dir(root)
    record = execute(
        argv,
        root=root,
        cwd=root,
        run_dir=run_dir,
        capture_output=False,
        env_capture="allowlist",
        extra_allowlist=[],
        snapshot=True,
    )
    assert record.exit_code == 0, record.warnings
    receipt = json.loads((root / "outputs/current/consumed.json").read_text())
    return record, run_dir, receipt


def test_stdlib_pair_proves_cap_consumption_state_diff_and_export(
    tmp_path: Path,
    stub_run_cmd: CmdStub,
) -> None:
    stub_run_cmd.on("git", returncode=128)
    stub_run_cmd.on("nvidia-smi", returncode=1)
    _prepare(tmp_path)
    first, first_dir, first_receipt = _probe(tmp_path)
    shutil.copyfile(tmp_path / "variants/eval-b.yaml", tmp_path / "validation/eval.yaml")
    shutil.copyfile(tmp_path / "variants/reprollm-b.yaml", tmp_path / "reprollm.yaml")
    second, second_dir, second_receipt = _probe(tmp_path)
    for record, run_dir, receipt, cap in (
        (first, first_dir, first_receipt, 32),
        (second, second_dir, second_receipt, 48),
    ):
        assert receipt["configuration"]["gen_kwargs"]["max_gen_toks"] == cap
        assert receipt["configuration"]["model_args"]["revision"] == (
            "7ae557604adf67be50417f59c2c2f167def9a775"
        )
        capture = next(item for item in record.files if item.path == "validation/eval.yaml")
        assert capture.sha256 == "sha256:" + receipt["input_sha256"]
        expected_sources = {
            "validation/eval.yaml": RECIPE
            / ("validation/eval.yaml" if cap == 32 else "variants/eval-b.yaml"),
            "validation/tasks/gsm8k_validation.yaml": RECIPE
            / "validation/tasks/gsm8k_validation.yaml",
            "lm_eval/tasks/gsm8k/gsm8k.yaml": RECIPE / "upstream/gsm8k.yaml",
            "probe.py": RECIPE / "probe.py",
        }
        captured = {item.path: item for item in record.files}
        assert expected_sources.keys() <= captured.keys()
        for relative, original in expected_sources.items():
            assert captured[relative].snapshot is not None
            assert (run_dir / captured[relative].snapshot).read_bytes() == original.read_bytes()
        assert record.bindings_observed["generation.max_tokens"][0].value == cap
        leaf = State.from_run(record, run_dir=run_dir).flatten()["generation.max_tokens"]
        assert leaf.value == cap and leaf.context.phase == "pre_child"
        output = CliRunner().invoke(app, ["export", str(tmp_path), "--run", record.run_id])
        assert output.exit_code == 0, output.output
        rendered = (tmp_path / "REPRODUCIBILITY.md").read_text()
        assert f"- `max_tokens`: {cap}" in rendered
        assert "Input consumption by the child is unverified." in rendered
    diff = CliRunner().invoke(
        app,
        [
            "diff",
            str(first_dir / "run.json"),
            str(second_dir / "run.json"),
            "--format",
            "json",
            "--fail-on",
            "HIGH",
        ],
    )
    assert diff.exit_code == 1, diff.output
    changes = json.loads(diff.stdout)["changes"]
    cap_change = next(item for item in changes if item["path"] == "generation.max_tokens")
    assert cap_change["a"] == 32 and cap_change["b"] == 48
    assert cap_change["severity"] == "HIGH"
    assert any(item["path"] == "files.validation/eval.yaml.sha256" for item in changes)


def test_consumed_then_rewritten_config_keeps_the_original_baseline(
    tmp_path: Path,
    stub_run_cmd: CmdStub,
) -> None:
    stub_run_cmd.on("git", returncode=128)
    stub_run_cmd.on("nvidia-smi", returncode=1)
    _prepare(tmp_path)
    record, run_dir, receipt = _probe(tmp_path, rewrite=True)
    assert receipt["configuration"]["gen_kwargs"]["max_gen_toks"] == 32
    assert (
        yaml.safe_load((tmp_path / "validation/eval.yaml").read_text())["gen_kwargs"][
            "max_gen_toks"
        ]
        == 96
    )
    assert record.input_capture is not None
    check = next(
        item for item in record.input_capture.checks if item.path == "validation/eval.yaml"
    )
    assert check.change == "changed" and check.before.sha256 == "sha256:" + receipt["input_sha256"]
    assert check.after.sha256 != check.before.sha256
    assert State.from_run(record, run_dir=run_dir).flatten()["generation.max_tokens"].value == 32
    result = CliRunner().invoke(app, ["export", str(tmp_path), "--run", record.run_id])
    assert result.exit_code == 0, result.output
    rendered = (tmp_path / "REPRODUCIBILITY.md").read_text()
    assert "- `max_tokens`: 32" in rendered and "- `max_tokens`: 96" not in rendered
    assert "validation/eval.yaml" in rendered and "changed" in rendered
