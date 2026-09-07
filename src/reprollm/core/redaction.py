"""Secret redaction policy (spec §16). Redaction is a security boundary.

M2 ships the forbidden-file matcher (§16.4) needed by ``env.secret_files_ignored``.
The full policy — env-name classification, value-pattern redaction, allowlisted
environment capture — lands in M5-T01 and must keep 100 % branch coverage.
"""

from __future__ import annotations

import fnmatch
from pathlib import PurePosixPath

#: Never snapshot or send these; their hashes MAY be recorded (spec §16.4).
FORBIDDEN_GLOBS: tuple[str, ...] = (
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "id_rsa*",
    "id_ed25519*",
    "credentials*",
    "*.p12",
    "*.pfx",
    "*.jks",
    "*_rsa",
    ".netrc",
    ".npmrc",
    ".pypirc",
)

#: Template names exempt from the forbidden list (still value-redacted).
EXEMPT_TEMPLATE_NAMES: frozenset[str] = frozenset({".env.example", ".env.sample", ".env.template"})


def is_forbidden_file(rel_path: str) -> bool:
    """True for secret-bearing file names (§16.4), exempting the templates.

    Matches on the basename, case-insensitively; directory components are
    irrelevant (``config/.env`` is as forbidden as ``.env``).
    """
    name = PurePosixPath(rel_path).name.lower()
    if name in EXEMPT_TEMPLATE_NAMES:
        return False
    return any(fnmatch.fnmatch(name, pattern.lower()) for pattern in FORBIDDEN_GLOBS)
