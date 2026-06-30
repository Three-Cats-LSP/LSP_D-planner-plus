#!/usr/bin/env python3
"""Issue #142 — Dive 2 gas override for surface interval calculator (SI-01–SI-05)."""
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

ISSUE142_JS = r"""
() => {
  if (typeof computeSurfIntervalCore !== 'function') throw new Error('computeSurfIntervalCore missing');
  const air = { fN2: 0.79, fHe: 0, fO2: 0.21 };
  const tx2135 = { fN2: 0.44, fHe: 0.35, fO2: 0.21 };
  const ean32 = { fN2: 0.68, fHe: 0, fO2: 0.32 };
  const o2pure = { fN2: 0, fHe: 0, fO2: 1.0 };
  const base = { gfLowPct: 30, gfHighPct: 85, descentRate: 18 };

  const si01a = computeSurfIntervalCore({
    ...base, d1: 30, bt1: 25, d2: 30, bt2: 25, dive1Gas: air, dive2Gas: air,
  });
  const si01b = computeSurfIntervalCore({
    ...base, d1: 30, bt1: 25, d2: 30, bt2: 25, dive1Gas: air,
  });
  const si01 = si01a.minSI === si01b.minSI;

  const si03 = computeSurfIntervalCore({
    ...base, d1: 28, bt1: 12, d2: 26, bt2: 10, dive1Gas: tx2135, dive2Gas: tx2135,
  });
  const si02 = computeSurfIntervalCore({
    ...base, d1: 28, bt1: 12, d2: 26, bt2: 10, dive1Gas: tx2135, dive2Gas: ean32,
  });
  const si02lt03 = si02.minSI < si03.minSI && !si03.siCapped;

  const si04 = computeSurfIntervalCore({
    ...base, d1: 30, bt1: 25, d2: 6, bt2: 5, dive1Gas: air, dive2Gas: o2pure,
  });
  const si04near0 = si04.minSI === 0;

  const o2El = document.getElementById('siD2O2');
  const heEl = document.getElementById('siD2He');
  const errEl = document.getElementById('siD2GasErr');
  const minEl = document.getElementById('siMinResult');
  if (!o2El || !heEl || !errEl || !minEl) throw new Error('si D2 gas DOM missing');
  calcSurfInt();
  const prevO2 = o2El.value;
  const prevHe = heEl.value;
  const prevMin = minEl.textContent;
  o2El.value = '60';
  heEl.value = '50';
  calcSurfInt();
  const si05err = errEl.style.display !== 'none' && /impossible/i.test(errEl.textContent || '');
  const si05stable = minEl.textContent === prevMin;
  o2El.value = prevO2;
  heEl.value = prevHe;
  if (errEl) errEl.style.display = 'none';
  calcSurfInt();

  const sumEl = document.getElementById('siD2GasSummary');
  o2El.value = '32';
  heEl.value = '0';
  updateD2GasSummary('si');
  const siSummary = sumEl && sumEl.textContent === 'EAN32';
  o2El.value = prevO2;
  heEl.value = prevHe;
  updateD2GasSummary('si');

  return {
    si01, si02lt03, si04near0, si05err, si05stable, siSummary,
    si01min: si01a.minSI, si02min: si02.minSI, si03min: si03.minSI,
  };
}
"""


def main() -> int:
    from playwright.sync_api import sync_playwright

    print("=" * 60)
    print("Issue #142 — Dive 2 gas override regression (SI-01–SI-05)")
    print("=" * 60)

    with serve_www(ROOT) as base_url:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(120000)
            boot_app_page(page, base_url)
            data = page.evaluate(ISSUE142_JS)
            browser.close()

    cases = []
    for key, case_id, label in [
        ("si01", "ISSUE142-SI-01-INHERIT", "blank override matches dive1Gas baseline"),
        ("si02lt03", "ISSUE142-SI-02-EAN32", "EAN32 dive2 shortens SI vs same-trimix"),
        ("si04near0", "ISSUE142-SI-04-O2-SHALLOW", "O2 dive2 shallow profile needs no SI"),
        ("si05err", "ISSUE142-SI-05-INVALID-MIX", "O2+He>100 shows inline error"),
        ("si05stable", "ISSUE142-SI-05-NO-NAN", "invalid mix does not corrupt results"),
        ("siSummary", "ISSUE142-SI-SUMMARY", "summary chip shows EAN32 label"),
    ]:
        ok = bool(data.get(key))
        print(f"  {'✓' if ok else '✗'} {label}: {data}")
        cases.append(case_row(case_id, ok))

    code = 0 if all(row["status"] == "PASS" for row in cases) else 1
    finish_suite(ROOT, cases, code)
    return code


if __name__ == "__main__":
    main()
