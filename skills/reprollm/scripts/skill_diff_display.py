"""Retain typed run context until native diff has compared and selected its display."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, cast

if TYPE_CHECKING:
    from reprollm.diff.inputs import DiffInput
    from reprollm.run.privacy import RunPrivacy
    from reprollm.schemas.diff_report import DiffReport
    from reprollm.schemas.run_record import RunRecord
    from reprollm.schemas.state import Leaf

ResultT = TypeVar("ResultT")
DisplaySanitizer = Callable[[Any, list[dict[str, Any]]], Any]


class _DiffCommands(Protocol):
    load_input: Callable[[str, Path], DiffInput]
    from_selected_run: Callable[[RunRecord, Path], DiffInput]
    _report: Callable[[DiffInput, DiffInput, Path], DiffReport]
    sanitize_report: Callable[[DiffReport, RunPrivacy], DiffReport]


class _InputReaders(Protocol):
    read_run: Callable[[Path, str], tuple[RunRecord, str]]
    read_run_record: Callable[[Path], tuple[RunRecord, str]]


@dataclass(frozen=True)
class _Side:
    values: dict[str, Leaf]
    records: tuple[RunRecord, ...]


def _display_value(
    value: Any,
    path: str,
    side: _Side,
    sanitize: DisplaySanitizer,
) -> tuple[Any, int]:
    from skill_run_display import mask_command_argv, mask_secret_env_observation

    from reprollm.core.bindings import values_equal

    leaf = side.values.get(path)
    if leaf is None or leaf.source != "run":
        return value, 0
    safe = value
    if (
        path == "command.argv"
        and isinstance(value, list)
        and all(isinstance(item, str) for item in value)
    ):
        safe, _ = mask_command_argv(value)
    kind = (leaf.detail or "").split(":", 1)[0]
    if kind not in {"cli", "config", "env"}:
        return safe, int(not values_equal(safe, value))
    matched = False
    for record in side.records:
        for observation in record.bindings_observed.get(path, ()):
            source = observation.source
            location = f"{source.path}:" if source.path else ""
            detail = f"{source.type}:{location}{source.key}"
            if detail != leaf.detail or not values_equal(observation.value, leaf.value):
                continue
            matched = True
            # Use the original typed source, not the ambiguous joined detail string.
            item = observation.model_dump(mode="json", exclude_unset=True)
            item["value"], _ = mask_secret_env_observation(
                observation.value, source.type, source.key
            )
            projected = sanitize({"bindings_observed": {path: [item]}}, [])
            fields = projected["bindings_observed"]
            if len(fields) != 1:
                raise ValueError("private diff observation projection is incomplete")
            candidate = next(iter(fields.values()))[0]["value"]
            if not values_equal(candidate, value):
                safe = candidate
    if not matched:
        raise ValueError("private diff source context is unavailable")
    return safe, int(not values_equal(safe, value))


def project_leaf_value(
    value: Any,
    path: str,
    leaf: Leaf,
    records: Sequence[RunRecord],
    sanitize: DisplaySanitizer,
) -> tuple[Any, int]:
    """Privately display one already selected leaf without choosing its evidence again."""
    return _display_value(value, path, _Side({path: leaf}, tuple(records)), sanitize)


def invoke_private_diff(
    argv: list[str],
    root: Path,
    *,
    invoke_cli: Callable[[list[str], Path], ResultT],
    sanitize: DisplaySanitizer,
) -> tuple[ResultT, list[dict[str, Any]]]:
    """Privately project displayed values after the original comparison and gate.

    A worker owns one native invocation. Temporary module bindings capture the
    records that invocation already reads; they are not a shared threaded API.
    """
    import importlib

    commands = cast(_DiffCommands, importlib.import_module("reprollm.cli.diff"))
    readers = cast(_InputReaders, importlib.import_module("reprollm.diff.inputs"))
    original_load = commands.load_input
    original_selected = commands.from_selected_run
    original_report = commands._report
    original_sanitize = commands.sanitize_report
    original_run_reader = readers.read_run
    original_record_reader = readers.read_run_record
    active_reads: list[list[RunRecord]] = []
    records_by_state: dict[int, tuple[RunRecord, ...]] = {}
    sides: tuple[_Side, _Side] | None = None
    diagnostics: list[dict[str, Any]] = []

    def capture_run(project: Path, prefix: str) -> tuple[RunRecord, str]:
        record, raw = original_run_reader(project, prefix)
        if active_reads:
            active_reads[-1].append(record)
        return record, raw

    def capture_record(path: Path) -> tuple[RunRecord, str]:
        record, raw = original_record_reader(path)
        if active_reads:
            active_reads[-1].append(record)
        return record, raw

    def capture_load(value: str, project: Path) -> DiffInput:
        records: list[RunRecord] = []
        active_reads.append(records)
        try:
            result = original_load(value, project)
        finally:
            active_reads.pop()
        records_by_state[id(result.state)] = tuple(records)
        return result

    def capture_selected(record: RunRecord, folder: Path) -> DiffInput:
        result = original_selected(record, folder)
        records_by_state[id(result.state)] = (record,)
        return result

    def capture_report(left: DiffInput, right: DiffInput, project: Path) -> DiffReport:
        nonlocal sides
        sides = (
            _Side(left.state.flatten(), records_by_state.get(id(left.state), ())),
            _Side(right.state.flatten(), records_by_state.get(id(right.state), ())),
        )
        return original_report(left, right, project)

    def private_report(report: DiffReport, privacy: RunPrivacy) -> DiffReport:
        if sides is None:
            raise ValueError("private diff input context is unavailable")
        # The CLI computes fail-on and its full summary before calling this seam.
        projected = report.model_copy(deep=True)
        changes = 0
        for change in projected.changes:
            change.a, count = _display_value(change.a, change.path, sides[0], sanitize)
            changes += count
            change.b, count = _display_value(change.b, change.path, sides[1], sanitize)
            changes += count
        if changes:
            diagnostics.append({"code": "display_value_transformation", "count": changes})
        return original_sanitize(projected, privacy)

    commands.load_input = capture_load
    commands.from_selected_run = capture_selected
    commands._report = capture_report
    commands.sanitize_report = private_report
    readers.read_run = capture_run
    readers.read_run_record = capture_record
    try:
        result = invoke_cli(argv, root)
    finally:
        commands.load_input = original_load
        commands.from_selected_run = original_selected
        commands._report = original_report
        commands.sanitize_report = original_sanitize
        readers.read_run = original_run_reader
        readers.read_run_record = original_record_reader
    return result, diagnostics
