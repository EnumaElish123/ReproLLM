"""Deterministic audit rules, one module per rule category (spec §12).

Importing this package registers every implemented rule; the engine imports it
before resolving profiles.
"""

from reprollm.rules import code, env, exec_  # noqa: F401 — @register_rule side effects
