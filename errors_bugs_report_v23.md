# LSP D-Planner + CCR — Errors & Bugs Report v23

**Repo:** `Three-Cats-LSP/LSP_D-planner-CCR`  
**Version analysed:** v2.30.29 (commit `88481ef`)  
**Date:** 2026-06-21  
**Audit result:** 374 checks, 0 failures  
**Scope:** Verification pass 23. One bug from v22 remains open; no new bugs found.

---

## Verification

### Improvements in v2.30.29 (commit `4fdbcc6`)

**`accumulateHeadlessPlanExposure()`** — new function called from inside `runDecoSchedule()` before `window._lastPlan` is set. Produces `totalOTU` and `totalCNS` directly from the collapsed deco steps with full CCR/pSCR awareness:

- Uses **baked `pO2`** values from each collapsed step (set by `ppO2Check` with `_ccrPpo2Opts` during deco schedule construction) when available — zero extra computation, maximum accuracy ✓
- For pSCR ascent segments without baked ppO2: computes sub-steps at midpoint runtime to track O₂ depletion across the segment ✓
- `ZHLEngine.calculate()` now prioritises `lp.totalCNS/totalOTU` (from this function) over the `computePlanExposureTotals` fallback — the fallback is only exercised if `_lastPlan` is absent ✓
- Prior-dive O₂ carry (`_priorDiveCarry`) correctly seeded into accumulator ✓

**VPM path** continues to use `computePlanExposureTotals(normPlan, settings, ...)` which is correct and uniform across all circuit types ✓

---

## Open Bug

### BUG-77 (still open) — `dg1Mix` and `dg2Mix` not in `DECO_FIELDS` — deco gas 1/2 mix selectors not persisted

**Status:** ⚠️ Still open after v2.30.29

`'dg1Mix'`, `'dg2Mix'`, `'dg1CustomO2'`, `'dg2CustomO2'` remain absent from `DECO_FIELDS` (verified in line ~17510). `'decoGas'` was added in v2.30.28, but the deco gas 1 and 2 selectors were not.

**Impact:** Users lose their configured deco gas 1 and gas 2 mixes (e.g. EAN 50, 100% O₂) on every page reload. The cylinder sizes/pressures (`cylDg1_size`, etc.) are saved, but the gas selection itself is not.

**Fix:** Add to `DECO_FIELDS`:
```js
'dg1Mix', 'dg1CustomO2', 'dg2Mix', 'dg2CustomO2',
```

---

## Summary

| # | Severity | Status | Description |
|---|---|---|---|
| BUG-77 | LOW | ⚠️ Still open | `dg1Mix`/`dg2Mix` not in `DECO_FIELDS` — deco gas mix selectors lost on reload |

**No new bugs found in v2.30.29.**

