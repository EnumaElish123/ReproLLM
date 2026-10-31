"""Original discovery collection/client/finalizer with owned, guarded publication."""

from __future__ import annotations

import ast
import contextlib
import getpass
import hashlib
import io
import math
import re
import socket
import textwrap
import tokenize
import unicodedata
import warnings
from collections.abc import Iterator
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any

import httpx
import skill_writes as writes
from skill_discover_guard import (
    BudgetError,
    DiscoverDeadline,
    GuardedClient,
    Ledger,
    identity,
    parse_grant,
)
from skill_request import Reply, Request, blocked

if TYPE_CHECKING:
    from reprollm.run.privacy import RunPrivacy

_WARNING_COUNT_LIMIT = 1000
_WARNING_CATEGORIES: dict[type[Warning], str] = {
    Warning: "other_warning",
    UserWarning: "user_warning",
    DeprecationWarning: "deprecation_warning",
    PendingDeprecationWarning: "pending_deprecation_warning",
    SyntaxWarning: "syntax_warning",
    RuntimeWarning: "runtime_warning",
    FutureWarning: "future_warning",
    ImportWarning: "import_warning",
    UnicodeWarning: "unicode_warning",
    BytesWarning: "bytes_warning",
    ResourceWarning: "resource_warning",
}


@dataclass
class _CollectionWarnings:
    counts: dict[str, int] = field(default_factory=dict)
    lower_bounds: set[str] = field(default_factory=set)

    @contextlib.contextmanager
    def capture(self) -> Iterator[None]:
        # Keep the caller's filters; source text and warning locations stay local.
        with warnings.catch_warnings(record=True) as observed:
            try:
                yield
            finally:
                for item in observed:
                    category = _WARNING_CATEGORIES.get(item.category, "other_warning")
                    count = self.counts.get(category, 0)
                    if count < _WARNING_COUNT_LIMIT:
                        self.counts[category] = count + 1
                    else:
                        self.lower_bounds.add(category)

    def diagnostics(self) -> list[dict[str, Any]]:
        return [
            {
                "code": "discover_collection_warning",
                "category": category,
                "count": count,
                "count_is_lower_bound": category in self.lower_bounds,
            }
            for category, count in sorted(self.counts.items())
        ]


@dataclass
class Collected:
    payload: Any
    config: Any
    report: str
    messages: list[dict[str, str]]
    source_sha256: str
    source_proofs: tuple[_SourceProof, ...] = ()


@dataclass(frozen=True)
class _SourceProof:
    start: int
    lexeme: str
    template_prefix: bool = False


def _controls(value: str) -> bool:
    return any(
        char not in {"\n", "\t"}
        and (unicodedata.category(char).startswith("C") or char in {"\u2028", "\u2029"})
        for char in value
    )


def _expression_private(node: ast.AST, privacy: RunPrivacy) -> None:
    """Prove a finite source expression without evaluating calls or containers."""
    visited = 0

    def visit(item: ast.AST, depth: int = 0, *, numeric: bool = False) -> None:
        nonlocal visited
        visited += 1
        if depth > 64 or visited > 10_000:
            raise BudgetError("discover_review_content_unavailable")
        if isinstance(item, ast.Constant):
            value = item.value
            if not (value is None or isinstance(value, (str, bool, int, float))):
                raise BudgetError("discover_review_content_unsafe")
            if numeric and (isinstance(value, bool) or not isinstance(value, (int, float))):
                raise BudgetError("discover_review_content_unsafe")
            if (
                isinstance(value, float)
                and not math.isfinite(value)
                or isinstance(value, str)
                and _controls(value)
                or privacy.value(value) != value
            ):
                raise BudgetError("discover_review_content_unsafe")
            return
        if numeric:
            if isinstance(item, ast.UnaryOp) and isinstance(item.op, (ast.UAdd, ast.USub)):
                visit(item.operand, depth + 1, numeric=True)
                return
            if isinstance(item, ast.BinOp) and isinstance(
                item.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)
            ):
                visit(item.left, depth + 1, numeric=True)
                visit(item.right, depth + 1, numeric=True)
                return
            raise BudgetError("discover_review_content_unsafe")
        references = (ast.Name, ast.Attribute, ast.Subscript)
        if isinstance(item, ast.Name):
            return
        if isinstance(item, ast.Attribute) and isinstance(item.value, references):
            visit(item.value, depth + 1)
            return
        if (
            isinstance(item, ast.Subscript)
            and isinstance(item.value, references)
            and isinstance(item.slice, ast.Constant)
            and isinstance(item.slice.value, (str, int))
            and not isinstance(item.slice.value, bool)
        ):
            visit(item.value, depth + 1)
            visit(item.slice, depth + 1)
            return
        if (
            isinstance(item, ast.Call)
            and isinstance(item.func, ast.Attribute)
            and isinstance(item.func.value, ast.Name)
            and not item.keywords
        ):
            name = (item.func.value.id, item.func.attr)
            if name == ("os", "getcwd") and not item.args:
                return
            if name == ("random", "randint") and len(item.args) == 2:
                for argument in item.args:
                    visit(argument, depth + 1, numeric=True)
                return
        # An opaque call/container can introduce unknown decoded key context.
        raise BudgetError("discover_review_content_unsafe")

    if not isinstance(node, ast.FormattedValue):
        raise BudgetError("discover_review_content_unsafe")
    visit(node.value)
    if node.format_spec is not None:
        if not isinstance(node.format_spec, ast.JoinedStr):
            raise BudgetError("discover_review_content_unsafe")
        for part in node.format_spec.values:
            if not isinstance(part, ast.Constant) or not isinstance(part.value, str):
                raise BudgetError("discover_review_content_unsafe")
            visit(part)


def _source_proofs(payload: Any, root: Path) -> tuple[_SourceProof, ...]:
    """Locate non-path Python lexemes in native-rendered snippets without evaluation."""
    from reprollm.run.privacy import _ABSOLUTE_PATH, RunPrivacy

    rendered = payload.render()
    privacy = RunPrivacy(root, hostname=socket.gethostname(), username=getpass.getuser())
    result = []
    for index, entry in enumerate(payload.files):
        if re.search(r"\.py#L[0-9]+$", entry.path) is None:
            continue
        # Derive offsets from the native renderer, not a second message renderer.
        prefix = replace(payload, files=payload.files[:index]).render()
        single = replace(payload, tree=[], files=[entry]).render()
        base = len(prefix) + len(single) - len(entry.text) - 1
        if rendered[base : base + len(entry.text)] != entry.text:
            raise BudgetError("discover_review_content_unavailable")
        lines = entry.text.splitlines(keepends=True)
        source = textwrap.dedent(entry.text)
        dedented = source.splitlines(keepends=True)
        try:
            # Native collection already owns warning facts. Rechecking the same
            # snippet must neither echo source text nor add duplicate warnings.
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                tree = ast.parse(source)
            for token in tokenize.generate_tokens(io.StringIO(entry.text).readline):
                if token.type != tokenize.COMMENT:
                    continue
                start = sum(map(len, lines[: token.start[0] - 1])) + token.start[1]
                if entry.text[start : start + len(token.string)] != token.string:
                    raise BudgetError("discover_review_content_unavailable")
                for separator in re.finditer(
                    r"`[A-Za-z_]\w*`(?P<slash>/`[A-Za-z_]\w*`)", token.string
                ):
                    offset = base + start + separator.start("slash")
                    match = _ABSOLUTE_PATH.match(rendered, offset)
                    if match and match[0] in {separator["slash"], separator["slash"] + "."}:
                        result.append(_SourceProof(offset, match[0]))
            for node in ast.walk(tree):
                if not isinstance(node, ast.JoinedStr) or len(node.values) < 2:
                    continue
                temporary = (
                    isinstance(node.values[0], ast.Constant)
                    and node.values[0].value == "/tmp/"
                    and isinstance(node.values[1], ast.FormattedValue)
                )
                suffix_index = (
                    1
                    if len(node.values) == 2 and isinstance(node.values[0], ast.FormattedValue)
                    else 2
                    if temporary and len(node.values) == 3
                    else None
                )
                tail = node.values[suffix_index] if suffix_index is not None else None
                suffix = (
                    tail.value
                    if isinstance(tail, ast.Constant)
                    and isinstance(tail.value, str)
                    and re.fullmatch(r"/[A-Za-z_][A-Za-z0-9_.-]*", tail.value)
                    else None
                )
                if not temporary and suffix is None:
                    continue
                segment = ast.get_source_segment(source, node)
                if segment is None:
                    continue
                opening = re.match(r"""(?i)(?:f|fr|rf)(?P<quote>"{3}|'{3}|"|')""", segment)
                if opening is None:
                    continue
                if temporary and not segment[opening.end() :].startswith("/tmp/{"):
                    continue
                if suffix is not None and not segment.endswith(suffix + opening["quote"]):
                    continue
                for formatted in node.values:
                    if isinstance(formatted, ast.FormattedValue):
                        _expression_private(formatted, privacy)
                line = dedented[node.lineno - 1]
                original = lines[node.lineno - 1]
                if not original.endswith(line):
                    raise BudgetError("discover_review_content_unavailable")
                # AST columns count UTF-8 bytes; native rendering counts characters.
                column = len(line.encode("utf-8")[: node.col_offset].decode("utf-8"))
                start = sum(map(len, lines[: node.lineno - 1])) + len(original) - len(line) + column
                if entry.text[start : start + len(segment)] != segment:
                    continue
                if temporary:
                    result.append(
                        _SourceProof(base + start + opening.end(), "/tmp/{", template_prefix=True)
                    )
                if suffix is not None:
                    offset = base + start + len(segment) - len(opening["quote"]) - len(suffix)
                    result.append(_SourceProof(offset, suffix))
        except (SyntaxError, tokenize.TokenError, IndentationError):
            continue
        except BudgetError:
            raise
        except (OSError, ValueError, RuntimeError, UnicodeError):
            raise BudgetError("discover_review_content_unavailable") from None
    return tuple(result)


def _source_text(value: str, root: Path, proofs: tuple[_SourceProof, ...] = ()) -> None:
    """Require exact source bytes to be safe for both review and submission.

    Native collection already applies the secret/drop policy. Its portable
    source literals need a different role from machine metadata, while unknown
    paths, identities and all other native privacy checks still fail closed.
    """
    from reprollm.run.privacy import _ABSOLUTE_PATH, _LOCAL_URI, RunPrivacy

    if _controls(value):
        raise BudgetError("discover_review_content_controls")
    privacy = RunPrivacy(root, hostname=socket.gethostname(), username=getpass.getuser())
    if (
        _LOCAL_URI.search(value)
        or any(pattern.search(value) for pattern, _ in privacy.identities)
        or re.search(r"(?<![\w])~[^/\\\s]+[/\\]", value)
    ):
        raise BudgetError("discover_review_content_unsafe")
    try:
        machine_roots = (root.resolve().as_posix(), Path.home().resolve().as_posix())
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
        index = 0
        by_start = {proof.start: proof for proof in proofs}
        if any(
            value[proof.start : proof.start + len(proof.lexeme)] != proof.lexeme for proof in proofs
        ):
            raise BudgetError("discover_review_content_unavailable")

        def portable(match: re.Match[str]) -> str:
            nonlocal index
            path = match[0]
            prefix = value[max(0, match.start() - 2) : match.start()]
            proof = by_start.get(match.start())
            proved = proof is not None and (
                path.startswith(proof.lexeme) if proof.template_prefix else path == proof.lexeme
            )
            home_relative = prefix.endswith("~")
            literal = path
            opening = match.start() - (2 if home_relative else 1)
            if (
                not proved
                and path.count("`") == 1
                and opening >= 0
                and value[opening] == "`"
                and (opening == 0 or value[opening - 1] != "`")
            ):
                closing = path.index("`")
                if any(char not in ".,;:!?。！？、，；：…" for char in path[closing + 1 :]):
                    raise BudgetError("discover_review_content_unsafe")
                literal = path[:closing]
            if (
                not literal.startswith("/")
                or literal.startswith("//")
                or "\\" in literal
                or any(part in {".", ".."} for part in literal.split("/"))
                or any(literal == base or literal.startswith(base + "/") for base in machine_roots)
            ):
                raise BudgetError("discover_review_content_unsafe")
            if not proved and any(char in literal for char in "{}[]()`$"):
                raise BudgetError("discover_review_content_unsafe")
            parts = PurePosixPath(literal).parts
            if (
                not (home_relative or proved)
                and len(parts) > 1
                and parts[1].casefold()
                in {
                    "home",
                    "users",
                    "root",
                    "private",
                    "tmp",
                    "var",
                    "run",
                    "mnt",
                    "media",
                    "volumes",
                    "srv",
                    "data",
                    "datasets",
                    "workspace",
                    "workspaces",
                    "proc",
                    "sys",
                    "dev",
                }
            ):
                raise BudgetError("discover_review_content_unsafe")
            allowed = (
                home_relative or proved or (len(parts) > 2 and parts[1] in {"usr", "opt", "api"})
            )
            allowed = allowed or (
                path == "/INST"
                and prefix.endswith("[")
                and value[match.end() : match.end() + 1] == "]"
            )
            allowed = allowed or bool(re.match(r"/v[0-9]+/", literal))
            if not allowed and prefix.endswith("](") and "%" not in literal:
                target = root / literal.split("#", 1)[0].split("?", 1)[0].lstrip("/")
                resolved = target.resolve()
                allowed = resolved.is_relative_to(root.resolve()) and resolved.exists()
            if not allowed:
                raise BudgetError("discover_review_content_unsafe")
            token = "Z" + digest + "Z" + str(index) + "Z"
            index += 1
            while token in value:
                token += "Z"
            # Protect only the proven /tmp/{ lexeme, never an entire expression.
            return (
                token + "{" + path[len(proof.lexeme) :]
                if proved and proof and proof.template_prefix
                else token
            )

        protected = _ABSOLUTE_PATH.sub(portable, value)
        if privacy.text(protected)[0] != protected:
            raise BudgetError("discover_review_content_unsafe")
    except BudgetError:
        raise
    except (OSError, ValueError, RuntimeError, RecursionError):
        raise BudgetError("discover_review_content_unavailable") from None


class _NativeSourceText(str):
    """Nominal worker-local proof; a JSON object/string cannot acquire this role."""

    def __new__(
        cls, value: str, root: Path, proofs: tuple[_SourceProof, ...] = ()
    ) -> _NativeSourceText:
        _source_text(value, root, proofs)
        return super().__new__(cls, value)


def finalize_preview(reply: Reply, root: Path) -> Reply:
    """Project every other field normally, then retain verified native source bytes."""
    from skill_runtime import sanitize_reply

    if reply.action != "discover.preview":
        return blocked(reply.action, "discover_review_transport_invalid")
    if not isinstance(reply.data, dict) or "messages" not in reply.data:
        return sanitize_reply(reply, root)
    messages = reply.data["messages"]
    if (
        not isinstance(messages, list)
        or len(messages) != 2
        or any(
            not isinstance(message, dict)
            or set(message) != {"role", "content"}
            or message["role"] != role
            or not isinstance(message["content"], _NativeSourceText)
            for message, role in zip(messages, ("system", "user"), strict=True)
        )
    ):
        return blocked(reply.action, "discover_review_transport_invalid")
    safe = sanitize_reply(
        replace(reply, data={key: value for key, value in reply.data.items() if key != "messages"}),
        root,
    )
    safe.data["messages"] = [
        {"role": message["role"], "content": str(message["content"])} for message in messages
    ]
    return safe


def _collect(
    request: Request,
    root: Path,
    state_home: Path,
    warning_counts: _CollectionWarnings | None = None,
) -> Collected:
    from skill_runtime import input_signature

    from reprollm.cli.discover import _manifest_field_list
    from reprollm.core.config import load_config
    from reprollm.core.context import AuditContext
    from reprollm.core.errors import UserError
    from reprollm.discover.collector import collect, dry_run_report
    from reprollm.schemas.config import DiscoverConfig

    if request.options.get("paper") is not None:
        raise UserError("Paper analysis is not available in Beta.")
    before = input_signature(root, [], state_home)
    loaded = load_config(root)
    config = loaded.discover if loaded else DiscoverConfig()
    if not (request.options.get("experimental") or config.enabled):
        raise UserError(
            "discover is experimental; pass --experimental or set "
            "discover.enabled: true in .reprollm/config.yaml"
        )
    if "max_chars" in request.options:
        config = config.model_copy(update={"max_chars": request.options["max_chars"]})
    observed = warning_counts if warning_counts is not None else _CollectionWarnings()
    with observed.capture():
        payload = collect(root, AuditContext(root, level=0).fs, config)
        system = (files("reprollm.discover") / "prompts/system.md").read_text(encoding="utf-8")
        declared = (
            _manifest_field_list(root)
            if any(entry.path == "reprollm.yaml" for entry in payload.files)
            else []
        )
        messages = [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": payload.render()
                + "\n\nAlready-declared manifest fields (do not re-suggest):\n"
                + (", ".join(declared) or "(none)"),
            },
        ]
    proofs = _source_proofs(payload, root)
    for message in messages:
        _source_text(message["content"], root, proofs if message["role"] == "user" else ())
    if input_signature(root, [], state_home) != before:
        raise BudgetError("discover_inputs_changed_during_collection")
    return Collected(
        payload,
        config,
        dry_run_report(payload),
        messages,
        identity(
            {
                "source_signature": before,
                "config": config.model_dump(mode="json"),
                "messages_sha256": identity(messages),
            }
        ),
        proofs,
    )


def preview(request: Request, *, root: Path, state_home: Path, helper_identity: str) -> Reply:
    warning_counts = _CollectionWarnings()
    reply = _preview(
        request,
        root=root,
        state_home=state_home,
        helper_identity=helper_identity,
        warning_counts=warning_counts,
    )
    reply.diagnostics.extend(warning_counts.diagnostics())
    return reply


def _preview(
    request: Request,
    *,
    root: Path,
    state_home: Path,
    helper_identity: str,
    warning_counts: _CollectionWarnings,
) -> Reply:
    from reprollm.core.errors import UserError

    try:
        collected = _collect(request, root, state_home, warning_counts)
        data = {
            "nothing_sent": True,
            "report": collected.report,
            "input_files": [entry.path for entry in collected.payload.files],
            "dropped_files": collected.payload.dropped_files,
            "truncated_files": collected.payload.truncated_files,
            "excluded_files": collected.payload.excluded_files,
            "approval_requirements": {
                "helper_sha256": helper_identity,
                "source_sha256": collected.source_sha256,
                "messages_sha256": identity(collected.messages),
                "base_url_env": collected.config.base_url_env,
                "api_key_env": collected.config.api_key_env,
                "model_env": collected.config.model_env,
            },
        }
        if request.options.get("show_content"):
            data["messages"] = [
                {
                    "role": message["role"],
                    "content": _NativeSourceText(
                        message["content"],
                        root,
                        collected.source_proofs if message["role"] == "user" else (),
                    ),
                }
                for message in collected.messages
            ]
        return Reply(request.action, cli_exit_code=0, data=data)
    except UserError as error:
        return writes._native_error(request, str(error))
    except BudgetError as error:
        return blocked(request.action, str(error))
    except (OSError, ValueError):
        return blocked(request.action, "discover_preview_inputs_unavailable")


def _publish(
    request: Request,
    context: Any,
    collected: Collected,
    raw: bytes,
    suffix: str,
    effects: list[writes.Published],
    warning_counts: _CollectionWarnings,
) -> str:
    from reprollm.core.rule_lifecycle import _owned_path

    state = writes._owned_state(context.home / "writes")
    relative = (
        ".reprollm/discover/" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + suffix
    )
    target = _owned_path(context.root, relative)
    artifact = writes._artifact(request, context.root, target, raw, role="discover", mode=0o600)
    if artifact.expected is not None:
        raise BudgetError("discover_output_already_exists")
    with context.publication(), writes._project_lock(state, context.root):
        if (
            _collect(request, context.root, context.home, warning_counts).source_sha256
            != collected.source_sha256
        ):
            raise BudgetError("discover_source_changed_after_submission")
        writes._check_artifact(artifact)
        directories: list[writes.DirectoryIdentity] = []
        ready = writes._make_directories(artifact, directories)
        writes.publish_artifact(ready, effects)
    return relative


def _native_failure(error: Exception, budget: dict[str, Any]) -> dict[str, Any]:
    from skill_network import failure_category

    diagnostic: dict[str, Any] = {"code": "discover_native_request_failed"}
    cause = error.__cause__
    if isinstance(cause, httpx.HTTPError):
        diagnostic["category"] = failure_category(cause)
    else:
        attempts = budget["attempts"]
        status = attempts[-1].get("http_status") if attempts else None
        if type(status) is int and status >= 400:
            diagnostic.update(
                status_code=status,
                category="access_denied"
                if status in {401, 403}
                else "rate_limited"
                if status == 429
                else "server_error"
                if status >= 500
                else "http_error",
            )
        else:
            diagnostic["category"] = "response_invalid"
    return diagnostic


def execute(request: Request, context: Any) -> Reply:
    """Use the native request loop once; no provider work is replayed here."""
    warning_counts = _CollectionWarnings()
    reply = _execute(request, context, warning_counts)
    reply.diagnostics.extend(warning_counts.diagnostics())
    return reply


def _execute(request: Request, context: Any, warning_counts: _CollectionWarnings) -> Reply:
    from skill_operations import _directory, _store

    from reprollm import __version__
    from reprollm.cli.discover import _endpoint_credentials
    from reprollm.core.errors import UserError
    from reprollm.discover.candidates import finalize, sanitize_response_text
    from reprollm.discover.client import DiscoverError, request_candidates
    from reprollm.run.privacy import RunPrivacy

    ledger: Ledger | None = None
    effects: list[writes.Published] = []
    try:
        if not request.grants.write or not request.grants.network:
            return blocked(request.action, "authorization_required", needs_authorization=True)
        if request.grants.paid_discover is None:
            return blocked(
                request.action, "discover_budget_approval_required", needs_authorization=True
            )
        policy, approval = parse_grant(request.grants.paid_discover)
        collected = _collect(request, context.root, context.home, warning_counts)
        base_url, api_key, model = _endpoint_credentials(collected.config)
        if (
            approval.helper_sha256 != context.identity
            or approval.source_sha256 != collected.source_sha256
            or approval.messages_sha256 != identity(collected.messages)
            or base_url.rstrip("/") + "/chat/completions" != policy.endpoint
            or model != policy.model
        ):
            raise BudgetError("discover_approval_binding_changed")
        store = _store(context.home, create=True)
        budgets = store / "discovery-budgets"
        _directory(budgets)
        ledger = Ledger(budgets / (approval.approval_id + ".json"), approval, context.operation_id)
        privacy = RunPrivacy(
            context.root, hostname=socket.gethostname(), username=getpass.getuser()
        )

        def check_current() -> None:
            context.check_cancel()
            if (
                _collect(request, context.root, context.home, warning_counts).source_sha256
                != collected.source_sha256
            ):
                raise BudgetError("discover_source_changed_before_send")

        with GuardedClient(
            policy=policy,
            approval=approval,
            messages=collected.messages,
            api_key=api_key,
            ledger=ledger,
            check_current=check_current,
        ) as transport:
            try:
                response = request_candidates(
                    base_url=base_url,
                    api_key=api_key,
                    model=model,
                    system_prompt=collected.messages[0]["content"],
                    user_content=collected.messages[1]["content"],
                    transport=transport,
                )
            except DiscoverError as error:
                safe, _ = sanitize_response_text(
                    error.raw_text or collected.messages[1]["content"],
                    privacy,
                    secret_values=(api_key,),
                )
                artifact = _publish(
                    request,
                    context,
                    collected,
                    safe.encode("utf-8"),
                    ".raw.txt",
                    effects,
                    warning_counts,
                )
                return Reply(
                    request.action,
                    invocation="internal_error",
                    cli_exit_code=3,
                    complete=False,
                    data={
                        "phase": "failed",
                        "artifacts_written": [artifact],
                        "budget": ledger.summary(),
                    },
                    diagnostics=[_native_failure(error, ledger.summary())],
                )
        document = finalize(
            response.candidates,
            model=model,
            reprollm_version=__version__,
            input_files=[entry.path for entry in collected.payload.files],
            dropped_files=collected.payload.dropped_files,
            truncated_files=collected.payload.truncated_files,
            generated_at=datetime.now(timezone.utc),
            privacy=privacy,
            secret_values=(api_key,),
        )
        raw = (document.model_dump_json(indent=2) + "\n").encode("utf-8")
        artifact = _publish(request, context, collected, raw, ".json", effects, warning_counts)
        return Reply(
            request.action,
            cli_exit_code=0,
            data={
                "phase": "applied",
                "artifacts_written": [artifact],
                "candidates": document.model_dump(mode="json"),
                "budget": ledger.summary(),
                "rules_accepted": False,
            },
        )
    except UserError as error:
        return writes._native_error(request, str(error))
    except (
        BudgetError,
        DiscoverDeadline,
        writes.WriteError,
        ImportError,
        httpx.HTTPError,
        OSError,
        ValueError,
        RecursionError,
    ) as error:
        reply = blocked(
            request.action,
            str(error)
            if isinstance(error, (BudgetError, writes.WriteError))
            else "discover_deadline_unknown_charge"
            if isinstance(error, DiscoverDeadline)
            else "discover_input_or_publication_failed",
            needs_authorization=isinstance(error, BudgetError)
            and str(error) == "discover_budget_insufficient_for_attempt_limit",
        )
        budget = None
        if ledger is not None:
            with contextlib.suppress(OSError, ValueError, KeyError):
                budget = ledger.summary()
        reply.data = {
            "phase": "partial" if effects else "unapplied",
            "artifacts_written": writes._remaining(effects, context.root),
            "preserved_changed_targets": writes._preserved_changes(effects, context.root),
            "budget": budget,
        }
        if isinstance(error, (ImportError, httpx.HTTPError)):
            from skill_network import failure_category

            reply.diagnostics.append(
                {"code": "discover_client_unavailable", "category": failure_category(error)}
            )
        return reply
