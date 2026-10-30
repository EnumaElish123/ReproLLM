"""UXR04: guided answers recover in place and report actual declaration gaps."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from reprollm.cli.main import app, cli
from reprollm.core.yaml_io import load_manifest

runner = CliRunner()


def _profile(root: Path, fields: list[str]) -> None:
    directory = root / ".reprollm" / "profiles"
    directory.mkdir(parents=True)
    (directory / "trial.yaml").write_text(
        "schema_version: 1\nname: trial\ndescription: Trial\nextends: [core]\nrules: []\n"
        f"required_fields: {json.dumps(fields)}\n",
        encoding="utf-8",
    )


def _guided(root: Path, profile: str, answers: list[str], *options: str):
    return runner.invoke(
        app,
        ["init", str(root), "--interactive", "--profiles", profile, *options],
        input="\n".join(["", *answers, ""]),
    )


@pytest.mark.parametrize(
    ("answer", "field"),
    [
        ("warm", "generation.temperature"),
        ("3", "generation.temperature"),
        ("nan", "generation.temperature"),
        ("inf", "generation.temperature"),
        ("many", "generation.max_tokens"),
        ("0", "generation.max_tokens"),
        ("1.5", "generation.max_tokens"),
        ("unknown", "inference.backend"),
    ],
)
def test_invalid_answer_retries_only_current_field(tmp_path: Path, answer: str, field: str) -> None:
    answers = ["org/model", "other", "0", "32"]
    index = {"inference.backend": 1, "generation.temperature": 2, "generation.max_tokens": 3}[field]
    answers.insert(index, answer)
    result = _guided(tmp_path, "inference", answers)
    assert result.exit_code == 0, result.output
    manifest = load_manifest(tmp_path / "reprollm.yaml")
    assert manifest.models["primary"].id == "org/model"
    assert manifest.inference is not None and manifest.inference.backend == "other"
    assert manifest.generation is not None and manifest.generation.temperature == 0
    assert manifest.generation.max_tokens == 32
    assert f"Invalid value for {field}." in result.output
    assert "0 required fields still need values in reprollm.yaml." in result.output
    assert "review" in result.output.lower() and "reprollm audit ." in result.output


def test_help_describes_actual_values_and_unknowns(tmp_path: Path) -> None:
    result = _guided(tmp_path, "inference", ["", "", "", ""])
    assert result.exit_code == 0, result.output
    assert "Use the values from your experiment" in result.output
    assert "leave it unknown" in result.output
    assert "Maximum generated tokens" in result.output
    assert "4 required fields still need values in reprollm.yaml." in result.output
    assert (
        "Remaining: models.primary.id, inference.backend, "
        "generation.temperature, generation.max_tokens" in result.output
    )


def test_blank_keeps_detected_candidate_without_filling_unknowns(tmp_path: Path) -> None:
    (tmp_path / "model.py").write_text(
        'from transformers import AutoModel\nAutoModel.from_pretrained("org/model")\n',
        encoding="utf-8",
    )
    result = _guided(tmp_path, "inference", ["", "", "", ""])
    assert result.exit_code == 0, result.output
    assert load_manifest(tmp_path / "reprollm.yaml").models["primary"].id == "org/model"
    assert "3 required fields still need values in reprollm.yaml." in result.output
    assert "[org/model]" in result.output


def test_selected_metrics_are_counted_but_manual_research_fields_remain(tmp_path: Path) -> None:
    tasks = tmp_path / "lm_eval" / "tasks"
    tasks.mkdir(parents=True)
    (tasks / "trial.yaml").write_text("task: trial\ndataset_path: org/data\n", encoding="utf-8")
    result = _guided(tmp_path, "safety", ["trial", "", "org/model", "other", "0", "32", "org/data"])
    assert result.exit_code == 0, result.output
    assert "2 required fields still need values in reprollm.yaml." in result.output
    assert "Remaining: evaluation.definitions.refusal, evaluation.definitions.asr" in result.output
    assert (
        "evaluation.metrics: task names selected; verify metric names and implementations"
        in result.output
    )
    manifest = load_manifest(tmp_path / "reprollm.yaml")
    assert manifest.evaluation is not None and [m.name for m in manifest.evaluation.metrics] == [
        "trial"
    ]


def test_privacy_manual_mechanism_is_not_silently_filled(tmp_path: Path) -> None:
    result = _guided(tmp_path, "privacy", ["org/model", "honest-but-curious server"])
    assert result.exit_code == 0, result.output
    assert "1 required fields still need values in reprollm.yaml." in result.output
    assert "Remaining: privacy.mechanism.name" in result.output
    assert load_manifest(tmp_path / "reprollm.yaml").privacy.mechanism is None


@pytest.mark.parametrize("answer", ["../judge.txt", "/private/judge.txt", "C:/private/judge.txt"])
def test_invalid_prompt_path_can_be_corrected(tmp_path: Path, answer: str) -> None:
    result = _guided(
        tmp_path, "judge_only", ["org/data", "judge-model", answer, "prompts/judge.txt", "0", "32"]
    )
    assert result.exit_code == 0, result.output
    manifest = load_manifest(tmp_path / "reprollm.yaml")
    assert "primary" not in manifest.models
    assert manifest.prompts["judge"].path == "prompts/judge.txt"
    assert "Invalid value for prompts.judge.path." in result.output
    assert "1 required fields still need values in reprollm.yaml." in result.output


@pytest.mark.parametrize(
    "answer", ["true", "alpha: beta", "with # hash", "[literal]", 'quoted "text"']
)
def test_explicit_text_keeps_literal_string_meaning(tmp_path: Path, answer: str) -> None:
    result = _guided(tmp_path, "privacy", ["org/model", answer])
    assert result.exit_code == 0, result.output
    assert load_manifest(tmp_path / "reprollm.yaml").privacy.threat_model == answer


def test_noninteractive_count_uses_rendered_values_and_never_prompts(tmp_path: Path) -> None:
    (tmp_path / "model.py").write_text(
        'from transformers import AutoModel\nAutoModel.from_pretrained("org/model")\n',
        encoding="utf-8",
    )
    result = runner.invoke(app, ["init", str(tmp_path), "--profiles", "inference"])
    assert result.exit_code == 0, result.output
    assert "3 required fields still need values in reprollm.yaml." in result.output
    assert "Use the values from your experiment" not in result.output


def test_custom_field_gets_help_and_saved_command_is_not_prompted(tmp_path: Path) -> None:
    _profile(tmp_path, ["execution.command", "execution.seed"])
    result = _guided(tmp_path, "trial", ["org/model", "0"], "--command", "python eval.py")
    assert result.exit_code == 0, result.output
    manifest = load_manifest(tmp_path / "reprollm.yaml")
    assert manifest.execution.seed == 0 and manifest.execution.command == "python eval.py"
    assert "Enter the value used by this experiment" in result.output
    assert "0 required fields still need values in reprollm.yaml." in result.output


def test_safe_fallback_project_name_is_filled_but_still_needs_review(tmp_path: Path) -> None:
    root = tmp_path / "space name"
    root.mkdir()
    result = _guided(root, "inference", ["org/model", "other", "0", "32"])
    assert result.exit_code == 0, result.output
    assert "0 required fields still need values in reprollm.yaml." in result.output
    assert "Set project.name in reprollm.yaml" in result.output


def test_eof_after_bad_answer_preserves_force_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert runner.invoke(app, ["init", str(tmp_path), "--profiles", "inference"]).exit_code == 0
    owned = [
        tmp_path / "reprollm.yaml",
        tmp_path / ".reprollm/config.yaml",
        tmp_path / ".reprollm/project-rules.yaml",
    ]
    before = {p: (p.read_bytes(), p.stat().st_mode) for p in owned}
    monkeypatch.setattr(
        "sys.argv",
        ["reprollm", "init", str(tmp_path), "--force", "--interactive", "--profiles", "inference"],
    )
    with (
        runner.isolation(input="\norg/model\nother\ninvalid-number\n"),
        pytest.raises(SystemExit) as raised,
    ):
        cli()
    assert raised.value.code == 2
    assert {p: (p.read_bytes(), p.stat().st_mode) for p in owned} == before
    assert not list(tmp_path.glob(".reprollm.yaml.*.tmp"))


def test_unsupported_custom_scaffold_fails_before_field_loop(tmp_path: Path) -> None:
    _profile(tmp_path, ["unsupported.value"])
    result = _guided(tmp_path, "trial", [])
    assert result.exit_code != 0
    assert "interactive scaffold" in str(result.exception)
    assert not (tmp_path / "reprollm.yaml").exists()


@pytest.mark.parametrize("field", ["custom.foo", "project.description"])
def test_unsupported_baseline_does_not_accept_discarded_answers(tmp_path: Path, field: str) -> None:
    _profile(tmp_path, [field])
    result = _guided(tmp_path, "trial", ["org/model", "answer"])
    assert result.exit_code != 0
    assert "interactive scaffold" in str(result.exception)
    assert not (tmp_path / "reprollm.yaml").exists()


@pytest.mark.parametrize("bad", ["sk-" + "a" * 40, "bad\x1bvalue", "bad\u202evalue", "bad\nvalue"])
def test_private_or_control_answer_can_be_retried_without_diagnostic_echo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bad: str
) -> None:
    answers = iter(["inference", "org/model", "other", bad, "0", "32"])
    monkeypatch.setattr("reprollm.cli.init.typer.prompt", lambda *args, **kwargs: next(answers))
    result = runner.invoke(app, ["init", str(tmp_path), "--interactive", "--profiles", "inference"])
    assert result.exit_code == 0, result.output
    assert bad not in result.output
    assert bad not in (tmp_path / "reprollm.yaml").read_text(encoding="utf-8")
    assert "Invalid value for generation.temperature." in result.stderr


def test_private_detected_candidate_is_not_echoed_as_new_default(tmp_path: Path) -> None:
    token = "org/sk-" + "a" * 40
    (tmp_path / "model.py").write_text(
        "from transformers import AutoModel\nAutoModel.from_pretrained("
        + json.dumps(token)
        + ")\n",
        encoding="utf-8",
    )
    result = _guided(tmp_path, "inference", ["", "", "", ""])
    assert result.exit_code != 0
    assert token not in result.output and token not in str(result.exception)
    assert not (tmp_path / "reprollm.yaml").exists()


def test_cancelled_required_prompt_preserves_force_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert runner.invoke(app, ["init", str(tmp_path), "--profiles", "inference"]).exit_code == 0
    manifest = tmp_path / "reprollm.yaml"
    before = (manifest.read_bytes(), manifest.stat().st_mode)
    calls = 0

    def cancelled(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return "inference"
        import typer

        raise typer.Abort()

    monkeypatch.setattr("reprollm.cli.init.typer.prompt", cancelled)
    monkeypatch.setattr(
        "sys.argv",
        ["reprollm", "init", str(tmp_path), "--interactive", "--force", "--profiles", "inference"],
    )
    with pytest.raises(SystemExit) as raised:
        cli()
    assert raised.value.code == 2
    assert (manifest.read_bytes(), manifest.stat().st_mode) == before


def test_custom_false_answer_is_a_value_not_a_missing_field(tmp_path: Path) -> None:
    _profile(tmp_path, ["generation.do_sample"])
    result = _guided(tmp_path, "trial", ["org/model", "false"])
    assert result.exit_code == 0, result.output
    assert load_manifest(tmp_path / "reprollm.yaml").generation.do_sample is False
    assert "0 required fields still need values in reprollm.yaml." in result.output


@pytest.mark.parametrize("interactive", [False, True])
def test_new_field_labels_hide_private_path_keys(tmp_path: Path, interactive: bool) -> None:
    field = "training.params./private/uxb-label-canary"
    _profile(tmp_path, [field])
    result = (
        _guided(tmp_path, "trial", ["org/model", ""])
        if interactive
        else runner.invoke(app, ["init", str(tmp_path), "--profiles", "trial"])
    )
    assert result.exit_code == 0, result.output
    assert "/private/uxb-label-canary" not in result.output
    assert "<required field in reprollm.yaml>" in result.output


def test_new_field_labels_hide_current_machine_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _profile(tmp_path, ["training.params.machinecanary"])
    monkeypatch.setattr("reprollm.core.init_guidance.socket.gethostname", lambda: "machinecanary")
    result = runner.invoke(app, ["init", str(tmp_path), "--profiles", "trial"])
    assert result.exit_code == 0, result.output
    assert "machinecanary" not in result.output
    assert "<required field in reprollm.yaml>" in result.output


@pytest.mark.parametrize("bad_temperature", [None, "warm"])
def test_pending_required_custom_scalar_keeps_existing_valid_flow(
    tmp_path: Path, bad_temperature: str | None
) -> None:
    _profile(tmp_path, ["generation.temperature", "training.deepspeed.config"])
    answers = ["org/model"]
    if bad_temperature is not None:
        answers.append(bad_temperature)
    answers.extend(["0", "configs/deepspeed.json"])
    result = _guided(tmp_path, "trial", answers)
    assert result.exit_code == 0, result.output
    manifest = load_manifest(tmp_path / "reprollm.yaml")
    assert manifest.models["primary"].id == "org/model"
    assert manifest.generation is not None and manifest.generation.temperature == 0
    assert manifest.training is not None and manifest.training.deepspeed is not None
    assert manifest.training.deepspeed.config == "configs/deepspeed.json"
    assert "0 required fields still need values in reprollm.yaml." in result.output
    if bad_temperature is not None:
        assert "Invalid value for generation.temperature." in result.stderr


def test_pending_required_custom_scalar_is_still_validated_when_answered(tmp_path: Path) -> None:
    _profile(tmp_path, ["training.deepspeed.config"])
    result = _guided(tmp_path, "trial", ["org/model", "../outside.json", "configs/deepspeed.json"])
    assert result.exit_code == 0, result.output
    assert "Invalid value for training.deepspeed.config." in result.stderr
    manifest = load_manifest(tmp_path / "reprollm.yaml")
    assert manifest.training is not None and manifest.training.deepspeed is not None
    assert manifest.training.deepspeed.config == "configs/deepspeed.json"


def test_unknown_nonnullable_custom_scalar_keeps_full_final_validation(tmp_path: Path) -> None:
    _profile(tmp_path, ["training.deepspeed.config"])
    result = _guided(tmp_path, "trial", ["org/model", ""])
    assert result.exit_code != 0
    assert "reprollm.yaml failed validation" in str(result.exception)
    assert not (tmp_path / "reprollm.yaml").exists()


def test_latent_cross_field_scaffold_error_stops_instead_of_retrying_valid_answer(
    tmp_path: Path,
) -> None:
    _profile(tmp_path, ["training.deepspeed.config", "evaluation.judge.params.temperature"])
    result = _guided(
        tmp_path, "trial", ["org/model", "configs/deepspeed.json", "configs/deepspeed.json"]
    )
    assert result.exit_code != 0
    assert "interactive scaffold" in str(result.exception)
    assert "Invalid value for training.deepspeed.config." not in result.stderr
    assert not (tmp_path / "reprollm.yaml").exists()
