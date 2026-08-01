from pathlib import Path

import pytest

from packages.config.env_file import parse_env_file, upsert_env_values


def test_upsert_preserves_comments_and_unrelated_keys(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    path.write_text(
        "# header\nFOO=bar\nLOCAL_AI_AGENT_APP_NAME=old\n",
        encoding="utf-8",
    )
    upsert_env_values(
        path,
        {
            "LOCAL_AI_AGENT_APP_NAME": "new",
            "LOCAL_AI_AGENT_LOG_LEVEL": "INFO",
        },
    )
    text = path.read_text(encoding="utf-8")
    assert "# header" in text
    assert "FOO=bar" in text
    assert "LOCAL_AI_AGENT_APP_NAME=new" in text
    assert "LOCAL_AI_AGENT_LOG_LEVEL=INFO" in text
    parsed = parse_env_file(path)
    assert parsed["LOCAL_AI_AGENT_APP_NAME"] == "new"
    assert parsed["FOO"] == "bar"


def test_upsert_rejects_non_agent_keys(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    with pytest.raises(ValueError, match="non-agent"):
        upsert_env_values(path, {"PATH": "/evil"})
