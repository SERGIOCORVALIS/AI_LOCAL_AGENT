from __future__ import annotations

from pydantic import BaseModel


class ChannelMessage(BaseModel):
    channel: str
    user_id: str
    text: str


class VoicePayload(BaseModel):
    channel: str
    transcript: str
    duration_seconds: float


class ApprovalResponse(BaseModel):
    task_id: str
    approved: bool
    reviewer: str
