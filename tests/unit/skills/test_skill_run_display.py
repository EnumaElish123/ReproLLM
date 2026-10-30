"""Historical run display preserves native formatting without exposing contextual secrets."""

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
import skill_run_display as display  # noqa: E402
import skill_runtime as runtime  # noqa: E402

RUN_ID = "20261030T010000Z-aaaaaa"
CANARY = "SyntheticLegacyDisplayCanary12345"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "研究 project"
    root.mkdir()
    return root


def record(
    root: Path,
    *,
    argv: list[str] | None = None,
    field: str = "custom.alpha",
    source: dict[str, Any] | None = None,
    value: Any = "public-value",
) -> tuple[Path, str]:
    from reprollm.schemas.run_record import RunRecord

    payload = {
        "schema_version": 1,
        "reprollm_version": "0.6.1",
        "run_id": RUN_ID,
        "name": "public experiment",
        "status": "completed",
        "exit_code": 0,
        "duration_seconds": 1.25,
        "command": {"argv": ["python", "eval.py"] if argv is None else argv, "cwd": "."},
        "bindings_observed": {
            field: [{"value": value, "source": source or {"type": "cli", "key": "--alpha"}}]
        },
        "warnings": ["public warning"],
    }
    RunRecord.model_validate(payload)
    folder = root / ".reprollm/runs" / RUN_ID
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "run.json"
    raw = json.dumps(payload, ensure_ascii=False) + "\n"
    path.write_text(raw)
    return path, raw


def sanitizer(value: Any, diagnostics: list[dict[str, Any]], root: Path) -> Any:
    return runtime._sanitize(value, root, action="runs.show", diagnostics=diagnostics)


def show(root: Path, run_id: str = RUN_ID) -> tuple[runtime.CliResult, list[dict[str, Any]]]:
    return display.invoke_private_show(
        ["runs", "show", "--", run_id],
        root,
        invoke_cli=runtime.invoke_cli,
        sanitize=lambda value, diagnostics: sanitizer(value, diagnostics, root),
    )


@pytest.mark.parametrize("kind", ["cli", "config", "env"])
@pytest.mark.parametrize("path_state", ["missing", "null", "relative"])
def test_public_observations_keep_original_native_text_and_file(
    project: Path, kind: str, path_state: str
) -> None:
    source: dict[str, Any] = {"type": kind, "key": "--alpha" if kind == "cli" else "alpha"}
    if path_state != "missing":
        source["path"] = None if path_state == "null" else "configs/options.yaml"
    path, original = record(project, source=source)
    native = runtime.invoke_cli(["runs", "show", RUN_ID], project)
    result, diagnostics = show(project)
    assert (result.exit_code, result.stdout, result.stderr) == (
        native.exit_code,
        native.stdout,
        native.stderr,
    )
    assert diagnostics == []
    assert path.read_text() == original


@pytest.mark.parametrize("value", [0, False, None, [0, False, None], {"visible": False}])
def test_public_value_types_keep_complete_original_native_text(project: Path, value: Any) -> None:
    path, original = record(project, value=value)
    native = runtime.invoke_cli(["runs", "show", RUN_ID], project)
    result, diagnostics = show(project)
    assert (result.exit_code, result.stdout, result.stderr) == (
        native.exit_code,
        native.stdout,
        native.stderr,
    )
    assert not diagnostics and path.read_text() == original


@pytest.mark.parametrize(
    "field,source",
    [
        ("custom.alpha", {"type": "cli", "key": "--api-key"}),
        ("custom.password", {"type": "config", "key": "credentials.password"}),
        ("custom.alpha", {"type": "env", "key": "PRIVATE_API_KEY"}),
    ],
)
def test_opaque_observation_is_masked_before_native_text_formatting(
    project: Path, field: str, source: dict[str, Any]
) -> None:
    path, original = record(project, field=field, source=source, value=CANARY)
    native = runtime.invoke_cli(["runs", "show", RUN_ID], project)
    assert CANARY in native.stdout
    result, diagnostics = show(project)
    assert result.exit_code == 0 and CANARY not in result.stdout
    assert "<REDACTED:generic_kv>" in result.stdout
    assert any(item["code"] == "display_value_transformation" for item in diagnostics)
    assert path.read_text() == original


@pytest.mark.parametrize(
    "argv,private",
    [
        (["python", "eval.py", "--api-key", CANARY], True),
        (["python", "eval.py", "--password", CANARY], True),
        (["python", "eval.py", "--api-key=" + CANARY], True),
        (["python", "eval.py", "--payload", json.dumps({"api_key": CANARY})], True),
        (["python", "eval.py", "", "--alpha", "literal"], False),
        ([], False),
    ],
)
def test_command_argv_context_and_public_spacing(
    project: Path, argv: list[str], private: bool
) -> None:
    path, original = record(project, argv=argv)
    native = runtime.invoke_cli(["runs", "show", RUN_ID], project)
    result, diagnostics = show(project)
    assert result.exit_code == native.exit_code == 0
    if private:
        assert CANARY in native.stdout and CANARY not in result.stdout
        assert diagnostics
    else:
        assert result.stdout == native.stdout and not diagnostics
    assert path.read_text() == original


def test_command_mask_uses_original_previous_flags_without_modifying_input() -> None:
    original = ["python", "--api-key", CANARY, "--alpha", "visible", ""]
    values = list(original)
    masked, count = display.mask_command_argv(values)
    assert values == original
    assert masked == ["python", "--api-key", "<REDACTED:generic_kv>", "--alpha", "visible", ""]
    assert count == 1


def test_replaced_flag_does_not_remove_context_from_the_next_original_token() -> None:
    original = ["python", "--password", "--api-key", CANARY]
    masked, count = display.mask_command_argv(original)
    assert CANARY not in masked and masked[-1] == "<REDACTED:generic_kv>" and count == 2
    assert original[-2:] == ["--api-key", CANARY]


def test_display_module_import_needs_only_standard_library() -> None:
    program = (
        "import sys;sys.path.insert(0,sys.argv[1]);import skill_run_display;"
        "assert not any(n=='reprollm' or n.startswith('reprollm.') or "
        "n=='pydantic' or n.startswith('pydantic.') for n in sys.modules)"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-S", "-c", program, str(SCRIPTS)],
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0 and not result.stdout and not result.stderr


@pytest.mark.parametrize(
    "name", ["HF_TOKEN", "OPENAI_API_KEY", "PRIVATE_API_KEY", "SSH_AUTH_SOCK", "KEY_FRAMES"]
)
@pytest.mark.parametrize("value", [CANARY, "short", "", False])
def test_formal_secret_env_names_hide_any_non_null_value(name: str, value: Any) -> None:
    masked, count = display.mask_secret_env_observation(value, "env", name)
    assert masked == "<REDACTED:generic_kv>" and count == 1


@pytest.mark.parametrize("name", ["LANG", "MAX_TOKENS", "TOKENIZERS_PARALLELISM"])
def test_public_environment_names_keep_values_and_types(name: str) -> None:
    for value in [CANARY, "", 0, False, None]:
        masked, count = display.mask_secret_env_observation(value, "env", name)
        assert masked == value and type(masked) is type(value) and count == 0


def test_formal_env_mask_keeps_null_and_its_own_marker() -> None:
    assert display.mask_secret_env_observation(None, "env", "HF_TOKEN") == (None, 0)
    assert display.mask_secret_env_observation("<REDACTED:generic_kv>", "env", "HF_TOKEN") == (
        "<REDACTED:generic_kv>",
        0,
    )
    assert display.mask_secret_env_observation(CANARY, "cli", "HF_TOKEN") == (CANARY, 0)


@pytest.mark.parametrize("name", ["HF_TOKEN", "OPENAI_API_KEY", "PRIVATE_API_KEY"])
def test_secret_environment_observation_is_masked_in_text(project: Path, name: str) -> None:
    path, original = record(project, source={"type": "env", "key": name}, value=CANARY)
    native = runtime.invoke_cli(["runs", "show", RUN_ID], project)
    assert CANARY in native.stdout
    result, diagnostics = show(project)
    assert CANARY not in result.stdout and "<REDACTED:generic_kv>" in result.stdout
    assert diagnostics and path.read_text() == original


@pytest.mark.parametrize("value", [None, "<REDACTED:generic_kv>"])
def test_unknown_or_already_private_env_value_keeps_native_text(project: Path, value: Any) -> None:
    path, original = record(project, source={"type": "env", "key": "HF_TOKEN"}, value=value)
    native = runtime.invoke_cli(["runs", "show", RUN_ID], project)
    result, diagnostics = show(project)
    assert (result.exit_code, result.stdout, result.stderr) == (
        native.exit_code,
        native.stdout,
        native.stderr,
    )
    assert not diagnostics and path.read_text() == original


def test_existing_secret_presence_metadata_is_not_a_bound_secret_value(project: Path) -> None:
    path, original = record(project)
    payload = json.loads(original)
    presence = {"HF_TOKEN": {"present": True}, "OPENAI_API_KEY": {"present": False}}
    payload["environment"] = {
        "os": "test",
        "platform": "linux",
        "python": "3.12",
        "hostname_sha256": "0" * 64,
        "env": presence,
    }
    safe = runtime._sanitize(payload, project, action="runs.show")
    assert safe["environment"]["env"] == presence
    assert path.read_text() == original


def test_source_descriptor_privacy_does_not_inherit_the_binding_key(project: Path) -> None:
    source = {"type": "config", "key": "credentials.password", "path": "configs/options.yaml"}
    path, original = record(project, field="custom.password", source=source, value=CANARY)
    result, _ = show(project)
    assert "config(configs/options.yaml:credentials.password)" in result.stdout
    assert CANARY not in result.stdout
    assert path.read_text() == original


def test_freeform_shape_never_receives_source_context_reset(project: Path) -> None:
    value = {"api_key": {"value": CANARY, "source": {"type": "cli", "key": "--safe"}}}
    path, original = record(project, value=value)
    result, diagnostics = show(project)
    assert CANARY not in result.stdout and diagnostics
    assert path.read_text() == original


def test_large_values_and_colliding_private_keys_keep_both_members(project: Path) -> None:
    first = "hf_" + "A" * 40
    second = "hf_" + "B" * 40
    value = {first: "公开" * 35_000 + " FIRST", second: "SECOND"}
    path, original = record(project, value=value)
    result, diagnostics = show(project)
    assert result.exit_code == 0
    assert first not in result.stdout and second not in result.stdout
    assert " FIRST" in result.stdout and "SECOND" in result.stdout
    line = next(line for line in result.stdout.splitlines() if line.startswith("Binding:"))
    rendered = json.loads(line.split(" = ", 1)[1].rsplit(" (", 1)[0])
    assert len(rendered) == 2
    assert any(item["code"] == "display_keys_disambiguated" for item in diagnostics)
    assert path.read_text() == original


def test_source_patterns_and_controls_are_sanitized_before_render(project: Path) -> None:
    secret = "sk-proj-" + "SyntheticSourceCanary" * 4
    source = {"type": "config", "key": "alpha", "path": "configs/" + secret + ".yaml"}
    path, original = record(project, source=source, value="public\u0001text")
    result, diagnostics = show(project)
    assert secret not in result.stdout and "\u0001" not in result.stdout
    assert diagnostics
    assert path.read_text() == original


@pytest.mark.parametrize("failure", ["invoke", "projection"])
def test_reader_hook_is_restored_even_if_display_fails(project: Path, failure: str) -> None:
    import reprollm.cli.runs as commands

    record(project)
    original = commands.read_run

    def broken(value: Any, diagnostics: list[dict[str, Any]]) -> Any:
        raise RuntimeError("synthetic projection failure")

    def invoke(argv: list[str], root: Path) -> runtime.CliResult:
        if failure == "invoke":
            raise RuntimeError("synthetic invocation failure")
        commands.read_run(root, RUN_ID)
        raise AssertionError("unreachable")

    with pytest.raises(RuntimeError, match="synthetic"):
        display.invoke_private_show(
            ["runs", "show", RUN_ID],
            project,
            invoke_cli=invoke,
            sanitize=broken,
        )
    assert commands.read_run is original


def test_original_usage_error_and_stderr_are_preserved(project: Path) -> None:
    import reprollm.cli.runs as commands

    original = commands.read_run
    native = runtime.invoke_cli(["runs", "show", "not-an-id"], project)
    result, diagnostics = show(project, "not-an-id")
    assert result.exit_code == native.exit_code == 2
    assert result.stdout == native.stdout and result.stderr == native.stderr
    assert not diagnostics and commands.read_run is original


def test_sanitizer_cannot_mutate_the_loaded_record(project: Path) -> None:
    import reprollm.cli.runs as commands

    record(project)
    original_record, original_raw = commands.read_run(project, RUN_ID)
    before = copy.deepcopy(original_record.model_dump(mode="json"))

    def destructive(value: Any, diagnostics: list[dict[str, Any]]) -> Any:
        value["command"]["argv"].append("projected-only")
        return value

    result, _ = display.invoke_private_show(
        ["runs", "show", RUN_ID],
        project,
        invoke_cli=runtime.invoke_cli,
        sanitize=destructive,
    )
    assert "projected-only" in result.stdout
    after, raw = commands.read_run(project, RUN_ID)
    assert raw == original_raw and after.model_dump(mode="json") == before
