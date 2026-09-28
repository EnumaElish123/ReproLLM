"""M7-T04: discover pipeline — gates, request, candidates, accept/ignore."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.discover.candidates import finalize
from reprollm.schemas.discover_candidates import Candidate, CandidateEvidence
from tests.conftest import materialize_repo

runner = CliRunner()


def run_cli(argv: list[str]):
    """Invoke through the cli() exit-code boundary (UserError→2 etc.)."""
    import sys

    import pytest as _pytest

    from reprollm.cli.main import cli

    old = sys.argv
    sys.argv = ["reprollm", *argv]
    try:
        with _pytest.raises(SystemExit) as excinfo:
            cli()
        return excinfo.value.code
    except Exception as exc:  # UserError is converted inside cli(); a raise
        raise AssertionError(f"uncaught {exc!r}") from exc
    finally:
        sys.argv = old


MOCK_RESPONSE = {
    "choices": [
        {
            "message": {
                "content": json.dumps(
                    {
                        "candidates": [
                            {
                                "kind": "parameter",
                                "name": "alpha",
                                "suggested_field": "custom.privacy_method.alpha",
                                "suggested_severity": "CRITICAL",
                                "confidence": "high",
                                "rationale": "controls noise scale",
                                "evidence": [
                                    {
                                        "kind": "file",
                                        "path": "configs/privacy.yaml",
                                        "line": 3,
                                        "snippet": "alpha: 0.25",
                                    }
                                ],
                                "suggested_bindings": {
                                    "config": "configs/privacy.yaml:method.alpha"
                                },
                            },
                            {
                                "kind": "parameter",
                                "name": "delta",
                                "suggested_field": "custom.privacy_method.delta",
                                "suggested_severity": "WARNING",
                                "confidence": "high",
                                "rationale": "constant shift",
                                "evidence": [{"kind": "file", "path": "configs/privacy.yaml"}],
                            },
                            {
                                "kind": "parameter",
                                "name": "ghost",
                                "suggested_field": "custom.ghost",
                                "suggested_severity": "INFO",
                                "confidence": "high",
                                "rationale": "hallucinated path",
                                "evidence": [{"kind": "file", "path": "not/in/payload.yaml"}],
                            },
                        ]
                    }
                )
            }
        }
    ]
}


@pytest.fixture
def repo(tmp_path: Path, monkeypatch) -> Path:
    repo = materialize_repo("privacy_custom_params", tmp_path)
    monkeypatch.chdir(repo)
    monkeypatch.setenv("REPROLLM_LLM_BASE_URL", "https://llm.example.com/v1")
    monkeypatch.setenv("REPROLLM_LLM_API_KEY", "sk-test-not-a-real-key-000")
    monkeypatch.setenv("REPROLLM_LLM_MODEL", "test-model")
    return repo


def test_gate_requires_experimental(tmp_path: Path, monkeypatch) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    monkeypatch.chdir(repo)
    monkeypatch.setattr("sys.argv", ["reprollm", "discover", "."])
    import pytest as _pytest

    from reprollm.cli.main import cli

    with _pytest.raises(SystemExit) as excinfo:
        cli()
    assert excinfo.value.code == 2


def test_paper_rejected_in_beta(repo: Path, capsys) -> None:
    code = run_cli(["discover", ".", "--experimental", "--paper", "p.pdf"])
    assert code == 2
    assert "not available in Beta" in capsys.readouterr().err


def test_missing_credentials_named(repo: Path, monkeypatch) -> None:
    monkeypatch.delenv("REPROLLM_LLM_MODEL")
    monkeypatch.setattr("sys.argv", ["reprollm", "discover", ".", "--experimental"])

    code = run_cli(["discover", ".", "--experimental"])
    assert code == 2


def test_dry_run_sends_nothing(repo: Path) -> None:
    result = runner.invoke(app, ["discover", ".", "--experimental", "--dry-run"])
    assert result.exit_code == 0
    assert "nothing is sent" in result.output.lower()
    assert "configs/privacy.yaml" in result.output
    assert ".env" not in result.output.split("Files included")[1].split("Dropped")[0]


def test_non_tty_without_yes_is_rejected(repo: Path) -> None:
    code = run_cli(["discover", ".", "--experimental"])
    assert code == 2


@respx.mock
def test_discover_writes_candidates_and_accept(repo: Path) -> None:
    respx.post("https://llm.example.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=MOCK_RESPONSE)
    )
    assert run_cli(["discover", ".", "--experimental", "--yes"]) == 0
    documents = sorted((repo / ".reprollm" / "discover").glob("*.json"))
    assert len(documents) == 1
    payload = json.loads(documents[0].read_text(encoding="utf-8"))
    ids = [c["id"] for c in payload["candidates"]]
    assert len(ids) == 3
    ghost = next(c for c in payload["candidates"] if c["name"] == "ghost")
    assert ghost["confidence"] == "low"  # evidence outside payload → demoted
    alpha = next(c for c in payload["candidates"] if c["name"] == "alpha")
    assert alpha["confidence"] == "high"
    assert "configs/privacy.yaml" in payload["input_files"]

    # manifest field with alpha present in manifest → not re-suggested? The
    # prompt carries the list; the mock ignores it — accepted behavior here.

    accept = runner.invoke(app, ["rules", "accept", alpha["id"]])
    assert accept.exit_code == 0, accept.output
    assert "project.alpha" in accept.output
    rules_doc = (repo / ".reprollm" / "project-rules.yaml").read_text(encoding="utf-8")
    assert "source: discover" in rules_doc
    assert alpha["id"] in rules_doc

    assert run_cli(["rules", "accept", alpha["id"]]) == 2

    ignore = runner.invoke(app, ["rules", "ignore", ghost["id"]])
    assert ignore.exit_code == 0, ignore.output
    listing = runner.invoke(app, ["rules", "list"])
    assert "[ignored]" in listing.output
    assert "[pending]" in listing.output


@respx.mock
def test_invalid_json_retry_then_raw_saved(repo: Path) -> None:
    route = respx.post("https://llm.example.com/v1/chat/completions")
    route.mock(
        side_effect=[
            httpx.Response(200, json={"choices": [{"message": {"content": "not json"}}]}),
            httpx.Response(200, json={"choices": [{"message": {"content": "still not json"}}]}),
        ]
    )
    assert run_cli(["discover", ".", "--experimental", "--yes"]) == 3
    raw = sorted((repo / ".reprollm" / "discover").glob("*.raw.txt"))
    assert raw, "the failed payload must be saved for inspection"


def test_finalize_deterministic_ids() -> None:
    from datetime import datetime, timezone

    stamp = datetime(2026, 9, 28, tzinfo=timezone.utc)
    kwargs = dict(
        model="m",
        reprollm_version="0.5.0a1",
        input_files=["configs/privacy.yaml"],
        dropped_files=[],
        truncated_files=[],
        generated_at=stamp,
    )
    candidates = [
        Candidate(
            id="placeholder",
            kind="parameter",
            name="alpha",
            suggested_field="custom.alpha",
            suggested_severity="INFO",
            confidence="high",
            rationale="r",
            evidence=[CandidateEvidence(path="configs/privacy.yaml", line=3)],
        )
    ]
    first = finalize([*candidates], **kwargs)
    second = finalize([*candidates], **kwargs)
    assert first.candidates[0].id == second.candidates[0].id
    assert first.candidates[0].id.startswith("c-")
    assert len(first.candidates[0].id) == 8
