# Open-Source Deco Libraries — Batch 2

**Study date**: 2026-06-18  
**Purpose**: Analysis of six more open-source Bühlmann / ZHL-16 implementations for comparison with LSP D-Planner engine  
**Sources**:
- [AquaBSD/libbuhlmann](https://github.com/AquaBSD/libbuhlmann) — C library, ZHL-12/16A/B/C, both Haldane and Schreiner, trimix, most stars (48)
- [Jens-Horstmann/Buhlmann-ZHL-16](https://github.com/Jens-Horstmann/Buhlmann-ZHL-16) — Java dive computer simulator, Schreiner, GF, N2-only
- [LouiseMcMahon/Buhlmann-Decompression-Node](https://github.com/LouiseMcMahon/Buhlmann-Decompression-Node) — Node.js / JavaScript, Schreiner, trimix, clean modular design
- [dmaziuk/diy-zhl](https://github.com/dmaziuk/diy-zhl) — Python Jupyter notebooks, ZHL-12/16 + Workman + DSAT tables, educational focus, GF, M-value conversion utilities
- [jirkapok/GasPlanner](https://github.com/jirkapok/GasPlanner) — TypeScript Angular web app, most production-grade (58 stars), Subsurface-inspired GF, trimix, salinity, altitude, CCR/OTU
- [eianlei/pydplan](https://github.com/eianlei/pydplan) — Python/PyQt5 GUI dive planner (32 stars), ZHL-16A/B/C, Schreiner, trimix, multi-tank gas switching

---

## 1. AquaBSD/libbuhlmann (C Library)

### Overview

| Property | Value |
|---|---|
| Language | C (ANSI C, autoconf/automake) |
| Stars | 48 (highest in this batch) |
| Last updated | 2026-02-27 |
| Algorithm | ZHL-12, ZHL-16A, ZHL-16B, ZHL-16C |
| Gas | N2 + He (trimix) |
| GF | Yes |
| Units | Metric (bar) |
| Tests | Python test suite with real dive XML logs |

### Architecture — clean separation of concerns

Each algorithm is its own C file:

```
src/
├── buhlmann.h        ← all function declarations + constant tables
├── haldane.c         ← Haldane equation (constant depth)
├── schreiner.c       ← Schreiner equation (varying depth)
├── alveolar.c        ← ventilation / alveolar pAlv
├── compartment.c     ← stagnate (Haldane) + descend (Schreiner) + M-value
├── ceiling.c         ← ceiling pressure from N2/He compartment state
├── gradientfactor.c  ← GF slope + GF at depth
├── stop.c            ← NDL via binary search
├── zh-l12.c          ← ZHL-12 tables
├── zh-l16.c          ← ZHL-16A, ZHL-16B, ZHL-16C tables
├── otu.c             ← OTU oxygen toxicity unit calculation
└── dive.c            ← top-level dive simulation
```

**This is the most clearly structured C implementation in the batch.** Each concern is isolated, tested separately, and named clearly. Excellent reference for understanding what each step does.

### Constants

```c
#define WATER_VAPOR_PRESSURE 0.0627f
#define CO2_PRESSURE         0.0534f
#define SCHREINER_RQ         0.8f     // physiologically realistic
#define USNAVY_RQ            0.9f
#define BUHLMANN_RQ          1.0f     // simplest form
#define STOPINC              0.3f     // 3m stop intervals in bar
```

**Three RQ values are defined and named** — this is the only implementation that explicitly names the US Navy convention (`USNAVY_RQ = 0.9`). When `RQ = 1.0` (Bühlmann), the CO2 correction cancels out and alveolar PP = `(P_amb - WV) * fracGas`.

### Haldane vs Schreiner — both implemented

```c
// haldane.c — for constant depth (stagnation at a stop)
double haldane(double pt0, double palv0, double t, double half_val) {
    double k = M_LN2 / half_val;
    return pt0 + (palv0 - pt0) * (1.0 - exp(-k * t));
}

// schreiner.c — for changing depth (descent/ascent)
double schreiner(double pt0, double palv0, double r, double t, double half_val) {
    double k = M_LN2 / half_val;
    return palv0 + r * (t - 1.0/k) - (palv0 - pt0 - r/k) * exp(-k * t);
}
```

`compartment_stagnate()` uses Haldane (for stops).  
`compartment_descend()` uses Schreiner (for ascent/descent transitions) — `r` is the pressure rate of change in bar/min, scaled by inert gas fraction.

### Alveolar Pressure (ventilation function)

```c
// alveolar.c
double ventilation(double pamb, double rq, double ig_ratio) {
    return (pamb - WATER_VAPOR_PRESSURE + ((1 - rq) / rq) * CO2_PRESSURE) * ig_ratio;
}
```

When called with `BUHLMANN_RQ = 1.0`: `(pamb - 0.0627 + 0) * fracGas` — identical to LSP.  
When called with `SCHREINER_RQ = 0.8`: adds `(0.25 * 0.0534) * fracGas = 0.01335 * fracGas` extra.

### Ceiling Formula

```c
// ceiling.c — NOTE: this is the raw Bühlmann formula WITHOUT GF
// Returns absolute ceiling pressure (bar)
double getCeiling(const struct compartment_constants *constants, struct compartment_state *compt) {
    double PStopN2 = (compt->n2_p - constants->n2_a) * constants->n2_b;
    double PStopHe = (compt->he_p - constants->he_a) * constants->he_b;
    return (PStopN2 > PStopHe) ? PStopN2 : PStopHe;
}
```

**Critical note**: This ceiling uses `max(N2_ceiling, He_ceiling)` separately — NOT the combined pressure formula used by Subsurface/LSP/tl5915. This is a simpler but less correct approach when both gases are present. The correct combined formula is:
```
P = pN2 + pHe
a = (aN2*pN2 + aHe*pHe) / P
b = (bN2*pN2 + bHe*pHe) / P
ceiling = (P - a*gf) / (gf/b + 1 - gf)
```
The AquaBSD ceiling picks the worse of N2 or He independently — conservative but not the standard mixed-gas formula.

### Composite M-Value (in compartment.c — correct formula)

```c
// compartment_mvalue() — uses correct weighted composite
double a = ((n2_p * n2_a) + (he_p * he_a)) / (n2_p + he_p);
double b = ((n2_p * n2_b) + (he_p * he_b)) / (n2_p + he_p);
return ((n2_p + he_p) - a) * b;
```

Interestingly, `compartment_mvalue()` uses the correct combined formula, but `getCeiling()` does not. The mvalue function returns the M-value in absolute pressure (bar).

### Gradient Factor

```c
// gradientfactor.c
double gradient_factor_slope(double gfhi, double gflow, double final_stop_depth, double first_stop_depth) {
    return (gfhi - gflow) / (final_stop_depth - first_stop_depth);
}

double gradient_factor(double gfslope, double curr_stop_depth, double gfhi) {
    return (gfslope * curr_stop_depth) + gfhi;
}
```

**Same sign issue as guyfleeman/libbuhlmann** (prev batch) — `gf(depth) = slope * depth + gfHi`. At first stop (deepest): `gf = slope * dFirst + gfHi`. For this to equal `gfLo`, slope must be negative, which requires `final_stop_depth < first_stop_depth` (i.e. final = surface = 0, first = deepest stop). If called correctly with `final_stop = 0` and `first_stop = deepest`, slope is `(gfHi - gfLo) / (0 - dFirst) = -(gfHi - gfLo) / dFirst` (negative), and `gf(dFirst) = -(gfHi - gfLo)/dFirst * dFirst + gfHi = gfLo`. So **this is actually correct if the caller passes arguments in the right order** (final=surface, first=deepest stop). The naming is confusing — `final_stop_depth` means the last/shallowest stop (surface side).

### NDL by Binary Search

```c
// stop.c — binary search for no-deco time
// Starts at 100 min, repeatedly halves or 1.5x based on whether ceiling > 1.0 bar
double nodecotime(...) {
    double Addtime = 100;
    while (iter < 100 && Addtime < 101 && (ceiling < 0.99 || ceiling > 1.1)) {
        if (ceiling > 1.1) Addtime = Addtime * 0.5;
        else               Addtime = Addtime * 1.5;
    }
    return Addtime;
}
```

Bisection approach — converges to when ceiling = 1.0 bar (surface). Functional but imprecise (±10% band `0.99–1.10`).

### ZHL-16C Table

Full 17-compartment table in `zh-l16.c` — matches canonical values exactly, same as previous batch.

---

## 2. Jens-Horstmann/Buhlmann-ZHL-16 (Java — Dive Computer Sim)

### Overview

| Property | Value |
|---|---|
| Language | Java (Maven/IntelliJ) |
| Stars | 19 |
| Last updated | 2026-05-14 |
| Algorithm | ZHL-16 (N2 only, 16 compartments from 1b) |
| Gas | OC single gas + trimix fractions in Gas class |
| GF | Yes — with `lowDepth` tracking |
| Units | Bar (metric) |
| Notable | Schreiner everywhere; real-time stop calculator with recursion |

### Key Design: `GradientFactors.getGF(depthInBar)`

```java
// GradientFactors.java
public double getGF(double depthInBar) {
    return high - ((high - low) / (lowDepth - highDepth) * (depthInBar - highDepth));
}
```

Where `highDepth` = surface pressure (1 bar), `lowDepth` = deepest first stop depth.  
At surface (`depthInBar = highDepth = 1`): `gf = high - 0 = gfHigh` ✓  
At first stop (`depthInBar = lowDepth`): `gf = high - (high-low) = gfLow` ✓  

**This is correct and expressed in pressure (bar), not depth (m)**. Works cleanly with bar-based arithmetic.

### Schreiner Used Everywhere — Including Stops

```java
// ZHL16.java — setTissueLoadsSchreiner()
// R=0 for constant depth → reduces to Haldane automatically
tissues[i].setLoad(pAlv + R*(time - 1/k) - (pAlv - pTissue0 - R/k) * Math.exp(-k * time));
```

With `R=0` (constant depth stop): `load = pAlv - (pAlv - pTissue0) * exp(-k*t)` = Haldane.  
**Using Schreiner with R=0 as a unified equation is a clean architectural choice** — one function handles both descents and stops.

### GF Low Depth Tracking

```java
// ZHL16.java — getDeepestStop()
// Tracks the lowest ceiling seen so far and uses it as GFLo reference depth
if (deepStop > diveSettings.getGf().getLowDepth()) {
    diveSettings.getGf().setLowDepth(deepStop);
}
```

GFLo depth is set to the deepest ceiling ever reached — not just the deepest current ceiling. This prevents the GF slope from "resetting" if you ascend and then go back down (repetitive dives, or during deco if ceiling rises). **This matches Subsurface behavior.**

### Deco Stop Algorithm — Recursive

```java
// calcSafetyStops() — recursive through stops array (40 entries, one per 3m stop)
// For each stop, calculates hold time until ceiling clears to next stop
// Uses Haldane inverse: haldaneTime() to find exact time needed
double ndli = haldaneTime(k, pTol, pTissue0, pAlv);
// haldaneTime: t = -(1/k) * ln((pTol - pAlv) / (pTissue0 - pAlv))
```

Rather than iterating in 1-minute chunks, it computes the **exact time** needed using the Haldane inverse. This is more mathematically elegant (and more accurate) than the step-simulation approach used by most other implementations.

### Alveolar PP (simple, no WV constant named)

```java
private double getPalvN2(double depthInBar) {
    return gas.getN2Amount() * (depthInBar - diveSettings.getPw());
}
```

`Pw` is the water vapour pressure from `DiveSettings` — value set by the caller. Implicitly 0.0627 bar.

---

## 3. LouiseMcMahon/Buhlmann-Decompression-Node (JavaScript/Node.js)

### Overview

| Property | Value |
|---|---|
| Language | JavaScript (Node.js, ES6) |
|Stars | 2 |
| Last updated | 2026-06-07 |
| Algorithm | ZHL-16 (16 compartments, no cpt 1 / 4min) |
| Gas | N2 + He (trimix supported) |
| GF | Yes — passed per call |
| Units | Metric (bar implied) |
| Tests | Mocha unit tests, GitHub Actions CI |

### ZHL-16C Table — Notable Differences

```js
// static-data.js — N2 a-values (compartments 1–16, starting from 1b)
nitrogenCoefficientA: [
    1.2599, 1.0000, 0.8618, 0.7562, 0.6200, 0.5043, 0.4410, 0.4000,
    0.3750, 0.3500, 0.3295, 0.3065, 0.2835, 0.2610, 0.2480, 0.2327,
],
nitrogenCoefficientB: [
    0.5050, ...  // ← cpt 1b b-value is 0.5050, not 0.5578
],
```

**Two anomalies vs canonical ZHL-16C:**
1. Compartment 1b N2 b-value: `0.5050` instead of `0.5578` — this is a significant difference in the fastest tissue
2. N2 a-values for cpts 5–15 match the pattern seen in ericmanning/Jens-Horstmann (the "C" variant with lower a-values) — same as what pydplan calls "ZHL16c"

The source comment credits `decotengu` — this appears to be the decotengu library's interpretation of ZHL-16C, which uses a slightly different table than the Bühlmann book value at compartment 1b.

### Schreiner Implementation in JavaScript

```js
// compartments.js
schreinerEquation: function(inertGasFraction, currentDepth, targetDepth, duration, gasHalfLife, gasCurrentPressure) {
    const p_alv = inertGasFraction * ((currentDepth + 10) / 10 - this.waterVapourPressure);
    const k = Math.log(2) / gasHalfLife;
    const r = inertGasFraction * ((targetDepth - currentDepth) / 10) / duration;
    return p_alv + r * (duration - 1/k) - (p_alv - gasCurrentPressure - r/k) * Math.exp(-k * duration);
}
```

Uses `(depth + 10) / 10` for depth-to-bar conversion (10 m/bar freshwater). WV subtracted from alveolar pressure.

**Bug alert**: When computing pAlv, `this.waterVapourPressure` (0.0627 bar) is subtracted from `(depth+10)/10` which is already in bar — this is correct. But the rate `r` does not subtract WV from the depth-to-bar conversion. This means the rate of change in N2 alveolar pressure is slightly overestimated during descents. A minor but real inaccuracy.

### Ceiling Formula (Bühlmann with GF)

```js
// compartments.js
buhlmannEquation: function(gradientFactor) {
    const P = this.nitrogenPressure + this.heliumPressure;
    const A = (n2A * n2P + heA * heP) / P;
    const B = (n2B * n2P + heB * heP) / P;
    return (P - A * gradientFactor) / (gradientFactor / B + 1 - gradientFactor);
}
```

Correct composite GF-modified ceiling formula. GF passed as a parameter (0.0–1.0).

---

## 4. dmaziuk/diy-zhl (Python — Educational Jupyter Notebooks)

### Overview

| Property | Value |
|---|---|
| Language | Python (Jupyter notebooks) |
| Stars | 16 |
| Last updated | 2026-06-08 |
| Algorithm | ZHL-12, ZHL-16 (A/B/C), Workman, DSAT |
| Gas | N2 + He |
| GF | Yes |
| Purpose | Learning / visualization — not a planner app |
| Notable | Only repo with ZHL-12 + Workman + DSAT tables, M-value conversion utilities |

### Multiple Algorithm Tables

This is the only repo that includes:
- **ZHL-12** — original Bühlmann 1983 publication model (precedes ZHL-16)
- **Workman M-values** — US Navy model (M0 + delta-M per foot)
- **DSAT** — PADI recreational model (NDL-focused, no delta-M)
- **ZHL-16 A/B/C** — full version comparison in one file

The ZHL-16 table encodes all three `a`-value variants per compartment:

```python
ZHL16N = {
    5: {"t": 27.0, "b": 0.8126, "a": {"A": 0.6667, "B": 0.6667, "C": 0.62}},
    6: {"t": 38.3, "b": 0.8434, "a": {"A": 0.5933, "B": 0.56,   "C": 0.5043}},
    7: {"t": 54.3, "b": 0.8693, "a": {"A": 0.5282, "B": 0.4947, "C": 0.441}},
    ...
}
```

**This is the authoritative cross-reference for A vs B vs C differences.** The b-values are identical across versions — only the a-values differ (A is most conservative, C is least).

### M-Value Conversion Utilities

```python
def m_w2b(M0=2.9624, dM=1.7928, P=1):
    """Workman to Bühlmann: returns (a, b)"""
    a = M0 - dM * P
    b = 1.0 / dM

def m_b2w(a=1.1696, b=0.5578, P=1):
    """Bühlmann to Workman: returns (M0, deltaM)"""
    M0 = a + P / b
    dM = 1.0 / b
```

Very useful for understanding the mathematical equivalence between Workman M-values and Bühlmann a/b coefficients. For cpt 1b: `M0 = 1.1696 + 1/0.5578 = 2.963 bar ≈ 29.6 msw` — matches Workman table.

### Schreiner with Explicit Variable Names (best pedagogical version)

```python
def schreiner(Pi=0.7451, Palv=0.7451, t=1, R=0, k=0.1386):
    x1 = R * (t - 1.0/k)
    x2 = Palv - Pi - R/k
    x3 = math.e ** (-k * t)
    return Palv + x1 - x2 * x3
```

Step-by-step breakdown with intermediate variables. Best version for teaching the Schreiner equation.

### RQ = 0.9 Used for Alveolar Pressure

```python
def palv(Pamb=1, Q=0.79, RQ=0.9):
    vw = Pamb - 0.0627 + (1.0 - RQ) / RQ * 0.0534
    return round(vw * Q, 4)
```

Defaults to `RQ=0.9` (US Navy / moderate exertion). With `RQ=0.9`, `(1-0.9)/0.9 * 0.0534 = 0.00593` — small CO2 correction. With `RQ=1.0` (Bühlmann pure): correction = 0.

### ZHL-16C a-Values Clarification (dmaziuk's comment)

> *"Note that 'B' is a misnomer as some implementations call it 'C', some call it 'B', and nobody can read German and/or drop a hundred bucks on Tauchmedizin to see what Herr Bühlmann actually said."*

This explains the widespread confusion in open-source code about which table is "C". The a-values that most code calls "ZHL-16C" (lower, less conservative) appear to match what dmaziuk labels as "C" based on multiple secondary sources.

---

## 5. jirkapok/GasPlanner (TypeScript — Production Web App)

### Overview

| Property | Value |
|---|---|
| Language | TypeScript (Angular, published npm library `scuba-physics`) |
| Stars | 58 (highest in this study) |
| Last updated | 2026-05-21 |
| Algorithm | ZHL-16C (16 compartments, starting from 1b) |
| Gas | N2 + He trimix, multiple deco gases, gas switching |
| GF | Yes — Subsurface-inspired algorithm |
| Units | Metric + Imperial switchable |
| Features | CCR/OTU/CNS, altitude, salinity, air breaks, repetitive dives, best mix calc |
| Notable | Most feature-complete; GF implementation inspired by Subsurface source |

### Architecture

Production Angular app with a reusable TypeScript library (`scuba-physics`) published to npm. Well-tested, CI/CD on GitHub Actions.

```
projects/scuba-physics/src/lib/
├── algorithm/
│   ├── BuhlmannAlgorithm.ts       ← main entry: noDecoLimit(), decompression()
│   ├── Compartments.ts            ← ZHL-16C constants
│   ├── Tissues.ts                 ← Schreiner tissue update + ceiling
│   ├── GradientFactors.ts         ← Subsurface GF algorithm
│   └── Options.ts                 ← GF Lo/Hi, salinity, speeds, OTU limits
├── physics/
│   ├── depth-converter.ts         ← salinity-aware depth↔bar conversion
│   └── pressure-converter.ts      ← altitude pressure calculation
├── gases/
│   ├── Gases.ts                   ← Gas, Gases classes
│   └── GasMixtures.ts             ← ppO2, END, EAD, best mix
└── calculators/
    ├── OtuCalculator.ts           ← OTU oxygen toxicity
    ├── cnsCalculator.ts           ← CNS%
    └── altitudeCalculator.ts      ← altitude dive planning
```

### ZHL-16C Table — Uses "ZHL-16C" Lower a-Values

```typescript
// Compartments.ts — comment: "Verified by Subsurface, wiki, nigelhewitt photo"
// 16 compartments starting from 1b (5.0 min half-time)
public static readonly buhlmannZHL16C: Compartment[] = [
    new Compartment(5.0, 1.1696, 0.5578, 1.88, 1.6189, 0.4770),
    new Compartment(8.0, 1.0000, 0.6514, 3.02, 1.3830, 0.5747),
    new Compartment(12.5, 0.8618, 0.7222, 4.72, 1.1919, 0.6527),
    new Compartment(18.5, 0.7562, 0.7826, 6.99, 1.0458, 0.7223),  // note: b=0.7826 not 0.7825
    new Compartment(27.0, 0.62, 0.8125, 10.21, 0.9220, 0.7582),    // a=0.62 (ZHL-16C lower value)
    new Compartment(38.3, 0.5043, 0.8434, 14.48, 0.8205, 0.7957),
    new Compartment(54.3, 0.441, 0.8693, 20.53, 0.7305, 0.8279),
    new Compartment(77.0, 0.4, 0.8910, 29.11, 0.6502, 0.8553),
    ...
];
```

Uses the same "ZHL-16C" lower a-values as ericmanning/Jens-Horstmann/pydplan. This variant is what most modern open-source tools call "C" — less conservative a-values than the ZHL-16B table.

Note: cpt 4 b-value is `0.7826` (GasPlanner) vs `0.7825` (most others) — floating point rounding difference, negligible.

### Schreiner Equation (time in seconds)

```typescript
// Tissues.ts — time in seconds, halfTime in minutes
private schreinerEquation(pBegin, pGas, time, halfTime, gasRate): number {
    const LOG2_60 = 1.155245301e-02; // Math.log(2) / 60 — converts min→sec
    const timeConstant = LOG2_60 / halfTime;
    const exp = Math.exp(-timeConstant * time);
    return pGas + (gasRate * (time - 1.0/timeConstant)) - ((pGas - pBegin - gasRate/timeConstant) * exp);
}
```

`LOG2_60 = ln(2)/60` precomputed constant. `time` is in seconds, `halfTime` in minutes. Uses `gasRate` (bar/sec × gas fraction) as the pressure rate. Handles both ascent/descent and constant depth (when `speed=0`, `gasRate=0` → Haldane).

WV constant in `Tissues.ts`:
```typescript
private static pressureInLungs(ambientPressure: number): number {
    const waterVapourPressure = 0.0627;  // 37°C body temperature
    return ambientPressure - waterVapourPressure;
}
```

### Subsurface-Inspired GF Algorithm

```typescript
// GradientFactors.ts — comment: "inspired by SubSurface"
// NOTE: This file is under GPL v2.0 because of the Subsurface derivation

private toleratedTissues(surface, lowestCeiling, gfHigh, gfLow): number {
    // Finds the GF-interpolated ceiling across all compartments simultaneously
    // Uses algebraic form: solves for depth where tissue ceiling matches GF line
    const currentTolerated =
        (-a * b * (gfHigh * lowestCeiling - gfLow * surface) -
         (1.0 - b) * (gfHigh - gfLow) * lowestCeiling * surface +
         b * (lowestCeiling - surface) * pTotal) /
        (-a * b * (gfHigh - gfLow) +
         (1.0 - b) * (gfLow * lowestCeiling - gfHigh * surface) +
         b * (lowestCeiling - surface));
}
```

This is the Subsurface-derived closed-form solution that finds the exact GF-interpolated pressure for each compartment without iterative search. It tracks `lowestCeiling` (maximum ceiling ever seen) as the reference depth for GFLo — same as Jens-Horstmann's approach. **GPL v2.0** applies to this file.

### Options/Defaults (production-calibrated)

```typescript
// Options.ts — OptionDefaults
gfLow:  0.40   // default GF Low 40
gfHigh: 0.85   // default GF High 85
ascentSpeed6m:        3   // m/min — slow final ascent
ascentSpeed50percTo6m: 3  // m/min
ascentSpeed50perc:    9   // m/min — standard
descentSpeed:        18   // m/min
lastStopDepth:        3   // m
decoStopDistance:     3   // m
maxPpO2:           1.4    // bar
maxDecoPpO2:       1.6    // bar
```

The **3-speed ascent profile** (9 → 3 → 3 m/min) is notable — slows significantly above 50% depth and again in the last 6m. This mirrors GUE/DIR protocols. LSP currently uses a single ascent rate.

### Salinity Support

```typescript
// depth-converter.ts — DepthConverterFactory
// Salinity.salt = 1.025 kg/L → 10.1 m/bar
// Salinity.fresh = 1.0 kg/L → 10.33 m/bar
// Salinity.brackish = 1.015 kg/L (approx)
```

The `DepthConverterFactory` creates the appropriate converter based on the `Salinity` option. This propagates through all depth↔pressure calculations. LSP hardcodes 33 ft/atm = 10.06 m/atm (between fresh and salt).

---

## 6. eianlei/pydplan (Python/PyQt5 GUI Planner)

### Overview

| Property | Value |
|---|---|
| Language | Python 3 + PyQt5 GUI |
| Stars | 32 |
| Last updated | 2026-05-14 |
| Algorithm | ZHL-16A, ZHL-16B, ZHL-16C (user selectable) |
| Gas | N2 + He trimix, multi-tank (travel/bottom/deco1/deco2) |
| GF | Yes — slope-based with correct sign |
| Units | Metric (bar) |
| Notable | Multi-tank gas switching, dive phase state machine, full A/B/C table comparison |

### WV and Surface Pressure

```python
# Constants class — pydplan_buhlmann.py
surfacePressure = 1.01325  # bar — standard atmosphere (not 1.0)
WaterVaporSurface = 0.0627 # bar — decotengu value
initN2 = 0.745             # initial N2 tissue loading (bar)
```

Surface pressure is `1.01325` bar (standard atmosphere), not `1.0`. This means at `depth=0`, tissues are initialized to `0.745` bar N2, not `0.7902 * (1.0 - 0.0627) = 0.7397`. Using `1.01325` gives `0.7808 * (1.01325 - 0.0627) = 0.7424` — closer to `0.745`.

### ZHL-16 A/B/C All Three Variants (user-selectable)

```python
# Buhlmann class defines all three model variants
# ZHL16c uses lower a-values (same as GasPlanner/ericmanning)
# Notable: pydplan ZHL16c cpt 5 a = 0.6200 (not 0.6491 from canonical AquaBSD)
```

At runtime, the user picks "ZHL16a", "ZHL16b", or "ZHL16c" from a UI dropdown, and the algorithm uses the appropriate table. Good model for implementing table-switching in LSP.

### Gradient Factor — Correct Slope Direction

```python
# pydplan_profiletools.py — gradientFactor class
def gfSet(self, depthNow):
    # Called once at first deco stop to establish slope
    self.gfSlope = (self.GFhigh - self.GFlow) / depthNow
    self.gfCurrent = self.GFlow
    return self.GFlow

def gfGet(self, depthNow):
    # Returns current GF at given depth
    self.gfCurrent = self.GFhigh - (self.gfSlope * depthNow)
    return self.gfCurrent
```

At first stop (`depthNow = dFirst`): `gf = GFhigh - slope * dFirst = GFhigh - (GFhigh-GFlow)/dFirst * dFirst = GFlow` ✓  
At surface (`depthNow = 0`): `gf = GFhigh - 0 = GFhigh` ✓  

**This is correct** — same convention as tl5915 (batch 1). The slope is set only once at the first deco stop and reused.

### Multi-Tank Gas Switching State Machine

```python
# DivePhase enum
class DivePhase(Enum):
    INIT_TANKS, STARTING, DESCENDING, BOTTOM, ASCENDING,
    STOP_DECO, DECOEND, SURFACE,
    DESC_T, ASC_T, STOP_DESC_T, STOP_ASC_T, ERROR, NULL

# tanksCheck() — called every step, handles:
# - Travel gas → Bottom gas transition at specified depth
# - Bottom gas → Deco gas 1 transition
# - Deco gas 1 → Deco gas 2 transition
```

Supports up to 4 tanks: TRAVEL, BOTTOM, DECO1, DECO2. Each tank has a `changeDepth` and `useFromTime`. The state machine advances phases and switches gases at the correct depths automatically. **This is the most complete gas switching logic in this study — good reference for multi-gas LSP features.**

---

## Cross-Batch Comparison Table

### Key Identifiers

| Repo | Language | Stars | WV | RQ | Schreiner | GF | He/Trimix | CCR | Altitude | Salinity |
|---|---|---|---|---|---|---|---|---|---|---|
| AquaBSD/libbuhlmann | C | 48 | 0.0627 | 0.8/0.9/1.0 | Yes | Yes | Yes | — | — | — |
| Jens-Horstmann | Java | 19 | 0.0627 | 1.0 | Yes (unified) | Yes | Yes (Gas class) | — | — | — |
| LouiseMcMahon | JS/Node | 2 | 0.0627 | 1.0 | Yes | Yes | Yes | — | — | — |
| dmaziuk/diy-zhl | Python | 16 | 0.0627 | 0.9 (default) | Yes | Yes | Partial | — | — | — |
| jirkapok/GasPlanner | TypeScript | 58 | 0.0627 | 1.0 | Yes | Yes (GPL) | Yes | Yes | Yes | Yes |
| eianlei/pydplan | Python | 32 | 0.0627 | 1.0 | Implied | Yes | Yes | — | — | — |

### ZHL-16C a-Value Variants (cpt 5 / 27 min, as discriminator)

| Repo | Cpt 5 N2 a | Variant |
|---|---|---|
| AquaBSD/libbuhlmann | 0.6491 | Canonical "C" per Bühlmann book |
| guyfleeman/libbuhlmann (batch 1) | 0.6491 | Canonical "C" |
| tl5915 (batch 1) | 0.6491 | Canonical "C" |
| GasPlanner (jirkapok) | 0.6200 | "C" per decotengu/Subsurface |
| ericmanning8 (batch 1) | 0.6200 | Same |
| Jens-Horstmann | 0.6200 | Same |
| LouiseMcMahon | 0.6200 | Same (sourced from decotengu) |
| pydplan (eianlei) | 0.6200 | Same |
| dmaziuk/diy-zhl | Explicit A/B/C | Shows all three: A=0.6667, B=0.6667, C=0.62 |
| LSP D-Planner | ? | **Needs verification** |

**Critical finding**: Two different sets of values are both called "ZHL-16C" in open-source code:
1. **"Canonical C"** (a5=0.6491): matches AquaBSD, guyfleeman, tl5915, and Bühlmann's book directly. Used by MultiDeco binary (confirmed in batch 1 APK analysis).
2. **"Decotengu/Subsurface C"** (a5=0.6200): used by GasPlanner, ericmanning, Jens-Horstmann, LouiseMcMahon, pydplan. This matches Subsurface's implementation and is what these apps ship with.

**dmaziuk labels these clearly**: `"A"` and `"B"` use `a5=0.6667`, `"C"` uses `a5=0.6200`. So the "C" variant has the lowest (least conservative) a-values for compartments 5–15. LSP D-Planner should explicitly declare which variant it uses and verify against the table.

---

## Key Takeaways for LSP D-Planner

### 1. Schreiner is the de-facto standard for ascent segments
Every production-quality repo (AquaBSD, Jens-Horstmann, LouiseMcMahon, GasPlanner, pydplan) uses Schreiner for ascent/descent and Haldane (or Schreiner with R=0) for stops. LSP uses Haldane for all segments — acceptable but slightly less accurate for fast descents.

### 2. Verify which ZHL-16C table LSP uses
There are two distinct ZHL-16C a-value sets. The "Subsurface/decotengu" variant (a5=0.6200) is what most modern open-source apps ship. The canonical Bühlmann book values (a5=0.6491) is used by MultiDeco (from binary analysis). Since LSP aims to match Subsurface, confirm LSP uses the same table as Subsurface.

### 3. Unified Schreiner with R=0 = Haldane (Jens-Horstmann trick)
Using Schreiner everywhere with `R=0` for constant-depth steps eliminates the need for two separate update functions. Simplifies code without any accuracy trade-off.

### 4. GasPlanner's 3-speed ascent profile
Three ascent speeds (9 → 3 → 3 m/min) is worth considering for LSP. The current single-speed ascent is simpler but adds conservatism unevenly. A 3-speed profile matches DIR/GUE recommendations.

### 5. pydplan gas switching state machine
The `DivePhase` enum + `tanksCheck()` pattern for multi-tank switching is clean and complete. Reference this when implementing TRAVEL + BOTTOM + DECO1 + DECO2 gas switching in LSP.

### 6. GasPlanner GF algorithm is GPL v2.0
The `GradientFactors.ts` file is explicitly marked as derived from Subsurface and under GPL v2.0. Do not copy it directly into LSP without checking license compatibility. The math can be re-derived independently.

### 7. dmaziuk provides the best ZHL-16 historical/variant reference
For understanding the history of A/B/C variants, Workman vs Bühlmann M-value equivalence, and DSAT model, `diyzhl.py` and its notebooks are the best single-file reference. Especially useful for understanding where the "C" a-value confusion originates.

### 8. Surface pressure = 1.01325 vs 1.0
pydplan uses the true standard atmosphere (1.01325 bar). Most others use 1.0 bar. This 0.13% difference compounds across long dives. LSP should document its choice explicitly.

### 9. OTU/CNS tracking (GasPlanner)
GasPlanner has full OTU and CNS% calculators (`OtuCalculator.ts`, `cnsCalculator.ts`). These are missing from LSP's current implementation and are safety-critical for high-O2 deco gas use.

---

## File References

| Repo | File | Key content |
|---|---|---|
| AquaBSD/libbuhlmann | `src/buhlmann.h` | All function declarations, RQ constants (0.8/0.9/1.0) |
| AquaBSD/libbuhlmann | `src/schreiner.c` | Clean Schreiner in C |
| AquaBSD/libbuhlmann | `src/compartment.c` | `stagnate()` (Haldane) + `descend()` (Schreiner) + M-value |
| AquaBSD/libbuhlmann | `src/gradientfactor.c` | GF slope + GF at depth |
| AquaBSD/libbuhlmann | `src/zh-l16.c` | ZHL-16A/B/C tables |
| Jens-Horstmann | `ZHL16.java` | Schreiner unified, recursive stops, haldaneTime inverse, GF tracking |
| Jens-Horstmann | `GradientFactors.java` | GF in bar units — correct interpolation |
| LouiseMcMahon | `src/compartments.js` | Schreiner + ceiling in JS — good LSP reference (same language) |
| LouiseMcMahon | `src/static-data.js` | ZHL-16 table (decotengu variant) |
| dmaziuk/diy-zhl | `diyzhl.py` | ZHL-12/16/Workman/DSAT tables, M-value conversion, Schreiner in Python |
| jirkapok/GasPlanner | `algorithm/Tissues.ts` | Schreiner in seconds, WV=0.0627, ceiling formula |
| jirkapok/GasPlanner | `algorithm/GradientFactors.ts` | Subsurface GF (GPL v2.0) |
| jirkapok/GasPlanner | `algorithm/Options.ts` | Production defaults (speeds, GF, ppO2 limits) |
| eianlei/pydplan | `pydplan_buhlmann.py` | ZHL-16A/B/C all three variants, WV=0.0627 |
| eianlei/pydplan | `pydplan_profiletools.py` | GF class, multi-tank state machine |
