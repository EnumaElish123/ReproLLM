"""InspectAI parser recovery through the public initialization commands."""

import ast
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

import reprollm
from reprollm.cli.main import app, cli

runner = CliRunner()

_PARSER_MARKER = "# synthetic-inspect-parser-recursion\n"


def _inspect_repo(root: Path) -> Path:
    root.mkdir()
    (root / "run.sh").write_text("inspect eval a_task.py\n", encoding="utf-8")
    (root / "a_task.py").write_text(
        _PARSER_MARKER + "from inspect_ai import task\n"
        "@task\n"
        "def zeta():\n"
        "    return None\n"
        "@task\n"
        "def alpha():\n"
        "    return None\n",
        encoding="utf-8",
    )
    (root / "z_task.py").write_text(
        "from inspect_ai import task\n@task\ndef alpha():\n    return None\n",
        encoding="utf-8",
    )
    return root


def _input_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def _fail_independent_parse(
    monkeypatch: pytest.MonkeyPatch, failure: Exception, *, include_primary: bool = False
) -> None:
    original_parse = ast.parse

    def limited_parse(
        source: str | bytes,
        filename: str = "<unknown>",
        mode: str = "exec",
        **kwargs: Any,
    ) -> ast.AST:
        if (
            (filename == "<unknown>" or include_primary)
            and isinstance(source, str)
            and _PARSER_MARKER in source
        ):
            raise failure
        return original_parse(source, filename=filename, mode=mode, **kwargs)

    monkeypatch.setattr(ast, "parse", limited_parse)


@pytest.mark.security
def test_list_tasks_recovers_inspect_names_after_parser_recursion_without_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _inspect_repo(tmp_path / "inspect-recovery")
    before = _input_bytes(repo)
    canary = f"SyntheticInspectParserSecretCanary {repo / 'private-source.py'}"
    _fail_independent_parse(monkeypatch, RecursionError(canary))

    result = runner.invoke(app, ["init", str(repo), "--list-tasks"])

    assert result.exit_code == 0, result.output
    assert result.stdout == "alpha\nzeta\n"
    assert result.stderr == ""
    assert canary not in result.stdout + result.stderr
    assert str(repo) not in result.stdout + result.stderr
    assert _input_bytes(repo) == before
    assert not (repo / "reprollm.yaml").exists()
    assert not (repo / ".reprollm").exists()


def _additional_decorators(repo: Path) -> None:
    path = repo / "a_task.py"
    path.write_text(
        path.read_text(encoding="utf-8") + "@task()\ndef called():\n    return None\n"
        "@inspect_ai.task\ndef qualified():\n    return None\n"
        "@task\nasync def asynchronous():\n    return None\n",
        encoding="utf-8",
    )


def test_normal_inspect_ast_keeps_supported_decorator_forms(tmp_path: Path) -> None:
    repo = _inspect_repo(tmp_path / "inspect-recovery")
    _additional_decorators(repo)
    before = _input_bytes(repo)

    result = runner.invoke(app, ["init", str(repo), "--list-tasks"])

    assert result.exit_code == 0, result.output
    assert result.stdout == "alpha\nasynchronous\ncalled\nqualified\nzeta\n"
    assert result.stderr == ""
    assert _input_bytes(repo) == before
    assert not (repo / ".reprollm").exists()


def test_inspect_parser_does_not_reopen_excluded_or_over_read_cap_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _inspect_repo(tmp_path / "inspect-recovery")
    selected = repo / "a_task.py"
    selected.write_text(
        selected.read_text(encoding="utf-8").replace(_PARSER_MARKER, ""), encoding="utf-8"
    )
    hidden_source = (
        _PARSER_MARKER + "from inspect_ai import task\n@task\ndef hidden():\n    return None\n"
    )
    for directory in (".venv", "__pycache__", "custom_environment"):
        excluded = repo / directory
        excluded.mkdir()
        (excluded / "hidden.py").write_text(hidden_source, encoding="utf-8")
    (repo / "custom_environment" / "pyvenv.cfg").write_text("home = synthetic\n", encoding="utf-8")
    (repo / "over_cap.py").write_text(hidden_source + "#" + "x" * (512 * 1024), encoding="utf-8")
    before = _input_bytes(repo)
    _fail_independent_parse(
        monkeypatch, MemoryError("excluded source must not reach the parser"), include_primary=True
    )

    result = runner.invoke(app, ["init", str(repo), "--list-tasks"])

    assert result.exit_code == 0, result.output
    assert result.stdout == "alpha\nzeta\n"
    assert result.stderr == ""
    assert _input_bytes(repo) == before
    assert not (repo / ".reprollm").exists()


def test_inspect_fallback_respects_real_file_budget_and_coverage_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _inspect_repo(tmp_path / "inspect-recovery")
    (repo / "z_task.py").rename(repo / "b_task.py")
    for index in range(498):
        (repo / f"m_{index:04}.py").write_text("value = 1\n", encoding="utf-8")
    (repo / "z_omitted.py").write_text(
        _PARSER_MARKER
        + "from inspect_ai import task\n@task\ndef not_selected():\n    return None\n",
        encoding="utf-8",
    )
    before = _input_bytes(repo)
    _fail_independent_parse(monkeypatch, RecursionError("controlled independent parser failure"))

    result = runner.invoke(app, ["-v", "init", str(repo), "--list-tasks"])

    assert result.exit_code == 0, result.output
    assert result.stdout == "alpha\nzeta\n"
    assert result.stderr == (
        "scan: Python analysis incomplete: parsed 500 of 501 candidate files; selected 500 "
        "(limit 500), omitted 1. Missing signals may be in unanalysed files.\n"
    )
    assert _input_bytes(repo) == before
    assert not (repo / ".reprollm").exists()


@pytest.mark.security
def test_secret_looking_recovered_task_name_is_neither_listed_nor_persisted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _inspect_repo(tmp_path / "inspect-recovery")
    secret_name = "hf_" + "a" * 40
    source = repo / "a_task.py"
    source.write_text(
        source.read_text(encoding="utf-8") + f"@task\ndef {secret_name}():\n    return None\n",
        encoding="utf-8",
    )
    before = _input_bytes(repo)
    _fail_independent_parse(monkeypatch, RecursionError("controlled independent parser failure"))

    listed = runner.invoke(app, ["init", str(repo), "--list-tasks"])

    assert listed.exit_code == 0, listed.output
    assert listed.stdout == "alpha\nzeta\n"
    assert listed.stderr == ""
    selected = runner.invoke(app, ["init", str(repo), "--task", "zeta"])
    assert selected.exit_code == 0, selected.output
    assert selected.stderr == ""
    text = (repo / "reprollm.yaml").read_text(encoding="utf-8")
    assert secret_name not in text + listed.stdout + selected.stdout
    manifest = yaml.safe_load(text)
    assert [metric["name"] for metric in manifest["evaluation"]["metrics"]] == ["zeta"]
    after = _input_bytes(repo)
    assert {name: after[name] for name in before} == before


def test_native_inspect_parser_recursion_lists_tasks_without_changing_recursion_limit(
    tmp_path: Path,
) -> None:
    source = (
        "from inspect_ai import task\n@task\ndef recovered():\n    return None\n"
        + "value = "
        + " + ".join(["value"] * 10000)
        + "\n"
    )
    assert len(source.encode("utf-8")) == 80073
    probe_code = (
        "import ast, sys\n"
        "try:\n"
        "    ast.parse(sys.stdin.read())\n"
        "except RecursionError:\n"
        "    print('recursion')\n"
        "else:\n"
        "    print('parsed')\n"
    )
    try:
        probe = subprocess.run(
            [sys.executable, "-c", probe_code],
            input=source,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        pytest.skip("Native AST probe exceeded 30 seconds; no native recovery proof is claimed.")
    if probe.returncode < 0 or (sys.platform == "win32" and probe.returncode & 0x80000000):
        pytest.skip(
            f"Native AST probe exited with process failure {probe.returncode}; "
            "this fix only handles catchable Python parser RecursionError."
        )
    assert probe.returncode == 0 and probe.stderr == "", probe.stderr
    if probe.stdout == "parsed\n":
        pytest.skip(
            "This interpreter parses the native source; external boundary injection covers "
            "parser RecursionError without changing its recursion limit."
        )
    assert probe.stdout == "recursion\n"
    repo = _inspect_repo(tmp_path / "inspect-recovery")
    (repo / "a_task.py").write_text(source, encoding="utf-8")
    before = _input_bytes(repo)
    source_root = Path(reprollm.__file__).resolve().parent.parent
    console_code = (
        "import sys; sys.path.insert(0, sys.argv.pop(1)); from reprollm.cli.main import cli; cli()"
    )

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            console_code,
            str(source_root),
            "init",
            ".",
            "--list-tasks",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "alpha\nrecovered\n"
    assert result.stderr == ""
    assert _input_bytes(repo) == before
    assert not (repo / ".reprollm").exists()


@pytest.mark.parametrize("failure_type", [SyntaxError, RecursionError])
def test_inspect_fallback_preserves_existing_bare_decorator_grammar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure_type: type[Exception]
) -> None:
    repo = _inspect_repo(tmp_path / "inspect-recovery")
    _additional_decorators(repo)
    before = _input_bytes(repo)
    _fail_independent_parse(monkeypatch, failure_type("controlled independent parser failure"))

    result = runner.invoke(app, ["init", str(repo), "--list-tasks"])

    assert result.exit_code == 0, result.output
    assert result.stdout == "alpha\nzeta\n"
    assert result.stderr == ""
    assert _input_bytes(repo) == before
    assert not (repo / ".reprollm").exists()


def test_inspect_cli_signal_recovers_tasks_after_primary_and_independent_parser_recursion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _inspect_repo(tmp_path / "inspect-recovery")
    (repo / "z_task.py").write_text("value = 1\n", encoding="utf-8")
    before = _input_bytes(repo)
    _fail_independent_parse(
        monkeypatch, RecursionError("SyntheticInspectParserSecretCanary"), include_primary=True
    )

    result = runner.invoke(app, ["-v", "init", str(repo), "--list-tasks"])

    assert result.exit_code == 0, result.output
    assert result.stdout == "alpha\nzeta\n"
    assert result.stderr == ""
    assert _input_bytes(repo) == before
    assert not (repo / ".reprollm").exists()


@pytest.mark.parametrize("failure_type", [MemoryError, RuntimeError])
def test_independent_inspect_parser_unrelated_errors_are_not_swallowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure_type: type[Exception]
) -> None:
    repo = _inspect_repo(tmp_path / "inspect-recovery")
    before = _input_bytes(repo)
    failure = failure_type("controlled independent parser failure")
    _fail_independent_parse(monkeypatch, failure)

    result = runner.invoke(app, ["init", str(repo), "--list-tasks"])

    assert result.exit_code != 0
    assert result.exception is failure
    assert result.stdout == result.stderr == ""
    assert _input_bytes(repo) == before
    assert not (repo / ".reprollm").exists()


def test_independent_inspect_tree_walk_recursion_is_not_a_parser_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _inspect_repo(tmp_path / "inspect-recovery")
    before = _input_bytes(repo)
    original_parse = ast.parse
    original_walk = ast.walk
    independent_tree: ast.AST | None = None
    failure = RecursionError("controlled independent tree-walk failure")

    def marked_parse(
        source: str | bytes,
        filename: str = "<unknown>",
        mode: str = "exec",
        **kwargs: Any,
    ) -> ast.AST:
        nonlocal independent_tree
        tree = original_parse(source, filename=filename, mode=mode, **kwargs)
        if filename == "<unknown>" and isinstance(source, str) and _PARSER_MARKER in source:
            independent_tree = tree
        return tree

    def limited_walk(node: ast.AST) -> Iterator[ast.AST]:
        if node is independent_tree:
            raise failure
        return original_walk(node)

    monkeypatch.setattr(ast, "parse", marked_parse)
    monkeypatch.setattr(ast, "walk", limited_walk)

    result = runner.invoke(app, ["init", str(repo), "--list-tasks"])

    assert result.exit_code != 0
    assert result.exception is failure
    assert result.stdout == result.stderr == ""
    assert _input_bytes(repo) == before
    assert not (repo / ".reprollm").exists()


def test_init_keeps_recovered_candidates_without_declaring_unselected_metrics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _inspect_repo(tmp_path / "inspect-recovery")
    before = _input_bytes(repo)
    _fail_independent_parse(monkeypatch, RecursionError("controlled independent parser failure"))

    result = runner.invoke(app, ["init", str(repo)])

    assert result.exit_code == 0, result.output
    assert result.stderr == ""
    manifest = yaml.safe_load((repo / "reprollm.yaml").read_text(encoding="utf-8"))
    assert manifest["experiment"]["profiles"] == ["evaluation"]
    assert manifest["evaluation"]["metrics"] == []
    assert "Task candidates: 2; selected: 0" in result.stdout
    assert "--task NAME" in result.stdout
    after = _input_bytes(repo)
    assert {name: after[name] for name in before} == before
    assert set(after) - set(before) == {
        "reprollm.yaml",
        ".reprollm/config.yaml",
        ".reprollm/project-rules.yaml",
    }


def test_selected_recovered_tasks_are_sorted_unique_and_repeatable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _inspect_repo(tmp_path / "inspect-recovery")
    before = _input_bytes(repo)
    _fail_independent_parse(monkeypatch, RecursionError("controlled independent parser failure"))
    args = ["init", str(repo), "--task", "zeta", "--task", "alpha", "--task", "zeta"]

    first = runner.invoke(app, args)

    assert first.exit_code == 0, first.output
    assert first.stderr == ""
    original_manifest = (repo / "reprollm.yaml").read_bytes()
    manifest = yaml.safe_load(original_manifest)
    assert [metric["name"] for metric in manifest["evaluation"]["metrics"]] == ["alpha", "zeta"]
    assert all(metric.get("implementation") is None for metric in manifest["evaluation"]["metrics"])
    assert "verify tasks and set implementation" in original_manifest.decode("utf-8")
    assert "Task candidates: 2; selected: 2" in first.stdout
    repeated = runner.invoke(
        app, ["init", str(repo), "--force", "--task", "alpha", "--task", "zeta"]
    )
    assert repeated.exit_code == 0, repeated.output
    assert repeated.stderr == ""
    assert (repo / "reprollm.yaml").read_bytes() == original_manifest
    assert {name: _input_bytes(repo)[name] for name in before} == before


def test_explicit_inference_retains_recovered_inventory_without_evaluation_declarations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _inspect_repo(tmp_path / "inspect-recovery")
    _fail_independent_parse(monkeypatch, RecursionError("controlled independent parser failure"))

    result = runner.invoke(app, ["init", str(repo), "--profiles", "inference"])

    assert result.exit_code == 0, result.output
    manifest = yaml.safe_load((repo / "reprollm.yaml").read_text(encoding="utf-8"))
    assert manifest["experiment"]["profiles"] == ["inference"]
    assert "evaluation" not in manifest
    assert "Task candidates: 2; selected: 0" in result.stdout
    assert result.stderr == ""


@pytest.mark.parametrize(
    "selectors",
    [
        pytest.param(["--task", "zeta", "--task", "missing"], id="unknown-name"),
        pytest.param(["--task", "sk-" + "a" * 40], id="unsafe-name"),
        pytest.param(["--profiles", "inference", "--task", "zeta"], id="incompatible-profile"),
    ],
)
def test_invalid_recovered_task_selection_exits_two_before_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    selectors: list[str],
) -> None:
    repo = _inspect_repo(tmp_path / "inspect-recovery")
    before = _input_bytes(repo)
    canary = "SyntheticInspectParserSecretCanary"
    _fail_independent_parse(monkeypatch, RecursionError(canary))
    monkeypatch.setattr(sys, "argv", ["reprollm", "init", str(repo), *selectors])

    with pytest.raises(SystemExit) as raised:
        cli()

    assert raised.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("error: ")
    assert canary not in captured.err
    assert "sk-" + "a" * 40 not in captured.err
    assert _input_bytes(repo) == before
    assert not (repo / ".reprollm").exists()
