# LSP D-Planner + CCR — Errors & Bugs Report: Multi-Level ZHL & API Hardening

**Repo:** `Three-Cats-LSP/LSP_D-planner-CCR`  
**Version analysed:** v2.30.31 (commit `6f14f92`)  
**Date:** 2026-06-23  
**Audit result:** 440 passed, 0 failed  
**Scope:** Full verification of commits 27d01ae / bd16163 / 80b233d (ZHL multi-level headless profiles, profile shape validation, differential iframe stabilization).

---

## New Features Verified Clean

### ZHL Multi-Level Headless Profiles (27d01ae)

`ZHLEngine.calculate()` now accepts multi-segment profiles: `[{depth:40,time:28}, {depth:20,time:15}]` where the first segment is deepest. `splitZhlProfileLevels()` splits into primary (deepest) + continuation (shallower holds). `runDecoSchedule()` processes each phase in a loop via `_zhlContinuationLevels` + `_zhlAscentFloors`.

Key checks:
- `rt` (runtime) accumulates correctly across all phases ✓
- `tissues` updated at each continuation level via `zhlLoadConst` ✓
- `steps` array builds across all phases → single `collapsed` output ✓
- `decoZoneEntered = _zhlPhaseIdx > 0` correctly treats subsequent phases as already in deco ✓
- `firstStopDepth` reset to 0 per phase → GF line re-anchors at each phase's first stop ✓
- `_zhlHeadlessDepth` nesting counter prevents state loss on nested calls ✓
- `prevContLevels` / `prevDecoDepth` / `prevDecoBT` restored on both success and catch ✓
- Multi-level only active in headless mode (`window._zhlHeadless`) — UI mode unaffected ✓

### Profile Shape Validation (bd16163)

`validateZhlHeadlessProfile(levels)`: rejects profiles where deepest segment is not first, or where any later segment is deeper than its predecessor. Returns `INVALID_PROFILE` with descriptive message. Called before DOM wiring in `ZHLEngine.calculate()`. ✓

### CCR Differential Iframe Stabilization (80b233d)

Two-pass readiness check (`enginesReady` + 50 ms settle re-verify) + `armHeadless` using new `_zhlHeadlessDepth` counter. Fixes CCR-C1 flake on first scenario. ✓

---

## Minor Inconsistency (non-blocking)

### ZHLEngine CCR validation error return missing `errors` array and `totalTime`

**Location:** `ZHLEngine.calculate()` lines ~11510–11520  

```js
if (!ccrVal.ok) {
  const e = ccrVal.errors[0];
  return {
    error: e.message,
    code: e.code,
    field: e.field || null,
    stops: [],
    plan: [],
    totalRuntime: 0,    // ← present
    // totalTime: 0     ← missing (VPM error returns have this)
    // errors: ccrVal.errors  ← missing (engineValidationError includes this)
  };
}
```

The profile shape and VPM error paths use `engineValidationError()` which includes `errors: validation.errors` and `totalTime: 0`. The CCR validation error path returns an inline object that lacks both. Callers checking `result.totalTime` or `result.errors` would get `undefined` on this specific path.

**Severity:** Low — no known callers currently depend on `totalTime` or `errors` array from ZHLEngine CCR error returns.

---

## Summary

| Item | Status |
|---|---|
| Multi-level ZHL headless profiles | ✅ Clean |
| Profile shape validation (re-descend, deepest-not-first) | ✅ Clean |
| CCR differential iframe stabilization | ✅ Clean |
| `validateEngineInputs` + `engineValidationError` | ✅ Clean |
| VPM deco gas `he/100` null safety (validated before map) | ✅ Clean |
| ZHLEngine CCR error return missing `errors`/`totalTime` | ⚠️ Minor inconsistency |
| 440/440 audit checks | ✅ |

