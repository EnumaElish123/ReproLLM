"""Version consistency tests."""

from typer.testing import CliRunner

from reprollm import __version__
from reprollm.cli.main import app


def test_version_flag_prints_package_version() -> None:
    result = CliRunner().invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"reprollm {__version__}" in result.output


def test_help_mentions_purpose() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "reprollm" in result.output
