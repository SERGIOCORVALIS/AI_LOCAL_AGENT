from services.channels import ChannelGateway


def test_channel_gateway_supports_text_voice_and_approval() -> None:
    gateway = ChannelGateway()

    message = gateway.ingest_text("cli", "user-1", "cleanup downloads")
    voice = gateway.ingest_voice("telegram", "run audit", 1.5)
    approval = gateway.record_approval("task-1", "operator", True)

    assert message.channel == "cli"
    assert voice.transcript == "run audit"
    assert approval.approved is True
