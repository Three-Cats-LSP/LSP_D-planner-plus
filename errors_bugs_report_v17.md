# LSP D-Planner + CCR — Errors & Bugs Report v17

**Repo:** `Three-Cats-LSP/LSP_D-planner-CCR`  
**Version analysed:** v2.30.23 (commit `37eb66d`)  
**Date:** 2026-06-21  
**Audit result:** 343 checks, 0 failures  
**Scope:** Verification pass 17. BUG-72 confirmed fixed. Two new bugs found.

---

## Verification

**BUG-72** ✅ Fixed — VPM (`reqDisp = gpVolDisp(reqL)`, line 7612) and emergency block (`reqDispE = gpVolDisp(reqL)`, line 10864) now use `gpVolDisp()` which correctly converts L → cu_ft in imperial mode.

Additional fixes verified:
- `ctxUseOCForPpo2(ctx)` → `ctxUseOCForPpo2(settings)` (ReferenceError fixed, ae01b7d) ✓
- `_zhlHeadless` preserved across `ZHLEngine.calculate()` (freeze fix, 03b91b4) ✓
- `lsp-test-harness.js` routing and `_zhlHeadless` assertion correct ✓

---

## New Bugs

### BUG-73 — `ZHLEngine.calculate()` headless CNS/OTU fallback uses OC ppO₂ for CCR dives — wrong CNS/OTU returned

**File:** `index.html`  
**Severity:** HIGH  
**Location:** `ZHLEngine.calculate()` headless CNS fallback, line ~11148

```js
const hCircuit  = s.circuit || prevCCR.circuit || 'OC';
const hBailout  = s.bailout != null ? s.bailout : (prevCCR.bailout === 'on');
const hPscrOnLoop = hCircuit === 'pSCR' && !hBailout;  // only pSCR

function headlessPpo2(depthM, fO2, fHe, runtimeMin) {
  if (hPscrOnLoop && ...) { /* pSCR: correct */ }
  return fO2 * pAmb;   // ← CCR falls here — wrong, should use setpoint
}
```

When `ZHLEngine.calculate()` is called with `settings.circuit = 'CCR'` (not bailout), `hPscrOnLoop` is false because it only checks `circuit === 'pSCR'`. CCR dives fall through to `fO2 * pAmb` (OC formula). The actual ppO₂ for a CCR diver is the maintained setpoint (e.g. 1.3 bar), not the diluent partial pressure (e.g. 0.21 × 5 = 1.05 bar at 40 m).

**Impact:** `ZHLEngine.calculate()` returns `totalCNS` and `totalOTU` at roughly 60–80% of the correct values for CCR dives (depending on depth and setpoint). This affects:
- Any test harness using `ZHLEngine.calculate()` with CCR settings (tests-verify.html, lsp-test-harness.js headless path)
- Any third-party code calling `ZHLEngine.calculate()` for CCR

The live DOM rendering path (interactive app) is correct — it uses `_ccrPpo2Opts()` and the CCR-aware `ppO2Check()`. Only the headless API result is wrong.

**Fix:** Add a CCR branch in `headlessPpo2`:
```js
const hCcrOnLoop = (hCircuit === 'CCR') && !hBailout;
// ...
function headlessPpo2(depthM, fO2, fHe, runtimeMin) {
  const pAmb = hAltP + depthM * hBAR;
  if (hPscrOnLoop ...) { /* existing pSCR branch */ }
  if (hCcrOnLoop && typeof getEffectiveSetpointAtDepth === 'function') {
    const sp = getEffectiveSetpointAtDepth(depthM, { circuit: 'CCR', ...ccrConfig }, hAltP);
    return Math.min(pAmb, Math.max(sp, fO2 * pAmb));
  }
  return fO2 * pAmb;
}
```

---

### BUG-74 — Version mismatch: `APP_VERSION`/`sw.js` at `2.30.23`, `package.json`/`build.gradle` still at `2.30.19`

**Files:** `package.json` line 3, `android/app/build.gradle` lines 10–11  
**Severity:** LOW

| File | Value |
|---|---|
| `index.html` `APP_VERSION` | `2.30.23` ✓ |
| `sw.js` `CACHE_VERSION` | `lsp-dplanner-ccr-v2.30.23` ✓ |
| `package.json` `version` | `2.30.19` ✗ |
| `android/app/build.gradle` `versionName` | `2.30.19` ✗ |
| `android/app/build.gradle` `versionCode` | `23019` ✗ |

Repeat of BUG-01/39 pattern — patch versions incremented rapidly (19 → 23) during bug fix cycles without updating all four files.

---

## Summary Table

| # | Severity | Area | Description |
|---|---|---|---|
| BUG-73 | HIGH | ZHLEngine headless / CCR | Headless CNS/OTU uses OC ppO₂ for CCR — should use setpoint. Returns ~60–80% of correct values |
| BUG-74 | LOW | Versioning | `package.json` and `build.gradle` stuck at `2.30.19`; `APP_VERSION` and `sw.js` at `2.30.23` |

