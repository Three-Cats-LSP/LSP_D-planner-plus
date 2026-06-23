# Dive Kit App — Deco Engine Analysis
**App:** `app.skuba.diving` (Dive Kit)  
**Developer:** Ronny Majani / Lazuli Global  
**Play Store:** https://play.google.com/store/apps/details?id=app.skuba.diving  
**Documentation:** https://divekit.app/docs/  
**Analysis date:** June 2026

---

## TL;DR — Engine is Open Source (Abysner)

DiveKit's decompression engine is derived from — or shares its lineage with — the open-source
**Abysner** app by NeoTech (Rolf Smit). Ronny Majani is a GitHub contributor to Abysner
([PR #198](https://github.com/NeoTech-Software/Abysner/pull/198)) and maintains a fork at
[`ronnymajani/Abysner`](https://github.com/ronnymajani/Abysner).

The full engine source is in:
- **`Buhlmann.kt`** — tissue compartment model, M-value/ceiling/GF math, ZHL-16A/B/C tables
- **`BuhlmannUtilities.kt`** — Schreiner equation, water vapour (Antoine), CCR Schreiner inputs
- **`Configuration.kt`** — all default values (GF, ascent rates, stop grid, ppO2 limits, CCR)
- **`DecompressionPlanner.kt`** — stop logic, gas switching, ascent loop, lookahead/TTS
- **`DecoGrid.kt`** — deco-stop grid snapping
- **`OxygenToxicityCalculator.kt`** — CNS and OTU

Repo: https://github.com/NeoTech-Software/Abysner  
Engine docs (Ronny's PR): https://github.com/NeoTech-Software/Abysner/pull/198

This supersedes the need for APK binary analysis of the deco engine. The ZHL-16C coefficient
table is readable directly in source; no reverse engineering required.

---

## Versions Analysed

| Version | Source | Notes |
|---|---|---|
| **1.1.8** | APKCombo (Dec 2025) | No `libDecoEngine.so` — C++ engine absent in this release |
| **2.8.5** | User device (2026-06-11) | C++ engine present (`libDecoEngine.so`); confirmed via DEX |
| **Abysner main** | GitHub (NeoTech-Software/Abysner) | Full Kotlin source — canonical engine implementation |

---

## Architecture

### DiveKit App Stack (v2.8.5)

| Component | Technology |
|---|---|
| UI framework | React Native 19.2.3 + Expo SDK 56.0.0 |
| JS runtime | Hermes v98 bytecode (25 MB bundle) |
| Native bridge | Nitro Modules (margelo/nitro) — JSI bridge |
| **Deco engine** | **`libDecoEngine.so`** — C++ native HybridObject |
| Storage | MMKV via `libNitroMmkv.so` |
| Crash tracking | Sentry (`de.sentry.io`, project `divekit-app`) |

The C++ engine (`libDecoEngine.so`) is DiveKit's own native port/re-implementation of the Abysner
Kotlin engine, bridged to JavaScript via Nitro Modules:

```
com.divekit.deco.DecoEnginePackage        (React Native package registration)
  └─ com.margelo.nitro.divekit.deco.DecoEngineOnLoad
       └─ System.loadLibrary("DecoEngine")   → libDecoEngine.so
```

### Abysner Engine Layer Diagram

```
DivePlanner          ← public entry point; multi-level, multi-dive orchestration
  └─ DecompressionPlanner  ← stop times, ascents, gas switching, TTS
       ├─ DecoGrid          ← snaps continuous ceiling to 3 m / 10 ft stop grid
       └─ Buhlmann          ← tissue loading and raw ceiling (DecompressionModel interface)
OxygenToxicityCalculator   ← CNS and OTU (post-plan, from segment list)
GasPlanner                 ← used/reserve gas, worst-case ascent, real-gas cylinder model
```

All internal calculations are in **absolute ambient pressure (bar)**. Conversions to/from meters
happen at the edges via `Pressure.kt`.

---

## ZHL-16C Coefficient Tables (from Source)

Source file: [`Buhlmann.kt`](https://github.com/NeoTech-Software/Abysner/blob/main/domain/src/commonMain/kotlin/org/neotech/app/abysner/domain/decompression/algorithm/buhlmann/Buhlmann.kt)

Cross-checked by the Abysner authors against Subsurface, DecoTengu, and dipplanner — with source links in comments.

**Note:** Across ZHL-16A, 16B, 16C — **only the N₂ `a` values differ**. Half-times, `b` values, and all He values are identical across all three variants.

### ZHL-16C (default, most conservative)

| # | N₂ t½ | N₂ a | N₂ b | He t½ | He a | He b |
|---|---|---|---|---|---|---|
| 1 | 5.0 | 1.1696 | 0.5578 | 1.88 | 1.6189 | 0.4770 |
| 2 | 8.0 | 1.0000 | 0.6514 | 3.02 | 1.3830 | 0.5747 |
| 3 | 12.5 | 0.8618 | 0.7222 | 4.72 | 1.1919 | 0.6527 |
| 4 | 18.5 | 0.7562 | 0.7825 | 6.99 | 1.0458 | 0.7223 |
| 5 | 27.0 | **0.6200** | 0.8126 | 10.21 | 0.9220 | 0.7582 |
| 6 | 38.3 | **0.5043** | 0.8434 | 14.48 | 0.8205 | 0.7957 |
| 7 | 54.3 | **0.4410** | 0.8693 | 20.53 | 0.7305 | 0.8279 |
| 8 | 77.0 | **0.4000** | 0.8910 | 29.11 | 0.6502 | 0.8553 |
| 9 | 109.0 | **0.3750** | 0.9092 | 41.20 | 0.5950 | 0.8757 |
| 10 | 146.0 | **0.3500** | 0.9222 | 55.19 | 0.5545 | 0.8903 |
| 11 | 187.0 | **0.3295** | 0.9319 | 70.69 | 0.5333 | 0.8997 |
| 12 | 239.0 | **0.3065** | 0.9403 | 90.34 | 0.5189 | 0.9073 |
| 13 | 305.0 | **0.2835** | 0.9477 | 115.29 | 0.5181 | 0.9122 |
| 14 | 390.0 | **0.2610** | 0.9544 | 147.42 | 0.5176 | 0.9171 |
| 15 | 498.0 | **0.2480** | 0.9602 | 188.24 | 0.5172 | 0.9217 |
| 16 | 635.0 | 0.2327 | 0.9653 | 240.03 | 0.5119 | 0.9267 |

Bold = values that differ from ZHL-16A/B. All other cells are identical across A/B/C.

---

## Algorithm Details (from Source)

### Schreiner Equation (`BuhlmannUtilities.kt`)

```kotlin
fun schreinerEquation(initialTissuePressure, inspiredGasPressure, time, halfTime, inspiredGasRate): Double {
    val timeConstant = ln(2.0) / halfTime
    return inspiredGasPressure + (inspiredGasRate * (time - 1/timeConstant)) -
           (inspiredGasPressure - initialTissuePressure - inspiredGasRate/timeConstant) * exp(-timeConstant * time)
}
```

Standard Schreiner form: `P(t) = Pio + R(t - 1/k) - (Pio - Po - R/k)·e^(-kt)`

Used for both flat and depth-change segments (handles the `R ≠ 0` ascent/descent case correctly,
unlike the simpler Haldane form). Water vapour is subtracted by the caller before computing `Pio` and `R`.

### Water Vapour (`BuhlmannUtilities.kt`, `Buhlmann.kt`)

Computed via the **Antoine equation** at body temperature 37°C:

```kotlin
private val waterVapourPressure: Double = waterVapourPressureInBars(37.0)
// ≈ 0.0627 bar
```

Subtracted from **inspired gas pressure only** (not from the ceiling calculation). This matches
DiveKit's documented value of "about 0.0627 bar".

### Ceiling and Gradient Factors (`Buhlmann.kt`)

**Per-compartment ceiling** (with combined N₂/He coefficients):

```kotlin
val a = (n2ValueA * pN2 + heValueA * pHe) / pTotal
val b = (n2ValueB * pN2 + heValueB * pHe) / pTotal
val ceiling = (pTotal - a * gf) / (gf/b + 1.0 - gf)
```

`gf = 1.0` → raw Bühlmann M-value. Smaller `gf` → deeper (more conservative) ceiling.

**GF interpolation** across the dive (`toleratedInertGasPressure`):
- `gfLow` applied at the deepest ceiling reached so far (`lowestCeiling`, tracked throughout)
- `gfHigh` applied at the surface
- Linear interpolation between those two anchor points
- Solved as a line through two (ambient, M-value) points, then inverted to get tolerated pressure

This is the standard Subsurface / OSTC gradient-factor approach. References cited in code:
Subsurface commit 67d59ff, OSTC GF doc (heinrichsweikamp), dive-tech M-values, DecoTengu.

### CCR Tissue Loading (`Buhlmann.kt`, `BuhlmannUtilities.kt`)

On CCR, setpoint clamps O₂; effective inert gas inspired pressure is:

```
(ambient - setpoint) * inertFraction / (1 - oxygenFractionDiluent)
```

Still linear in ambient → same Schreiner equation applies. Segments that cross the setpoint
pressure (ambient = setpoint during ascent or descent) are **split at the crossing point**. Above
setpoint: ambient O₂ only, no inert gas loading (`inspiredPressure = 0, rate = 0`).

Verified in `BuhlmannUtilitiesTest` against Helling CCR Schreiner + iterative Haldane simulation.

### Planning Loop (`DecompressionPlanner.kt`)

The whole engine plans in **whole minutes** — ascent/descent speeds are rounded, not the stop times.

Stop loop:
1. Find first deco ceiling (`findFirstDecoCeiling`)
2. Check/switch to better OC deco gas at current depth
3. Ascend to first ceiling (`addDecoDepthChange`)
4. Repeat: add 1-minute stops until ceiling clears enough to move up, ascend
5. Safety valve: `PlanningException` after 1000 minutes if ceiling never clears

**Lookahead:** Before committing to a stop, the planner simulates the ascent via snapshot/rollback
(`lookahead {}`), to check if off-gassing during the climb already clears the ceiling (avoids
unnecessary 1-minute penalties). Same mechanism used for TTS calculations.

**Gas switching (OC):** At each grid stop, `findBetterGasOrFallback()` checks for a richer gas
within ppO₂ and END limits. Gas-switch time (default: 1 min) is spent on the *old* gas. CCR stays
on loop; CCR→OC bailout handled as special case.

### Deco Stop Grid (`DecoGrid.kt`)

- Raw ceiling (continuous bar) is snapped **up** (deeper) to the next 3 m grid point
- If between surface and last stop depth, clamps to last stop
- `findNextDecoStopPressure(from)` → next shallower grid point
- Grid built so stops always land on whole display units (meters or feet)

---

## Default Configuration (from `Configuration.kt`)

These are **Abysner's** defaults. DiveKit uses different defaults (confirmed from JS bundle):

| Parameter | Abysner default | DiveKit default |
|---|---|---|
| GF Low | **60** (0.6) | **50** (0.50) |
| GF High | **70** (0.7) | **80** (0.80) |
| Max ascent rate | 5 m/min | 9 m/min (deep), 3 m/min (shallow) |
| Max descent rate | 20 m/min | 20 m/min |
| Last stop depth | 3 m | 6 m (settings schema) |
| Deco step | 3 m | 3 m |
| Gas switch time | 1 min | 0 min (default) |
| Max ppO₂ (deco) | 1.6 bar | 1.4/1.5/1.6 (by O₂ band) |
| Max ppO₂ (bottom) | 1.4 bar | 1.4 bar |
| Salinity | Fresh | Salt |
| CCR low setpoint | 0.7 bar | — |
| CCR high setpoint | 1.2 bar | — |
| CCR loop volume | 7.0 L | — |
| CCR metabolic O₂ | 0.8 L/min | 0.85 L/min |
| SAC (working) | 20 L/min | 20 L/min |
| SAC (deco/reserve) | 40 L/min | 15 L/min (deco RMV) |

DiveKit's split ascent rate (9 m/min deep / 3 m/min shallow) and ppO₂ band system are DiveKit-specific additions not present in Abysner's configuration model.

---

## Oxygen Toxicity (`OxygenToxicityCalculator.kt`)

Computed post-plan from the finished segment list.

### CNS

Exponential fit to the NOAA exposure table, in two line segments:

```kotlin
fun getCnsPpo2Slope(ppO2: Double): Double {
    return if (ppO2 <= 1.5) -11.7853 + (1.93873 * ppO2)
    else                    -23.6349 + (9.80829 * ppO2)
}
// Contribution = (duration_seconds) * exp(slope) * 100  [%]
```

Below ppO₂ 0.5 bar: no CNS contribution. Based on Baker/Helling.

### OTU

Improved Baker/Helling formula, valid for flat, ascending, and descending segments:

```kotlin
val pm = (ppo2Start + ppo2End) - 1.0
val rate = pm.pow(5.0/6.0) * (1.0 - 5.0 * (ppo2End - ppo2Start).pow(2) / 216 / (pm * pm))
return rate * durationInMinutes
```

Below ppO₂ 0.5 bar: no OTU contribution.

On CCR: effective ppO₂ = `min(max(setpoint, diluentPpO2), ambient)`.

---

## Comparison vs MultiDeco

DiveKit publishes a 26-scenario cross-reference dataset. Key documented divergences:

| Topic | Detail |
|---|---|
| Gas switch depths | EAN50 @ 21 m, O₂ @ 6 m — match exactly |
| Decozone start | Within ~one 3 m step on 25/26 scenarios |
| Deep trimix first stop | May differ 1–4 steps — He off-gases faster than diver climbs |
| Integration timestep | DiveKit: whole minutes (Abysner design); MultiDeco: coarser |
| Water vapour | DiveKit/Abysner: ~0.0627 bar; MultiDeco default: 0.0577 bar |

Cross-reference dataset (local copies in repo):

| File | Contents |
|---|---|
| `divekit-cross-reference/inputs.json` | 26 dive scenarios |
| `divekit-cross-reference/divekit-results.json` | DiveKit output per scenario |
| `divekit-cross-reference/multideco-results.json` | MultiDeco output |
| `divekit-cross-reference/notes.json` | Per-scenario commentary |

---

## Comparison vs GUE DecPlanner

| Topic | GUE DecPlanner | Dive Kit / Abysner |
|---|---|---|
| Architecture | Capacitor/Ionic web app, pure JS | React Native + C++ native (Kotlin-derived) |
| Engine language | JavaScript (Decimal.js) | C++ native (from Kotlin Abysner engine) |
| ZHL model | ZHL-16C | ZHL-16C |
| VPM-B | Yes (primary) | No |
| Default GF | 20/85 (OC) | 50/80 |
| CCR | Yes | Yes |
| Open source | Engine JS extractable | Abysner Kotlin source fully open (AGPL v3) |

---

## APK Binary Analysis Summary

### v1.1.8 (APKCombo, Dec 2025)
- Hermes v96, 13 MB bundle — UI only, no deco engine SO
- 31 native `.so` files — no `libDecoEngine.so`
- Engine was absent or pre-compiled into a different form

### v2.8.5 (User device, 2026-06-11)
- Hermes **v98**, **25 MB** bundle (UI grew substantially — CCR screens, air breaks, plan variants)
- 7 DEX files (was 6) — new DEX contains `DecoEngineOnLoad` and `DecoEnginePackage`
- `System.loadLibrary("DecoEngine")` confirmed in `classes5.dex`
- `libDecoEngine.so` in separate arm64 split APK (not included in provided zip)

### JS Bundle Default Settings Object (confirmed from v2.8.5 bytecode)

```js
{
  gfLow: 50, gfHigh: 80,
  ascentRateDeep: 9, ascentRateShallow: 3, ascentRateChangeDepth: 6,  // m/min
  descentRate: 20,
  lastStopDepth: 6, decoStepSize: 3,
  stopTimePrecision: 'roundMinutes',
  maxPO2Lean: 1.4, maxPO2Mid: 1.5, maxPO2Rich: 1.6,
  waterType: 'salt',
  workingRmv: 20, decoRmv: 15, ccrMetabolicO2Rate: 0.85,
  gasSwitchTime: 0, switchGasAtMod: true,
  treatO2AsNarcotic: false,
  airBreaksEnabled: false, airBreakPO2Threshold: 1.4,
  airBreakInterval: 20, airBreakDuration: 5, airBreaksOnCCR: false,
  includeTravelInLevelTime: false,
  maxENDWarning: 30, gasDensityWarning: 5.2, gasDensityCritical: 6.2,
  cnsWarningThreshold: 80, otuWarningThreshold: 300, minPO2Warning: 0.18
}
```

### Tissue State Bridge (from string pool)

```
"Invalid tissue state from native engine: expected 16 compartments, got N2=..."
```

C++ engine returns 16 N₂ + 16 He compartment values to JavaScript for repetitive dive chaining
and UI display. Confirms 16-compartment model at the native layer.

---

## Notes for LSP D-Planner

1. **GF defaults differ:** DiveKit = 50/80, Abysner = 60/70, GUE = 20/85. LSP allows user to set — confirm the UI makes this discoverable.
2. **Water vapour 0.0627 bar:** Both DiveKit and Abysner use this (Antoine @ 37°C). LSP uses 0.0577 (MultiDeco alignment). Consider making it configurable or documenting the divergence.
3. **Whole-minute planning (Abysner design decision):** Ascent/descent speeds are rounded, not stop times. This is the stated design rationale. LSP uses 1-second integration — explain divergence in docs.
4. **Ceiling formula verified in source:** The `calculateCeiling` and `toleratedInertGasPressure` functions are now readable — use them as a cross-check against LSP's implementation.
5. **CCR split-at-setpoint:** Abysner explicitly handles the segment-crossing-setpoint case. LSP CCR implementation should verify this edge case is handled.
6. **Air breaks:** DiveKit adds configurable air breaks on top of the Abysner base. Abysner itself does not have air breaks (confirmed from `Configuration.kt`). This is a DiveKit-specific feature.
7. **Cross-reference dataset:** `divekit-cross-reference/` provides 3-way LSP vs MultiDeco vs DiveKit validation — run after any ZHL+GF engine change.
8. **Coefficient table:** ZHL-16C table from Abysner source is now canonical reference for LSP. Matches Subsurface, MultiDeco, GUE DecPlanner.
9. **GF auto-raise:** DiveKit silently raises GF High to the minimum value that produces a valid plan. Abysner throws `PlanningException` after 1000 min. Both protect against infinite loops; approaches differ.

---

## Source References

### Open Source Engine (Abysner)
- Repo: https://github.com/NeoTech-Software/Abysner (AGPL v3)
- `Buhlmann.kt`: https://github.com/NeoTech-Software/Abysner/blob/main/domain/src/commonMain/kotlin/org/neotech/app/abysner/domain/decompression/algorithm/buhlmann/Buhlmann.kt
- `BuhlmannUtilities.kt`: https://github.com/NeoTech-Software/Abysner/blob/main/domain/src/commonMain/kotlin/org/neotech/app/abysner/domain/decompression/algorithm/buhlmann/BuhlmannUtilities.kt
- `Configuration.kt`: https://github.com/NeoTech-Software/Abysner/blob/main/domain/src/commonMain/kotlin/org/neotech/app/abysner/domain/core/model/Configuration.kt
- Ronny's engine docs PR: https://github.com/NeoTech-Software/Abysner/pull/198
- Ronny's fork: https://github.com/ronnymajani/Abysner

### DiveKit Documentation
- https://divekit.app/docs/engine/how-it-works/
- https://divekit.app/docs/engine/gradient-factors/
- https://divekit.app/docs/engine/design-decisions/
- https://divekit.app/docs/engine/assumptions-and-limits/
- https://divekit.app/docs/engine/compared-to-multideco/

### Algorithm Sources (from Abysner code comments)
- Subsurface deco.cpp: https://github.com/subsurface/subsurface/blob/35556b9f/core/deco.cpp#L83
- OSTC GF document: https://www.heinrichsweikamp.net/downloads/OSTC_GF_web_en.pdf
- DecoTengu model: https://wrobell.dcmod.org/decotengu/model.html
- dive-tech M-values: http://www.dive-tech.co.uk/resources/mvalues.pdf
- Robert Helling, "Why is Bühlmann not like Bühlmann": https://thetheoreticaldiver.org/wordpress/index.php/2017/11/02/why-is-buhlmann-not-like-buhlmann/
- Erik Baker: "Understanding M-Values", "Oxygen Toxicity Calculations"
- A. A. Bühlmann, *Decompression: Decompression Sickness*

---

*Analysis: APK inspection (v1.1.8 + v2.8.5) + Abysner open-source engine (full source read)*  
*v2.8.5 build date: 2026-06-11 23:43 UTC. Engine lineage confirmed via ronnymajani/Abysner and PR #198.*
