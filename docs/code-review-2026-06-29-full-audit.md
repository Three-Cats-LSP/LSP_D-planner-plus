# LSP D-Planner+ — Full Codebase Audit Report
**Version:** v2.53.00  
**Audit Date:** 2026-06-29  
**Head Commits Reviewed:** `3c1922f` (issue #130), `b2ad2ee` (issue #128), `692fa77` (issue #127), `9b5dcf8`/`ed8c6cb` (issue #125)  
**Scope:** Full engine layer + UI layer + tooling + service worker — all open audit issues synthesised  
**Method:** Multi-pass static audit, 10-angle independent-finder method, mirror rule applied throughout  

---

## Summary

| Severity   | Count | Status |
|------------|-------|--------|
| 🔴 CRITICAL | 4     | Open — release-blocking |
| 🟠 HIGH     | 13    | Open |
| 🟡 MEDIUM   | 14    | Open |
| 🔵 LOW      | 7     | Open |
| **Total**   | **38** | **NOT RELEASE-CLEAN** |

**Files audited:**
- `zhl-physics-core.js`
- `zhl-gas-core.js`
- `zhl-ccr-core.js`
- `zhl-schedule-core.js`
- `zhl-engine-bundle.js`
- `vpm-engine-core.js`
- `vpm-engine-bundle.js`
- `index.html`
- `sw.js`
- `tools/build_zhl_bundle.py`
- `tools/check_engine_parity.py`
- `.github/workflows/ci.yml`

---

## 🔴 CRITICAL (4)

### C-01 — `ppO2Check` variable shadowing: inner `const fO2` hides outer `const fO2`
**Files:** `zhl-engine-bundle.js` lines 321, 327 · `zhl-gas-core.js` lines 317, 323  
**Issue:** `#130`

The function declares `const fO2 = 1 - fN2 - fHeVal` at the outer scope, then inside the CCR `if`-block re-declares `const fO2 = opts.fO2 != null ? opts.fO2 : o2frac`. The inner const is valid ES6 block scope, so no syntax error fires — but the outer `fO2` is computed and **never used on the CCR path**. The naming collision is a latent correctness hazard: any future refactor that removes the `if`-block braces or reorders declarations will silently use the wrong O₂ fraction in safety-critical decompression math.

**Fix:** Rename inner CCR variable to `ccrFO2` or `inspFO2`.

---

### C-02 — `runZhlScheduleCore` deco ascent rate default is 9 m/min; `buildZhlScheduleParamsFromEngine` passes 3 m/min — dead code masks dangerous fallback
**Files:** `zhl-engine-bundle.js` lines 748–749, 1405–1406  
**Issue:** `#130`

`runZhlScheduleCore` uses `?? 9` as fallback for `decoAscentRate` and `surfaceAscentRate`. `buildZhlScheduleParamsFromEngine` (the standard call path) always passes `|| 3`. The `?? 9` is dead on the normal path but fires at 3× the intended rate for any direct caller — including `zhl-schedule-core.js`. A deco ascent at 9 m/min produces dangerously short schedules.

**Fix:** Change fallback at lines 748–749 from `?? 9` to `?? 3`, or add a guard that throws when the field is absent.

---

### C-03 — `getEffectiveSetpointAtDepth` `deepestCross` guard intercepts before per-zone logic — `decoSP` never returned for any realistic dive
**Files:** `zhl-ccr-core.js` lines 56–79 · `zhl-engine-bundle.js` (mirror)  
**Issue:** `#128`

The `if (depthM > deepestCross) return bottomSP` shortcut fires for every depth deeper than the shallowest crossing (~3 m on a typical 3-SP CCR profile), making the per-crossing branch at lines 70–78 unreachable. For `decoSP > bottomSP` configurations the bottom phase is under-loaded.

**Fix:** Remove the `deepestCross` shortcut. Compare `depthM` against individual crossing depths in descending physical order.

---

### C-04 — CCR inert PP denominator uses `(1 − fO2_diluent)` instead of `(fN2d + fHe)` — overstates N₂/He partial pressures for trimix diluents
**Files:** `zhl-ccr-core.js` lines 105–113 · `zhl-engine-bundle.js` (mirror)  
**Issue:** `#128`

In the primary CCR branch, `den = max(0.001, 1 - fO2)` is only algebraically correct when `fHe = 0`. For trimix or EANx diluents, `(1 − fO2)` diverges from `(fN2d + fHe)`, producing a pN₂ or pHe that can exceed physically available pressure. The shallow (below-setpoint) branch already uses the correct `inertSrc = max(0.001, fHe + fN2d)`.

**Fix:** Replace `den = max(0.001, 1 - fO2)` with `den = max(0.001, fN2d + fHe)` — matching `ccrLoopGasBelowSetpoint`.

---

## 🟠 HIGH (13)

### H-01 — `getActiveGas` fallback hardcodes `fHe: 0` — trimix bottom-gas helium silently ignored on ascent
**Files:** `zhl-gas-core.js` ~line 131  
**Issue:** `#127`

When no deco-gas switch qualifies, `getActiveGas` returns `{ fN2: bottomFN2, fHe: 0, label: … }`. No `bottomFHe` parameter is accepted. All helium off-gassing between bottom depth and the first switch depth is computed as `fHe = 0` — non-conservative for trimix bottom gas.

**Fix:** Add `bottomFHe` parameter; return `fHe: bottomFHe` in the fallback. Update all call sites.

---

### H-02 — `ppO2Check` OC path clamps `fO2` to 0 on float rounding overflow — suppresses toxicity warning
**Files:** `zhl-gas-core.js` ~line 136  
**Issue:** `#127`

`Math.max(0, 1 - fN2 - fHeVal)` silently returns `0.00` for a 10/90 trimix when float rounding pushes the sum above 1. ppO2 reads `0.00`, suppressing any CNS toxicity advisory.

**Fix:** Validate `fO2 < 0` explicitly and return an error string rather than clamping to 0.

---

### H-03 — `ndlClearAtDepth` local `gfAt` closure ignores `shallowGradient` mode — NDL is optimistic
**Files:** `zhl-physics-core.js` lines ~159–164  
**Issue:** `#127`

The local `gfAt` closure always interpolates as if `shallowGradient = true`. When `shallowGradient = false` is active, NDL values allow the diver closer to the deco limit than the planner intends.

**Fix:** Replace local closure with a call to `gfAtDepth(d, gfL, gfH, firstStop, lastStop, shallowGradient)`. Thread `shallowGradient` through `ndlClearAtDepth` and `buhNDL`.

---

### H-04 — `runContingencyScenario` missing `try/finally` — main-plan DOM permanently corrupted on error
**File:** `index.html` lines ~13821–13857  
**Issue:** `#127`

If `runDecoSchedule()` throws inside the contingency swap block, execution exits before the DOM restore and `_contingencyRunning = false`. All subsequent calculations, gas consumption, PDF export, and NDL display operate on contingency data. Recovery requires a full page reload.

**Fix:** Wrap swap-call-restore in `try { … } finally { /* DOM restore + flag reset */ }`.

---

### H-05 — `computePSCRFractions` ppO2Drop altitude scaling is inverted — understates inert loading at altitude
**Files:** `zhl-ccr-core.js` ~line 122 · `zhl-engine-bundle.js` ~line 479 (mirror — identical)  
**Issue:** `#127`

`ppO2Drop = (metO2 / loopVol) * (pAmb / altSurfaceP)`. The Baker pSCR formula yields a constant `ΔppO2 = VO2 / VL`. The altitude factor makes the drop shrink at altitude, so the loop appears oxygen-richer than it is — understating inert loading for altitude pSCR dives (non-conservative).

**Fix:** Re-examine the intended formula. If depth-independent Baker is correct, remove the `* (pAmb / altSurfaceP)` factor. Apply to canonical source and regenerate bundle.

---

### H-06 — ZHL worker may not call `applyEnvironment` — altitude dives use sea-level pressure in worker
**Files:** `zhl-schedule-worker.js` · `zhl-engine-bundle.js` `calculate` function  
**Issue:** `#127`

`environment` is passed to `calculate()` but whether `applyEnvironment()` is actually called before physics runs is unverified. The main thread calls `_syncZhlBundleEnv()` before every calculation; the worker has no equivalent confirmed mechanism.

**Fix:** Verify or add explicit `ZhlEngineBundle.applyEnvironment(environment)` at the start of the worker's `calculate` path.

---

### H-07 — `validateHypoxicDecoGas` `heVal > 0` bypass skips all validation — accepts `O2=0, He=100`
**Files:** `zhl-gas-core.js` lines 92–110  
**Issue:** `#128`

Any helium-containing gas bypasses hypoxic validation unconditionally. A data-entry error like 0/100 passes silently; the planner later rejects the gas at all depths without explaining why.

**Fix:** Add a guard: if `(o2 + heVal > 1.0 + 1e-6)` emit `ERR_TOTAL_EXCEEDS_100`. Add a separate warning for `heVal > 0` gases where ppO2 at declared MOD is below `PSCR_MIN_PPO2`.

---

### H-08 — `_diveRuntimeMin` incremented on CCR path only — name implies total runtime; semantics incorrect for bailout dives
**Files:** `zhl-schedule-core.js` lines 46–57  
**Issue:** `#128`

On OC dives the counter stays 0. On a bailout-to-loop dive, runtime is behind real elapsed time after the OC phase. No comment documents the intentional asymmetry.

**Fix:** Rename to `_ccrLoopElapsedMin`, or maintain a parallel `_totalElapsedMin` that increments unconditionally.

---

### H-09 — VPM dedup incomplete: `vpm-engine-bundle.js` is a manual mirror copy — no `build_vpm_bundle.py`
**Files:** `vpm-engine-bundle.js` · `vpm-engine-core.js` (entire files)  
**Issue:** `#125`

The Tier-3 dedup eliminated the ZHL CCR mirror problem but left the VPM pair as a hand-maintained mirror. Any patch to `vpm-engine-core.js` not also applied to `vpm-engine-bundle.js` silently leaves the worker on old code. No CI check catches VPM drift.

**Fix:** Create `tools/build_vpm_bundle.py` on the same pattern as `build_zhl_bundle.py`. Add to `build:bundles` and `bundle-sync` CI job. Add VPM parity to `check_engine_parity.py`.

---

### H-10 — `applyNuclearRegeneration` double-call: #124 M-2 fix is incomplete in both VPM files
**Files:** `vpm-engine-bundle.js` lines 1433, 1656 · `vpm-engine-core.js` lines 1429, 1652  
**Issue:** `#125`

The inter-level call at lines 1433/1429 was not removed. Two calls with different time arguments apply exponential decay twice, inflating critical radii and yielding non-conservative deco on multi-level dives.

**Fix:** Remove the `applyNuclearRegeneration` call inside `runInterLevelDecoAscent`. Keep only the post-bottom call with `bottomPhaseRuntime`. Apply to both files (H-09 VPM dedup will automate this going forward).

---

### H-11 — `_restoreFields` suppresses ALL `change` events during restore loop — UI post-reload broken
**File:** `index.html` lines 16484–16503  
**Issue:** `#125`

`_restoreInProgress = true` gates the `dispatchEvent` call with `!this._restoreInProgress`, which is always `false` during the loop. All UI handlers that react to restored values (CCR sub-panels, custom gas toggles, narcosis selects, min-deco profile switches) are silently skipped — UI left in stale visual state on every page reload.

**Fix:** Fire `change` events unconditionally during restore, or do a post-restore sweep after `_restoreInProgress` is cleared.

---

### H-12 — `calcSurfInt` Dive 2 BT is hardcoded to Dive 1 BT — safety-relevant surface-interval underestimate
**File:** `index.html` ~line 11746  
**Issue:** `#125` (carried from `#124` M-6 unfixed)

`btAtDepth2 = Math.max(0, bt1 - descTime2)` always uses Dive 1 BT. A deeper Dive 2 gets the same BT as Dive 1, underestimating tissue loading and producing a recommended surface interval that is too short.

**Fix:** Add a Dive 2 BT slider to the surface interval UI. Pass it as a separate parameter to `simulateDive2`.

---

### H-13 — `ppO2Check` delegate skips `mergeCCRSettings` normalisation — only CCR delegate that does so
**File:** `index.html` lines 7520–7522  
**Issue:** `#125`

Every other CCR-consuming delegate calls `mergeCCRSettings(ccr)` before passing the CCR object into the bundle. `ppO2Check` passes `opts.ccr` raw, risking `null`/`undefined` fields and NaN ppO2 values.

**Fix:** Apply `mergeCCRSettings(opts.ccr)` inside the `ppO2Check` delegate before calling `ZhlEngineBundle.ppO2Check(…)`.

---

## 🟡 MEDIUM (14)

### M-01 — `margin` computed from display-capped `effNDLCap` (max 90) — false red alarm when true NDL > 90
**File:** `index.html` lines ~10333–10335  
**Issue:** `#127`

`margin = effNDLCap - bt` with `effNDLCap = Math.min(effNDL, 90)`. A 95-min true NDL with 92-min BT shows `margin = -2` (red warning) when the real margin is +3.

**Fix:** Compute `margin = effNDL - bt` (uncapped). Apply `Math.min(90)` cap to the display label only.

---

### M-02 — All surface-interval calculator sliders absent from `DECO_FIELDS` — values not persisted
**Files:** `index.html` DECO_FIELDS ~line 16204; DOM ~lines 3365, 3375, 3385, 3395  
**Issue:** `#127`

`siD1Depth`, `siD1BT`, `siD2Depth`, `siD2BT` are missing from `DECO_FIELDS`. None trigger `appSettings.save()`. All four sliders reset to HTML defaults on every reload, silently discarding user values.

**Fix:** Add all four sliders to `DECO_FIELDS`. Add `appSettings.save()` to each `oninput` handler (or call from within `calcSurfInt`).

---

### M-03 — `saturateLinearCCR` descending sub-segment uses shallow-endpoint setpoint — tissue loading understated on CCR descent
**Files:** `zhl-ccr-core.js` ~line 323 · `zhl-engine-bundle.js` (mirror — identical)  
**Issue:** `#127`

`endpointDepth = ascending ? seg.toDepth : seg.fromDepth`. For descending segments, the shallower start is used, missing the higher setpoint at the destination depth. Non-conservative when a setpoint change crosses mid-descent.

**Fix:** For descending segments use `seg.toDepth` (deeper end). Fix canonical source, regenerate bundle.

---

### M-04 — `validateHypoxicDecoGas` blocks legitimate CCR hypoxic diluents — spurious validation error
**File:** `zhl-gas-core.js` lines ~159–170  
**Issue:** `#127`

The function flags any O₂ < 18% deco-gas entry regardless of helium content or circuit type. A valid CCR diluent 12/60 triggers `HYPOXIC_DECO_GAS`, blocking plan calculation.

**Fix:** Only flag gases where `he === 0` (pure nitrox with hypoxic O₂). When `he > 0`, suppress the block (or expose CCR/trimix context to the caller).

---

### M-05 — `runContingencyScenario` `decoTime` reads wrong table column — always returns 0
**File:** `index.html` ~line 13837  
**Issue:** `#127`

`tr.querySelectorAll('td')[2]` selects the stop-duration column (plain integer minutes). `parseRunMinutes` expects `MM:SS` format and silently returns 0. `c.decoTime` shows `0'00"` in scenario cards and PDF export even when deco stops are present.

**Fix:** Use the correct column index and `parseInt` rather than `parseRunMinutes` for the stop-duration column.

---

### M-06 — `vpmStopCapHit` per-segment warning is unreachable — `vpmStopCapError` discards the plan
**Files:** `vpm-engine-core.js` ~line 1182 · `index.html` lines ~7824–7854  
**Issue:** `#127`

When the 999-min stop cap fires, `vpmStopCapError` returns `{ plan: [] }`. The rendering loop that reads `seg.vpmStopCapHit` is never reached. The UI warning logic added in #125 L-1 is dead code.

**Fix:** Include the partial plan in the `vpmStopCapError` return object, or move the cap warning to the early-exit branch where the error is displayed.

---

### M-07 — `check_engine_parity.py` api_exports list missing 4 of 6 new dedup functions
**File:** `tools/check_engine_parity.py` lines ~98–111  
**Issue:** `#127`

`ndlClearAtDepth`, `n2FracFromCustomO2`, `n2FracFromPercentages`, `validateHypoxicDecoGas` are absent from the `api_exports` verification list. Their accidental removal from the bundle postamble would not be caught by CI.

**Fix:** Add the four missing names to the `api_exports` list.

---

### M-08 — Ceiling loop guard (360 min) silently caps extreme trimix first-stop deco
**Files:** `zhl-schedule-core.js` lines 305–330  
**Issue:** `#128`

For penetration trimix dives >150 m the first-stop ceiling can legitimately require >6 hours. When `stopT` hits 360 the loop exits with the ceiling still unsatisfied, silently underestimating the deco obligation. Same pattern exists in the last-stop loop with a 180-min cap.

**Fix:** Increase guard to ≥1440 min. When the guard fires, set `hitSafetyGuard: true` on the step and emit a hard UI warning.

---

### M-09 — `saturateLinearCCR` has no own constant-depth guard — INF segment time if called directly
**Files:** `zhl-ccr-core.js` lines 155–170  
**Issue:** `#128`

`segTime = abs(range) / abs(toDepth - fromDepth) * totalTime`. If `fromDepth === toDepth`, the denominator falls to `1e-9`, producing near-infinite segment times and `Infinity` tissue pressures. The guard exists only in the caller, not the function itself.

**Fix:** Add at the top of `saturateLinearCCR`: `if (Math.abs(toDepth - fromDepth) < 1e-9) return saturateCCR(…);`

---

### M-10 — `params.decoAscentRate` / `surfaceAscentRate` have no fallback defaults — `undefined` propagates as `NaN`
**Files:** `zhl-schedule-core.js` lines 19–22  
**Issue:** `#128`

No nullish fallback on either field. If omitted by a direct caller, every division `(cur - stopDepth) / decoRate` produces `NaN`, propagating through tissue loading and silently producing a zero-stop schedule for any dive that requires decompression.

**Fix:** Add `?? 9` (or `?? 3`) defaults, or add a validation block that throws a descriptive error when mandatory fields are absent.

---

### M-11 — `check_engine_parity.py` has three separate correctness defects — effectively does not catch drift
**File:** `tools/check_engine_parity.py` lines 42–89  
**Issue:** `#125`

Defect 1: skips `applyEnvironment`, `defaultEnvironment`, `setHeHalfTimeMode` unconditionally.  
Defect 2: CCR body comparison is dead code — `norm_ccr` is longer than the bundle slice, vacuously always triggers the `len` guard.  
Defect 3: API export check matches by simple substring, missing trailing-item and false-positive cases.

**Fix:** Remove skip list (D1). Rewrite CCR comparison function-by-function (D2). Use word-boundary regex for export check (D3).

---

### M-12 — `OTU_EXPONENT` hardcoded in `index.html` — not sourced from bundle
**Files:** `index.html` line 3999 · `zhl-physics-core.js` line 19 · `zhl-engine-bundle.js` line 24  
**Issue:** `#125`

Three OTU call sites in `index.html` use a local `const OTU_EXPONENT = 0.8333`. If corrected in `zhl-physics-core.js`, the bundle updates but the three inline sites use the stale value, producing divergent OTU totals.

**Fix:** Replace with `const OTU_EXPONENT = ZhlEngineBundle.OTU_EXPONENT`, consistent with `PSCR_MIN_PPO2`.

---

### M-13 — `enforceMinDecoProfile` and `getActiveGas` delegates missing `_syncZhlBundleEnv()` — wrong environment at altitude
**File:** `index.html` lines 7263–7265, 7515, 7520  
**Issue:** `#125`

Every other physics-delegating wrapper calls `_syncZhlBundleEnv()` first. These two delegates do not. At altitude, deco gas switch depths and minimum stop profiles are computed against stale environment values.

**Fix:** Prepend `_syncZhlBundleEnv();` to both delegate bodies.

---

### M-14 — Build script concatenation order places CCR before gas-core — violates stated dependency order
**File:** `tools/build_zhl_bundle.py` lines 21–24  
**Issue:** `#125`

Order is `physics → ccr → gas → schedule`. Dependency order is `physics → gas → ccr → schedule`. Works today because `function` declarations are hoisted, but breaks silently if any function is converted to a `const` arrow or if a CCR top-level initialiser is introduced.

**Fix:** Change order to `physics_core → gas_core → ccr_core → schedule_core → bundle_wrapper`.

---

## 🔵 LOW (7)

### L-01 — `adjustedCritRadiiHe` length not checked in VPM bubble carry guard
**Files:** `vpm-engine-core.js` ~line 261 · `vpm-engine-bundle.js` (mirror)  
**Issue:** `#127`

Guard checks `adjustedCritRadiiN2.length` but not `adjustedCritRadiiHe.length`. A truncated prior state passes and silently extends a sparse array, writing `undefined` into compartments — `NaN` propagates into gradient and ceiling calculations for repetitive dives.

**Fix:** Add `&& _prevBubbleState.adjustedCritRadiiHe?.length === NC` to guard. Fix canonical source, regenerate bundle.

---

### L-02 — `surfP || altSurfaceP` treats valid `surfP = 0` as falsy
**Files:** `zhl-ccr-core.js` lines ~54, ~67 · `zhl-engine-bundle.js` (mirror)  
**Issue:** `#127`

`surfP = 0` is a valid mock value (unit tests, pathological altitude edge case). The `||` operator silently falls through to `altSurfaceP`.

**Fix:** Replace `surfP || altSurfaceP` with `surfP != null ? surfP : altSurfaceP`. Fix canonical source, regenerate bundle.

---

### L-03 — `calcAllowableGradients` ignores its `_conservatism` parameter — inter-level off-loop relaxation is a no-op
**Files:** `vpm-engine-core.js` ~line 1432 · `vpm-engine-bundle.js` (mirror)  
**Issue:** `#127`

The `_conservatism` parameter (leading underscore) is never read inside the function. The inter-level conservatism relaxation for off-loop CCR segments has no effect — overly conservative but not a safety risk.

**Fix:** Implement the conservatism relaxation, or remove the dead parameter and the `interLevelConservatism` computation if the feature is deferred.

---

### L-04 — `check_engine_parity.py` brace counter is blind to string/regex literals — truncates template-literal functions
**File:** `tools/check_engine_parity.py` lines 30–47  
**Issue:** `#127`

Raw `{`/`}` counting includes template literal interpolations. A function using `` `{${val}}` `` is extracted too early, producing a truncated body for comparison.

**Fix:** Add a string/template-literal skip pass, or use a JS-aware parser (`esprima`/`acorn` via subprocess).

---

### L-05 — SW optional precache failures are silent — no client notification of degraded offline state
**Files:** `sw.js` lines 96–112  
**Issue:** `#128`

Failed optional precache assets (woff2, ttf, png) produce only `console.warn`. No `postMessage` to client — user is offline with missing fonts and no UI indication.

**Fix:** After install, `postMessage` to all clients listing which optional assets failed so the app can surface a degraded-offline notice.

---

### L-06 — `audit` CI job has no `needs: [bundle-sync]` — runs in parallel against potentially stale bundle
**File:** `.github/workflows/ci.yml` line 16  
**Issue:** `#125`

`audit` runs against the committed (potentially stale) bundle. If a developer edits a core source file without regenerating the bundle, `audit` validates the stale bundle and may pass; a PR can land with a stale bundle if only `audit` is required for merge.

**Fix:** Add `needs: [bundle-sync]` to the `audit` job.

---

### L-07 — `docs/AUDIT_MIRROR_RULE.md` describes `index.html` CCR delegates as "(until removed)" — inaccurate post-dedup
**File:** `docs/AUDIT_MIRROR_RULE.md` line 9  
**Issue:** `#125`

After the 9b5dcf8 refactor all CCR logic in `index.html` is thin delegate wrappers, not inline copies. The parenthetical "(until removed)" will mislead future auditors into searching for CCR logic that no longer exists there.

**Fix:** Update mirror table row to "(thin delegates — single source is bundle)".

---

## Confirmed Clean

The following items were audited and found correct at HEAD:

- `schreinerLinear` R-convention: consistent across all call sites ✓
- `buhNDL` delegate argument count and order: correct 7-argument call ✓
- `n2FracFromCustomO2` / `n2FracFromPercentages` / `validateHypoxicDecoGas` export names: match exactly ✓
- `applyNuclearRegeneration` single-call at post-bottom (as fixed by #124, minus H-10 double-call above) ✓
- `vpm-engine-core.js` vs `vpm-engine-bundle.js` functional parity: no divergence found (H-09 is process gap, not current divergence) ✓
- `'use strict'` placement in VPM bundle: correctly inside IIFE body ✓
- `--orange` CSS variable: defined in both light and dark `:root` blocks ✓
- `FN2_EAN32` / `FN2_EAN36` declaration order: precedes usage, no hoisting issue ✓
- `ceiling()` gfHigh guard (#124 H-1): present ✓
- `gfAt()` zero-denominator guard (#124 H-2): present ✓
- `getEffectivePpo2` altSurfaceP guard (#124 H-4): present in both CCR-core and bundle ✓
- `vpmStopCapHit` rendering (#124 L-1): present in `index.html` lines 7780–7880 ✓

---

## Previously Fixed (Closed Issues — Confirmed)

| Issue | Description | Status |
|-------|-------------|--------|
| #107  | Latest fix | ✅ CLOSED 2026-06-27 |
| #114  | 15 findings from #113 fix | ✅ CLEAN |
| #115  | VPM nuclear regen bottom-phase runtime (#124 M-2) | ✅ CLEAN |

---

## Release Verdict

**NOT RELEASE-CLEAN.**

The four CRITICAL findings (C-01 through C-04) are in the active CCR tissue-loading path and produce incorrect inert-gas partial pressures for setpoint-controlled dives at depth. All four must be resolved and regression-tested before any release containing CCR plan calculations.

HIGH findings H-01, H-02, H-03 affect NDL, ppO2 toxicity display, and trimix tissue loading — all safety-relevant for OC trimix dives.  
HIGH finding H-04 (`try/finally`) causes permanent UI corruption on contingency scenario errors.  
HIGH findings H-09/H-10 (VPM dedup / double nuclear regen) produce non-conservative multi-level VPM deco schedules.

**Recommended fix priority:**
1. C-03, C-04 (CCR setpoint + inert PP — release-blocking safety)
2. C-01, C-02 (variable shadow + deco rate default — latent safety)
3. H-10 (VPM nuclear regen double-call — non-conservative)
4. H-04 (`try/finally` — UI corruption)
5. H-11 (`_restoreFields` change events — UX broken every reload)
6. H-01, H-02, H-03 (trimix fHe, ppO2 clamp, NDL shallowGradient)
7. H-09 (VPM build automation — process gap)
8. Remaining HIGH, MEDIUM, LOW in severity order

---

*Report compiled 2026-06-29 from issues #125, #127, #128, #130 by automated multi-pass static audit. No code was written or modified.*
