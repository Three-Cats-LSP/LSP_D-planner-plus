# GUE DecPlanner 4 (v1.4.2) — Reverse Engineering Analysis

**Package:** `cloud.udive.app`  
**Version:** 1.4.2 (December 2024)  
**APK size:** ~19 MB  
**Source:** APKPure CDN  
**Analysis date:** June 2026

---

## 1. Architecture Overview

GUE DecPlanner 4 is built on **Capacitor (Ionic)** — a hybrid mobile framework that wraps a web application in a native Android/iOS shell. The entire dive planning logic runs as JavaScript inside a WebView.

**Key finding: There are zero native `.so` shared libraries.** Unlike MultiDeco (which embeds `libmultideco.so`), GUE DecPlanner ships its decompression engine entirely in JavaScript.

### APK Structure

```
DecoPlannerMobile_1.4.2.apk
├── AndroidManifest.xml         — package: cloud.udive.app
├── classes.dex                 — Capacitor shell + plugins only
├── classes2.dex
├── classes3.dex
├── assets/public/
│   ├── index.html              — Stencil/Ionic app entry point
│   └── build/
│       ├── p-b31951de.js       — 3.4 MB  ← DECO ENGINE IS HERE
│       ├── p-0246f3f7.entry.js — 3.6 MB  ← UI components
│       └── *.js                — other Stencil chunks
└── res/                        — Android resources/icons
```

### DEX Contents (Java/Kotlin layer)

JADX decompilation reveals the Java layer is purely a Capacitor shell. No decompression logic exists in Java. Notable plugins present:

| Package | Role |
|---|---|
| `com.capacitorjs.plugins.filesystem` | File read/write |
| `com.capacitorjs.plugins.geolocation` | Altitude/GPS |
| `com.capacitorjs.plugins.keyboard` | Keyboard handling |
| `com.capacitorjs.plugins.statusbar` | UI chrome |
| `com.google.firebase.*` | Analytics + license auth |

---

## 2. JavaScript Engine Discovery

### Bundle: `p-b31951de.js` (3.4 MB, minified)

The deco engine is class `tC`, starting at byte offset **820,925** in the minified bundle. Total size: ~54 KB of minified JS, 2,585 lines when beautified.

**Key class map:**

| Class | Role |
|---|---|
| `tC` | Main VPM-B calculation engine (top-level API) |
| `QI` | ZHL-16 Bühlmann implementation (OC/CCR) |
| `qI` | Single tissue compartment (holds ppHe, ppN2, a/b coeffs) |
| `WI` | Gradient Factor controller |
| `NI` | Preferences / default settings |
| `ZI` | pSCR partial-pressure calculations |
| `RI` | Dive utilities / pressure conversions |

Entry point: `tC.runVPM(missionData, isBailout)` — returns boolean success. Calls `this.calculate()` internally.

---

## 3. VPM-B Engine (class `tC`)

### 3.1 Core VPM-B Constants

From the `tC` constructor:

```javascript
this.critical_radius_n2_microns_basic = 0.55    // μm — baseline N2 nucleus radius
this.critical_radius_he_microns_basic = 0.45    // μm — baseline He nucleus radius
this.crit_volume_parameter_lambda     = 6500    // atm·min/μm²
this.gradient_onset_of_imperm_atm    = 8.2     // atm — crush pressure threshold
this.surface_tension_gamma           = 0.0179  // N/m — surface tension γ
this.skin_compression_gammac         = 0.257   // N/m — skin compression γ_c
this.regeneration_time_constant      = 20160   // min = 14 days
this.pressure_other_gases_mmhg       = 102     // mmHg (CO₂ + H₂O)
```

These are **identical** to the canonical VPM-B reference implementation (Baker 1998). The same values appear in MultiDeco (`libmultideco.so` rodata).

### 3.2 Conservatism Effect on Critical Radius

The `conservatism` parameter (default: `2`, range inferred `0–4` from `modifiers = [0,2,4,6,8]`) adjusts critical radii at runtime:

```javascript
this.critical_radius_n2_microns = critical_radius_n2_microns_basic + conservatism / 20
this.critical_radius_he_microns = critical_radius_he_microns_basic + conservatism / 20
```

**At default conservatism=2:**
- N2 critical radius: `0.55 + 2/20 = 0.65 μm`
- He critical radius: `0.45 + 2/20 = 0.55 μm`

The `modifiers` array `[0, 2, 4, 6, 8]` maps to 5 conservatism levels (0–4), adding up to `+0.40 μm` at maximum.

### 3.3 VPM-B GF Mode (Hybrid Option)

The engine supports an optional VPM-GFS hybrid mode where VPM-B allowable gradients are scaled by a GF-High factor:

```javascript
this.VPM_GFS    = false   // default off
this.VPM_gf_high = 90    // % (used only when VPM_GFS=true)
```

In `calc_ascent_ceiling()`:
```javascript
let t = this.VPM_GFS ? this.VPM_gf_high / 100 : 1;
o = r + constant_pressure_other_gases - i * t;  // i = VPM allowable gradient
```

### 3.4 Helium Half-Time Multiplier

An undocumented feature: `helium_half_time_multiplier` shifts He halftimes relative to N2 halftimes. Default is `0` (no adjustment).

The formula shifts N2 halftimes toward He halftimes proportionally:
```javascript
e[n] = ((N2_halftime[n] - He_halftime[n]) / 10.1) * helium_half_time_multiplier
// New He halftime = He_base + e[n]
// New N2 halftime = N2_base + i[n]  (i=0 when multiplier >= 0)
```

At `multiplier=0` (default): halftimes are pure standard values.  
At `multiplier=10.1`: He and N2 halftimes merge to identical values.

---

## 4. ZHL-16 Bühlmann Engine (class `QI`)

### 4.1 Model Selection

The QI class defaults to **ZHL-16B** (`this.modelName = "ZHL16B"`), but also supports ZHL-16C. The GUE UI appears to use ZHL-16B for the Bühlmann plan.

### 4.2 Complete ZHL-16 Coefficient Table

The `setTimeConstants()` function holds two full tables. Column format:  
`[He_t½, N2_t½, aN2 (bar), bN2, aHe (bar), bHe]`

**Base data array (shared between ZHL-16B and ZHL-16C):**

| Comp | He t½ (min) | N2 t½ (min) | aN2 (bar) | bN2 | aHe (bar) | bHe |
|------|-------------|-------------|-----------|-----|-----------|-----|
| 1 | 1.88 | 5.0 | 16.189 | 0.4770 | 11.696 | 0.5578 |
| 2 | 3.02 | 8.0 | 13.83 | 0.5747 | 10.000 | 0.6514 |
| 3 | 4.72 | 12.5 | 11.919 | 0.6527 | 8.618 | 0.7222 |
| 4 | 6.99 | 18.5 | 10.458 | 0.7223 | 7.562 | 0.7825 |
| 5 | 10.21 | 27.0 | 9.220 | 0.7582 | 6.200 | 0.8126 |
| 6 | 14.48 | 38.3 | 8.205 | 0.7957 | 5.043 | 0.8434 |
| 7 | 20.53 | 54.3 | 7.305 | 0.8279 | 4.410 | 0.8693 |
| 8 | 29.11 | 77.0 | 6.502 | 0.8553 | 4.000 | 0.8910 |
| 9 | 41.2 | 109.0 | 5.950 | 0.8757 | 3.750 | 0.9092 |
| 10 | 55.19 | 146.0 | 5.545 | 0.8903 | 3.500 | 0.9222 |
| 11 | 70.69 | 187.0 | 5.333 | 0.8997 | 3.295 | 0.9319 |
| 12 | 90.34 | 239.0 | 5.189 | 0.9073 | 3.065 | 0.9403 |
| 13 | 115.29 | 305.0 | 5.181 | 0.9122 | 2.835 | 0.9477 |
| 14 | 147.42 | 390.0 | 5.176 | 0.9171 | 2.610 | 0.9544 |
| 15 | 188.24 | 498.0 | 5.172 | 0.9217 | 2.480 | 0.9602 |
| 16 | 240.03 | 635.0 | 5.119 | 0.9267 | 2.327 | 0.9653 |

**ZHL-16C** (differences from ZHL-16B: only the He `a` coefficients differ for compartments 5–16):

| Comp | ZHL-16B aHe | ZHL-16C aHe | Difference |
|------|-------------|-------------|------------|
| 5 | 6.667 | 6.200 | −0.467 |
| 6 | 5.600 | 5.043 | −0.557 |
| 7 | 4.947 | 4.410 | −0.537 |
| 8 | 4.500 | 4.000 | −0.500 |
| 9 | 4.187 | 3.750 | −0.437 |
| 10 | 3.798 | 3.500 | −0.298 |
| 11 | 3.497 | 3.295 | −0.202 |
| 12 | 3.223 | 3.065 | −0.158 |
| 13 | 2.850 | 2.835 | −0.015 |
| 14 | 2.737 | 2.610 | −0.127 |
| 15 | 2.523 | 2.480 | −0.043 |
| 16 | 2.327 | 2.327 | 0 (identical) |

> **Critical finding:** Compartment 5 He `a` value for ZHL-16C is **6.200** — exactly matching MultiDeco, Subsurface, and Abysner. All four apps share the same ZHL-16C He `a` table.

### 4.3 Halftime Ratios

N2/He halftime ratios (standard relationship):

| Comp | He t½ | N2 t½ | N2/He ratio |
|------|-------|-------|-------------|
| 1 | 1.88 | 5.0 | 2.66 |
| 8 | 29.11 | 77.0 | 2.65 |
| 16 | 240.03 | 635.0 | 2.65 |

Average N2/He ratio ≈ **2.65** — standard Bühlmann diffusion ratio. Unlike MultiDeco (which uses a custom diffusion-derived set), GUE DecPlanner uses standard published halftimes.

### 4.4 GF Ceiling Calculation

```javascript
ceiling() {
  for (t = 0; t < 16; t++) {
    i = tissues[t].getMaxAmb(gradient.getGradientFactor()) - ambientPress;
    if (i > e) e = i;
  }
  return e;  // excess pressure over ambient
}
```

`getMaxAmb(gf)` in tissue compartment `qI`:
```javascript
// maxAmb = (ppHe + ppN2 - a * gf) / (gf/b - gf + 1)   [Bühlmann M-value]
```

GF slope is computed linearly from first deco stop depth to surface:
```javascript
setGfSlopeAtDepth(firstDecoDepth) {
  gfSlope = (gfHigh - gfLow) / (0 - firstDecoDepth);
}
setGfAtDepth(currentDepth) {
  if (gfSlope < 1 && currentDepth >= 0)
    gf = currentDepth * gfSlope + gfHigh;
}
```

### 4.5 Default Gradient Factors

From `NI.setDefaultPrefs()`:

| Setting | Value |
|---|---|
| GF Low (OC) | **0.20** (20%) |
| GF High (OC) | **0.85** (85%) |
| GF Low (bailout) | **0.90** (90%) |
| GF High (bailout) | **0.90** (90%) |
| Multilevel GF mode | `true` |

The bailout GF of 90/90 produces essentially no gradient factor restriction — appropriate for emergency ascent.

---

## 5. Gas Equations

### 5.1 Schreiner Equation (linear pressure change)

```javascript
schreiner_equation__(Pi, R, t, k, P0) {
  return Pi + R * (t - 1/k) - (Pi - P0 - R/k) * Math.exp(-k * t);
}
```

Parameters: `Pi` = inspired gas pressure, `R` = rate of pressure change, `t` = time, `k` = time constant (ln2/t½), `P0` = initial tissue pressure.

Used for: descent, ascent, and constant-rate segments.

### 5.2 Haldane Equation (constant depth)

```javascript
haldane_equation__(P0, Pi, k, t) {
  return P0 + (Pi - P0) * (1 - Math.exp(-k * t));
}
```

Used for: deco stops, surface intervals.

### 5.3 Water Vapor Pressure

From `NI` class (metric, default):  
`pH2O = 0.627 msw` (≈ 62.7 mbar ≈ 47 mmHg at 37°C — Bühlmann standard)

In Imperial mode: `pH2O = 2.0461 fsw`

---

## 6. CCR / pSCR Support

### 6.1 Breathing Configuration

Set via `this.configuration` (default: `"OC"`). Supported values: `"OC"`, `"CCR"`, `"pSCR"`.

### 6.2 CCR Inspired Gas (`calc_inspired_gas`)

```javascript
if (configuration == "CCR" && setpoint != 0) {
  let gasFraction = fHe + fN2;
  let heRatio = fHe / gasFraction;
  let n2Ratio = fN2 / gasFraction;
  let fO2_ccr = setpoint / PI.depth2press(depth);
  let diluent = 1 - fO2_ccr;
  fHe = diluent * heRatio;
  fN2 = diluent * n2Ratio;
  fO2 = fO2_ccr;
}
```

Bailout mode forces `setpoint = 0` for depths shallower than `minimum_profile_depth` (set from profile).

### 6.3 pSCR

pSCR uses class `ZI` (RMV + metabolic O₂ consumption) to compute the PF (partial pressure fraction) accounting for O₂ drop across the scrubber. The minimum safe pO₂ floor is `0.16 bar`.

### 6.4 Bailout Conservatism

When `run_bailout = true`:
- Uses `conservatism_bailout` (separate from normal conservatism)
- Uses `gfLow_bailout` / `gfHigh_bailout` (90/90 default)
- Gas setpoints set to 0 (OC breathing assumed)
- Surface desat intervals still calculated with OC

### 6.5 Descent ppO₂

`this.descentppO2 = 0.7` — used during descent on CCR before reaching setpoint depth.

---

## 7. VPM-B Allowable Gradient Formula

The initial allowable gradient (maximum supersaturation) per compartment:

```javascript
// For N2:
G_N2 = (2γ(γ_c - γ)) / (r_N2 × γ_c)   // converted: Pa → msw via units_factor
// For He:
G_He = (2γ(γ_c - γ)) / (r_He × γ_c)

// With: γ=0.0179 N/m, γ_c=0.257 N/m, r = regenerated critical radius
```

**Repetitive diving adjustment** (`vpm_repetitive_algorithm`):

```javascript
// If max_actual_gradient > initial_allowable_gradient (bubble was crushed):
r_new = r_initial + (r_initial - r_skin) * exp(-surface_interval / regeneration_time)
// r_skin = equilibrium radius at crushing pressure (from surface tension equations)
// Otherwise: r_new = r_initial (no adjustment needed)
```

This models bubble nucleus regeneration over surface intervals with `τ = 20160 min = 14 days`.

---

## 8. Dive Profile Parameters (defaults from NI)

| Parameter | Metric | Imperial |
|---|---|---|
| Ascent rate | 9 m/min | 30 ft/min |
| Descent rate | 20 m/min | 60 ft/min |
| Last stop depth | 3 m | 10 ft |
| Deco step size | 3 m | 10 ft |
| Min deco stop time | 1 min | 1 min |
| Altitude default | 1000 m | 3300 ft |
| Max bottom ppO₂ | 1.2 bar | 1.2 bar |
| Max deco ppO₂ | 1.2 bar | 1.2 bar |
| Max O₂ ppO₂ | 1.5 bar | 1.5 bar |
| Dive RMV | 20 L/min | — |
| Deco RMV | 15 L/min | — |

---

## 9. Altitude Dive Algorithm

When `altitude_dive_algorithm = "on"`:
- `ascent_to_altitude_hours` and `hours_at_altitude_before_dive` are used
- `diver_acclimatized_at_altitude` flag adjusts surface nitrogen loading
- `starting_acclimatized_altitude` = 0 m (sea level default)
- Barometric pressure adjusted for dive altitude

---

## 10. Authentication / Licensing

Firebase SDK is bundled (`com.google.firebase.*`). This is used for:
- License key validation
- Usage analytics

The deco engine itself has no license checks — it is instantiated directly in JavaScript. Firebase authentication gates the UI layer, not the computation.

---

## 11. Cross-Application Comparison

### VPM-B Constants

| Parameter | GUE DecPlanner | MultiDeco |
|---|---|---|
| γ (surface tension) | 0.0179 | 0.0179 |
| γ_c (skin compression) | 0.257 | 0.257 |
| r_N2 basic (μm) | 0.55 | 0.55 |
| r_He basic (μm) | 0.45 | 0.45 |
| λ (crit volume) | 6500 | 6500 |
| Regeneration τ | 20160 min | 20160 min |

**All VPM-B constants are identical between GUE DecPlanner and MultiDeco.**

### ZHL-16 Table (compartment 5, key discriminator)

| App | Model | Comp 5 aN2 | Comp 5 aHe |
|---|---|---|---|
| GUE DecPlanner (ZHL-16C) | ZHL-16C | 9.220 | **6.200** |
| GUE DecPlanner (ZHL-16B) | ZHL-16B | 9.220 | 6.667 |
| MultiDeco | ZHL-16C | 9.220 | **6.200** |
| Subsurface | ZHL-16C | 9.220 | **6.200** |
| Abysner | ZHL-16C | 9.220 | **6.200** |

**All four apps use the same ZHL-16C He `a` table** — the Subsurface variant. The `a5_He = 6.200` value differs from some published tables (e.g., Baker's original 6.200 vs Bühlmann's 6.667 for ZHL-16B comp 5).

### Halftime Source

| App | N2 halftimes | He halftimes | N2/He ratio |
|---|---|---|---|
| GUE DecPlanner | Standard Bühlmann | Standard Bühlmann | ~2.65 |
| MultiDeco | Non-standard (diffusion-derived) | Custom | k_N2 = k_He / 2.6595 |
| Abysner | Standard Bühlmann | Standard Bühlmann | ~2.65 |
| Subsurface | Standard Bühlmann | Standard Bühlmann | ~2.65 |

**Notable:** MultiDeco uses custom non-standard halftimes; all others use standard published values.

---

## 12. Technical Summary

| Feature | Value |
|---|---|
| Engine type | JavaScript (no native binary) |
| Framework | Capacitor (Ionic) |
| Deco algorithm | VPM-B (primary) + ZHL-16B/C (GF mode) |
| Bühlmann default | ZHL-16B |
| Supported configs | OC, CCR, pSCR |
| Repetitive diving | Yes (VPM bubble regeneration) |
| Altitude support | Yes |
| Multi-level GF | Yes |
| VPM-GFS hybrid | Yes (optional) |
| CCR bailout mode | Yes (separate GF 90/90) |
| Default GF (OC) | 20/85 |
| Default GF (bailout) | 90/90 |

---

## 13. Files Referenced

| File | Description |
|---|---|
| `assets/public/build/p-b31951de.js` | Main engine bundle (3.4 MB, minified) |
| `assets/public/build/p-0246f3f7.entry.js` | UI components (3.6 MB) |
| Beautified engine | `/tmp/gue_deco_engine_pretty.js` (2585 lines) |
| Beautified QI class | `/tmp/gue_qi_pretty.js` (1089 lines) |

---

*Analysis performed by extracting class `tC` (VPM-B engine, offset 820925) and class `QI` (ZHL-16 engine, offset 803714) from the minified JavaScript bundle. No decompilation required — the engine is open JavaScript. JADX was used to confirm no native code exists in the DEX layer.*
