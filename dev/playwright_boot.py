"""Shared Playwright boot helpers for LSP regression suites."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

APP_URL = "/index.html?regression=1&massiveSuite=1"

ENGINE_WAIT_JS = """() => window.ZHLEngine && window.VPMEngine
  && typeof window.ZHLEngine.calculate === 'function'
  && typeof window.VPMEngine.calculate === 'function'
  && typeof window.ZhlEngineBundle !== 'undefined'"""


def boot_app_page(page, base_url: str, *, extra_wait_ms: int = 2000) -> None:
    """Navigate to index.html in headless test mode and wait for engines."""
    page.goto(f"{base_url.rstrip('/')}{APP_URL}", wait_until="domcontentloaded", timeout=180000)
    page.wait_for_function(ENGINE_WAIT_JS, timeout=180000)
    page.evaluate("() => { window._zhlHeadless = true; }")
    if extra_wait_ms > 0:
        page.wait_for_timeout(extra_wait_ms)
