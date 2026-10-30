"""Project historical run facts through native privacy before native text rendering."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, cast

if TYPE_CHECKING:
    from reprollm.schemas.run_record import RunRecord

ResultT = TypeVar("ResultT")
DisplaySanitizer = Callable[[Any, list[dict[str, Any]]], Any]


class _RunReaderModule(Protocol):
    read_run: Callable[[Path, str], tuple[RunRecord, str]]


def mask_command_argv(argv: Sequence[str]) -> tuple[list[str], int]:
    """Reuse recorder key context; subsequent display processing handles text patterns."""
    from reprollm.core.persistence import redact_keyed_values

    result = []
    count = 0
    for index, token in enumerate(argv):
        previous = argv[index - 1] if index else ""
        context = (previous,) if previous.startswith("-") else ()
        masked = str(redact_keyed_values(token, context))
        result.append(masked)
        count += masked != token
    return result, count


def mask_secret_env_observation(value: Any, source_type: str, source_key: str) -> tuple[Any, int]:
    """Reuse the existing environment-name policy for formal bound env values."""
    from reprollm.core.redaction import is_secret_env_name

    if source_type != "env" or value is None or not is_secret_env_name(source_key):
        return value, 0
    marker = "<REDACTED:generic_kv>"
    return marker, int(value != marker)


def invoke_private_show(
    argv: list[str],
    root: Path,
    *,
    invoke_cli: Callable[[list[str], Path], ResultT],
    sanitize: DisplaySanitizer,
) -> tuple[ResultT, list[dict[str, Any]]]:
    """Call the original formatter with private projections in one isolated worker.

    The worker handles one command. As with its native CLI invocation, this
    temporary module binding is not a threaded or shared terminal interface.
    """
    import reprollm.cli.runs as commands
    from reprollm.schemas.run_record import Observation

    readers = cast(_RunReaderModule, commands)
    original_reader = readers.read_run
    diagnostics: list[dict[str, Any]] = []

    def private_reader(project: Path, prefix: str) -> tuple[RunRecord, str]:
        record, raw = original_reader(project, prefix)
        saved = json.loads(raw)
        # Parse a separate tree, so projection never changes the validated source.
        projected = {
            "command": saved["command"],
            "bindings_observed": saved.get("bindings_observed", {}),
        }
        masked, count = mask_command_argv(record.command.argv)
        projected["command"]["argv"] = masked
        for field, observations in record.bindings_observed.items():
            for index, observation in enumerate(observations):
                safe_value, changed = mask_secret_env_observation(
                    observation.value, observation.source.type, observation.source.key
                )
                if changed:
                    projected["bindings_observed"][field][index]["value"] = safe_value
                    count += changed
        if count:
            diagnostics.append({"code": "display_value_transformation", "count": count})
        safe = sanitize(projected, diagnostics)
        safe_command = record.command.model_copy(
            update={"argv": safe["command"]["argv"], "cwd": safe["command"]["cwd"]}
        )
        safe_bindings = {
            field: [Observation.model_validate(item) for item in observations]
            for field, observations in safe["bindings_observed"].items()
        }
        # Keep timestamps, status/evidence, and saved redaction counts untouched.
        return record.model_copy(
            update={"command": safe_command, "bindings_observed": safe_bindings}
        ), raw

    readers.read_run = private_reader
    try:
        result = invoke_cli(argv, root)
    finally:
        readers.read_run = original_reader
    return result, diagnostics
