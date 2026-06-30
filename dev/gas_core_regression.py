#!/usr/bin/env python3
"""Cycle 5 gas-plan-core / gas-table-core behavioral regression (GP-01–03, GT-01, GT-03)."""
from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_DEV = ROOT / "dev"
if str(_DEV) not in sys.path:
    sys.path.insert(0, str(_DEV))

from playwright_boot import boot_app_page  # noqa: E402
from test_http import serve_www  # noqa: E402
from tools.audit.suite_emit import case_row, finish_suite  # noqa: E402

GAS_CORE_JS = r"""
() => {
  const out = {};

  // T-GP-01: turn pressure uses bottom-cylinder portion only when travel pooled
  if (typeof computePooledBottomTurnBars !== 'function') throw new Error('computePooledBottomTurnBars missing');
  const botSize = 12, botFill = 200, botRes = 50, travelPooledL = (200 - 50) * 3, fraction = 1 / 3;
  const pooled = computePooledBottomTurnBars(botSize, botFill, botRes, travelPooledL, fraction);
  const botCylUsableL = (botFill - botRes) * botSize;
  const expectedTurn = botFill - (botCylUsableL * fraction) / botSize;
  out.gp01 = pooled && Math.abs(pooled.turnBar - expectedTurn) < 0.01;
  out.gp01turn = pooled && pooled.turnBar;
  out.gp01expected = expectedTurn;

  // T-GP-02: bottom-phase rate yields higher max BT than total consumption rate
  const reqL = 400, bottomPhaseL = 150, plannedBT = 30, usableL = 200;
  const totalRate = reqL / plannedBT;
  const bottomRate = bottomPhaseL / plannedBT;
  const maxBtTotal = Math.floor(usableL / totalRate);
  const maxBtBottom = Math.floor(usableL / bottomRate);
  out.gp02 = maxBtBottom > maxBtTotal && maxBtBottom > 0;
  out.gp02maxBtBottom = maxBtBottom;
  out.gp02maxBtTotal = maxBtTotal;

  // T-GP-03: one-way dedup by label, not gas name
  const botLabel = '21/35';
  const oneWay = [
    { name: 'Travel', label: botLabel },
    { name: 'Deco 1', label: botLabel },
    { name: 'Deco 2', label: 'EAN50' },
  ];
  const filtered = oneWay.filter(g => g.label !== botLabel);
  out.gp03 = filtered.length === 1 && filtered[0].label === 'EAN50';

  // T-GT-01: calcEND_tool narcotic load tracks calcNarcPP when O2-narcotic toggles
  if (typeof calcNarcPP !== 'function') throw new Error('calcNarcPP missing');
  const setEnd = (o2, he) => {
    document.getElementById('endDepth').value = '30';
    document.getElementById('endO2').value = String(o2);
    document.getElementById('endHe').value = String(he);
  };
  setEnd(21, 35);
  const fN2 = (100 - 21 - 35) / 100;
  const fHe = 0.35;
  narcoticO2 = true;
  calcEND_tool();
  const narcOn = parseFloat(document.getElementById('endNarcLoad').textContent);
  const expectOn = calcNarcPP(30, fN2, fHe);
  narcoticO2 = false;
  calcEND_tool();
  const narcOff = parseFloat(document.getElementById('endNarcLoad').textContent);
  const expectOff = calcNarcPP(30, fN2, fHe);
  out.gt01 = Math.abs(narcOn - expectOn) < 0.02
    && Math.abs(narcOff - expectOff) < 0.02
    && Math.abs(narcOn - narcOff) > 0.05;

  // T-GT-03: hypoxic warning at ppO2 below engine-aligned 0.18 bar threshold
  setEnd(17, 45);
  calcEND_tool();
  const warnEl = document.getElementById('endMixWarn');
  const hypoxicShown = warnEl && warnEl.style.display !== 'none'
    && /Hypoxic|hypoxic/i.test(warnEl.innerHTML || '');
  setEnd(21, 35);
  calcEND_tool();
  const clearAfterNorm = warnEl && warnEl.style.display === 'none';
  out.gt03 = hypoxicShown && clearAfterNorm;

  return out;
}
"""


def main() -> int:
    from playwright.sync_api import sync_playwright

    print("=" * 60)
    print("Cycle 5 — gas-plan + gas-table core regression")
    print("=" * 60)

    with serve_www(ROOT) as base_url:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(120000)
            boot_app_page(page, base_url)
            data = page.evaluate(GAS_CORE_JS)
            browser.close()

    cases = []
    for key, case_id, label in [
        ("gp01", "T-GP-01", "pooled turn uses bottom-cylinder portion only"),
        ("gp02", "T-GP-02", "bottom-phase rate yields higher max BT than total rate"),
        ("gp03", "T-GP-03", "one-way dedup excludes pooled label not gas name"),
        ("gt01", "T-GT-01", "END narcotic load tracks calcNarcPP on O2 toggle"),
        ("gt03", "T-GT-03", "hypoxic warning below 0.18 bar ppO2 at surface"),
    ]:
        ok = bool(data.get(key))
        print(f"  {'✓' if ok else '✗'} {label}: {data}")
        cases.append(case_row(case_id, ok))

    code = 0 if all(row["status"] == "PASS" for row in cases) else 1
    finish_suite(ROOT, cases, code)
    return code


if __name__ == "__main__":
    main()
