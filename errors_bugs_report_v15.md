# LSP D-Planner + CCR — Errors & Bugs Report v15

**Repo:** `Three-Cats-LSP/LSP_D-planner-CCR`  
**Version analysed:** v2.30.16 (commit `7f1a3eb`)  
**Date:** 2026-06-21  
**Audit result:** 323 checks, 0 failures  
**Scope:** Verification of BUG-69/70 fixes plus full deep audit. Both v14 bugs confirmed fixed. One new bug found.

---

## Verification

| Bug | Fix | Status |
|---|---|---|
| BUG-69 — `computeSurfaceGF` hardcoded `P_surf=1.0` | Now `const P_surf = altSurfaceP` | ✅ Fixed |
| BUG-70 — Stress reserve bottom-depth only | `addBailoutStressReserve()` distributes across bottom + all deco stop depths | ✅ Fixed |

`addBailoutStressReserve()` correctly deduplicates depths, splits `reserveMin` evenly across all dive phases, and calls `getBailoutReserveMixLabel()` at each depth to select the appropriate gas. Both Bühlmann (line 10550) and VPM (line 7528) paths call it. Implementation verified clean.

---

## New Bug

### BUG-71 — Gas consumption calculated in cu_ft·bar in imperial mode — Gas Plan sufficiency comparison broken

**File:** `index.html`  
**Location:** `runDecoSchedule()` lines ~10412–10413; `runVPMSchedule()` line ~7506; `ccrGasLitres()` line ~5981

```js
// Gas consumption: SAC read raw from DOM (cu_ft/min in imperial)
const sacBottom = parseFloat(document.getElementById('sacBottom')?.value) || 20; // cu_ft/min if imperial
// ...
function ccrGasLitres(label, depthM, durMin, sac) {
  const absP = altSurfaceP + depthM * BAR_PER_METRE;  // bar
  return sac * absP * durMin;  // cu_ft/min × bar × min = cu_ft·bar (NOT litres in imperial)
}
```

When units = `'imperial'`, `convertNumericInput('sacBottom', v => v * CUFT_PER_L, ...)` converts the DOM value from L/min to cu_ft/min. Subsequent gas consumption calls use this raw cu_ft/min value multiplied by depth pressure in bar, yielding `cu_ft·bar` — a dimensionally incorrect unit.

`_lastGasConsumed` then stores these `cu_ft·bar` values. `calcGasPlan()` calls `gpRequiredFor()` which returns these values as `reqL`, then compares against `gpSizeL() × gpPresBar()` which correctly returns `L·bar`. The comparison is therefore between different unit systems.

**Impact example:** 40 m dive, air, 20 min BT at sea level. SAC = 0.71 cu_ft/min (20 L/min converted).  
- Correct metric: `20 L/min × 5 bar × 20 min = 2000 L`  
- Incorrect imperial: `0.71 cu_ft/min × 5 bar × 20 min = 71 cu_ft·bar`  
- `gpVolDisp(71)` → `71 × 0.0353 = 2.5 cu_ft` displayed as required  
- Actual available: `42 cu_ft × (200-50 PSI / 14.5) = 42 × 10.3 = 433 L·bar → gpVolDisp = 15.3 cu_ft`  
- Gas plan shows `2.5 cu_ft needed` vs `15.3 cu_ft available` → appears massively sufficient, when the correct answer (in metric) is 2000 L needed vs ~4330 L available.  
- The numeric ratio happens to produce a similar "ok" verdict by coincidence in this case, but the absolute values displayed are wrong and edge-case dives (long deco) will show incorrect sufficiency status.

**Fix:** Convert `sacBottom` and `sacDeco` from cu_ft/min to L/min before use:
```js
const sacBottom = (parseFloat(document.getElementById('sacBottom')?.value) || 20)
  * (units === 'imperial' ? 1 / CUFT_PER_L : 1);  // always in L/min internally
```
Or equivalently, convert inside `ccrGasLitres()` if the units flag is accessible there.

**Note:** The cylinder SIZE conversion (BUG-37, BUG-40) was fixed by converting `szRaw` to litres before the capacity calculation. The SAC conversion was not applied in the same fix, leaving this parallel bug unresolved.

---

## Summary Table

| # | Severity | Area | Description |
|---|---|---|---|
| BUG-71 | MEDIUM | Gas plan / Imperial | SAC in cu_ft/min used directly in gas consumption — `_lastGasConsumed` in cu_ft·bar, Gas Plan sufficiency wrong in imperial |

