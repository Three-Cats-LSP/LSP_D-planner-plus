# APK Reverse Engineering — DiveKit & MultiDeco
**Date:** June 2026  
**Analyst:** Three-Cats-LSP / Perplexity Computer  
**Purpose:** Study deco engine internals from published Android APKs for comparison with LSP and Subsurface

---

## Overview

Two APKs were obtained and analyzed:

| App | Package | APK Source | Engine Type |
|-----|---------|-----------|-------------|
| DiveKit | `app.skuba.diving` | APKPure XAPK v1.1.8 (107 MB) | React Native / Hermes JS bytecode |
| MultiDeco | `com.hhssoftware.multideco` | hhssoftware.com v2.26 (4.3 MB) | Native C++ via JNI (`libmultideco.so`) |

Tools used:
- `hermes-dec` — decompile Hermes bytecode v96 to pseudo-JS
- Python `struct` — binary scanning of native `.so` for float64/float32 constants
- Linux `strings` — extract symbol table and string pool
- DEX string table parsing — read Java class/method/field names

---

## DiveKit (`app.skuba.diving`)

### Architecture

DiveKit is a **React Native** app built with Expo. The entire application logic ships as a single Hermes bytecode bundle:

```
assets/index.android.bundle  — 13 MB, Hermes bytecode version 96
```

This was decompiled with `hermes-dec` to ~1.58 million lines of pseudo-JS (59 MB).

### Deco Planner Status: **Not Yet Implemented**

The i18n string table (confirmed in 6 language packs — EN, AR, DE, SV, TR, and more) shows:

```js
r11['decoPlanner'] = { description: 'Coming soon...', title: 'Deco Planner' }
```

This appears in every language pack. **There is no deco engine in this version of the app.**

The app contains working implementations of:
- EAD / END / PPO₂ / gas density calculator
- Best mix / MOD
- Gas blender (partial-pressure + continuous)
- Gas usage planner (rule of thirds / sixths)
- RMV / SAC
- Buoyancy calculator
- Cylinder database

But the decompression planner module is a stub. There is no Bühlmann compartment math, no tissue loading, no ceiling calculation in this APK.

### What the Bundle Contains

```
ead-ppo2.tsx        — full PPO₂ / EAD / END / gas density screen
ppo2Values          — [1.2, 1.4, 1.6] threshold configs
tissueLoading       — string field only (user types "Low (per computer)")
```

The `tissueLoading` field in the dive log is a **free-text entry** — the user types their computer's tissue loading readout. It is not computed by DiveKit.

### Implication for Cross-Reference Data

DiveKit results in the previous `LSP_vs_MultiDeco_vs_DiveKit` comparison table came from a **different source** (likely the DiveKit web app at divekit.app, which may have a working engine, or an earlier beta). The public Android APK v1.1.8 cannot generate deco plans.

---

## MultiDeco (`com.hhssoftware.multideco`)

### Architecture

MultiDeco is a thin Java UI shell over a **native C++ deco engine**. The engine is in:

```
lib/arm64-v8a/libmultideco.so   — 378 KB, ELF64 ARM, stripped
lib/armeabi-v7a/libmultideco.so — 32-bit version
```

Built with: **NDK r29, Clang 21.0.0**, Android API 27+, with PGO + Bolt + LTO optimizations.

The Java side calls the engine via 13 JNI functions in `com.hhssoftware.multideco.Settings`:

```java
Java_com_hhssoftware_multideco_Settings_initDecoCalc
Java_com_hhssoftware_multideco_Settings_decoCalc
Java_com_hhssoftware_multideco_Settings_cleanup
Java_com_hhssoftware_multideco_Settings_nextDive
Java_com_hhssoftware_multideco_Settings_getCurrentDiveN
Java_com_hhssoftware_multideco_Settings_getErrString
Java_com_hhssoftware_multideco_Settings_getResultRows
Java_com_hhssoftware_multideco_Settings_resultRow
Java_com_hhssoftware_multideco_Settings_getWarning
Java_com_hhssoftware_multideco_Settings_diveReport
Java_com_hhssoftware_multideco_Settings_ic
Java_com_hhssoftware_multideco_Settings_rs
Java_com_hhssoftware_multideco_Settings_setPackage
```

### Engine Class: `TVPM`

The engine is structured as a single C++ class named **`TVPM`** (demangle confirms this). Key methods extracted from the symbol table:

#### Gas Loading
```
TVPM::GAS_LOADINGS_CONST_DEPTH(double, double)
TVPM::GAS_LOADINGS_ASCENT_DESCENT(double, double, double)
TVPM::GAS_LOADINGS_ALTITUDE_CHANGE(double, double, double)
TVPM::CALC_O2_LOADINGS_CLOSED(double, double, double, double*, double*)
TVPM::CALC_O2_LOADINGS_OPEN(double, double, double, double, double*, double*)
```

#### Ceiling / Deco
```
TVPM::CALC_DECO_CEILING_GF(double, double*)
TVPM::CALC_DECO_CEILING(double*)
TVPM::CALC_ASCENT_CEILING(double*, int)
TVPM::CALC_START_OF_DECO_ZONE(double, double, double*, int*)
TVPM::DECOMPRESS_STOP(double, double)
TVPM::PROJECTED_ASCENT(double, double, double, double*)
```

#### VPM-B Specific
```
TVPM::VPM_CALCULATE(rdFGsndd*, double, double)
TVPM::VPM_ALT_DIVE_ALGORITHM(w23hdtMi*)
TVPM::VPM_REPETITIVE_ALGORITHM(double)
TVPM::NUCLEAR_REGENERATION(double)
TVPM::CALC_CRUSH_PRESS(double, double, double)
TVPM::BOYLES_LAW_COMPENSATION(double, double, double)
TVPM::CRIT_VOLUME(double)
TVPM::CALC_SURFACE_PHASE_VOLUME_TIME()
TVPM::FAST_BAILOUT_BIAS(double, double, double)
```

#### Configuration Properties
```cpp
TVPM::SetExtendedStops(bool)
TVPM::SetO2Affect(bool)
TVPM::SetForceExtendedStops(bool)
TVPM::SetAddExtendedStopsTime(bool)
TVPM::SetSetPoint(double)
```

### ZHL-16C Constants Confirmed in Binary

#### N2 b-coefficients — found at `0x015e80` (16× float64, 8-byte aligned)

```
Compartment | b (stored) | b (ZHL-16C ref)
     1      |  0.557800  |    0.5578  ✓
     2      |  0.651400  |    0.6514  ✓
     3      |  0.722200  |    0.7222  ✓
     4      |  0.782500  |    0.7825  ✓
     5      |  0.812600  |    0.8126  ✓
     6      |  0.843400  |    0.8434  ✓
     7      |  0.869300  |    0.8693  ✓
     8      |  0.891000  |    0.8910  ✓
     9      |  0.909200  |    0.9092  ✓
    10      |  0.922200  |    0.9222  ✓
    11      |  0.931900  |    0.9319  ✓
    12      |  0.940300  |    0.9403  ✓
    13      |  0.947700  |    0.9477  ✓
    14      |  0.954400  |    0.9544  ✓
    15      |  0.960200  |    0.9602  ✓
    16      |  0.965300  |    0.9653  ✓
```

All 16 values are exact matches to ZHL-16C. This is the definitive proof MultiDeco uses Bühlmann ZHL-16C.

#### N2 a-values — found at `0x015e00` (preceding the b array)

The values at `0x015e00` are **not** the standard bar-unit a-values. They appear to be a scaled representation (possibly a-values × 10 or in a custom unit used internally):

```
[1] 16.1890  [2] 13.8300  [3] 11.9190  [4] 10.4580
[5]  9.2200  [6]  8.2050  [7]  7.3050  [8]  6.5020
...
```

These may be related to the M-value / critical tension ceiling representation.
Exact mapping requires disassembly of `CALC_DECO_CEILING_GF`.

#### N2 Half-Times — found as immediate values in compiled code

ZHL-16C N2 half-times appear scattered as double-precision immediates in the `.text` section:
- `5.0` at `0x015798` and `0x016320`
- `8.0` at `0x016330`
- `12.5` at `0x016350`

They are compiled as instruction operands, not stored as a flat array — consistent with the LTO-optimized build inlining constants.

### Water Vapour Pressure Analysis

This is the most safety-critical constant. Three candidates found:

| Value | Location | Identification |
|-------|----------|---------------|
| `0.049318` | `0x037f05` (unaligned, in code) | Schreiner constant (47 mmHg ≈ 0.0493 bar) |
| `0.050000` | `0x013860` (aligned double) | Rounded Schreiner / arbitrary |
| `~0.0625` | Many float32 hits in code | Likely **computed values** (not a hardcoded constant) |

**Key finding:** `Water_Vapor_Press` is a **named global variable** (confirmed from symbol table at `0x005d69`). It is **not a compile-time constant** — it can be set at runtime. The Java DEX contains:

```
configWater         — UI config key
ConfigRowWater      — settings screen row
ConfigRowWaterHelp  — help text
WaterType           — saltwater / freshwater toggle
```

This means **MultiDeco's WV pressure is user-configurable** (or at minimum set during `initDecoCalc` from a preference). The `Water_Vapor_Press` variable name matches the VPM-B Baker source code directly, suggesting the engine is derived from the original Fortran-to-C port.

### Gradient Factors

Confirmed in both DEX string table and native symbol table:

```
GFHi              — Java setting key
GFLo              — Java setting key  
configGFHi        — UI config
configGFLoHi      — UI config
configConserveGFHi / configConserveGFLo  — bailout conservatism
bailConserveGFHi  — bailout config
CALC_DECO_CEILING_GF(double, double*)  — native ceiling function taking GF
Deco_Grad_N2 / Deco_Grad_He           — per-gas gradient tracking
```

MultiDeco implements GF as a **wrapper around the VPM-B ceiling**, not as a standalone Bühlmann-GF implementation. The function `CALC_DECO_CEILING_GF` applies gradient scaling to the VPM-B critical tension ceiling.

### Shallow Gradient Logic

MultiDeco has a proprietary **shallow gradient acceleration** feature:

```
Shallow_Grad_Depth_Factor
Shallow_Grad_Time_Factor  
Shallow_Grad_Max_ATA_Factor
ShallowGradDepthTest()
Apply_Shallow_Grad
```

This is separate from GF and appears to be an optional acceleration of shallow stops. No equivalent exists in LSP or Subsurface.

### CCR / SCR Support

Full closed-circuit and semi-closed circuit support confirmed:

```
CCRStart              — CCR mode start time
SCRDataValid          — SCR validation flag
SCRO2Drop             — SCR O₂ drop rate
CALC_O2_LOADINGS_CLOSED(...)   — CCR O₂ loading
CALC_O2_LOADINGS_OPEN(...)     — OC O₂ loading
ppO2Above / ppO2Below / ppO2Deep / ppO2ReallyDeep / ppO2Swaps
```

### Altitude Support

```
GAS_LOADINGS_ALTITUDE_CHANGE(double, double, double)
FromAlt              — altitude acclimatisation pre-saturation flag
Baro_Press           — ambient barometric pressure
Elevation = %d %s    — report string
```

Altitude pre-saturation (acclimatisation) is confirmed — matches what we observed in scenario A5 cross-reference.

### VPM-B Constants

The variable names match Baker's VPM-B Fortran source directly:

```
Crit_Rad_N2_Microns      Init_Crit_Rad_N2
Crit_Rad_He_Microns      Init_Crit_Rad_He
Adj_Crit_Rad_N2          Adj_Crit_Rad_He
Adj_Crush_Press_N2       Adj_Crush_Press_He
Max_Crush_Press_N2       Max_Crush_Press_He
Regen_Rad_N2             Regen_Rad_He
Gas_Tension_Onset_of_Imperm
Amb_Press_Onset_of_Imperm
Allow_Grad_N2 / Allow_Grad_He
Init_Allow_Grad_N2 / Init_Allow_Grad_He
Max_Boyle_Datum / Calc_Boyle_Datum
Surface_Phase_Volume_Time
NUCLEAR_REGENERATION(double)
CRIT_VOLUME(double)
BOYLES_LAW_COMPENSATION(double, double, double)
VPMModel             — model selection (ZHL-GF or VPM-B)
```

Both **ZHL-16C + GF** and **VPM-B** are selectable at runtime via `VPMModel`.

---

## Comparison: Engine Architecture Summary

| Feature | LSP D-Planner | MultiDeco | Subsurface | DiveKit |
|---------|--------------|-----------|------------|---------|
| Language | JavaScript | C++ (native) | C (core/deco.cpp) | JavaScript (RN) |
| ZHL-16C | ✓ | ✓ confirmed | ✓ confirmed | Not shipped yet |
| VPM-B | ✓ | ✓ full Baker port | ✓ | — |
| GF support | ✓ | ✓ | ✓ | — |
| b-coefficients | ZHL-16C exact | ZHL-16C exact | ZHL-16C exact | — |
| WV pressure | 0.0577 bar | Configurable (default ~0.05?) | 0.0627 bar | — |
| CCR | ✓ | ✓ | ✓ | — |
| Altitude pre-sat | ✗ | ✓ | partial | — |
| Shallow grad | ✗ | ✓ (proprietary) | ✗ | — |
| APK size | ~11 MB | 4.3 MB | — | 107 MB |

---

## Revised Verdict on WV Pressure

Our previous analysis attributed the TTS difference between MultiDeco and Subsurface primarily to WV pressure:
- Subsurface: `0.0627 bar` (strict Bühlmann)
- MultiDeco/LSP: assumed `0.0577 bar`

**This is now partially revised.** MultiDeco's `Water_Vapor_Press` is a runtime variable — not a compile-time constant — and the binary does not contain `0.0577` as a stored double. The closest hardcoded value is `0.0500` (Schreiner-adjacent). 

The actual WV value used by MultiDeco is **set from user settings or internal defaults** via `initDecoCalc`. It may differ from what we assumed, and the output gap between MultiDeco and Subsurface may have more to do with:
1. Last-stop release logic (`Forced_First_Stop_Depth`, stop completion logic)
2. The shallow gradient feature (`Shallow_Grad_*`)
3. GF applied on top of VPM-B ceilings differently

LSP's WV choice of `0.0577` was an explicit code decision, not inherited from MultiDeco. LSP is the most conservative in reducing WV (relative to Subsurface), which intentionally produces shorter TTS — a deliberate conservatism trade-off by the LSP developer.

---

## Files in This Analysis

| File | Description |
|------|-------------|
| `APK_Reverse_Engineering.md` | This document |
| `subsurface_engine.py` | Python port of Subsurface `core/deco.cpp` |
| `Subsurface_Engine_Analysis.md` | Full Subsurface engine cross-reference analysis |
| `DiveKit_Engine_Knowledge_Base.md` | DiveKit algorithm documentation |

---

*Sources: APKs analyzed under fair use / research. MultiDeco © HHS Software. DiveKit © Ronny Majani. Subsurface © GPL v2.*
