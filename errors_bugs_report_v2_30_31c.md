# LSP D-Planner + CCR — Errors & Bugs Report v2.30.31c

**Repo:** `Three-Cats-LSP/LSP_D-planner-CCR`  
**Version analysed:** v2.30.31 (commit `c852e5f`)  
**Date:** 2026-06-22  
**Audit result:** 437 passed, 0 failed  
**Scope:** Final verification pass for v2.30.31. No new bugs found.

---

## Fix Verified: VPM empty-levels error shape (ad77380)

The pre-existing `'No bottom segments defined'` VPM error return (identified in the v2.30.31b report) now matches the full ZHL/CCR error shape:

```js
return {
    error: 'No bottom segments defined',
    code: 'INVALID_PROFILE',
    stops: [],
    plan: [],
    totalTime: 0,
    totalRuntime: 0,
};
```

`code`, `plan: []`, and `totalRuntime: 0` added. ✅

---

## Comprehensive Verification

| Check | Result |
|---|---|
| BUG-86 pSCR trimix `sourceInert` normalization | ✅ |
| BUG-87 `__units__` persistence | ✅ |
| BUG-91 tissue chart reads `gfHighInput` | ✅ |
| BUG-94 SW offline `.then(cached =>)` | ✅ |
| BUG-95 pSCR early return before setpoint check | ✅ |
| BUG-96 CCR setpoint defaults (0.7 / 1.2 / 1.3) | ✅ |
| BUG-97 `validateGasFractionsPct` NaN He handling | ✅ |
| BUG-98 `decoGases` passed to `validateCcrCalculationInputs` | ✅ |
| BUG-99 Percent convention in level gas validation | ✅ |
| BUG-100 Raw DOM gas validation before clamping | ✅ |
| VPM CCR validation gate (`isRebreatherCircuit`) | ✅ |
| `collectDecoGasesPctFromDom` uses `getDomDecoGasPct` (percent, not fractions) | ✅ |
| `validateDomDecoGases` guards `!g` before `validateGasFractionsPct` | ✅ |
| `getDomDecoGasPct` unknown-mix fallback returns `null` (skipped safely) | ✅ |
| Differential report: 0 failures / 72 inconclusive / 0 missing required | ✅ |
| Version consistency: all files at 2.30.31 | ✅ |
| 437/437 audit checks | ✅ |

**No new bugs found. v2.30.31 is clean.**

