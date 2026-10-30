"""SK16 online adapters preserve native identity, transport and authorization contracts."""

from __future__ import annotations

import contextlib
import hashlib
import json
import ssl
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/reprollm/scripts"))
import skill_runtime as runtime  # noqa: E402
from skill_request import Grants, Request, dispatch  # noqa: E402

SHA = "1" * 40
CONFIG = b'{"model_type":"public"}\n'
TOKENIZER = b'{"chat_template":"{{ text }}"}\n'
HUB = "https://huggingface.co/api/models/public/model/revision/main"
CONFIG_URL = f"https://huggingface.co/public/model/resolve/{SHA}/config.json"
TOKENIZER_URL = f"https://huggingface.co/public/model/resolve/{SHA}/tokenizer_config.json"


@pytest.fixture(autouse=True)
def isolated_mock_routes():
    # Re-enter the shared router so each case restores an empty request history.
    with respx.mock:
        yield


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    from reprollm.core import proc
    from reprollm.core.proc import CmdResult

    def command(argv, **kwargs):
        if argv == ["git", "--version"]:
            return CmdResult(0, "git version 2.47.0\n", "")
        return CmdResult(127, "", "unavailable fixture")

    monkeypatch.setattr(proc, "run_cmd", command)
    for key in (
        "HF_TOKEN",
        "HUGGING_FACE_HUB_TOKEN",
        "HF_ENDPOINT",
        "OPENAI_API_KEY",
        "OPENROUTER_API_KEY",
        "ANTHROPIC_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "public-project"
    root.mkdir()
    (root / "reprollm.yaml").write_text(
        "schema_version: 1\nproject: {name: public}\nexperiment: {profiles: []}\n"
        "models:\n  primary: {provider: huggingface, id: public/model}\n",
        encoding="utf-8",
    )
    return root


@dataclass
class Context:
    root: Path
    home: Path
    identity: str = "public-test-policy"

    def check_cancel(self) -> None:
        pass

    @contextlib.contextmanager
    def publication(self):
        yield


def online(root: Path, home: Path, *, write: bool = True, network: bool = True, **options: Any):
    req = Request(
        "lock", str(root), {"offline": False, **options}, Grants(write=write, network=network)
    )
    return runtime.operation_worker_entry(req, Context(root, home))


def routes():
    info = respx.get(HUB).respond(
        200,
        json={
            "sha": SHA,
            "siblings": [{"rfilename": "config.json"}, {"rfilename": "tokenizer_config.json"}],
        },
    )
    config = respx.get(CONFIG_URL).respond(200, content=CONFIG)
    tokenizer = respx.get(TOKENIZER_URL).respond(200, content=TOKENIZER)
    return info, config, tokenizer


@pytest.mark.parametrize(
    "options,expected",
    [
        ({}, True),
        ({"offline": False}, True),
        ({"offline": True}, False),
        ({"offline": True, "hash_large_files": True}, True),
        ({"check": True}, False),
        ({"check": True, "hash_large_files": True}, False),
    ],
)
def test_online_build_uses_owned_operation_but_check_keeps_priority(options, expected):
    assert runtime.long_operation(Request("lock", options=options)) is expected


def test_network_grant_precedes_installation_and_executor(project):
    def forbidden(req):
        pytest.fail("An unauthorized network request entered the executor")

    for req in [
        Request("lock", str(project), {}, Grants(write=True)),
        Request("doctor", str(project), {"check_network": True}),
    ]:
        reply = dispatch(req, executor=forbidden)
        assert reply.invocation == "blocked" and reply.needs_authorization


def test_doctor_typed_network_flag_reaches_native_argv(project):
    req = Request("doctor", str(project), {"check_network": True}, Grants(network=True))
    argv, parsed_json = runtime.command_args(req, project)
    assert argv == ["doctor", "--json", "--check-network"] and parsed_json


@pytest.mark.parametrize("as_json", [True, False])
def test_doctor_calls_only_native_gpt2_probe(project, tmp_path, as_json):
    route = respx.get("https://huggingface.co/api/models/gpt2/revision/main").respond(
        200, json={"sha": SHA, "siblings": []}
    )
    req = Request(
        "doctor", str(project), {"check_network": True, "json": as_json}, Grants(network=True)
    )
    reply = runtime.execute(req, cache_home=tmp_path / "state/responses")
    assert reply.invocation == "handled_result" and reply.cli_exit_code == 0
    assert reply.gate_failed is None and route.call_count == 1
    if as_json:
        network = next(c for c in reply.data["checks"] if c["name"] == "network")
        assert network == {
            "name": "network",
            "status": "ok",
            "detail": "Hugging Face gpt2: revision metadata reachable",
        }
    else:
        assert "revision metadata reachable" in reply.data


def test_nominal_online_lock_preserves_complete_native_identity(project, tmp_path):
    mocks = routes()
    reply = online(project, tmp_path / "owned")
    assert reply.invocation == "handled_result" and reply.cli_exit_code == 0
    assert reply.gate_failed is None and reply.child_exit_code is None
    document = reply.data["lock"]
    assert document["resolution"]["mode"] == "online"
    primary = document["models"]["primary"]
    assert primary["revision"]["value"] == SHA
    assert primary["revision"]["source"] == "hf_api"
    assert primary["revision"]["confidence"] == "exact"
    assert primary["tokenizer"]["revision"]["value"] == SHA
    assert primary["config_sha256"]["value"] == "sha256:" + hashlib.sha256(CONFIG).hexdigest()
    assert primary["chat_template"]["sha256"]["value"] == (
        "sha256:" + hashlib.sha256(b"{{ text }}").hexdigest()
    )
    assert all(route.call_count == 1 for route in mocks)
    from reprollm.core.yaml_io import load_lock

    assert load_lock(project / "reprollm.lock").model_dump(mode="json") == document


def test_offline_after_online_does_not_invent_a_metadata_cache(project, tmp_path, monkeypatch):
    routes()
    assert online(project, tmp_path / "owned").cli_exit_code == 0

    def forbidden(*a, **k):
        pytest.fail("Offline follow-up constructed an HTTP client")

    monkeypatch.setattr(httpx, "Client", forbidden)
    reply = runtime.execute(
        Request("lock", str(project), {"offline": True}, Grants(write=True)),
        cache_home=tmp_path / "owned/responses",
    )
    assert reply.cli_exit_code == 0
    revision = reply.data["lock"]["models"]["primary"]["revision"]
    assert revision["value"] is None and revision["source"] == "offline"
    assert revision["confidence"] == "unresolved"


@pytest.mark.parametrize(
    "status,source",
    [(401, "hf_api_forbidden"), (403, "hf_api_forbidden"), (404, "hf_api_not_found")],
)
def test_hf_denial_is_unresolved_native_result_not_a_failed_audit_gate(
    project, tmp_path, monkeypatch, status, source
):
    secret = "hf_public_synthetic_key"
    monkeypatch.setenv("HF_TOKEN", secret)
    route = respx.get(HUB).respond(status)
    reply = online(project, tmp_path / "owned")
    assert reply.invocation == "handled_result" and reply.cli_exit_code == 0
    assert reply.gate_failed is None and route.call_count == 1
    revision = reply.data["lock"]["models"]["primary"]["revision"]
    assert revision["source"] == source and revision["confidence"] == "unresolved"
    assert revision["value"] is None and secret not in json.dumps(reply.as_dict())
    assert secret.encode() not in (project / "reprollm.lock").read_bytes()


@pytest.mark.parametrize(
    "failure,expected_category",
    [
        ("timeout", "timeout"),
        ("proxy", "proxy_error"),
        ("tls", "tls_error"),
        ("connect", "connection_error"),
    ],
)
def test_observed_failure_category_is_safe_and_does_not_rewrite_native_source(
    project, tmp_path, monkeypatch, failure, expected_category
):
    secret = "public-synthetic-uri-secret"
    if failure == "timeout":
        error = httpx.ReadTimeout(secret)
    elif failure == "proxy":
        error = httpx.ProxyError(secret)
    else:
        error = httpx.ConnectError(secret)
        if failure == "tls":
            error.__cause__ = ssl.SSLCertVerificationError(secret)

    class TLSFailureStream(httpx.SyncByteStream):
        def __iter__(self):
            try:
                raise ssl.SSLCertVerificationError(secret)
            except ssl.SSLError as cause:
                raise httpx.ConnectError(secret) from cause

    # respx wraps direct side effects; a mocked body preserves the actual cause chain.
    route = respx.get(HUB).mock(
        side_effect=(lambda request: httpx.Response(200, stream=TLSFailureStream()))
        if failure == "tls"
        else error
    )
    delays = []
    monkeypatch.setattr("reprollm.lock.hf_client.time.sleep", delays.append)
    reply = online(project, tmp_path / "owned")
    assert reply.cli_exit_code == 0 and reply.gate_failed is None
    assert reply.data["lock"]["models"]["primary"]["revision"]["source"] == "network_error"
    assert route.call_count == 3 and delays == [0.5, 1.5]
    categories = {
        d.get("category") for d in reply.diagnostics if d.get("code") == "network_attempt"
    }
    assert expected_category in categories
    assert secret not in json.dumps(reply.as_dict())


def test_online_preview_resolves_but_never_publishes_project_lock(project, tmp_path):
    routes()
    before = {p.name: p.read_bytes() for p in project.iterdir() if p.is_file()}
    reply = online(project, tmp_path / "owned", write=False, preview=True)
    assert reply.cli_exit_code == 0 and reply.data["phase"] == "prepared"
    assert reply.data["artifacts_written"] == []
    assert before == {p.name: p.read_bytes() for p in project.iterdir() if p.is_file()}


def test_input_mutation_after_network_keeps_previous_lock_and_does_not_retry(project, tmp_path):
    info, _, tokenizer = routes()
    old = b"original lock bytes must remain\n"
    (project / "reprollm.lock").write_bytes(old)

    def change(request):
        with (project / "reprollm.yaml").open("a", encoding="utf-8") as stream:
            stream.write("\n# Concurrent external change\n")
        return httpx.Response(200, content=CONFIG)

    config = respx.get(CONFIG_URL).mock(side_effect=change)
    reply = online(project, tmp_path / "owned")
    assert reply.invocation != "handled_result"
    assert (project / "reprollm.lock").read_bytes() == old
    assert info.call_count == tokenizer.call_count == config.call_count == 1


def test_httpx_environment_proxy_path_is_preserved(project, tmp_path, monkeypatch):
    routes()
    monkeypatch.setenv(
        "HTTPS_PROXY", "http://public_user:public_proxy_secret@proxy.example.test:8080"
    )
    monkeypatch.setenv("NO_PROXY", "")
    original = httpx.Client._get_proxy_map
    flags = []

    def observe(self, proxy, allow_env_proxies):
        flags.append(allow_env_proxies)
        return original(self, proxy, allow_env_proxies)

    monkeypatch.setattr(httpx.Client, "_get_proxy_map", observe)
    reply = online(project, tmp_path / "owned")
    assert reply.cli_exit_code == 0 and flags and all(flags)
    assert "public_proxy_secret" not in json.dumps(reply.as_dict())


@pytest.mark.parametrize(
    "provider,key_name,header",
    [
        ("openai", "OPENAI_API_KEY", "Authorization"),
        ("openrouter", "OPENROUTER_API_KEY", "Authorization"),
        ("anthropic", "ANTHROPIC_API_KEY", "x-api-key"),
    ],
)
@pytest.mark.parametrize("verify", [False, True])
def test_api_verification_is_explicit_metadata_and_preserves_unpinnability(
    project, tmp_path, monkeypatch, provider, key_name, header, verify
):
    secret = "public_synthetic_provider_key"
    monkeypatch.setenv(key_name, secret)
    (project / "reprollm.yaml").write_text(
        "schema_version: 1\nproject: {name: public}\nexperiment: {profiles: []}\n"
        f"models:\n  judge:\n    provider: {provider}\n    id: public-model\n"
        "    endpoint: {base_url: 'https://public-gateway.example.test/v1'}\n",
        encoding="utf-8",
    )
    route = None
    if verify:
        route = respx.get("https://public-gateway.example.test/v1/models/public-model").respond(200)
    reply = online(project, tmp_path / "owned", verify_api=verify)
    assert reply.invocation == "handled_result" and reply.cli_exit_code == 0
    judge = reply.data["lock"]["models"]["judge"]
    assert judge["pinnability"] == "unpinnable"
    assert judge["revision"]["value"] is None and judge["revision"]["confidence"] == "unresolved"
    assert judge["revision"]["note"] == ("exists" if verify else None)
    if verify:
        assert route is not None and route.call_count == 1
        assert secret in route.calls[0].request.headers[header]
    assert secret not in json.dumps(reply.as_dict())


@pytest.mark.parametrize("action", ["lock", "doctor"])
def test_direct_adapter_network_grant_precedes_client_or_cli(project, tmp_path, action):
    def forbidden(*args, **kwargs):
        pytest.fail("Missing network grant reached a network-capable collaborator")

    if action == "lock":
        import skill_local

        reply = skill_local.execute_lock(
            Request("lock", str(project), {}, Grants(write=True)),
            root=project,
            state_home=tmp_path / "state",
            identity="grant-test",
            client_context_factory=forbidden,
        )
    else:
        reply = runtime.execute(
            Request("doctor", str(project), {"check_network": True}),
            cache_home=tmp_path / "state/responses",
            cli_runner=forbidden,
        )
    assert reply.invocation == "blocked" and reply.needs_authorization


def test_online_lock_full_document_and_stdout_equal_native(project, tmp_path, monkeypatch):
    import shutil
    from datetime import datetime

    from reprollm.lock import writer

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 31, 0, 0, 0, tzinfo=tz)

    monkeypatch.setattr(writer, "datetime", Clock)
    reference = tmp_path / "reference"
    shutil.copytree(project, reference)
    mocks = routes()
    native = runtime.invoke_cli(["lock", str(reference)], reference)
    reply = online(project, tmp_path / "owned")
    assert native.exit_code == reply.cli_exit_code == 0
    assert (project / "reprollm.lock").read_bytes() == (reference / "reprollm.lock").read_bytes()
    assert reply.data["stdout"] == native.stdout
    assert all(mock.call_count == 2 for mock in mocks)


@pytest.mark.parametrize("offline", [True, False])
def test_check_priority_and_offline_verify_never_construct_client(
    project, tmp_path, monkeypatch, offline
):
    import skill_local

    def forbidden(*args, **kwargs):
        pytest.fail("Offline/check constructed a client context")

    if not offline:
        respx.get(HUB).respond(403)
    first = skill_local.execute_lock(
        Request("lock", str(project), {"offline": True, "verify_api": True}, Grants(write=True)),
        root=project,
        state_home=tmp_path / "state",
        identity="precedence",
        client_context_factory=forbidden,
    )
    assert first.cli_exit_code == 0
    monkeypatch.setattr(httpx, "Client", forbidden)
    reply = runtime.execute(
        Request(
            "lock",
            str(project),
            {"check": True, "offline": offline, "verify_api": True, "hash_large_files": True},
        ),
        cache_home=tmp_path / "state/responses",
    )
    assert reply.cli_exit_code == 0 and reply.data["reasons"] == []


@pytest.mark.parametrize("failure", ["dependency", "tls_configuration"])
def test_client_construction_failures_are_safe_and_preserve_lock(
    project, tmp_path, monkeypatch, failure
):
    old = b"previous lock remains\n"
    (project / "reprollm.lock").write_bytes(old)
    secret = "synthetic-proxy-credential-never-emit"

    def invalid(self, *args, **kwargs):
        if failure == "dependency":
            raise ImportError(secret)
        raise ssl.SSLError(secret)

    monkeypatch.setattr(httpx.Client, "__init__", invalid)
    reply = online(project, tmp_path / "state")
    assert reply.invocation == "blocked" and reply.complete is False
    assert {"code": "network_client_unavailable"} in reply.diagnostics
    category = "dependency_unavailable" if failure == "dependency" else "tls_error"
    assert {"code": "network_client", "category": category} in reply.diagnostics
    assert secret not in json.dumps(reply.as_dict())
    assert (project / "reprollm.lock").read_bytes() == old


@pytest.mark.parametrize("verify", [False, True])
def test_other_provider_never_guesses_a_key_or_makes_a_verification_request(
    project, tmp_path, monkeypatch, verify
):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-key-not-for-other")
    (project / "reprollm.yaml").write_text(
        "schema_version: 1\nproject: {name: public}\nexperiment: {profiles: []}\n"
        "models:\n  judge:\n    provider: other\n    id: public-model\n"
        "    endpoint: {base_url: 'https://other.example.test/v1'}\n",
        encoding="utf-8",
    )
    reply = online(project, tmp_path / "state", verify_api=verify)
    assert reply.cli_exit_code == 0
    model = reply.data["lock"]["models"]["judge"]
    assert model["revision"]["value"] is None
    assert model["revision"]["note"] == ("verify skipped: no api key" if verify else None)
    assert not any(d.get("code") == "network_attempt" for d in reply.diagnostics)


@pytest.mark.parametrize(
    "status,note",
    [
        (200, "exists"),
        (404, "not_found"),
        (401, "verify error: HTTP 401"),
        (403, "verify error: HTTP 403"),
        (500, "verify error: HTTP 500"),
    ],
)
def test_api_http_result_remains_native_and_never_adds_outer_retries(
    project, tmp_path, monkeypatch, status, note
):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-provider-key")
    (project / "reprollm.yaml").write_text(
        "schema_version: 1\nproject: {name: public}\nexperiment: {profiles: []}\n"
        "models:\n  judge: {provider: openai, id: public-model}\n",
        encoding="utf-8",
    )
    route = respx.get("https://api.openai.com/v1/models/public-model").respond(status)
    reply = online(project, tmp_path / "state", verify_api=True)
    assert reply.cli_exit_code == 0 and route.call_count == 1
    assert reply.data["lock"]["models"]["judge"]["revision"]["note"] == note


def test_reviewed_manifest_change_rejects_before_sending_credentials(project, tmp_path):
    manifest = project / "reprollm.yaml"
    reviewed = hashlib.sha256(manifest.read_bytes()).hexdigest()
    manifest.write_bytes(manifest.read_bytes() + b"\n# changed declaration\n")
    request = Request(
        "lock",
        str(project),
        {},
        Grants(
            network=True,
            write=True,
            expected_hashes={"reprollm.yaml": reviewed},
        ),
    )
    reply = runtime.operation_worker_entry(request, Context(project, tmp_path / "state"))
    assert reply.invocation == "blocked" and reply.needs_input
    assert not (project / "reprollm.lock").exists()


@pytest.mark.parametrize(
    "first,fallback,expected",
    [
        ("hf_synthetic_primary", "hf_synthetic_fallback", "Bearer hf_synthetic_primary"),
        (None, "hf_synthetic_fallback", "Bearer hf_synthetic_fallback"),
        ("  ", "hf_synthetic_fallback", None),
    ],
)
def test_hf_endpoint_and_token_precedence_remain_native(
    project, tmp_path, monkeypatch, first, fallback, expected
):
    monkeypatch.setenv("HF_ENDPOINT", "https://selected-hub.example.test")
    if first is not None:
        monkeypatch.setenv("HF_TOKEN", first)
    monkeypatch.setenv("HUGGING_FACE_HUB_TOKEN", fallback)
    route = respx.get(
        "https://selected-hub.example.test/api/models/public/model/revision/main"
    ).respond(403)
    reply = online(project, tmp_path / "state")
    assert reply.cli_exit_code == 0 and route.call_count == 1
    request = route.calls[0].request
    assert request.headers.get("Authorization") == expected
    assert request.extensions["timeout"] == {
        key: 10.0 for key in ("connect", "read", "write", "pool")
    }
    assert fallback not in json.dumps(reply.as_dict())


def test_online_preview_approval_rejects_remote_alias_change(project, tmp_path):
    routes()
    first = online(project, tmp_path / "state", preview=True, write=False)
    assert first.data["phase"] == "prepared"
    respx.get(HUB).respond(200, json={"sha": "2" * 40, "siblings": []})
    request = Request(
        "lock",
        str(project),
        {},
        Grants(
            network=True,
            write=True,
            plan_hash=first.data["plan_hash"],
        ),
    )
    reply = runtime.operation_worker_entry(request, Context(project, tmp_path / "state"))
    assert reply.invocation == "blocked" and not (project / "reprollm.lock").exists()


@pytest.mark.parametrize("action", ["lock", "doctor"])
def test_selected_socks_proxy_without_optional_dependency_is_not_silently_bypassed(
    project, tmp_path, monkeypatch, action
):
    secret = "synthetic-proxy-secret"
    monkeypatch.setenv("ALL_PROXY", f"socks5://public-user:{secret}@proxy.example.test:1080")
    monkeypatch.setenv("NO_PROXY", "")
    monkeypatch.setitem(sys.modules, "socksio", None)
    if action == "lock":
        reply = online(project, tmp_path / "state")
        assert reply.invocation == "blocked" and not (project / "reprollm.lock").exists()
        assert {"code": "network_client", "category": "dependency_unavailable"} in reply.diagnostics
    else:
        reply = runtime.execute(
            Request("doctor", str(project), {"check_network": True}, Grants(network=True)),
            cache_home=tmp_path / "state/responses",
        )
        assert reply.invocation == "internal_error" and reply.cli_exit_code == 3
    assert secret not in json.dumps(reply.as_dict())


def test_default_tls_verification_and_environment_trust_are_preserved(
    project, tmp_path, monkeypatch
):
    routes()
    original = httpx.Client._init_transport
    observed = []

    def transport(self, **kwargs):
        observed.append((kwargs["verify"], kwargs["trust_env"], kwargs["transport"]))
        return original(self, **kwargs)

    monkeypatch.setattr(httpx.Client, "_init_transport", transport)
    reply = online(project, tmp_path / "state")
    assert reply.cli_exit_code == 0 and observed == [(True, True, None)]


def test_network_diagnostics_are_bounded_and_never_infer_tls_from_error_text():
    from skill_network import MAX_OBSERVATIONS, client_context, failure_category

    error = httpx.ConnectError("SSL certificate synthetic-secret")
    error.__cause__ = error
    assert failure_category(error) == "connection_error"
    route = respx.get("https://public.example.test/metadata").respond(200)
    diagnostics = []
    with client_context(diagnostics) as http:
        for _ in range(MAX_OBSERVATIONS + 3):
            http.get("https://public.example.test/metadata")
    assert route.call_count == MAX_OBSERVATIONS + 3
    assert len(diagnostics) == MAX_OBSERVATIONS + 1
    assert diagnostics[-1] == {"code": "network_observation_limit", "limit": MAX_OBSERVATIONS}
    assert "public.example.test" not in json.dumps(diagnostics)


@pytest.mark.parametrize("provider", ["openai", "openrouter", "anthropic"])
def test_verification_without_the_selected_provider_key_remains_unverified(
    project, tmp_path, provider
):
    (project / "reprollm.yaml").write_text(
        "schema_version: 1\nproject: {name: public}\nexperiment: {profiles: []}\n"
        f"models:\n  judge: {{provider: {provider}, id: public-model}}\n",
        encoding="utf-8",
    )
    reply = online(project, tmp_path / "state", verify_api=True)
    assert reply.cli_exit_code == 0
    revision = reply.data["lock"]["models"]["judge"]["revision"]
    assert revision["value"] is None and revision["confidence"] == "unresolved"
    assert revision["note"] == "verify skipped: no api key"
    assert not any(event.get("code") == "network_attempt" for event in reply.diagnostics)


def test_owned_cancellation_stops_native_retries_before_next_send(project, tmp_path, monkeypatch):
    from skill_local import LocalError

    class Cancellable(Context):
        cancelled = False

        def check_cancel(self):
            if self.cancelled:
                raise LocalError("operation_cancelled")

    context = Cancellable(project, tmp_path / "state")
    old = b"prior lock remains\n"
    (project / "reprollm.lock").write_bytes(old)

    def interrupt(request):
        context.cancelled = True
        raise httpx.ReadTimeout("synthetic-timeout-without-visible-text")

    route = respx.get(HUB).mock(side_effect=interrupt)
    delays = []
    monkeypatch.setattr("reprollm.lock.hf_client.time.sleep", delays.append)
    reply = runtime.operation_worker_entry(
        Request("lock", str(project), {}, Grants(network=True, write=True)),
        context,
    )
    assert reply.invocation == "blocked" and reply.complete is False
    assert {"code": "operation_cancelled"} in reply.diagnostics
    assert route.call_count == 1 and delays == [0.5]
    assert (project / "reprollm.lock").read_bytes() == old
