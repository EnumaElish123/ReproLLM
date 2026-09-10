"""Top-level ReproLLM CLI application.

Exit-code contract (D-11, M2F-T02): 0 success / below threshold, 1 findings
or drift at/above threshold, 2 user-fixable error (one-line message), 3
internal error (traceback only with ``-v``). No default output ever exposes a
traceback.
"""

import traceback

import typer

from reprollm import __version__
from reprollm.cli import audit, doctor, profiles, schema
from reprollm.cli import init as init_cmd
from reprollm.core.errors import ReproLLMError, UserError

app = typer.Typer(
    name="reprollm",
    help="Make LLM experiments reproducible.",
    no_args_is_help=True,
)

app.add_typer(schema.app, name="schema")
app.add_typer(profiles.app, name="profiles")
app.command()(audit.audit)
app.command()(doctor.doctor)
app.command(name="init")(init_cmd.init)

#: Global CLI flags set by the callback before any command runs; read by the
#: exception boundary in :func:`cli` (verbose → internal tracebacks).
STATE = {"verbose": False, "quiet": False}


def cli() -> None:
    """Console-script entry point: the single exit-code/traceback boundary."""
    try:
        app()
    except typer.Exit:
        raise
    except UserError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise SystemExit(exc.exit_code) from None
    except ReproLLMError as exc:
        typer.echo(f"internal error: {exc}", err=True)
        raise SystemExit(exc.exit_code) from None
    except KeyboardInterrupt:  # pragma: no cover - interactive interrupt
        raise SystemExit(130) from None
    except Exception as exc:
        if STATE["verbose"]:
            typer.echo(traceback.format_exc(), err=True)
        typer.echo(f"internal error: unexpected {type(exc).__name__}: {exc}", err=True)
        raise SystemExit(3) from None


def _version_callback(value: bool | None) -> None:
    if value:
        typer.echo(f"reprollm {__version__}")
        raise typer.Exit


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Print the reprollm version and exit.",
    ),
    no_color: bool = typer.Option(False, "--no-color", help="Disable colored output."),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable verbose output."),
    quiet: bool = typer.Option(False, "-q", "--quiet", help="Suppress non-essential output."),
) -> None:
    """Make LLM experiments reproducible.

    Record and audit the state that makes LLM research comparable:
    model revisions, tokenizer and chat-template hashes, prompt hashes,
    generation parameters, judge configurations, and runtime truth.
    """
    STATE["verbose"] = verbose
    STATE["quiet"] = quiet


if __name__ == "__main__":
    app()
