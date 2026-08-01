"""Luxury admin panel assets and HTML renderer."""

from __future__ import annotations

from pathlib import Path

from packages.config import Settings

ADMIN_DIR = Path(__file__).resolve().parent
STATIC_DIR = ADMIN_DIR


def render_admin_html(settings: Settings) -> str:
    template = (ADMIN_DIR / "panel.html").read_text(encoding="utf-8")
    title = settings.admin_ui_title.replace("&", "&amp;").replace("<", "&lt;").replace(
        ">", "&gt;"
    )
    return template.replace("{{ADMIN_TITLE}}", title)


__all__ = ["ADMIN_DIR", "STATIC_DIR", "render_admin_html"]
