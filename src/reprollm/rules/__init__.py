"""Deterministic audit rules, one module per rule category (spec §12).

Importing this package registers every implemented rule; the engine imports it
before resolving profiles.
"""

from reprollm.rules import (  # noqa: F401 — registration
    code,
    dataset,
    env,
    exec_,
    gen,
    model,
    prompt,
)
