from __future__ import annotations

import struct
from importlib.util import find_spec
from pathlib import Path

from packages.perception import ScreenshotAnalysis
from services.llm import OLLAMA_UNAVAILABLE, OllamaClient


class VisionAnalyzer:
    """Image inspector with header parsing, optional OCR, and Ollama VLM."""

    def __init__(
        self,
        ollama_client: OllamaClient | None = None,
        vision_model: str = "gemma4",
    ) -> None:
        self._ollama = ollama_client
        self._vision_model = vision_model

    def inspect_image(self, path: Path) -> ScreenshotAnalysis:
        if not path.exists():
            raise FileNotFoundError(path)
        payload = path.read_bytes()
        width, height, kind = self._read_dimensions(payload)
        labels = self._heuristic_labels(path, width, height, len(payload))
        ocr_text = self._ocr_text(path)
        vlm_text = self._vlm_text(path)
        parts = [
            f"Image analysis for {path.name}: format={kind}",
            f"size={width}x{height}",
            f"bytes={len(payload)}",
            f"labels={', '.join(labels)}",
        ]
        if ocr_text:
            parts.append(f"ocr={ocr_text[:200]}")
            labels.append("ocr")
        if vlm_text and vlm_text != OLLAMA_UNAVAILABLE:
            parts.append(f"vlm={vlm_text[:300]}")
            labels.append("vlm")
        elif self._ollama is not None:
            parts.append(f"vlm={OLLAMA_UNAVAILABLE}")
        summary = "; ".join(parts) + "."
        return ScreenshotAnalysis(
            path=str(path),
            width=width,
            height=height,
            summary=summary,
            labels=labels,
        )

    def _vlm_text(self, path: Path) -> str | None:
        if self._ollama is None:
            return None
        return self._ollama.generate_with_image(
            self._vision_model,
            "Describe visible UI/text in this image for local automation. Be concise.",
            path,
        )

    def _ocr_text(self, path: Path) -> str | None:
        if find_spec("pytesseract") is None or find_spec("PIL") is None:
            return None
        try:
            import pytesseract  # type: ignore[import-not-found]
            from PIL import Image
        except Exception:
            return None
        try:
            pytesseract.get_tesseract_version()
        except Exception:
            return None
        try:
            return str(pytesseract.image_to_string(Image.open(path))).strip() or None
        except Exception:
            return None

    @staticmethod
    def ocr_available() -> bool:
        from services.perception.readiness import ocr_available

        return ocr_available()

    def _read_dimensions(self, payload: bytes) -> tuple[int, int, str]:
        if payload.startswith(b"\x89PNG\r\n\x1a\n") and len(payload) >= 24:
            width, height = struct.unpack(">II", payload[16:24])
            return width, height, "png"
        if payload.startswith(b"\xff\xd8"):
            return (*self._jpeg_dimensions(payload), "jpeg")
        if payload[:6] in {b"GIF87a", b"GIF89a"} and len(payload) >= 10:
            width, height = struct.unpack("<HH", payload[6:10])
            return width, height, "gif"
        return 0, 0, "unknown"

    def _jpeg_dimensions(self, payload: bytes) -> tuple[int, int]:
        index = 2
        while index + 9 < len(payload):
            if payload[index] != 0xFF:
                index += 1
                continue
            marker = payload[index + 1]
            if marker in {0xC0, 0xC1, 0xC2}:
                height, width = struct.unpack(">HH", payload[index + 5 : index + 9])
                return width, height
            length = struct.unpack(">H", payload[index + 2 : index + 4])[0]
            index += 2 + length
        return 0, 0

    def _heuristic_labels(
        self,
        path: Path,
        width: int,
        height: int,
        size_bytes: int,
    ) -> list[str]:
        labels: list[str] = []
        suffix = path.suffix.lower()
        if suffix:
            labels.append(suffix.lstrip("."))
        if width >= 1200 or height >= 800:
            labels.append("screenshot-like")
        if size_bytes < 2_048:
            labels.append("tiny")
        if not labels:
            labels.append("unclassified")
        return labels
