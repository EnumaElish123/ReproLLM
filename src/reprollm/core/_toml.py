"""tomllib shim: stdlib on Python 3.11+, ``tomli`` fallback on 3.10 (D-29)."""

from __future__ import annotations

import sys

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - exercised only on Python 3.10
    import tomli as tomllib  # type: ignore[import-not-found]

__all__ = ["tomllib"]
