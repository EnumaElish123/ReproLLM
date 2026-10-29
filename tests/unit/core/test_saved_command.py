"""Portable saved command strings are a small non-shell language."""

import pytest

from reprollm.core.errors import UserError


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("python train.py --epochs 3", ["python", "train.py", "--epochs", "3"]),
        ("python 'two words.py' '' \"a:b#c\"", ["python", "two words.py", "", "a:b#c"]),
        ("python -c 'print(\"a;b\")'", ["python", "-c", 'print("a;b")']),
        (
            "'C:\\Program Files\\Python\\python.exe' 'C:\\work\\train.py'",
            [r"C:\Program Files\Python\python.exe", r"C:\work\train.py"],
        ),
        (
            '"C:/Program Files/Python/python.exe" train.py',
            ["C:/Program Files/Python/python.exe", "train.py"],
        ),
        (r"python two\ words.py", ["python", "two words.py"]),
        ("python '$HOME' '`literal`' '*.txt' '|'", ["python", "$HOME", "`literal`", "*.txt", "|"]),
    ],
    ids=[
        "plain",
        "quoted-values",
        "quoted-python",
        "windows-backslashes",
        "windows-slashes",
        "escaped-space",
        "literal-shell-symbols",
    ],
)
def test_saved_tokens(command: str, expected: list[str]) -> None:
    from reprollm.core.saved_command import parse_saved_command

    assert parse_saved_command(command) == expected


@pytest.mark.parametrize(
    "command",
    [
        "",
        " ",
        "'' arg",
        "python 'broken",
        "python x | other",
        "python x&&other",
        "python x > out",
        "python x;other",
        "python x\nother",
        "python x\targ",
        "python $HOME/x",
        'python "$HOME/x"',
        "python `whoami`",
        "NAME=value python x",
        "python *.py",
        "python ~/train.py",
        "python {a,b}.py",
        'python "\\$HOME"',
        "python x # comment",
        r"python C:\work\train.py",
        "python \x00x",
        "python \u202ex",
        "python \u200bx",
    ],
    ids=[
        "empty",
        "blank",
        "empty-executable",
        "bad-quote",
        "pipe",
        "and",
        "redirect",
        "semicolon",
        "newline",
        "tab",
        "variable",
        "double-quoted-variable",
        "substitution",
        "assignment",
        "glob",
        "tilde",
        "braces",
        "escaped-double-dollar",
        "comment",
        "windows-unquoted",
        "nul",
        "bidi-control",
        "zero-width-format",
    ],
)
def test_unsupported_saved_syntax_has_private_actionable_error(command: str) -> None:
    from reprollm.core.saved_command import parse_saved_command

    with pytest.raises(UserError, match="execution.command"):
        parse_saved_command(command)
