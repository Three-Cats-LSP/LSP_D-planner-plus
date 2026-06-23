# LSP D-Planner+CCR — Errors & Bugs Report v10

**Version audited:** v2.30.11  
**Date:** 2026-06-21  
**Auditor:** Perplexity Computer (automated deep audit)  
**Repo:** `Three-Cats-LSP/LSP_D-planner-CCR`  
**Scope:** Full deep audit of CCR engine, gas plan, exports, UI/settings, and VPM parity after all v9 fixes confirmed resolved.

---

## Status of Previous Reports

All **BUG-01 through BUG-50** (reports v1–v9) have been verified **fixed** in v2.30.11. ✅  
This report covers new issues discovered in the v10 deep audit pass.

---

## Summary

| # | Area | Severity | Status |
|---|------|----------|--------|
| BUG-51 | CCR engine — `getCCRInertSchreinerParams` pSCR rate formula dimension error | High | Open |
| BUG-52 | CCR engine — `isCcrOnLoopGasLabel` does not recognise `pSCR` prefix | Medium | Open |
| BUG-53 | Exports — `shortMix()` collapses `CCR Air` / `pSCR Air` loop labels to `Air` | Medium | Open |
| BUG-54 | ZHLEngine headless — `diluentUseAsBailout` not saved/restored in `prevCCR` snapshot | Low | Open |
| BUG-55 | UI — `toggleCircuitFields()` does not hide `ccrBailoutSettingsGroup` for pSCR | Low | Open |
| BUG-56 | Gas plan — `ccrDiluentSurfaceLpm()` uses diluent fO2 for pSCR (should use inspired fO2) | Medium | Open |

---

## Detailed Bug Descriptions

---

### BUG-51 — `getCCRInertSchreinerParams` pSCR Schreiner rate has wrong dimension

**File:** `index.html`  
**Line:** ~5818–5828  
**Severity:** High  
**Area:** CCR engine — pSCR tissue loading (Bühlmann + VPM)

**Code:**
```js
const fr0 = computePSCRFractions(pAmbStart, fO2, fHe, cfg.scrRuntimeMin, cfg);
const pEnd = pAmbStart + pressureRate * 1;
const fr1 = computePSCRFractions(pEnd, fO2, fHe, cfg.scrRuntimeMin, cfg);
const ppH2O = WATER_VAPOR;
const inspN2Start = (pAmbStart - ppH2O) * fr0.fN2;
const inspHeStart = (pAmbStart - ppH2O) * fr0.fHe;
return {
  inspN2Start,
  inspHeStart,
  rN2: ((pEnd - ppH2O) * fr1.fN2 - inspN2Start) * pressureRate,
  rHe: ((pEnd - ppH2O) * fr1.fHe - inspHeStart) * pressureRate,
};
```

**Problem:**  
The Schreiner equation expects `rate` in units of **bar/min** (change in inspired partial pressure per minute). The rate terms `rN2` and `rHe` are computed as:

```
rN2 = [(pEnd - ppH2O)*fr1.fN2 - inspN2Start] * pressureRate
```

`pEnd - ppH2O)*fr1.fN2 - inspN2Start` is already a **pressure difference in bar** (one time-step of pressure change at rate `pressureRate` for 1 minute). Multiplying by `pressureRate` again squares the units, giving **bar²/min** instead of **bar/min**.

The correct formula should be:

```js
rN2: ((pEnd - ppH2O) * fr1.fN2 - inspN2Start)   // bar/min (already one step)
rHe: ((pEnd - ppH2O) * fr1.fHe - inspHeStart)
```

(i.e., divide by 1, not multiply by `pressureRate`). Because `pEnd = pAmbStart + pressureRate * 1` the delta term already encodes exactly one minute of rate change. The extra `* pressureRate` introduces a quadratic scaling error: at faster descent/ascent rates the inert loading will be substantially over- or under-stated for pSCR dives.

**Impact:** Incorrect tissue loading for pSCR during all linear (descent/ascent) segments. The faster the rate, the larger the error. Constant-depth segments use `saturateCCR` (Schreiner constant, not this path) and are unaffected.

---

### BUG-52 — `isCcrOnLoopGasLabel` does not recognise `pSCR` label prefix

**File:** `index.html`  
**Line:** ~5940–5942  
**Severity:** Medium  
**Area:** CCR engine — gas label classification

**Code:**
```js
function isCcrOnLoopGasLabel(label) {
  return typeof label === 'string' && label.toUpperCase().startsWith('CCR ');
}
```

**Problem:**  
In pSCR mode `loopMixLabelFor()` prefixes the diluent label with `"pSCR "` (e.g. `"pSCR Air"`). However `isCcrOnLoopGasLabel()` only checks for the `"CCR "` prefix (uppercase), so a label of `"pSCR Air"` returns **false**.

`isCcrOnLoopGasLabel()` is called by `isCcrDiluentGasLabel()` (line ~5951), which in turn is called by `ccrGasLitres()` (line ~5970) to decide whether to use metabolic-rate consumption or SAC-based consumption. When pSCR mode produces a gas key prefixed `"pSCR "`, `isCcrDiluentGasLabel()` returns false for that path and falls through to the SAC formula, resulting in incorrect (grossly overstated) diluent consumption in pSCR gas accounting.

**Expected fix:** Change the check to `label.toUpperCase().startsWith('CCR ') || label.toUpperCase().startsWith('PSCR ')`.

---

### BUG-53 — `shortMix()` in slate/messenger/text collapses `CCR Air` / `pSCR Air` to `"Air"`

**File:** `index.html`  
**Lines:** ~14141–14143 (`buildExportText`), ~14829–14831 (`buildMessengerText`), ~14548–14551 (`buildSlateText`)  
**Severity:** Medium  
**Area:** Exports — slate, messenger, text

**Code (representative, all three functions have the same pattern):**
```js
if (/air/i.test(s)) return 'Air';
```

**Problem:**  
Loop gas labels in CCR/pSCR mode are `"CCR Air"` or `"pSCR Air"` (produced by `loopMixLabelFor()`). The `shortMix()` helper in all three export functions applies a blanket `/air/i` regex that matches both strings and reduces them to `"Air"`, stripping the circuit prefix. This makes the exported plan ambiguous — a diver reading the slate has no indication they are on CCR/pSCR loop gas rather than an OC air supply.

**Expected fix:** Test for standalone Air (e.g. `/^air$/i` or after stripping the `CCR /pSCR ` prefix) so that `"CCR Air"` is rendered as `"CCR Air"` (or at minimum `"CCR/Air"`) rather than plain `"Air"`.

---

### BUG-54 — `ZHLEngine` headless does not save/restore `diluentUseAsBailout` in `prevCCR`

**File:** `index.html`  
**Line:** ~10877–10891 (prevCCR snapshot), ~11104–11116 (restore)  
**Severity:** Low  
**Area:** ZHLEngine headless interface / CCR test harness

**Code (snapshot):**
```js
const prevCCR = {
  circuit: ...,
  setpoint: ...,
  descentSetpoint: ...,
  bottomSetpoint: ...,
  bailout: ...,
  bailoutGfLow: ...,
  bailoutGfHigh: ...,
  scrLoopVolume: ...,
  scrMetabolicO2: ...,
  sacStress: ...,
  sacDecoCcr: ...,
  stressTimeMin: ...,
  problemSolveMin: ...,
  // ← diluentUseAsBailout is missing
};
```

**Problem:**  
`ZHLEngine.calculate()` saves and restores all CCR DOM fields to/from a `prevCCR` object so it can temporarily override them for headless computation. The `diluentUseAsBailout` field (element `#diluentUseAsBailout`) is included in `appSettings.DECO_FIELDS` and in `getCCRSettingsFromDOM()`, but is **not** saved in `prevCCR` and therefore **not restored** after a headless run. If a test harness call happens while `diluentUseAsBailout === 'on'`, that state will persist into subsequent interactive computations (e.g. `validateCcrGasConfiguration()` silently sees diluent-as-bailout as enabled even after the headless call returns).

**Expected fix:** Add `diluentUseAsBailout: document.getElementById('diluentUseAsBailout')?.value` to the `prevCCR` snapshot, and `if (prevCCR.diluentUseAsBailout != null) setEl('diluentUseAsBailout', prevCCR.diluentUseAsBailout);` in the restore block.

---

### BUG-55 — `toggleCircuitFields()` shows `ccrBailoutSettingsGroup` for pSCR even when bailout is off

**File:** `index.html`  
**Line:** ~5988–5989  
**Severity:** Low  
**Area:** UI — circuit field visibility

**Code:**
```js
const boGrp = document.getElementById('ccrBailoutSettingsGroup');
if (boGrp) boGrp.style.display = isRB ? '' : 'none';
```

**Problem:**  
`isRB` is true for both CCR and pSCR. The `ccrBailoutSettingsGroup` contains the Bailout GF Low/High selectors, which are CCR-specific settings (pSCR uses OC bailout but does not have a programmable setpoint loop that requires separate bailout GF tuning in the same way). Showing the bailout GF group for pSCR is not necessarily wrong in all workflows, but the `ccrSpDescentRow`, `ccrSpBottomRow`, `ccrSpDecoRow` fields are correctly hidden for pSCR (`if (el) el.style.display = isCCR ? '' : 'none'`), while the bailout GF group is shown for both.

More importantly: when pSCR mode is active, the `ccrBailoutSettingsGroup` is shown regardless of whether the `ccrBailoutToggle` is on or off (the bailout toggle visibility itself is already correct — it shows for `isRB`). This means pSCR users always see the bailout GF selectors even when bailout mode is off. Other CCR apps typically hide the GF sub-group until bailout is toggled on.

**Note:** This is a UX issue rather than a data-corruption bug. The GF values themselves are only consumed when `_ccrSettings.bailout === true`, so no incorrect computation results. However it presents settings that have no effect in the current mode, which can confuse users.

---

### BUG-56 — `ccrDiluentSurfaceLpm()` uses diluent fO2 for pSCR flow estimate

**File:** `index.html`  
**Line:** ~5943–5948  
**Severity:** Medium  
**Area:** Gas consumption — pSCR diluent flow

**Code:**
```js
function ccrDiluentSurfaceLpm() {
  const ccr = getCCRSettingsFromDOM();
  const metRate = getCcrMetabolicO2Rate(ccr);
  const bot = getBottomGasFractions();
  return metRate / Math.max(0.01, bot.fO2 || 0.21);
}
```

**Problem:**  
For a CCR, diluent surface flow rate (L/min) ≈ `metabolicO2 / fO2_diluent` is a reasonable approximation. However for **pSCR**, the diver breathes the loop gas whose fO2 is dynamically reduced by O₂ consumption (`computePSCRFractions()`). The actual diluent injection (fresh gas flow) for a pSCR is driven by the **scrubber bypass ratio and minute ventilation**, not purely by metabolic O₂ / fO2. Dividing metabolic O₂ rate by the *diluent* fO2 overestimates the required diluent flow in a pSCR because part of the O₂ deficit is made up by re-breathing loop gas; the true fresh-gas injection is only the bypass fraction of total ventilation.

More critically: `ccrDiluentSurfaceLpm()` is called from `ccrGasLitres()` for **all** rebreather circuit modes (CCR and pSCR), even though the pSCR gas consumption model is conceptually different. This path is reached because `isCcrDiluentGasLabel()` (line ~5951) is true for pSCR loop gas labels (once BUG-52 is fixed), meaning pSCR diluent consumption will still use the CCR metabolic-rate formula, which does not account for the bypass ratio.

**Impact:** pSCR diluent consumption is underestimated (for typical sport pSCR bypass ratios of 1:7–1:10, actual gas flow may be 3–5× the metabolic-only estimate). Divers may believe they have sufficient diluent for a pSCR dive when they actually do not.

**Note:** A full pSCR flow model requires the bypass ratio input (not currently a UI field). At minimum, a documentation note or warning should be added that pSCR gas consumption displayed is based on metabolic O₂ only and does not account for bypass flow.

---

## Non-Bug Observations (Code Quality / Future Consideration)

1. **`scrRuntimeMin` is not propagated in `saturateLinearCCR` segment re-split** (line ~5894–5907): The `totalTime` is split across segments proportionally, but `scrRuntimeMin` in `segCcr` always starts from the `cfg.scrRuntimeMin` at the beginning of the outer call — it is not incremented by the time already consumed in earlier segments of the same linear traversal. For short segments this is negligible, but it means `computePSCRFractions()` uses a slightly stale runtime within multi-segment linear passes. This is a precision concern, not a correctness bug, since the runtime offset within a single segment is typically < 1 min.

2. **`getInertFractions()` in VPM engine** (line ~8014–8020) ignores pSCR and uses the CCR setpoint formula for both CCR and pSCR:
   ```js
   function getInertFractions(o2Frac, heFrac, pAmb, setpoint, settings) {
     if (!setpoint || setpoint <= 0) {
       return { n2: 1 - o2Frac - heFrac, he: heFrac };
     }
     const den = Math.max(0.001, 1 - o2Frac);
     return { n2: Math.max(0, 1 - o2Frac - heFrac) / den, he: heFrac / den };
   }
   ```
   For pSCR the setpoint is returned as `0` by `getEffectiveSetpointAtDepth()` (line ~5737: `if (ccr.circuit === 'pSCR') return 0`), so this path falls through to the OC formula `n2 = 1 - fO2 - fHe`, which is correct for the fractions-as-passed case. However the VPM engine passes the **bottom setpoint** (line ~7237: `setpoint: settings.bottomSetpoint ?? settings.setpoint ?? 1.2`) even for pSCR, so in practice pSCR would get CCR-style inert fractions in the VPM path instead of OC-style. This is a latent inconsistency between the Bühlmann path (correct: returns 0 for pSCR) and the VPM path (uses bottomSetpoint regardless of circuit). Since the main VPM CCR tissue loading (`loadTissuesConstant` / `loadTissuesLinear`) calls `getInspiredInertPressures()` (the outer shared function which correctly handles pSCR), the impact is limited to the `calcStartOfDecoZone` / `projectedAscent` helpers inside VPMEngine. Worth reviewing in a future pass.

---

## Carry-Over (OC Main Repo — not back-ported)

The following bugs from previous reports remain open in `LSP_D-planner` (OC main), but are **out of scope** for this CCR repo audit:

- **BUG-40** — Bühlmann emergency gas `sz` not converted cu ft→L in OC main `index.html` line ~9789  
- **BUG-41** — `appSettings.clear()` only removes `lspDiveSettings_v3` in OC main line ~16449

---

## Verification Checklist

All previously reported bugs **confirmed fixed** in v2.30.11:

| Bug | Description | Status |
|-----|-------------|--------|
| BUG-01 through BUG-42 | All v1–v8 carry-overs | ✅ Fixed |
| BUG-43 | `getCcrMetabolicO2Rate` default was 0.85, now 1.5 | ✅ Fixed |
| BUG-44 | `validateCcrGasConfiguration` used wrong ppO2 limit for pSCR | ✅ Fixed |
| BUG-45 | `gpRequiredFor()` CCR label fallback | ✅ Fixed |
| BUG-46 | `ccrGasLitres()` depth-scaling | ✅ Fixed |
| BUG-47 | Meta description | ✅ Fixed |
| BUG-48 | `apple-mobile-web-app-title` | ✅ Fixed |
| BUG-49 | Gas Plan / Emergency PDF filename prefixes | ✅ Fixed |
| BUG-50 | CNS export header | ✅ Fixed |

---

*Report generated by automated deep audit. Do NOT apply fixes without explicit instruction.*
