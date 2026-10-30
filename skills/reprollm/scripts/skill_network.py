"""Bounded network observations without changing native transport policy."""

from __future__ import annotations

import contextlib
import ssl
from collections.abc import Callable, Iterator
from typing import Any

import httpx

MAX_OBSERVATIONS = 64


class NetworkClientError(ValueError):
    """Client setup failed before native resolution; exception text stays private."""


def failure_category(error: BaseException) -> str:
    if isinstance(error, ImportError):
        return "dependency_unavailable"
    if isinstance(error, httpx.ProxyError):
        return "proxy_error"
    if isinstance(error, httpx.TimeoutException):
        return "timeout"
    seen: set[int] = set()
    pending: list[BaseException] = [error]
    for _ in range(8):
        if not pending:
            break
        current = pending.pop(0)
        if id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, ssl.SSLError):
            return "tls_error"
        pending.extend(
            nested
            for nested in (current.__cause__, current.__context__)
            if nested is not None and id(nested) not in seen
        )
    if isinstance(error, httpx.ConnectError):
        return "connection_error"
    if isinstance(error, httpx.HTTPError):
        return "request_error"
    return "configuration_error"


def _observe(diagnostics: list[dict[str, Any]], category: str, status: int | None = None) -> None:
    if len(diagnostics) >= MAX_OBSERVATIONS:
        if len(diagnostics) == MAX_OBSERVATIONS:
            diagnostics.append({"code": "network_observation_limit", "limit": MAX_OBSERVATIONS})
        return
    event: dict[str, Any] = {"code": "network_attempt", "category": category}
    if status is not None:
        event["status_code"] = status
    diagnostics.append(event)


@contextlib.contextmanager
def client_context(
    diagnostics: list[dict[str, Any]], *, before_send: Callable[[], None] | None = None
) -> Iterator[httpx.Client]:
    """Observe public send calls; retain default proxies, TLS and native retries.

    One send can follow redirects. These events describe client attempts and
    observed final responses, never an exact wire-request or billing count.
    """

    class ObservedClient(httpx.Client):
        def send(self, *args: Any, **kwargs: Any) -> httpx.Response:
            if before_send is not None:
                before_send()
            try:
                response = super().send(*args, **kwargs)
            except httpx.HTTPError as error:
                _observe(diagnostics, failure_category(error))
                raise
            status = response.status_code
            category = (
                "access_denied"
                if status in {401, 403}
                else "not_found"
                if status == 404
                else "server_error"
                if status >= 500
                else "http_error"
                if status >= 400
                else "response"
            )
            _observe(diagnostics, category, status)
            if before_send is not None:
                before_send()
            return response

    try:
        http = ObservedClient()
    except (ImportError, OSError, ValueError, httpx.HTTPError) as error:
        diagnostics.append({"code": "network_client", "category": failure_category(error)})
        raise NetworkClientError("network_client_unavailable") from None
    with contextlib.closing(http):
        yield http
