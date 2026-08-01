from __future__ import annotations

import json
from pathlib import Path

from packages.channels import ApprovalResponse, ChannelMessage, VoicePayload
from services.perception.stt import STT_UNAVAILABLE, SpeechToText


class ChannelGateway:
    """Unified message intake with durable approval recording."""

    def __init__(
        self,
        approval_log_path: Path | None = None,
        stt: SpeechToText | None = None,
    ) -> None:
        self._approval_log_path = approval_log_path or Path(
            "./runtime/approvals/events.jsonl"
        )
        self._stt = stt or SpeechToText()

    def ingest_text(self, channel: str, user_id: str, text: str) -> ChannelMessage:
        return ChannelMessage(channel=channel, user_id=user_id, text=text.strip())

    def ingest_voice(
        self,
        channel: str,
        transcript: str = "",
        duration_seconds: float = 0.0,
        *,
        audio_path: Path | str | None = None,
        language: str | None = None,
    ) -> VoicePayload:
        cleaned = transcript.strip()
        source = "transcript"
        if audio_path is not None and not cleaned:
            path = Path(audio_path)
            cleaned = self._stt.transcribe(path, language=language).strip()
            source = "stt"
            if not cleaned:
                cleaned = STT_UNAVAILABLE
        return VoicePayload(
            channel=channel,
            transcript=cleaned,
            duration_seconds=duration_seconds,
            source=source,
            audio_path=str(audio_path) if audio_path is not None else None,
        )

    def record_approval(self, task_id: str, reviewer: str, approved: bool) -> ApprovalResponse:
        response = ApprovalResponse(
            task_id=task_id,
            reviewer=reviewer,
            approved=approved,
        )
        self._approval_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self._approval_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(response.model_dump(mode="json"), ensure_ascii=True) + "\n")
        return response

    def list_approvals(self, limit: int = 20) -> list[ApprovalResponse]:
        if not self._approval_log_path.exists():
            return []
        rows = self._approval_log_path.read_text(encoding="utf-8").splitlines()
        items = [
            ApprovalResponse.model_validate(json.loads(row))
            for row in rows[-limit:]
            if row.strip()
        ]
        return list(reversed(items))
