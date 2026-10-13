"""Compare complete JSON documents without updating either input (VOPT-03).

Run with the project's environment:
  uv run python scripts/compare_gold.py expected.json actual.json --audit-metadata

Stdout is a schema-versioned comparison report. Exit 0 means equal, 1 means a
semantic delta, and 2 means invalid input. This is not a complete Gate A runner:
the caller still checks target identity, command exits, text, hints and resources.
Reports reference input byte hashes, never duplicate leaf values or input paths.
Keep the independently reviewed expected file and original actual file alongside
the report; no command in this script creates or refreshes gold answers.
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import math
import socket
from decimal import Decimal
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from reprollm.core.redaction import redact_text
from reprollm.schemas.finding import AuditReport

MAX_BYTES = 32 * 1024 * 1024
AUDIT_METADATA = ("generated_at", "reprollm_version")


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError("non-finite JSON number")


def _finite_decimal(value: str) -> Decimal:
    if not math.isfinite(float(value)):
        raise ValueError("non-finite JSON number")
    return Decimal(value)


def _load(path: Path, audit: bool) -> tuple[dict[str, Any], str]:
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("JSON document exceeds 32 MiB")
    document = json.loads(
        raw, object_pairs_hook=_object, parse_constant=_reject_constant, parse_float=_finite_decimal
    )
    if not isinstance(document, dict):
        raise ValueError("expected a JSON document object")
    if type(document.get("schema_version")) is not int or document["schema_version"] != 1:
        raise ValueError("expected schema_version 1")
    if audit:
        # Validate, but never compare model_dump(): it would coerce values, fill
        # defaults and normalize aliases, hiding differences in the actual bytes.
        AuditReport.model_validate(document)
        document = {key: value for key, value in document.items() if key not in AUDIT_METADATA}
    return document, hashlib.sha256(raw).hexdigest()


def _safe_segment(key: str, identities: tuple[str, ...]) -> str:
    # Arbitrary JSON keys can themselves contain secrets or local paths. Keep
    # those distinguishable without copying them into a shareable report.
    if (
        redact_text(key)[1]
        or "/" in key
        or "\\" in key
        or any(identity and identity in key for identity in identities)
    ):
        return "<key-sha256:" + hashlib.sha256(key.encode()).hexdigest() + ">"
    return key.replace("~", "~0")


def _differences(
    expected: Any, actual: Any, pointer: str, identities: tuple[str, ...]
) -> list[dict[str, str]]:
    if type(expected) is not type(actual):
        return [{"pointer": pointer, "kind": "type"}]
    result: list[dict[str, str]] = []
    if isinstance(expected, dict):
        for key in sorted(expected.keys() | actual.keys()):
            child = pointer + "/" + _safe_segment(key, identities)
            if key not in actual:
                result.append({"pointer": child, "kind": "missing"})
            elif key not in expected:
                result.append({"pointer": child, "kind": "unexpected"})
            else:
                result.extend(_differences(expected[key], actual[key], child, identities))
    elif isinstance(expected, list):
        for index in range(max(len(expected), len(actual))):
            child = pointer + "/" + str(index)
            if index >= len(actual):
                result.append({"pointer": child, "kind": "missing"})
            elif index >= len(expected):
                result.append({"pointer": child, "kind": "unexpected"})
            else:
                result.extend(_differences(expected[index], actual[index], child, identities))
    elif expected != actual:
        result.append({"pointer": pointer, "kind": "value"})
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("expected", type=Path, help="independently reviewed gold JSON")
    parser.add_argument("actual", type=Path, help="observed JSON; command exit checked separately")
    parser.add_argument(
        "--audit-metadata",
        action="store_true",
        help="validate AuditReport inputs and ignore only root generated_at/reprollm_version",
    )
    args = parser.parse_args()
    report: dict[str, Any] = {
        "schema_version": 1,
        "ignored_root_fields": list(AUDIT_METADATA) if args.audit_metadata else [],
    }
    documents: list[dict[str, Any]] = []
    for label in ("expected", "actual"):
        try:
            document, digest = _load(getattr(args, label), args.audit_metadata)
        except (OSError, ValueError, ValidationError, RecursionError):
            # Parser/OS/Pydantic messages can quote a secret or absolute path.
            report.update(
                status="INVALID_INPUT",
                invalid_input=label,
                error="Use readable, unique-key schema_version 1 JSON objects; "
                "audit mode requires valid AuditReport documents (limit 32 MiB).",
            )
            print(json.dumps(report, sort_keys=True, indent=2))
            return 2
        documents.append(document)
        report[label + "_sha256"] = digest
    try:
        identities = (getpass.getuser(), socket.gethostname())
        differences = _differences(documents[0], documents[1], "", identities)
    except (OSError, RecursionError):
        report.update(status="INVALID_INPUT", error="Comparison could not complete safely.")
        print(json.dumps(report, sort_keys=True, indent=2))
        return 2
    report.update(status="FAIL" if differences else "PASS", differences=differences)
    print(json.dumps(report, sort_keys=True, indent=2))
    return 1 if differences else 0


if __name__ == "__main__":
    raise SystemExit(main())
