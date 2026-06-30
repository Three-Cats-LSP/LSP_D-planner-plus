#!/usr/bin/env python3
"""Issue #140 behavioral regression — surface interval gas/GF and pooled gas plan."""
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

ISSUE140_JS = r"""
() => {
  if (typeof computeSurfIntervalCore !== 'function') throw new Error('computeSurfIntervalCore missing');
  if (typeof computePooledBottomTurnBars !== 'function') throw new Error('computePooledBottomTurnBars missing');
  const air = { fN2: 0.79, fHe: 0 };
  const ean32 = { fN2: 0.68, fHe: 0 };
  const trimix = { fN2: 0.35, fHe: 0.35 };
  const base = { d1: 30, bt1: 20, d2: 30, bt2: 20, gfLowPct: 30, gfHighPct: 85, descentRate: 18 };

  const airSurf = computeSurfIntervalCore({ ...base, dive1Gas: air, dive2Gas: air, surfGas: air });
  const eanOffAir = computeSurfIntervalCore({ ...base, dive1Gas: ean32, dive2Gas: ean32, surfGas: air });
  const eanOffEan = computeSurfIntervalCore({ ...base, dive1Gas: ean32, dive2Gas: ean32, surfGas: ean32 });
  const h1a = eanOffAir.minSI !== eanOffEan.minSI;

  const heDive = computeSurfIntervalCore({ ...base, dive1Gas: trimix, dive2Gas: trimix, surfGas: air });
  const h1b = heDive.minSI >= airSurf.minSI;

  const gf70 = computeSurfIntervalCore({ ...base, dive1Gas: air, dive2Gas: air, surfGas: air, gfHighPct: 70 });
  const gf85 = computeSurfIntervalCore({ ...base, dive1Gas: air, dive2Gas: air, surfGas: air, gfHighPct: 85 });
  const h1c = gf70.minSI >= gf85.minSI;

  const heavy = computeSurfIntervalCore({
    d1: 55, bt1: 45, d2: 55, bt2: 45,
    dive1Gas: air, dive2Gas: air, surfGas: air,
    gfLowPct: 30, gfHighPct: 85, descentRate: 18,
  });
  const h1d = heavy.siCapped === true && heavy.recSI === null;

  const pooled = computePooledBottomTurnBars(12, 200, 50, (200 - 50) * 3, 1 / 3);
  const wrongTurn = pooled ? 200 - pooled.portionL / 12 : null;
  const h2 = pooled && wrongTurn != null && pooled.turnBar > wrongTurn + 0.5;

  return {
    h1a, h1b, h1c, h1d, h2,
    airMin: airSurf.minSI,
    pooledTurn: pooled && pooled.turnBar,
    wrongTurn,
  };
}
"""


def main() -> int:
    from playwright.sync_api import sync_playwright

    print("=" * 60)
    print("Issue #140 — surface interval + pooled gas plan regression")
    print("=" * 60)

    with serve_www(ROOT) as base_url:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(120000)
            boot_app_page(page, base_url)
            data = page.evaluate(ISSUE140_JS)
            browser.close()

    cases = []
    for key, case_id, label in [
        ("h1a", "ISSUE140-H1-SURF-GAS", "surface off-gas uses air not bottom mix"),
        ("h1b", "ISSUE140-H1-HE-CARRY", "trimix He extends surface interval vs air"),
        ("h1c", "ISSUE140-H1-GF-HIGH", "lower GF High increases required SI"),
        ("h1d", "ISSUE140-H1-SI-CAP", "12h cap sets siCapped and clears recSI"),
        ("h2", "ISSUE140-H2-POOLED-TURN", "pooled travel raises bottom turn pressure"),
    ]:
        ok = bool(data.get(key))
        print(f"  {'✓' if ok else '✗'} {label}: {data}")
        cases.append(case_row(case_id, ok))

    code = 0 if all(row["status"] == "PASS" for row in cases) else 1
    finish_suite(ROOT, cases, code)
    return code


if __name__ == "__main__":
    main()
