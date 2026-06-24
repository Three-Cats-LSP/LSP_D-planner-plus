"""Shared Playwright boot helpers for LSP regression suites."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

APP_URL = "/index.html?regression=1&massiveSuite=1"

_ENGINE_READY_CHECK = (
    "window._lspEngineReady === true"
    " && window.ZHLEngine && window.VPMEngine"
    " && typeof window.ZHLEngine.calculate === 'function'"
    " && typeof window.VPMEngine.calculate === 'function'"
    " && typeof window.ZhlEngineBundle !== 'undefined'"
)

ENGINE_WAIT_JS = (
    "() => {"
    " if (window._lspEngineError) {"
    "   throw new Error('Engine boot failed: ' + window._lspEngineError);"
    " }"
    f" return ({_ENGINE_READY_CHECK});"
    "}"
)

ENGINE_WAIT_CCR_JS = (
    "() => {"
    " if (window._lspEngineError) {"
    "   throw new Error('Engine boot failed: ' + window._lspEngineError);"
    " }"
    f" return ({_ENGINE_READY_CHECK}"
    " && typeof window.validateCcrCalculationInputs === 'function');"
    "}"
)


def boot_app_page(page, base_url: str, *, require_ccr: bool = False) -> None:
    """Navigate to index.html in headless test mode and wait for engines."""
    wait_js = ENGINE_WAIT_CCR_JS if require_ccr else ENGINE_WAIT_JS
    page.goto(f"{base_url.rstrip('/')}{APP_URL}", wait_until="domcontentloaded", timeout=180000)
    page.wait_for_function(wait_js, timeout=180000)
    page.evaluate("() => { window._zhlHeadless = true; }")


def ensure_app_engines(page, *, require_ccr: bool = False, timeout: int = 60000) -> None:
    """Re-check engine globals between evaluations (e.g. after long Playwright steps)."""
    wait_js = ENGINE_WAIT_CCR_JS if require_ccr else ENGINE_WAIT_JS
    page.wait_for_function(wait_js, timeout=timeout)


def wait_app_engines(page, *, require_ccr: bool = False, timeout: int = 180000) -> None:
    """Alias kept for audit/issue #3 guards and legacy harness callers."""
    ensure_app_engines(page, require_ccr=require_ccr, timeout=timeout)
