# LSP D-Planner + CCR — Errors & Bugs Report v2.30.31

**Repo:** `Three-Cats-LSP/LSP_D-planner-CCR`  
**Version analysed:** v2.30.31 (commit `70efac0`)  
**Date:** 2026-06-22  
**Audit result:** 423 passed, 0 failed  
**Scope:** Full verification of v2.30.31 changes (Issue #2 CCR differential harness + fixes). Two new bugs found in `validateCcrCalculationInputs`.

---

## What Changed in v2.30.31

### New: CCR Engine Differential Test Harness (`a138fc7`, `f0aa694`)
17 scenario fixtures, MultiDeco/DiveKit/Abysner/Subsurface goldens, CI integration, Playwright runner. 21 scenarios: 0 failures, 72 inconclusive (no golden captures), all confirmed differences documented in `expected-differences.json`.

### Fixed: ZHL repetitive surface-interval offgas used VPM-internal struct references (`650a5ce`)
Inside `ZHLEngine.calculate()`, the repetitive dive surface interval offgassing block was computing `kN2 = Math.LN2 / ZHL16C_N2[i].ht` and `kHe = Math.LN2 / ZHL16C_He[i].ht` — these are VPM-internal structs not accessible in the Bühlmann engine scope. Now correctly uses `Math.LN2 / ZHL16C[i][0]` (global N2 HT) and `Math.LN2 / ZHL16C_HE_HT[i]` (global He HT). ✅

### New: `validateCcrCalculationInputs()` at ZHLEngine boundary (`650a5ce`)
Validates profile levels, gas fractions, and setpoint ranges before running the engine. Called from both `runDecoSchedule()` (UI path) and `ZHLEngine.calculate()` (headless path). ✅

---

## New Bugs

### BUG-95 — `validateCcrCalculationInputs()` rejects pSCR calls — setpoints semantically unused for pSCR but validated against CCR range

**File:** `index.html` lines ~11200–11213  
**Severity:** HIGH

```js
for (const [name, value, min, max] of [
  ['descent', s.descentSetpoint, 0.5, 1.0],   // pSCR callers pass 0
  ['bottom',  s.bottomSetpoint || s.setpoint, 0.7, 1.6],  // pSCR callers pass 0
  ['deco',    s.decoSetpoint || s.setpoint,   0.7, 1.6],  // pSCR callers pass 0
]) {
  if (!Number.isFinite(value) || value < min || value > max) {
    errors.push(...)  // fires for all three when circuit='pSCR'
  }
}
```

`isRebreatherCircuit('pSCR') = true`, so pSCR inputs reach the setpoint validation. pSCR callers (tests, headless API) pass `{setpoint:0, descentSetpoint:0, bottomSetpoint:0, decoSetpoint:0}` — sentinel zeros indicating that setpoints are not applicable for pSCR. All three checks fire (`0 < 0.5`, `0 < 0.7`, `0 < 0.7`), and `ZHLEngine.calculate()` returns `{error: 'descent setpoint must be between 0.5 and 1.0 bar'}`.

**Impact:** Any headless pSCR call to `ZHLEngine.calculate()` fails immediately with a setpoint error. The pSCR OTU/CNS tests in `tests-pscr-otu-cns.html` call `WIN.ZHLEngine.calculate(levels, [], pscrSettings())` — these would return errors instead of plans (browser test status depends on whether assertion checks `r.error`).

**Fix:** Skip setpoint validation for pSCR:
```js
if (circuit !== 'pSCR') {
  for (const [...] of [...]) { /* setpoint range checks */ }
}
```

---

### BUG-96 — `validateCcrCalculationInputs()` rejects CCR callers that omit `descentSetpoint` — no default applied

**File:** `index.html` line ~11201  
**Severity:** MEDIUM

When `s.descentSetpoint` is `undefined` (not explicitly passed), `!Number.isFinite(undefined)` is `true` in JavaScript — the function pushes an `INVALID_SETPOINT` error and returns `ok: false`. The descent setpoint has a well-defined default of 0.7 bar everywhere else in the engine (`getCCRSettingsFromDOM()` returns `|| 0.7`; `mergeCCRSettings()` applies the DOM default).

**Impact:** Any headless `ZHLEngine.calculate()` call with `{circuit:'CCR', setpoint:1.3}` (without explicit `descentSetpoint`) returns an error instead of a plan. Callers following existing API patterns like `tests-verify.html` Section I tests (which pass `descentSetpoint:0.7` explicitly) are unaffected, but any new caller using the minimal CCR settings signature will be unexpectedly rejected.

**Fix:** Apply the same defaults as `getCCRSettingsFromDOM()`:
```js
const descentSP = s.descentSetpoint != null ? Number(s.descentSetpoint) : 0.7;
const bottomSP  = s.bottomSetpoint  != null ? Number(s.bottomSetpoint)  : (s.setpoint != null ? Number(s.setpoint) : 1.2);
const decoSP    = s.decoSetpoint    != null ? Number(s.decoSetpoint)    : (s.setpoint != null ? Number(s.setpoint) : 1.3);
```

---

## Summary Table

| # | Severity | Area | Description |
|---|---|---|---|
| BUG-95 | HIGH | ZHLEngine / pSCR | `validateCcrCalculationInputs` fires for pSCR setpoint:0 — all pSCR headless calls rejected |
| BUG-96 | MEDIUM | ZHLEngine / CCR | `validateCcrCalculationInputs` rejects CCR calls without explicit `descentSetpoint` — no default |

