"""Top-level ReproLLM CLI application."""

import typer

from reprollm import __version__
from reprollm.cli import audit, schema

app = typer.Typer(
    name="reprollm",
    help="Make LLM experiments reproducible.",
    no_args_is_help=True,
)

app.add_typer(schema.app, name="schema")
app.command()(audit.audit)


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


if __name__ == "__main__":
    app()
