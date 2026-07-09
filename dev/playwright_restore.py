"""Playwright page-state restore helpers shared by shell regressions."""
from __future__ import annotations

from typing import Any

from tools.seven_lens_browser_trace import (
    SETTINGS_SAVE_DEBOUNCE_WAIT_MS,
    _apply_storage_snapshot,
    _invoke_restore_fields,
    _restore_session_begin,
    _restore_session_end,
    _sync_dom_from_storage,
    _verify_persisted_consistency,
    _wait_settings_debounce_contract,
)

CAPTURE_PROBE_STATE_JS = r"""
() => ({
  navSection: 'buh',
  depth: document.getElementById('tecDepth')?.value || '40',
  bt: document.getElementById('tecBT')?.value || '30',
  hadResults: document.getElementById('resultsPanel')?.classList.contains('has-results') === true,
  activeId: document.activeElement?.id || '',
  localStorage: Object.fromEntries(Object.keys(localStorage).map(k => [k, localStorage.getItem(k)])),
  sessionStorage: Object.fromEntries(Object.keys(sessionStorage).map(k => [k, sessionStorage.getItem(k)])),
})
"""

RESTORE_DOM_STATE_JS = r"""
(before) => {
  if (!before) return false;
  setMainNav(before.navSection || 'buh');
  if (before.depth != null) {
    const depthEl = document.getElementById('tecDepth');
    if (depthEl) depthEl.value = String(before.depth);
  }
  if (before.bt != null) {
    const btEl = document.getElementById('tecBT');
    if (btEl) btEl.value = String(before.bt);
  }
  if (typeof _syncTecDepthBtSteppers === 'function') _syncTecDepthBtSteppers();
  if (before.hadResults) {
    if (typeof runDecoSchedule === 'function') runDecoSchedule();
  } else if (typeof _clearPlannerResults === 'function') {
    _clearPlannerResults();
  }
  setMobilePlanView('plan');
  if (before.activeId) {
    const el = document.getElementById(before.activeId);
    if (el && typeof el.focus === 'function') el.focus();
  } else {
    document.body.focus();
  }
  return true;
}
"""


def storage_snapshot(probe_state: dict[str, Any]) -> dict[str, Any]:
    return {
        "localStorage": probe_state.get("localStorage") or {},
        "sessionStorage": probe_state.get("sessionStorage") or {},
        "globals": {},
    }


def restore_probe_state(page, probe_state: dict[str, Any]) -> None:
    """Restore DOM and persisted settings without losing nested save-block guards."""
    storage = storage_snapshot(probe_state)
    _restore_session_begin(page)
    try:
        _apply_storage_snapshot(page, storage)
        page.evaluate(RESTORE_DOM_STATE_JS, probe_state)
        _invoke_restore_fields(page)
        _wait_settings_debounce_contract(page)
        _apply_storage_snapshot(page, storage)
        _sync_dom_from_storage(page)
        _verify_persisted_consistency(page, storage)
    finally:
        _restore_session_end(page)


__all__ = [
    "CAPTURE_PROBE_STATE_JS",
    "SETTINGS_SAVE_DEBOUNCE_WAIT_MS",
    "restore_probe_state",
    "storage_snapshot",
]
