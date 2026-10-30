"""Original discovery collection/client/finalizer with owned, guarded publication."""

from __future__ import annotations

import contextlib
import getpass
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path
from typing import Any

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


@dataclass
class Collected:
    payload: Any
    config: Any
    report: str
    messages: list[dict[str, str]]
    source_sha256: str


def _collect(request: Request, root: Path, state_home: Path) -> Collected:
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
    )


def preview(request: Request, *, root: Path, state_home: Path, helper_identity: str) -> Reply:
    from reprollm.core.errors import UserError

    try:
        collected = _collect(request, root, state_home)
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
            data["messages"] = collected.messages
        return Reply(request.action, cli_exit_code=0, data=data)
    except UserError as error:
        return writes._native_error(request, str(error))
    except (OSError, ValueError):
        return blocked(request.action, "discover_preview_inputs_unavailable")


def _publish(
    request: Request,
    context: Any,
    collected: Collected,
    raw: bytes,
    suffix: str,
    effects: list[writes.Published],
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
        if _collect(request, context.root, context.home).source_sha256 != collected.source_sha256:
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
        collected = _collect(request, context.root, context.home)
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
                _collect(request, context.root, context.home).source_sha256
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
                    request, context, collected, safe.encode("utf-8"), ".raw.txt", effects
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
        artifact = _publish(request, context, collected, raw, ".json", effects)
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
