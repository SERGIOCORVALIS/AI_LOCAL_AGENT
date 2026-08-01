from __future__ import annotations

from importlib.util import find_spec
from pathlib import Path

STT_UNAVAILABLE = "stt_unavailable"


class SpeechToText:
    """Local speech-to-text with optional Whisper backends."""

    def is_available(self) -> bool:
        return find_spec("faster_whisper") is not None or find_spec("whisper") is not None

    def transcribe(self, audio_path: Path, language: str | None = None) -> str:
        """Transcribe audio. language=None enables auto-detect (RU/EN/...)."""
        if not audio_path.exists():
            return STT_UNAVAILABLE
        text = self._transcribe_faster_whisper(audio_path, language)
        if text is not None:
            return text
        text = self._transcribe_openai_whisper(audio_path, language)
        if text is not None:
            return text
        return STT_UNAVAILABLE

    def _transcribe_faster_whisper(
        self,
        audio_path: Path,
        language: str | None,
    ) -> str | None:
        if find_spec("faster_whisper") is None:
            return None
        try:
            from faster_whisper import WhisperModel
        except Exception:
            return None
        try:
            model = WhisperModel("base", device="cpu", compute_type="int8")
            segments, _info = model.transcribe(str(audio_path), language=language)
            text = " ".join(segment.text.strip() for segment in segments).strip()
            return text or None
        except Exception:
            return None

    def _transcribe_openai_whisper(
        self,
        audio_path: Path,
        language: str | None,
    ) -> str | None:
        if find_spec("whisper") is None:
            return None
        try:
            import whisper  # type: ignore[import-not-found]
        except Exception:
            return None
        try:
            model = whisper.load_model("base")
            result = model.transcribe(str(audio_path), language=language)
            text = str(result.get("text", "")).strip()
            return text or None
        except Exception:
            return None
