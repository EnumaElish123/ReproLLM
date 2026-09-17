"""Small Hugging Face Hub HTTP client used by lock resolution (spec §4.3).

The client deliberately depends only on ``httpx``.  It exposes the narrow Hub
surface ReproLLM needs and never includes authentication material in errors.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import quote

import httpx

DEFAULT_ENDPOINT = "https://huggingface.co"
DEFAULT_MAX_BYTES = 2 * 1024 * 1024
REQUEST_TIMEOUT_SECONDS = 10.0
_RETRY_DELAYS = (0.5, 1.5)


@dataclass(frozen=True)
class RepoInfo:
    """The stable subset of a Hub repository response used by resolvers."""

    sha: str
    siblings: list[str]


class HfError(Exception):
    """Base class for sanitized Hub failures with a provenance source."""

    source = "network_error"


class HfForbidden(HfError):
    source = "hf_api_forbidden"


class HfNotFound(HfError):
    source = "hf_api_not_found"


class HfNetworkError(HfError):
    source = "network_error"


class FileTooLarge(HfError):
    source = "hf_file_too_large"


class HfClient:
    """Resolve Hub revisions and fetch bounded metadata files."""

    def __init__(self, http: httpx.Client, token: str | None) -> None:
        self._http = http
        self.base_url = (os.getenv("HF_ENDPOINT") or DEFAULT_ENDPOINT).rstrip("/")
        candidate = token or os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
        self._token = candidate.strip() if candidate and candidate.strip() else None

    def model_info(self, repo_id: str, revision: str = "main") -> RepoInfo:
        url = self._repo_info_url("models", repo_id, revision)
        return self._repo_info(url)

    def dataset_info(self, repo_id: str, revision: str = "main") -> RepoInfo:
        url = self._repo_info_url("datasets", repo_id, revision)
        return self._repo_info(url)

    def fetch_file(
        self,
        kind: Literal["model", "dataset"],
        repo_id: str,
        sha: str,
        filename: str,
        max_bytes: int = DEFAULT_MAX_BYTES,
    ) -> bytes:
        """Fetch one small repository file, rejecting bodies over ``max_bytes``."""
        if max_bytes < 0:
            raise ValueError("max_bytes must be non-negative")
        prefix = "datasets/" if kind == "dataset" else ""
        if kind not in {"model", "dataset"}:
            raise ValueError(f"unsupported Hugging Face repository kind: {kind}")
        repo_path = _quote_repo_id(repo_id)
        revision_path = quote(sha, safe="")
        filename_path = quote(filename, safe="/")
        response = self._request(
            f"{self.base_url}/{prefix}{repo_path}/resolve/{revision_path}/{filename_path}"
        )
        length = response.headers.get("content-length")
        if length is not None:
            try:
                if int(length) > max_bytes:
                    raise FileTooLarge(f"Hugging Face file exceeds {max_bytes} bytes")
            except ValueError:
                pass
        content = response.content
        if len(content) > max_bytes:
            raise FileTooLarge(f"Hugging Face file exceeds {max_bytes} bytes")
        return content

    def _repo_info_url(self, kind: str, repo_id: str, revision: str) -> str:
        return (
            f"{self.base_url}/api/{kind}/{_quote_repo_id(repo_id)}"
            f"/revision/{quote(revision, safe='')}"
        )

    def _repo_info(self, url: str) -> RepoInfo:
        response = self._request(url)
        try:
            payload: Any = response.json()
            sha = payload["sha"]
            siblings = payload.get("siblings", [])
            if not isinstance(sha, str) or not isinstance(siblings, list):
                raise TypeError
            names = [item["rfilename"] for item in siblings if isinstance(item, dict)]
            if not all(isinstance(name, str) for name in names):
                raise TypeError
        except (ValueError, KeyError, TypeError) as exc:
            raise HfNetworkError("invalid response from Hugging Face Hub") from exc
        return RepoInfo(sha=sha, siblings=sorted(names))

    def _request(self, url: str) -> httpx.Response:
        headers = {"Authorization": f"Bearer {self._token}"} if self._token else {}
        for attempt in range(len(_RETRY_DELAYS) + 1):
            try:
                response = self._http.get(
                    url,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT_SECONDS,
                    follow_redirects=True,
                )
            except httpx.RequestError as exc:
                if attempt < len(_RETRY_DELAYS):
                    time.sleep(_RETRY_DELAYS[attempt])
                    continue
                raise HfNetworkError("Hugging Face request failed after retries") from exc

            if response.status_code >= 500 and attempt < len(_RETRY_DELAYS):
                response.close()
                time.sleep(_RETRY_DELAYS[attempt])
                continue
            if response.status_code in {401, 403}:
                raise HfForbidden("Hugging Face repository access was denied")
            if response.status_code == 404:
                raise HfNotFound("Hugging Face repository or file was not found")
            if response.status_code >= 400:
                raise HfNetworkError(
                    f"Hugging Face request failed with status {response.status_code}"
                )
            return response
        raise AssertionError("retry loop exhausted")  # pragma: no cover


def _quote_repo_id(repo_id: str) -> str:
    return "/".join(quote(part, safe="") for part in repo_id.split("/"))
