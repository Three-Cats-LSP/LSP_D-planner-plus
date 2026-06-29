## Cursor implementation checklist

**Cursor: implement all findings in this issue. Do not weaken validation or remove existing audit coverage.**

### Phase 1 — HIGH (8)
- [x] H-1: `validateHypoxicDecoGas` on bottom gas in `buildZhlScheduleParamsFromDom` + `validateDomDecoGases`
- [x] H-2: Sanitize `err.message` in `runDecoSchedule` catch via `escapeHtmlText`
- [x] H-3: `conservatismSelect` `onchange` → `onConservatismChange()` replan
- [x] H-4: `setWaterDensity()` calls `replanAfterEnvChange()`
- [x] H-5/H-6: Bühlmann `modPpo2` hoisted; ppO₂ alert uses user limit
- [x] H-7: `getZhlRepStateForSchedule` includes `totalCNS`/`totalOTU`; exposure uses `repState`
- [x] H-8: VPM `levels` use `btAtDepthMin` not raw BT

### Phase 2 — MEDIUM (22)
- [x] M-1: Skip `validateCcrGasConfiguration` during contingency
- [x] M-2: Optional chaining on rate DOM reads in `buildZhlScheduleParamsFromDom`
- [x] M-3: `vpmStopCapError` imperial/metric unit suffix
- [x] M-4: Inter-level VPM skip zero-time forced min stop
- [x] M-5: ppO₂ boundary uses `>=` limit
- [x] M-6: Null-safe `s.gas.toUpperCase()` in row render
- [x] M-7: `ean80` in `getDomDecoGasPct` (verified present)
- [x] M-8: Duplicate gas keys use clamped `getDecoCardFractions`
- [x] M-9: `setCustomGF` swaps inverted GF pair on commit
- [x] M-10: `ppo2Bottom`/`ppo2Deco` persist via `appSettings.save`
- [x] M-11: `ccrDecoSetpoint` `oninput` handler
- [x] M-12: `_restoreInProgress` cleared after sync; save after restore
- [x] M-13: `parseCcrSetpoint` avoids `||` falsy-0 trap
- [x] M-14: `resolveGasAtDepth` null-safe `fN2`
- [x] M-15: pSCR setpoint range validation
- [x] M-16: NDL MOD uses `ppo2Bottom`
- [x] M-17: `calcEND`/`calcEAD` null for zero/negative END
- [x] M-18: VPM rejects NaN deco gas fractions
- [x] M-19: VPM `gfHi` fallback when `mGF.high` unset
- [x] M-20: `mergeRepSettings` injects CNS/OTU when `_preTissues` preset
- [x] M-21: VPM `altitude` NaN guard
- [x] M-22: App init defers defaults when `appSettings._loadPending`

### Phase 3 — LOW (10)
- [x] L-1: pSCR included in VPM inter-level conservatism relaxation
- [x] L-2: `calcCrushRadius` guards `r0 <= 0`
- [x] L-3: Ascent row ppO₂ uses `toFixed(2)` / fallback
- [x] L-4: Warn on invalid trimix N₂ in `getN2Frac`
- [x] L-5: Corrupt settings load sets `_loaded = true`
- [x] L-6: ppO₂ ERR path unchanged (finite guard handles)
- [x] L-7: Remove stale `PSCR_MIN_PPO2` const; use `getPscrMinPpo2()`
- [x] L-8: `ppo2Bottom` optional chaining in schedule params
- [x] L-9: `n2FracFromPercentages` rejects `fN2 > 1`
- [x] L-10: `getGasLabel` stub in `zhl-schedule-core.js`

### Validation
```
python tools/extract_ui_cores.py
python audit.py
python tools/check_engine_parity.py
npm run build:bundles
python dev/engine_regression.py
python dev/run_all_regression.py --tier release
```
