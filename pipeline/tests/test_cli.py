from typer.testing import CliRunner

from atlas.cli import app
from tests.conftest import FIXTURES


def test_version_command_prints_version():
    result = CliRunner().invoke(app, ["version"])
    assert result.exit_code == 0
    assert "2.0.0" in result.stdout


def test_eleven_real_fixtures_present():
    assert len(list((FIXTURES / "thaijo_md").glob("*.md"))) == 11
