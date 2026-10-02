"""Generate the resource-free CLI walkthrough required by M8-T02.

Run every documented command in a disposable copy; never execute eval.py or
replace the reviewed manifest and lock in the shipped example.
"""

from __future__ import annotations

import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Step:
    title: str
    command: list[str]
    stdout: str
    stderr: str
    exit_code: int
    elapsed_seconds: float
    report_json: str = ""


def _env() -> dict[str, str]:
    # Child commands need executable lookup and platform temp locations, not
    # credentials inherited from a developer's interactive shell.
    # getpass needs these on Windows, where pwd is absent. Runtime privacy
    # uses this identity to remove usernames from captured artifacts.
    names = (
        "PATH",
        "PYTHONPATH",
        "SystemRoot",
        "WINDIR",
        "PATHEXT",
        "TMPDIR",
        "TEMP",
        "TMP",
        "LOGNAME",
        "USER",
        "LNAME",
        "USERNAME",
    )
    env = {name: os.environ[name] for name in names if name in os.environ}
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    env.update(
        {
            "COLUMNS": "80",
            "LINES": "24",
            "TERMINAL_WIDTH": "80",
            "TERM": "dumb",
            "NO_COLOR": "1",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
        }
    )
    return env


def _run(args: list[str], cwd: Path, title: str = "") -> Step:
    command = [sys.executable, "-c", "from reprollm.cli.main import cli; cli()", *args]
    started = time.monotonic()
    result = subprocess.run(command, cwd=cwd, capture_output=True, encoding="utf-8", env=_env())
    if result.returncode not in (0, 1):
        raise RuntimeError(f"reprollm {' '.join(args)} failed: {result.stderr}")
    report = result.stdout if "--format" in args and "json" in args else ""
    return Step(
        title,
        args,
        result.stdout.rstrip(),
        result.stderr.rstrip(),
        result.returncode,
        time.monotonic() - started,
        report,
    )


def _git(work: Path, *args: str) -> None:
    env = _env()
    env.update(
        {
            "GIT_AUTHOR_NAME": "Tour",
            "GIT_AUTHOR_EMAIL": "tour@example.invalid",
            "GIT_COMMITTER_NAME": "Tour",
            "GIT_COMMITTER_EMAIL": "tour@example.invalid",
            "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
            "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z",
        }
    )
    subprocess.run(
        ["git", "-c", "core.autocrlf=false", "-c", "commit.gpgsign=false", *args],
        cwd=work,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def prepare(work: Path) -> None:
    shutil.copytree(
        ROOT / "examples/hf_vllm_eval",
        work,
        ignore=shutil.ignore_patterns(
            "reprollm.yaml", "reprollm.lock", ".reprollm", "REPRODUCIBILITY*"
        ),
    )
    shutil.copyfile(ROOT / "scripts/capture_probe.py", work / "capture_probe.py")
    with (work / ".gitignore").open("a", encoding="utf-8", newline="\n") as handle:
        handle.write("\n.reprollm/runs/\nREPRODUCIBILITY.md\n")
    _git(work, "init", "-q", "-b", "main")
    _git(work, "add", "-A")
    _git(work, "commit", "-qm", "Prepare capture exercise")


def manifest_text(max_tokens: int = 32) -> str:
    fixture = ROOT / "tests/fixtures/repos/hf_vllm_eval/manifests/complete.yaml"
    manifest = yaml.safe_load(fixture.read_text(encoding="utf-8"))
    manifest["project"]["name"] = "capture-tour"
    manifest["generation"]["max_tokens"] = max_tokens
    manifest["execution"]["command"] = "python capture_probe.py --config configs/capture.json"
    manifest["execution"]["config_files"] = ["configs/capture.json"]
    manifest["bindings"] = {
        "generation.temperature": {"config": "configs/capture.json:generation.temperature"},
        "generation.max_tokens": {"config": "configs/capture.json:generation.max_tokens"},
    }
    return str(yaml.safe_dump(manifest, sort_keys=False, width=100))


def config_text(max_tokens: int = 32) -> str:
    return (
        json.dumps({"generation": {"temperature": 0.0, "max_tokens": max_tokens}}, indent=2) + "\n"
    )


def _fill(work: Path, max_tokens: int) -> None:
    (work / "reprollm.yaml").write_text(manifest_text(max_tokens), encoding="utf-8", newline="\n")
    (work / "configs/capture.json").write_text(
        config_text(max_tokens), encoding="utf-8", newline="\n"
    )


def _capture(work: Path, label: str) -> tuple[Step, str]:
    before = set(work.glob(".reprollm/runs/*/run.json"))
    step = _run(
        [
            "run",
            "--name",
            label,
            "--capture-output",
            "--",
            "python",
            "capture_probe.py",
            "--config",
            "configs/capture.json",
        ],
        work,
        f"Capture {label} (standard-library probe)",
    )
    created = set(work.glob(".reprollm/runs/*/run.json")) - before
    if len(created) != 1:
        raise RuntimeError("capture must create exactly one run record")
    return step, created.pop().parent.name


def run_workflow(work: Path) -> list[Step]:
    prepare(work)
    records = [
        _run(
            ["audit", ".", "--no-color", "--format", "json"],
            work,
            "Audit before initialization: Level 0",
        )
    ]
    records.append(_run(["init", "."], work, "Create a scaffold"))
    records.append(
        _run(
            ["audit", ".", "--no-color", "--format", "json"], work, "Inspect the scaffold: Level 1"
        )
    )
    _fill(work, 32)
    records.append(
        _run(
            ["audit", ".", "--no-color", "--format", "json"],
            work,
            "Audit the filled declaration: Level 1",
        )
    )
    records.append(_run(["lock", ".", "--offline"], work, "Hash inputs without network resolution"))
    records.append(_run(["lock", ".", "--check"], work, "Check manifest and rule freshness"))
    _git(work, "add", "-A")
    _git(work, "commit", "-qm", "Declare capture a")
    step, run_a = _capture(work, "capture-a")
    records.append(step)
    _fill(work, 48)
    records.append(
        _run(["lock", ".", "--offline"], work, "Record the intentional parameter change")
    )
    _git(work, "add", "-A")
    _git(work, "commit", "-qm", "Declare capture b")
    # Latest-run selection sorts second-resolution IDs. Keep the two examples
    # in distinct seconds, as a person following the guide would naturally do.
    while time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) == run_a.split("-", 1)[0]:
        time.sleep(0.05)
    step, run_b = _capture(work, "capture-b")
    records.append(step)
    records.append(
        _run(
            ["audit", ".", "--no-color", "--format", "json"], work, "Audit captured state: Level 2"
        )
    )
    records.append(
        _run(
            ["diff", run_a, run_b, "--fail-on", "HIGH", "--format", "json"],
            work,
            "Explain the drift",
        )
    )
    records.append(_run(["export", ".", "--run", run_b], work, "Export the selected capture"))
    return records


def scrub(text: str, work: Path) -> str:
    """Remove tempdir paths so the document is reproducible across runs."""
    for spelling in sorted({str(work), str(work.resolve())}, key=len, reverse=True):
        text = text.replace(spelling, "examples/hf_vllm_eval")
    return text.replace("examples/hf_vllm_eval\\", "examples/hf_vllm_eval/")


def _excerpt(step: Step) -> str:
    if step.command[0] == "audit":
        report = json.loads(step.report_json)
        return json.dumps({"level": report["level"], "summary": report["summary"]}, indent=2)
    if step.command[0] == "diff":
        report = json.loads(step.report_json)
        change = next(item for item in report["changes"] if item["path"] == "generation.max_tokens")
        return json.dumps({"changes": [change], "highest": report["summary"]["highest"]}, indent=2)
    return step.stdout


def render(records: list[Step], work: Path) -> str:
    body = [
        "# Quick start",
        "",
        "This tour needs Python 3.10 or newer and Git. "
        "It runs a standard-library capture probe; it does not run Qwen, load MMLU, "
        "install model libraries, use a GPU, or call an API. "
        "The HF/vLLM experiment declaration remains an example of intended research state.",
        "",
        "Commands below are executed in a disposable example by CI. JSON blocks are excerpts "
        "of actual reports; run IDs and elapsed seconds are replaced with placeholders. "
        "Audit exit 1 means findings reached the configured threshold (default: critical). "
        "Diff exit 1 means the requested drift threshold was reached. "
        "Exit 2 means an input or usage error; exit 3 means an internal error.",
        "",
        "## Install and prepare a separate copy",
        "",
        "```bash",
        "python --version  # must be 3.10 or newer",
        "python -m venv .venv",
        "# macOS/Linux: source .venv/bin/activate",
        "# Windows PowerShell: .venv\\Scripts\\Activate.ps1",
        "python -m pip install reprollm",
        "reprollm --version",
        "git clone https://github.com/EnumaElish123/ReproLLM.git",
        'python -c "import shutil',
        "shutil.copytree('ReproLLM/examples/hf_vllm_eval', 'reprollm-tour',",
        "    ignore=shutil.ignore_patterns('reprollm.yaml', 'reprollm.lock',",
        "        '.reprollm', 'REPRODUCIBILITY*'))",
        "shutil.copyfile('ReproLLM/scripts/capture_probe.py',",
        "    'reprollm-tour/capture_probe.py')\"",
        "cd reprollm-tour",
        'python -c "from pathlib import Path',
        "p=Path('.gitignore')",
        "p.write_text(p.read_text()+'\\n.reprollm/runs/\\nREPRODUCIBILITY.md\\n')\"",
        "git init -b main",
        "git config user.name Tour",
        "git config user.email tour@example.invalid",
        "git add .",
        'git -c commit.gpgsign=false commit -m "Prepare capture exercise"',
        "```",
        "",
        "The source example's completed manifest, reviewed online lock and exports stay untouched. "
        "This copy starts with no manifest or lock, so its first audit really is Level 0. "
        "For your own project, start with `reprollm audit .` in that repository.",
        "",
    ]
    diff = next(row for row in records if row.command[0] == "diff")
    replacements = {diff.command[1]: "<run-a>", diff.command[2]: "<run-b>"}
    for index, step in enumerate(records):
        if index == 3:
            body.extend(
                [
                    "## Fill the declaration",
                    "",
                    "Replace `reprollm.yaml` with the following completed example and save "
                    "`configs/capture.json` with the JSON below. In your own project, fill the "
                    "scaffold from your actual model, data, prompt and execution settings. "
                    "Here only `capture_probe.py` executes; the model and metric declarations "
                    "describe the research example, not a successful evaluation.",
                    "",
                    "```yaml",
                    manifest_text().rstrip(),
                    "```",
                    "",
                    "```json",
                    config_text().rstrip(),
                    "```",
                    "",
                ]
            )
        if step.command[0] == "run":
            label = "a" if "capture-a" in step.command else "b"
            body.extend(
                [
                    "Commit the declared inputs before capture:",
                    "",
                    "```bash",
                    "git add .",
                    f'git -c commit.gpgsign=false commit -m "Declare capture {label}"',
                    "```",
                    "",
                ]
            )
        if step.title == "Record the intentional parameter change":
            body.extend(
                [
                    "Change `generation.max_tokens` from `32` to `48` in both "
                    "`reprollm.yaml` and `configs/capture.json`, then rebuild the offline lock.",
                    "",
                ]
            )
        command_line = f"reprollm {' '.join(step.command)}"
        for actual, placeholder in replacements.items():
            command_line = command_line.replace(actual, placeholder)
        body.extend([f"## {step.title}", "", "```bash", command_line, "```", ""])
        output = scrub(_excerpt(step), work).replace("examples/hf_vllm_eval", "<workdir>")
        for actual, placeholder in replacements.items():
            output = output.replace(actual, placeholder)
        output = re.sub(r"\(exit (\d+), [\d.]+ s,", r"(exit \1, <elapsed> s,", output)
        body.extend(
            [
                "```text" if not step.report_json else "```json",
                output,
                "```",
                f"Exit: `{step.exit_code}`.",
                "",
            ]
        )
        if step.command[0] == "lock" and "--offline" in step.command:
            body.extend(
                [
                    "Offline lock hashes available inputs and retains declared values. It leaves "
                    "remote revisions unresolved. Level 2 and a fresh lock describe available "
                    "evidence; they do not mean the model experiment passed. Resolve online "
                    "with `reprollm lock .` later when the required network access is available.",
                    "",
                ]
            )
        if step.command[0] == "run":
            body.extend(
                [
                    "Keep the printed run ID for the diff/export commands below. "
                    "Use `reprollm runs list` and `reprollm runs show <run-id>` to inspect it. "
                    "Hardware or environment availability warnings may vary by machine.",
                    "",
                ]
            )
    body.extend(
        [
            "Open `REPRODUCIBILITY.md` to review the selected capture, unresolved metadata "
            "and audit limitations. Export success means the report was written. "
            "This tour verifies capture and comparison; a real inference/evaluation run still "
            "requires the experiment's libraries, model/data access and compute.",
            "",
            "---",
            "Continue: [concepts](concepts.md) · [CLI reference](cli.md) · [why ReproLLM](why.md)",
            "",
        ]
    )
    return "\n".join(body)


def main(check: bool = False) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "hf_vllm_eval"
        text = render(run_workflow(work), work)
    target = ROOT / "docs/quickstart.md"
    if check:
        current = target.read_text(encoding="utf-8") if target.exists() else ""
        if current != text:
            print("docs/quickstart.md is stale; regenerate with scripts/gen_quickstart.py")
            print(
                "".join(
                    difflib.unified_diff(
                        current.splitlines(keepends=True),
                        text.splitlines(keepends=True),
                        fromfile="docs/quickstart.md",
                        tofile="generated/quickstart.md",
                    )
                ),
                end="",
            )
            return 1
        print("quickstart fresh")
        return 0
    target.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(check="--check" in sys.argv))
