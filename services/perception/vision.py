from __future__ import annotations

from pathlib import Path

from packages.perception import ScreenshotAnalysis


class VisionAnalyzer:
    """Placeholder screenshot analyzer for future OCR/UI grounding."""

    def inspect_image(self, path: Path) -> ScreenshotAnalysis:
        if not path.exists():
            raise FileNotFoundError(path)
        payload = path.read_bytes()
        return ScreenshotAnalysis(
            path=str(path),
            width=0,
            height=0,
            summary=f"Binary image captured for analysis ({len(payload)} bytes).",
        )
