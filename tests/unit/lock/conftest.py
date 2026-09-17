from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
import respx


@pytest.fixture
def hf_mock() -> Iterator[respx.MockRouter]:
    fixtures = Path(__file__).parents[2] / "fixtures" / "hf_api"
    router = respx.MockRouter(assert_all_called=False, assert_all_mocked=True)

    def json_response(relative: str, status_code: int = 200) -> httpx.Response:
        payload = json.loads((fixtures / relative).read_text(encoding="utf-8"))
        return httpx.Response(status_code, json=payload)

    router.get("https://huggingface.co/api/models/Qwen/Qwen3-32B/revision/main").mock(
        return_value=json_response("models/Qwen__Qwen3-32B/revision_main.json")
    )
    router.get(
        "https://huggingface.co/Qwen/Qwen3-32B/resolve/"
        "8fa23e7c1a0000000000000000000000000000aa/tokenizer_config.json"
    ).mock(
        return_value=httpx.Response(
            200,
            content=(fixtures / "files/Qwen__Qwen3-32B/tokenizer_config.json").read_bytes(),
        )
    )
    router.get(
        "https://huggingface.co/Qwen/Qwen3-32B/resolve/"
        "8fa23e7c1a0000000000000000000000000000aa/config.json"
    ).mock(
        return_value=httpx.Response(
            200,
            content=(fixtures / "files/Qwen__Qwen3-32B/config.json").read_bytes(),
        )
    )
    router.get("https://huggingface.co/api/datasets/cais/mmlu/revision/main").mock(
        return_value=json_response("datasets/cais__mmlu/revision_main.json")
    )
    router.get(
        "https://huggingface.co/api/models/meta-llama/Llama-3.1-8B-Instruct/revision/main"
    ).mock(
        return_value=json_response(
            "models/meta-llama__Llama-3.1-8B-Instruct/revision_main.403.json", 403
        )
    )
    router.get("https://huggingface.co/api/models/gpt2/revision/main").mock(
        return_value=json_response("models/gpt2/revision_main.json")
    )

    with router:
        yield router
