# LSP D-Planner+CCR — Errors & Bugs Report v21

**App version:** v2.30.28  
**Audit date:** 2026-06-21  
**Previous report:** errors_bugs_report_v20.md (v2.30.26 — BUG-75 fixed)  
**Audit tool:** audit.py — 363 checks, 0 failures  
**Scope:** v2.30.25–26 refactor verification + BUG-76/BUG-77 fixes + verify test calibration.

---

## Fix status

| Bug | Status | Fix summary |
|-----|--------|-------------|
| BUG-75 | **FIXED** (v2.30.26) | `ccrDiluentSurfaceLpm()` pSCR branch: `metRate × PSCR_DEFAULT_BYPASS_RATIO` |
| BUG-76 | **FIXED** (v2.30.28) | `tests-massive.html` hang at ~20/234 — `_zhlHeadless` leak triggered full DOM render |
| BUG-77 | **FIXED** (v2.30.28) | pSCR OTU/CNS plan walk: segment-start `scrRuntimeMin`, ascent depth, shared VPM totals |

---

## BUG-75 — Verified fixed in v2.30.26

```js
if (ccr.circuit === 'pSCR' && !ccr.bailout) {
  return metRate * PSCR_DEFAULT_BYPASS_RATIO;
}
```

Result: `1.5 × 10 = 15 L/min` at default settings (was ~93 L/min for EAN32 at 40 m).

**Regression coverage:** `tests-verify.html` section I, `tests-massive.html`, audit.py GROUP 58.

---

## v2.30.25 refactor — `computePlanExposureTotals()` (verified)

Shared OTU/CNS integration for ZHLEngine headless path. Correctness confirmed for pSCR depletion, CCR setpoint phases, OC/bailout fallback, and cumulative `run` injection on plan segments.

v2.30.28 extends this helper with `planSegDepthM()`, segment-start `scrRuntimeMin`, and VPM `buildResult()` totals from the same walk (BUG-77).

---

## BUG-76 — Massive suite freezes at ~20/234

**Symptom:** `tests-massive.html` auto-run stops at **20/234**. Progress bar frozen; browser tab unresponsive.

**Root cause:**

1. `fastRDS()` cleared `_zhlHeadless` in a `finally` block after setup.
2. Deferred app callbacks (`appSettings.load`, `setDecoAlgorithm`, `setAltitude`) ran with `_zhlHeadless === false`.
3. Full DOM `runDecoSchedule()` on saved 40m/30min profile blocked the JS thread.
4. `setDecoAlgorithm()` / `setCustomGF()` called `renderNDLTable()` unconditionally.

**Fix (v2.30.28):**

| File | Change |
|------|--------|
| `index.html` | Early `_zhlHeadless` when `?massiveSuite=1`; guard `renderNDLTable()` in algo/GF setters |
| `tests-massive.html` | `enterMassiveHeadless()`, `installMassiveSuiteGuards()`, headless-only `fastRDS()` + stub DOM |
| `tests-massive-main.html` | Same headless guards on `runCalc()` |

**Regression coverage:** audit.py GROUP 60.

---

## BUG-77 — pSCR OTU/CNS plan exposure walk

**Symptom:** `tests-pscr-otu-cns.html` failures — VPM `totalOTU` vs plan recompute ≈ 0; ZHL CNS mismatch; VPM vs ZHL OTU diverge.

**Root cause:**

1. `depth=0` on VPM ascent segments (only `seg.depth` checked).
2. `scrRuntimeMin` at end-of-segment → depleted loop → zero OTU on recompute.
3. VPM `buildResult()` used inline `vpmAccumPpo2` instead of shared plan walk.

**Fix (v2.30.28):**

```js
// planSegDepthM() — depth / endDepth / from-to midpoint
// scrRuntimeMin = Math.max(0, runEnd - dur)
// VPM buildResult → totalOTU/totalCNS from computePlanExposureTotals()
window.computePlanExposureTotals = computePlanExposureTotals;
```

**Regression coverage:** `tests-pscr-otu-cns.html`, audit.py GROUP 59.

---

## Test calibration — `tests-verify.html` CCR section

**Issue:** "Above setpoint depth: zero inert loading" used `pAmb = SP + ppH2O + 0.01` — above the crossover threshold, so `pN2 ≈ 0.01` bar is correct engine behaviour, not a bug.

**Fix:** Test now uses `pAmb = sp + ppH2O` (at crossover) with epsilon tolerance. Badge display shows PASS/FAIL per test instead of section-wide WARN.

---

## Open bugs

**None in CCR repo.**

---

## Cumulative status

| Report | Version | Bugs | Status |
|--------|---------|------|--------|
| v18–v19 | v2.30.24 | BUG-75 | ✅ Fixed (v2.30.26) |
| v20 | v2.30.26 | BUG-75 + test calibration | ✅ Complete |
| **v21** | **v2.30.28** | **BUG-76, BUG-77 + verify calibration** | **✅ Complete** |
