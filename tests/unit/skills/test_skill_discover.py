"""Native preview, explicit approval, immutable publication and changed inputs."""

from __future__ import annotations

import contextlib
import dataclasses
import hashlib
import json
import sys
import warnings
from pathlib import Path

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/reprollm/scripts"))
import skill_discover as discover  # noqa: E402
from skill_discover_guard import identity  # noqa: E402
from skill_request import Grants, Request  # noqa: E402
from tests.unit.skills.test_skill_discover_guard import (  # noqa: E402
    ENDPOINT,
    KEY,
    approval,
    policy,
    response,
)

from reprollm.core.proc import CmdResult  # noqa: E402
from reprollm.schemas.discover_candidates import DiscoverCandidates  # noqa: E402


@pytest.fixture(autouse=True)
def offline_test_boundary(monkeypatch):
    respx.reset()
    monkeypatch.setattr("reprollm.core.proc.run_cmd", lambda *a, **kw: CmdResult(127, "", ""))


@pytest.fixture
def project(tmp_path, monkeypatch):
    root = tmp_path / "research"
    root.mkdir()
    (root / "README.md").write_text(
        "# Public experiment\nUse --repeat to repeat.\n", encoding="utf-8"
    )
    (root / "train.py").write_text(
        "import argparse\np=argparse.ArgumentParser()\np.add_argument('--repeat',type=int)\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("REPROLLM_LLM_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setenv("REPROLLM_LLM_API_KEY", KEY)
    monkeypatch.setenv("REPROLLM_LLM_MODEL", "deepseek-flash")
    return root


@dataclasses.dataclass
class Context:
    root: Path
    home: Path
    identity: str = "b" * 64
    operation_id: str = "1" * 32

    def check_cancel(self):
        pass

    def publication(self):
        return contextlib.nullcontext()


def preview(root, home, **options):
    return discover.preview(
        Request("discover.preview", str(root), {"experimental": True, **options}),
        root=root,
        state_home=home,
        helper_identity="b" * 64,
    )


def approved(root, home):
    pre = preview(root, home, show_content=True)
    assert pre.cli_exit_code == 0 and pre.complete
    bindings = pre.data["approval_requirements"]
    price = policy()
    grant = approval(
        price,
        source_sha256=bindings["source_sha256"],
        messages_sha256=bindings["messages_sha256"],
    )
    raw = {
        "schema_version": 1,
        "currency": "CNY",
        "policy": {**dataclasses.asdict(price), "served_models": list(price.served_models)},
        "approval": dataclasses.asdict(grant),
    }
    return Request(
        "discover",
        str(root),
        {"experimental": True},
        Grants(install=False, write=True, network=True, paid_discover=raw),
    )


def test_preview_uses_native_messages_without_credentials_or_any_client(
    project, tmp_path, monkeypatch
):
    for key in ("REPROLLM_LLM_BASE_URL", "REPROLLM_LLM_API_KEY", "REPROLLM_LLM_MODEL"):
        monkeypatch.delenv(key)
    monkeypatch.setattr(
        httpx.Client, "__init__", lambda *a, **kw: pytest.fail("preview made Client")
    )
    before = {p.name: p.read_bytes() for p in project.iterdir()}
    result = preview(project, tmp_path / "state", show_content=True)
    assert result.cli_exit_code == 0 and result.data["nothing_sent"]
    assert result.data["approval_requirements"]["messages_sha256"] == identity(
        result.data["messages"]
    )
    assert "--repeat" in result.data["messages"][1]["content"]
    assert {p.name: p.read_bytes() for p in project.iterdir()} == before
    assert not (tmp_path / "state").exists()


@pytest.mark.linux_only
@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux owned paid workers")
def test_approved_native_result_is_finalized_but_never_accepted(project, tmp_path):
    context = Context(project, tmp_path / "home")
    request = approved(project, context.home)
    route = respx.post(ENDPOINT).mock(return_value=response())
    result = discover.execute(request, context)
    assert result.cli_exit_code == 0 and result.data["phase"] == "applied"
    assert route.call_count == 1
    paths = list((project / ".reprollm/discover").glob("*.json"))
    assert len(paths) == 1
    document = DiscoverCandidates.model_validate_json(paths[0].read_bytes())
    assert document.candidates == [] and document.input_files == ["README.md", "train.py#L3"]
    assert not (project / ".reprollm/project-rules.yaml").exists()
    assert KEY not in json.dumps(result.as_dict())
    assert KEY not in paths[0].read_text(encoding="utf-8")


@pytest.mark.linux_only
@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux owned paid workers")
def test_approved_discovery_preserves_collection_warning_facts_without_extra_posts(
    project, tmp_path
):
    (project / "train.py").write_text(
        "import argparse\np=argparse.ArgumentParser()\n"
        'p.add_argument("--pattern", default="\\D")\n',
        encoding="utf-8",
    )
    context = Context(project, tmp_path / "home")
    with warnings.catch_warnings():
        warnings.simplefilter("always")
        request = approved(project, context.home)
        route = respx.post(ENDPOINT).mock(return_value=response())
        result = discover.execute(request, context)
    assert result.cli_exit_code == 0 and result.data["phase"] == "applied"
    assert route.call_count == 1
    assert result.diagnostics == [
        {
            "code": "discover_collection_warning",
            "category": "syntax_warning" if sys.version_info >= (3, 12) else "deprecation_warning",
            "count": 3,
            "count_is_lower_bound": False,
        }
    ]
    assert result.data["budget"]["attempt_count"] == 1


def test_preview_warning_diagnostics_bound_counts_and_hide_unknown_categories(
    project, tmp_path, monkeypatch
):
    from reprollm.discover import collector

    original = collector.collect

    class PrivateMachineWarning(Warning):
        pass

    def emit_warnings(*args, **kwargs):
        warnings.warn(
            "PRIVATE_WARNING_BODY /home/private-user/source.py",
            PrivateMachineWarning,
            stacklevel=2,
        )
        for _ in range(1001):
            warnings.warn("PRIVATE_REPEATED_BODY", UserWarning, stacklevel=2)
        return original(*args, **kwargs)

    baseline = preview(project, tmp_path / "state", show_content=True)
    monkeypatch.setattr(collector, "collect", emit_warnings)
    with warnings.catch_warnings():
        warnings.simplefilter("always")
        result = preview(project, tmp_path / "state", show_content=True)
    assert result.data == baseline.data
    assert result.diagnostics == [
        {
            "code": "discover_collection_warning",
            "category": "other_warning",
            "count": 1,
            "count_is_lower_bound": False,
        },
        {
            "code": "discover_collection_warning",
            "category": "user_warning",
            "count": 1000,
            "count_is_lower_bound": True,
        },
    ]
    wire = json.dumps(result.as_dict())
    assert "PRIVATE_WARNING_BODY" not in wire and "PRIVATE_REPEATED_BODY" not in wire
    assert "PrivateMachineWarning" not in wire and "/home/private-user" not in wire


@pytest.mark.parametrize("kind", ["missing", "changed-source", "changed-endpoint", "changed-model"])
@pytest.mark.linux_only
@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux owned paid workers")
def test_pre_send_changes_or_missing_spending_grant_send_nothing(
    project, tmp_path, monkeypatch, kind
):
    context = Context(project, tmp_path / "home")
    request = approved(project, context.home)
    if kind == "missing":
        request = dataclasses.replace(request, grants=Grants(write=True, network=True))
    elif kind == "changed-source":
        (project / "README.md").write_text("changed", encoding="utf-8")
    elif kind == "changed-endpoint":
        monkeypatch.setenv("REPROLLM_LLM_BASE_URL", "https://other.invalid")
    else:
        monkeypatch.setenv("REPROLLM_LLM_MODEL", "other-model")
    route = respx.post(ENDPOINT).mock(return_value=response())
    result = discover.execute(request, context)
    assert result.invocation == "blocked" and not result.complete
    assert route.call_count == 0 and not (project / ".reprollm/discover").exists()


@pytest.mark.linux_only
@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux owned paid workers")
def test_source_change_after_paid_response_is_charged_unapplied_without_resend(project, tmp_path):
    context = Context(project, tmp_path / "home")
    request = approved(project, context.home)

    def changed(request):
        (project / "README.md").write_text("changed during response", encoding="utf-8")
        return response()

    route = respx.post(ENDPOINT).mock(side_effect=changed)
    result = discover.execute(request, context)
    assert result.invocation == "blocked" and result.data["phase"] == "unapplied"
    assert result.data["budget"]["attempt_count"] == 1
    assert result.data["budget"]["held_nano"] == 2621440000
    assert route.call_count == 1 and not (project / ".reprollm/discover").exists()


@pytest.mark.linux_only
@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux owned paid workers")
def test_actual_source_candidate_requires_separate_specific_acceptance(project, tmp_path):
    from skill_local import execute_rules
    from skill_runtime import invoke_cli

    from reprollm.core.rule_lifecycle import read_rules
    from reprollm.schemas.discover_candidates import candidate_id

    context = Context(project, tmp_path / "home")
    manifest = project / "reprollm.yaml"
    manifest.write_text(
        "schema_version: 1\nproject: {name: public}\nexperiment: {profiles: []}\n", encoding="utf-8"
    )
    request = approved(project, context.home)
    raw = {
        "kind": "parameter",
        "name": "repeat",
        "suggested_field": "custom.repeat",
        "suggested_severity": "WARNING",
        "confidence": "high",
        "rationale": "Record repeat count",
        "evidence": [
            {
                "kind": "code",
                "path": "train.py",
                "line": 3,
                "snippet": "p.add_argument('--repeat',type=int)",
            }
        ],
        "suggested_bindings": {"cli": "--repeat"},
    }
    respx.post(ENDPOINT).mock(return_value=response(json.dumps({"candidates": [raw]})))
    result = discover.execute(request, context)
    assert result.cli_exit_code == 0
    source = project / result.data["artifacts_written"][0]
    document = DiscoverCandidates.model_validate_json(source.read_bytes())
    candidate = document.candidates[0]
    assert candidate.id == candidate_id("parameter", "repeat", "train.py")
    assert (
        candidate.evidence[0].snippet
        in (project / "train.py").read_text(encoding="utf-8").splitlines()[2]
    )
    assert read_rules(project).rules == []
    accepted = Request(
        "rules.accept",
        str(project),
        {"candidate_id": candidate.id},
        Grants(
            write=True,
            expected_hashes={
                source.relative_to(project).as_posix(): hashlib.sha256(
                    source.read_bytes()
                ).hexdigest(),
                ".reprollm/project-rules.yaml": None,
            },
        ),
    )
    first = execute_rules(
        accepted, root=project, state_home=context.home / "writes", identity=context.identity
    )
    assert first.cli_exit_code == 0
    rules = read_rules(project).rules
    assert len(rules) == 1 and rules[0].candidate_id == candidate.id
    assert rules[0].bindings.cli == "--repeat"
    current = project / ".reprollm/project-rules.yaml"
    before = current.read_bytes()
    accepted = dataclasses.replace(
        accepted,
        grants=dataclasses.replace(
            accepted.grants,
            expected_hashes={
                source.relative_to(project).as_posix(): hashlib.sha256(
                    source.read_bytes()
                ).hexdigest(),
                ".reprollm/project-rules.yaml": hashlib.sha256(before).hexdigest(),
            },
        ),
    )
    duplicate = execute_rules(
        accepted, root=project, state_home=context.home / "writes", identity=context.identity
    )
    assert duplicate.cli_exit_code == 2 and current.read_bytes() == before
    argv = ["audit", str(project), "--level", "1", "--format", "json", "--fail-on", "never"]
    missing = invoke_cli(argv, project)
    assert missing.exit_code == 0
    observed = [
        item for item in json.loads(missing.stdout)["findings"] if item["rule_id"] == rules[0].id
    ]
    assert len(observed) == 1 and observed[0]["status"] == "fail"
    manifest.write_text(
        manifest.read_text(encoding="utf-8") + "custom: {repeat: 4}\n", encoding="utf-8"
    )
    declared = invoke_cli(argv, project)
    assert declared.exit_code == 0
    observed = [
        item for item in json.loads(declared.stdout)["findings"] if item["rule_id"] == rules[0].id
    ]
    assert len(observed) == 1 and observed[0]["status"] == "pass"


@pytest.mark.linux_only
@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux owned paid workers")
def test_failure_after_publication_reports_actual_file_and_retained_cost(
    project, tmp_path, monkeypatch
):
    context = Context(project, tmp_path / "home")
    request = approved(project, context.home)
    original = discover.writes.publish_artifact

    def committed_then_failed(artifact, published):
        original(artifact, published)
        raise OSError("private implementation text must not escape")

    monkeypatch.setattr(discover.writes, "publish_artifact", committed_then_failed)
    respx.post(ENDPOINT).mock(return_value=response())
    result = discover.execute(request, context)
    assert result.invocation == "blocked" and result.data["phase"] == "partial"
    assert len(result.data["artifacts_written"]) == 1
    assert (project / result.data["artifacts_written"][0]).is_file()
    assert result.data["budget"]["held_nano"] == 2621440000
    assert "private implementation text" not in json.dumps(result.as_dict())


@pytest.mark.linux_only
@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux owned paid workers")
def test_client_setup_failure_is_known_zero_cost_without_private_error_text(
    project, tmp_path, monkeypatch
):
    context = Context(project, tmp_path / "home")
    request = approved(project, context.home)

    def unavailable(*a, **kw):
        raise ImportError("proxy setup private " + KEY)

    monkeypatch.setattr(httpx.Client, "__init__", unavailable)
    result = discover.execute(request, context)
    assert result.invocation == "blocked" and result.data["budget"]["attempt_count"] == 0
    assert result.data["budget"]["held_nano"] == 0
    assert any(item.get("category") == "dependency_unavailable" for item in result.diagnostics)
    assert KEY not in json.dumps(result.as_dict())
    ledgers = list((context.home / "operations/discovery-budgets").glob("*.json"))
    assert len(ledgers) == 1 and json.loads(ledgers[0].read_bytes())["attempts"] == []


@pytest.mark.parametrize(
    "error, category",
    [
        (httpx.ProxyError("private " + KEY), "proxy_error"),
        (httpx.ReadTimeout("private " + KEY), "timeout"),
    ],
)
@pytest.mark.linux_only
@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux owned paid workers")
def test_native_transport_failure_keeps_category_and_unknown_charge(
    project, tmp_path, error, category
):
    context = Context(project, tmp_path / "home")
    request = approved(project, context.home)
    route = respx.post(ENDPOINT).mock(side_effect=error)
    result = discover.execute(request, context)
    assert result.invocation == "internal_error" and result.cli_exit_code == 3
    assert result.data["budget"]["attempt_count"] == 1
    assert result.data["budget"]["charge_uncertain"]
    assert result.data["budget"]["held_nano"] == 2621440000
    assert any(item.get("category") == category for item in result.diagnostics)
    assert route.call_count == 1 and KEY not in json.dumps(result.as_dict())


@pytest.mark.linux_only
@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux owned paid workers")
def test_underfunded_total_grant_does_not_collect_claim_send_or_publish(
    project, tmp_path, monkeypatch
):
    context = Context(project, tmp_path / "home")
    request = approved(project, context.home)
    request.grants.paid_discover["approval"]["max_attempts"] = 3
    route = respx.post(ENDPOINT).mock(return_value=response())
    monkeypatch.setattr(discover, "_collect", lambda *a: pytest.fail("underfunded grant collected"))
    result = discover.execute(request, context)
    assert result.invocation == "blocked" and result.needs_authorization
    assert any(
        item["code"] == "discover_budget_insufficient_for_attempt_limit"
        for item in result.diagnostics
    )
    assert route.call_count == 0 and not context.home.exists()
    assert not (project / ".reprollm/discover").exists()
