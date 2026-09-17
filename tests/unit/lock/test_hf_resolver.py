from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx

from reprollm.core.hashing import sha256_text
from reprollm.schemas.lock import Confidence

from .helpers import manifest, resolve

QWEN_SHA = "8fa23e7c1a0000000000000000000000000000aa"


def test_hf_model_dataset_and_same_repo_tokenizer_resolve_exactly(
    tmp_path: Path, hf_mock: respx.MockRouter
) -> None:
    result = resolve(
        tmp_path,
        manifest(
            models={"primary": {"provider": "huggingface", "id": "Qwen/Qwen3-32B"}},
            datasets={"eval": {"provider": "huggingface", "id": "cais/mmlu"}},
        ),
    )

    model = result.models["primary"]
    assert model.revision.value == QWEN_SHA
    assert model.revision.confidence == Confidence.EXACT
    assert model.tokenizer is not None
    assert model.tokenizer.id == "Qwen/Qwen3-32B"
    assert model.tokenizer.revision.value == QWEN_SHA
    assert model.chat_template is not None
    assert model.chat_template.status == "present"
    assert model.chat_template.sha256.source == "hf_file:tokenizer_config.json"
    assert model.config_sha256 is not None
    assert model.config_sha256.source == "hf_file:config.json"
    assert result.datasets["eval"].revision.value == ("b77a9100b00000000000000000000000000000bb")
    model_info_calls = [
        call
        for call in hf_mock.calls
        if call.request.url.path == "/api/models/Qwen/Qwen3-32B/revision/main"
    ]
    assert len(model_info_calls) == 1


def test_declared_model_revision_is_sent_to_hub(tmp_path: Path) -> None:
    router = respx.MockRouter(assert_all_called=False, assert_all_mocked=True)
    paths: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path.startswith("/api/models/"):
            return httpx.Response(200, json={"sha": "resolved-sha", "siblings": []})
        raise AssertionError(request.url)

    router.get(url__regex=r"https://huggingface\.co/.*").mock(side_effect=respond)
    with router:
        result = resolve(
            tmp_path,
            manifest(
                models={
                    "primary": {
                        "provider": "huggingface",
                        "id": "org/model",
                        "revision": "release/v1",
                    }
                }
            ),
        )

    assert "/api/models/org/model/revision/release/v1" in paths
    assert result.models["primary"].revision.value == "resolved-sha"


def test_chat_template_jinja_has_priority(tmp_path: Path) -> None:
    router = respx.MockRouter(assert_all_called=False, assert_all_mocked=True)
    fetched: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        fetched.append(request.url.path)
        if request.url.path.startswith("/api/models/"):
            return httpx.Response(
                200,
                json={
                    "sha": "abc",
                    "siblings": [
                        {"rfilename": "chat_template.jinja"},
                        {"rfilename": "tokenizer_config.json"},
                    ],
                },
            )
        if request.url.path.endswith("/chat_template.jinja"):
            return httpx.Response(200, content=b"{{ messages }}")
        raise AssertionError(request.url)

    router.get(url__regex=r"https://huggingface\.co/.*").mock(side_effect=respond)
    with router:
        model = resolve(
            tmp_path,
            manifest(models={"primary": {"provider": "huggingface", "id": "org/model"}}),
        ).models["primary"]

    assert model.chat_template is not None
    assert model.chat_template.sha256.source == "hf_file:chat_template.jinja"
    assert not any(path.endswith("tokenizer_config.json") for path in fetched)


def test_distinct_tokenizer_repo_and_structured_template_are_resolved(tmp_path: Path) -> None:
    router = respx.MockRouter(assert_all_called=False, assert_all_mocked=True)
    paths: list[str] = []
    template = [{"role": "user", "template": "{{ content }}"}]

    def respond(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path == "/api/models/org/model/revision/main":
            return httpx.Response(200, json={"sha": "model-sha", "siblings": []})
        if request.url.path == "/api/models/org/tokenizer/revision/token-v1":
            return httpx.Response(
                200,
                json={
                    "sha": "tokenizer-sha",
                    "siblings": [{"rfilename": "tokenizer_config.json"}],
                },
            )
        if request.url.path.endswith("/tokenizer_config.json"):
            return httpx.Response(200, json={"chat_template": template})
        raise AssertionError(request.url)

    router.get(url__regex=r"https://huggingface\.co/.*").mock(side_effect=respond)
    with router:
        model = resolve(
            tmp_path,
            manifest(
                models={
                    "primary": {
                        "provider": "huggingface",
                        "id": "org/model",
                        "tokenizer": {"id": "org/tokenizer", "revision": "token-v1"},
                    }
                }
            ),
        ).models["primary"]

    assert "/api/models/org/tokenizer/revision/token-v1" in paths
    assert model.tokenizer is not None
    assert model.tokenizer.revision.value == "tokenizer-sha"
    assert model.chat_template is not None
    serialized = json.dumps(template, sort_keys=True, ensure_ascii=False)
    assert model.chat_template.sha256.value == sha256_text(serialized)


def test_custom_chat_template_is_local_and_skips_remote_template(
    tmp_path: Path, hf_mock: respx.MockRouter
) -> None:
    template = tmp_path / "templates/chat.jinja"
    template.parent.mkdir()
    template.write_text("{{ messages }}", encoding="utf-8")

    model = resolve(
        tmp_path,
        manifest(
            models={
                "primary": {
                    "provider": "huggingface",
                    "id": "Qwen/Qwen3-32B",
                    "chat_template": {"path": "templates/chat.jinja"},
                }
            }
        ),
    ).models["primary"]

    assert model.chat_template is not None
    assert model.chat_template.status == "custom_file"
    assert model.chat_template.sha256.source == "filesystem"
    assert not any(
        call.request.url.path.endswith("tokenizer_config.json") for call in hf_mock.calls
    )


def test_absent_chat_template_is_recorded_as_known_absent(tmp_path: Path) -> None:
    router = respx.MockRouter(assert_all_called=False, assert_all_mocked=True)
    router.get("https://huggingface.co/api/models/org/model/revision/main").mock(
        return_value=httpx.Response(200, json={"sha": "abc", "siblings": []})
    )
    with router:
        model = resolve(
            tmp_path,
            manifest(models={"primary": {"provider": "huggingface", "id": "org/model"}}),
        ).models["primary"]

    assert model.chat_template is not None
    assert model.chat_template.status == "absent"
    assert model.chat_template.sha256.confidence == Confidence.EXACT
    assert model.chat_template.sha256.value is None


def test_gated_model_becomes_unresolved_without_exposing_credentials(
    tmp_path: Path, hf_mock: respx.MockRouter
) -> None:
    model = resolve(
        tmp_path,
        manifest(
            models={
                "primary": {
                    "provider": "huggingface",
                    "id": "meta-llama/Llama-3.1-8B-Instruct",
                }
            }
        ),
    ).models["primary"]

    assert model.revision.confidence == Confidence.UNRESOLVED
    assert model.revision.source == "hf_api_forbidden"
    assert model.revision.value is None


def test_offline_hf_resolution_never_calls_http_and_preserves_declared_revision(
    tmp_path: Path,
) -> None:
    result = resolve(
        tmp_path,
        manifest(
            models={
                "declared": {
                    "provider": "huggingface",
                    "id": "org/model",
                    "revision": "v1",
                },
                "unknown": {"provider": "huggingface", "id": "org/other"},
            },
            datasets={"eval": {"provider": "huggingface", "id": "org/data", "revision": "v2"}},
        ),
        offline=True,
    )

    assert result.models["declared"].revision.confidence == Confidence.DECLARED
    assert result.models["declared"].revision.value == "v1"
    assert result.models["unknown"].revision.source == "offline"
    assert result.datasets["eval"].revision.confidence == Confidence.DECLARED


def test_remote_and_local_peft_adapters_are_hashed(
    tmp_path: Path, hf_mock: respx.MockRouter
) -> None:
    adapter_sha = "ddd0000000000000000000000000000000000000"
    hf_mock.get("https://huggingface.co/api/models/org/adapter/revision/main").mock(
        return_value=httpx.Response(
            200,
            json={"sha": adapter_sha, "siblings": [{"rfilename": "adapter_config.json"}]},
        )
    )
    hf_mock.get(
        f"https://huggingface.co/org/adapter/resolve/{adapter_sha}/adapter_config.json"
    ).mock(return_value=httpx.Response(200, content=b'{"r": 8}'))
    local_adapter = tmp_path / "adapters/local"
    local_adapter.mkdir(parents=True)
    (local_adapter / "adapter_config.json").write_text('{"r": 4}', encoding="utf-8")

    result = resolve(
        tmp_path,
        manifest(
            models={
                "remote": {
                    "provider": "huggingface",
                    "id": "Qwen/Qwen3-32B",
                    "adapter": {"provider": "peft", "id": "org/adapter", "type": "lora"},
                },
                "local": {
                    "provider": "huggingface",
                    "id": "Qwen/Qwen3-32B",
                    "adapter": {
                        "provider": "peft",
                        "id": "adapters/local",
                        "type": "lora",
                    },
                },
            }
        ),
    )

    remote = result.models["remote"].adapter
    local = result.models["local"].adapter
    assert remote is not None and remote.revision.value == adapter_sha
    assert remote.config_sha256 is not None
    assert local is not None and local.revision.source == "filesystem"
    assert local.config_sha256 is not None
