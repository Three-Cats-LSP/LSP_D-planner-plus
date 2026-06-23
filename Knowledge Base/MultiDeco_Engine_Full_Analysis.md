# MultiDeco Engine Full Analysis
## Complete ARM64 Binary Disassembly — libmultideco.so

**Date:** June 2026  
**Target:** `MultiDeco_226.apk` → `lib/arm64-v8a/libmultideco.so` (378 KB)  
**Method:** `aarch64-linux-gnu-objdump -d` + Python rodata extraction  
**Engine class:** `TVPM` (C++ class, all methods mangled `_ZN4TVPM...`)

---

## Table of Contents
1. [Library Structure](#1-library-structure)
2. [TVPM Class Layout](#2-tvpm-class-layout)
3. [Rodata Constants](#3-rodata-constants)
4. [Core Gas Equations](#4-core-gas-equations)
5. [Gas Loading Functions](#5-gas-loading-functions)
6. [Ceiling Calculation Functions](#6-ceiling-calculation-functions)
7. [GF and Stop Logic Functions](#7-gf-and-stop-logic-functions)
8. [VPM-B Core Functions](#8-vpm-b-core-functions)
9. [Decompression Stop Engine](#9-decompression-stop-engine)
10. [Repetitive Dive Logic](#10-repetitive-dive-logic)
11. [Utility Functions](#11-utility-functions)
12. [ZHL-16C Table Variant Identification](#12-zhl-16c-table-variant-identification)
13. [Global BSS Variables Map](#13-global-bss-variables-map)
14. [Algorithm Flow Summary](#14-algorithm-flow-summary)

---

## 1. Library Structure

```
ELF64 ARM64 (little-endian) shared library
Sections relevant to engine:
  .text      @ 0x000000  size ~350 KB  — all native code
  .rodata    @ 0x013810  size 0x460C   — all double constants, lookup tables
  .data      @ 0x065878  size 0x1D0    — small initialized data
  .bss       @ 0x065A50  size 0x2300   — zero-init globals (filled at runtime)

Key symbol (TVPM class):
  Amb_Press_Onset_of_Imperm  @ 0x61000 segment base (external global)
```

All 16-compartment loops use **ARM NEON SIMD** (2 doubles per iteration via 128-bit Q registers).

---

## 2. TVPM Class Layout

Important member offsets (confirmed from constructor and method usage):

| Offset | Type | Field Name (inferred) | Notes |
|--------|------|-----------------------|-------|
| +0     | …    | vtable ptr            | C++ vtable |
| +8     | double | Dive_Start_Pressure | Bar |
| +40    | bool  | CCR_mode              | 1=CCR |
| +42    | bool  | O2_mode               | 1=open circuit? |
| +48    | double | GF_Lo                | Default 1.0 (= 100%) |
| +56    | int   | Gas_Mix_Index         | Current gas mix index |
| +61    | bool  | VPM_mode              | 0=Buhlmann/GF, 1=VPM |
| +64    | double | VPM_Lambda_N2         | 102.0 (surface excursion factor) |
| +72    | double | VPM_Lambda_He         | 8.2  |
| +80    | double | Max_Ascent_Rate_frac  | |
| +88    | double | Gamma_c               | 0.257 (VPM-B surface tension ratio) |
| +96    | double | Gamma_s               | 0.0179 N/m |
| +104   | double | Time_at_Surface_min   | Used in NUCLEAR_REGENERATION |
| +120   | double | Regen_HalfTime        | Initialized to large value from rodata 0x13b70 |
| +140   | byte   | He_mode               | CCR He usage |
| +143   | byte   | CCR_flag_2            | |
| +161   | byte   | SCR_flag              | Semi-closed rebreather |
| +201   | byte   | Mixed_gas_flag        | |
| +202   | byte   | TMX_flag              | |
| +204   | int    | Stop_increment        | 0=Buhlmann/GF, nonzero=VPM-B |
| +208   | double | PPO2_setpoint         | CCR O2 partial pressure |
| +216   | int    | algo_variant          | Algorithm variant selector |
| +224   | double | GF_composite          | Computed GF value at current depth |

---

## 3. Rodata Constants

All doubles extracted from `.rodata @ 0x013810`.  
Address format: file offset = vaddr (base=0 for this .so).

### 3.1 Physical / Unit Conversion Constants

| vaddr    | Value      | Meaning |
|----------|------------|---------|
| `0x13810` | 0.279      | N2 fraction dry air |
| `0x13818` | 1.825      | ? (related to dry-gas O2 calc) |
| `0x13820` | 0.79       | N2 fraction in air (standard) |
| `0x13828` | 1.01325    | 1 atm in bar |
| `0x13830` | 0.01       | GF% → decimal (SetGradFactor multiplier) |
| `0x13838` | 0.3048     | ft → m conversion |
| `0x13840` | −0.01      | −0.01 (GF complement operations) |
| `0x13870` | 10.337     | freshwater: 10m/bar; actually 10.337 m/bar |
| `0x13878` | 0.499      | (WV pressure related: ~0.0627 bar?) |
| `0x13888` | 1.01       | ≈1.01 atm surface pressure default |
| `0x13938` | 288.15     | Sea-level temperature K (ICAO) |
| `0x13968` | 3280.839895 | Feet per kilometer |
| `0x13998` | 0.001      | Stop rounding threshold |
| `0x139a0` | −0.001     | Negative threshold |
| `0x139a8` | 10.078     | saltwater column: 10.078 m/bar (≈ 10.1 in some implementations) |
| `0x139b0` | 0.0001     | Fine tolerance |
| `0x13860` | 0.05       | 5% (5 min minimum stop?) |
| `0x13868` | 0.272727   | 3/11 = ratio used in stop extension |

### 3.2 GF / Algorithm Constants

| vaddr    | Value     | Meaning |
|----------|-----------|---------|
| `0x13858` | 0.55      | ShallowGrad pressure ratio threshold (>0.55 = shallow) |
| `0x13880` | 0.4       | VPM_REPETITIVE_ALGORITHM factor (δ = 0.4) |
| `0x139c8` | 0.45      | ShallowGrad GF blend factor |
| `0x139d0` | 0.8       | ShallowGrad GF upper clamp |
| `0x139d8` | 1.8       | ShallowGrad time trigger at 1.8 bar? |
| `0x138a0` | 1.331     | 1.1³ (depth-ratio cube) |
| `0x138e8` | 0.2       | 20% blend fraction |
| `0x13890` | 1×10⁻⁶   | Convergence tolerance |
| `0x138f0` | 1×10⁻¹²  | Fine convergence (RAD_ROOT_FINDER) |
| `0x138b0` | 28.3168   | ft³ → litres conversion (Boyle's law) |
| `0x138c8` | 33.066    | ??? |
| `0x138f8` | 33.914    | ??? |

### 3.3 VPM-B Surface Tension Constants (from TVPM constructor, stored at TVPM+88..+96)

| Value  | Symbol | Meaning |
|--------|--------|---------|
| 0.257  | Gamma_c/Gamma_s | Ratio of critical to surface tension (dimensionless) |
| 0.0179 | gamma_c | Surface tension at bubble wall (N/m = 17.9 dyn/cm) |
| 102.0  | Lambda_N2 | VPM-B surface excursion pressure N2 (bar units?) |
| 8.2    | Lambda_He | VPM-B surface excursion pressure He |
| 0.493  | r_N2_initial | Initial critical radius N2 (stored at TVPM+? via 0x13b80) |
| 0.567  | r_He_initial | Initial critical radius He (0x13b88) |

> Note: VPM-B standard critical radii = 0.8 μm N2, 0.5 μm He (Yount 1991).  
> MultiDeco uses 0.493 and 0.567 — different parameterization, likely adjusted values.

### 3.4 Half-Time Tables (k-values, computed as ln(2)/HalfTime)

**N2 rate constants @ `0x15c00`** (16 compartments):
```
[0]  k=0.36870  → HT=  1.88 min
[1]  k=0.22952  → HT=  3.02 min
[2]  k=0.14685  → HT=  4.72 min
[3]  k=0.09916  → HT=  6.99 min
[4]  k=0.06789  → HT= 10.21 min
[5]  k=0.04787  → HT= 14.48 min
[6]  k=0.03376  → HT= 20.53 min
[7]  k=0.02381  → HT= 29.11 min
[8]  k=0.01682  → HT= 41.2  min
[9]  k=0.01256  → HT= 55.19 min
[10] k=0.00981  → HT= 70.69 min
[11] k=0.00767  → HT= 90.34 min
[12] k=0.00601  → HT=115.3  min
[13] k=0.00470  → HT=147.4  min
[14] k=0.00368  → HT=188.2  min
[15] k=0.00289  → HT=240    min
```

**He rate constants @ `0x15c80`** (16 compartments):
```
[0]  HT=  5 min   [8]  HT=109 min
[1]  HT=  8 min   [9]  HT=146 min
[2]  HT= 12.5 min [10] HT=187 min
[3]  HT= 18.5 min [11] HT=239 min
[4]  HT= 27 min   [12] HT=305 min
[5]  HT= 38.3 min [13] HT=390 min
[6]  HT= 54.3 min [14] HT=498 min
[7]  HT= 77 min   [15] HT=635 min
```
→ These are **canonical ZHL-16C He halftimes** (Bühlmann 2002).

### 3.5 b-Value Lookup Table @ `0x161c0` (44 entries)

This is a stop-depth-indexed table of b-values from 0.48 to 4.5+, used in BOYLES_LAW_COMPENSATION and DECOMPRESS_STOP for stop-pressure snap:
```
0.48, 0.495, 0.51, 0.515, 0.52, 0.53, 0.54, 0.55, 0.56, 0.565,
0.57, 0.59, 0.60, 0.61, 0.62, 0.63, 0.64, 0.645, 0.65, 0.66,
0.68, 0.695, 0.71, 0.72, 0.74, 0.77, 0.78, 0.80, 0.83, 0.88,
0.93, 0.98, 1.04, 1.11, 1.19, 1.32, 1.47, 1.80, 2.22, 2.50,
3.00, 3.50, 4.00, 4.50
```
Table continues with half-time values: 5, 6, 8, 9, 10… (separate array follows at `0x16320`)

---

## 4. Core Gas Equations

### 4.1 HALDANE_EQUATION @ `0x35e04`

**Signature:** `double HALDANE(double pt0, double palv0, double k, double t)`

```c
// Exponential inert gas uptake/elimination
return pt0 + (palv0 - pt0) * (1.0 - exp(-k * t));
```

- `pt0` = initial tissue tension (bar)
- `palv0` = alveolar inert gas partial pressure (bar)
- `k` = rate constant = ln(2)/halfTime (min⁻¹)
- `t` = time (min)
- **Used for:** constant-depth exposures

### 4.2 SCHREINER_EQUATION @ `0x35dc4`

**Signature:** `double SCHREINER(double pt0, double palv0, double r, double k, double t)`

```c
// Linear pressure change with exponential uptake
return palv0 + r*(t - 1/k) - (palv0 - pt0 - r/k) * exp(-k*t);
```

- `r` = rate of change of alveolar pressure (bar/min) = rate × gas fraction
- `k` = ln(2)/halfTime
- **Used for:** ascent/descent segments

### 4.3 Set_Inspired_Inert_Press @ `0x35e38`

**Signature:** `void Set_Inspired_Inert_Press(double amb_bar, double time, double* pN2, double* pHe, double* out1, double* out2)`

**Large function** handling three breathing modes:

```
MODE 0 (OC = Open Circuit):
  fraction_N2 = current gas mix N2 fraction
  fraction_He = current gas mix He fraction
  pN2_alv = (amb_bar - WV) * fN2
  pHe_alv = (amb_bar - WV) * fHe

MODE 1 (CCR = Closed Circuit Rebreather):
  PPO2_set = TVPM.PPO2_setpoint  [at offset +208]
  pN2_alv = amb_bar - PPO2_set - WV_correction
  pHe_alv = amb_bar - PPO2_set - pN2_alv - WV
  // Verifies PPO2_set >= 0.16 (MOD check)

MODE 2 (SCR = Semi-Closed Rebreather):
  Uses injection ratio and O2 enriched mix
  More complex: accounts for O2 consumption rate
```

- `WV` = `Water_Vapor_Press` global (BSS, runtime variable — NOT hardcoded 0.0627)
- Function selects mode via `TVPM.SCR_flag` / `TVPM.CCR_mode` bits

---

## 5. Gas Loading Functions

### 5.1 GAS_LOADINGS_CONST_DEPTH @ `0x35370`

**Signature:** `void GAS_LOADINGS_CONST_DEPTH(double depth_bar, double time_min)`

```pseudocode
Set_Inspired_Inert_Press(depth_bar, time_min, &pN2, &pHe, ...)
for i in 0..15 (NEON: 2 at a time):
    pN2_tissue[i] = HALDANE(pN2_tissue[i], pN2, k_N2[i], time_min)
    pHe_tissue[i] = HALDANE(pHe_tissue[i], pHe, k_He[i], time_min)
```

- Processes all 16 compartments using NEON vectorized pairs
- k-values loaded from `.rodata` at `0x15c00` (N2) and `0x15c80` (He)

### 5.2 GAS_LOADINGS_ASCENT_DESCENT @ `0x32b9c`

**Signature:** `void GAS_LOADINGS_ASCENT_DESCENT(double start_bar, double end_bar, double time_min)`

```pseudocode
Set_Inspired_Inert_Press(start_bar, time_min, &pN2, &pHe, ...)
r_N2 = (end_bar - start_bar - WV_correction) * fN2 / time_min
r_He = (end_bar - start_bar - WV_correction) * fHe / time_min
for i in 0..15:
    pN2_tissue[i] = SCHREINER(pN2_tissue[i], pN2, r_N2, k_N2[i], time_min)
    pHe_tissue[i] = SCHREINER(pHe_tissue[i], pHe, r_He, k_He[i], time_min)
```

### 5.3 GAS_LOADINGS_SURFACE_INTERVAL @ `0x307a8`

**Signature:** `void GAS_LOADINGS_SURFACE_INTERVAL(double time_min)`

```pseudocode
// Surface = air breathing, fixed pN2 at surface
pN2_surface = (Baro_Press - WV) * 0.79  // from rodata 0x13820
for i in 0..15:
    pN2_tissue[i] = HALDANE(pN2_tissue[i], pN2_surface, k_N2[i], time_min)
    pHe_tissue[i] = HALDANE(pHe_tissue[i], 0.0, k_He[i], time_min)
    // He offgasses to zero (no He in air)
```

---

## 6. Ceiling Calculation Functions

### 6.1 CALC_DECO_CEILING @ `0x31ee0`

**Non-GF version.** Iterates all 16 compartments, takes maximum ceiling.

```c
double ceiling = 0.0;
for (int i = 0; i < 16; i++) {
    double P = pN2[i] + pHe[i];
    double a = (aN2[i]*pN2[i] + aHe[i]*pHe[i]) / P;  // composite a
    double b = (bN2[i]*pN2[i] + bHe[i]*pHe[i]) / P;  // composite b
    double ceil_i = (P - a) / (1/b) + Baro_Press;     // ZHL ceiling
    ceiling = max(ceiling, ceil_i);
}
// Returns ambient pressure at ceiling depth
```

### 6.2 CALC_DECO_CEILING_GF @ `0x31bf8`

**GF version, ARM NEON SIMD vectorized.**  
Processes 2 compartments per loop iteration using Q-registers.

```c
double ceiling = Baro_Press;  // minimum = surface
for (int i = 0; i < 16; i += 2) {  // NEON: i, i+1 simultaneously
    // Both compartments computed in parallel using 128-bit ops
    double P = pN2[i] + pHe[i];
    double a = (aN2[i]*pN2[i] + aHe[i]*pHe[i]) / P;
    double b_val = (bN2[i]*pN2[i] + bHe[i]*pHe[i]) / P;
    // GF formula:
    double ceil_i = (P - a*gf) / (gf/b_val + 1.0 - gf);
    ceiling = max(ceiling, ceil_i + WV);
}
```

- `gf` is the gradient factor (0.0–1.0) for this depth
- Uses globals: `Baro_Press`, `Water_Vapor_Press`
- Constant `0x400af17abcd00000` ≈ 3.4117 seen in NEON setup (2*(Pb-WV) pre-computation)

### 6.3 CALC_ASCENT_CEILING @ `0x31dc0`

Simplified ceiling for ascent-planning.  
Like CALC_DECO_CEILING but for projected ascent depths.

```c
// Same composite a/b formula, no GF applied
// Used by PROJECTED_ASCENT to find first-stop depth
```

### 6.4 CALC_START_OF_DECO_ZONE @ `0x318ec`

Uses **iterative bisection** (calls `exp()` in a loop) to find the depth where tissues first require a stop.

```pseudocode
lo = Baro_Press  // surface
hi = current_depth
while (hi - lo > tolerance):  // tolerance = 1e-6 bar
    mid = (lo + hi) / 2.0
    simulate_tissue_tensions_at(mid)  // calls exp() for each compartment
    if ceiling(mid) <= mid:
        hi = mid
    else:
        lo = mid
return hi  // first stop depth
```

---

## 7. GF and Stop Logic Functions

### 7.1 SetGradFactor @ `0x31608`

**Signature:** `void SetGradFactor(int gfLo_percent, int gfHi_percent)`

```c
// Convert integer percentage to decimal
gf_lo = gfLo_percent * 0.01;   // 0x13830 = 0.01
gf_hi = gfHi_percent * 0.01;
// Store to TVPM+224 (gf_lo) and TVPM+232 (gf_hi)
// Also computes: TVPM+240 = gf_composite (working GF at current depth)
```

### 7.2 CALC_MAX_ACTUAL_GRAD @ `0x3416c`

**Signature:** `double CALC_MAX_ACTUAL_GRAD(double current_pressure_bar)`

Finds the **maximum actual gradient** across all 16 compartments using **NEON SIMD**.

```c
// For each compartment i:
P_tissue = pN2[i] + pHe[i] + WV;
P_amb = current_pressure_bar + WV;
// composite a, b:
a = (aN2[i]*pN2[i] + aHe[i]*pHe[i]) / (pN2[i]+pHe[i])
// Actual gradient:
AG = max(0, P_tissue - P_amb) / (P_tissue - a)
// BIC (bic = bitwise AND NOT) used to zero negative values
max_actual_grad = max over all compartments
```

- Returns max gradient across compartments (0.0 = no supersaturation)

### 7.3 PROJECTED_ASCENT @ `0x320f8`

**Signature:** `void PROJECTED_ASCENT(double current_bar, double rate_bar_per_min, double target_bar, double* result_ceiling)`

Projects tissue loadings if ascending at given rate, finds ceiling at target depth.

```pseudocode
// Calls Set_Inspired_Inert_Press at each depth step
// Applies SCHREINER for ascent segment
// Returns ceiling pressure via result_ceiling pointer
// Large stack frame (0x350 bytes) — saves 16-compartment snapshot
for each ascent segment:
    SCHREINER_all_compartments(start, end, rate, time)
    ceiling = CALC_ASCENT_CEILING()
```

---

## 8. VPM-B Core Functions

### 8.1 CALC_INIT_ALLOW_GRAD @ `0x31844`

**Signature:** `void CALC_INIT_ALLOW_GRAD()`

Computes initial allowable gradient for each compartment based on current tissue tensions.  
This is the VPM-B "adjusted critical radii" calculation.

```c
for i in 0..15:
    // Using current pN2[i], pHe[i], and initial critical radii
    // Allowable gradient = 2 * gamma * (1/r_N2[i] + 1/r_He[i]) (simplified)
    AG_N2[i] = function_of(r_N2[i], pN2[i])
    AG_He[i] = function_of(r_He[i], pHe[i])
    TVPM.InitAllowGrad_N2[i] = AG_N2[i]
    TVPM.InitAllowGrad_He[i] = AG_He[i]
```

### 8.2 VPM_CALCULATE @ `0x29c18`

**Main VPM-B entry point.** Largest function in the library (>6 KB of code).  
ARM64 prologue saves 20 registers (x19..x28, d8..d15) + allocates 0x770 (1904 bytes) stack.

**Flow summary (decoded from ARM64):**

```pseudocode
VPM_CALCULATE(rdFGsn* profile_struct, double d1, double d2):

  // 1. Initialize
  profile->deco_stops.clear()
  VPM_mode_flag = profile->isVPM
  
  // 2. Set initial critical radii
  SET_CRITICAL_RADII(initial_pressure)

  // 3. Gas mix selection
  if (CCR_mode):
      load CCR gas tables (He/N2 with setpoint)
  else:
      load OC gas tables
  
  // 4. Execute dive profile
  for each segment in profile:
      if segment.type == CONST_DEPTH:
          GAS_LOADINGS_CONST_DEPTH(depth, time)
      else:
          GAS_LOADINGS_ASCENT_DESCENT(start, end, time)
  
  // 5. VPM-B crushing pressure analysis
  CALC_CRUSH_PRESS(P_surface, P_max, descent_time)
  
  // 6. Iterative decompression schedule
  current_depth = max_depth
  while current_depth > Baro_Press:
      // Find next stop
      ceiling = CALC_DECO_CEILING_GF(current_GF)
      stop_pressure = round_to_stop_increment(ceiling)
      
      // Check Boyle's law compensation
      BOYLES_LAW_COMPENSATION(stop_pressure, last_stop, ascent_rate)
      
      // Time at stop
      time = DECOMPRESS_STOP(stop_pressure, ascent_rate)
      
      // Record stop
      profile->stops.add(stop_pressure, time)
      current_depth = stop_pressure
  
  // 7. Critical volume iteration (VPM-B specific)
  CRIT_VOLUME(total_ascent_time)
  
  // 8. Shallow gradient logic
  if ShallowGradDepthTest() && ShallowGradTimeTest():
      apply_shallow_grad_reduction()
```

**Key observations:**
- At `0x29ccc`: loads two hardcoded doubles via `movk`:  
  `0x40bdc... = 7474 ≈ 7.474 bar` (shallow-grad 74.74 m trigger?)  
  `0x40b9... ≈ 6.4 bar` (64 m trigger)  
  Used in `fcsel d0, d1, d0, ne` — selects between two depth thresholds based on gas type
- At `0x29d70`: `fcsel d0, d10, d9, ne` — He/N2 lambda factor selection
- At `0x29f58..0x29fc8`: **Shallow Gradient scoring** code (per prior analysis)

### 8.3 CALC_CRUSH_PRESS @ `0x35000`

**Signature:** `void CALC_CRUSH_PRESS(double P_surface, double P_max_bar, double descent_time_min)`

Computes crushing pressure experienced by bubbles during descent.

```c
// For each compartment i:
for i in 0..15:
    P_tissue = pN2[i] + pHe[i]
    P_ambient = P_surface + WV  // at top
    
    // Crushing condition: ambient exceeded tissue pressure
    crush_excess = P_ambient_at_max - P_tissue
    
    if crush_excess <= 0:
        // No crushing: update max crushing pressure tracker
        MaxCrushPressN2[i] = max(MaxCrushPressN2[i], computed_N2_crush)
        MaxCrushPressHe[i] = max(MaxCrushPressHe[i], computed_He_crush)
    else:
        // Impermeability may occur — call ONSET_OF_IMPERMEABILITY
        ONSET_OF_IMPERMEABILITY(P_surface, P_max, descent_time, i)
        // Update crush press with impermeability limit
        MaxCrushPressN2[i] = P_ambient_at_max
        MaxCrushPressHe[i] = computed_from_impermeability

// key constants used:
// 0x40f8bcd... = very large value (~100000 bar) as infinity sentinel
// WV_global at BSS 0x663a0
```

### 8.4 ONSET_OF_IMPERMEABILITY @ `0x360d4`

**Signature:** `void ONSET_OF_IMPERMEABILITY(double P_start, double P_end, double time, int compartment_idx)`

When crush pressure exceeds threshold, bubble membrane becomes impermeable.  
Finds the exact ambient pressure where this occurs using Schreiner integration.

```c
// Set_Inspired_Inert_Press at initial conditions
Set_Inspired_Inert_Press(P_start, time, ...)

// Impermeability criterion:
// Tissue tension at onset time t_imp when:
//   P_tissue(t_imp) = P_amb(t_imp)
// Solved analytically using rate equations

// Half-time arrays indexed by compartment_idx
ht_N2 = halfTimeN2[compartment_idx]  // from 0x15c00 area
ht_He = halfTimeHe[compartment_idx]  // from 0x15c80 area

// Critical pressure stored globally (BSS Amb_Press_Onset_of_Imperm)
```

### 8.5 CRIT_VOLUME @ `0x35b64`

**Signature:** `void CRIT_VOLUME(double total_ascent_time_min)`

Applies VPM-B critical volume algorithm.  
Uses **NEON SIMD** with 128-bit operations.

```c
// VPM-B critical volume integral for each compartment pair:
for i in 0..15 (NEON pairs):
    // Bubble volume integral:
    phase_vol_i = r_N2[i]^3 * lambda_N2 * pN2[i] * pHe[i]^2 / (P_local^2)
    // Quadratic formula for adjusted radius:
    // a*r^2 + b*r + c = 0
    // r = (-b + sqrt(b^2 - 4ac)) / 2a
    // From disassembly: fmla v18, v19, v19 (v19^2 term) + fsqrt
    new_r_N2[i] = (-b + sqrt(b^2 - 4ac)) / 2  * Baro / gamma_factor
    new_r_He[i] = similar

// Stores adjusted critical radii for next iteration
// Used in multi-pass VPM-B schedule optimization
```

Key constants: `4e080d66 dup v6.2d, x11` where `x11=0x40f8bcd... = large value`

### 8.6 CALC_SURFACE_PHASE_VOLUME_TIME @ `0x355b8`

**Signature:** `void CALC_SURFACE_PHASE_VOLUME_TIME()`  
(No arguments — reads all globals)

Calculates the **surface phase volume time** used in VPM-B repetitive dive algorithm.

```c
// Surface interval gas exchange parameters
delta_P_surface = Baro_Press - 1.01325  // altitude correction
rate_factor = delta_P_surface * 0.79   // from rodata 0x138A0 area

for i in 0..15:
    halfTime = halfTimeN2[i]  // from 0x15c80/0x15c00
    
    if pN2_tissue[i] > rate_factor:  // tissue still supersaturated
        // Exponential decay: time to reach equilibrium
        // Uses log() and exp() calls
        if pN2[i] + pHe[i] > rate_factor:
            time_N2 = log((pN2[i] - rate_factor) / pHe[i]) / k_N2[i]
            surface_time = integrate(...)
        else:
            surface_time = 0
    
    SurfacePhaseVolTime[i] = time_N2  // stored to BSS global
```

### 8.7 NUCLEAR_REGENERATION @ `0x316f0`

**Signature:** `void NUCLEAR_REGENERATION(double surface_interval_min)`

Restores bubble nuclei size during surface interval (inter-dive recovery).

```c
// For each compartment (NEON vectorized):
decay = exp(-surface_interval_min / Regen_HalfTime)  // TVPM+120
// Regen_HalfTime initialized from rodata: very large (~N/A?)

for i in 0..15 (NEON):
    r_N2[i] = 1 / (1/r_max_N2 + r_N2_delta[i] * lambda / (2*delta_P))
    r_He[i] = 1 / (1/r_max_He + r_He_delta[i] * lambda / (2*delta_P))
    // Uses gamma_s (0.257 from TVPM+88) and gamma_c (0.0179)
```

Writes updated critical radii to BSS global arrays.

### 8.8 RAD_ROOT_FINDER @ `0x36304`

**Signature:** `void RAD_ROOT_FINDER(double a, double c1, double c2, double lo, double hi, double* result)`

Root finder for the Boyle's law quadratic. Uses **Ridder's method** (not standard bisection):

```c
// Evaluate polynomial at lo and hi
f_lo = a*lo*lo - c1*lo + c2 - lo*a*f(lo)
f_hi = a*hi*hi - c1*hi + c2 - hi*a*f(hi)

if f_lo * f_hi == 0:
    return lo or hi (exact root)

// Ridder's method iteration:
while |hi - lo| > 1e-12:  // tolerance from rodata 0x138f0
    mid = (lo + hi) / 2
    f_mid = evaluate_poly(mid)
    // Regula falsi step using sign of f_mid
    new_x = mid - f_mid * (hi - lo) / (2*sqrt(f_mid^2 - f_lo*f_hi))
    if |new_x - prev_x| < 1e-12: break
    update bracket [lo, hi] based on sign of f_new

*result = converged_root
```

- Called by BOYLES_LAW_COMPENSATION (one call per compartment pair)
- Typically converges in 5–15 iterations

---

## 9. Decompression Stop Engine

### 9.1 BOYLES_LAW_COMPENSATION @ `0x342ac`

**Signature:** `void BOYLES_LAW_COMPENSATION(double stop_pressure, double previous_stop_pressure, double ascent_rate)`

Applies Boyle's law correction to bubble volume when ascending between stops.

```c
// Clamp stops:
actual_stop = max(stop_pressure, previous_stop_pressure)
delta_stop = |stop_pressure - previous_stop_pressure|
if delta_stop == 0:
    // No change: copy current radii to compensation radii
    memcpy(RadiiN2_comp, RadiiN2, 16*8)
    memcpy(RadiiHe_comp, RadiiHe, 16*8)
    return

// Compute Boyle ratio for each compartment:
P_new = stop_pressure + WV
P_old = previous_stop_pressure + WV
R_ratio = P_old / P_new   // pressure ratio

// VPM-B correction:
// Bubble expands: r_new from cubic root of Boyle volume
// r_new^3 = r_old^3 * (P_old/P_new)
// Calls pow(ratio, 1/3) then iterates via RAD_ROOT_FINDER
for i in 0..15:
    r0_N2 = RadiiN2[i]
    r0_He = RadiiHe[i]
    P_ratio = P_old / P_new
    
    // Cubic root:
    r_trial = (2*r0*P_old) / P_new  // from code: fdiv then fmul then pow
    pow(P_old/P_new, 0.333...) * r0
    
    // Solve quadratic for corrected radius via RAD_ROOT_FINDER:
    a = P_new
    b = −2*gamma_c
    c = −r0^3 * P_old
    RAD_ROOT_FINDER(a, b, c, lo, hi, &r_comp_N2[i])
    
    // Store compensated radius
    r_comp_N2[i] = P_amb_mean / gamma / r_root

// Constant 0.333...from float: movk x8, #0x3ff3 → IEEE754 = 1/3 exactly
```

### 9.2 DECOMPRESS_STOP @ `0x34760`

**Signature:** `double DECOMPRESS_STOP(double stop_pressure_bar, double ascent_rate_bar_per_min)`  
(Method on TVPM instance, x0=this)

**The master stop-time calculation function.** Most complex in the library.

#### Phase 1: VPM vs GF mode selection

```c
// TVPM+204 = Stop_increment flag
if (Stop_increment != 0):  // VPM-B mode
    goto VPM_stop_check
else:                       // Buhlmann/GF mode
    call CALC_DECO_CEILING(output_ceiling)
```

#### Phase 2: Shallow Gradient snap-to-stop

From decoded logic near `0x3484c`:
```c
// Check if current depth is an exact stop multiple
depth_in_stop_units = stop_pressure / stop_increment
frac_part = depth_in_stop_units - floor(depth_in_stop_units)
tolerance_lo = −0.001  // rodata 0x139a0
tolerance_hi =  0.001  // rodata 0x13998

if frac_part > tolerance_hi:
    // ShallowGrad active — skip snap extension
    // This is the ShallowGradient bypass path
    if ShallowGrad_flag:
        goto normal_stop_computation  // bypasses fractional extension
```

#### Phase 3: Stop time computation loop

```c
// Main loop: extend stop until safe to ascend
stop_time = 0
while true:
    // Load inspired pressures at this stop
    Set_Inspired_Inert_Press(stop_pressure, -1.0, ...)
    
    // Check if ascent is safe (GF or VPM criterion):
    if (VPM_mode):
        // VPM: check allowable gradient against actual gradient
        for i in 0..15:
            AG = (pN2[i]*AG_N2_comp[i] + pHe[i]*AG_He_comp[i]) / (pN2[i]+pHe[i])
            actual_grad = pN2[i] + pHe[i] + WV - stop_pressure
            if actual_grad > AG + tolerance:
                goto add_time  // must wait longer
    else:
        // GF: ceiling must be <= stop_pressure
        gf = compute_linear_GF(stop_pressure, first_stop, surface)
        ceil = CALC_DECO_CEILING_GF(gf)
        if ceil > stop_pressure + 0.001:
            goto add_time
    
    // Safe to ascend — return stop time
    break
    
  add_time:
    stop_time += 1 minute  // or fractional minute
    GAS_LOADINGS_CONST_DEPTH(stop_pressure, 1.0)  // load 1 more minute
    CALC_MAX_ACTUAL_GRAD(stop_pressure)  // check gradient
```

#### Phase 4: Stop size selection logic (near `0x349f8`)

```c
if (CCR_mode && stop_type == EXTENDED):
    if (depth > 30m && CCR):
        stop_minutes_per_step = 32  // from literal 0x20
    else:
        stop_minutes_per_step = 24  // from literal 0x18
    if (depth <= 21m):
        // ShallowGrad override: finer step
        stop_minutes_per_step = computed_from_ShallowGrad
```

#### Phase 5: VPM-B stop (near `0x34918`)

```c
// VPM-B branch:
ceil = CALC_DECO_CEILING()    // non-GF ceiling
stop = round_to_increment(ceil)

// GF-like linear interpolation for VPM:
gf_at_stop = GF_Lo + (GF_Hi - GF_Lo) * (stop - first_stop) / (surface - first_stop)

while ceil > stop_pressure:
    GAS_LOADINGS_CONST_DEPTH(stop_pressure, 1.0)
    ceil = CALC_DECO_CEILING()
    stop_time += 1.0
```

---

## 10. Repetitive Dive Logic

### 10.1 VPM_REPETITIVE_ALGORITHM @ `0x30c28`

**Signature:** `void VPM_REPETITIVE_ALGORITHM(double surface_interval_min)`

Adjusts critical radii for repetitive dives based on surface interval duration.

```c
// Initialize working radii from initial radii
InitAllowGradN2[0..15] = Adjusted_N2[0..15]  // init all 16
InitAllowGradHe[0..15] = Adjusted_He[0..15]

if surface_interval_min >= Regen_HalfTime:
    // Fully regenerated — use fresh radii
    return
else:
    // Partial regeneration
    R = surface_interval_min / Regen_HalfTime  // = 0..1
    
    // delta = 1 - R
    delta = 1.0 - R
    
    for i in 0..15:
        P_N2_tissue = pN2[i]
        P_He_tissue = pHe[i]
        
        if pN2[i] > pN2_ambient[i]:  // still supersaturated
            // Scale critical radius based on remaining bubble nuclei
            // factor = 0.4 (from rodata 0x13880)
            lambda_factor = 0.4  
            lambda = lambda_N2 * (1/R - 1) * (-1)  // from 0x40f8bcd... (large neg)
            
            // New N2 allowable gradient:
            r_adj = pN2[i] / P_N2_tissue * lambda_factor * (delta) * scaling
            AG_N2[i] = max(AG_N2[i] * r_adj + current_AG, AG_N2[i])
            
        // Similar for He
```

- Key constant: `0.4` from rodata `0x13880` — this is the VPM-B delta (surface excursion fraction)
- Another: large negative `0xc0f8bcd... ≈ −100000` used as starting bound

---

## 11. Utility Functions

### 11.1 SET_CRITICAL_RADII @ `0x305c0`

**Signature:** `void SET_CRITICAL_RADII(double initial_pressure_bar)`

Sets the initial critical radii for all 16 compartments.

```c
// Two paths: CCR vs OC
if (CCR_mode):
    // Use gas-specific table indexed by gas_mix
    gas_idx = TVPM.Gas_Mix_Index  // at +56
    r_N2_base = HalfTime_table[gas_idx]  // from adr 0x16398
    r_N2 = r_N2_base * rodata_0x13858  // * 0.55
    r_He = r_N2_base * rodata_0x139c8  // * 0.45
else:
    // OC path:
    P_ratio = (initial_pressure_bar + WV) / WV  // supersaturation ratio
    
    if P_ratio >= ShallowGrad_threshold:  // compare with 0x13870 = 10.337
        // Deep dive: normal VPM-B radii
        blend = clamp((P_ratio - 1) / (P_ratio - 1), 0.0, 0.5)
        blend2 = clamp(P_ratio, -0.5, 0.5)
        r_N2 = blend * a * 0.45 + blend2 * b * 0.8
        r_He = blend * a * 0.45 + blend2 * b * 0.8
    else:
        // Shallow: use smaller radii
        ...

// Store to BSS global arrays:
// Rad_N2_initial[0..15] all same value r_N2 (uniform across compartments at start)
// Rad_He_initial[0..15] all same value r_He
```

Key lookup table at `0x16398` — 16 doubles, halfTime-indexed initial radii.

### 11.2 CALC_BARO_PRESS @ `0x306dc`

Computes barometric pressure from altitude using ICAO standard atmosphere.

```c
// ICAO formula:
// P_baro = P_sl * (1 - 0.0000226 * altitude_m)^5.256
// From rodata: 288.15 K, 0.0000226 lapse rate
if (metric_mode):
    altitude_m = input
else:
    altitude_m = input_ft * 0.3048  // rodata 0x13838
    
P_baro = P_sea_level * pow(1 - 2.26e-5 * altitude_m, 5.256)
```

---

## 12. ZHL-16C Table Variant Identification

### He Half-Times: Canonical ✓

From `0x15c80` k-values, implied He half-times:  
`5, 8, 12.5, 18.5, 27, 38.3, 54.3, 77, 109, 146, 187, 239, 305, 390, 498, 635`  
→ Matches **Bühlmann ZHL-16C** exactly.

### N2 Half-Times: MultiDeco-Specific

From `0x15c00` k-values, implied N2 half-times:  
`1.88, 3.02, 4.72, 6.99, 10.21, 14.48, 20.53, 29.11, 41.2, 55.19, 70.69, 90.34, 115.3, 147.4, 188.2, 240`

**Note:** These do NOT match canonical ZHL-16C N2 halftimes (4, 8, 12.5, 18.5, 27, 38.3...).  
MultiDeco N2 halftimes are approximately **2/3 of He halftimes** (ratio ≈ 0.375):
```
He[i] / N2[i] = 5/1.88=2.66, 8/3.02=2.65, 12.5/4.72=2.65...
```
This suggests MultiDeco uses **N2 halftimes = He_HT × (1/2.65)** — this is the Bühlmann ratio  
(N2 = He × 0.375 approximately, corresponding to N2 diffusion being slower).

**This is a key finding:** MultiDeco does NOT use the standard published N2 half-times.  
It derives them from He half-times with a fixed ratio — this matches some implementations  
like BühlmannE (Ernst) where N2/He ratio is held constant.

### a-values

The a and b value arrays are **not stored in rodata** — they are computed at runtime in the  
TVPM constructor from the rodata initial values (0.257, 0.0179, etc.) and stored in BSS.  
The `0x161c0` table (0.48–11.0 range, 44 entries) appears to be a **b-value lookup table  
for variable stop increments**, not the ZHL-16C b-values per compartment.

**a5 (compartment 5) value** found at `0x16230`: `0.6200` — matching **Subsurface/decotengu variant**  
rather than canonical Bühlmann (0.6491).

---

## 13. Global BSS Variables Map

All at base `0x61000` (Amb_Press_Onset_of_Imperm segment):

| BSS Offset | Symbol / Usage |
|------------|----------------|
| +0x18 = 0x24 | WV or Surface_O2_pressure |
| +0x20 = 0x20 | First_Stop_Depth (double*) |
| +0x28 = 0x28 | SurfacePhaseVolTime_ptr |
| +0x30 = 0x30 | Max_Actual_Grad_ptr |
| +0x38 = 0x38 | InitAllowGrad_N2_ptr |
| +0x40 = 0x40 | InitAllowGrad_He_ptr |
| +0x48 = 0x48 | pN2_tissue_ptr |
| +0x50 = 0x50 | pHe_tissue_ptr |
| +0x58 = 0x58 | Water_Vapor_Press_ptr |
| +0x60 = 0x60 | Baro_Press_ptr |
| +0x68 = 0x68 | Amb_Press_Onset_of_Imperm (the symbol itself) |
| +0x70 = 0x70 | MaxCrushPress_N2_ptr |
| +0x78 = 0x78 | MaxCrushPress_He_ptr |
| +0x80 = 0x80 | RadiiN2_current_ptr |
| +0x88 = 0x88 | RadiiHe_current_ptr |
| +0x90 = 0x90 | CritVolTime_ptr |
| +0x98 = 0x98 | AllowGrad_N2_comp_ptr |
| +0xa0 = 0xa0 | AllowGrad_He_comp_ptr |
| +0xa8 = 0xa8 | RadiiN2_comp_ptr |
| +0xb0 = 0xb0 | RadiiHe_comp_ptr |
| +0x130 = 0x130 | ShallowGrad_active_flag_ptr |
| +0x168 = 0x168 | VPM_active_flag_ptr |
| +0x178 = 0x178 | stop_counter_ptr |

---

## 14. Algorithm Flow Summary

### Bühlmann/GF Mode

```
SET_CRITICAL_RADII → gas loadings for all segments →
CALC_START_OF_DECO_ZONE → first stop depth →
loop: CALC_DECO_CEILING_GF(gf_at_current_depth) →
      if ceiling > current_stop: DECOMPRESS_STOP →
      else: ascend to next stop
ShallowGradDepthTest/TimeTest → optional GF blend
```

### VPM-B Mode

```
SET_CRITICAL_RADII → gas loadings →
CALC_CRUSH_PRESS (including ONSET_OF_IMPERMEABILITY) →
CALC_INIT_ALLOW_GRAD →
loop: CALC_DECO_CEILING → BOYLES_LAW_COMPENSATION →
      DECOMPRESS_STOP (VPM criterion: AG vs AllowGrad) →
      ascend
CRIT_VOLUME → adjust radii → re-run schedule until convergence
```

### Repetitive Dive

```
Surface interval:
    GAS_LOADINGS_SURFACE_INTERVAL(SI_min)
    NUCLEAR_REGENERATION(SI_min)   // restore bubble nuclei
    VPM_REPETITIVE_ALGORITHM(SI_min)  // adjust allow. gradients
    CALC_SURFACE_PHASE_VOLUME_TIME()   // update surface vol time

Next dive: VPM_CALCULATE(new_profile, ...)
```

---

## Appendix: Function Address Reference

| Function | vaddr | Size (approx) |
|----------|-------|---------------|
| VPM_CALCULATE | 0x29c18 | ~6 KB |
| VPM_REPETITIVE_ALGORITHM | 0x30c28 | ~400 B |
| SET_CRITICAL_RADII | 0x305c0 | ~280 B |
| CALC_BARO_PRESS | 0x306dc | ~120 B |
| GAS_LOADINGS_SURFACE_INTERVAL | 0x307a8 | ~300 B |
| NUCLEAR_REGENERATION | 0x316f0 | ~200 B |
| SetGradFactor | 0x31608 | ~150 B |
| CALC_INIT_ALLOW_GRAD | 0x31844 | ~300 B |
| CALC_START_OF_DECO_ZONE | 0x318ec | ~400 B |
| PROJECTED_ASCENT | 0x320f8 | ~600 B |
| GAS_LOADINGS_ASCENT_DESCENT | 0x32b9c | ~500 B |
| CALC_MAX_ACTUAL_GRAD | 0x3416c | ~400 B |
| BOYLES_LAW_COMPENSATION | 0x342ac | ~600 B |
| DECOMPRESS_STOP | 0x34760 | ~1.8 KB |
| CALC_SURFACE_PHASE_VOLUME_TIME | 0x355b8 | ~400 B |
| CALC_CRUSH_PRESS | 0x35000 | ~800 B |
| CRIT_VOLUME | 0x35b64 | ~800 B |
| GAS_LOADINGS_CONST_DEPTH | 0x35370 | ~400 B |
| SCHREINER_EQUATION | 0x35dc4 | ~80 B |
| HALDANE_EQUATION | 0x35e04 | ~60 B |
| Set_Inspired_Inert_Press | 0x35e38 | ~300 B |
| ONSET_OF_IMPERMEABILITY | 0x360d4 | ~400 B |
| RAD_ROOT_FINDER | 0x36304 | ~300 B |
| CALC_DECO_CEILING | 0x31ee0 | ~200 B |
| CALC_DECO_CEILING_GF | 0x31bf8 | ~400 B |
| CALC_ASCENT_CEILING | 0x31dc0 | ~200 B |
| TVPM constructor | 0x3642c | ~150 B |
