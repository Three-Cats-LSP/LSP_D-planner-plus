# LSP D-Planner + CCR — Errors & Bugs Report v2.30.31b

**Repo:** `Three-Cats-LSP/LSP_D-planner-CCR`  
**Version analysed:** v2.30.31 (commit `2b8b098`)  
**Date:** 2026-06-22  
**Audit result:** 436 passed, 0 failed  
**Scope:** Full verification of commits 9766de9 → 2b8b098 (BUG-95/96 fix + BUG-97–100 new validation hardening). No new bugs found.

---

## Verification

### BUG-95 / BUG-96 — Confirmed fixed (9766de9)

`validateCcrCalculationInputs` now:
- Returns early for pSCR after profile/gas checks — no setpoint validation for pSCR ✅
- Applies defaults (`descentSP=0.7`, `bottomSP=1.2`, `decoSP=1.3`) for omitted CCR setpoints ✅

---

## New Fixes: BUG-97 through BUG-100 (01e068d, b68196a)

### BUG-97 — `validateGasFractionsPct` correctly handles NaN He without `|| 0` coercion

New utility function validates gas fractions in percent space. Specifically handles the case where `parseFloat('')` returns `NaN` for an empty trimix He field — the value is not silently coerced to 0 but correctly rejected as invalid. ✅

### BUG-98 — `validateCcrCalculationInputs` now receives and validates deco gases

Both `ZHLEngine.calculate()` (line 11353) and the UI path (line 9902) now pass `decoGases` as a third argument. Invalid deco gas fractions (negative, over 100%, O2+He > 100%) are caught before the engine runs. ✅

### BUG-99 — Percent convention correctly applied in level gas validation

Gas values passed as integers (e.g. `o2: 21`, `he: 45`) are correctly recognized as percent (`> 1` check) by `validateGasFractionsPct`. Values passed as fractions (`o2: 0.21`) are also handled. ✅

### BUG-100 — Raw DOM gas inputs validated before `getBottomGasFractions()` clamping

New functions `getDomBottomGasPct()`, `getDomDecoGasPct(idx)`, and `validateDomDecoGases()` read gas inputs at the DOM level before `getBottomGasFractions()` applies clamping. This catches user-entered NaN, negative, or over-limit values before they are silently normalized. Called from `runDecoSchedule()` (gated to CCR/pSCR mode) and `validateCcrGasConfiguration()`. ✅

---

## Additional Cross-checks

| Check | Result |
|---|---|
| VPM `calculate()` now validates CCR inputs at entry (mirrors ZHLEngine) | ✅ |
| VPM CCR validation error return includes `totalRuntime: 0` | ✅ |
| `validateDomDecoGases` correctly gated to `!_zhlHeadless && isRebreatherCircuit` | ✅ |
| `getDomDecoGasPct` covers all dg1/dg2Mix options: none, ean50, ean80, o2, custom, trimix | ✅ |
| Trimix He field empty (NaN) correctly blocked | ✅ |
| Version consistency: all files at 2.30.31 | ✅ |
| 436/436 audit checks | ✅ |
| CCR differential: 21 scenarios, 0 failures | ✅ |

**No new bugs found.**

