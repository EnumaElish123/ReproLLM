"""Dependency-free request validation and capability routing for the Agent Skill."""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, TypeAlias

JSONValue: TypeAlias = str | int | float | bool | None | list["JSONValue"] | dict[str, "JSONValue"]
Invocation: TypeAlias = Literal["handled_result", "user_error", "internal_error", "blocked"]
MAX_REQUEST_BYTES = 256 * 1024
MAX_REPLY_BYTES = 256 * 1024
BASE_ACTIONS = frozenset({"about", "tool.status"})


class RequestError(ValueError):
    """A fixed public diagnostic, without values copied from an invalid request."""


@dataclass(frozen=True)
class Option:
    kind: str
    choices: tuple[str, ...] = ()
    required: bool = False
    nullable: bool = False
    minimum: int | None = None


@dataclass(frozen=True)
class ActionSpec:
    purpose: str
    options: Mapping[str, Option]


BOOL = Option("bool")
TEXT = Option("str")
PATH = Option("path")
STRINGS = Option("strings")
COMMON = {"no_color": BOOL, "verbose": BOOL, "quiet": BOOL}
RUN_OPTIONS = {
    "argv": STRINGS,
    "cwd": PATH,
    "name": TEXT,
    "capture_output": Option("bool", nullable=True),
    "env_capture": Option("str", ("allowlist", "all")),
    "no_snapshot": BOOL,
}
DRIFT = ("NONE", "LOW", "MEDIUM", "MEDIUM_HIGH", "HIGH")


def _action(purpose: str, **options: Option) -> ActionSpec:
    return ActionSpec(purpose, {**COMMON, **options})


ACTION_SPECS: dict[str, ActionSpec] = {
    "about": ActionSpec("Explain capabilities and relevant natural-language examples.", {}),
    "tool.status": ActionSpec("Inspect the verified tool installation without installing it.", {}),
    "audit": _action(
        "Check reproducibility declarations and evidence with deterministic rules.",
        format=Option("str", ("text", "json", "github")),
        output=PATH,
        fail_on=Option("str", ("critical", "warning", "never")),
        level=Option("str", ("auto", "0", "1", "2")),
        profiles=STRINGS,
        show_passed=Option("bool", nullable=True),
        show_skipped=BOOL,
        details=BOOL,
    ),
    "doctor": _action(
        "Diagnose the tool environment and explicitly requested connectivity.",
        json=BOOL,
        check_network=BOOL,
    ),
    "profiles.list": _action("List available experiment profiles.", json=BOOL),
    "profiles.show": _action(
        "Explain one profile and its inherited requirements.", name=Option("str", required=True)
    ),
    "init.tasks": _action("List detected experiment tasks without writing a manifest."),
    "runs.list": _action(
        "List recorded experiments with explicit filters.",
        json=BOOL,
        name=TEXT,
        status=Option("str", ("running", "completed", "failed", "interrupted")),
        outcome=Option("str", ("success", "failure")),
        limit=Option("int", minimum=1),
    ),
    "runs.show": _action(
        "Inspect a recorded experiment and its evidence scope.",
        run_id=Option("str", required=True),
        json=BOOL,
    ),
    "diff": _action(
        "Compare explicit records or the two most recent successful experiments.",
        a=TEXT,
        b=TEXT,
        latest_successful=BOOL,
        name=TEXT,
        format=Option("str", ("text", "json")),
        min_severity=Option("str", DRIFT[1:]),
        fail_on=Option("str", DRIFT),
    ),
    "run.preview": _action(
        "Preview a saved or explicit experiment command without executing it.", **RUN_OPTIONS
    ),
    "init": _action(
        "Create a manifest, select tasks and register an explicitly provided command.",
        force=BOOL,
        profiles=STRINGS,
        command=TEXT,
        tasks=STRINGS,
        answers=Option("string_map"),
    ),
    "lock": _action(
        "Resolve or check artifact identities; this does not install experiment packages.",
        offline=BOOL,
        check=BOOL,
        verify_api=BOOL,
        hash_large_files=BOOL,
    ),
    "export": _action(
        "Export current or historical evidence as a reproducibility report.",
        run=TEXT,
        output=PATH,
        template=Option("str", ("default", "neurips", "acl", "acm")),
    ),
    "schema.export": _action("Export the product's ten JSON Schema documents.", out=PATH),
    "discover.preview": _action(
        "Preview the exact eligible source content without an API request.",
        experimental=BOOL,
        show_content=BOOL,
        max_chars=Option("int", minimum=1),
    ),
    "discover": _action(
        "Request opt-in discovery under a specific content and budget approval.",
        experimental=BOOL,
        max_chars=Option("int", minimum=1),
    ),
    "rules.list": _action(
        "Inspect active rules or the latest discovery candidates.", json=BOOL, candidates=BOOL
    ),
    "rules.candidates": _action(
        "Inspect complete latest candidates and their acceptance state.", json=BOOL
    ),
    "rules.show": _action(
        "Inspect a rule, candidate or immutable recovery archive.", id=Option("str", required=True)
    ),
    "rules.add": _action(
        "Add an explicitly specified project rule.",
        field=Option("str", required=True),
        severity=Option("str", ("CRITICAL", "WARNING", "INFO"), required=True),
        reason=Option("str", required=True),
        id=TEXT,
        cli=TEXT,
        config=TEXT,
        env=TEXT,
    ),
    "rules.accept": _action(
        "Accept the specific candidate the user reviewed.",
        candidate_id=Option("str", required=True),
        severity=Option("str", ("CRITICAL", "WARNING", "INFO")),
        field=TEXT,
    ),
    "rules.ignore": _action(
        "Ignore a reviewed, inactive candidate.",
        candidate_id=Option("str", required=True),
        reason=TEXT,
    ),
    "rules.remove": _action(
        "Archive and remove an explicitly selected active rule.",
        rule_id=Option("str", required=True),
        reason=Option("str", required=True),
    ),
    "rules.restore": _action(
        "Restore a specific immutable rule recovery archive.",
        archive_id=Option("str", required=True),
    ),
    "run.start": _action(
        "Execute the user-authorized experiment in its selected environment.", **RUN_OPTIONS
    ),
    "run.status": _action(
        "Inspect the state of an owned operation.", operation_id=Option("str", required=True)
    ),
    "run.logs": _action(
        "Read available redacted capture logs of an owned operation.",
        operation_id=Option("str", required=True),
        stream=Option("str", ("stdout", "stderr")),
    ),
    "run.cancel": _action(
        "Cancel only the specifically authorized owned operation.",
        operation_id=Option("str", required=True),
    ),
    "run.result": _action(
        "Read an owned operation's recorded result without restarting it.",
        operation_id=Option("str", required=True),
    ),
}


@dataclass(frozen=True)
class Grants:
    install: bool = True
    write: bool = False
    network: bool = False
    run: bool = False
    external_paths: tuple[str, ...] = ()
    expected_hashes: dict[str, str | None] = field(default_factory=dict)


@dataclass(frozen=True)
class ResponseOptions:
    page_size: int = 100
    cursor: str | None = None


@dataclass(frozen=True)
class Request:
    action: str
    project: str | None = None
    options: dict[str, Any] = field(default_factory=dict)
    grants: Grants = field(default_factory=Grants)
    response: ResponseOptions = field(default_factory=ResponseOptions)
    schema_version: int = 1


@dataclass
class Reply:
    action: str | None
    invocation: Invocation = "handled_result"
    cli_exit_code: int | None = None
    gate_failed: bool | None = None
    child_exit_code: int | None = None
    complete: bool = True
    data: Any = None
    diagnostics: list[Any] = field(default_factory=list)
    next_cursor: str | None = None
    snapshot: str | None = None
    needs_input: bool = False
    needs_authorization: bool = False
    questions: list[str] = field(default_factory=list)
    schema_version: int = 1

    def as_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}


Executor: TypeAlias = Callable[[Request], Reply]
StatusProvider: TypeAlias = Callable[[], JSONValue]


def _mapping(value: Any, allowed: set[str], code: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise RequestError(code)
    if not set(value).issubset(allowed):
        raise RequestError(code)
    return value


def _safe_path(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not value
        or any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in value)
    ):
        raise RequestError("invalid_path")
    return value


def _option(value: Any, spec: Option) -> bool:
    if value is None and spec.nullable:
        return True
    if spec.kind == "bool":
        return type(value) is bool
    if spec.kind in {"str", "path"}:
        if not isinstance(value, str) or "\x00" in value:
            return False
        if spec.kind == "path":
            _safe_path(value)
        return not spec.choices or value in spec.choices
    if spec.kind == "int":
        return type(value) is int and (spec.minimum is None or value >= spec.minimum)
    if spec.kind == "strings":
        return isinstance(value, list) and all(
            isinstance(s, str) and "\x00" not in s for s in value
        )
    if spec.kind == "string_map":
        return isinstance(value, dict) and all(
            isinstance(k, str) and isinstance(v, str) and "\x00" not in k + v
            for k, v in value.items()
        )
    return False


def _finite(value: Any, depth: int = 0) -> None:
    if depth > 64:
        raise RequestError("request_nesting_limit")
    if isinstance(value, float) and not math.isfinite(value):
        raise RequestError("nonfinite_json")
    if isinstance(value, (list, dict)):
        for child in value.values() if isinstance(value, dict) else value:
            _finite(child, depth + 1)


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RequestError("duplicate_json_key")
        result[key] = value
    return result


def _constant(value: str) -> None:
    raise RequestError("nonfinite_json")


def parse_request(value: bytes | dict[str, Any]) -> Request:
    try:
        if isinstance(value, bytes):
            if len(value) > MAX_REQUEST_BYTES:
                raise RequestError("request_size_limit")
            value = json.loads(value, object_pairs_hook=_unique, parse_constant=_constant)
        _finite(value)
        data = _mapping(
            value,
            {"schema_version", "action", "project", "options", "grants", "response"},
            "invalid_request_fields",
        )
        if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
            raise RequestError("unsupported_schema_version")
        action = data.get("action")
        if not isinstance(action, str) or action not in ACTION_SPECS:
            raise RequestError("unknown_action")
        project = None if data.get("project") is None else _safe_path(data["project"])
        spec = ACTION_SPECS[action]
        options = _mapping(data.get("options", {}), set(spec.options), "unknown_option")
        for name, option_spec in spec.options.items():
            if name not in options:
                if option_spec.required:
                    raise RequestError("required_option_missing")
            elif not _option(options[name], option_spec):
                raise RequestError("invalid_option_type_or_value")
        grant_data = _mapping(
            data.get("grants", {}),
            {"install", "write", "network", "run", "external_paths", "expected_hashes"},
            "invalid_grants",
        )
        for name in ("install", "write", "network", "run"):
            if name in grant_data and type(grant_data[name]) is not bool:
                raise RequestError("invalid_grants")
        external = grant_data.get("external_paths", [])
        if not isinstance(external, list):
            raise RequestError("invalid_grants")
        external_paths = tuple(_safe_path(path) for path in external)
        hashes = grant_data.get("expected_hashes", {})
        if not isinstance(hashes, dict):
            raise RequestError("invalid_grants")
        for path, digest in hashes.items():
            _safe_path(path)
            if digest is not None and (
                not isinstance(digest, str)
                or len(digest) != 64
                or any(c not in "0123456789abcdef" for c in digest)
            ):
                raise RequestError("invalid_expected_hash")
        grants = Grants(
            **{
                name: grant_data[name]
                for name in ("install", "write", "network", "run")
                if name in grant_data
            },
            external_paths=external_paths,
            expected_hashes=dict(hashes),
        )
        page = _mapping(
            data.get("response", {}), {"page_size", "cursor"}, "invalid_response_options"
        )
        size, cursor = page.get("page_size", 100), page.get("cursor")
        if type(size) is not int or not 1 <= size <= 1000:
            raise RequestError("invalid_response_options")
        if cursor is not None and (
            not isinstance(cursor, str)
            or not cursor
            or len(cursor) > 4096
            or any(ord(c) < 32 or ord(c) == 127 for c in cursor)
        ):
            raise RequestError("invalid_response_options")
        return Request(action, project, dict(options), grants, ResponseOptions(size, cursor))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise RequestError("invalid_json_request") from error


def capabilities(available_actions: frozenset[str] = BASE_ACTIONS) -> dict[str, Any]:
    return {
        "principle": "LLM discovers. Rules decide. Runtime verifies.",
        "purpose": "Record LLM experiment identity and explain reproducibility gaps and drift.",
        "actions": [
            {"action": name, "purpose": spec.purpose, "available": name in available_actions}
            for name, spec in sorted(ACTION_SPECS.items())
        ],
        "examples": [
            "Check this repository for reproducibility gaps.",
            "Record this experiment command and export its report.",
            "Compare my two most recent successful experiments.",
        ],
        "limits": [
            "Unknown research facts stay unknown; audit success does not prove paper reproduction.",
            "Tool installation does not install models or prepare a training environment.",
            "Paper prose analysis is not supported by the current CLI.",
            "An available product command may still require resources or a later Skill adapter.",
        ],
    }


def blocked(
    action: str | None,
    code: str,
    *,
    needs_input: bool = False,
    needs_authorization: bool = False,
    questions: list[str] | None = None,
) -> Reply:
    return Reply(
        action,
        invocation="blocked",
        complete=False,
        diagnostics=[{"code": code}],
        needs_input=needs_input,
        needs_authorization=needs_authorization,
        questions=questions or [],
    )


def required_grants(request: Request) -> frozenset[str]:
    action, options = request.action, request.options
    grants: set[str] = set()
    if action in {
        "init",
        "export",
        "schema.export",
        "rules.add",
        "rules.accept",
        "rules.ignore",
        "rules.remove",
        "rules.restore",
        "discover",
        "run.start",
    }:
        grants.add("write")
    if action in {"run.start", "run.cancel"}:
        grants.add("run")
    if action == "lock" and not options.get("check", False):
        grants.add("write")
        if not options.get("offline", False):
            grants.add("network")
    if action == "discover" or action == "doctor" and options.get("check_network", False):
        grants.add("network")
    if action == "audit" and "output" in options:
        grants.add("write")
    return frozenset(grants)


def dispatch(
    request: Request,
    *,
    executor: Executor | None = None,
    status_provider: StatusProvider | None = None,
    available_actions: frozenset[str] = BASE_ACTIONS,
) -> Reply:
    if request.action == "about":
        return Reply("about", data=capabilities(available_actions))
    if request.action == "tool.status":
        if status_provider is None:
            return blocked(request.action, "status_provider_unavailable")
        return Reply(request.action, data=status_provider())
    if request.project is None:
        return blocked(
            request.action,
            "project_required",
            needs_input=True,
            questions=["Which project directory should this task use?"],
        )
    if executor is None:
        return blocked(request.action, "action_unavailable")
    missing = sorted(name for name in required_grants(request) if not getattr(request.grants, name))
    if missing:
        return blocked(
            request.action,
            "authorization_required",
            needs_authorization=True,
            questions=["Confirm the requested operation's " + ", ".join(missing) + " scope."],
        )
    return executor(request)


def error_reply(error: RequestError) -> Reply:
    return Reply(None, invocation="user_error", complete=False, diagnostics=[{"code": str(error)}])


def _compact_failure(reply: Reply, code: str, *, internal: bool = False) -> Reply:
    action = (
        reply.action if isinstance(reply.action, str) and reply.action in ACTION_SPECS else None
    )
    invocation: Invocation = (
        "internal_error"
        if internal
        else reply.invocation
        if reply.invocation in {"internal_error", "user_error"}
        else "blocked"
    )
    diagnostics: list[dict[str, Any]] = [{"code": code, "data_omitted": True}]
    retained: dict[str, dict[str, Any]] = {}
    original = reply.diagnostics if isinstance(reply.diagnostics, list) else []
    for diagnostic in reversed(original):
        if not isinstance(diagnostic, dict):
            continue
        diagnostic_code = diagnostic.get("code")
        if diagnostic_code == "runtime_lease_cleanup_failed":
            retained[diagnostic_code] = {"code": diagnostic_code}
        if (
            isinstance(diagnostic_code, str)
            and diagnostic_code in {"runtime_worker_exit", "runtime_worker_stderr"}
            and diagnostic_code not in retained
            and type(diagnostic.get("worker_exit_code")) is int
        ):
            retained[diagnostic_code] = {
                "code": diagnostic_code,
                "worker_exit_code": diagnostic["worker_exit_code"],
            }
    diagnostics.extend(retained[key] for key in sorted(retained))
    if len(original) > len(retained):
        diagnostics[0]["diagnostics_omitted"] = len(original) - len(retained)
    if action is None and invocation == "blocked":
        invocation = "internal_error"
    compact = Reply(action, invocation=invocation, complete=False, diagnostics=diagnostics)
    if action is not None:
        compact.cli_exit_code = reply.cli_exit_code if type(reply.cli_exit_code) is int else None
        compact.child_exit_code = (
            reply.child_exit_code if type(reply.child_exit_code) is int else None
        )
        compact.gate_failed = reply.gate_failed if type(reply.gate_failed) is bool else None
    return compact


def encode_reply(reply: Reply) -> bytes:
    try:
        raw = json.dumps(
            reply.as_dict(),
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError):
        reply = _compact_failure(reply, "invalid_executor_reply", internal=True)
        raw = json.dumps(reply.as_dict(), sort_keys=True).encode("utf-8")
    if len(raw) > MAX_REPLY_BYTES - 1:
        return encode_reply(_compact_failure(reply, "reply_budget_exceeded"))
    return raw
