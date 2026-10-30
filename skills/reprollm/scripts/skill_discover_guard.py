"""A bounded send boundary for the original discovery client; no request retry loop."""

from __future__ import annotations

import contextlib
import dataclasses
import hashlib
import json
import math
import re
import signal
import sys
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeGuard
from urllib.parse import urlsplit

import httpx
from skill_operations import _atomic, _lock, _private, _read

MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_CONTINUATION_BYTES = 32 * 1024
MAX_BUDGET_RECORDS = 256
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_PUBLIC_MODEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}\Z")
_OWNER = "reprollm-skill-discovery-budget"


class BudgetError(ValueError):
    """A fixed diagnostic; provider content and credentials never enter it."""


class DiscoverDeadline(BaseException):
    """Interrupt one owned worker without entering the native retry branch."""


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def identity(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _integer(value: Any, minimum: int, maximum: int) -> TypeGuard[int]:
    return type(value) is int and minimum <= value <= maximum


def _expiry(value: Any) -> bool:
    return type(value) in {int, float} and math.isfinite(value) and value > 0


def _credential_content(value: Any, secret: str, depth: int = 0) -> bool:
    if depth > 64:
        return True
    if isinstance(value, str):
        if secret in value:
            return True
        if depth == 0:
            try:
                return _credential_content(json.loads(value), secret, 1)
            except RecursionError:
                return True
            except ValueError:
                return False
        return False
    if isinstance(value, list):
        return any(_credential_content(item, secret, depth + 1) for item in value)
    if isinstance(value, dict):
        return any(
            _credential_content(item, secret, depth + 1) for pair in value.items() for item in pair
        )
    return False


@dataclass(frozen=True)
class PricePolicy:
    """User-reviewed provider facts, bound verbatim into the spending grant."""

    endpoint: str
    model: str
    served_models: tuple[str, ...]
    input_tokens: int
    output_tokens: int
    miss_nano: int
    hit_nano: int
    output_nano: int
    output_basis: str
    evidence_sha256: str
    expires_at: float

    def validate(self) -> None:
        url = urlsplit(self.endpoint)
        if (
            url.scheme not in {"http", "https"}
            or not url.hostname
            or url.username is not None
            or url.password is not None
            or url.query
            or url.fragment
            or not url.path.endswith("/chat/completions")
            or not _PUBLIC_MODEL.fullmatch(self.model)
            or not self.served_models
            or any(not _PUBLIC_MODEL.fullmatch(item) for item in self.served_models)
            or len(self.served_models) > 8
            or not _integer(self.input_tokens, 1, 16 * 1024 * 1024)
            or not _integer(self.output_tokens, 1, 1024 * 1024)
            or any(
                not _integer(item, 0, 10**12)
                for item in (self.miss_nano, self.hit_nano, self.output_nano)
            )
            or self.hit_nano > self.miss_nano
            or self.output_basis not in {"native-default", "published-maximum"}
            or not _HASH.fullmatch(self.evidence_sha256)
            or not _expiry(self.expires_at)
        ):
            raise BudgetError("discover_price_policy_invalid")

    @property
    def fingerprint(self) -> str:
        return identity(dataclasses.asdict(self))

    @property
    def reserve_nano(self) -> int:
        return self.input_tokens * self.miss_nano + self.output_tokens * self.output_nano


@dataclass(frozen=True)
class Approval:
    approval_id: str
    helper_sha256: str
    source_sha256: str
    messages_sha256: str
    policy_sha256: str
    budget_nano: int
    max_attempts: int
    expires_at: float

    def validate(self) -> None:
        if (
            re.fullmatch(r"[0-9a-f]{32}", self.approval_id) is None
            or any(
                not _HASH.fullmatch(value)
                for value in (
                    self.helper_sha256,
                    self.source_sha256,
                    self.messages_sha256,
                    self.policy_sha256,
                )
            )
            or not _integer(self.budget_nano, 0, 10**18)
            or not _integer(self.max_attempts, 1, 3)
            or not _expiry(self.expires_at)
        ):
            raise BudgetError("discover_approval_invalid")

    @property
    def fingerprint(self) -> str:
        return identity(dataclasses.asdict(self))


def _budget_coverage(policy: PricePolicy, approval: Approval) -> None:
    if approval.budget_nano < approval.max_attempts * policy.reserve_nano:
        raise BudgetError("discover_budget_insufficient_for_attempt_limit")


def parse_grant(value: Any) -> tuple[PricePolicy, Approval]:
    """Parse an authorization supplied by the host, never by repository content."""
    try:
        if (
            not isinstance(value, dict)
            or set(value) != {"schema_version", "currency", "policy", "approval"}
            or type(value["schema_version"]) is not int
            or value["schema_version"] != 1
            or value["currency"] != "CNY"
            or not isinstance(value["policy"], dict)
            or set(value["policy"]) != set(PricePolicy.__dataclass_fields__)
            or not isinstance(value["approval"], dict)
            or set(value["approval"]) != set(Approval.__dataclass_fields__)
            or not isinstance(value["policy"]["served_models"], list)
        ):
            raise BudgetError("discover_approval_invalid")
        fields = dict(value["policy"])
        fields["served_models"] = tuple(fields["served_models"])
        policy = PricePolicy(**fields)
        approval = Approval(**value["approval"])
        policy.validate()
        approval.validate()
        if (
            approval.policy_sha256 != policy.fingerprint
            or approval.expires_at > policy.expires_at
            or approval.expires_at > time.time() + 24 * 3600
        ):
            raise BudgetError("discover_approval_binding_changed")
        _budget_coverage(policy, approval)
        return policy, approval
    except (TypeError, KeyError, AttributeError, OverflowError):
        raise BudgetError("discover_approval_invalid") from None


class Ledger:
    """Reserve before send; submitted/uncertain costs survive worker interruption."""

    def __init__(self, path: Path, approval: Approval, operation_id: str) -> None:
        approval.validate()
        if re.fullmatch(r"[0-9a-f]{32}", operation_id) is None:
            raise BudgetError("discover_operation_identity_invalid")
        _private(path.parent, directory=True)
        self.path = path
        self.approval = approval
        self.operation_sha256 = identity(operation_id)

    def _load(self) -> dict[str, Any]:
        if not self.path.exists() and not self.path.is_symlink():
            return {
                "schema_version": 1,
                "owner": _OWNER,
                "approval_sha256": self.approval.fingerprint,
                "operation_sha256": self.operation_sha256,
                "attempts": [],
            }
        record = _read(self.path)
        if (
            set(record)
            != {"schema_version", "owner", "approval_sha256", "operation_sha256", "attempts"}
            or record["owner"] != _OWNER
            or record["approval_sha256"] != self.approval.fingerprint
            or record["operation_sha256"] != self.operation_sha256
            or not isinstance(record["attempts"], list)
            or len(record["attempts"]) > 3
        ):
            raise BudgetError("discover_budget_state_invalid")
        for item in record["attempts"]:
            if (
                not isinstance(item, dict)
                or not _integer(item.get("held_nano"), 0, self.approval.budget_nano)
                or item.get("outcome") not in {"unknown", "response"}
                or type(item.get("usage_verified")) is not bool
            ):
                raise BudgetError("discover_budget_state_invalid")
        return record

    def _save(self, record: dict[str, Any]) -> None:
        new = not self.path.exists()
        if new and len(list(self.path.parent.glob("*.json"))) >= MAX_BUDGET_RECORDS:
            raise BudgetError("discover_budget_store_limit")
        _atomic(self.path, canonical(record), exclusive=new)

    def claim(self) -> None:
        with _lock(self.path.parent / "budget.lock"):
            record = self._load()
            if not self.path.exists():
                self._save(record)

    def reserve(self, reserve: int, expected_previous: int) -> int:
        with _lock(self.path.parent / "budget.lock"):
            record = self._load()
            entries = record["attempts"]
            if len(entries) != expected_previous:
                raise BudgetError("discover_already_submitted")
            if len(entries) >= self.approval.max_attempts:
                raise BudgetError("discover_attempt_limit")
            if sum(item["held_nano"] for item in entries) + reserve > self.approval.budget_nano:
                raise BudgetError("discover_budget_exhausted")
            entries.append({"held_nano": reserve, "outcome": "unknown", "usage_verified": False})
            self._save(record)
            return len(entries) - 1

    def finish(self, index: int, observation: dict[str, Any]) -> None:
        with _lock(self.path.parent / "budget.lock"):
            record = self._load()
            item = record["attempts"][index]
            if item["outcome"] != "unknown":
                raise BudgetError("discover_budget_state_invalid")
            item.update(observation, outcome="response")
            self._save(record)

    def summary(self) -> dict[str, Any]:
        with _lock(self.path.parent / "budget.lock"):
            record = self._load()
        attempts = record["attempts"]
        return {
            "currency": "CNY",
            "attempt_count": len(attempts),
            "attempt_count_basis": "reserved_or_submitted",
            "confirmed_response_count": sum(item["outcome"] == "response" for item in attempts),
            "held_nano": sum(item["held_nano"] for item in attempts),
            "charge_uncertain": any(not item["usage_verified"] for item in attempts),
            "cost_is_estimate": True,
            "attempts": attempts,
        }


@contextlib.contextmanager
def _deadline(seconds: float) -> Iterator[None]:
    if sys.platform == "win32":
        raise BudgetError("discover_deadline_platform_unavailable")
    if (
        not hasattr(signal, "setitimer")
        or threading.current_thread() is not threading.main_thread()
        or signal.getitimer(signal.ITIMER_REAL)[0] != 0
    ):
        raise BudgetError("discover_deadline_platform_unavailable")

    def expired(number: int, frame: Any) -> None:
        raise DiscoverDeadline

    previous = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def _usage(document: Any, policy: PricePolicy) -> tuple[int | None, dict[str, int] | None]:
    usage = document.get("usage") if isinstance(document, dict) else None
    if not isinstance(usage, dict):
        return None, None
    prompt, completion, total = (
        usage.get(key) for key in ("prompt_tokens", "completion_tokens", "total_tokens")
    )
    if (
        not _integer(prompt, 0, policy.input_tokens)
        or not _integer(completion, 0, policy.output_tokens)
        or not _integer(total, 0, policy.input_tokens + policy.output_tokens)
        or total != prompt + completion
    ):
        return None, None
    hit = usage.get("prompt_cache_hit_tokens", 0)
    miss = usage.get("prompt_cache_miss_tokens", prompt - hit if type(hit) is int else -1)
    if not _integer(hit, 0, prompt) or not _integer(miss, 0, prompt) or hit + miss != prompt:
        return None, None
    prompt_details = usage.get("prompt_tokens_details")
    if prompt_details is not None and (
        not isinstance(prompt_details, dict)
        or not _integer(prompt_details.get("cached_tokens"), 0, prompt)
        or prompt_details["cached_tokens"] != hit
    ):
        return None, None
    completion_details = usage.get("completion_tokens_details")
    if completion_details is not None and (
        not isinstance(completion_details, dict)
        or not _integer(completion_details.get("reasoning_tokens"), 0, completion)
    ):
        return None, None
    return (
        hit * policy.hit_nano + miss * policy.miss_nano + completion * policy.output_nano,
        {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "cache_hit_tokens": hit,
            "cache_miss_tokens": miss,
        },
    )


class GuardedClient(httpx.Client):
    """Observe public send while retaining HTTPX's ordinary proxy and TLS setup."""

    def __init__(
        self,
        *,
        policy: PricePolicy,
        approval: Approval,
        messages: list[dict[str, str]],
        api_key: str,
        ledger: Ledger,
        check_current: Callable[[], None],
    ) -> None:
        policy.validate()
        approval.validate()
        self.policy, self.approval, self.ledger = policy, approval, ledger
        self.messages = json.loads(canonical(messages))
        self.api_key, self.check_current = api_key, check_current
        self.submitted = 0
        self.started = time.monotonic()
        self._allowed_continuation: str | None = None
        self._allow_mode_fallback = False
        self._last_mode = True
        self._may_send = True
        self._invalid_responses = 0
        if (
            policy.fingerprint != approval.policy_sha256
            or identity(messages) != approval.messages_sha256
            or len(messages) != 2
            or [item.get("role") for item in messages] != ["system", "user"]
            or any(set(item) != {"role", "content"} for item in messages)
            or not api_key
            or any(api_key in item["content"] for item in messages)
        ):
            raise BudgetError("discover_approval_binding_changed")
        _budget_coverage(policy, approval)
        if time.time() >= min(policy.expires_at, approval.expires_at):
            raise BudgetError("discover_approval_expired")
        ledger.claim()
        super().__init__(
            timeout=120.0, follow_redirects=False, headers={"Accept-Encoding": "identity"}
        )

    def _verify(self, request: httpx.Request, options: dict[str, Any]) -> dict[str, Any]:
        if not self._may_send:
            raise BudgetError("discover_already_submitted")
        now = time.time()
        if now >= min(self.policy.expires_at, self.approval.expires_at):
            raise BudgetError("discover_approval_expired")
        self.check_current()
        if (
            request.method != "POST"
            or str(request.url) != self.policy.endpoint
            or request.headers.get("Authorization") != "Bearer " + self.api_key
            or options.get("follow_redirects") not in {None, False, httpx.USE_CLIENT_DEFAULT}
            or options.get("auth", httpx.USE_CLIENT_DEFAULT) not in {None, httpx.USE_CLIENT_DEFAULT}
            or self.auth is not None
        ):
            raise BudgetError("discover_wire_request_changed")
        try:
            body = json.loads(request.content)
        except (ValueError, UnicodeError):
            raise BudgetError("discover_wire_body_invalid") from None
        if (
            not isinstance(body, dict)
            or set(body)
            not in (
                {"model", "temperature", "messages", "response_format"},
                {"model", "temperature", "messages"},
            )
            or body.get("model") != self.policy.model
            or type(body.get("temperature")) is not int
            or body["temperature"] != 0
            or not isinstance(body.get("messages"), list)
            or body["messages"][:2] != self.messages
            or self.api_key in canonical(body).decode("utf-8")
        ):
            raise BudgetError("discover_wire_body_changed")
        mode = "response_format" in body
        if mode and body["response_format"] != {"type": "json_object"}:
            raise BudgetError("discover_wire_body_changed")
        if self.submitted == 0:
            if len(body["messages"]) != 2 or not mode:
                raise BudgetError("discover_initial_messages_changed")
        else:
            if mode != self._last_mode and not (self._allow_mode_fallback and not mode):
                raise BudgetError("discover_retry_changed")
            expected = list(self.messages)
            if self._allowed_continuation is not None:
                expected.append({"role": "user", "content": self._allowed_continuation})
            if body["messages"] != expected:
                raise BudgetError("discover_retry_changed")
        self._last_mode = mode
        return body

    def _observe(self, response: httpx.Response, raw: bytes) -> dict[str, Any]:
        observation: dict[str, Any] = {
            "http_status": response.status_code,
            "requested_model_sha256": identity(self.policy.model),
        }
        try:
            document = json.loads(raw)
        except (ValueError, UnicodeError):
            document = None
        self._allow_mode_fallback = bool(
            self.submitted == 1
            and self._last_mode
            and "response_format" in response.text[:200]
            and (response.status_code >= 400 or document is None)
        )
        self._may_send = self._allow_mode_fallback
        if isinstance(document, dict):
            model = document.get("model")
            if isinstance(model, str):
                observation["served_model_sha256"] = identity(model)
                observation["served_model_matches_policy"] = model in self.policy.served_models
            cost, usage = (
                _usage(document, self.policy)
                if model in self.policy.served_models and response.status_code < 400
                else (None, None)
            )
            if cost is not None:
                observation.update(held_nano=cost, usage_verified=True, usage=usage)
            if response.status_code >= 400:
                return observation
            try:
                choice = document["choices"][0]
                finish = choice.get("finish_reason")
                if finish in {"stop", "length", "content_filter", "tool_calls", "function_call"}:
                    observation["finish_reason"] = finish
                content = choice["message"]["content"]
                from reprollm.discover.client import _parse

                candidates, error = _parse(content)
                if candidates is None:
                    self._invalid_responses += 1
                    continuation = (
                        f"Your previous reply was not valid JSON for the schema: {error}. "
                        "Reply again with JSON only."
                    )
                    if (
                        len(continuation.encode("utf-8")) <= MAX_CONTINUATION_BYTES
                        and self.api_key not in continuation
                        and not _credential_content(content, self.api_key)
                        and self._invalid_responses == 1
                        and response.status_code < 400
                    ):
                        self._allowed_continuation = continuation
                        self._may_send = True
                    else:
                        self._allowed_continuation = None
            except (KeyError, TypeError, IndexError):
                pass
        return observation

    def send(self, request: httpx.Request, **kwargs: Any) -> httpx.Response:
        self._verify(request, kwargs)
        remaining = min(120.0, 400.0 - (time.monotonic() - self.started))
        if remaining <= 0:
            raise BudgetError("discover_deadline_exceeded")
        timeout = request.extensions.get("timeout", {})
        request.extensions["timeout"] = {
            key: min(value, remaining) if isinstance(value, (int, float)) else remaining
            for key, value in {
                "connect": remaining,
                "read": remaining,
                "write": remaining,
                "pool": remaining,
                **timeout,
            }.items()
        }
        # Check timer support before reserving. A crash after reserve intentionally
        # keeps the cost even if submission can no longer be established.
        with _deadline(remaining):
            self._may_send = False
            index = self.ledger.reserve(self.policy.reserve_nano, self.submitted)
            self.submitted += 1
            kwargs.update(stream=True, follow_redirects=False)
            response = super().send(request, **kwargs)
            try:
                if response.headers.get("content-encoding", "").strip().lower() not in {
                    "",
                    "identity",
                }:
                    raise BudgetError("discover_encoded_response_unknown_charge")
                raw = bytearray()
                chunks = (
                    (response.content,)
                    if response.is_stream_consumed
                    else response.iter_raw(chunk_size=65536)
                )
                for part in chunks:
                    if len(raw) + len(part) > MAX_RESPONSE_BYTES:
                        raise BudgetError("discover_response_limit_unknown_charge")
                    raw.extend(part)
                safe_response = httpx.Response(
                    response.status_code,
                    content=bytes(raw),
                    headers={"content-type": response.headers.get("content-type", "")},
                    request=request,
                )
            finally:
                response.close()
            self.ledger.finish(index, self._observe(safe_response, bytes(raw)))
            return safe_response
