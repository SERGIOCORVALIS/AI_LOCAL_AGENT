from pathlib import Path
from unittest.mock import MagicMock, patch

from services.channels import ChannelGateway
from services.perception.stt import STT_UNAVAILABLE, SpeechToText


def test_channel_gateway_supports_text_voice_and_approval() -> None:
    gateway = ChannelGateway()

    message = gateway.ingest_text("cli", "user-1", "cleanup downloads")
    voice = gateway.ingest_voice("telegram", "run audit", 1.5)
    approval = gateway.record_approval("task-1", "operator", True)

    assert message.channel == "cli"
    assert voice.transcript == "run audit"
    assert voice.source == "transcript"
    assert approval.approved is True


def test_channel_gateway_transcribes_audio_via_stt(tmp_path: Path) -> None:
    audio = tmp_path / "clip.wav"
    audio.write_bytes(b"RIFF")
    stt = MagicMock(spec=SpeechToText)
    stt.transcribe.return_value = "open downloads folder"
    gateway = ChannelGateway(stt=stt)
    voice = gateway.ingest_voice("telegram", transcript="", audio_path=audio)
    assert voice.transcript == "open downloads folder"
    assert voice.source == "stt"
    stt.transcribe.assert_called_once()


def test_speech_to_text_returns_unavailable_without_backends(tmp_path: Path) -> None:
    missing = tmp_path / "missing.wav"
    assert SpeechToText().transcribe(missing) == STT_UNAVAILABLE


def test_speech_to_text_reports_availability_flag() -> None:
    assert isinstance(SpeechToText().is_available(), bool)


def test_speech_to_text_uses_injected_backend_via_mock(tmp_path: Path) -> None:
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"RIFF")
    stt = SpeechToText()
    with patch.object(stt, "_transcribe_faster_whisper", return_value="hello world"):
        assert stt.transcribe(audio) == "hello world"


def test_speech_to_text_falls_back_to_openai_whisper_path(tmp_path: Path) -> None:
    audio = tmp_path / "b.wav"
    audio.write_bytes(b"RIFF")
    stt = SpeechToText()
    with (
        patch.object(stt, "_transcribe_faster_whisper", return_value=None),
        patch.object(stt, "_transcribe_openai_whisper", return_value="whisper text"),
    ):
        assert stt.transcribe(audio) == "whisper text"
