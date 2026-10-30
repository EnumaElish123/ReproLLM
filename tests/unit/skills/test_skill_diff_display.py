"""Compare original values, then privately render legacy run context through native diff."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

SCRIPTS = Path(__file__).resolve().parents[3] / "skills/reprollm/scripts"
sys.path.insert(0, str(SCRIPTS))
import skill_diff_display as display  # noqa: E402
import skill_runtime as runtime  # noqa: E402

LEFT = "20261030T010000Z-aaaaaa"
RIGHT = "20261030T020000Z-bbbbbb"
FIELD = "evaluation.judge.params.label"
CANARY_A = "OpaqueDiffBindingAlpha123456"
CANARY_B = "OpaqueDiffBindingBravo123456"
ARGV_A = "OpaqueDiffCommandAlpha123456"
ARGV_B = "OpaqueDiffCommandBravo123456"
MARKER = "<REDACTED:generic_kv>"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "研究 project"
    root.mkdir()
    return root


def write_record(
    root: Path,
    run_id: str,
    *,
    value: Any,
    source: dict[str, Any] | None = None,
    argv: list[str] | None = None,
    observations: dict[str, list[dict[str, Any]]] | None = None,
) -> tuple[Path, str]:
    from reprollm.schemas.run_record import RunRecord

    payload = {
        "schema_version": 1,
        "reprollm_version": "0.6.1",
        "run_id": run_id,
        "name": "pair",
        "status": "completed",
        "exit_code": 0,
        "command": {"argv": argv or ["python", "eval.py"], "cwd": ".", "redactions": 0},
        "bindings_observed": observations
        if observations is not None
        else {FIELD: [{"value": value, "source": source or {"type": "cli", "key": "--label"}}]},
    }
    RunRecord.model_validate(payload)
    folder = root / ".reprollm/runs" / run_id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "run.json"
    raw = json.dumps(payload, ensure_ascii=False) + "\n"
    path.write_text(raw)
    return path, raw


def arguments(
    format: str = "json", *extra: str, inputs: tuple[str, str] = (LEFT, RIGHT)
) -> list[str]:
    return ["diff", "--format", format, *extra, "--", *inputs]


def invoke(root: Path, argv: list[str]) -> tuple[runtime.CliResult, list[dict[str, Any]]]:
    return display.invoke_private_diff(
        argv,
        root,
        invoke_cli=runtime.invoke_cli,
        sanitize=lambda value, diagnostics: runtime._sanitize(
            value, root, action="runs.show", diagnostics=diagnostics
        ),
    )


def invariants(report: dict[str, Any]) -> Any:
    report = copy.deepcopy(report)
    for change in report["changes"]:
        change.pop("a")
        change.pop("b")
    return report


@pytest.mark.parametrize("format", ["json", "text"])
@pytest.mark.parametrize("selection", ["ids", "paths", "directories", "latest"])
def test_public_values_use_original_selection_format_and_single_native_call(
    project: Path, format: str, selection: str
) -> None:
    files = [
        write_record(project, LEFT, value=32),
        write_record(project, RIGHT, value=48),
    ]
    args = arguments(format)
    if selection == "paths":
        args = arguments(format, inputs=tuple(str(path) for path, _ in files))
    if selection == "directories":
        args = arguments(format, inputs=tuple(str(path.parent) for path, _ in files))
    if selection == "latest":
        args = ["diff", "--format", format, "--latest-successful", "--name", "pair"]
    native = runtime.invoke_cli(args, project)
    calls = []

    def call(argv: list[str], root: Path) -> runtime.CliResult:
        calls.append((argv, root))
        return runtime.invoke_cli(argv, root)

    result, diagnostics = display.invoke_private_diff(
        args,
        project,
        invoke_cli=call,
        sanitize=lambda value, diagnostics: runtime._sanitize(
            value, project, action="runs.show", diagnostics=diagnostics
        ),
    )
    assert (result.exit_code, result.stdout, result.stderr) == (
        native.exit_code,
        native.stdout,
        native.stderr,
    )
    assert len(calls) == 1 and not diagnostics
    assert all(path.read_text() == raw for path, raw in files)


@pytest.mark.parametrize("format", ["json", "text"])
@pytest.mark.parametrize(
    "source",
    [
        {"type": "cli", "key": "--api-key"},
        {"type": "config", "key": "credentials.password", "path": "configs/options.yaml"},
        {"type": "config", "key": "namespace:api_key", "path": "configs/colon:name.yaml"},
        {"type": "env", "key": "HF_TOKEN"},
    ],
)
def test_contextual_secrets_are_masked_only_after_comparison(
    project: Path, format: str, source: dict[str, Any]
) -> None:
    files = [
        write_record(project, LEFT, value=CANARY_A, source=source),
        write_record(project, RIGHT, value=CANARY_B, source=source),
    ]
    native_json = runtime.invoke_cli(arguments("json", "--fail-on", "HIGH"), project)
    raw = json.loads(native_json.stdout)
    original = next(change for change in raw["changes"] if change["path"] == FIELD)
    assert original["a"] == CANARY_A and original["b"] == CANARY_B
    assert original["severity"] == "HIGH" and native_json.exit_code == 1
    result, diagnostics = invoke(project, arguments(format, "--fail-on", "HIGH"))
    assert result.exit_code == 1 and CANARY_A not in result.stdout and CANARY_B not in result.stdout
    assert diagnostics and not result.stderr
    if format == "json":
        safe = json.loads(result.stdout)
        assert invariants(safe) == invariants(raw)
        changed = next(change for change in safe["changes"] if change["path"] == FIELD)
        assert changed["a"] == changed["b"] == MARKER
    else:
        assert "HIGH" in result.stdout and MARKER in result.stdout
    assert all(path.read_text() == original for path, original in files)


@pytest.mark.parametrize("format", ["json", "text"])
def test_command_argv_has_separate_original_previous_flag_context_per_side(
    project: Path, format: str
) -> None:
    files = [
        write_record(project, LEFT, value=32, argv=["python", "eval.py", "--api-key", ARGV_A]),
        write_record(project, RIGHT, value=48, argv=["python", "eval.py", "--label", ARGV_B]),
    ]
    native = runtime.invoke_cli(arguments("json"), project)
    result, diagnostics = invoke(project, arguments(format))
    assert result.exit_code == native.exit_code == 0
    assert ARGV_A not in result.stdout and ARGV_B in result.stdout and diagnostics
    if format == "json":
        safe = json.loads(result.stdout)
        assert invariants(safe) == invariants(json.loads(native.stdout))
        command = next(change for change in safe["changes"] if change["path"] == "command.argv")
        assert command["a"][-1] == MARKER and command["b"][-1] == ARGV_B
    assert all(path.read_text() == raw for path, raw in files)


def test_context_is_neither_global_by_field_nor_global_by_value(project: Path) -> None:
    observations_left = {
        "custom.alpha": [{"value": CANARY_A, "source": {"type": "cli", "key": "--api-key"}}],
        "custom.beta": [{"value": CANARY_A, "source": {"type": "cli", "key": "--beta"}}],
    }
    observations_right = {
        "custom.alpha": [{"value": CANARY_B, "source": {"type": "cli", "key": "--alpha"}}],
        "custom.beta": [{"value": CANARY_B, "source": {"type": "cli", "key": "--beta"}}],
    }
    write_record(project, LEFT, value=None, observations=observations_left)
    write_record(project, RIGHT, value=None, observations=observations_right)
    result, _ = invoke(project, arguments())
    changes = {change["path"]: change for change in json.loads(result.stdout)["changes"]}
    assert changes["custom.alpha"]["a"] == MARKER
    assert changes["custom.alpha"]["b"] == CANARY_B
    assert changes["custom.beta"]["a"] == CANARY_A
    assert changes["custom.beta"]["b"] == CANARY_B


def test_losing_private_alternative_does_not_override_effective_public_source(
    project: Path,
) -> None:
    for run_id, value in [(LEFT, CANARY_A), (RIGHT, CANARY_B)]:
        write_record(
            project,
            run_id,
            value=None,
            observations={
                FIELD: [
                    {"value": value, "source": {"type": "cli", "key": "--api-key"}},
                    {"value": value, "source": {"type": "cli", "key": "--label"}},
                ]
            },
        )
    native = runtime.invoke_cli(arguments(), project)
    result, diagnostics = invoke(project, arguments())
    assert result.stdout == native.stdout and not diagnostics


def test_same_private_values_remain_no_value_drift(project: Path) -> None:
    source = {"type": "cli", "key": "--api-key"}
    write_record(project, LEFT, value=CANARY_A, source=source)
    write_record(project, RIGHT, value=CANARY_A, source=source)
    native = runtime.invoke_cli(arguments(), project)
    result, diagnostics = invoke(project, arguments())
    assert result.stdout == native.stdout and not diagnostics
    assert not any(change["path"] == FIELD for change in json.loads(result.stdout)["changes"])


@pytest.mark.parametrize(
    "arguments_extra", [("--min-severity", "HIGH"), ("--min-severity", "MEDIUM_HIGH")]
)
def test_filter_summary_order_notes_and_gate_remain_native(
    project: Path, arguments_extra: tuple[str, str]
) -> None:
    source = {"type": "cli", "key": "--api-key"}
    write_record(project, LEFT, value=CANARY_A, source=source)
    write_record(project, RIGHT, value=CANARY_B, source=source)
    argv = arguments("json", *arguments_extra, "--fail-on", "HIGH")
    native = runtime.invoke_cli(argv, project)
    result, _ = invoke(project, argv)
    assert result.exit_code == native.exit_code == 1
    assert invariants(json.loads(result.stdout)) == invariants(json.loads(native.stdout))


def test_missing_input_keeps_native_usage_error_and_restores_all_bindings(project: Path) -> None:
    import reprollm.cli.diff as commands
    import reprollm.diff.inputs as inputs

    originals = (
        commands._report,
        commands.load_input,
        commands.from_selected_run,
        commands.sanitize_report,
        inputs.read_run,
        inputs.read_run_record,
    )
    argv = arguments(inputs=(LEFT, RIGHT))
    native = runtime.invoke_cli(argv, project)
    result, diagnostics = invoke(project, argv)
    assert result.exit_code == native.exit_code == 2
    assert (result.stdout, result.stderr) == (native.stdout, native.stderr) and not diagnostics
    assert originals == (
        commands._report,
        commands.load_input,
        commands.from_selected_run,
        commands.sanitize_report,
        inputs.read_run,
        inputs.read_run_record,
    )


@pytest.mark.parametrize("format", ["json", "text"])
def test_inline_flags_keep_native_existing_redaction(project: Path, format: str) -> None:
    write_record(project, LEFT, value=32, argv=["python", "eval.py", "--api-key=" + ARGV_A])
    write_record(project, RIGHT, value=48, argv=["python", "eval.py", "--api-key=" + ARGV_B])
    argv = arguments(format)
    native = runtime.invoke_cli(argv, project)
    result, _ = invoke(project, argv)
    assert (result.exit_code, result.stdout, result.stderr) == (
        native.exit_code,
        native.stdout,
        native.stderr,
    )
    assert ARGV_A not in result.stdout and ARGV_B not in result.stdout


@pytest.mark.parametrize("format", ["json", "text"])
@pytest.mark.parametrize(
    "source",
    [
        {"type": "config", "key": "api_key:label", "path": "configs/colon:name.yaml"},
        {"type": "config", "key": "label", "path": "configs/api_key:transport.yaml"},
    ],
)
def test_source_metadata_is_not_misparsed_as_the_bound_value_context(
    project: Path, format: str, source: dict[str, Any]
) -> None:
    write_record(project, LEFT, value=CANARY_A, source=source)
    write_record(project, RIGHT, value=CANARY_B, source=source)
    argv = arguments(format)
    native = runtime.invoke_cli(argv, project)
    result, diagnostics = invoke(project, argv)
    assert (result.exit_code, result.stdout, result.stderr) == (
        native.exit_code,
        native.stdout,
        native.stderr,
    )
    assert CANARY_A in result.stdout and CANARY_B in result.stdout and not diagnostics


@pytest.mark.parametrize("side", ["a", "b"])
def test_added_removed_private_values_mask_only_the_present_side(project: Path, side: str) -> None:
    source = {"type": "env", "key": "OPENAI_API_KEY"}
    for position, run_id in [("a", LEFT), ("b", RIGHT)]:
        write_record(
            project,
            run_id,
            value=CANARY_A,
            source=source,
            observations=None if side == position else {},
        )
    native = runtime.invoke_cli(arguments(), project)
    result, diagnostics = invoke(project, arguments())
    original = json.loads(native.stdout)
    safe = json.loads(result.stdout)
    assert invariants(safe) == invariants(original) and diagnostics
    changed = next(change for change in safe["changes"] if change["path"] == FIELD)
    assert changed[side] == MARKER
    assert changed["b" if side == "a" else "a"] is None


@pytest.mark.parametrize("left,right", [(0, False), (False, None), ([], {}), ([False, 0], [None])])
def test_public_scalar_and_container_types_preserve_complete_native_report(
    project: Path, left: Any, right: Any
) -> None:
    write_record(project, LEFT, value=left)
    write_record(project, RIGHT, value=right)
    native = runtime.invoke_cli(arguments(), project)
    result, diagnostics = invoke(project, arguments())
    assert (result.exit_code, result.stdout, result.stderr) == (
        native.exit_code,
        native.stdout,
        native.stderr,
    )
    assert not diagnostics


def test_freeform_source_value_shape_gets_no_observation_privilege(project: Path) -> None:
    for run_id, value in [(LEFT, CANARY_A), (RIGHT, CANARY_B)]:
        write_record(
            project,
            run_id,
            value={"ordinary": {"value": value, "source": {"type": "cli", "key": "--api-key"}}},
        )
    native = runtime.invoke_cli(arguments(), project)
    result, diagnostics = invoke(project, arguments())
    assert result.stdout == native.stdout and not diagnostics
    assert CANARY_A in result.stdout and CANARY_B in result.stdout


@pytest.mark.parametrize("format", ["json", "text"])
def test_relative_and_external_run_files_keep_their_exact_source_scope(
    project: Path, tmp_path: Path, format: str
) -> None:
    external = tmp_path / "external 记录"
    external.mkdir()
    left, left_raw = write_record(
        external, LEFT, value=CANARY_A, source={"type": "cli", "key": "--api-key"}
    )
    right, right_raw = write_record(project, RIGHT, value=CANARY_B)
    argv = arguments(format, inputs=(str(left), str(right.relative_to(project))))
    native = runtime.invoke_cli(
        arguments("json", inputs=(str(left), str(right.relative_to(project)))), project
    )
    result, _ = invoke(project, argv)
    assert result.exit_code == native.exit_code == 0
    assert CANARY_A not in result.stdout and CANARY_B in result.stdout
    assert left.read_text() == left_raw and right.read_text() == right_raw
    if format == "json":
        assert invariants(json.loads(result.stdout)) == invariants(json.loads(native.stdout))


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("format", ["json", "text"])
def test_lock_run_combinations_use_native_resolution_and_private_run_side(
    project: Path, reverse: bool, format: str
) -> None:
    import yaml

    from reprollm.schemas.lock import Lock

    lock = project / "baseline.lock"
    data = {
        "schema_version": 1,
        "reprollm_version": "0.7.0",
        "generated_at": "2026-10-30T00:00:00Z",
        "manifest_sha256": "sha256:" + "a" * 64,
        "resolution": {"mode": "offline"},
    }
    Lock.model_validate(data)
    lock.write_text(yaml.safe_dump(data))
    run, raw = write_record(
        project, RIGHT, value=CANARY_A, source={"type": "cli", "key": "--api-key"}
    )
    pair = (str(lock), str(run))
    if reverse:
        pair = pair[::-1]
    native = runtime.invoke_cli(arguments("json", inputs=pair), project)
    result, diagnostics = invoke(project, arguments(format, inputs=pair))
    assert result.exit_code == native.exit_code == 0
    assert CANARY_A not in result.stdout and diagnostics
    if format == "json":
        assert invariants(json.loads(result.stdout)) == invariants(json.loads(native.stdout))
    assert run.read_text() == raw and yaml.safe_load(lock.read_text()) == data


@pytest.mark.parametrize("error", [RuntimeError("synthetic callback failure"), KeyboardInterrupt()])
def test_callback_failure_always_restores_native_module_bindings(
    project: Path, error: BaseException
) -> None:
    import reprollm.cli.diff as commands
    import reprollm.diff.inputs as inputs

    originals = (
        commands._report,
        commands.load_input,
        commands.from_selected_run,
        commands.sanitize_report,
        inputs.read_run,
        inputs.read_run_record,
    )

    def fail(argv: list[str], root: Path) -> runtime.CliResult:
        raise error

    with pytest.raises(type(error)):
        display.invoke_private_diff(
            arguments(), project, invoke_cli=fail, sanitize=lambda value, _: value
        )
    assert originals == (
        commands._report,
        commands.load_input,
        commands.from_selected_run,
        commands.sanitize_report,
        inputs.read_run,
        inputs.read_run_record,
    )


def test_projection_failure_does_not_emit_raw_values_and_restores_bindings(project: Path) -> None:
    import reprollm.cli.diff as commands
    import reprollm.diff.inputs as inputs

    write_record(project, LEFT, value=CANARY_A)
    write_record(project, RIGHT, value=CANARY_B)
    originals = (
        commands._report,
        commands.load_input,
        commands.from_selected_run,
        commands.sanitize_report,
        inputs.read_run,
        inputs.read_run_record,
    )

    def fail(value: Any, diagnostics: list[dict[str, Any]]) -> Any:
        raise ValueError("synthetic projection failure")

    result, _ = display.invoke_private_diff(
        arguments(), project, invoke_cli=runtime.invoke_cli, sanitize=fail
    )
    assert result.exit_code == 3 and CANARY_A not in result.stdout and CANARY_B not in result.stdout
    assert originals == (
        commands._report,
        commands.load_input,
        commands.from_selected_run,
        commands.sanitize_report,
        inputs.read_run,
        inputs.read_run_record,
    )


def test_missing_typed_context_fails_closed_without_raw_output(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import reprollm.cli.diff as commands
    from reprollm.diff.inputs import DiffInput

    write_record(project, LEFT, value=CANARY_A, source={"type": "cli", "key": "--api-key"})
    write_record(project, RIGHT, value=CANARY_B, source={"type": "cli", "key": "--api-key"})
    original = commands.load_input

    def disconnected(value: str, root: Path) -> DiffInput:
        # A future native loader that bypasses the known reader seam must not
        # silently fall back to uncontextualized secret display.
        from reprollm.diff.inputs import from_selected_run
        from reprollm.run.reader import read_run

        record, _ = read_run(root, value)
        return from_selected_run(record, root / ".reprollm/runs" / record.run_id)

    monkeypatch.setattr(commands, "load_input", disconnected)
    result, _ = invoke(project, arguments())
    assert result.exit_code == 3
    assert CANARY_A not in result.stdout and CANARY_B not in result.stdout
    assert commands.load_input is disconnected
    monkeypatch.setattr(commands, "load_input", original)


def test_incomplete_projection_fails_closed_before_native_output(project: Path) -> None:
    write_record(project, LEFT, value=CANARY_A)
    write_record(project, RIGHT, value=CANARY_B)
    result, _ = display.invoke_private_diff(
        arguments(),
        project,
        invoke_cli=runtime.invoke_cli,
        sanitize=lambda value, diagnostics: {"bindings_observed": {}},
    )
    assert result.exit_code == 3
    assert CANARY_A not in result.stdout and CANARY_B not in result.stdout


def test_latest_selection_keeps_private_side_context(project: Path) -> None:
    write_record(project, LEFT, value=CANARY_A, source={"type": "cli", "key": "--api-key"})
    write_record(project, RIGHT, value=CANARY_B, source={"type": "cli", "key": "--label"})
    argv = [
        "diff",
        "--format",
        "json",
        "--latest-successful",
        "--name",
        "pair",
        "--fail-on",
        "HIGH",
    ]
    native = runtime.invoke_cli(argv, project)
    result, diagnostics = invoke(project, argv)
    assert result.exit_code == native.exit_code == 1
    safe = json.loads(result.stdout)
    assert invariants(safe) == invariants(json.loads(native.stdout)) and diagnostics
    value = next(change for change in safe["changes"] if change["path"] == FIELD)
    assert value["a"] == MARKER and value["b"] == CANARY_B


def test_module_import_needs_only_standard_library() -> None:
    program = (
        "import sys;sys.path.insert(0,sys.argv[1]);import skill_diff_display;"
        "assert not any(name=='reprollm' or name.startswith('reprollm.') "
        "for name in sys.modules);assert 'pydantic' not in sys.modules"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-B", "-c", program, str(SCRIPTS)],
        check=False,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 0 and not result.stdout and not result.stderr
