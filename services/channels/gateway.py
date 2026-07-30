from __future__ import annotations

from packages.channels import ApprovalResponse, ChannelMessage, VoicePayload


class ChannelGateway:
    """Unified message intake for CLI, Telegram, and voice adapters."""

    def ingest_text(self, channel: str, user_id: str, text: str) -> ChannelMessage:
        return ChannelMessage(channel=channel, user_id=user_id, text=text)

    def ingest_voice(self, channel: str, transcript: str, duration_seconds: float) -> VoicePayload:
        return VoicePayload(
            channel=channel,
            transcript=transcript,
            duration_seconds=duration_seconds,
        )

    def record_approval(self, task_id: str, reviewer: str, approved: bool) -> ApprovalResponse:
        return ApprovalResponse(task_id=task_id, reviewer=reviewer, approved=approved)
