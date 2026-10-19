"""Sanitize Python literals without treating source syntax as serialized data.

The AST supplies scalar/key boundaries; tokenization supplies comments and names.
No source is executed, and unchanged source keeps its exact original bytes.
"""

from __future__ import annotations

import ast
import io
import json
import re
import tokenize
import warnings
from collections.abc import Callable
from types import EllipsisType

from reprollm.core.persistence import redact_keyed_values

Sanitize = Callable[[str, tuple[str, ...]], tuple[str, int]]
Scalar = str | bytes | int | float | complex | bool | EllipsisType | None
_LIMIT = 1_048_576
_NODE_LIMIT = 10_000
_DEPTH_LIMIT = 64


def _target_keys(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Name):
        return (node.id,)
    if isinstance(node, ast.Attribute):
        return (node.attr,)
    if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
        return (str(node.slice.value),)
    return ()


def _lookup_arguments(node: ast.Call) -> tuple[int | None, frozenset[str]]:
    # These source descriptors classify location syntax, not verified runtime
    # callees. Unknown methods retain secret-value context conservatively.
    parts = []
    function = node.func
    while isinstance(function, ast.Attribute):
        parts.append(function.attr)
        function = function.value
    if not isinstance(function, ast.Name):
        return None, frozenset()
    descriptor = ".".join([function.id, *reversed(parts)])
    if descriptor in {"os.getenv", "os.environ.get"}:
        return 0, frozenset({"key"})
    if descriptor in {"getattr", "builtins.getattr"}:
        # getattr's name parameter is positional-only in supported Python.
        return 1, frozenset()
    return None, frozenset()


def _contexts(tree: ast.AST) -> dict[ast.AST, tuple[str, ...]]:
    contexts: dict[ast.AST, tuple[str, ...]] = {}

    def assign(target: ast.AST, value: ast.AST) -> None:
        if isinstance(target, (ast.Tuple, ast.List)) and isinstance(value, (ast.Tuple, ast.List)):
            if len(target.elts) == len(value.elts):
                for left, right in zip(target.elts, value.elts, strict=True):
                    assign(left, right)
            return
        contexts[value] = (*contexts.get(value, ()), *_target_keys(target))

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                assign(target, node.value)
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign, ast.NamedExpr)):
            if node.value is not None:
                assign(node.target, node.value)
        elif isinstance(node, ast.keyword) and node.arg is not None:
            contexts[node.value] = (node.arg,)
        elif isinstance(node, ast.arguments):
            positional = [*node.posonlyargs, *node.args]
            if node.defaults:
                for arg, value in zip(
                    positional[-len(node.defaults) :], node.defaults, strict=True
                ):
                    contexts[value] = (arg.arg,)
            for arg, optional in zip(node.kwonlyargs, node.kw_defaults, strict=True):
                if optional is not None:
                    contexts[optional] = (arg.arg,)
    return contexts


class _Source:
    def __init__(self, text: str, sanitize: Sanitize, tree: ast.AST) -> None:
        self.text = text
        self.sanitize = sanitize
        self.contexts = _contexts(tree)
        self.lines = re.findall(r"[^\r\n]*(?:\r\n|\r|\n|$)", text)
        if self.lines and not self.lines[-1]:
            self.lines.pop()
        self.offsets = [0]
        for line in self.lines:
            self.offsets.append(self.offsets[-1] + len(line))
        self.replacements: list[tuple[int, int, str]] = []
        self.fstrings: list[tuple[int, int]] = []
        self.count = 0

    def position(self, line: int, column: int, *, utf8: bool = True) -> int:
        prefix = self.lines[line - 1]
        length = len(prefix.encode("utf-8")[:column].decode("utf-8")) if utf8 else column
        return self.offsets[line - 1] + length

    def span(self, node: ast.AST) -> tuple[int, int]:
        assert isinstance(node, (ast.expr, ast.stmt))
        assert node.end_lineno is not None and node.end_col_offset is not None
        return self.position(node.lineno, node.col_offset), self.position(
            node.end_lineno, node.end_col_offset
        )

    def encoded(self, value: Scalar, node: ast.AST) -> str:
        if not isinstance(value, str):
            return ast.unparse(ast.Constant(value))
        start, end = self.span(node)
        original = self.text[start:end]
        quoted = re.match(r"(?i)[rubf]*([\"'])", original)
        encoded = json.dumps(value, ensure_ascii=False)
        if quoted and quoted[1] == "'":
            return "'" + encoded[1:-1].replace('\\"', '"').replace("'", "\\'") + "'"
        return encoded

    def scalar(self, value: Scalar, keys: tuple[str, ...]) -> tuple[Scalar, bool]:
        decoded = value.decode("latin-1") if isinstance(value, bytes) else str(value)
        safe, count = self.sanitize(decoded, keys)
        if safe == decoded:
            return value, False
        self.count += max(count, 1)
        return (safe.encode("latin-1") if isinstance(value, bytes) else safe), True

    def visit(
        self, node: ast.AST, keys: tuple[str, ...] = (), *, in_fstring: bool = False
    ) -> tuple[ast.AST, bool]:
        keys = (*keys, *self.contexts.get(node, ()))
        if isinstance(node, (ast.Attribute, ast.BinOp)):
            start, end = self.span(node)
            original = self.text[start:end]
            # Hyphen/dot chains can contain a normative token or a machine
            # identity across several Python tokens. They contain no field
            # syntax, quoted data, or division operators.
            if re.fullmatch(r"[\w.-]+", original):
                safe_name, count = self.sanitize(original, ())
                if safe_name != original:
                    replacement: ast.AST = ast.copy_location(ast.Name(_identifier(safe_name)), node)
                    if not in_fstring:
                        self.replacements.append((start, end, _identifier(safe_name)))
                    self.count += max(count, 1)
                    return replacement, True
        if isinstance(node, ast.JoinedStr):
            return self.joined(node, keys, in_fstring=in_fstring)
        if isinstance(node, ast.Constant):
            safe, changed = self.scalar(node.value, keys)
            if not changed:
                return node, False
            replacement = ast.copy_location(ast.Constant(safe), node)
            if not in_fstring:
                self.replacements.append((*self.span(node), self.encoded(safe, node)))
            return replacement, True
        if (
            isinstance(node, ast.UnaryOp)
            and isinstance(node.op, (ast.UAdd, ast.USub))
            and isinstance(node.operand, ast.Constant)
            and type(node.operand.value) in (int, float, complex)
        ):
            original = ast.literal_eval(node)
            safe, changed = self.scalar(original, keys)
            if changed:
                replacement = ast.copy_location(ast.Constant(safe), node)
                if not in_fstring:
                    self.replacements.append((*self.span(node), self.encoded(safe, node)))
                return replacement, True
            return node, False

        changed = False
        dictionary_keys = (
            [str(key.value) if isinstance(key, ast.Constant) else None for key in node.keys]
            if isinstance(node, ast.Dict)
            else []
        )
        lookup_index, lookup_keywords = (
            _lookup_arguments(node) if isinstance(node, ast.Call) else (None, frozenset())
        )
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for index, child in enumerate(value):
                    if not isinstance(child, ast.AST):
                        continue
                    inherited = keys
                    if isinstance(node, ast.Dict):
                        if field == "values":
                            key = dictionary_keys[index]
                            inherited = (*keys, *((key,) if key is not None else ()))
                        else:
                            inherited = ()
                    if (
                        isinstance(node, ast.Call)
                        and field == "args"
                        and index == lookup_index
                        and not any(isinstance(arg, ast.Starred) for arg in node.args[: index + 1])
                    ):
                        inherited = ()
                    if (
                        isinstance(node, ast.Call)
                        and field == "keywords"
                        and isinstance(child, ast.keyword)
                        and child.arg in lookup_keywords
                    ):
                        inherited = ()
                    value[index], edited = self.visit(child, inherited, in_fstring=in_fstring)
                    changed |= edited
            elif isinstance(value, ast.AST):
                inherited = () if isinstance(node, ast.Subscript) and field == "slice" else keys
                replacement, edited = self.visit(value, inherited, in_fstring=in_fstring)
                setattr(node, field, replacement)
                changed |= edited
        if in_fstring:
            name_field = {
                ast.Name: "id",
                ast.Attribute: "attr",
                ast.arg: "arg",
                ast.keyword: "arg",
            }.get(type(node))
            original_name = getattr(node, name_field, None) if name_field else None
            if original_name is not None:
                safe, count = self.sanitize(original_name, ())
                if safe != original_name:
                    assert name_field is not None
                    setattr(node, name_field, _identifier(safe))
                    self.count += max(count, 1)
                    changed = True
        return node, changed

    def joined(
        self, node: ast.JoinedStr, keys: tuple[str, ...], *, in_fstring: bool
    ) -> tuple[ast.AST, bool]:
        changed = False
        if not in_fstring:
            self.fstrings.append(self.span(node))
        for index, part in enumerate(node.values):
            if isinstance(part, ast.Constant):
                # A slash following an interpolation is a relative template suffix.
                # Keep that context while checking the decoded scalar itself.
                prefix = (
                    "{captureContext}"
                    if index
                    and str(part.value).startswith("/")
                    and isinstance(node.values[index - 1], ast.FormattedValue)
                    else ""
                )
                original = str(part.value)
                # The synthetic template prefix must not increase the real value's
                # length for the keyed policy's minimum-eight-character rule.
                contextual = str(redact_keyed_values(original, keys)) if prefix else original
                safe, count = self.sanitize(prefix + contextual, () if prefix else keys)
                if contextual != original or safe != prefix + contextual:
                    part.value = safe.removeprefix(prefix) if prefix else safe
                    self.count += max(count + (contextual != original), 1)
                    changed = True
            elif isinstance(part, ast.FormattedValue):
                value, edited = self.visit(part.value, keys, in_fstring=True)
                assert isinstance(value, ast.expr)
                part.value = value
                changed |= edited
                if part.format_spec is not None:
                    spec, edited = self.visit(part.format_spec, keys, in_fstring=True)
                    assert isinstance(spec, ast.JoinedStr)
                    part.format_spec = spec
                    changed |= edited
        if changed and not in_fstring:
            self.replacements.append((*self.span(node), ast.unparse(node)))
        return node, changed

    def tokens(self) -> None:
        comments: list[tuple[int, int]] = []

        def flush() -> None:
            if not comments:
                return
            start, end = comments[0][0], comments[-1][1]
            original = self.text[start:end]
            safe, count = self.sanitize(original, ())
            if safe != original:
                if not any(left <= start and end <= right for left, right, _ in self.replacements):
                    self.replacements.append((start, end, safe))
                self.count += max(count, 1)
            comments.clear()

        for token in tokenize.generate_tokens(io.StringIO(self.text, newline=None).readline):
            start = (
                self.position(*token.start, utf8=False)
                if token.start[0] <= len(self.lines)
                else len(self.text)
            )
            end = (
                self.position(*token.end, utf8=False)
                if token.end[0] <= len(self.lines)
                else len(self.text)
            )
            in_fstring = any(left <= start and end <= right for left, right in self.fstrings)
            if token.type == tokenize.COMMENT:
                comments.append((start, end))
            elif token.type not in {
                tokenize.NL,
                tokenize.NEWLINE,
                tokenize.INDENT,
                tokenize.DEDENT,
            }:
                flush()
                if (
                    token.type == tokenize.NAME
                    and not in_fstring
                    and not any(
                        left <= start and end <= right for left, right, _ in self.replacements
                    )
                ):
                    safe, count = self.sanitize(token.string, ())
                    if safe != token.string:
                        self.replacements.append((start, end, _identifier(safe)))
                        self.count += max(count, 1)
        flush()


def _identifier(safe: str) -> str:
    # Source snapshots are evidence substitutes. Keep their lexical structure
    # valid when a pattern-bearing identifier itself contains private material.
    result = re.sub(r"\W", "_", safe)
    return result if result.isidentifier() else "_" + result


def redact_python_source(text: str, sanitize: Sanitize) -> tuple[str, int] | None:
    """Return a safe source copy, or let invalid/oversize Python fail closed upstream."""
    if len(text) > _LIMIT or len(text.encode("utf-8")) > _LIMIT:
        return None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", (SyntaxWarning, DeprecationWarning))
            tree = ast.parse(text)
        pending: list[tuple[ast.AST, int]] = [(tree, 0)]
        visited = 0
        while pending:
            node, depth = pending.pop()
            visited += 1
            if visited > _NODE_LIMIT or depth > _DEPTH_LIMIT:
                return None
            pending.extend((child, depth + 1) for child in ast.iter_child_nodes(node))
    except (SyntaxError, ValueError, RecursionError):
        return None
    source = _Source(text, sanitize, tree)
    source.visit(tree)
    source.tokens()
    result = text
    for start, end, safe in sorted(source.replacements, reverse=True):
        result = result[:start] + safe + result[end:]
    if source.replacements:
        # Do not persist a partially rewritten capture if its lexical structure
        # cannot be represented safely after redaction.
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", (SyntaxWarning, DeprecationWarning))
                ast.parse(result)
        except (SyntaxError, ValueError, RecursionError):
            raise ValueError("cannot sanitize captured Python source") from None
    return result, source.count
