#!/usr/bin/env python3
"""Seven-lens Cycle 08 UI-PLANNER-SHELL + UI-RESULTS-PANEL behavioral regression."""
from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
_DEV = ROOT / "dev"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(_DEV) not in sys.path:
    sys.path.insert(0, str(_DEV))

from playwright_boot import boot_app_page  # noqa: E402
from test_http import serve_www  # noqa: E402
from tools.audit.suite_emit import case_row, finish_suite  # noqa: E402

CASE_IDS = (
    "SL-C08-MOBILE-PANEL-EXCLUSIVE",
    "SL-C08-NAV-PRESERVES-RESULTS",
    "SL-C08-INVALID-TEC-CLEARS-STALE",
    "SL-C08-DEAD-RESULT-TAB-PREFIX",
    "SL-C08-SINGLE-MOBILE-INIT",
)

RESTORE_STATE_JS = r"""
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

CAPTURE_RESTORE_JS = r"""
() => ({
  navSection: 'buh',
  depth: document.getElementById('tecDepth')?.value || '40',
  bt: document.getElementById('tecBT')?.value || '30',
  hadResults: document.getElementById('resultsPanel')?.classList.contains('has-results') === true,
  activeId: document.activeElement?.id || '',
})
"""

STATE_HASH_JS = r"""
() => {
  const parts = [];
  parts.push(document.body.className);
  parts.push(typeof navMode !== 'undefined' ? navMode : '');
  parts.push(typeof plannerAlgo !== 'undefined' ? plannerAlgo : '');
  parts.push(typeof units !== 'undefined' ? units : '');
  parts.push(document.getElementById('tecDepth')?.value || '');
  parts.push(document.getElementById('tecBT')?.value || '');
  parts.push(document.getElementById('resultsPanel')?.classList.contains('has-results') ? '1' : '0');
  parts.push(document.querySelectorAll('#decoTableBody tr').length);
  parts.push(document.querySelector('#tecResultTabs .result-tab-btn.active')?.dataset?.tab || '');
  parts.push(document.activeElement?.id || '');
  return parts.join('::');
}
"""

MOBILE_EXCLUSIVE_JS = r"""
async () => {
  const vis = (id) => {
    const el = document.getElementById(id);
    if (!el) return 'missing';
    return getComputedStyle(el).display;
  };
  const activePlan = () => (plannerAlgo === 'rec' ? 'recPlannerView' : 'tecPlannerView');
  const planId = activePlan();
  const beforePlan = vis(planId);
  const beforeResults = vis('resultsPanel');
  const bothBefore = beforePlan !== 'none' && beforeResults !== 'none';

  if (typeof setMobilePlanView === 'function') setMobilePlanView('plan');
  await new Promise(r => setTimeout(r, 100));
  const planOnly = vis(planId) !== 'none' && vis('resultsPanel') === 'none';

  if (typeof setMobilePlanView === 'function') setMobilePlanView('results');
  await new Promise(r => setTimeout(r, 100));
  const resultsOnly = vis('resultsPanel') !== 'none' && vis(planId) === 'none';

  if (typeof setMobilePlanView === 'function') setMobilePlanView('plan');
  await new Promise(r => setTimeout(r, 50));

  return {
    planId,
    bothBefore,
    planOnly,
    resultsOnly,
    inactiveHidden: vis(plannerAlgo === 'rec' ? 'tecPlannerView' : 'recPlannerView') === 'none',
    ok: !bothBefore && planOnly && resultsOnly,
  };
}
"""

NAV_PRESERVES_JS = r"""
async () => {
  const prevHeadless = window._zhlHeadless;
  window._zhlHeadless = false;
  try {
    setMainNav('buh');
    const depthEl = document.getElementById('tecDepth');
    const btEl = document.getElementById('tecBT');
    if (depthEl) depthEl.value = '45';
    if (btEl) btEl.value = '25';
    if (typeof _syncTecDepthBtSteppers === 'function') _syncTecDepthBtSteppers();
    document.getElementById('tecGenerateBtn')?.click();
    let rows = 0;
    for (let i = 0; i < 30; i++) {
      await new Promise(r => setTimeout(r, 250));
      rows = document.querySelectorAll('#decoTableBody tr').length;
      if (rows >= 5) break;
    }
    const before = {
      hasResults: document.getElementById('resultsPanel')?.classList.contains('has-results'),
      rows,
      tab: document.querySelector('#tecResultTabs .result-tab-btn.active')?.dataset?.tab || '',
    };
    if (!before.hasResults || before.rows < 5) {
      return { ok: false, reason: 'generate_failed', before };
    }
    document.getElementById('navBtnTools')?.click();
    await new Promise(r => setTimeout(r, 300));
    document.getElementById('bnavPlanner')?.click();
    await new Promise(r => setTimeout(r, 500));
    const after = {
      hasResults: document.getElementById('resultsPanel')?.classList.contains('has-results'),
      rows: document.querySelectorAll('#decoTableBody tr').length,
      tab: document.querySelector('#tecResultTabs .result-tab-btn.active')?.dataset?.tab || '',
      decoDisplay: document.getElementById('decoResult')?.style.display || '',
    };
    return {
      before,
      after,
      ok: after.hasResults && after.rows >= before.rows && after.rows > 0,
    };
  } finally {
    window._zhlHeadless = prevHeadless;
  }
}
"""

INVALID_CLEARS_JS = r"""
async () => {
  const prevHeadless = window._zhlHeadless;
  window._zhlHeadless = false;
  try {
    setMainNav('buh');
    const depthEl = document.getElementById('tecDepth');
    const btEl = document.getElementById('tecBT');
    if (depthEl) depthEl.value = '45';
    if (btEl) btEl.value = '25';
    if (typeof _syncTecDepthBtSteppers === 'function') _syncTecDepthBtSteppers();
    document.getElementById('tecGenerateBtn')?.click();
    let validRows = 0;
    for (let i = 0; i < 30; i++) {
      await new Promise(r => setTimeout(r, 250));
      validRows = document.querySelectorAll('#decoTableBody tr').length;
      if (validRows >= 5) break;
    }
    const valid = {
      hasResults: document.getElementById('resultsPanel')?.classList.contains('has-results'),
      rows: validRows,
    };
    if (!valid.hasResults || valid.rows < 5) {
      return { ok: false, reason: 'valid_generate_failed', valid };
    }
    if (depthEl) depthEl.value = '999';
    if (typeof _syncTecDepthBtSteppers === 'function') _syncTecDepthBtSteppers();
    document.getElementById('tecGenerateBtn')?.click();
    await new Promise(r => setTimeout(r, 800));
    const afterInvalid = {
      hasResults: document.getElementById('resultsPanel')?.classList.contains('has-results'),
      rows: document.querySelectorAll('#decoTableBody tr').length,
      toastVisible: !!document.querySelector('.toast.schedule, .toast-error, [class*="toast"]'),
    };
    if (depthEl) depthEl.value = '45';
    if (typeof _syncTecDepthBtSteppers === 'function') _syncTecDepthBtSteppers();
    document.getElementById('tecGenerateBtn')?.click();
    let correctedRows = 0;
    for (let i = 0; i < 30; i++) {
      await new Promise(r => setTimeout(r, 250));
      correctedRows = document.querySelectorAll('#decoTableBody tr').length;
      if (correctedRows >= 5) break;
    }
    const corrected = {
      hasResults: document.getElementById('resultsPanel')?.classList.contains('has-results'),
      rows: correctedRows,
    };
    return {
      valid,
      afterInvalid,
      corrected,
      ok: !afterInvalid.hasResults && afterInvalid.rows === 0
        && corrected.hasResults && corrected.rows >= 5,
    };
  } finally {
    window._zhlHeadless = prevHeadless;
  }
}
"""

TAB_PREFIX_JS = r"""
() => {
  const src = typeof switchResultTab === 'function' ? switchResultTab.toString() : '';
  const deadPrefix = /const prefix = isRec \? '' : ''/.test(src);
  setMainNav('buh');
  const tabs = ['profile', 'contingency', 'graphs', 'tissue'];
  const results = [];
  for (const name of tabs) {
    const btn = document.querySelector(`#tecResultTabs [data-tab='${name}']`);
    if (!btn) { results.push({ name, missing: true }); continue; }
    btn.click();
    const pane = document.getElementById('resultTab-' + name);
    results.push({
      name,
      paneActive: pane?.classList.contains('active') === true,
      btnActive: btn.classList.contains('active'),
    });
  }
  const allActive = results.every(r => r.paneActive && r.btnActive);
  return { deadPrefix, results, ok: !deadPrefix && allActive };
}
"""

MOBILE_INIT_JS = r"""
() => {
  const initSrc = typeof initV3Layout === 'function' ? initV3Layout.toString() : '';
  const usesEnsure = initSrc.includes('_ensureMobilePlanViewBootstrap');
  const guard = window._mobilePlanViewBootstrapDone === true;
  if (typeof _ensureMobilePlanViewBootstrap === 'function') {
    _ensureMobilePlanViewBootstrap();
    _ensureMobilePlanViewBootstrap();
  }
  if (typeof initV3Layout === 'function') initV3Layout();
  return {
    usesEnsure,
    guard,
    guardAfterRepeat: window._mobilePlanViewBootstrapDone === true,
    ok: usesEnsure && guard && window._mobilePlanViewBootstrapDone === true,
  };
}
"""

SETTINGS_NAV_JS = r"""
async () => {
  const prevHeadless = window._zhlHeadless;
  window._zhlHeadless = false;
  try {
    setMainNav('buh');
    const depthEl = document.getElementById('tecDepth');
    const btEl = document.getElementById('tecBT');
    if (depthEl) depthEl.value = '45';
    if (btEl) btEl.value = '25';
    if (typeof _syncTecDepthBtSteppers === 'function') _syncTecDepthBtSteppers();
    document.getElementById('tecGenerateBtn')?.click();
    let beforeRows = 0;
    for (let i = 0; i < 30; i++) {
      await new Promise(r => setTimeout(r, 250));
      beforeRows = document.querySelectorAll('#decoTableBody tr').length;
      if (beforeRows >= 5) break;
    }
    document.getElementById('navBtnSettings')?.click();
    await new Promise(r => setTimeout(r, 300));
    document.getElementById('bnavPlanner')?.click();
    await new Promise(r => setTimeout(r, 500));
    const afterRows = document.querySelectorAll('#decoTableBody tr').length;
    return {
      beforeRows,
      afterRows,
      ok: beforeRows >= 5 && afterRows >= beforeRows,
    };
  } finally {
    window._zhlHeadless = prevHeadless;
  }
}
"""


def run_cases(page, viewport: tuple[int, int], *, run_behavioral: bool = True) -> dict:
    restore_snapshot = page.evaluate(CAPTURE_RESTORE_JS)
    before_hash = page.evaluate(STATE_HASH_JS)
    page.evaluate("() => { localStorage.removeItem('lspDiveSettings_v6'); }")
    page.evaluate("() => { window._zhlHeadless = false; }")

    mobile = {}
    nav = {}
    invalid = {}
    tabs = {}
    init = {}
    settings = {}

    try:
        if viewport[0] <= 640:
            mobile = page.evaluate(MOBILE_EXCLUSIVE_JS)
        if run_behavioral and viewport == (1280, 800):
            nav = page.evaluate(NAV_PRESERVES_JS)
            invalid = page.evaluate(INVALID_CLEARS_JS)
            tabs = page.evaluate(TAB_PREFIX_JS)
            init = page.evaluate(MOBILE_INIT_JS)
            settings = page.evaluate(SETTINGS_NAV_JS)
    finally:
        page.evaluate(RESTORE_STATE_JS, restore_snapshot)
        page.wait_for_timeout(300)
        page.locator("body").click(position={"x": 8, "y": 8})
        after_hash = page.evaluate(STATE_HASH_JS)
        state_restored = before_hash == after_hash

    out = {
        "_detail": {
            "viewport": viewport,
            "mobile": mobile,
            "nav": nav,
            "invalid": invalid,
            "tabs": tabs,
            "init": init,
            "settings": settings,
            "state_restored": state_restored,
            "before_hash": before_hash,
            "after_hash": after_hash,
        },
    }
    mobile_ok = bool(mobile.get("ok")) if viewport[0] <= 640 else True
    nav_ok = bool(nav.get("ok")) and bool(settings.get("ok")) if run_behavioral and viewport == (1280, 800) else True
    out["SL-C08-MOBILE-PANEL-EXCLUSIVE"] = mobile_ok
    out["SL-C08-NAV-PRESERVES-RESULTS"] = nav_ok if run_behavioral and viewport == (1280, 800) else True
    out["SL-C08-INVALID-TEC-CLEARS-STALE"] = bool(invalid.get("ok")) if run_behavioral and viewport == (1280, 800) else True
    out["SL-C08-DEAD-RESULT-TAB-PREFIX"] = bool(tabs.get("ok")) if run_behavioral and viewport == (1280, 800) else True
    out["SL-C08-SINGLE-MOBILE-INIT"] = bool(init.get("ok")) if run_behavioral and viewport == (1280, 800) else True
    if not state_restored and run_behavioral and viewport == (1280, 800):
        for case_id in CASE_IDS:
            out[case_id] = False
    return out


def _run_viewport(browser, base_url: str, viewport: tuple[int, int], *, run_behavioral: bool = True) -> dict:
    context = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
    page = context.new_page()
    page.set_default_timeout(120000)
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    try:
        page.goto(f"{base_url}/index.html", wait_until="load")
        boot_app_page(page, base_url)
        result = run_cases(page, viewport, run_behavioral=run_behavioral)
        result["_detail"]["console_errors"] = errors
        if errors:
            for case_id in CASE_IDS:
                result[case_id] = False
        return result
    finally:
        context.close()


def main() -> int:
    from playwright.sync_api import sync_playwright

    print("=" * 60)
    print("Cycle 08 — UI-SHELL-RESULTS behavioral regression")
    print("=" * 60)

    results: dict[str, bool] = {case_id: True for case_id in CASE_IDS}
    detail: dict = {}

    with serve_www(ROOT) as base_url:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            desktop = _run_viewport(browser, base_url, (1280, 800))
            detail["1280x800"] = desktop.pop("_detail")
            for case_id, ok in desktop.items():
                results[case_id] = results[case_id] and bool(ok)

            portrait = _run_viewport(browser, base_url, (375, 667), run_behavioral=False)
            detail["375x667"] = portrait.pop("_detail")
            results["SL-C08-MOBILE-PANEL-EXCLUSIVE"] = (
                results["SL-C08-MOBILE-PANEL-EXCLUSIVE"]
                and bool(portrait.get("SL-C08-MOBILE-PANEL-EXCLUSIVE"))
            )

            landscape = _run_viewport(browser, base_url, (667, 375), run_behavioral=False)
            detail["667x375"] = landscape.pop("_detail")
            results["SL-C08-MOBILE-PANEL-EXCLUSIVE"] = (
                results["SL-C08-MOBILE-PANEL-EXCLUSIVE"]
                and bool(landscape.get("SL-C08-MOBILE-PANEL-EXCLUSIVE"))
            )

            browser.close()

    rows = [case_row(case_id, results[case_id]) for case_id in CASE_IDS]
    for case_id in CASE_IDS:
        print(f"  {'✓' if results[case_id] else '✗'} [{case_id}]")
    code = 0 if all(results.values()) else 1
    out = ROOT / "dev" / "ui_shell_results_regression_results.json"
    out.write_text(json.dumps({"results": results, "detail": detail}, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")
    out.unlink(missing_ok=True)
    finish_suite(ROOT, rows, code)


if __name__ == "__main__":
    raise SystemExit(main())
