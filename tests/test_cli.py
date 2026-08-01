from pathlib import Path
from unittest.mock import MagicMock

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
    from unittest.mock import patch

    from services.quality.evaluator import QualityReport

    fake = QualityReport(
        lint_ready=True,
        typed_contracts_ready=True,
        tests_ready=True,
        audit_ready=True,
        details={"mocked": True},
    )
    with (
        patch("apps.cli.main.QualityEvaluator") as evaluator_cls,
        patch("apps.cli.main.build_memory_backend") as memory_cls,
        patch(
            "apps.cli.main.perception_readiness",
            return_value={"stt": {"available": False}},
        ),
    ):
        evaluator_cls.return_value.evaluate.return_value = fake
        memory_cls.return_value = MagicMock(embedder=None)
        result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert '"lint_ready": true' in result.stdout
    evaluator_cls.return_value.evaluate.assert_called_once()


def test_approve_command_missing_task() -> None:
    result = runner.invoke(
        app,
        ["approve", "00000000-0000-0000-0000-000000000000", "--approved"],
    )
    assert result.exit_code == 0
    assert "was not found" in result.stdout


def test_voice_command_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.ogg"
    result = runner.invoke(app, ["voice", str(missing)])
    assert result.exit_code != 0


def test_voice_command_transcribes_with_gateway_mock(tmp_path: Path) -> None:
    from unittest.mock import MagicMock, patch

    audio = tmp_path / "clip.ogg"
    audio.write_bytes(b"OggS")
    fake = MagicMock()
    fake.model_dump_json.return_value = '{"transcript":"hello","source":"stt"}'
    with patch("apps.cli.main.ChannelGateway") as gateway_cls:
        gateway_cls.return_value.ingest_voice.return_value = fake
        result = runner.invoke(app, ["voice", str(audio), "--channel", "cli"])
    assert result.exit_code == 0
    assert "hello" in result.stdout


def test_ollama_check_command() -> None:
    from unittest.mock import patch

    from services.llm import AgentModelConfig, ResolvedAgents

    configured = AgentModelConfig(
        primary="gemma4",
        router="gemma4",
        vision="gemma4",
        embed="nomic-embed-text",
    )
    resolved = ResolvedAgents(
        configured=configured,
        resolved=AgentModelConfig(
            primary="gemma4:e4b-it-q4_K_M",
            router="gemma4:e4b-it-q4_K_M",
            vision="gemma4:e4b-it-q4_K_M",
            embed="nomic-embed-text:latest",
        ),
        installed=["gemma4:e4b-it-q4_K_M", "nomic-embed-text:latest"],
        online=True,
    )
    readiness = {
        "online": True,
        "installed": resolved.installed,
        "slots": {
            "primary": {"available": True},
            "router": {"available": True},
            "vision": {"available": True},
            "embed": {"available": True},
        },
        "roles": {"coder": {"available": True}},
        "all_required_available": True,
        "hint": None,
    }
    with (
        patch("apps.cli.main.OllamaClient") as client_cls,
        patch("apps.cli.main.resolve_agents", return_value=resolved),
        patch("apps.cli.main.ollama_agents_readiness", return_value=readiness),
    ):
        client_cls.return_value = MagicMock()
        result = runner.invoke(app, ["ollama-check"])
    assert result.exit_code == 0
    assert "gemma4:e4b-it-q4_K_M" in result.stdout
    assert '"all_required_available": true' in result.stdout


def test_playwright_setup_command() -> None:
    from unittest.mock import patch

    with patch("apps.cli.main.PlaywrightAutomationAdapter") as adapter_cls:
        adapter_cls.return_value.ensure_browsers.return_value = {
            "success": True,
            "summary": "ok",
            "already_installed": True,
        }
        result = runner.invoke(app, ["playwright-setup"])
    assert result.exit_code == 0
    assert "already_installed" in result.stdout


def test_playwright_setup_command_fails() -> None:
    from unittest.mock import patch

    with patch("apps.cli.main.PlaywrightAutomationAdapter") as adapter_cls:
        adapter_cls.return_value.ensure_browsers.return_value = {
            "success": False,
            "summary": "missing package",
        }
        result = runner.invoke(app, ["playwright-setup"])
    assert result.exit_code == 1
