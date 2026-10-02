"""UX-T06: opaque API declarations stay honest, per-role and source-aware."""

from pathlib import Path

import pytest

from reprollm.core.engine import run_audit
from reprollm.core.hashing import sha256_file
from reprollm.core.yaml_io import dump_yaml
from reprollm.rules.model import (
    DtypeDeclaredRule,
    ProviderKnownRule,
    QuantizationDeclaredRule,
    RevisionPinnedRule,
)
from reprollm.schemas.finding import FindingStatus, Severity
from tests.unit.rules.helpers import context
from tests.unit.rules.test_lock_rules import _lock, _model, _provenance
from tests.unit.rules.test_runtime_consistency import observation, run_record

ENDPOINT = "https://gateway.example.test/v1"
INVALID_ENDPOINTS = [
    None,
    "",
    " \t\n",
    " " + ENDPOINT,
    ENDPOINT + " ",
    "\x00" + ENDPOINT,
    ENDPOINT + "\x7f",
    ENDPOINT + "\u202e",
    ENDPOINT + "\u200b",
    "https://gate\tway.example.test/v1",
    "https://gateway.example.test/\nv1",
    "ftp://gateway.example.test/v1",
    "gateway.example.test/v1",
    "https:///v1",
    "https://[malformed/v1",
    "https://gateway.example.test:invalid/v1",
    "https://gateway.example.test:99999/v1",
    "https://user@gateway.example.test/v1",
    "https://user:password@gateway.example.test/v1",
    ENDPOINT + "#fragment",
    ENDPOINT + "#",
    ENDPOINT + "?api_key=abcdefghijk",
    ENDPOINT + "/sk-abcdefghijklmnopqrstuvwxyz",
    ENDPOINT + "?cache=/Users/private/cache",
    "https://audit-host.example.test/v1",
    ENDPOINT + "/audit-user",
]


@pytest.fixture(autouse=True)
def controlled_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("socket.gethostname", lambda: "audit-host")
    monkeypatch.setattr("getpass.getuser", lambda: "audit-user")


@pytest.mark.parametrize("rule_type", [DtypeDeclaredRule, QuantizationDeclaredRule])
@pytest.mark.parametrize("level", [1, 2])
@pytest.mark.parametrize(
    "endpoint",
    [
        ENDPOINT,
        "http://gateway.example.test:8080/v1",
        ENDPOINT + "/chat?api-version=2025-01-01&region=west",
    ],
)
def test_other_api_presence_is_manifest_based_and_per_role(
    tmp_path: Path, rule_type, level: int, endpoint: str
) -> None:
    ctx = context(
        tmp_path,
        level=level,
        models={
            "primary": {"provider": "local", "id": "weights/model"},
            "judge": {"provider": "other", "endpoint": {"base_url": endpoint}},
        },
        lock=_lock(models={"judge": _model("huggingface")}) if level == 2 else None,
    )
    judge, primary = rule_type().check(ctx)
    assert judge.status == FindingStatus.SKIPPED
    assert judge.evidence[0].field == f"models.judge.{rule_type.field}"
    assert primary.status == FindingStatus.FAIL
    assert primary.evidence[0].field == f"models.primary.{rule_type.field}"


@pytest.mark.parametrize("rule_type", [DtypeDeclaredRule, QuantizationDeclaredRule])
@pytest.mark.parametrize("endpoint", INVALID_ENDPOINTS)
def test_unsafe_or_absent_endpoint_does_not_exempt_other(
    tmp_path: Path, rule_type, endpoint: str | None
) -> None:
    model = {"provider": "other", "endpoint": {"base_url": endpoint}}
    ctx = context(tmp_path, models={"primary": model}, inference={"backend": "openai"})
    (finding,) = rule_type().check(ctx)
    assert finding.status == FindingStatus.FAIL


@pytest.mark.parametrize("provider", ["huggingface", "local", None])
def test_endpoint_alone_does_not_change_provider_classification(
    tmp_path: Path, provider: str | None
) -> None:
    ctx = context(
        tmp_path,
        models={
            "primary": {
                "provider": provider,
                "id": "models/model",
                "endpoint": {"base_url": ENDPOINT},
            }
        },
        inference={"backend": "openai"},
    )
    assert DtypeDeclaredRule().check(ctx)[0].status == FindingStatus.FAIL


def test_provider_warning_preserves_other_identity_and_explains_limitations(tmp_path: Path) -> None:
    ctx = context(
        tmp_path,
        models={"judge": {"provider": "other", "endpoint": {"base_url": ENDPOINT}}},
    )
    (finding,) = ProviderKnownRule().check(ctx)
    assert finding.status == FindingStatus.FAIL
    assert finding.severity == Severity.WARNING
    assert finding.evidence[0].note == "unsupported provider"
    assert "models.judge.endpoint.base_url" in finding.fix_hint
    assert "provider metadata" in finding.fix_hint
    assert "immutable" in finding.fix_hint
    assert ctx.manifest is not None and ctx.manifest.models["judge"].provider == "other"


@pytest.mark.parametrize(
    "pinnability,severity", [("unpinnable", Severity.WARNING), ("snapshot_alias", Severity.INFO)]
)
def test_other_api_revision_uses_existing_api_pinnability_policy(
    tmp_path: Path, pinnability: str, severity: Severity
) -> None:
    locked = _lock(
        models={
            "judge": _model(
                "other",
                pinnability=pinnability,
                revision=_provenance(
                    confidence="unresolved", value=None, source="provider_no_pinning"
                ),
            )
        }
    )
    ctx = context(
        tmp_path,
        level=2,
        lock=locked,
        models={"judge": {"provider": "other", "endpoint": {"base_url": ENDPOINT}}},
    )
    before = ctx.state.model_dump() if ctx.state is not None else None
    (finding,) = RevisionPinnedRule().check(ctx)
    assert finding.severity == severity
    assert finding.evidence[0].field == "models.judge.pinnability"
    assert finding.evidence[0].value == pinnability
    assert "source=provider_no_pinning" in (finding.evidence[0].note or "")
    assert locked.models["judge"].revision.value is None
    assert locked.models["judge"].provider == "other"
    assert ctx.state is not None and ctx.state.model_dump() == before


@pytest.mark.parametrize("endpoint", INVALID_ENDPOINTS)
def test_other_lock_with_unqualified_endpoint_keeps_critical_revision(
    tmp_path: Path, endpoint: str | None
) -> None:
    ctx = context(
        tmp_path,
        level=2,
        lock=_lock(models={"judge": _model("other", confidence="unresolved")}),
        models={"judge": {"provider": "other", "endpoint": {"base_url": endpoint}}},
    )
    (finding,) = RevisionPinnedRule().check(ctx)
    assert finding.severity == Severity.CRITICAL
    assert finding.evidence[0].field == "models.judge.revision"


@pytest.mark.parametrize("endpoint", [None, ENDPOINT])
@pytest.mark.parametrize("locked_provider", ["huggingface", "local", "openai", "other"])
def test_stale_provider_classification_uses_effective_state_not_current_manifest(
    tmp_path: Path, endpoint: str | None, locked_provider: str
) -> None:
    ctx = context(
        tmp_path,
        level=2,
        lock=_lock(
            models={
                "judge": _model(locked_provider, confidence="unresolved", pinnability="unpinnable")
            }
        ),
        models={"judge": {"provider": "other", "endpoint": {"base_url": endpoint}}},
    )
    (finding,) = RevisionPinnedRule().check(ctx)
    expected_api = locked_provider == "openai" or (locked_provider == "other" and endpoint)
    assert finding.severity == (Severity.WARNING if expected_api else Severity.CRITICAL)
    assert ctx.state is not None
    provider = ctx.state.flatten()["models.judge.provider"]
    assert provider.value == locked_provider and provider.source == "lock"
    assert provider.alternatives[0].value == "other"
    assert provider.alternatives[0].source == "manifest"


@pytest.mark.parametrize("runtime_endpoint", [ENDPOINT, "ftp://gateway.example.test/v1"])
def test_runtime_endpoint_classification_retains_alternatives_without_affecting_presence(
    tmp_path: Path, runtime_endpoint: str
) -> None:
    declared_endpoint = "https://declared.example.test/v1"
    ctx = context(
        tmp_path,
        level=2,
        lock=_lock(
            models={"judge": _model("other", confidence="unresolved", pinnability="unpinnable")}
        ),
        models={"judge": {"provider": "other", "endpoint": {"base_url": declared_endpoint}}},
        bindings={"models.judge.endpoint.base_url": {"cli": "--endpoint"}},
    )
    ctx.runs = [
        run_record(
            bindings_observed={
                "models.judge.endpoint.base_url": [
                    observation(runtime_endpoint, key="--endpoint"),
                    observation(
                        "https://config.example.test/v1",
                        kind="config",
                        key="endpoint",
                        path="config.yaml",
                    ),
                ]
            }
        )
    ]
    state = ctx.state
    assert state is not None
    ctx.state = state
    before = state.model_dump()
    (finding,) = RevisionPinnedRule().check(ctx)
    assert finding.severity == (
        Severity.WARNING if runtime_endpoint == ENDPOINT else Severity.CRITICAL
    )
    assert DtypeDeclaredRule().check(ctx)[0].status == FindingStatus.SKIPPED
    assert state.model_dump() == before
    leaf = state.flatten()["models.judge.endpoint.base_url"]
    assert (leaf.value, leaf.source, leaf.confidence, leaf.detail) == (
        runtime_endpoint,
        "run",
        "observed",
        "cli:--endpoint",
    )
    assert [(item.value, item.source) for item in leaf.alternatives] == [
        ("https://config.example.test/v1", "run"),
        (declared_endpoint, "manifest"),
    ]


def test_effective_provider_binding_is_required_even_with_qualified_endpoint(
    tmp_path: Path,
) -> None:
    ctx = context(
        tmp_path,
        level=2,
        lock=_lock(
            models={"judge": _model("other", confidence="unresolved", pinnability="unpinnable")}
        ),
        models={"judge": {"provider": "other", "endpoint": {"base_url": ENDPOINT}}},
        bindings={"models.judge.provider": {"cli": "--provider"}},
    )
    ctx.runs = [
        run_record(
            bindings_observed={
                "models.judge.provider": [observation("huggingface", key="--provider")]
            }
        )
    ]
    assert RevisionPinnedRule().check(ctx)[0].severity == Severity.CRITICAL


def test_judge_endpoint_cannot_exempt_primary_other_model(tmp_path: Path) -> None:
    ctx = context(
        tmp_path,
        level=2,
        lock=_lock(
            models={
                role: _model("other", confidence="unresolved", pinnability="unpinnable")
                for role in ("primary", "judge")
            }
        ),
        models={
            "primary": {"provider": "other"},
            "judge": {"provider": "other", "endpoint": {"base_url": ENDPOINT}},
        },
    )
    judge, primary = RevisionPinnedRule().check(ctx)
    assert judge.severity == Severity.WARNING
    assert primary.severity == Severity.CRITICAL


def test_api_classification_preserves_stale_lock_and_critical_identity_conflict(
    tmp_path: Path,
) -> None:
    ctx = context(
        tmp_path,
        level=2,
        models={
            "primary": {"provider": "other", "id": "old-alias", "endpoint": {"base_url": ENDPOINT}}
        },
        bindings={"models.primary.id": {"cli": "--model"}},
    )
    assert ctx.manifest is not None
    path = tmp_path / "reprollm.yaml"
    path.write_text(dump_yaml(ctx.manifest), encoding="utf-8")
    locked = _lock(
        models={
            "primary": _model(
                "other", id="old-alias", confidence="unresolved", pinnability="unpinnable"
            )
        }
    )
    locked.manifest_sha256 = sha256_file(path)
    (tmp_path / "reprollm.lock").write_text(dump_yaml(locked), encoding="utf-8")
    assert ctx.manifest.models["primary"].endpoint is not None
    ctx.manifest.models["primary"].endpoint.base_url = "https://changed.example.test/v1"
    path.write_text(dump_yaml(ctx.manifest), encoding="utf-8")
    run = run_record(
        bindings_observed={"models.primary.id": [observation("new-alias", key="--model")]}
    )
    directory = tmp_path / ".reprollm/runs" / run.run_id
    directory.mkdir(parents=True)
    (directory / "run.json").write_text(run.model_dump_json(), encoding="utf-8")
    report = run_audit(tmp_path)
    findings = {item.rule_id: item for item in report.findings}
    assert findings["model.revision_pinned"].severity == Severity.WARNING
    assert findings["model.provider_known"].severity == Severity.WARNING
    assert findings["model.dtype_declared"].status == FindingStatus.SKIPPED
    assert findings["consistency.lock_fresh"].status == FindingStatus.FAIL
    assert findings["consistency.lock_fresh"].severity == Severity.WARNING
    assert findings["consistency.model_identity"].severity == Severity.CRITICAL
    assert [item.value for item in findings["consistency.model_identity"].evidence] == [
        "old-alias",
        "old-alias",
        "new-alias",
    ]
