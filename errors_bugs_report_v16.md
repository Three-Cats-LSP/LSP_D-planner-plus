# LSP D-Planner + CCR — Errors & Bugs Report v16

**Repo:** `Three-Cats-LSP/LSP_D-planner-CCR`  
**Version analysed:** v2.30.17 (commit `a3d819f`)  
**Date:** 2026-06-21  
**Audit result:** 324 checks, 0 failures  
**Scope:** Verification of BUG-71 fix plus full sweep. BUG-71 confirmed fixed. One new display bug found.

---

## Verification

**BUG-71** ✅ Fixed — `sacDomToLpm()` correctly converts cu_ft/min → L/min when `units === 'imperial'`. All three paths (Bühlmann `sacBottom`/`sacDeco`, VPM `sacBotVPM`/`sacDecoVPM`, CCR `sacDecoCcr`/`sacStress`) now use L/min internally. `_lastGasConsumed` stores correct litres. `calcGasPlan()` cross-check now valid in imperial.

---

## New Bug

### BUG-72 — VPM and emergency/contingency gas display shows litres labelled as "cu ft" in imperial

**File:** `index.html`  
**Severity:** MEDIUM  
**Locations:**

**VPM gas consumption block** (lines ~7612, 7621, 7624, 7639, 7643, 7647–7648, 7667):
```js
const reqDisp  = Math.round(reqL);          // reqL is in L (correct after BUG-71 fix)
const availDisp = usableL != null ? Math.round(usableL) : null;  // usableL also in L
// ...displayed with:
const volUnitV = units === 'imperial' ? 'cu ft' : 'L';  // label says cu ft
// → shows "2000 cu ft" when correct display is "70.6 cu ft"
```

**Bühlmann emergency/contingency gas block** (lines ~10863–10865):
```js
emergRows += `... ${Math.round(reqL)} ${volUnitV2} ...`;  // reqL in L, volUnitV2='cu ft' in imperial
```

Both blocks correctly compute the sufficiency comparison (`reqL` vs `avail` both in L — comparison is valid). Only the **display values** are wrong: litres are shown with a "cu ft" label without being converted.

The main **Gas Plan tab** (`calcGasPlan()`) is correct — it uses `gpVolDisp(litres)` which calls `litres * GP_CUFT_PER_L` to convert before display.

**Impact:** In imperial mode, gas volumes in the inline deco schedule gas summary and the emergency contingency gas card show raw litre values labelled as "cu ft". Example: a dive requiring 2000 L of bottom gas displays as "2000 cu ft" instead of "70.6 cu ft". The Gas Plan tab (separate page) shows the correct value.

**Fix:** In both blocks, convert `reqL` and `usableL` for display:
```js
const reqDisp  = units === 'imperial' ? (reqL  * CUFT_PER_LITRE).toFixed(1) : Math.round(reqL);
const availDisp = usableL != null
  ? (units === 'imperial' ? (usableL * CUFT_PER_LITRE).toFixed(1) : Math.round(usableL))
  : null;
```

---

## Additional Note

**`ccrSacDeco` and `ccrSacStress` labels always show "L/min"** even in imperial mode (lines ~2097, 2102). These fields are not converted by `convertNumericInput` (they stay in L/min regardless of unit selection), so the label is technically correct. However, a user in imperial mode sees all other SAC fields in cu_ft/min and these two in L/min — minor UX inconsistency. Not a calculation bug.

---

## Summary Table

| # | Severity | Area | Description |
|---|---|---|---|
| BUG-72 | MEDIUM | Display / Imperial | VPM and emergency gas blocks display L values labelled "cu ft" — wrong volume numbers in imperial mode |

