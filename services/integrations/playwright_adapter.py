from __future__ import annotations

from importlib.util import find_spec
from pathlib import Path
from typing import Any

PLAYWRIGHT_INSTALL_HINT = "python -m playwright install chromium"


class PlaywrightAutomationAdapter:
    """Real Playwright automation boundary with graceful unavailable fallback."""

    def is_package_available(self) -> bool:
        return find_spec("playwright") is not None

    def browsers_installed(self) -> bool:
        if not self.is_package_available():
            return False
        try:
            from playwright.sync_api import sync_playwright
        except Exception:
            return False
        try:
            with sync_playwright() as playwright:
                executable = Path(playwright.chromium.executable_path)
                return executable.exists()
        except Exception:
            return False

    def is_available(self) -> bool:
        return self.is_package_available() and self.browsers_installed()

    def ensure_browsers(self) -> dict[str, Any]:
        """Install Chromium for Playwright when the package is present."""
        if not self.is_package_available():
            return {
                "success": False,
                "summary": "Playwright package is not installed. pip install playwright",
            }
        if self.browsers_installed():
            return {
                "success": True,
                "summary": "Playwright Chromium already installed.",
                "already_installed": True,
            }
        import subprocess
        import sys

        completed = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True,
            text=True,
            check=False,
        )
        ok = completed.returncode == 0 and self.browsers_installed()
        return {
            "success": ok,
            "summary": (
                "Playwright Chromium installed."
                if ok
                else f"Playwright browser install failed: {completed.stderr.strip()}"
            ),
            "exit_code": completed.returncode,
            "hint": PLAYWRIGHT_INSTALL_HINT,
        }

    def open_page(self, url: str, screenshot_path: Path | None = None) -> dict[str, Any]:
        if not self.is_package_available():
            return {
                "success": False,
                "summary": "Playwright package is not installed.",
                "url": url,
                "hint": "pip install 'local-ai-agent[integrations]'",
            }
        if not self.browsers_installed():
            return {
                "success": False,
                "summary": (
                    "Playwright package is installed but Chromium browser is missing."
                ),
                "url": url,
                "hint": PLAYWRIGHT_INSTALL_HINT,
            }
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:  # pragma: no cover - import edge
            return {
                "success": False,
                "summary": f"Playwright import failed: {exc}",
                "url": url,
            }

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page()
                response = page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                title = page.title()
                final_url = page.url
                status = response.status if response is not None else None
                saved: str | None = None
                if screenshot_path is not None:
                    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=str(screenshot_path), full_page=True)
                    saved = str(screenshot_path)
                browser.close()
            return {
                "success": True,
                "summary": f"Opened '{title}' ({status})",
                "url": final_url,
                "title": title,
                "status": status,
                "screenshot": saved,
            }
        except Exception as exc:
            return {
                "success": False,
                "summary": f"Playwright navigation failed: {exc}",
                "url": url,
                "hint": PLAYWRIGHT_INSTALL_HINT,
            }
