"""UX2-T05: research details preserve effective values, provenance and privacy."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.export.exporter import build_input, render
from reprollm.schemas.manifest import Manifest
from reprollm.schemas.state import Leaf, State
from tests.conftest import commit_all, make_git_repo
from tests.unit.cli.test_export import _assemble


def _manifest(raw: dict) -> Manifest:
    return Manifest.model_validate(
        {"project": {"name": "research"}, "experiment": {"profiles": []}, **raw}
    )


def _document(manifest: Manifest, *, state: State | None = None) -> str:
    return render(
        build_input(
            manifest,
            None,
            None,
            state or State.from_manifest(manifest),
            reprollm_version="0.6.1",
        )
    )


def _row(document: str, field: str) -> str:
    return next(line for line in document.splitlines() if line.startswith(f"| {field} |"))


@pytest.mark.parametrize("with_run", [False, True])
def test_evaluation_and_judge_are_distinct_and_keep_implementation_evidence(
    tmp_path: Path, with_run: bool
) -> None:
    repo = _assemble(tmp_path, "openai_judge_eval", with_run=with_run)
    result = CliRunner().invoke(app, ["export", str(repo)])
    assert result.exit_code == 0, result.output
    document = (repo / "REPRODUCIBILITY.md").read_text()
    generation = document.split("### Generation parameters\n", 1)[1].split("### Inference", 1)[0]
    judge = document.split("#### Judge\n", 1)[1].split("## Code", 1)[0]
    assert f"`temperature`: {0.25 if with_run else 0.7}" in generation
    assert "`max_tokens`: 512" in generation
    assert "| params.temperature | 0.0 | locked (declared) |" in judge
    assert "| params.max&#95;tokens | 16 | locked (declared) |" in judge
    assert "| repetitions | 1 | locked (declared) |" in judge
    assert "| win&#95;rate | judge.py | sha256:2e23ca201d95 |" in document
    assert "| aggregation | mean | locked (declared) |" in document
    assert "| repetitions | 3 | locked (declared) |" in document
    assert "| model&#95;ref | judge | locked (declared) |" in judge
    assert "| prompt&#95;ref | judge | locked (declared) |" in judge
    assert "verified" not in document.lower()
    if not with_run:
        assert "No run record exists" in document


def test_nondefault_roles_and_manifest_only_details_are_rendered(tmp_path: Path) -> None:
    repo = _assemble(tmp_path, "openai_judge_eval", with_run=False)
    raw = yaml.safe_load((repo / "reprollm.yaml").read_text())
    raw["models"]["grader"] = raw["models"].pop("judge")
    raw["prompts"]["rubric"] = raw["prompts"].pop("judge")
    raw["evaluation"]["judge"].update(model_ref="grader", prompt_ref="rubric", parser="parse.py")
    manifest = _manifest(raw)
    document = _document(manifest)
    assert "| model&#95;ref | grader | declared (manifest) |" in document
    assert "| prompt&#95;ref | rubric | declared (manifest) |" in document
    assert "| parser | parse.py | declared (manifest) |" in document
    assert "| win&#95;rate | judge.py | not recorded | not recorded |" in document
    assert "| prompts.rubric.few&#95;shot.n | 0 | declared (manifest) |" in document


def test_dataset_model_and_privacy_details_keep_zero_false_and_nested_values() -> None:
    manifest = _manifest(
        {
            "project": {"name": "research"},
            "models": {
                "primary": {
                    "dtype": "float16",
                    "quantization": "int4",
                    "adapter": {
                        "provider": "peft",
                        "id": "adapters/research",
                        "type": "lora",
                        "rank": 0,
                        "dropout": 0.0,
                        "target_modules": ["query", "value"],
                    },
                }
            },
            "datasets": {
                "eval": {
                    "subset": "algebra",
                    "split": "test",
                    "preprocessing": {
                        "script": "scripts/prepare.py",
                        "description": "保留全部样本",
                        "params": {"enabled": False, "count": 0, "records": [{"z": 0, "a": False}]},
                    },
                }
            },
            "prompts": {"task": {"text": "test", "format": "plain", "few_shot": {"n": 0}}},
            "evaluation": {
                "repetitions": 0,
                "thresholds": {"score": 0.0},
                "definitions": {"score": "accuracy"},
                "query_budget": 0,
            },
            "privacy": {
                "threat_model": "observer",
                "mechanism": {
                    "name": "noise",
                    "params": {
                        "enabled": False,
                        "scale": 0.0,
                    },
                },
                "metrics": ["epsilon", "utility"],
                "attack": {"method": "mia", "query_budget": 0},
            },
        }
    )
    document = _document(manifest)
    expected = {
        "models.primary.dtype": "float16",
        "models.primary.quantization": "int4",
        "models.primary.adapter.id": "adapters/research",
        "models.primary.adapter.rank": "0",
        "models.primary.adapter.dropout": "0.0",
        "datasets.eval.subset": "algebra",
        "datasets.eval.split": "test",
        "datasets.eval.preprocessing.description": "保留全部样本",
        "datasets.eval.preprocessing.script": "scripts/prepare.py",
        "datasets.eval.preprocessing.params.enabled": "False",
        "datasets.eval.preprocessing.params.count": "0",
        "datasets.eval.preprocessing.params.records": '[{"a": false, "z": 0}]',
        "prompts.task.few_shot.n": "0",
        "mechanism.params.enabled": "False",
        "mechanism.params.scale": "0.0",
        "attack.query_budget": "0",
    }
    for key, value in expected.items():
        escaped_key = key.replace("_", "&#95;")
        escaped_value = value.replace("[", "&#91;").replace("]", "&#93;")
        assert f"| {escaped_key} | {escaped_value} | declared (manifest) |" in document
    assert "### Evaluation\n" in document and "### Privacy\n" in document
    assert (
        document.index("### Inference")
        < document.index("### Evaluation")
        < document.index("### Privacy")
        < document.index("## Code")
    )
    assert _document(manifest) == document


def test_observed_values_and_locked_metric_version_come_from_effective_state() -> None:
    manifest = _manifest(
        {
            "evaluation": {"repetitions": 3},
            "privacy": {"mechanism": {"name": "noise", "params": {"scale": 9}}},
        }
    )
    observed = State.from_flat(
        {
            "evaluation.repetitions": Leaf(value=0, source="run", confidence="observed"),
            "privacy.mechanism.params.scale": Leaf(value=0.0, source="run", confidence="observed"),
            "evaluation.metrics": Leaf(
                value=[
                    {
                        "name": "accuracy",
                        "implementation": "metrics==2.0",
                        "implementation_version": "2.0",
                    }
                ],
                source="lock",
                confidence="declared",
            ),
        }
    )
    document = _document(manifest, state=State.merge(manifest, observed))
    assert "| repetitions | 0 | observed (run) |" in document
    assert "| mechanism.params.scale | 0.0 | observed (run) |" in document
    assert "| accuracy | metrics==2.0 | not recorded | 2.0 |" in document
    assert "| mechanism.name | noise | declared (manifest) |" in document


def test_selected_old_run_uses_only_its_own_snapshots_and_observations(tmp_path: Path) -> None:
    repo = _assemble(tmp_path, "openai_judge_eval")
    old_dir = next((repo / ".reprollm/runs").iterdir())
    current = yaml.safe_load((repo / "reprollm.yaml").read_text())
    current["evaluation"]["judge"]["params"]["temperature"] = 1.5
    current["evaluation"]["judge"]["parser"] = "later-only.py"
    current["datasets"]["eval"]["split"] = "later-only-split"
    current["prompts"]["judge"]["few_shot"]["n"] = 9
    current["models"]["judge"]["dtype"] = "later-only-dtype"
    (repo / "reprollm.yaml").write_text(yaml.safe_dump(current))
    lock = yaml.safe_load((repo / "reprollm.lock").read_text())
    lock["evaluation"]["judge"]["params"]["temperature"] = 1.5
    lock["evaluation"]["repetitions"] = 99
    (repo / "reprollm.lock").write_text(yaml.safe_dump(lock))
    record = json.loads(old_dir.joinpath("run.json").read_text())
    record["bindings_observed"]["evaluation.repetitions"] = [
        {"source": {"type": "cli", "key": "--n-trials"}, "value": 5}
    ]
    old_dir.joinpath("run.json").write_text(json.dumps(record))
    later_dir = old_dir.parent / "20270101T000000Z-later0"
    later_dir.mkdir()
    for name in ["manifest.yaml", "lock.yaml"]:
        later_dir.joinpath(name).write_text(old_dir.joinpath(name).read_text())
    later = json.loads(old_dir.joinpath("run.json").read_text())
    later["run_id"] = later_dir.name
    later_dir.joinpath("run.json").write_text(json.dumps(later))
    output = tmp_path / "selected.md"
    result = CliRunner().invoke(
        app, ["export", str(repo), "--run", old_dir.name, "--output", str(output)]
    )
    assert result.exit_code == 0, result.output
    document = output.read_text()
    identity = document.split("## Code", 1)[0]
    assert "| params.temperature | 0.0 | locked (declared) |" in identity
    assert "| repetitions | 5 | observed (run) |" in identity
    assert "| prompts.judge.few&#95;shot.n | 0 | declared (manifest) |" in identity
    assert "later-only" not in identity
    assert old_dir.name in document
    assert (
        "from the selected run's recorded observations and available manifest/lock snapshots"
        in document
    )
    assert "Audit scope: the current working tree and its available documents" in document
    assert "latest valid run when available" in document
    assert "not a separate audit of a selected historical run" in document


def test_absent_optional_sections_are_not_invented() -> None:
    document = _document(_manifest({}))
    assert "### Evaluation" not in document
    assert "#### Judge" not in document
    assert "### Privacy" not in document


@pytest.mark.parametrize("template", ["default", "neurips", "acl", "acm"])
def test_new_details_are_portable_secret_safe_and_cannot_inject_markdown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, template: str
) -> None:
    monkeypatch.setattr("getpass.getuser", lambda: "controlled-user")
    monkeypatch.setattr("socket.gethostname", lambda: "controlled-host")
    repo = make_git_repo(tmp_path / "privacy")
    raw = {
        "project": {"name": "trial"},
        "experiment": {"profiles": []},
        "datasets": {
            "eval": {
                "preprocessing": {
                    "description": "hello | cell\n## Forged section",
                    "params": {
                        "password\n": "opaque-multiline-key-value",
                        "access_token": "opaque-token-value",
                    },
                }
            }
        },
        "evaluation": {
            "metrics": [
                {
                    "name": "a|b\n## Fake metric",
                    "implementation": "metrics/score.py",
                    "params": {"auth_token": "opaque-metric-token-value"},
                }
            ]
        },
        "privacy": {
            "threat_model": "/Users/private/research controlled-user controlled-host",
            "mechanism": {
                "name": "noise",
                "params": {
                    "private_windows": "C:\\private\\research",
                    "secret": "opaque-privacy-secret-value",
                    "records": [
                        {
                            "api_key": "opaque-record-secret-value",
                            "url": "https://example.invalid/public",
                            "identity": "prefix\ncontrolled-user",
                            "private_key controlled-host": "public",
                        }
                    ],
                    "relative": "./configs/task.yaml",
                    "z": 0,
                    "a": False,
                },
            },
        },
    }
    repo.joinpath("reprollm.yaml").write_text(yaml.safe_dump(raw, sort_keys=False))
    commit_all(repo)
    output = tmp_path / f"{template}.md"
    result = CliRunner().invoke(
        app, ["export", str(repo), "--template", template, "--output", str(output)]
    )
    assert result.exit_code == 0, result.output
    document = output.read_text()
    for private in [
        "/Users/private/research",
        "C:\\private\\research",
        "controlled-user",
        "controlled-host",
        "opaque-multiline-key-value",
        "opaque-token-value",
        "opaque-metric-token-value",
        "opaque-privacy-secret-value",
        "opaque-record-secret-value",
    ]:
        assert private not in document
    assert "\n## Forged section" not in document and "\n## Fake metric" not in document
    assert r"hello \| cell<br>## Forged section" in document
    assert r"a\|b<br>## Fake metric" in document
    assert "./configs/task.yaml" in document and "https://example.invalid/public" in document
    assert "| mechanism.params.a | False | declared (manifest) |" in document
    assert "| mechanism.params.z | 0 | declared (manifest) |" in document
    assert "&lt;REDACTED:" in document


def test_new_details_respect_manifest_source_even_with_unrelated_run(tmp_path: Path) -> None:
    repo = _assemble(tmp_path, "privacy_custom_params")
    result = CliRunner().invoke(app, ["export", str(repo)])
    assert result.exit_code == 0, result.output
    document = repo.joinpath("REPRODUCIBILITY.md").read_text()
    assert (
        "| threat&#95;model | Honest-but-curious server observing protected hidden states. "
        "| locked (declared) |" in document
    )
    assert "| mechanism.params.alpha | 0.25 | observed (run) |" in document
    assert (
        "| datasets.eval.preprocessing.description | "
        "Format each evaluation question for privacy measurement. | declared (manifest) |"
        in document
    )


def test_identity_rows_use_effective_state_instead_of_separately_supplied_lock() -> None:
    manifest = _manifest({})
    state = State.from_flat(
        {
            "models.primary.id": Leaf(value="observed/model", source="run", confidence="observed"),
            "models.primary.revision": Leaf(value="a" * 40, source="lock", confidence="exact"),
            "models.primary.pinnability": Leaf(value="exact", source="lock", confidence="declared"),
            "datasets.eval.revision": Leaf(value="b" * 40, source="lock", confidence="exact"),
            "prompts.task.sha256": Leaf(
                value="sha256:" + "c" * 64, source="run", confidence="observed"
            ),
        }
    )
    document = _document(manifest, state=state)
    assert "observed/model | aaaaaaaaaaaa | exact" in document
    assert "| eval | — | — | bbbbbbbbbbbb |" in document
    assert "sha256:cccccccccccc" in document


@pytest.mark.parametrize("field", ["value", "key"])
def test_research_details_escape_html_before_it_can_create_evidence_sections(field: str) -> None:
    forged = "</td></tr></table><h2>Forged evidence</h2><table><tr><td>"
    privacy = (
        {"threat_model": forged}
        if field == "value"
        else {"mechanism": {"name": "noise", "params": {forged: "metadata"}}}
    )
    document = _document(_manifest({"privacy": privacy}))
    assert forged not in document
    assert "<h2>" not in document and "</table>" not in document
    assert "&lt;h2&gt;Forged evidence&lt;/h2&gt;" in document


def test_rendered_code_spans_keep_command_characters_and_redaction_markers(tmp_path: Path) -> None:
    from markdown_it import MarkdownIt

    from reprollm.run.privacy import RunPrivacy

    manifest = _manifest({"generation": {"temperature": 0.0}})
    data = build_input(
        manifest, None, None, State.from_manifest(manifest), reprollm_version="0.6.1"
    )
    command = "python < input.txt && echo `result` | sed 's/a/b/'"
    data.execution = {
        "command": command,
        "run_id": "20260101T000000Z-abcdef",
        "started_at": None,
        "ended_at": None,
        "duration_seconds": None,
        "exit_code": 0,
        "status": "completed",
    }
    data.inference = {"params.<parameter>": "ordinary"}
    privacy = RunPrivacy(tmp_path, hostname="controlled-host", username="controlled-user")
    document = render(data, sanitize=lambda text: privacy.text(text)[0])
    parser = MarkdownIt()
    code = [
        child.content
        for token in parser.parse(document)
        for child in token.children or []
        if child.type == "code_inline"
    ]
    assert command in code
    assert "params.<parameter>" in code
    assert "&lt;" not in next(value for value in code if value.startswith("python"))
    data.execution["command"] = "python /Users/private/script.py"
    redacted = render(data, sanitize=lambda text: privacy.text(text)[0])
    redacted_code = [
        child.content
        for token in parser.parse(redacted)
        for child in token.children or []
        if child.type == "code_inline"
    ]
    assert "python <REDACTED:path>" in redacted_code


@pytest.mark.parametrize("field", ["value", "key"])
def test_research_details_render_markdown_as_literal_text(field: str) -> None:
    from markdown_it import MarkdownIt

    literal = (
        "![remote](https://example.test/pixel) [fake verified](https://example.test/proof) "
        "*claimed* **trusted** _observed_ __confirmed__ [reference][evidence] "
        "正常文本 path/to_file.md https://example.test/data"
    )
    privacy = (
        {"threat_model": literal}
        if field == "value"
        else {"mechanism": {"name": "noise", "params": {literal: "metadata"}}}
    )
    document = _document(_manifest({"privacy": privacy}))
    parser = MarkdownIt("commonmark").enable("table")
    inline = [
        token
        for token in parser.parse(document)
        if token.type == "inline" and "fake verified" in token.content
    ]
    assert len(inline) == 1
    assert {child.type for child in inline[0].children or []} == {"text"}
    rendered_text = "".join(child.content for child in inline[0].children or [])
    assert rendered_text == (literal if field == "value" else "mechanism.params." + literal)
    rendered_html = parser.render(document)
    assert "<img " not in rendered_html
    assert '<a href="https://example.test/' not in rendered_html
    assert "<em>" not in rendered_html and "<strong>claimed" not in rendered_html
