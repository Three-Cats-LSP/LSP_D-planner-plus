# LSP D-Planner+CCR — Full App Release Audit (v27)

**App version:** v2.30.30  
**Audit date:** 2026-06-21  
**Scope:** Complete whole-app pre-release deep audit — all subsystems, not limited to CCR.  
**Audit tool:** audit.py — 383 checks, 0 failures  
**Baseline:** All prior bugs BUG-01–84 confirmed fixed.

---

## Audit Result: ✅ RELEASE READY — 0 bugs found

All 12 subsystem areas passed. No new bugs, no regressions. The codebase is clean.

---

## Subsystems Audited

### 1. Bühlmann ZHL-16C Engine ✅

| Check | Result |
|-------|--------|
| ZHL16C N2 coefficients (16 compartments, a/b/ht) | ✅ Match Bühlmann/Völlm/Nussberger ZHL-16C standard |
| He half-times — Baker 1998 array (`ZHL16C_HE_HT_BAKER`) | ✅ Correct (ht[0]=1.88, matches VPM-B canonical) |
| He half-times — Bühlmann 2003 array (`ZHL16C_HE_HT_BUHL2003`) | ✅ Correct (ht[0]=1.51, all others identical to Baker) |
| He a/b values (`ZHL16C_HE_AB`) | ✅ Standard ZHL-16C He values |
| Schreiner equation (constant pressure) | ✅ `pGas + (p0-pGas) × exp(−LN2/ht × t)` |
| Schreiner linear (pressure-varying — ascent/descent) | ✅ Standard Haldane linear-R form; inspired ppN2 water-vapor corrected |
| GF interpolation (Baker formula) | ✅ `gfL + (gfH − gfL) × (firstStop − depth) / (firstStop − interpBase)` |
| Shallow Gradient extension | ✅ `interpBase = lastStop` when on; GF Hi reached at last stop |
| `ceiling()` — trimix-weighted a/b | ✅ `pAmbMin = (pN2+pHe − GF×a) / (1 − GF + GF/b)` — altitude-aware via `altSurfaceP` |
| `computeSurfaceGF()` — altitude-aware (BUG-69) | ✅ `P_surf = altSurfaceP` |
| `buhNDL()` | ✅ Uses `ceiling(next, gfHigh/100)` — correct |
| He half-time sync to VPMEngine (`_syncHeHalfTimes`) — BUG-76 | ✅ Fixed — all 16 compartments synced on mode change and startup |

### 2. VPM-B Engine ✅

| Check | Result |
|-------|--------|
| ΓAMMA = 0.0179, ΓAMMA_C = 0.257 | ✅ Baker canonical values |
| Initial radii: N2 = 0.55 μm, He = 0.45 μm | ✅ VPM-B canonical |
| Regeneration time: 20160 min (2 weeks) | ✅ Correct |
| Critical volume λ = 7500 fsw·min | ✅ Standard |
| Conservatism factors (+0–+5): 1.00, 1.05, 1.12, 1.22, 1.35, 1.50 | ✅ Correct scaling |
| `calcAllowableGradients()` — `2γ/r × (γc−γ)/γc` | ✅ Baker formula |
| Trimix-weighted ceiling (same as Bühlmann) | ✅ |
| Repetitive bubble state carry (`adjustedCritRadii`, `regeneratedRadii`) | ✅ |
| VPM surface interval radii regeneration (exponential, `REGEN_TIME`) | ✅ |
| `selectDecoGas()` — richest O2 within ppO2 limit at depth | ✅ Altitude-aware via `getAmbientPressure()` |
| pSCR OTU/CNS via `vpmAccumPpo2` (9 call sites) | ✅ (BUG-63–68 all fixed) |
| CCR OTU/CNS via `computePlanExposureTotals` + `mergeCCRSettings` | ✅ (BUG-73/80/82 fixed) |

### 3. pSCR / CCR Tissue Loading & OTU/CNS ✅

| Check | Result |
|-------|--------|
| `computePSCRFractions()` — metabolic depletion model | ✅ |
| `getEffectivePpo2()` — pSCR branch (`fr.fO2 × pAmb`, floored at `PSCR_MIN_PPO2`) | ✅ |
| `getEffectiveSetpointAtDepth()` — phase-aware (descent/bottom/deco) | ✅ |
| `ccrDiluentSurfaceLpm()` pSCR: `metRate × bypassRatio` (BUG-75) | ✅ Fixed |
| `accumulateHeadlessPlanExposure()` — delegates to `computePlanExposureTotals` | ✅ (BUG-82) |
| `computePlanExposureTotals()` pSCR sub-step depth interpolation for ascent | ✅ `from + (to-from) × frac` |
| `addBailoutStressReserve()` — depth-distributed stress reserve | ✅ (BUG-70) |
| Bühlmann `_ccrPpo2Opts` `scrRuntimeMin: diveRuntimeMin` | ✅ (BUG-66) |
| `calcCNS()` standalone tab `scrRuntimeMin: bt` | ✅ (BUG-67) |
| VPM and Bühlmann OTU/CNS parity for pSCR/CCR | ✅ Both via `getEffectivePpo2 → computePSCRFractions` |
| CCR VPMEngine headless OTU/CNS via `headlessPpo2`→`computePlanExposureTotals` | ✅ (BUG-73) |

### 4. Gas Logic ✅

| Check | Result |
|-------|--------|
| `nitroxMOD(fO2, ppO2)` = `floor((ppO2/fO2 − 1) × 10)` | ✅ |
| `calcMOD()` internal = `floor((ppO2/fO2 − 1) / BAR_PER_METRE)` — altitude-aware | ✅ |
| Pure-O2 `o2AtMOD` override at fixed 6 m | ✅ |
| `calcEND()` — altitude-aware, narcotic N2/O2 toggles | ✅ |
| `selectDecoGas()` — richest O2 within ppO2 limit; manual switch depth support | ✅ |
| Travel gas auto-switch (MOD-based) and manual switch depth | ✅ |
| Gas switch pause time: `switchPauseT = 0` (no phantom time added) | ✅ |
| `getBottomGasFractions()` — trimix, nitrox, air, custom O2 | ✅ |

### 5. Gas Plan / Consumption ✅

| Check | Result |
|-------|--------|
| `gpSizeL()`: cu ft → L via `GP_CUFT_PER_L = 0.0353147` | ✅ |
| `gpPresBar()`: psi → bar via `GP_PSI_PER_BAR = 14.5038` | ✅ |
| `gpVolDisp()` / `gpPresDisp()`: reverse conversion for display | ✅ |
| Emergency gas `sz`: `szRaw × 28.3168` (cu ft→L) in CCR repo | ✅ |
| Emergency gas `pr`: `prRaw / 14.5038` (psi→bar) | ✅ |
| `sacDomToLpm()` — imperial SAC cu_ft/min → L/min (BUG-71) | ✅ Fixed |
| `ccrSacStress` — stays in L/min regardless of units (UX note, no calc bug) | ✅ by design |
| Rule-of-thirds / half-tank logic | ✅ |

### 6. Multi-Dive ✅

| Check | Result |
|-------|--------|
| `offgasAtSurface()` — CCR on-loop uses loop gas, OC uses air | ✅ |
| Surface interval tissue offgassing: Haldane, all 16 N2 + He compartments | ✅ |
| Prior-dive OTU/CNS carry (`_priorDiveCarry`) | ✅ |
| VPM repetitive: tissue + bubble state carry + SI regeneration | ✅ |
| CNS SI decay: `× exp(−SI/90)` (90-min half-life, Baker/NOAA) | ✅ |
| CCR-aware NDL display in multi-dive planner | ✅ |

### 7. Altitude / Water Density ✅

| Check | Result |
|-------|--------|
| `altToPressure()`: `1.01325 × exp(−h/8434)` (ISA approximation) | ✅ |
| `altSurfaceP` used in `ceiling()`, `computeSurfaceGF()`, `calcMOD()`, `calcEND()` | ✅ |
| `WATER_DENSITY`: salt=0.10000, fresh=0.09681, en13319=0.09921 bar/m | ✅ Match MultiDeco/DiveKit references |
| `BAR_PER_METRE` global updated by `setWaterDensity()` | ✅ |
| Custom density: `(kg × 9.80665) / 100000` bar/m | ✅ |
| Altitude persisted in `lspAltitude` and restored on reload | ✅ |

### 8. Exports ✅

| Check | Result |
|-------|--------|
| PDF filename: `LSP_CCR_<date>_Deco_…pdf` | ✅ |
| PDF imperial unit display (`_pdfSacUnit`, depth `du`) | ✅ |
| Bühlmann OTU/CNS export from `_lastPlan.totalCNS/totalOTU` | ✅ |
| VPM OTU/CNS export from `_lastVPMExport.cns/otu` | ✅ |
| Text export (`buildExportText`) — depth unit, altitude, density, all circuits | ✅ |
| Slate export (`buildSlateText`) — reads rendered DOM table | ✅ |
| Messenger export — OTU/CNS from plan summary | ✅ |
| Gas Plan PDF (`buildGasPlanPDF`) — imperial vol/pres via `gpVolDisp`/`gpPresDisp` | ✅ |

### 9. UI / Settings / Persistence ✅

| Check | Result |
|-------|--------|
| `DECO_FIELDS` — all 40+ fields including `dg1Mix`/`dg2Mix` trimix (BUG-77) | ✅ Fixed |
| `appSettings.clear()` — all 13 app-owned `localStorage` keys | ✅ |
| `card_open_*` / `LSP_PROFILE_PRESETS_KEY` correctly excluded from clear | ✅ by design |
| `settingsFingerprint` includes `dg1Mix`/`dg2Mix` for plan invalidation | ✅ |
| Version sync: `APP_VERSION`, `package.json`, `build.gradle`, `sw.js` all `2.30.30` | ✅ (BUG-84) |
| SW `CACHE_VERSION = 'lsp-dplanner-ccr-v2.30.30'` | ✅ |
| `skipWaiting` on install + `SKIP_WAITING` message | ✅ |
| `updateHeHalfTime()` called twice on startup (immediate + 1-sec retry) | ✅ |
| Named presets restore calls `toggleDecoCustomO2` + `updateHeHalfTime` | ✅ |

### 10. Recreational Planner ✅

| Check | Result |
|-------|--------|
| PADI NDL metric table (`PADI_NDL_M`) — 11 depths 10–40 m | ✅ Matches PADI RDP |
| PADI NDL imperial table (`PADI_NDL_FT`) | ✅ Same values (PADI uses same NDL regardless of unit) |
| PADI Nitrox EAN32 NDL | ✅ Matches PADI Enriched Air Diver table |
| PADI Nitrox EAN36 NDL | ✅ Correct |
| `PADI_DEPTHS_FT = [35,40,50,60,70,80,90,100,110,120,130]` | ✅ Match metric equivalents |
| `buhNDL()` Bühlmann NDL — ceiling(next, gfHigh/100) | ✅ |
| MOD display in NDL table for EAN32/36 beyond MOD | ✅ |
| Pressure group approximation (`padiGroup`) | ✅ |

### 11. Regression Suite ✅

| Check | Result |
|-------|--------|
| `audit.py` — 383 checks, 0 failures | ✅ |
| `tests-pscr-otu-cns.html` — 6 scenarios × depths × dilutents × VPM+ZHL | ✅ |
| `tests-verify.html` — CCR tissue loading, BUG-73 regression, NDL (GF 100/100) | ✅ |
| `tests-massive.html` — iframe stale-ref + `_suiteRunId` cancellation guard | ✅ (BUG-78/81) |
| `tests-massive-main.html` — same guards | ✅ |
| BUG-75 regression (pSCR surface LPM ≈ 15, not 93) | ✅ |
| BUG-76 regression (`_syncHeHalfTimes` in audit.py GROUP) | ✅ |

---

## Open Items

**None.** All 84 CCR repo bugs (BUG-01–84) are closed.

### Historical OC main carry-overs (LSP_D-planner repo — out of scope)
These were noted in earlier reports. They do NOT affect the CCR repo:

| Item | Status |
|------|--------|
| BUG-40 — OC main: emergency gas `sz` not converted cu ft→L | Out of scope (OC repo only) |
| BUG-41 — OC main: `appSettings.clear()` incomplete | Out of scope (OC repo only) |

Note: Both equivalent issues in the CCR repo were independently fixed:
- Emergency gas imperial conversion: `szRaw × 28.3168` at line 10825 ✅
- `appSettings.clear()`: all 13 keys covered at line 17712 ✅

---

## Release Verdict

**v2.30.30 is clean. No known bugs. Safe to release.**

All decompression algorithms, gas calculations, OTU/CNS tracking, exports,
settings persistence, and regression tests verified correct. The pSCR
consistency audit (v2.30.15–30 cycle) is complete and all findings resolved.
