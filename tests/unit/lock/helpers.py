from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from reprollm.lock.resolver import ResolvedManifest, resolve_manifest
from reprollm.schemas.manifest import Manifest

NOW = datetime(2026, 10, 1, 9, 30, tzinfo=timezone.utc)


def manifest(**sections: Any) -> Manifest:
    return Manifest.model_validate(
        {
            "project": {"name": "lock-acceptance"},
            "experiment": {"profiles": []},
            **sections,
        }
    )


def resolve(root: Path, value: Manifest, **options: Any) -> ResolvedManifest:
    with httpx.Client() as http:
        return resolve_manifest(root, value, http=http, now=NOW, **options)
