#!/usr/bin/env python3
"""Seven-lens Cycle 07 UI-CSS-RESULTS behavioral regression (computed styles + layout)."""
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
    "V5-CSS-CHIP-YELLOW-DISTINCT",
    "V5-CSS-PPO2-SEVERITY-COLORS",
    "V5-CSS-DEAD-LEGACY-CARDS",
    "V5-CSS-RESULTS-DEAD-ALGO-SWITCHER",
    "V5-CSS-RESULTS-REDUCED-MOTION",
    "V5-CSS-PRINT-RESULTS",
)

STATE_HASH_JS = r"""
() => {
  const parts = [];
  parts.push(document.body.className);
  parts.push(typeof navMode !== 'undefined' ? navMode : '');
  return parts.join('::');
}
"""

GENERATE_TEC_JS = r"""
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
    const btn = document.getElementById('tecGenerateBtn');
    if (btn && typeof btn.click === 'function') btn.click();
    else if (typeof runDecoSchedule === 'function') runDecoSchedule();
    await new Promise(r => setTimeout(r, 1200));
    if (typeof setMobilePlanView === 'function') setMobilePlanView('results');
    const profileTab = document.querySelector("#tecResultTabs [data-tab='profile']");
    if (profileTab && typeof switchResultTab === 'function') switchResultTab('profile', profileTab);
    let rowCount = document.querySelectorAll('#decoTableBody tr').length;
    for (let i = 0; rowCount < 5 && i < 30; i++) {
      await new Promise(r => setTimeout(r, 250));
      rowCount = document.querySelectorAll('#decoTableBody tr').length;
    }
    if (rowCount < 5 && typeof runDecoSchedule === 'function') {
      runDecoSchedule();
      await new Promise(r => setTimeout(r, 1500));
      rowCount = document.querySelectorAll('#decoTableBody tr').length;
    }
    return {
      hasResults: document.getElementById('resultsPanel')?.classList.contains('has-results'),
      rowCount,
      chipCount: document.querySelectorAll('#resultChipRow .chip').length,
      profileActive: document.getElementById('resultTab-profile')?.classList.contains('active'),
    };
  } finally {
    window._zhlHeadless = prevHeadless;
  }
}
"""

CHIP_JS = r"""
() => {
  const host = document.querySelector('#resultChipRow') || document.getElementById('resultsPanel') || document.body;
  const makeProbe = (klass, text) => {
    const el = document.createElement('span');
    el.className = `chip ${klass}`;
    el.innerHTML = '<span class="chip-dot"></span>' + text;
    el.dataset.probe = 'true';
    host.appendChild(el);
    return el;
  };
  const yellow = document.querySelector('#resultChipRow .chip-yellow') || makeProbe('chip-yellow', 'Yellow probe');
  const orange = document.querySelector('#resultChipRow .chip-orange') || makeProbe('chip-orange', 'Orange probe');
  const yc = getComputedStyle(yellow);
  const oc = getComputedStyle(orange);
  const dot = yellow.querySelector('.chip-dot');
  const resolve = (token) => {
    const p = document.createElement('span');
    p.style.color = token;
    document.body.appendChild(p);
    const c = getComputedStyle(p).color;
    p.remove();
    return c;
  };
  const resolvedYellow = resolve('var(--yellow)');
  const resolvedOrange = resolve('var(--status-orange)');
  const result = {
    yellowColor: yc.color,
    orangeColor: oc.color,
    distinct: yc.color !== oc.color,
    yellowNearToken: yc.color === resolvedYellow,
    orangeNearToken: oc.color === resolvedOrange,
    hasDot: !!dot,
    hasLabel: (yellow.textContent || '').replace(/\s+/g, ' ').trim().length > 3,
    ok: yc.color !== oc.color && !!dot && (yellow.textContent || '').replace(/\s+/g, ' ').trim().length > 3,
  };
  document.querySelectorAll('[data-probe="true"]').forEach(el => el.remove());
  return result;
}
"""

PPO2_JS = r"""
() => {
  const read = (sel) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    return getComputedStyle(el).color;
  };
  const resolve = (token) => {
    const p = document.createElement('span');
    p.style.color = token;
    document.body.appendChild(p);
    const c = getComputedStyle(p).color;
    p.remove();
    return c;
  };
  const neutral = resolve('var(--text)');
  const rightCells = [
    ...document.querySelectorAll('#resultsPanel #decoTableBody tr[data-phase]:not(.row-summary) td[data-label="Mix"], #resultsPanel #decoTableBody tr[data-phase]:not(.row-summary) td[data-label="PPO2"], #resultsPanel #decoTableBody tr[data-phase]:not(.row-summary) td[data-label="CNS"], #resultsPanel #decoTableBody tr[data-phase]:not(.row-summary) td[data-label="EAD"]')
  ];
  const rightColors = rightCells.map(el => getComputedStyle(el).color);
  const okColor = read('#resultsPanel #decoTableBody .col-ppo2.ppo2-ok');
  const warnColor = read('#resultsPanel #decoTableBody .col-ppo2.ppo2-warn');
  const critColor = read('#resultsPanel #decoTableBody .col-ppo2.ppo2-crit');
  const neutralRightColumns = rightCells.length > 0 && rightColors.every(color => color === neutral);
  return {
    okColor,
    warnColor,
    critColor,
    neutral,
    rightColors,
    neutralRightColumns,
    ok: neutralRightColumns,
    counts: {
      ok: document.querySelectorAll('#resultsPanel #decoTableBody .ppo2-ok').length,
      warn: document.querySelectorAll('#resultsPanel #decoTableBody .ppo2-warn').length,
      crit: document.querySelectorAll('#resultsPanel #decoTableBody .ppo2-crit').length,
    },
  };
}
"""

DEAD_JS = r"""
async () => {
  const fetchText = async (href) => {
    try { return await (await fetch(href)).text(); }
    catch (_) { return ''; }
  };
  const css = await fetchText('lsp-dplanner-results.css');
  return {
    legacyPanelsDisplay: document.querySelector('.legacy-panels')
      ? getComputedStyle(document.querySelector('.legacy-panels')).display
      : 'missing',
    legacyCardTables: document.querySelectorAll('.legacy-panels .deco-table:not(.table-view)').length,
    v4ScheduleTables: document.querySelectorAll('#resultsPanel .schedule-table').length,
    hasLegacyMobileBlock: /\.legacy-panels\s+\.deco-table:not\(\.table-view\)/.test(css),
    algoSwitcherCount: document.querySelectorAll('.algo-switcher').length,
    hasAlgoSwitcherRule: /\.algo-switcher\s*\{/.test(css),
    deadLegacyOk:
      document.querySelectorAll('.legacy-panels .deco-table:not(.table-view)').length === 0
      && !/\.legacy-panels\s+\.deco-table:not\(\.table-view\)/.test(css),
    deadAlgoOk:
      document.querySelectorAll('.algo-switcher').length === 0
      && !/\.algo-switcher\s*\{/.test(css),
  };
}
"""

REDUCED_JS = r"""
() => {
  const read = (sel) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    const cs = getComputedStyle(el);
    return { transitionDuration: cs.transitionDuration, transitionProperty: cs.transitionProperty };
  };
  const tab = read('#tecResultTabs .result-tab-btn');
  const mode = read('#headerTopRow .mode-btn');
  const thumb = read('.theme-pill-thumb');
  const zeroed = (row) => row && (
    row.transitionDuration === '0s'
    || row.transitionDuration.startsWith('0s')
    || row.transitionProperty === 'none'
  );
  return { tab, mode, thumb, ok: zeroed(tab) && (mode ? zeroed(mode) : true) && zeroed(thumb) };
}
"""

PRINT_JS = r"""
async () => {
  const fetchText = async (href) => {
    try { return await (await fetch(href)).text(); }
    catch (_) { return ''; }
  };
  const css = await fetchText('lsp-dplanner-results.css');
  const alert = document.querySelector('#decoAlerts .alert.deco, #decoAlertsNarcotic .alert.deco, #decoAlerts .alert.narcotic-warn, #decoAlertsNarcotic .alert.narcotic-warn');
  const scheduleRow = document.querySelector('#resultsPanel #decoTableBody tr, #decoResult .deco-table.schedule-table tbody tr');
  const metricStrip = document.getElementById('resultMetricStrip');
  const readDisplay = (el) => (el ? getComputedStyle(el).display : 'missing');
  const breakInside = scheduleRow ? getComputedStyle(scheduleRow).breakInside : '';
  const pageBreakInside = scheduleRow ? getComputedStyle(scheduleRow).pageBreakInside : '';
  const breakOk = breakInside === 'avoid' || pageBreakInside === 'avoid';
  const safetyVisible = !alert || readDisplay(alert) !== 'none';
  return {
    hasPrintBlock: /@media\s+print/.test(css),
    alertDisplay: readDisplay(alert),
    scheduleDisplay: readDisplay(scheduleRow),
    metricDisplay: readDisplay(metricStrip),
    scheduleBreakInside: breakInside,
    ok:
      /@media\s+print/.test(css)
      && safetyVisible
      && readDisplay(scheduleRow) !== 'none'
      && readDisplay(metricStrip) !== 'none'
      && breakOk,
  };
}
"""


def run_cases(
    page,
    viewport: tuple[int, int],
    *,
    browser_version: str = "",
    light_theme: bool = False,
    run_behavioral: bool = True,
) -> dict:
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    page.evaluate("() => { document.body.classList.remove('light-theme'); }")
    before_hash = page.evaluate(STATE_HASH_JS)
    if light_theme:
        page.evaluate("() => { document.body.classList.add('light-theme'); }")

    page.evaluate("() => { window._zhlHeadless = false; setMainNav('buh'); }")
    page.locator("body").click(position={"x": 8, "y": 8})
    active_before = page.evaluate("() => document.activeElement?.id || ''")
    chip = {}
    ppo2 = {}
    dead = {}
    reduced = {}
    print_probe = {}
    gen = {}
    try:
        if run_behavioral:
            gen = {}
            for attempt in range(3):
                gen = page.evaluate(GENERATE_TEC_JS)
                if gen.get("hasResults") and int(gen.get("rowCount") or 0) >= 5:
                    break
                page.wait_for_timeout(800)
            if not gen.get("hasResults") or int(gen.get("rowCount") or 0) < 5:
                raise RuntimeError(f"TEC plan did not render schedule rows: {gen}")
            chip = page.evaluate(CHIP_JS)
            ppo2 = page.evaluate(PPO2_JS)
        else:
            gen = page.evaluate(GENERATE_TEC_JS)
            if not gen.get("hasResults"):
                raise RuntimeError(f"TEC plan did not render results (landscape): {gen}")

        dead = page.evaluate(DEAD_JS)

        page.emulate_media(reduced_motion="reduce")
        reduced = page.evaluate(REDUCED_JS)
        page.emulate_media(reduced_motion="no-preference")

        page.emulate_media(media="print")
        print_probe = page.evaluate(PRINT_JS)
        page.emulate_media(media="screen")
    finally:
        page.evaluate(
            """(activeId) => {
              document.body.classList.remove('light-theme');
              setMainNav('buh');
              const el = activeId ? document.getElementById(activeId) : null;
              if (el && typeof el.focus === 'function') el.focus();
              else document.body.focus();
            }""",
            active_before,
        )
        page.emulate_media(reduced_motion="no-preference")
        page.emulate_media(media="screen")
        page.locator("body").click(position={"x": 8, "y": 8})
        page.evaluate("() => { document.body.focus(); }")
        after_hash = page.evaluate(STATE_HASH_JS)
        state_restored = before_hash == after_hash

    out = {
        "_detail": {
            "viewport": viewport,
            "browserVersion": browser_version,
            "light_theme": light_theme,
            "gen": gen,
            "chip": chip,
            "ppo2": ppo2,
            "dead": dead,
            "reduced": reduced,
            "print": print_probe,
            "state_restored": state_restored,
            "before_hash": before_hash,
            "after_hash": after_hash,
        },
    }
    out["V5-CSS-CHIP-YELLOW-DISTINCT"] = bool(chip.get("ok")) if run_behavioral else True
    out["V5-CSS-PPO2-SEVERITY-COLORS"] = bool(ppo2.get("ok")) if run_behavioral else True
    out["V5-CSS-DEAD-LEGACY-CARDS"] = bool(dead.get("deadLegacyOk"))
    out["V5-CSS-RESULTS-DEAD-ALGO-SWITCHER"] = bool(dead.get("deadAlgoOk"))
    out["V5-CSS-RESULTS-REDUCED-MOTION"] = bool(reduced.get("ok"))
    out["V5-CSS-PRINT-RESULTS"] = bool(print_probe.get("ok"))
    if not state_restored:
        out["_detail"]["state_restored"] = False
    return out


def _run_viewport(
    browser,
    base_url: str,
    viewport: tuple[int, int],
    *,
    light_theme: bool = False,
    run_behavioral: bool = True,
) -> dict:
    context = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
    page = context.new_page()
    page.set_default_timeout(120000)
    try:
        page.goto(f"{base_url}/index.html", wait_until="load")
        boot_app_page(page, base_url)
        return run_cases(
            page,
            viewport,
            browser_version=browser.version,
            light_theme=light_theme,
            run_behavioral=run_behavioral,
        )
    finally:
        context.close()


def main() -> int:
    from playwright.sync_api import sync_playwright

    print("=" * 60)
    print("Cycle 07 — UI-CSS-RESULTS computed-style regression")
    print("=" * 60)

    results: dict[str, bool] = {case_id: True for case_id in CASE_IDS}
    detail: dict = {}

    with serve_www(ROOT) as base_url:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            dark = _run_viewport(browser, base_url, (1280, 800), light_theme=False)
            detail["1280x800-dark"] = dark.pop("_detail")
            for case_id, ok in dark.items():
                results[case_id] = results[case_id] and bool(ok)

            light = _run_viewport(browser, base_url, (1280, 800), light_theme=True)
            detail["1280x800-light"] = light.pop("_detail")
            for case_id, ok in light.items():
                results[case_id] = results[case_id] and bool(ok)

            landscape = _run_viewport(
                browser, base_url, (667, 375), light_theme=False, run_behavioral=False
            )
            detail["667x375"] = landscape.pop("_detail")
            for case_id, ok in landscape.items():
                if case_id in (
                    "V5-CSS-CHIP-YELLOW-DISTINCT",
                    "V5-CSS-PPO2-SEVERITY-COLORS",
                    "V5-CSS-PRINT-RESULTS",
                ):
                    continue
                results[case_id] = results[case_id] and bool(ok)

            browser.close()

    rows = [case_row(case_id, results[case_id]) for case_id in CASE_IDS]
    for case_id in CASE_IDS:
        print(f"  {'✓' if results[case_id] else '✗'} [{case_id}]")
        if not results[case_id]:
            for vp, d in detail.items():
                if case_id == "V5-CSS-PRINT-RESULTS" and d.get("print"):
                    print(f"    {vp} print: {json.dumps(d['print'], indent=2)}")
    code = 0 if all(results.values()) else 1
    finish_suite(ROOT, rows, code)
    out = ROOT / "dev" / "ui_results_css_regression_results.json"
    out.write_text(json.dumps({"results": results, "detail": detail}, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
