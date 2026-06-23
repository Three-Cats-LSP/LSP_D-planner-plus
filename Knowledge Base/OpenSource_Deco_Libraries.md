# Open-Source C++ Decompression Algorithm Libraries

**Study date**: 2026-06-18  
**Purpose**: Analysis of open-source ZHL-16C / gradient-factor implementations in C++ for comparison with LSP D-Planner engine  
**Sources**:
- [guyfleeman/libbuhlmann](https://github.com/guyfleeman/libbuhlmann) — full planning library, ZHL-16A/B/C, GF, trimix
- [tl5915/Buehlmann-ZHL-16C](https://github.com/tl5915/Buehlmann-ZHL-16C) — compact Arduino/DIY dive computer library, N2-only, OC+CCR
- [ericmanning8/Modified-Buhlmann-Decompression-Algorithm](https://github.com/ericmanning8/Modified-Buhlmann-Decompression-Algorithm) — academic ZHL-16 with exertion modifier (BME 405 / UDive watch project)

---

## 1. libbuhlmann (`guyfleeman/libbuhlmann`)

### Overview

| Property | Value |
|---|---|
| Author | Guy Fleeman |
| Language | C++ (C++14/17, CMake) |
| Stars | 4 |
| Last updated | 2025-06-18 |
| Algorithm | ZHL-16A, ZHL-16B, ZHL-16C |
| Gas support | N2 + He (trimix) |
| GF support | Yes — GF Lo/Hi slope |
| Units | Imperial (feet, atm) |
| Status | **WARNING: contains bugs, no stable release** |

### Architecture

```
libbuhlmann/
├── include/
│   ├── model/
│   │   ├── BuhlmannConstatnts.hpp   ← ZHL-16A/B/C tables, WV, CO2 constants
│   │   ├── BuhlmannCompartment.hpp  ← single tissue compartment
│   │   ├── BuhlmannModel.hpp        ← main model + deco schedule generator
│   │   └── BuhlmannModelVersion.hpp ← enum: ZHL_16A/B/C
│   ├── planning/
│   │   ├── WorkPlan.hpp             ← dive profile input + gas optimizer
│   │   └── WorkPlanEntry.hpp        ← single segment (depth, time, gas)
│   ├── BreathingGas.hpp             ← O2/He/H2 fractions, MOD, END, PPO2
│   ├── DiverParameters.hpp          ← GF Lo/Hi, ascent/descent rate, maxPPO2
│   └── units/Units.hpp             ← physical constants
└── src/
    ├── model/
    │   ├── BuhlmannCompartment.cpp  ← ceiling formula, Haldane update
    │   └── BuhlmannModel.cpp        ← full engine: init, update, deco gen
    └── planning/
        ├── WorkPlan.cpp             ← profile loading, gas selection
        └── WorkPlanEntry.cpp
```

### Key Constants (`BuhlmannConstatnts.hpp`)

```cpp
constexpr float WATER_VAPOR_PRESSURE = 0.0627f;  // same as Subsurface default
constexpr float CO2_PRESSURE         = 0.0534f;  // alveolar CO2 (Schreiner model)
constexpr float BUHLMANN_RQ          = 1.0f;     // respiratory quotient
constexpr int   ZHL_16C_COMPARTMENTS = 17;       // 16 + compartment 1b
```

**WV = 0.0627** — confirms this is the "standard" Bühlmann value. Same as Subsurface/LSP.  
**RQ = 1.0** — simplification; real value ~0.8–0.9. Affects alveolar partial pressure.  
**CO2 = 0.0534** — uses Schreiner alveolar sub-model (not all engines do this).

### ZHL-16C Table (verbatim from source)

17 compartments (includes 1b):

| Cpt | N2 t½ | N2 a | N2 b | He t½ | He a | He b |
|-----|--------|------|------|--------|------|------|
| 1   | 4.0    | 1.2599 | 0.5240 | 1.51  | 1.7424 | 0.4245 |
| 1b  | 5.0    | 1.1696 | 0.5578 | 1.88  | 1.6189 | 0.4770 |
| 2   | 8.0    | 1.0000 | 0.6514 | 3.02  | 1.3830 | 0.5747 |
| 3   | 12.5   | 0.8618 | 0.7222 | 4.72  | 1.1919 | 0.6527 |
| 4   | 18.5   | 0.7562 | 0.7825 | 6.99  | 1.0458 | 0.7223 |
| 5   | 27.0   | 0.6491 | 0.8126 | 10.21 | 0.9220 | 0.7582 |
| 6   | 38.3   | 0.5316 | 0.8434 | 14.48 | 0.8205 | 0.7957 |
| 7   | 54.3   | 0.4681 | 0.8693 | 20.53 | 0.7305 | 0.8279 |
| 8   | 77.0   | 0.4301 | 0.8910 | 29.11 | 0.6502 | 0.8553 |
| 9   | 109.0  | 0.4049 | 0.9092 | 41.20 | 0.5950 | 0.8757 |
| 10  | 146.0  | 0.3719 | 0.9222 | 55.19 | 0.5545 | 0.8903 |
| 11  | 187.0  | 0.3447 | 0.9319 | 70.69 | 0.5333 | 0.8997 |
| 12  | 239.0  | 0.3176 | 0.9403 | 90.34 | 0.5189 | 0.9073 |
| 13  | 305.0  | 0.2828 | 0.9477 | 115.29| 0.5181 | 0.9122 |
| 14  | 390.0  | 0.2716 | 0.9544 | 147.42| 0.5176 | 0.9171 |
| 15  | 498.0  | 0.2523 | 0.9602 | 188.24| 0.5172 | 0.9217 |
| 16  | 635.0  | 0.2327 | 0.9653 | 240.03| 0.5119 | 0.9267 |

These match the canonical ZHL-16C table exactly.

### Alveolar Sub-Model (Schreiner)

```cpp
// updateLowLevelDiffusion() — BuhlmannModel.cpp
float alveolarPP = (ambientPressure - WATER_VAPOR_PRESSURE 
                    + ((1 - rq) / rq) * CO2_PRESSURE) 
                   * internalGasRatio;
```

With `RQ=1.0` this simplifies to:
```
alveolarPP = (P_amb - 0.0627) * fracGas
```

If RQ were 0.8 (more realistic), the CO2 term would add `0.25 * 0.0534 * fracGas`. The choice of RQ=1.0 effectively ignores the CO2 correction, making this identical to the simpler Bühlmann formula.

**LSP D-Planner uses the same formula** — `(P_amb - 0.0627) * fracN2`.

### Haldane Tissue Update

```cpp
// updateHaldaneGas() — BuhlmannModel.cpp
float k = (float) M_LN2 / halfLife;
return pt0 + (initialAlveolarPressure - pt0) * (1.0f - exp(-k * time));
```

Standard Haldane equation: `P(t) = P_alv + (P0 - P_alv) * e^(-k*t)`  
This is **constant-pressure** (not Schreiner rate-of-change). Works for static depth segments.

### Ceiling Formula (with GF)

```cpp
// getCeiling() — BuhlmannCompartment.cpp
float compositePressure = pressureN2 + pressureHe;
float aFactor = (N2_a * pressureN2 + He_a * pressureHe) / compositePressure;
float bFactor = (N2_b * pressureN2 + He_b * pressureHe) / compositePressure;

// GF-corrected ceiling:
float ceiling = (compositePressure - aFactor * gf) 
                / (gf / bFactor + 1.0f - gf);
```

This is the standard GF-modified M-value ceiling formula. When `gf=1.0` (no conservatism), reduces to pure Bühlmann. Matches LSP D-Planner implementation.

### Gradient Factor Implementation

GF slope is computed **at the start of deco**, from first stop to surface:

```cpp
// setGradientFactorSlope() — BuhlmannModel.cpp
gradientFactorSlope = (GFHi - GFLo) / (endStopDepth - startStopDepth);

// gradientFactor() — returns GF at a given depth
float gf = (gradientFactorSlope * currentStopDepth) + GFHi;
```

**Note**: The slope formula here computes: `GF(depth) = slope * depth + GFHi`  
This means GF increases as depth decreases (GFLo at deepest stop → GFHi at surface).  
**However, the sign convention looks inverted** — this is one of the known bugs author warned about. Correct formula should give GFLo at first stop and GFHi at surface.

### Decompression Schedule Generator

```cpp
// generateDecompressionSchedule() — BuhlmannModel.cpp
const float STOP_DEPTH_INTERVAL = 10.0f;  // 10 ft stops
const float LAST_STOP_DEPTH     = 10.0f;  // last stop at 10 ft
const float STOP_TIME_INTERVAL  = 60.0f;  // 1 min increments (in seconds)
```

Algorithm:
1. Find ceiling → round up to nearest 10 ft stop
2. At each stop: simulate in 60-second increments until ceiling drops below next stop
3. Gas selection: highest O2 fraction below MOD (`getOptimizedGasForDepth()`)
4. Continue until ceiling < 0.1 ft threshold

**Stop interval is 10 ft (imperial).** LSP uses 3 m (~10 ft), so comparable.

### Trimix / Mixed Gas Support

Compartment pressures track N2 and He separately:
```cpp
float pressureN2;
float pressureHe;
```
Combined a/b are weighted by partial pressures:
```cpp
aFactor = (N2_a * pN2 + He_a * pHe) / (pN2 + pHe);
bFactor = (N2_b * pN2 + He_b * pHe) / (pN2 + pHe);
```
This is standard ZHL-16C trimix formula. LSP D-Planner currently handles trimix the same way.

### Identified Bugs / Limitations

1. **GF slope sign** — `gradientFactor()` returns `slope * depth + GFHi`, which may give inverted GF at shallow stops (author flagged as buggy)
2. **NDL stub** — `getNoDecompressionTime()` returns `0.0f` always (not implemented)
3. **RQ=1.0** — CO2 correction term cancels out; fine for N2 but slight inaccuracy for He mixes
4. **OpenMP misuse** — `#pragma omp parallel` wraps `for` loops without proper reduction guards; data races possible
5. **Imperial units only** — 33 ft/atm hardcoded, no metric path

---

## 2. tl5915/Buehlmann-ZHL-16C (Arduino Library)

### Overview

| Property | Value |
|---|---|
| Author | tl5915 |
| Language | C++ (Arduino-compatible) |
| Stars | 1 |
| Last updated | 2026-05-15 |
| Algorithm | ZHL-16C (N2 only — no He) |
| Gas support | OC (fixed FiO2) + CCR (fixed PPO2) |
| GF support | Yes — GF Lo/Hi, `ripNtear(true)` forces GF=100% |
| Units | Metric (meters, atm) |
| Target | Embedded / DIY dive computers |

### Architecture

Single-file implementation (`src/ZHL16C.cpp` + `src/ZHL16C.h`). Designed for microcontroller RAM constraints.

```
ZHL16C/
├── src/
│   ├── ZHL16C.h    ← DecoResult struct + public API
│   └── ZHL16C.cpp  ← complete engine in ~300 lines
└── examples/
    └── Dive_Computer/
        └── Dive_Computer.ino  ← Arduino usage example
```

### Key Constants

```cpp
static constexpr float WATER_VAPOR    = 0.0627f;    // WV pressure
static constexpr float FiO2_AIR       = 0.2095f;    // air FiO2
static constexpr float FiN2_AIR       = 0.7902f;    // air FiN2
static constexpr float SEAWATER_DENSITY = 1020.0f;  // kg/m³ (EN13319)
static constexpr float METERS_PER_ATM = ATM_PRESSURE_PA / (SEAWATER_DENSITY * GRAVITY);
// = 101325 / (1020 * 9.81) = 10.128 m/atm
```

**WV = 0.0627** — matches libbuhlmann and LSP.  
**Seawater density 1020 kg/m³** — EN13319 standard. Many engines use 1025 or 1030 (saltwater) or 1000 (freshwater). This is an important calibration point.

```
LSP D-Planner:    33 fsw/atm → 10.058 m/atm (freshwater-ish)
tl5915:           10.128 m/atm (EN13319 seawater)
Subsurface:       10.1325 m/atm (freshwater, standard atm)
```

### ZHL-16C Table (N2 only, 16 compartments — no compartment 1)

```cpp
// N2 half-times — starts from compartment 1b (5.0 min)
static const float kHT[16] = {
    5.0, 8.0, 12.5, 18.5, 27.0, 38.3, 54.3, 77.0,
    109.0, 146.0, 187.0, 239.0, 305.0, 390.0, 498.0, 635.0
};
static const float kA[16] = {
    1.1696, 1.0000, 0.8618, 0.7562, 0.6491, 0.5316, 0.4681, 0.4301,
    0.4049, 0.3719, 0.3447, 0.3176, 0.2828, 0.2716, 0.2523, 0.2327
};
static const float kB[16] = {
    0.5578, 0.6514, 0.7222, 0.7825, 0.8126, 0.8434, 0.8693, 0.8910,
    0.9092, 0.9222, 0.9319, 0.9403, 0.9477, 0.9544, 0.9602, 0.9653
};
```

**Omits compartment 1 (4.0 min half-time)** — uses 16 compartments starting from 1b (5.0 min). This is a common simplification for N2-only models; compartment 1 (4 min) has minimal impact on typical recreational/tech plans.

### Alveolar PPN2 (OC and CCR)

```cpp
// OC mode
p = (ambientAtm - WATER_VAPOR) * (1.0f - FiO2);

// CCR mode
p = ambientAtm - po2Setpoint - WATER_VAPOR;
```

**OC formula**: `pN2_alv = (P_amb - 0.0627) * FiN2`  
**CCR formula**: `pN2_alv = P_amb - PPO2_setpoint - 0.0627`

The CCR formula is correct: on a rebreather, the diver breathes at constant PPO2, so N2 loading = ambient - O2 partial pressure - WV.

**This is exactly what LSP D-Planner needs to implement CCR support.** The formula is simple and verified here.

### Tissue Update

```cpp
static void tickTissuesAmbient(float n2[], float ambientAtm, float dtMin) {
    const float pAlv = ppN2AlvFromAmb(ambientAtm);
    for (int i = 0; i < 16; i++) {
        const float k = LN2 / kHT[i];
        n2[i] += (pAlv - n2[i]) * (1.0f - expf(-k * dtMin));
    }
}
```

Standard Haldane constant-depth update. Time in **minutes** (not seconds).

### Ceiling Formula

```cpp
// ceilDepth() — N2 only
float denom = gf / kB[i] + 1.0f - gf;
float c = (p - kA[i] * gf) / denom;
```

Identical to libbuhlmann's formula, just N2-only. Correct GF-modified M-value calculation.

### GF Interpolation

```cpp
// gfAt() — linear interpolation
float gf = gfHigh + (gfLow - gfHigh) * depth / dFirst;
```

Where `dFirst` = depth of first stop.  
At `depth = dFirst`: `gf = gfLow` ✓  
At `depth = 0`:     `gf = gfHigh` ✓

**This is correct** — the sign convention is right here, unlike libbuhlmann's version.

### Surface GF (novel feature)

```cpp
// surfaceGfPercent() — real-time M-value ratio
float denom = kA[i] + SURFACE_ATM / kB[i] - SURFACE_ATM;
float gf = (p - SURFACE_ATM) / denom;
```

Computes: `surfGF = max tissue load / M-value-at-surface × 100%`

This is reported in `DecoResult.surfGF` — useful for understanding how close you are to the limit. LSP D-Planner does not currently expose this.

### Deco Stop Simulation

```cpp
// decoCompute() — iterates 1-minute steps at each stop
while (ceilDepth(n2, gfNext) > dNext) {
    tickTissuesDepth(n2, dStop, 1.0f);
    stopMin++;
    totalMin++;
}
```

**1-minute stop increments**. Stops at 3 m intervals, last stop at 3 m (or 6 m if `setLastStop6m(true)`).

Ascent between stops uses midpoint approximation:
```cpp
static void simAscent(float n2[], float from, float to, uint16_t *totalMin) {
    const float avg = (from + to) * 0.5f;
    const float travelMin = (from - to) / ASCENT_RATE;
    tickTissuesDepth(n2, avg, travelMin);
}
```

This is a simplification — a linear ascent should ideally integrate the loading, but midpoint works well for short segments.

### `ripNtear` Mode

```cpp
void ripNtear(bool enabled) {
    gfEnabled = !enabled;  // true = disable GF = force 100% GF
}
```

When enabled, forces `gf = 1.0f` everywhere — removes all conservatism and shows pure Bühlmann M-value limit. Named with dark humor. Useful for testing and for understanding raw algorithm behavior.

### Arduino Usage Pattern

```cpp
// setup()
decoSetupOC(60, 85, 0.21f);  // GF 60/85, air
decoInit();

// loop() — runs every second (or as fast as sensor updates)
decoUpdate(pressureAtm, dtMin);     // update tissues
DecoResult r = decoCompute(pressureAtm);  // calculate stops

// r.inDeco, r.nextStopDepth, r.stopTime, r.timeToSurface, r.surfGF
```

Clean separation of `update` (tissue loading) and `compute` (deco calculation with scratch copy). This pattern is efficient for embedded systems.

---

## 3. ericmanning8/Modified-Buhlmann (UDive Watch — BME405)

### Overview

| Property | Value |
|---|---|
| Author | Eric Manning (BME 405, academic project) |
|  Language | C++ |
| Stars | 5 |
| Last updated | 2026-05-14 |
| Algorithm | ZHL-16 (modified — N2 only) |
| Novel feature | **Heart rate / exertion modifier** |
| Gas support | OC, single gas |
| GF support | Yes — GF Lo/Hi |
| Units | Mixed (bar, feet) |
| Status | Academic prototype — hardcoded deco table fallback |

### Architecture

```
Team_3_UDive/
├── tissue.h / tissue.cpp  ← TISSUE class (a, b, k, load)
├── zhl16.h / zhl16.cpp    ← ZHL16 engine
├── gas.h / gas.cpp        ← GAS class (O2/He/N2 fractions, adjusted PP)
└── data.h / data.cpp      ← Data class (pressure, depth, time, heart rate readings)
```

### ZHL-16 Constants (note: uses different a-values)

```cpp
// tissues[] initialized in ZHL16 constructor — ZHL-16 B values (not C)
tissues[0] = new TISSUE(1.1696, 0.5578, 0.00231049, ppN2_surf);  // cpt 1b
tissues[1] = new TISSUE(1.0,    0.6514, 0.00144405, ppN2_surf);  // cpt 2
tissues[2] = new TISSUE(0.8618, 0.7222, 0.00092419, ppN2_surf);  // cpt 3
tissues[3] = new TISSUE(0.7562, 0.7825, 0.00062445, ppN2_surf);  // cpt 4
tissues[4] = new TISSUE(0.62,   0.8126, 0.00042786, ppN2_surf);  // cpt 5 ← a=0.62 (not 0.6491)
tissues[5] = new TISSUE(0.5043, 0.8434, 0.00030163, ppN2_surf);  // cpt 6 ← a=0.5043 (not 0.5316)
...
```

**Several a-values differ from canonical ZHL-16C** (e.g. cpt 5: 0.62 vs 0.6491, cpt 6: 0.5043 vs 0.5316). These may be ZHL-16 B values or transcription errors.

**k-values** are stored directly as `ln2 / halfTime_seconds`:
```
k[0] = 0.00231049 = ln2 / (5.0 * 60) = 0.693147 / 300  ✓
k[1] = 0.00144405 = ln2 / (8.0 * 60)                    ✓
```
Time updates run in **seconds** (unlike tl5915 which uses minutes).

### Schreiner Rate-of-Change Tissue Update

```cpp
// zhl16_update_tissue_loads() — uses full Schreiner equation
double r = (P_current - P_previous) / delta;  // pressure rate of change
tissues[i]->load = pressure + r * (time - 1/k) 
                   - (pressure - prevLoad - r/k) * exp(-k * time);
```

This is the **Schreiner equation** for linear pressure changes (ascent/descent). More accurate than constant-depth Haldane for ramped segments. LSP D-Planner uses the Haldane constant-pressure form; this is a potential accuracy improvement for fast descents/ascents.

Formula:
```
P(t) = P_i + R*(t - 1/k) - (P_i - P_0 - R/k) * e^(-k*t)
```
Where `R` = rate of change in ambient pressure, `P_i` = initial alveolar PP, `P_0` = initial tissue load.

### Heart Rate / Exertion Modifier (novel)

```cpp
// gas.cpp: gas_get_adjusted_partial_pressure()
// updateN2() modifies gas FiN2 based on VO2 and diver weight
void GAS::updateN2(double VO2, double weight, double time) {
    // VO2 max consumption modifies effective FiN2
    // Models increased N2 uptake under physical exertion
}
```

The idea: under high workload (elevated heart rate), more gas is consumed per unit time, increasing N2 uptake rate. This is physiologically motivated but **not validated** — it's an academic exploration for the UDive watch concept.

### Decompression Logic

The engine has two modes:
1. **Calculated**: `getDecompressionTime()` uses GF-corrected ceiling to determine if deco is needed
2. **Hardcoded fallback**: `calculateWaitTime()` is a depth/time lookup table (US Navy-style) for depths ≤ 60 ft only

The fallback is clearly incomplete (many depth ranges commented out) — this is academic prototype code.

### GF Implementation

```cpp
// Standard M-value tolerance
double zhl16_get_ptol(double ambient, double a, double b, double gf) {
    return ( a * gf + ((ambient * (gf - gf*b + b)) / b) );
}
```

Rearranged form of the standard formula. Equivalent to: `P_tol = (P_amb - a*gf) / (gf/b + 1 - gf)` but expressed differently. Same result.

---

## Cross-Library Comparison

### Constants

| Constant | libbuhlmann | tl5915 | ericmanning | LSP D-Planner | Subsurface |
|---|---|---|---|---|---|
| WV pressure (atm) | 0.0627 | 0.0627 | not explicit | 0.0627 | 0.0627 |
| Surface N2 fraction | 0.78 | 0.7902 (FiN2_AIR) | gas input | 0.7902 | 0.7902 |
| m/atm | 33 ft/atm (10.06) | 10.128 (EN13319) | bar | 33 ft/atm (10.06) | 10.1325 |
| Compartments | 17 (inc. 1) | 16 (from 1b) | 16 (from 1b) | 17 (inc. 1) | 17 |
| Helium | Yes | No | No | Yes | Yes |

### Algorithm Choices

| Feature | libbuhlmann | tl5915 | ericmanning | LSP |
|---|---|---|---|---|
| Tissue update | Haldane constant-P | Haldane constant-P | Schreiner rate | Haldane constant-P |
| GF slope sign | **Possibly inverted (bug)** | Correct | Correct | Correct |
| NDL calc | Not implemented | Not implemented | Partial | Implemented |
| Surface GF display | No | **Yes** | No | No |
| CCR support | No | **Yes** | No | Partial |
| TTS calculation | No | **Yes** | No | Yes |
| Stop interval | 10 ft | 3 m | lookup table | 3 m |
| Last stop depth | 10 ft | 3 m (or 6 m option) | N/A | 3 m |
| Gas switching (deco) | Yes (optimize by O2%) | No | No | Yes |

---

## Key Takeaways for LSP D-Planner

### 1. WV = 0.0627 is universally consistent
All three open-source C++ engines independently confirm `0.0627` as the standard WV pressure. LSP uses the same value. MultiDeco (from binary analysis) uses it as a configurable parameter but likely defaults to this value.

### 2. Surface GF is a useful display metric (tl5915)
```cpp
surfGF = max_over_compartments( (pN2 - P_surface) / (a + P_surface/b - P_surface) ) * 100
```
This shows how close the diver is to the raw M-value at surface pressure. Worth adding to LSP display — useful for understanding conservatism margin.

### 3. CCR formula is simple and verified
```cpp
// CCR: pN2_alv = P_amb - PPO2_setpoint - WV
pN2 = ambientAtm - po2Setpoint - WATER_VAPOR;
```
Confirmed across tl5915 and general diving physics. If LSP ever adds CCR, this is the formula.

### 4. Schreiner equation for ascent segments (ericmanning)
```cpp
P(t) = P_i + R*(t - 1/k) - (P_i - P_0 - R/k) * exp(-k*t)
```
More accurate than constant-depth Haldane for the ascent/descent ramps. Current LSP Haldane is fine for step-by-step profiles, but Schreiner would improve accuracy for steep dive profiles with fast depth changes.

### 5. libbuhlmann GF slope is inverted — don't copy it
The `gradientFactor()` function in libbuhlmann likely returns the wrong GF at intermediate depths (returns GFHi at the deep first stop, GFLo approaching surface — backwards). This is the "known bug" the author warns about. tl5915 has the correct implementation.

### 6. Correct GF interpolation (tl5915 style — confirmed correct)
```cpp
gf(depth) = GFHi + (GFLo - GFHi) * (depth / depth_first_stop)
// At first stop (depth = dFirst): gf = GFLo  ✓
// At surface (depth = 0):         gf = GFHi  ✓
```
LSP D-Planner should verify it uses this convention.

### 7. EN13319 seawater density
tl5915 uses `1020 kg/m³` → `10.128 m/atm`. LSP uses 33 ft/atm = 10.058 m/atm. The difference is ~0.7% — small but worth knowing when comparing TTS values with tl5915-based hardware.

---

## File References

| Repo | File | Key content |
|---|---|---|
| guyfleeman/libbuhlmann | `include/model/BuhlmannConstatnts.hpp` | ZHL-16A/B/C tables verbatim |
| guyfleeman/libbuhlmann | `src/model/BuhlmannModel.cpp` | Haldane update, GF slope, deco schedule |
| guyfleeman/libbuhlmann | `src/model/BuhlmannCompartment.cpp` | Ceiling formula |
| tl5915/Buehlmann-ZHL-16C | `src/ZHL16C.cpp` | Full engine in ~300 lines, CCR, surface GF |
| tl5915/Buehlmann-ZHL-16C | `src/ZHL16C.h` | Clean public API / `DecoResult` struct |
| ericmanning8/Modified-Buhlmann | `Team_3_UDive/zhl16.cpp` | Schreiner update equation |
| ericmanning8/Modified-Buhlmann | `Team_3_UDive/tissue.cpp` | Tissue class with k in 1/s |
