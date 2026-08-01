from __future__ import annotations

from importlib.util import find_spec
from typing import Any

from services.integrations.playwright_adapter import (
    PLAYWRIGHT_INSTALL_HINT,
    PlaywrightAutomationAdapter,
)
from services.llm import AgentModelConfig, OllamaClient, ollama_agents_readiness
from services.llm.models import model_is_available
from services.memory.embeddings import EmbeddingService
from services.perception.stt import SpeechToText
from services.perception.vision import VisionAnalyzer


def ocr_available() -> bool:
    if find_spec("pytesseract") is None or find_spec("PIL") is None:
        return False
    try:
        import pytesseract

        # get_tesseract_version raises if binary is missing.
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def stt_backend_name(stt: SpeechToText | None = None) -> str:
    probe = stt or SpeechToText()
    if find_spec("faster_whisper") is not None:
        return "faster_whisper"
    if find_spec("whisper") is not None:
        return "whisper"
    if probe.is_available():
        return "available"
    return "none"


def vlm_readiness(
    ollama_client: OllamaClient | None = None,
    vision_model: str | None = None,
) -> dict[str, Any]:
    if ollama_client is None:
        return {
            "available": False,
            "backend": "ollama",
            "model": vision_model,
            "hint": "Ollama client not configured.",
        }
    online = ollama_client.ping()
    if not online:
        return {
            "available": False,
            "backend": "ollama",
            "model": vision_model,
            "hint": "Ollama is offline; start it and pull a vision model.",
        }
    if vision_model:
        tags = ollama_client.list_models()
        if not model_is_available(vision_model, tags):
            return {
                "available": False,
                "backend": "ollama",
                "model": vision_model,
                "hint": (
                    f"Ollama online but model '{vision_model}' not found. "
                    f"ollama pull {vision_model}"
                ),
            }
    return {
        "available": True,
        "backend": "ollama",
        "model": vision_model,
        "hint": None,
    }


def perception_readiness(
    *,
    embedder: EmbeddingService | None = None,
    ollama_client: OllamaClient | None = None,
    vision_model: str | None = None,
    agents: AgentModelConfig | None = None,
) -> dict[str, Any]:
    """Snapshot of optional perception/automation backends for status/doctor."""
    stt = SpeechToText()
    playwright = PlaywrightAutomationAdapter()
    stt_ok = stt.is_available()
    ocr_ok = ocr_available()
    package_ok = playwright.is_package_available()
    browsers_ok = playwright.browsers_installed() if package_ok else False
    embedding_info: dict[str, Any] = {
        "backend": "hashed",
        "dimensions": 64,
        "model": None,
        "hint": "Start Ollama and pull an embed model (e.g. nomic-embed-text).",
    }
    if embedder is not None:
        embedder.ensure_ready()
        embedding_info = {
            "backend": embedder.backend,
            "dimensions": embedder.dimensions,
            "model": embedder.model,
            "hint": None
            if embedder.backend == "ollama"
            else "Ollama embeddings unavailable; using hashed fallback.",
        }

    agent_config = agents
    if agent_config is None and vision_model is not None:
        agent_config = AgentModelConfig(vision=vision_model)
    elif agent_config is None:
        agent_config = AgentModelConfig()

    return {
        "stt": {
            "available": stt_ok,
            "backend": stt_backend_name(stt),
            "hint": None
            if stt_ok
            else "pip install 'local-ai-agent[integrations]' (faster-whisper)",
        },
        "ocr": {
            "available": ocr_ok,
            "backend": "pytesseract" if ocr_ok else "none",
            "hint": None
            if ocr_ok
            else (
                "pip install 'local-ai-agent[perception]' and install Tesseract OCR "
                "system binary"
            ),
        },
        "vlm": vlm_readiness(ollama_client, vision_model or agent_config.vision),
        "playwright": {
            "package": package_ok,
            "browsers": browsers_ok,
            "available": package_ok and browsers_ok,
            "hint": None
            if (package_ok and browsers_ok)
            else (
                PLAYWRIGHT_INSTALL_HINT
                if package_ok
                else "pip install 'local-ai-agent[integrations]'"
            ),
        },
        "embeddings": embedding_info,
        "ollama_agents": ollama_agents_readiness(ollama_client, agent_config),
        "vision_analyzer": VisionAnalyzer.__name__,
    }
