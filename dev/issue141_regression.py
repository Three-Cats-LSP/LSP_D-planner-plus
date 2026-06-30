#!/usr/bin/env python3
"""Issue #141 — delegate/schedule audit: pSCR diluent bypass, getN2Frac, resolveCcrSac cleanup."""
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

ISSUE141_JS = r"""
() => {
  const out = {};

  // M-1: pSCR diluent LPM derived from computePSCRFractions, not hardcoded ×10
  const met = 1.5;
  const loopVol = 10;
  const depthM = 40;
  const pSurf = altSurfaceP || 1.01325;
  const pAmb = pSurf + depthM * BAR_PER_METRE;
  const ccr = { circuit: 'pSCR', scrLoopVolume: loopVol, scrMetabolicO2: met, bailout: false };
  const fO2Dil = 0.21;
  const fr = computePSCRFractions(pAmb, fO2Dil, 0, ccr);
  const delta = Math.max(1e-6, fO2Dil - fr.fO2);
  const expectedSurf = (met / delta) * (pSurf / pAmb);
  const hardcoded = met * 10;
  out.m1 = Math.abs(expectedSurf - hardcoded) > 0.5;
  out.m1delta = delta;
  out.m1expected = expectedSurf;

  const sel = document.getElementById('circuitSelect');
  const prevCircuit = sel ? sel.value : null;
  if (sel) sel.value = 'pSCR';
  toggleCircuitFields?.();
  const lpm = ccrDiluentSurfaceLpm(depthM);
  if (sel && prevCircuit != null) { sel.value = prevCircuit; toggleCircuitFields?.(); }
  out.m1lpm = lpm;
  out.m1match = Number.isFinite(lpm) && Math.abs(lpm - expectedSurf) < 0.25;

  // L-1: resolveCcrSacForGas removed
  out.l1 = typeof resolveCcrSacForGas === 'undefined';

  // L-2: invalid trimix returns null, not FN2_AIR
  const o2El = document.getElementById('plannerTrimixO2');
  const heEl = document.getElementById('plannerTrimixHe');
  const prevO2 = o2El ? o2El.value : null;
  const prevHe = heEl ? heEl.value : null;
  if (o2El) o2El.value = '60';
  if (heEl) heEl.value = '50';
  const badN2 = getN2Frac('trimix');
  if (o2El && prevO2 != null) o2El.value = prevO2;
  if (heEl && prevHe != null) heEl.value = prevHe;
  out.l2 = badN2 === null;

  return out;
}
"""


def main() -> int:
    from playwright.sync_api import sync_playwright

    print("=" * 60)
    print("Issue #141 — delegate/schedule audit regression")
    print("=" * 60)

    with serve_www(ROOT) as base_url:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(120000)
            boot_app_page(page, base_url)
            data = page.evaluate(ISSUE141_JS)
            browser.close()

    cases = []
    for key, case_id, label in [
        ("m1match", "ISSUE141-M1-PSCR-BYPASS", "pSCR diluent LPM from computePSCRFractions"),
        ("l1", "ISSUE141-L1-RESOLVE-SAC", "resolveCcrSacForGas removed"),
        ("l2", "ISSUE141-L2-TRIMIX-NULL", "invalid trimix getN2Frac returns null"),
    ]:
        ok = bool(data.get(key))
        print(f"  {'✓' if ok else '✗'} {label}: {data}")
        cases.append(case_row(case_id, ok))

    code = 0 if all(row["status"] == "PASS" for row in cases) else 1
    finish_suite(ROOT, cases, code)
    return code


if __name__ == "__main__":
    main()
