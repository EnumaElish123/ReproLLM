"""M4-T05: resolved lock identity and content-hash rules."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reprollm.core.engine import run_audit
from reprollm.core.hashing import sha256_file
from reprollm.core.yaml_io import dump_yaml
from reprollm.rules.dataset import LocalFilesHashedRule
from reprollm.rules.dataset import RevisionPinnedRule as DatasetRevisionRule
from reprollm.rules.gen import BackendVersionLockedRule
from reprollm.rules.judge import PinnabilityRecordedRule
from reprollm.rules.judge import PromptHashedRule as JudgePromptRule
from reprollm.rules.model import (
    ChatTemplateHashedRule,
    TokenizerPinnedRule,
)
from reprollm.rules.model import (
    RevisionPinnedRule as ModelRevisionRule,
)
from reprollm.rules.prompt import HashedRule as PromptHashedRule
from reprollm.schemas.finding import FindingStatus, Severity
from reprollm.schemas.lock import Lock
from tests.unit.rules.helpers import context, failures

NOW = datetime(2026, 10, 1, 9, 30, tzinfo=timezone.utc)
SHA = "sha256:" + "a" * 64


def _provenance(
    *,
    confidence: str = "exact",
    value: object | None = SHA,
    source: str = "hf_api",
    note: str | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "value": value,
        "source": source,
        "confidence": confidence,
    }
    if note is not None:
        result["note"] = note
    return result


def _model(
    provider: str,
    *,
    confidence: str = "exact",
    pinnability: str = "exact",
    note: str | None = None,
    **fields: Any,
) -> dict[str, object]:
    return {
        "provider": provider,
        "id": "org/model",
        "pinnability": pinnability,
        "revision": _provenance(confidence=confidence, note=note),
        **fields,
    }


def _lock(**sections: Any) -> Lock:
    return Lock.model_validate(
        {
            "reprollm_version": "0.2.0",
            "generated_at": NOW,
            "manifest_sha256": SHA,
            "resolution": {"mode": "online"},
            **sections,
        }
    )


def test_model_revision_huggingface_requires_exact_and_records_provenance(
    tmp_path: Path,
) -> None:
    exact = _lock(models={"primary": _model("huggingface")})
    assert ModelRevisionRule().check(context(tmp_path, level=2, lock=exact)) == []

    unresolved = _lock(
        models={
            "primary": _model(
                "huggingface",
                confidence="unresolved",
                note="HfForbiddenError",
                revision=_provenance(
                    confidence="unresolved",
                    value=None,
                    source="hf_api_forbidden",
                    note="HfForbiddenError",
                ),
            )
        }
    )
    finding = failures(ModelRevisionRule().check(context(tmp_path, level=2, lock=unresolved)))[0]
    assert finding.severity == Severity.CRITICAL
    assert finding.evidence[0].field == "models.primary.revision"
    assert "source=hf_api_forbidden" in (finding.evidence[0].note or "")
    assert "note=HfForbiddenError" in (finding.evidence[0].note or "")
    assert "HF_TOKEN" in finding.fix_hint


def test_model_revision_api_reports_unpinnable_and_snapshot_alias(tmp_path: Path) -> None:
    lock = _lock(
        models={
            "judge": _model(
                "openai",
                confidence="unresolved",
                pinnability="snapshot_alias",
                revision=_provenance(
                    confidence="unresolved", value=None, source="provider_no_pinning"
                ),
            ),
            "primary": _model(
                "openai",
                confidence="unresolved",
                pinnability="unpinnable",
                revision=_provenance(
                    confidence="unresolved", value=None, source="provider_no_pinning"
                ),
            ),
        }
    )

    result = ModelRevisionRule().check(context(tmp_path, level=2, lock=lock))

    assert [(finding.evidence[0].field, finding.severity) for finding in result] == [
        ("models.judge.pinnability", Severity.INFO),
        ("models.primary.pinnability", Severity.WARNING),
    ]
    assert all(finding.status == FindingStatus.FAIL for finding in result)


def test_model_revision_local_requires_config_hash(tmp_path: Path) -> None:
    weights = {"hashed": True, "total_size_bytes": 1, "sha256": SHA}
    exact = _lock(
        models={
            "primary": _model(
                "local",
                local={
                    "path": "models/local",
                    "config_sha256": _provenance(source="filesystem:config_files"),
                    "weights": weights,
                },
            )
        }
    )
    assert ModelRevisionRule().check(context(tmp_path, level=2, lock=exact)) == []

    missing = _lock(
        models={"primary": _model("local", local={"path": "models/local", "weights": weights})}
    )
    finding = failures(ModelRevisionRule().check(context(tmp_path, level=2, lock=missing)))[0]
    assert finding.severity == Severity.CRITICAL
    assert finding.evidence[0].field == "models.primary.local.config_sha256"


def test_tokenizer_revision_passes_exact_and_fails_unresolved(tmp_path: Path) -> None:
    exact = _lock(
        models={
            "primary": _model(
                "huggingface",
                tokenizer={"id": "org/tokenizer", "revision": _provenance()},
            )
        }
    )
    assert TokenizerPinnedRule().check(context(tmp_path, level=2, lock=exact)) == []

    unresolved = _lock(
        models={
            "primary": _model(
                "huggingface",
                tokenizer={
                    "id": "org/tokenizer",
                    "revision": _provenance(
                        confidence="unresolved", value=None, source="network_error"
                    ),
                },
            )
        }
    )
    finding = failures(TokenizerPinnedRule().check(context(tmp_path, level=2, lock=unresolved)))[0]
    assert finding.severity == Severity.WARNING
    assert finding.evidence[0].field == "models.primary.tokenizer.revision"
    assert "source=network_error" in (finding.evidence[0].note or "")


def test_chat_template_absence_passes_with_note_and_unresolved_fails(tmp_path: Path) -> None:
    absent = _lock(
        models={
            "primary": _model(
                "huggingface",
                chat_template={
                    "status": "absent",
                    "sha256": _provenance(
                        value=None, source="hf_api", note="model has no chat template"
                    ),
                },
            )
        }
    )
    result = ChatTemplateHashedRule().check(context(tmp_path, level=2, lock=absent))
    assert len(result) == 1 and result[0].status == FindingStatus.PASS
    assert result[0].evidence[0].note == "model has no chat template"

    unresolved = _lock(
        models={
            "primary": _model(
                "huggingface",
                chat_template={
                    "status": "present",
                    "sha256": _provenance(
                        confidence="unresolved", value=None, source="network_error"
                    ),
                },
            )
        }
    )
    finding = failures(ChatTemplateHashedRule().check(context(tmp_path, level=2, lock=unresolved)))[
        0
    ]
    assert finding.severity == Severity.WARNING
    assert finding.evidence[0].field == "models.primary.chat_template.sha256"


def test_dataset_revision_passes_exact_and_fails_unresolved(tmp_path: Path) -> None:
    exact = _lock(
        datasets={
            "eval": {
                "provider": "huggingface",
                "id": "org/data",
                "revision": _provenance(),
            }
        }
    )
    assert DatasetRevisionRule().check(context(tmp_path, level=2, lock=exact)) == []

    unresolved = _lock(
        datasets={
            "eval": {
                "provider": "huggingface",
                "id": "org/data",
                "revision": _provenance(confidence="declared", value="main", source="manifest"),
            }
        }
    )
    finding = failures(DatasetRevisionRule().check(context(tmp_path, level=2, lock=unresolved)))[0]
    assert finding.severity == Severity.WARNING
    assert finding.evidence[0].field == "datasets.eval.revision"


def test_local_dataset_requires_hash_for_every_declared_file(tmp_path: Path) -> None:
    manifest = {
        "datasets": {
            "eval": {
                "provider": "local",
                "id": "data",
                "files": ["data/a.jsonl", "data/b.jsonl"],
            }
        }
    }
    complete = _lock(
        datasets={
            "eval": {
                "provider": "local",
                "id": "data",
                "revision": _provenance(value=None, source="filesystem"),
                "files": [
                    {"path": "data/a.jsonl", "sha256": SHA, "size_bytes": 1},
                    {"path": "data/b.jsonl", "sha256": SHA, "size_bytes": 1},
                ],
            }
        }
    )
    assert LocalFilesHashedRule().check(context(tmp_path, level=2, lock=complete, **manifest)) == []

    incomplete = _lock(
        datasets={
            "eval": {
                "provider": "local",
                "id": "data",
                "revision": _provenance(value=None, source="filesystem"),
                "files": [{"path": "data/a.jsonl", "sha256": SHA, "size_bytes": 1}],
            }
        }
    )
    finding = failures(
        LocalFilesHashedRule().check(context(tmp_path, level=2, lock=incomplete, **manifest))
    )[0]
    assert finding.severity == Severity.CRITICAL
    assert finding.evidence[0].field == "datasets.eval.files"
    assert finding.evidence[0].expected == ["data/a.jsonl", "data/b.jsonl"]
    assert finding.evidence[0].value == ["data/a.jsonl"]


def test_backend_version_passes_exact_and_fails_unresolved(tmp_path: Path) -> None:
    exact = _lock(
        inference={
            "backend": "transformers",
            "version": _provenance(value="4.57.0", source="importlib_metadata"),
        }
    )
    assert (
        BackendVersionLockedRule().check(
            context(tmp_path, level=2, lock=exact, inference={"backend": "transformers"})
        )
        == []
    )

    unresolved = _lock(
        inference={
            "backend": "transformers",
            "version": _provenance(
                confidence="unresolved", value=None, source="importlib_metadata"
            ),
        }
    )
    finding = failures(
        BackendVersionLockedRule().check(
            context(
                tmp_path,
                level=2,
                lock=unresolved,
                inference={"backend": "transformers"},
            )
        )
    )[0]
    assert finding.severity == Severity.WARNING
    assert finding.evidence[0].field == "inference.version"


def test_prompt_hash_passes_for_source_hash_and_fails_when_lock_role_missing(
    tmp_path: Path,
) -> None:
    complete = _lock(prompts={"system": {"text_sha256": SHA}})
    assert (
        PromptHashedRule().check(
            context(
                tmp_path,
                level=2,
                lock=complete,
                prompts={"system": {"text": "hello"}},
            )
        )
        == []
    )

    missing = _lock(prompts={})
    finding = failures(
        PromptHashedRule().check(
            context(tmp_path, level=2, lock=missing, prompts={"system": {"text": "hello"}})
        )
    )[0]
    assert finding.severity == Severity.WARNING
    assert finding.evidence[0].field == "prompts.system.text_sha256"


def _judge_context(tmp_path: Path, lock: Lock):
    return context(
        tmp_path,
        level=2,
        lock=lock,
        models={"grader": {"provider": "openai", "id": "gpt-4o-2024-08-06"}},
        prompts={"rubric": {"text": "score this"}},
        evaluation={"judge": {"model_ref": "grader", "prompt_ref": "rubric"}},
    )


def test_judge_prompt_hash_uses_referenced_role_for_pass_and_fail(tmp_path: Path) -> None:
    complete = _lock(prompts={"rubric": {"text_sha256": SHA}})
    assert JudgePromptRule().check(_judge_context(tmp_path, complete)) == []

    finding = failures(JudgePromptRule().check(_judge_context(tmp_path, _lock())))[0]
    assert finding.severity == Severity.WARNING
    assert finding.evidence[0].field == "prompts.rubric.text_sha256"


def test_judge_pinnability_uses_referenced_role_for_pass_and_fail(tmp_path: Path) -> None:
    complete = _lock(
        models={"grader": _model("openai", confidence="unresolved", pinnability="snapshot_alias")}
    )
    assert PinnabilityRecordedRule().check(_judge_context(tmp_path, complete)) == []

    finding = failures(PinnabilityRecordedRule().check(_judge_context(tmp_path, _lock())))[0]
    assert finding.severity == Severity.WARNING
    assert finding.evidence[0].field == "models.grader.pinnability"


def test_openai_judge_fixture_reports_primary_warning_and_judge_info(
    materialize, tmp_path: Path
) -> None:
    root = materialize("openai_judge_eval", manifest="complete")
    manifest_path = root / "reprollm.yaml"
    lock = _lock(
        manifest_sha256=sha256_file(manifest_path),
        models={
            "judge": {
                **_model(
                    "openai",
                    confidence="unresolved",
                    pinnability="snapshot_alias",
                    revision=_provenance(
                        confidence="unresolved", value=None, source="provider_no_pinning"
                    ),
                ),
                "id": "gpt-4o-2024-08-06",
            },
            "primary": {
                **_model(
                    "openai",
                    confidence="unresolved",
                    pinnability="unpinnable",
                    revision=_provenance(
                        confidence="unresolved", value=None, source="provider_no_pinning"
                    ),
                ),
                "id": "gpt-4o-mini",
            },
        },
        prompts={
            "judge": {
                "path": "prompts/judge.txt",
                "sha256": sha256_file(root / "prompts/judge.txt"),
                "size_bytes": (root / "prompts/judge.txt").stat().st_size,
            }
        },
    )
    (root / "reprollm.lock").write_text(dump_yaml(lock), encoding="utf-8")

    findings = [
        finding
        for finding in run_audit(root).findings
        if finding.rule_id == "model.revision_pinned"
    ]

    assert [(finding.evidence[0].field, finding.severity) for finding in findings] == [
        ("models.primary.pinnability", Severity.WARNING),
        ("models.judge.pinnability", Severity.INFO),
    ]
