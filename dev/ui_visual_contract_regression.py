#!/usr/bin/env python3
"""Cross-unit visual contracts for the technical planner and results shell."""
from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "dev") not in sys.path:
    sys.path.insert(0, str(ROOT / "dev"))

from playwright_boot import boot_app_page  # noqa: E402
from test_http import serve_www  # noqa: E402
from tools.audit.suite_emit import case_row, finish_suite  # noqa: E402


CASE_IDS = (
    "SL-VIS-GAS-DOT-SINGLE-SOURCE",
    "SL-VIS-GAS-SWITCH-TOKEN-PARITY",
    "SL-VIS-DESKTOP-TWO-COLUMN-LAYOUT",
    "SL-VIS-DECO-BANNER-GAS-LABELS",
    "SL-VIS-SWITCH-ROW-THEME-PARITY",
)


GENERATE_JS = r"""
async () => {
  window._zhlHeadless = false;
  setMainNav('buh');
  const depth = document.getElementById('tecDepth');
  const bt = document.getElementById('tecBT');
  if (depth) depth.value = '40';
  if (bt) bt.value = '30';
  if (typeof _syncTecDepthBtSteppers === 'function') _syncTecDepthBtSteppers();
  document.getElementById('tecGenerateBtn')?.click();
  for (let i = 0; i < 40; i++) {
    await new Promise(resolve => setTimeout(resolve, 250));
    if (document.querySelectorAll('#decoTableBody tr').length >= 5
        && document.querySelector('.gas-pills .deco1')) return true;
  }
  return false;
}
"""


CAPTURE_JS = r"""
() => {
  const rgb = value => value.replace(/\s+/g, '').toLowerCase();
  const style = (el, prop) => el ? getComputedStyle(el)[prop] : '';
  const resolveColor = value => {
    const probe = document.createElement('span');
    probe.style.color = value;
    document.body.appendChild(probe);
    const resolved = rgb(getComputedStyle(probe).color);
    probe.remove();
    return resolved;
  };
  const root = getComputedStyle(document.body);
  const title = document.getElementById('diluentCardTitle');
  const titleRow = title?.closest('.gas-card-title-row');
  const dots = titleRow ? titleRow.querySelectorAll('.gas-dot') : [];
  const graphSwatch = document.querySelector('#decoProfileLegend .gas-switch-swatch');
  const decoDots = [...document.querySelectorAll('.deco-gas-card .gas-dot')];
  const pills = [...document.querySelectorAll('#resultsPanel .gas-pills .gas-pill')];
  const switchRows = [...document.querySelectorAll('#resultsPanel .schedule-table tr[data-phase="switch"]')];
  const switchCells = switchRows.flatMap(row =>
    [...row.querySelectorAll('td:not([data-label="PPO2"])')]
  );
  const planner = document.getElementById('tecPlannerView')?.getBoundingClientRect();
  const results = document.getElementById('resultsPanel')?.getBoundingClientRect();
  const expectedSwitch = resolveColor(root.getPropertyValue('--gas-switch'));
  const expectedBg = resolveColor(root.getPropertyValue('--gas-switch-label-bg'));
  const expectedText = resolveColor(root.getPropertyValue('--gas-switch-label-text'));
  const swatchBg = rgb(style(graphSwatch, 'backgroundColor'));
  const decoDotColors = decoDots.map(el => rgb(style(el, 'backgroundColor')));
  const decoPills = pills.filter(el => el.classList.contains('deco1') || el.classList.contains('deco2'));
  return {
    title: title?.textContent?.trim() || '',
    bottomDotCount: dots.length,
    titleHasEmoji: /[\u{1F535}\u{1F7E1}\u{1F7E0}\u{1F7E2}]/u.test(title?.textContent || ''),
    swatchBg,
    expectedBg,
    expectedText,
    decoDotColors,
    pillTexts: pills.map(el => el.textContent.trim()),
    decoPillBackgrounds: decoPills.map(el => rgb(style(el, 'backgroundColor'))),
    decoPillColors: decoPills.map(el => rgb(style(el, 'color'))),
    switchRowCount: switchRows.length,
    switchCellColors: switchCells.map(el => rgb(style(el, 'color'))),
    expectedSwitch,
    layout: planner && results ? {
      plannerLeft: planner.left,
      plannerRight: planner.right,
      resultsLeft: results.left,
      plannerTop: planner.top,
      resultsTop: results.top,
      sideBySide: results.left >= planner.right - 1 && Math.abs(results.top - planner.top) <= 2,
    } : null,
  };
}
"""


def _capture(browser, base_url: str, viewport: tuple[int, int], light: bool) -> dict:
    context = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
    page = context.new_page()
    page.set_default_timeout(120_000)
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    try:
        boot_app_page(page, base_url)
        page.evaluate(
            "light => document.body.classList.toggle('light-theme', light)", light
        )
        generated = bool(page.evaluate(GENERATE_JS))
        capture = page.evaluate(CAPTURE_JS)
        capture["generated"] = generated
        capture["console_errors"] = errors
        return capture
    finally:
        context.close()


def main() -> int:
    from playwright.sync_api import sync_playwright

    results = {case_id: True for case_id in CASE_IDS}
    details: dict[str, dict] = {}

    with serve_www(ROOT, port=0) as base_url:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            for width, height in ((1280, 800), (1024, 768), (768, 720), (667, 600)):
                key = f"{width}x{height}-dark"
                details[key] = _capture(browser, base_url, (width, height), False)
            details["1280x800-light"] = _capture(browser, base_url, (1280, 800), True)
            browser.close()

    dark = details["1280x800-dark"]
    light = details["1280x800-light"]
    captures = list(details.values())

    results["SL-VIS-GAS-DOT-SINGLE-SOURCE"] = all(
        c["bottomDotCount"] == 1 and not c["titleHasEmoji"] for c in captures
    )
    results["SL-VIS-GAS-SWITCH-TOKEN-PARITY"] = all(
        c["generated"]
        and c["swatchBg"] == c["expectedBg"]
        and bool(c["decoDotColors"])
        and all(color == c["expectedBg"] for color in c["decoDotColors"])
        for c in captures
    )
    results["SL-VIS-DESKTOP-TWO-COLUMN-LAYOUT"] = all(
        bool(c["layout"] and c["layout"]["sideBySide"])
        for key, c in details.items() if not key.endswith("-light")
    )
    results["SL-VIS-DECO-BANNER-GAS-LABELS"] = all(
        c["generated"]
        and any(text.startswith("Bottom: ") for text in c["pillTexts"])
        and any(text.startswith("Deco 1: ") and " @ " in text for text in c["pillTexts"])
        and bool(c["decoPillBackgrounds"])
        and all(color == c["expectedBg"] for color in c["decoPillBackgrounds"])
        and all(color == c["expectedText"] for color in c["decoPillColors"])
        for c in (dark, light)
    )
    results["SL-VIS-SWITCH-ROW-THEME-PARITY"] = all(
        c["generated"]
        and c["switchRowCount"] >= 1
        and bool(c["switchCellColors"])
        and all(color == c["expectedSwitch"] for color in c["switchCellColors"])
        for c in (dark, light)
    )

    for case_id, passed in results.items():
        print(f"  {'PASS' if passed else 'FAIL'} [{case_id}]")
    if not all(results.values()):
        print(json.dumps(details, indent=2))

    rows = [case_row(case_id, passed) for case_id, passed in results.items()]
    finish_suite(ROOT, rows, 0 if all(results.values()) else 1)


if __name__ == "__main__":
    raise SystemExit(main())
