"""ReproLLM error types (D-11, AGENTS.md §8).

User-facing failures raise :class:`UserError` (exit code 2): the message must name the
file or field path at fault and say how to fix it. Anything else is an internal error
(exit code 3); a traceback is printed only with ``-v``.
"""


class ReproLLMError(Exception):
    """Base class for all ReproLLM errors; defaults to the internal exit code."""

    exit_code = 3


class UserError(ReproLLMError):
    """A user-fixable problem. Exit code 2."""

    exit_code = 2


class InternalError(ReproLLMError):
    """An unexpected internal failure. Exit code 3."""

    exit_code = 3
