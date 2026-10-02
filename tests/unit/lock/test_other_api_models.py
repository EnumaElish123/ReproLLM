"""UX-T06: recognizing opaque API declarations adds no transport or credentials."""

from pathlib import Path

import httpx
import pytest
import respx
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.core.yaml_io import dump_yaml, load_lock
from reprollm.lock.api_resolver import resolve_api_model
from reprollm.schemas.lock import Confidence
from reprollm.schemas.manifest import ModelSpec
from tests.unit.lock.helpers import NOW, manifest, resolve

ENDPOINT = "https://gateway.example.test/v1"


@pytest.mark.parametrize("verify_api", [False, True])
@pytest.mark.parametrize(
    "model_id,pinnability",
    [
        ("vendor/model", "unpinnable"),
        ("vendor/model-2025-01-01", "snapshot_alias"),
        ("vendor/model@20250101", "snapshot_alias"),
    ],
)
def test_other_resolution_preserves_identity_and_never_looks_up_credentials(
    monkeypatch: pytest.MonkeyPatch, verify_api: bool, model_id: str, pinnability: str
) -> None:
    def unexpected_key_lookup(*args, **kwargs):
        raise AssertionError("other has no credential contract")

    monkeypatch.setattr("reprollm.lock.api_resolver.os.getenv", unexpected_key_lookup)
    model = ModelSpec.model_validate(
        {"provider": "other", "id": model_id, "endpoint": {"base_url": ENDPOINT}}
    )
    locked = resolve_api_model(model, http=None, verify_api=verify_api, now=NOW)
    assert locked.provider == "other"
    assert locked.id == model_id
    assert locked.pinnability == pinnability
    assert locked.revision.value is None
    assert locked.revision.confidence == Confidence.UNRESOLVED
    assert locked.revision.source == "provider_no_pinning"
    assert locked.revision.note == ("verify skipped: no api key" if verify_api else None)
    assert locked.observed_at == NOW
    assert "endpoint" not in locked.model_dump()


def test_offline_other_lock_constructs_no_http_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stub_run_cmd
) -> None:
    def unexpected_client(*args, **kwargs):
        raise AssertionError("offline must not construct an HTTP client")

    monkeypatch.setattr(httpx, "Client", unexpected_client)
    stub_run_cmd.on("nvidia-smi", returncode=127, stderr="not found")
    (tmp_path / "reprollm.yaml").write_text(
        dump_yaml(
            manifest(
                models={
                    "primary": {
                        "provider": "other",
                        "id": "vendor/model",
                        "endpoint": {"base_url": ENDPOINT},
                    }
                }
            )
        ),
        encoding="utf-8",
    )
    result = CliRunner().invoke(app, ["lock", str(tmp_path), "--offline"])
    assert result.exit_code == 0, result.output
    locked = load_lock(tmp_path / "reprollm.lock")
    assert locked.models["primary"].provider == "other"
    assert locked.models["primary"].revision.value is None
    assert locked.models["primary"].pinnability == "unpinnable"


def test_other_online_lock_keeps_existing_client_but_sends_no_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stub_run_cmd
) -> None:
    original_client = httpx.Client
    clients: list[httpx.Client] = []

    def tracked_client(*args, **kwargs):
        client = original_client(*args, **kwargs)
        clients.append(client)
        return client

    monkeypatch.setattr(httpx, "Client", tracked_client)
    stub_run_cmd.on("nvidia-smi", returncode=127, stderr="not found")
    (tmp_path / "reprollm.yaml").write_text(
        dump_yaml(
            manifest(
                models={
                    "primary": {
                        "provider": "other",
                        "id": "vendor/model",
                        "endpoint": {"base_url": ENDPOINT},
                    }
                }
            )
        ),
        encoding="utf-8",
    )
    router = respx.MockRouter(assert_all_called=False, assert_all_mocked=True)
    with router:
        result = CliRunner().invoke(app, ["lock", str(tmp_path), "--verify-api"])
    assert result.exit_code == 0, result.output
    assert len(clients) == 1 and clients[0].is_closed
    assert len(router.calls) == 0


def test_mixed_hf_other_resolution_keeps_mocked_hf_transport(
    tmp_path: Path, hf_mock: respx.MockRouter, stub_run_cmd, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HUGGINGFACEHUB_API_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    stub_run_cmd.on("nvidia-smi", returncode=127, stderr="not found")
    result = resolve(
        tmp_path,
        manifest(
            models={
                "primary": {"provider": "huggingface", "id": "Qwen/Qwen3-32B"},
                "judge": {
                    "provider": "other",
                    "id": "vendor/model",
                    "endpoint": {"base_url": ENDPOINT},
                },
            }
        ),
    )
    assert result.models["primary"].revision.confidence == Confidence.EXACT
    assert result.models["judge"].provider == "other"
    assert result.models["judge"].pinnability == "unpinnable"
    assert hf_mock.calls
    assert all(call.request.url.host == "huggingface.co" for call in hf_mock.calls)
