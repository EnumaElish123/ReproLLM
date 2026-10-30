"""Read one typed Skill request and emit one bounded JSON reply."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

# Isolated Python omits the script directory; only this trusted sibling is added.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from skill_request import (  # noqa: E402
    BASE_ACTIONS,
    MAX_REQUEST_BYTES,
    Executor,
    JSONValue,
    Reply,
    RequestError,
    StatusProvider,
    blocked,
    dispatch,
    encode_reply,
    error_reply,
    parse_request,
)


class InstallationBlocked(Exception):
    """The existing installation could not be safely verified."""


def installation_status(home: Path | None = None) -> JSONValue:
    from bootstrap import Bootstrap, BootstrapError, default_home
    from install_catalog import CatalogError, load_catalog

    try:
        catalog = load_catalog(Path(__file__).resolve().parents[1] / "assets/install-catalog.json")
        return cast(JSONValue, Bootstrap(home or default_home(), catalog).status())
    except (BootstrapError, CatalogError, OSError) as error:
        raise InstallationBlocked from error


def handle(
    raw: bytes,
    *,
    executor: Executor | None = None,
    status_provider: StatusProvider | None = None,
    available_actions: frozenset[str] = BASE_ACTIONS,
) -> Reply:
    request = None
    try:
        request = parse_request(raw)
        return dispatch(
            request,
            executor=executor,
            status_provider=status_provider,
            available_actions=available_actions,
        )
    except RequestError as error:
        return error_reply(error)
    except InstallationBlocked:
        return blocked(request.action if request else None, "installation_verification_failed")
    except Exception:
        # Provider/executor errors may contain credentials or machine paths.
        return Reply(
            None,
            invocation="internal_error",
            complete=False,
            diagnostics=[{"code": "skill_execution_failed"}],
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, help="Use this owned tool installation directory.")
    args = parser.parse_args(argv)
    from skill_runtime import AVAILABLE_ACTIONS, RuntimeExecutor

    raw = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
    reply = handle(
        raw,
        executor=RuntimeExecutor(args.home),
        status_provider=lambda: installation_status(args.home),
        available_actions=AVAILABLE_ACTIONS,
    )
    wire = encode_reply(reply)
    sys.stdout.buffer.write(wire + b"\n")
    sys.stdout.buffer.flush()
    invocation = json.loads(wire)["invocation"]
    return {"handled_result": 0, "user_error": 2, "internal_error": 3, "blocked": 2}[invocation]


if __name__ == "__main__":
    raise SystemExit(main())
