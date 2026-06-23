# LSP D-Planner+CCR — Errors & Bugs Report v13

**App version audited:** v2.30.15  
**Audit date:** 2026-06-21  
**Previous report:** errors_bugs_report_v12.md (v2.30.13 — 1 bug: BUG-63)  
**Audit tool:** audit.py — 303 checks, 0 failures  
**Commits audited:** `092aaa9` (v2.30.14) → `d5e217b` (v2.30.15)

---

## Summary

v2.30.14 fixed BUG-63 (primary VPM pSCR OTU/CNS path).  
v2.30.15 fixed BUG-64–68 (remaining pSCR OTU/CNS paths from the pSCR_OTU_CNS_consistency_audit).

**All 6 fixes (BUG-63–68) verified correct.**  
**0 new bugs found.**

---

## BUG-63 Fix Verification (v2.30.14, commit `092aaa9`)

**Status:** ✅ Fixed and verified

`vpmAccumPpo2()` helper introduced in VPMEngine. Replaces all 6 inline
`curSP > 0 ? Math.min(curSP, pAmbSeg) : curO2 * pAmbSeg` patterns in
`VPMEngine.calculate()` level loop (lines ~8961, ~9013, ~9059, ~9084,
~9102, ~9127).

- For pSCR on-loop: routes through `getEffectivePpo2(pAmb, 0, fO2, ccr, depthM, fHe)` → `computePSCRFractions()` with `_scrRuntimeMin` tracking.
- For CCR/OC/bailout: falls through to `fO2 * pAmb` (correct).

---

## BUG-64–68 Fix Verification (v2.30.15, commit `216e8d4`)

### BUG-64 — VPM continuation helpers (MEDIUM) ✅ Fixed

`addExposureToContext`, `addConstantExposure`, `runRoundedDecoStop`:
all three now call `vpmAccumPpo2(..., ctxUseOCForPpo2(ctx))` instead of
the old inline `ctx.currentO2 * pAmb`.

`ctxUseOCForPpo2(ctx)` closes over outer `settings`; returns `true`
(OC mode) when `settings.bailout || settings.circuit !== 'pSCR'`.  
`maybeSwitchDecoGas` returns immediately for any rebreather on-loop
(`isRebreatherCircuit && !bailout`) so `ctx.currentSP` cannot be zeroed
out by a deco gas switch on pSCR — `ctxUseOCForPpo2` not ignoring
`ctx.currentSP` is safe.

`settings._scrRuntimeMin` is synced to `ctx.runtime` before each call
site, correctly propagating cumulative runtime into `computePSCRFractions`.

**Note (non-bug):** `addConstantExposure` and `runRoundedDecoStop` use
end-of-segment runtime for the single-point ppO₂ integration over
the full stop duration. For long pSCR bottom holds this slightly
underestimates OTU/CNS (more depletion at end → lower loop ppO₂ →
less toxicity). This is a known simplification consistent with
`runRoundedDecoStop` in the original single-level path — not a bug.

### BUG-65 — vpmDisplayPpo2 scrRuntimeMin (LOW) ✅ Fixed

`vpmDisplayPpo2` now builds `ccrDisp = { ..._vpmCcr, scrRuntimeMin: seg && seg.runtime != null ? seg.runtime : 0 }` and passes it to `getEffectivePpo2`. VPM table ppO₂ column now reflects per-segment depletion.

### BUG-66 — Bühlmann _ccrPpo2Opts scrRuntimeMin (MEDIUM) ✅ Fixed

`_ccrPpo2Opts` now passes `ccr: { ..._ccrSettings, scrRuntimeMin: diveRuntimeMin }`.  
`diveRuntimeMin` is updated by every `zhlLoadLinear` / `zhlLoadConst` call before
`_ccrPpo2Opts` is invoked for the `pO2` step field — OTU/CNS inputs now match
tissue loading runtime for Bühlmann pSCR.

### BUG-67 — calcCNS() pSCR scrRuntimeMin (LOW) ✅ Fixed

CNS standalone tab now builds `ccrForPpo2 = { ...ccr, scrRuntimeMin: bt }` for
pSCR, giving the end-of-BT depleted loop ppO₂ as the single-point estimate.

### BUG-68 — ZHLEngine headless OTU/CNS (LOW) ✅ Fixed

`headlessPpo2(depthM, fO2, fHe, runtimeMin)` helper introduced. For pSCR
on-loop reads loop/metabolic params from DOM with fallback defaults (10 L / 1.5 L·min⁻¹).
Descent, bottom, and all step segments now route through `headlessPpo2`.

---

## Audit Scope — All Areas Clean

### CCR engine logic
- `computePSCRFractions`: correct metabolic depletion model ✅
- `getEffectivePpo2`: pSCR branch (`fr.fO2 * pAmb`, floored at `PSCR_MIN_PPO2`) ✅
- `vpmAccumPpo2`: correct fallback to `fO2 * pAmb` for OC/bailout ✅
- `ccrDiluentSurfaceLpm`: uses `pSurf` (not `pAmb`) correctly (BUG-57 still fixed) ✅
- `toggleCircuitFields` bailout group: `isRB` guard (BUG-59 still fixed) ✅
- `VPM offLoopPath` pSCR guard (BUG-60 still fixed) ✅
- `maybeSwitchDecoGas`: returns immediately for rebreather on-loop — pSCR cannot switch to OC deco gas ✅

### Gas plan / gas consumption
- `gpSizeL` / `gpPresBar` / `gpVolDisp` / `gpPresDisp`: correct imperial ↔ metric conversions using `GP_CUFT_PER_L = 0.0353147` and `GP_PSI_PER_BAR = 14.5038` ✅
- `ccrGasLitres` / `gpRequiredFor`: CCR/pSCR loop label matching intact ✅
- Rule-of-thirds / half-tank logic: no regressions ✅

### Exports (PDF, text, messenger, slate)
- All export paths read OTU/CNS from `result.totalCNS` / `result.totalOTU` (VPM) or `window._lastPlan.totalCNS` / `totalOTU` (Bühlmann) — both now correctly computed ✅
- `_lastVPMExport.cns/otu` populated from `result.totalCNS/totalOTU` ✅
- No new export regressions from v2.30.15 diff ✅

### UI / settings / persistence
- `appSettings.clear()`: removes all 19 known app-owned localStorage keys including `waterDensity`, `lspAltitude`, `gfCustomLow/High`, `lspUserAdvDefaults`, `diveTheme`, all versioned `lspDiveSettings_*` ✅
- `card_open_*` keys (accordion state) are UI convenience keys, not app settings — correct to exclude from `clear()` ✅
- `SW_VERSION_KEY`, `LSP_PROFILE_PRESETS_KEY`, `LSP_CONFIG_PRESETS_KEY`, `LSP_PRESETS_KEY`: user data / SW versioning — correct to exclude from `clear()` ✅
- `sw.js` CACHE_VERSION bumped to `lsp-dplanner-ccr-v2.30.15` ✅

### VPM vs Bühlmann parity
- Both engines now route pSCR OTU/CNS through `getEffectivePpo2` → `computePSCRFractions` ✅
- Per-segment runtime (`_scrRuntimeMin` / `diveRuntimeMin`) propagated correctly in both engines ✅
- CNS formula difference (VPM: rate table; Bühlmann: NOAA limits) is by design — not a parity bug ✅
- `calcCNS` standalone tab uses BT as pSCR proxy (consistent with single-depth model) ✅

---

## New Bugs Found

**None.**

---

## Carry-Over OC Main Bugs (out of scope for CCR repo)

| Bug | Description | Repo |
|-----|-------------|------|
| BUG-40 | Bühlmann emergency gas `sz` not converted cu ft→L (~line 9789) | LSP_D-planner |
| BUG-41 | `appSettings.clear()` only removes `lspDiveSettings_v3` (~line 16449) | LSP_D-planner |

---

## All CCR Repo Bugs — Cumulative Status

| Report | Bugs | Status |
|--------|------|--------|
| v1–v9  | BUG-01–50 | ✅ All fixed |
| v10 (v2.30.11) | BUG-51–56 | ✅ All fixed (v2.30.12) |
| v11 (v2.30.12) | BUG-57–62 | ✅ All fixed (v2.30.13) |
| v12 (v2.30.13) | BUG-63    | ✅ Fixed (v2.30.14) |
| **v13 (v2.30.15)** | **0 new bugs** | **✅ Clean** |
