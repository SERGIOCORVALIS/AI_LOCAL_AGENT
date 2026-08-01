from __future__ import annotations

from unittest.mock import MagicMock, patch

from services.memory.embeddings import EmbeddingService
from services.perception.readiness import (
    ocr_available,
    perception_readiness,
    stt_backend_name,
)
from services.perception.stt import SpeechToText


def test_perception_readiness_reports_backends() -> None:
    embedder = MagicMock(spec=EmbeddingService)
    embedder.backend = "hashed"
    embedder.dimensions = 64
    embedder.model = "nomic-embed-text"
    payload = perception_readiness(embedder=embedder)
    assert "stt" in payload
    assert "ocr" in payload
    assert "playwright" in payload
    assert payload["embeddings"]["backend"] == "hashed"
    assert payload["embeddings"]["dimensions"] == 64
    embedder.ensure_ready.assert_called_once()


def test_perception_readiness_without_embedder_and_hints() -> None:
    with (
        patch("services.perception.readiness.SpeechToText") as stt_cls,
        patch("services.perception.readiness.ocr_available", return_value=False),
        patch("services.perception.readiness.PlaywrightAutomationAdapter") as pw_cls,
        patch(
            "services.perception.readiness.stt_backend_name",
            return_value="none",
        ),
    ):
        stt_cls.return_value.is_available.return_value = False
        pw = pw_cls.return_value
        pw.is_package_available.return_value = True
        pw.browsers_installed.return_value = False
        payload = perception_readiness()
    assert payload["embeddings"]["backend"] == "hashed"
    assert payload["stt"]["available"] is False
    assert "faster-whisper" in (payload["stt"]["hint"] or "")
    assert payload["ocr"]["available"] is False
    assert "Tesseract" in (payload["ocr"]["hint"] or "")
    assert payload["playwright"]["package"] is True
    assert payload["playwright"]["browsers"] is False
    assert "playwright install" in (payload["playwright"]["hint"] or "")


def test_perception_readiness_ready_backends() -> None:
    embedder = MagicMock(spec=EmbeddingService)
    embedder.backend = "ollama"
    embedder.dimensions = 768
    embedder.model = "nomic-embed-text"
    ollama = MagicMock()
    ollama.ping.return_value = True
    ollama.list_models.return_value = ["gemma4:e4b-it-q4_K_M", "nomic-embed-text:latest"]
    with (
        patch("services.perception.readiness.SpeechToText") as stt_cls,
        patch("services.perception.readiness.ocr_available", return_value=True),
        patch("services.perception.readiness.PlaywrightAutomationAdapter") as pw_cls,
        patch(
            "services.perception.readiness.stt_backend_name",
            return_value="faster_whisper",
        ),
    ):
        stt_cls.return_value.is_available.return_value = True
        pw = pw_cls.return_value
        pw.is_package_available.return_value = True
        pw.browsers_installed.return_value = True
        payload = perception_readiness(
            embedder=embedder,
            ollama_client=ollama,
            vision_model="gemma4",
        )
    assert payload["stt"]["hint"] is None
    assert payload["ocr"]["backend"] == "pytesseract"
    assert payload["playwright"]["available"] is True
    assert payload["embeddings"]["hint"] is None
    assert payload["embeddings"]["dimensions"] == 768
    assert payload["vlm"]["available"] is True
    assert payload["ollama_agents"]["slots"]["primary"]["available"] is True
    assert payload["ollama_agents"]["roles"]["coder"]["available"] is True


def test_vlm_readiness_reports_offline() -> None:
    from services.perception.readiness import vlm_readiness

    assert vlm_readiness(None)["available"] is False
    ollama = MagicMock()
    ollama.ping.return_value = False
    assert vlm_readiness(ollama, "vision")["available"] is False
    ollama.ping.return_value = True
    ollama.list_models.return_value = ["other:latest"]
    assert vlm_readiness(ollama, "vision")["available"] is False


def test_ocr_available_paths() -> None:
    with patch("services.perception.readiness.find_spec", return_value=None):
        assert ocr_available() is False
    fake_module = MagicMock()
    fake_module.get_tesseract_version = MagicMock(return_value="5.0")
    with (
        patch(
            "services.perception.readiness.find_spec",
            side_effect=lambda name: object() if name in {"pytesseract", "PIL"} else None,
        ),
        patch.dict("sys.modules", {"pytesseract": fake_module}),
    ):
        assert ocr_available() is True
        fake_module.get_tesseract_version = MagicMock(side_effect=RuntimeError("missing"))
        assert ocr_available() is False


def test_stt_backend_name_branches() -> None:
    stt = MagicMock(spec=SpeechToText)
    stt.is_available.return_value = False
    with patch("services.perception.readiness.find_spec", return_value=None):
        assert stt_backend_name(stt) == "none"
    with patch(
        "services.perception.readiness.find_spec",
        side_effect=lambda name: object() if name == "faster_whisper" else None,
    ):
        assert stt_backend_name(stt) == "faster_whisper"
    with patch(
        "services.perception.readiness.find_spec",
        side_effect=lambda name: object() if name == "whisper" else None,
    ):
        assert stt_backend_name(stt) == "whisper"
    stt.is_available.return_value = True
    with patch("services.perception.readiness.find_spec", return_value=None):
        assert stt_backend_name(stt) == "available"


def test_status_endpoint_includes_perception() -> None:
    from fastapi.testclient import TestClient

    from apps.api.main import app

    with patch(
        "services.perception.readiness.perception_readiness",
        return_value={"stt": {"available": False}},
    ):
        response = TestClient(app).get("/status")
    assert response.status_code == 200
    assert "perception" in response.json()
