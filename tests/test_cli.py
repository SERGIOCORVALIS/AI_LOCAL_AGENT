from typer.testing import CliRunner

from apps.cli.main import app

runner = CliRunner()


def test_status_command() -> None:
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "local-ai-agent" in result.stdout


def test_run_command() -> None:
    result = runner.invoke(app, ["run", "Bootstrap", "Exercise the runtime"])
    assert result.exit_code == 0
    assert '"success": true' in result.stdout


def test_doctor_command() -> None:
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert '"lint_ready": true' in result.stdout
