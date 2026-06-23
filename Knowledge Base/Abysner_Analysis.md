# Abysner Open-Source Dive Planner — Analysis
**Repo:** [NeoTech-Software/Abysner](https://github.com/NeoTech-Software/Abysner)  
**License:** AGPLv3  
**Language:** Kotlin Multiplatform + Compose Multiplatform  
**Platforms:** Android, iOS (store builds carry a small fee to cover dev costs; source build is free)  
**Stars:** 36 (as of May 2026) — actively maintained  
**Last commit:** 2026-05-20

---

## 1. Why This Matters for LSP D-Planner

Abysner is the most readable, cleanly documented open-source implementation of **Bühlmann ZHL-16 A/B/C with gradient factors** available for mobile. Unlike Subsurface (C++) or decotengu (Python), the Kotlin source is structured for clarity with extensive inline comments explaining every formula. The CCR Schreiner implementation is particularly well documented and peer-reviewed against ScubaBoard references.

Key value:
- Verified ZHL-16C table to compare against MultiDeco's Subsurface-variant table
- Complete GF linear interpolation implementation (full derivation in comments)
- Schreiner equation for both OC and CCR in one file
- 8 reference plans cross-validated against Subsurface and DIVESOFT.APP

---

## 2. Module Structure

```
Abysner/
├── domain/          ← pure algorithm, no Android/iOS dependencies
│   ├── decompression/
│   │   ├── algorithm/buhlmann/
│   │   │   ├── Buhlmann.kt          ← tissue model, GF ceiling, compartment tables
│   │   │   └── BuhlmannUtilities.kt ← Schreiner eq, CCR Schreiner inputs, water vapour
│   │   ├── DecompressionPlanner.kt  ← stop search, ascent planning
│   │   └── DecoGrid.kt              ← depth/time grid for table output
│   ├── diveplanning/
│   │   └── DivePlanner.kt           ← full multi-segment planner, gas switches, CCR SP
│   ├── gasplanning/
│   │   ├── GasPlanner.kt            ← reserve gas, TTS worst-point algorithm
│   │   └── OxygenToxicityCalculator.kt
│   └── core/
│       ├── model/Configuration.kt   ← all user settings, defaults
│       ├── physics/                 ← pressure, gas density, real gas model
│       └── model/Gas.kt
├── composeApp/      ← shared UI (Android + iOS)
├── androidApp/      ← Android entry point
└── iosApp/          ← iOS entry point
```

---

## 3. ZHL-16 Compartment Tables

`CompartmentParameters(n2HalfTime, n2A, n2B, heHalfTime, heA, heB)`

### ZHL-16A
| Comp | N2 HT | N2 a   | N2 b   | He HT  | He a   | He b   |
|------|-------|--------|--------|--------|--------|--------|
| 1    | 5.0   | 1.1696 | 0.5578 | 1.88   | 1.6189 | 0.4770 |
| 2    | 8.0   | 1.0000 | 0.6514 | 3.02   | 1.3830 | 0.5747 |
| 3    | 12.5  | 0.8618 | 0.7222 | 4.72   | 1.1919 | 0.6527 |
| 4    | 18.5  | 0.7562 | 0.7825 | 6.99   | 1.0458 | 0.7223 |
| 5    | 27.0  | 0.6667 | 0.8126 | 10.21  | 0.9220 | 0.7582 |
| 6    | 38.3  | 0.5933 | 0.8434 | 14.48  | 0.8205 | 0.7957 |
| 7    | 54.3  | 0.5282 | 0.8693 | 20.53  | 0.7305 | 0.8279 |
| 8    | 77.0  | 0.4701 | 0.8910 | 29.11  | 0.6502 | 0.8553 |
| 9    | 109.0 | 0.4187 | 0.9092 | 41.20  | 0.5950 | 0.8757 |
| 10   | 146.0 | 0.3798 | 0.9222 | 55.19  | 0.5545 | 0.8903 |
| 11   | 187.0 | 0.3497 | 0.9319 | 70.69  | 0.5333 | 0.8997 |
| 12   | 239.0 | 0.3223 | 0.9403 | 90.34  | 0.5189 | 0.9073 |
| 13   | 305.0 | 0.2971 | 0.9477 | 115.29 | 0.5181 | 0.9122 |
| 14   | 390.0 | 0.2737 | 0.9544 | 147.42 | 0.5176 | 0.9171 |
| 15   | 498.0 | 0.2523 | 0.9602 | 188.24 | 0.5172 | 0.9217 |
| 16   | 635.0 | 0.2327 | 0.9653 | 240.03 | 0.5119 | 0.9267 |

### ZHL-16B (differs from A at comps 6, 7, 8, 13)
| Comp | N2 HT | N2 a   | N2 b   | He HT  | He a   | He b   |
|------|-------|--------|--------|--------|--------|--------|
| 5    | 27.0  | 0.6667 | 0.8126 | 10.21  | 0.9220 | 0.7582 |
| 6    | 38.3  | **0.5600** | 0.8434 | 14.48  | 0.8205 | 0.7957 |
| 7    | 54.3  | **0.4947** | 0.8693 | 20.53  | 0.7305 | 0.8279 |
| 8    | 77.0  | **0.4500** | 0.8910 | 29.11  | 0.6502 | 0.8553 |
| 13   | 305.0 | **0.2850** | 0.9477 | 115.29 | 0.5181 | 0.9122 |
*(all other comps identical to ZHL-16A)*

### ZHL-16C (differs from A at comps 5–15)
| Comp | N2 HT | N2 a   | N2 b   | He HT  | He a   | He b   |
|------|-------|--------|--------|--------|--------|--------|
| 5    | 27.0  | **0.6200** | 0.8126 | 10.21  | 0.9220 | 0.7582 |
| 6    | 38.3  | **0.5043** | 0.8434 | 14.48  | 0.8205 | 0.7957 |
| 7    | 54.3  | **0.4410** | 0.8693 | 20.53  | 0.7305 | 0.8279 |
| 8    | 77.0  | **0.4000** | 0.8910 | 29.11  | 0.6502 | 0.8553 |
| 9    | 109.0 | **0.3750** | 0.9092 | 41.20  | 0.5950 | 0.8757 |
| 10   | 146.0 | **0.3500** | 0.9222 | 55.19  | 0.5545 | 0.8903 |
| 11   | 187.0 | **0.3295** | 0.9319 | 70.69  | 0.5333 | 0.8997 |
| 12   | 239.0 | **0.3065** | 0.9403 | 90.34  | 0.5189 | 0.9073 |
| 13   | 305.0 | **0.2835** | 0.9477 | 115.29 | 0.5181 | 0.9122 |
| 14   | 390.0 | **0.2610** | 0.9544 | 147.42 | 0.5176 | 0.9171 |
| 15   | 498.0 | **0.2480** | 0.9602 | 188.24 | 0.5172 | 0.9217 |
| 16   | 635.0 | 0.2327 | 0.9653 | 240.03 | 0.5119 | 0.9267 |
*(comps 1–4 identical to ZHL-16A; bold = differs from A)*

### Comparison: Abysner ZHL-16C vs MultiDeco vs Subsurface

**Abysner ZHL-16C comp 5 a-value: 0.6200** — matches Subsurface/MultiDeco exactly.  
All three use the **same Subsurface-derived ZHL-16C variant** (not canonical Bühlmann 0.6491).  
Abysner, Subsurface, and MultiDeco are algorithmically consistent on ZHL-16C a-values.

---

## 4. Core Algorithm — Tissue Loading

**File:** `Buhlmann.kt`

### Schreiner Equation (OC)
```kotlin
fun schreinerEquation(
    initialTissuePressure: Double,
    inspiredGasPressure: Double,
    time: Double,
    halfTime: Double,
    inspiredGasRate: Double   // dP/dt of inspired inert gas
): Double {
    val timeConstant = ln(2.0) / halfTime
    return (inspiredGasPressure
        + (inspiredGasRate * (time - (1.0 / timeConstant)))
        - ((inspiredGasPressure - initialTissuePressure - (inspiredGasRate / timeConstant))
           * exp(-timeConstant * time)))
}
```

### CCR Schreiner Inputs
On CCR, O2 pp is held constant at setpoint. Inspired inert gas pressure and rate become:
```kotlin
fun ccrSchreinerInputs(
    startPressure: Double,
    pressureRate: Double,
    inertFraction: Double,        // fraction of inert gas in diluent
    oxygenFractionDiluent: Double,
    setpoint: Double,             // water-vapour-corrected
): Pair<Double, Double> {
    if (startPressure < setpoint) return Pair(0.0, 0.0)  // pure O2 loop, no inert
    val denominator = 1.0 - oxygenFractionDiluent
    return Pair(
        inertFraction * (startPressure - setpoint) / denominator,  // inspiredGasPressure
        inertFraction * pressureRate / denominator                  // inspiredGasRate
    )
}
```
Verified against Helling's CCR Schreiner derivation and brute-force Haldane simulation.

### Water Vapour Pressure
Antoine equation, SI units, at alveolar temperature 37°C:
```kotlin
private val waterVapourPressure: Double = waterVapourPressureInBars(37.0)
// = ~0.0627 bar at 37°C
```
Initial tissue N2 loading:
```kotlin
pNitrogen = partialPressure(atmosphericPressure - waterVapourPressure, 0.79)
```

### Mixed-gas a/b values (trimix)
Compartment a and b are pressure-weighted by current N2/He tissue loads:
```kotlin
val a = (n2ValueA * pNitrogen + heValueA * pHelium) / pTotal
val b = (n2ValueB * pNitrogen + heValueB * pHelium) / pTotal
```

---

## 5. Gradient Factor Ceiling Calculation

Full derivation is documented in `toleratedInertGasPressure()` with step-by-step algebra.

**Key formula (GF linear interpolation):**
```
pToleratedSurface      = (P_surf / b + a - P_surf) * gfHigh + P_surf
pToleratedLowestCeil   = (P_lowest / b + a - P_lowest) * gfLow + P_lowest

gfSlopeNumerator = lowestCeiling - surface
                 + gfLow * (lowestCeiling * (1-b)/b + a)
                 - gfHigh * (surface * (1-b)/b + a)
gfSlope = gfSlopeNumerator / (lowestCeiling - surface)
gfIntercept = surface + gfHigh * (surface*(1-b)/b + a) - gfSlope * surface

ceiling = (pTotal - gfIntercept) / gfSlope
```

**Lowest ceiling tracking:** The model tracks the deepest ceiling reached during the dive (`lowestCeiling`). GF interpolation anchors gfLow at that ceiling and gfHigh at the surface, creating the linear gradient line. This matches the standard Heinrichs-Weikamp / Baker implementation.

---

## 6. Default Configuration

From `Configuration.kt`:

| Parameter | Default | Notes |
|---|---|---|
| Algorithm | ZHL-16C | Can select A, B, or C |
| GF Low | 0.60 (60%) | Conservative default |
| GF High | 0.70 (70%) | |
| Max PPO2 deco | 1.6 bar | |
| Max PPO2 bottom | 1.4 bar | |
| Max END | 30 m | |
| Ascent rate | 5 m/min | |
| Descent rate | 20 m/min | |
| Deco step size | 3 m | |
| Last deco stop | 3 m | |
| Salinity | Fresh | |
| Altitude | 0 m | |
| SAC rate | 20 L/min | |
| SAC out-of-air | 40 L/min | |
| Gas switch time | 1 min | |
| CCR low SP | 0.7 bar | Used during descent |
| CCR high SP | 1.2 bar | Used at bottom + ascent |
| CCR loop volume | 7 L | |
| CCR metabolic O2 | 0.8 L/min | |
| Contingency deeper | 3 m | |
| Contingency longer | 3 min | |

---

## 7. Planning Algorithm

**File:** `DecompressionPlanner.kt` + `DivePlanner.kt`

### Calculation is in whole minutes
By design: avoids rounding ambiguity between second-precision internal calculation and minute-precision output. Ascent/descent speeds are snapped to whole-minute steps.

### Ascent stop search
Binary search: for each deco stop depth, find the minimum whole-minute stop time that reduces the ceiling to the next shallower stop.

### Setpoint switching (CCR)
- Descent: switches from low SP to high SP at configured depth (or at first bottom section)
- Ascent: optionally switches back to low SP at configured depth
- Abysner checks for setpoint crossings mid-segment and splits the Schreiner call if needed

### Gas switch timing
A configurable `gasSwitchTime` (default 1 min) is added at the depth where a gas switch occurs.

### Multi-dive / surface interval
Surface off-gassing uses the same Schreiner equation with ambient pressure as the "dive", running time forward until the next dive begins.

---

## 8. Reserve Gas / TTS Algorithm

**File:** `GasPlanner.kt`

Rather than assuming the worst point is end-of-bottom-time, Abysner computes **Time-To-Surface (TTS)** at every segment boundary, finds the maximum, and uses that as the worst-case ascent point for reserve gas. On multi-level profiles this correctly identifies cases where a shallower but longer section accumulates more deco obligation than the deep portion.

---

## 9. Reference Plan Observations (vs Subsurface)

From the README, 9 reference plans compared against Subsurface (6.0.5214+) and DIVESOFT.APP:

| Plan | Abysner vs Subsurface |
|---|---|
| 20m/20min OC air (plan 1) | **Identical** runtime and stop structure |
| 30m/30min multi-gas (plan 2) | Same runtime (50 min); Subsurface merges ascent+stop, Abysner shows separately |
| 45m/15min trimix (plan 3) | Same runtime (33 min); same stop structure |
| 60m/20min trimix altitude 1000m (plan 4) | 59 min (Abysner) vs 63 min (Subsurface) — minor differences at 12, 6, 3m stops |
| Multi-level cave (plan 5) | Same runtime (67 min); 1 min diff at 6m stop |
| CCR 30m/30min (plan 6) | Same runtime (39 min); CNS 17% vs 16% |
| CCR bailout (plan 7) | 52 min (Abysner) vs 51 min (Subsurface) |
| CCR trimix 60m (plan 8) | 70 min (Abysner) vs 69 min (Subsurface); Abysner needs 24m stop, Subsurface does not |
| Repetitive 30m/30min SI=30min (plan 9) | Dive 1 identical; Dive 2: 65 vs 66 min, same stop structure |

**Conclusion:** Abysner produces results very close to Subsurface for OC dives. Minor differences (1–4 min) exist in complex plans, attributable to minute-precision calculation vs second-precision + rounding in Subsurface.

---

## 10. Comparison to MultiDeco ZHL-16C

| Feature | Abysner | MultiDeco |
|---|---|---|
| ZHL-16C source | Subsurface-derived (a5=0.6200) | Subsurface-derived (a5=0.6200) |
| N2 halftimes | Standard (5, 8, 12.5 … 635 min) | Non-standard (derived: `k_N2 = k_He / 2.6595`) |
| He halftimes | Standard (1.88, 3.02 … 240 min) | Standard (1.88, 3.02 … 240 min) |
| GF implementation | Full linear interpolation (lowestCeiling anchor) | Full linear interpolation (same) |
| Water vapour | Antoine eq at 37°C (~0.0627 bar) | Likely same (standard) |
| VPM-B | Not supported | Full TVPM implementation |
| CCR | Yes (Schreiner) | Yes (Schreiner) |
| Source | Fully open (AGPLv3) | Proprietary (binary only) |

**Key divergence:** MultiDeco uses a non-standard N2 halftime set derived from He halftimes via the diffusion ratio (×2.6595). Abysner uses the canonical published N2 halftimes. This means plans will differ on N2-dominant tissues (slower compartments) despite identical a/b values.

---

## 11. Files of Most Interest

| File | What's useful |
|---|---|
| `domain/…/buhlmann/Buhlmann.kt` | Complete ZHL tables for A, B, C; GF ceiling derivation with algebra comments; tissue loading OC+CCR |
| `domain/…/buhlmann/BuhlmannUtilities.kt` | Schreiner eq; CCR Schreiner inputs; water vapour Antoine equation |
| `domain/…/model/Configuration.kt` | All defaults; algorithm enum; unit snapping |
| `domain/…/DecompressionPlanner.kt` | Stop search; ascent planning logic |
| `domain/…/DivePlanner.kt` | Full planning pipeline; gas switches; setpoint switching |
| `domain/…/GasPlanner.kt` | Reserve gas; TTS worst-point algorithm |
| `domain/src/commonTest/…` | Unit tests validating every component against known references |

---

*Analysis based on Abysner main branch as of 2026-05-20.*  
*Source: [https://github.com/NeoTech-Software/Abysner](https://github.com/NeoTech-Software/Abysner)*
