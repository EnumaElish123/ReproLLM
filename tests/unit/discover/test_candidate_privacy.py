"""Discover responses are untrusted text at the persistence boundary."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from reprollm.discover.candidates import finalize
from reprollm.schemas.discover_candidates import (
    Candidate,
    CandidateEvidence,
    CandidateSuggestedBindings,
    DiscoverCandidates,
    candidate_id,
)

SECRET = "sk-" + "a" * 40


@pytest.fixture
def private_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("getpass.getuser", lambda: "private-author")
    monkeypatch.setattr("socket.gethostname", lambda: "private-node")
    return tmp_path


def candidate(**updates: object) -> Candidate:
    values: dict[str, object] = {
        "id": "pending",
        "kind": "parameter",
        "name": "alpha",
        "suggested_field": "custom.privacy.alpha",
        "suggested_severity": "WARNING",
        "confidence": "high",
        "rationale": "Controls the privacy budget.",
        "evidence": [CandidateEvidence(path="configs/privacy.yaml", line=3)],
    }
    values.update(updates)
    return Candidate.model_validate(values)


def document(
    raw: Candidate,
    *,
    input_files: list[str] | None = None,
    secret_values: tuple[str, ...] = (),
) -> DiscoverCandidates:
    return finalize(
        [raw],
        model="test-model",
        reprollm_version="0.6.0",
        input_files=input_files or ["configs/privacy.yaml"],
        dropped_files=[],
        truncated_files=[],
        generated_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        secret_values=secret_values,
    )


def test_finalize_redacts_returned_prose_and_machine_identity(private_root: Path) -> None:
    raw = candidate(
        rationale=f"{SECRET} private-author private-node /Users/example/private-experiment",
        evidence=[
            CandidateEvidence(
                path="configs/privacy.yaml",
                line=3,
                snippet='cache="C:\\Users\\example\\private" stop="</s>" glob="**/*.json"',
            )
        ],
    )

    result = document(raw)

    saved = result.model_dump_json()
    for value in (SECRET, "private-author", "private-node", "/Users/example", "C:\\Users"):
        assert value not in saved
    assert result.candidates[0].rationale == (
        "<REDACTED:openai> <REDACTED:username> <REDACTED:hostname> <REDACTED:path>"
    )
    assert result.candidates[0].evidence[0].snippet == (
        'cache="<REDACTED:path>" stop="</s>" glob="**/*.json"'
    )
    assert raw.rationale.startswith(SECRET)


def test_finalize_sanitizes_names_before_deriving_ids(private_root: Path) -> None:
    result = document(candidate(name=SECRET))

    actual = result.candidates[0]
    assert actual.name == "<REDACTED:openai>"
    assert actual.id == candidate_id(actual.kind, actual.name, "configs/privacy.yaml")
    assert actual.confidence == "low"


@pytest.mark.parametrize(
    "unsafe_field",
    [f"custom.{SECRET}", "custom.private-author.alpha", "custom./Users/example/value"],
)
def test_finalize_drops_fields_that_cannot_safely_be_accepted(
    private_root: Path, unsafe_field: str
) -> None:
    assert document(candidate(suggested_field=unsafe_field)).candidates == []


@pytest.mark.parametrize(
    "binding",
    [SECRET, "/Users/example/private.yaml:alpha", "--private-author", "<REDACTED:path>"],
)
def test_finalize_drops_unsafe_bindings_without_keeping_executable_markers(
    private_root: Path, binding: str
) -> None:
    raw = candidate(
        suggested_bindings=CandidateSuggestedBindings(cli="--alpha", config=binding, env="ALPHA")
    )

    actual = document(raw).candidates[0]

    assert actual.suggested_bindings == CandidateSuggestedBindings(cli="--alpha", env="ALPHA")
    assert actual.confidence == "low"
    assert binding not in actual.model_dump_json()


def test_finalize_preserves_safe_dsl_bindings_and_ids(private_root: Path) -> None:
    bindings = CandidateSuggestedBindings(
        cli="--alpha", config="configs/privacy.yaml:method.alpha", env="PRIVACY_ALPHA"
    )
    raw = candidate(suggested_bindings=bindings)

    actual = document(raw).candidates[0]

    assert actual.suggested_bindings == bindings
    assert actual.id == candidate_id(raw.kind, raw.name, "configs/privacy.yaml")
    assert actual.confidence == "high"


@pytest.mark.parametrize(
    "binding",
    [
        "./configs/privacy.yaml:method.alpha",
        "configs/./privacy.yaml:method.alpha",
        "./configs/./privacy.yaml:method.alpha",
    ],
)
def test_finalize_preserves_relative_config_dot_segments(private_root: Path, binding: str) -> None:
    bindings = CandidateSuggestedBindings(cli="--alpha", config=binding, env="ALPHA")
    raw = candidate(suggested_bindings=bindings)

    actual = document(raw).candidates[0]

    assert actual.suggested_bindings == bindings
    assert actual.confidence == "high"
    assert actual.id == candidate_id(raw.kind, raw.name, "configs/privacy.yaml")


@pytest.mark.parametrize(
    ("binding", "configured_secret"),
    [
        ("./configs/opaque-credential.yaml:alpha", "./configs/opaque-credential"),
        ("configs/./opaque-credential.yaml:alpha", "configs/./opaque-credential"),
    ],
)
def test_relative_config_normalization_cannot_hide_configured_secret(
    private_root: Path, binding: str, configured_secret: str
) -> None:
    raw = candidate(suggested_bindings=CandidateSuggestedBindings(config=binding, cli="--alpha"))

    actual = document(raw, secret_values=(configured_secret,)).candidates[0]

    assert actual.suggested_bindings == CandidateSuggestedBindings(cli="--alpha")
    assert actual.confidence == "low"
    assert configured_secret not in actual.model_dump_json()


@pytest.mark.parametrize(
    "binding",
    [
        "/opt/private/./config.yaml:alpha",
        "../configs/./privacy.yaml:alpha",
        "configs/../outside/./privacy.yaml:alpha",
        "C:/Users/example/./privacy.yaml:alpha",
        "C:\\Users\\example\\.\\privacy.yaml:alpha",
        "\\\\private-server\\share\\privacy.yaml:alpha",
        "//private-server/share/./privacy.yaml:alpha",
        f"./configs/{SECRET}.yaml:alpha",
        "./configs/private-author.yaml:alpha",
        "configs/./private-node.yaml:alpha",
    ],
)
def test_relative_config_exception_still_rejects_unsafe_originals(
    private_root: Path, binding: str
) -> None:
    raw = candidate(suggested_bindings=CandidateSuggestedBindings(config=binding, env="ALPHA"))

    actual = document(raw).candidates[0]

    assert actual.suggested_bindings == CandidateSuggestedBindings(env="ALPHA")
    assert actual.confidence == "low"
    assert binding not in actual.model_dump_json()


@pytest.mark.parametrize("filename", ["README#Links.md", "README#L12", "config.py#L12"])
def test_finalize_matches_actual_input_files_before_removing_locators(
    private_root: Path, filename: str
) -> None:
    (private_root / filename).write_text("content", encoding="utf-8")
    raw = candidate(evidence=[CandidateEvidence(path=filename, line=4)])

    actual = document(raw, input_files=[filename]).candidates[0]

    assert actual.evidence[0].path == filename
    assert actual.id == candidate_id(raw.kind, raw.name, filename)
    assert actual.confidence == "high"


def test_finalize_only_removes_terminal_numeric_locators(private_root: Path) -> None:
    filename = "README#Links.md"
    (private_root / filename).write_text("content", encoding="utf-8")
    raw = candidate(evidence=[CandidateEvidence(path=f"{filename}#L42", line=42)])

    actual = document(raw, input_files=[filename]).candidates[0]

    assert actual.evidence[0].path == filename
    assert actual.confidence == "high"


def test_finalize_sanitizes_document_metadata(private_root: Path) -> None:
    result = finalize(
        [],
        model=f"private-node {SECRET}",
        reprollm_version="0.6.0",
        input_files=["README.md", "/Users/example/private-experiment", "private-author.md"],
        dropped_files=["private-author.md", SECRET],
        truncated_files=[str(private_root / "large.yaml")],
        generated_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )

    saved = result.model_dump_json()
    for value in (SECRET, "private-author", "private-node", str(private_root), "/Users/example"):
        assert value not in saved
    assert result.input_files == ["README.md"]
    assert result.dropped_files == []
    assert result.truncated_files == ["large.yaml"]
