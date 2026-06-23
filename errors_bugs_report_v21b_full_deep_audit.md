# LSP D-Planner + CCR — Errors & Bugs Report v21

**Repo:** `Three-Cats-LSP/LSP_D-planner-CCR`  
**Version analysed:** v2.30.26 (commit `35e0059`)  
**Date:** 2026-06-21  
**Audit result:** 353 checks, 0 failures  
**Scope:** Full deep audit of the entire application — not limited to CCR subsystems. All prior bugs BUG-01 through BUG-75 confirmed fixed. Two new bugs found.

---

## Systems Audited — All Clear

The following subsystems were fully verified with no new bugs:

| Subsystem | Status |
|---|---|
| Bühlmann ZHL-16C coefficients (N2/He a,b, half-times) | ✓ Correct |
| Schreiner equations (constant + linear pressure) | ✓ Correct |
| GF interpolation (Baker formula, shallow gradient) | ✓ Correct |
| ceiling() and mustStop() — altitude-aware via altSurfaceP | ✓ Correct |
| computeSurfaceGF — altitude-aware (BUG-69 fix) | ✓ Correct |
| VPM-B/GFS bubble model — radii, λ, γ, γ_c constants | ✓ Correct (Baker canonical) |
| VPM conservatism radius scaling 0–5 | ✓ Correct |
| OTU accumulation (exponent 5/6, NOAA limits) | ✓ Correct |
| CNS accumulation (NOAA table, interpolated) | ✓ Correct |
| EAD and END formulas — altitude and trimix aware | ✓ Correct |
| MOD formula — altitude and trimix aware | ✓ Correct |
| Best Mix formula | ✓ Correct |
| PADI NDL / Nitrox NDL / pressure group tables | ✓ Correct |
| Bühlmann NDL (buhNDL) | ✓ Correct |
| Gas switch selection (richest O2 within ppO2 limit) | ✓ Correct |
| initTissues / saturate / saturateLinear | ✓ Correct |
| Surface interval offgassing (Haldane) | ✓ Correct |
| altToPressure / water density / BAR_PER_METRE | ✓ Correct (industry standards) |
| Travel gas logic and switch depth | ✓ Correct |
| Min deco profile enforcement | ✓ Correct |
| MultiDeco transit mode (tissue skip during inter-stop transit) | ✓ Correct |
| Prior-dive tissue carry and O2 carry | ✓ Correct |
| Repetitive VPM dive bubble state carry | ✓ Correct |
| CCR tissue loading (all phases, phase-aware setpoints) | ✓ Correct |
| pSCR tissue loading (computePSCRFractions) | ✓ Correct |
| pSCR gas consumption (metRate × bypassRatio — BUG-75 fix) | ✓ Correct |
| ZHLEngine.calculate() headless CCR/pSCR CNS/OTU | ✓ Correct (BUG-73 fix) |
| computePlanExposureTotals CCR/pSCR/OC phasing | ✓ Correct |
| Multi Dive CCR-aware tissue loading | ✓ Correct (BUG-24 fix) |
| Gas plan imperial SAC conversion (sacDomToLpm) | ✓ Correct (BUG-71 fix) |
| Gas plan cylinder size imperial conversion (sz × 28.3168) | ✓ Correct (BUG-40 fix) |
| gpVolDisp in VPM/emergency blocks | ✓ Correct (BUG-72 fix) |
| Water vapour setting (0.0627 / 0.0577 user-selectable) | ✓ Correct |
| He half-time mode (Baker / Bühlmann 2003) | ✓ Partial — see BUG-76 |
| Decompression gas mixes persistence | ✓ Partial — see BUG-77 |
| PDF filename branding (LSP_CCR_) | ✓ Correct |
| SW network-first / cache-first strategy | ✓ Correct |
| Capacitor Android integration | ✓ Correct |
| appSettings.clear() key | ✓ Correct (BUG-41 fix) |
| addBailoutStressReserve depth-split | ✓ Correct (BUG-70 fix) |

---

## New Bugs

### BUG-76 — VPMEngine He half-time not updated when switching to Bühlmann 2003 mode: `_setHeHT1` is never defined

**File:** `index.html`  
**Severity:** LOW  
**Location:** `updateHeHalfTime()` lines 3949–3952; VPMEngine internal `ZHL16C_He` lines 7813–7831

```js
// updateHeHalfTime() calls:
if (window.VPMEngine && typeof window.VPMEngine._setHeHT1 === 'function') {
    window.VPMEngine._setHeHT1(src[0]);  // ← no-op: function never defined in VPMEngine
}
```

VPMEngine declares `ZHL16C_He` as a `const` internal array (line 7813) — compartment [0] has `ht: 1.88` (Baker 1998). No exposed setter exists on `window.VPMEngine`. `_setHeHT1` is checked but never defined, so the `typeof` guard silently no-ops.

When the user switches to **Bühlmann 2003** He half-times (ht[0]=1.51):
- Bühlmann engine: correctly updated (global `ZHL16C_HE_HT[0]` changed in-place) ✓  
- VPMEngine: still uses ht[0]=1.88 ✗

**Impact:** Trimix dives with VPM-B or VPM-B/GFS when `heHalfTimeMode = 'buhl2003'` — He[0] compartment half-time is wrong by 20% (1.88 vs 1.51 min). The fastest compartment drives the first deco stop on short deep dives. This could produce slightly different first-stop depths between Bühlmann+GF and VPM on trimix when buhl2003 mode is selected.

---

### BUG-77 — Deco gas mixes (`dg1Mix`, `dg2Mix`) not saved in `DECO_FIELDS` — lost on every page reload

**File:** `index.html`  
**Severity:** LOW  
**Location:** `appSettings.DECO_FIELDS` array, line ~17395

`DECO_FIELDS` saves all cylinder size/pressure fields (`cylDg1_size`, `cylDg1_pres`, `cylDg1_reserve`, etc.) but not the corresponding gas mix selectors (`dg1Mix`, `dg2Mix`), custom O₂ inputs (`dg1CustomO2`, `dg2CustomO2`), or trimix He inputs (`dg1TrimixHe`, `dg2TrimixHe`).

The custom O₂ inputs for trimix (`dg1TrimixO2`, `dg2TrimixO2`) are in `DECO_FIELDS` but the mix mode selector (`dg1Mix`, `dg2Mix`) is not — so the app restores the O₂ percentage but not the mode, leaving the gas card in its default ('none') state which ignores the trimix value.

**Impact:** On every page reload or explicit settings restore, the user's configured deco gas mixes revert to 'none' (not configured), while the cylinder sizes/pressures remain. The user must manually re-select their deco gases every session. This is particularly inconvenient for CCR divers who configure specific bailout mixes.

**Note:** The CCR-specific gas UI (circuit select, setpoints, etc.) IS fully persisted. Only the bottom/deco gas mix selectors are affected.

**Fix:** Add to `DECO_FIELDS`:
```js
'dg1Mix', 'dg1CustomO2', 'dg2Mix', 'dg2CustomO2',
'decoGas', 'decoCustomO2',
```
(Note: `decoGas` = bottom gas selector, `decoCustomO2` = bottom gas custom O₂ — also not persisted.)

---

## Summary Table

| # | Severity | Area | Description |
|---|---|---|---|
| BUG-76 | LOW | VPM / He HT | `VPMEngine._setHeHT1` never defined — buhl2003 He half-time not applied to VPM engine (Baker 1.88 always used) |
| BUG-77 | LOW | Settings / UX | Deco gas mix selectors (`dg1Mix`, `dg2Mix`, `decoGas`) not in `DECO_FIELDS` — lost on every page reload |

