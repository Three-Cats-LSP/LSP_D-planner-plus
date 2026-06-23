# LSP D-Planner + CCR — Full Recheck Report v2.30.31

**Repo:** `Three-Cats-LSP/LSP_D-planner-CCR`  
**Version:** v2.30.31 (commit `e05bcf5`)  
**Date:** 2026-06-23  
**Audit result:** 441 passed, 0 failed  
**Scope:** Complete recheck of all fixes from BUG-86 through multi-level ZHL + latest two fix commits.

---

## Latest Fixes Verified

### 7e7ecaf — ZHL/VPM CCR validation errors routed through `engineValidationError`
- ZHLEngine `ccrVal` error now calls `engineValidationError(ccrVal)` ✅
- ZHLEngine "No levels" now uses `engineValidationError(...)` ✅
- All error shapes consistent: `{ error, code, field, errors[], stops[], plan[], totalRuntime, totalTime }` ✅

### bb26874 — VPM deco gas He normalization via `gasFractionsFromPct`
- `normalizedDecoGases` now uses `gasFractionsFromPct(g.o2, g.he)` ✅
- `gasFractionsFromPct`: `(he == null || he === '') ? 0 : Number(he)` matches `validateGasFractionsPct` convention ✅
- `label: "${f.o2Pct}/${f.hePct}"` uses whole-percent display values ✅

---

## Full Physics Verification

### pSCR Trimix (BUG-86)
```
computePSCRFractions: Tx 18/45 at 4 bar, 20 min
  sourceInert = fHe + fN2src = 0.82
  heShare = 0.45 / 0.82 = 0.5488
  n2Share = 0.37 / 0.82 = 0.4512
  → fO2=0.040, fHe=0.527, fN2=0.433, sum=1.000 ✅
```

### PSCR_MIN_PPO2 = 0.16 bar floor (BUG-88)
```
minLoopO2BarLiters = 0.16 × loopVol  (no pAmb)
→ min ppO2 at 4 bar = (0.16×10)/(10×4) × 4 = 0.16 bar ✅
→ min ppO2 at 7 bar = (0.16×10)/(10×7) × 7 = 0.16 bar ✅
```

---

## Validation Chain Verification

### ZHLEngine.calculate()
1. `validateCcrCalculationInputs(levels, s, decoGases)` — gas fractions + CCR setpoints + pSCR skip ✅
2. `validateZhlHeadlessProfile(levels)` — deepest-first + no re-descend ✅
3. DOM wired; `runDecoSchedule()` runs with `_zhlContinuationLevels` for multi-level ✅
4. Error returns all use `engineValidationError()` ✅

### VPMEngine.calculate()
1. `validateEngineInputs(levels, decoGases)` — gas fractions + depth/time ✅
2. `validateCcrCalculationInputs(levels, s, decoGases)` — CCR/pSCR (if rebreather circuit) ✅
3. `normalizedDecoGases` via `gasFractionsFromPct` — null He safe ✅

### validateCcrCalculationInputs
- pSCR early return after profile/gas check, before setpoint loop ✅
- `descentSP` default 0.7, `bottomSP` default 1.2, `decoSP` default 1.3 ✅

---

## Complete Fix Registry (BUG-86 → current)

| # | Fix | Status |
|---|-----|--------|
| BUG-86 | pSCR trimix `sourceInert = fHe + fN2src` | ✅ |
| BUG-87 | `__units__` saved/restored before fields | ✅ |
| BUG-88 | `minLoopO2BarLiters = PSCR_MIN_PPO2 × loopVol` (no pAmb) | ✅ |
| BUG-89 | `validateDecoInputs()` blocks negative/extreme depth/BT | ✅ |
| BUG-90 | EAN80 option in dg1Mix/dg2Mix | ✅ |
| BUG-91 | `renderTissueLoadChart` uses `gfHighInput` | ✅ |
| BUG-92 | Rec export reads `getElementById('gasMix')` | ✅ |
| BUG-93 | PWA manifest `"start_url": "./"` | ✅ |
| BUG-94 | SW offline `.then(cached => cached \|\| ...)` | ✅ |
| BUG-95 | pSCR skips setpoint validation in `validateCcrCalculationInputs` | ✅ |
| BUG-96 | CCR setpoint defaults applied before range check | ✅ |
| BUG-97 | `validateGasFractionsPct` handles NaN He without `\|\| 0` coercion | ✅ |
| BUG-98 | `decoGases` passed to `validateCcrCalculationInputs` | ✅ |
| BUG-99 | Percent convention in level gas validation | ✅ |
| BUG-100 | Raw DOM gas validated before `getBottomGasFractions()` clamping | ✅ |
| — | VPM empty-levels error: `code`, `plan[]`, `totalRuntime` added | ✅ |
| — | `validateZhlHeadlessProfile`: deepest-first + no re-descend | ✅ |
| — | `_zhlContinuationLevels` multi-level support | ✅ |
| — | `_zhlHeadlessDepth` nesting counter | ✅ |
| — | `gasFractionsFromPct`: null-safe He normalization | ✅ |
| — | All CCR/ZHL/VPM error returns use `engineValidationError()` | ✅ |

**441/441 audit checks. 0 new bugs found.**

