# LSP D-Planner+CCR — Errors & Bugs Report v12

**App version**: v2.30.13 (commit `32d7bbd`)  
**Audit date**: 2026-06-21  
**Auditor**: Deep code audit (static analysis)  
**Previous report**: errors_bugs_report_v11.md (BUG-57–62, all fixed in v2.30.13)  
**Scope**: Full deep audit of `index.html` — CCR/pSCR engine, gas plan, exports, UI/settings, VPM parity

---

## Summary

1 new bug found (BUG-63).  
All v11 bugs (BUG-57–62) confirmed fixed and verified correct.  
No regressions introduced by the v2.30.13 fixes.

---

## BUG-63 — VPM pSCR: OTU/CNS accumulator uses diluent ppO₂ instead of loop ppO₂

**Severity**: MEDIUM  
**Area**: VPM engine — pSCR OTU/CNS tracking  
**File location**: VPMEngine `calculate()` — descent/bottom/ascent ppO₂ calculation (~lines 9091, 9116, 8950)

### Description

Throughout VPMEngine, OTU and CNS are accumulated using this pattern:

```js
const ppO2Seg = curSP > 0 ? Math.min(curSP, pAmbSeg) : curO2 * pAmbSeg;
totalOTU += calculateOTU(ppO2Seg, dtA);
totalCNS += calculateCNS(ppO2Seg, dtA);
```

For pSCR, `curSP = getEffectiveSetpoint(...) = 0` (correct — pSCR has no electronic setpoint).
The fallback is `curO2 * pAmbSeg` — which is the **diluent** O₂ fraction multiplied by ambient
pressure. This is the OC-equivalent ppO₂, not the actual pSCR loop ppO₂.

The actual pSCR ppO₂ is always lower than the diluent ppO₂ at depth (the loop is partially
depleted of O₂ by the metabolic process). Using diluent ppO₂ consistently **overstates**
OTU and CNS for pSCR dives in VPM.

Example at 40m with EAN32 diluent:
- Diluent ppO₂ (VPM uses): `0.32 × 5.01 bar = 1.60 bar`
- Actual pSCR loop ppO₂ (what diver breathes): ~0.16–0.21 bar (heavily depleted by metabolic O₂ consumption)

The OTU/CNS overstatement is significant — the diver is accumulating substantially less
oxygen toxicity than VPM reports. This is conservative (safe), but incorrect and misleading.

**Contrast with Bühlmann**: The Bühlmann engine uses `rowDisplayPpo2 → ppO2Check →
getEffectivePpo2 → computePSCRFractions` to display pSCR ppO₂ correctly, and the
same `rowDisplayPpo2` is used for OTU/CNS accumulation — so Bühlmann is correct.

### Affected paths

All three OTU/CNS accumulation sites in VPMEngine where `curSP <= 0` and circuit is pSCR:

1. **Descent phase** (~line 9091): `ppO2D = sp > 0 ? min(sp, pAmbEnd) : o2Frac * pAmbEnd`
2. **Bottom phase** (~line 9116): `ppO2B = sp > 0 ? min(sp, pAmbB) : o2Frac * pAmbB`
3. **Ascent/deco phases** (~lines 8950, 8999, 9006): `ppO2Seg = curSP > 0 ? min(curSP, pAmbSeg) : curO2 * pAmbSeg`

### Expected behaviour

When `settings.circuit === 'pSCR'`, the ppO₂ used for OTU/CNS accumulation should be
computed via `getEffectivePpo2(pAmb, 0, fO2, settings, depth, fHe)` which correctly routes
to `computePSCRFractions` and returns the actual loop ppO₂.

---

## Previously Fixed (confirmed in v2.30.13)

| Bug | Description | Status |
|-----|-------------|--------|
| BUG-57 | `ccrDiluentSurfaceLpm` pSCR double-depth-scaling via depth-dependent `fO2Loop` | ✅ Fixed — now uses `pSurf` for `computePSCRFractions` |
| BUG-58 | `scrRuntimeMin=0` at gas-plan time — always uses undepleted loop O₂ | ✅ Fixed — falls back to `decoBT` DOM value |
| BUG-59 | `ccrBailoutSettingsGroup` hidden for pSCR bailout-ON (condition was `isCCR`) | ✅ Fixed — now `isRB && bailoutOn` |
| BUG-60 | VPM `offLoopPath=true` for pSCR — reduced ceiling conservatism | ✅ Fixed — `offLoopPath` now excludes `pSCR` circuit |
| BUG-61 | VPM gas consumption depth=0 for arrow-format rows (`"0→40m"`) | ✅ Fixed — `endParseDepthM()` extracts max depth |
| BUG-62 | `appSettings.clear()` missed `waterDensity`, altitude, GF custom, etc. | ✅ Fixed — now clears all app-owned localStorage keys |

### Fix verification notes

- **BUG-57**: Confirmed correct. `computePSCRFractions(pSurf, ...)` returns a surface-based
  fO2Loop; `ccrGasLitres` then applies `(pAmb / pSurf)` once. For undepleted EAN50 at 10m
  with 1 min runtime, `fO2Old=0.2885` vs `fO2New=0.2885` at surface; at 20m `fO2Old=0.3234`
  (inflated) vs `fO2New=0.2885` (stable). Fix eliminates depth inflation. ✓

- **BUG-60**: `offLoopPath = isCCR && settings.circuit !== 'pSCR' && (forcedOCMode || curSP <= 0)`.
  For pSCR `curSP=0` but excluded → `offLoopPath=false`. pSCR now uses full VPM conservatism
  for ceiling rounding, consistent with its on-loop status. ✓

- **BUG-61**: `endParseDepthM("0→40m") = 40`, `endParseDepthM("40→0m") = 40`,
  `endParseDepthM("130→0ft") = 39.62m`. All arrow-format depth strings extract the maximum
  (deepest) depth, which is the correct depth for gas consumption calculations. ✓

---

## New Bugs Summary

| Bug | Area | Severity | Description |
|-----|------|----------|-------------|
| BUG-63 | VPM engine / pSCR | MEDIUM | VPM OTU/CNS uses `fO2 × pAmb` (diluent ppO₂) for pSCR instead of actual loop ppO₂ — overstates O₂ toxicity in VPM pSCR dives |
