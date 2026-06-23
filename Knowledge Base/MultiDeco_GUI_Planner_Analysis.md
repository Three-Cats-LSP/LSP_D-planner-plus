# MultiDeco GUI Planner — Full Analysis
**Source:** `classes.dex` decompiled via jadx 1.5.1  
**App package:** `com.hhssoftware.multideco`  
**App author:** HHS Software  
**Total Java classes decompiled:** 2,020 (28 in app package, rest AndroidX/Kotlin stdlib)

---

## 1. Activity Map

| Activity class | Role |
|---|---|
| `multideco_main` | Central hub — dive segment table, CALC button, async engine dispatch |
| `multideco_level` | Add/edit a bottom segment (depth, time, gas, CCR setpoint) |
| `multideco_deco` | Add/edit a deco gas (O2%, He%, optional swap depth) |
| `multideco_config` | All settings (model, GF, ppO2 limits, ascent/descent rates, etc.) |
| `multideco_result` | Display plan rows + gas report + warnings; email/copy |
| `multideco_bail` | CCR bail-out plan |
| `multideco_maxtime` | Max bottom time calculator |
| `multideco_bestmix` | Best mix calculator |
| `multideco_eadmod` | EAD/MOD calculator |
| `multideco_about` | Version / credits |
| `multideco_agree` | EULA agreement |
| `multideco_registration` | License key screen |
| `multideco_toolslist` | Tools menu launcher |
| `Settings` | **JNI bridge + all settings persistence** |
| `tools_calc` | Pure-Java gas tools (nitrox, trimix blending, density) |
| `Gastank_setting` | Tank/RMV model |
| `Theme_setting` | Dark/light theme selection |
| `VersionCheck` | Remote version check (hhssoftware.com) |
| `Android_RSA` | RSA license verification (hhssoftware.com CGI) |
| `Identity` | Registration identity |

---

## 2. JNI Interface (Settings.java)

The `Settings` class is the **only** JNI bridge to `libmultideco.so`:

```java
static { System.loadLibrary("multideco"); }
```

### Native Methods

| Method | Signature | Purpose |
|---|---|---|
| `setPackage` | `(String) → int` | Pass APK source path; reads embedded license data; returns 1 if config reset needed |
| `initDecoCalc` | `(int surfInt, String levels, String decos, String maxtime) → int` | Load dive plan into engine; returns error code (0 = OK) |
| `decoCalc` | `() → int` | Run the decompression calculation; returns error code |
| `getResultRows` | `() → int` | Number of result rows produced |
| `resultRow` | `(int row) → String[]` | Fetch one result row (7 elements) |
| `diveReport` | `() → String[]` | Fetch the gas/dive summary report strings |
| `getWarning` | `(int row) → int` | Warning bitmask for a result row |
| `getErrString` | `() → String` | Human-readable error detail string |
| `getCurrentDiveN` | `() → int` | Current dive number (for repetitive dives) |
| `nextDive` | `(boolean) → int` | Advance to next repetitive dive |
| `cleanup` | `() → int` | Free native memory (called in `onDestroy`) |
| `m52ic` | `(String) → String` | License check / identity confirmation (obfuscated name) |
| `m53rs` | `(String, String) → int` | Registration store (obfuscated name) |

---

## 3. Dive Segment String Format

All dive data is passed to `initDecoCalc` as **`#`-delimited lists of formatted strings**.  
Each segment uses `, ` (comma-space) delimiters internally.

### Bottom Segment String (OC mode)
```
"<depth>, <time>, <O2>[/<He>]"
```
Examples:
- `"40, 25, 21"` → 40 ft/m, 25 min, air
- `"40, 25, 21/35"` → 40 ft/m, 25 min, 21/35 trimix
- `"40, -, 21"` → depth-only (no time; used for travel segments)

### Bottom Segment String (CCR mode)
```
"<depth>, <time>, <O2>[/<He>], [OC|SCR|<setpoint>]"
```
Examples:
- `"40, 25, 10/50, 1.20"` → CCR with SP 1.20
- `"40, 25, 10/50, OC"` → CCR with OC bailout override
- `"40, 25, 10/50, SCR"` → CCR in SCR mode

### Deco Gas String
```
"<O2>[/<He>] [<swap_depth><unit>]"
```
Examples:
- `"50"` → EAN50, no swap
- `"100"` → pure O2
- `"50 70ft"` → EAN50, switch at 70 ft
- `"21/35 100ft"` → trimix deco gas, switch at 100 ft

### `calclevels` / `calcdecos` to `initDecoCalc`
```java
// Each selected row appended with '#'
calclevels = "40, 25, 21#" + "30, 10, 21#"   // two bottom segs
calcdecos  = "50#100#"                          // two deco gases
calcmaxtime = "50<gas_avail>#..."               // gas availability (optional)
```
These three strings are passed as `strArr[0]`, `strArr[1]`, `strArr[2]` to `initDecoCalc`.

### Segment Field Index (`Settings.LegStrSeg` / `LegIntSeg`)
The static helper `LegStrSeg(String, int)` parses segment strings by field:

| Index | Field |
|---|---|
| 1 | Depth |
| 2 | Time |
| 3 | Mix string (full) |
| 4 | O2% (integer) |
| 5 | He% (integer) |
| 6 | CCR mode flag (OC = "OC") |
| 7 | SCR flag ("SCR") |
| 8 | CCR setpoint (float) |
| 9 | Decozone from (OC/CCR switch depth, only when no `, ` separators) |

---

## 4. Calculation Flow

```
User fills segments in multideco_main
        │
        ▼
doCalcClick()
  ├─ collect checked rows from TableLevels → calclevels (string)
  ├─ collect checked rows from TableDecos  → calcdecos  (string)
  ├─ collect gas availability from tanks   → calcmaxtime (string)
  └─ new CalcTask().execute(calclevels, calcdecos, calcmaxtime)
        │
        ▼  (AsyncTask background thread)
CalcTask.doInBackground()
  ├─ settings.initDecoCalc(surfInt, calclevels, calcdecos, calcmaxtime) → errCode
  └─ if errCode==0: settings.decoCalc() → errCode
        │
        ▼  (back on UI thread)
CalcTask.onPostExecute()
  ├─ errCode != 0 → doCalcErrDlg(errCode)   [alert with err_str()]
  └─ errCode == 0 → launchResultActivity()
        │
        ▼
launchResultActivity()
  ├─ getResultRows()         → N rows
  ├─ resultRow(i) → String[7] per row
  ├─ getWarning(i) → bitmask per row
  ├─ diveReport()  → String[] summary
  └─ startActivityForResult(multideco_result.class, ...)
        │
        ▼
multideco_result.onCreate()
  ├─ buildRows()        (table of dive steps)
  ├─ insertBanners()    (column headers)
  ├─ insertWarnings()   (colored warning rows)
  └─ addButtons()       (Next Dive, Copy, Email)
```

---

## 5. Result Row Format (`resultRow(int)` → `String[7]`)

Each row returned by the native engine has 7 fields:

| Index | Content | Example |
|---|---|---|
| 0 | Row type code (2-char) | `"De"` (descent), `"As"` (ascend), `"St"` (stop), `"Le"` (level), `"Su"` (surface) |
| 1 | Depth string | `"40 ft"` / `"12 m"` |
| 2 | Stop time (min) | `"5"` |
| 3 | Run time (min) | `"42"` |
| 4 | Gas mix | `"21"` / `"50"` / `"21/35"` |
| 5 | ppO2 | `"1.40"` |
| 6 | EAD/END | `"40 ft"` |

Row type second character determines icon in `buildrow()`:
- `'e'` → descend icon  
- `'s'` → ascend icon  
- `'t'` → stop icon  
- `'v'` → level icon  
- `'f'` → surface icon  

---

## 6. Warning System

`getWarning(int row)` returns a bitmask. Defined flags in `Settings.java`:

| Bit | Constant | Meaning |
|---|---|---|
| 1 | `kHighppO2Warn` | ppO2 above limit |
| 2 | `kLowppO2Warn` | ppO2 below limit |
| 4 | `kOTUWarn` | OTU accumulation |
| 8 | `kCNSWarn` | CNS% |
| 16 | `kIBCDN2Warn` | IBCD N2 (isobaric counter-diffusion) |
| 32 | `kIBCDHeWarn` | IBCD He |
| 64 | `kCCRWarn` | CCR loop warning |
| 128 | `kGasVolHardLimit` | Gas volume hard limit exceeded |
| 256 | `kGasVolSoftLimit` | Gas volume soft limit exceeded |

The highest set bit determines which `warn_colors[]` entry to use.  
Rows with warnings get colored background + contrasting text via `contrastColor()`.

---

## 7. Decompression Models Supported

From `Settings.modelString()`:

| Value | Constant | Model |
|---|---|---|
| 0 | `VPMA` | VPM (original) |
| 1 | `VPMB` | VPM-B |
| 2 | `VPMBE` | VPM-B/E (extended) |
| 3 | `VPMBFBO` | VPM-B/FBO (full bubble oxygenation) |
| 4 | `VPMB_GFS` | VPM-B + GFS (Gradient Factor Shallow) |
| 5 | `ZHLB_GF` | ZHL-B + Gradient Factors |
| 6 | `ZHLC_GF` | ZHL-C + Gradient Factors |

Default: `VPMModel = 1` (VPM-B).

---

## 8. Key Settings Parameters Passed to Engine

All settings are serialized to `vpm_config.data` (Java `ObjectOutputStream`) and reloaded at startup. The native engine reads them via `initDecoCalc`. Relevant fields:

| Field | Type | Default | Meaning |
|---|---|---|---|
| `VPMModel` | int | 1 (VPM-B) | Deco model selection (0–6) |
| `GFLo` | int | 30 | GF Low % (ZHL modes) |
| `GFHi` | int | 85 | GF High % (ZHL modes) |
| `GFS` | int | 90 | GF Shallow % (VPM-B+GFS) |
| `Metric` | bool | false | Units: true=metric, false=imperial |
| `WaterType` | int | 0 (Salt) | 0=salt, 1=fresh |
| `Alt` | int | 0 | Altitude index (→ elevationValue()) |
| `Step` | int | 0 | Stop depth step (index) |
| `Last` | int | 0 | Last stop depth index |
| `ppO2` | int | 4 | Max ppO2 index for deco (→ ppO2Swaps[]) |
| `ppO2Deep` | int | 3 | Max ppO2 index for deep stops |
| `ppO2ReallyDeep` | int | 2 | Max ppO2 index for really deep |
| `MaxO2` | int | 3 | Max ppO2 index for MOD |
| `ascent` | int | 7 | Ascent rate index (→ rateValue()) |
| `descent` | int | 14 | Descent rate index |

> **⚠️ CORRECTION — §8 table is incomplete on ascent/descent rates (confirmed June 2026 via screenshot):**
> The jadx decompile of `Settings.java` only surfaced a single `ascent` field and a single `descent`
> field. However, a screenshot of MultiDeco's actual "Descent / ascent rates" config screen shows
> **four independently adjustable fields** — Descent and three separate ascent-phase fields (Surface,
> Deco, Ascent) — each with its own dropdown. Default values confirmed from the running app:
> - **Descent:** 22 mpm (not the ~18 m/min / 60 ft/min implied by `rateValue(14, false)`)
> - **Surface ascent:** 9 mpm
> - **Deco ascent:** 9 mpm
> - **Ascent (deep):** 9 mpm
>
> The `Settings.java` decompile likely missed the other three rate fields (possibly named differently,
> stored as separate fields in a later version, or defined in a different class not captured by jadx).
> **Do not rely on the single `ascent`/`descent` fields in this table as a complete picture of
> MultiDeco's rate settings — use the screenshot-confirmed values above for the Item 6 preset
> implementation.** A follow-up read of the full decompiled `Settings.java` source (in `jadx_out/`
> if available) may identify the missing field names, but is not blocking.
| `OC_CCR` | int | 0 | 0=OC, 1=CCR |
| `CCRStart` | double | 0.7 | CCR start setpoint (ata) |
| `Extend` | bool | false | Extended deco stops |
| `ExtStop` | int | 5 | Extended stop time (min) |
| `O2Affect` | bool | false | O2 affects tissues |
| `OxyNarc` | bool | false | O2 narcotic (for END calc) |
| `surfInt` | int | -1 | Surface interval (min; -1=none) |
| `TwoWeeks` | int | 0 | Repetitive dive window |
| `bailactive` | bool | false | Bailout mode active |
| `bailModel` | int | 3 | Bailout deco model |
| `bailConserveGFLo` | int | 50 | Bail GFLo |
| `bailConserveGFHi` | int | 90 | Bail GFHi |

### ppO2Swaps lookup
```java
public static final float[] ppO2Swaps = {1.2f, 1.3f, 1.4f, 1.5f, 1.6f};
// Index 0→1.2, 1→1.3, 2→1.4, 3→1.5, 4→1.6 ata
```

### Last stop values
```java
// Imperial: 10, 15, 15, 20, 30 ft
// Metric: 3, 4.5, 5, 6, 9 m
static float lastStopValue(int i, boolean metric)
```

---

## 9. Pure-Java Tool Calculations (`tools_calc.java`)

These calculations are **not** handled by the native engine — they are pure Java:

| Tool code | Tool | Notes |
|---|---|---|
| 36 | Nitrox blending | Partial-pressure blending with Z-factor correction |
| 132 | Best mix | Max ppO2 optimization, optional He |
| 241 | EAD/MOD/END | EAD, MOD, END, narcotic depth calcs |
| 725 | Top-up blending | Top-up from partial fill |
| 752 | Trimix blending | Full trimix blending with He Z-factor |
| 787 | Gas density | Density in g/L; sea water / fresh water modes |
| 9999 | Tank capacity | Volume / pressure conversion |

Gas compressibility Z-factors are stored as lookup tables per 100 psi/bar steps:
- `O2ZFactor[41]`, `HeZFactor[41]`, `N2ZFactor[41]`, `AirZFactor[41]`
- Range: 0–4000 psi in 100 psi steps

---

## 10. License / Registration System

- License is checked server-side via RSA: `Android_RSA.rsaEncrypt()` → `https://www.hhssoftware.com/cgi-bin/android_install.cgi`
- The native `setPackage(apkPath)` reads the APK's embedded certificate/data for initial validation
- `m52ic(String)` / `m53rs(String, String)` are the native registration helpers (names obfuscated by jadx deobfuscation; originals were `ic` and `rs`)
- Unregistered users:
  - Cannot use trimix deco gases (contain `/`)
  - Cannot use trimix bottom gases
  - Cannot use O2 deco (100%)
  - Are subject to a "nag" delay timer that grows with install age (up to 30 min wait)

---

## 11. Implication for LSP D-Planner Integration

### How to replicate the engine call protocol
To call the native engine from your own code (if porting to desktop/web), replicate:

1. **Level string format:**  
   `"<depth_ft_or_m>, <time_min>, <O2pct>[/<Hepct>]"` (OC)  
   `"<depth>, <time>, <O2>/<He>, <setpoint_or_OC>"` (CCR)  
   Concatenate with `#`: `"40, 25, 21#"` etc.

2. **Deco string format:**  
   `"<O2>[/<He>][ <swap_depth><unit>]"` e.g. `"50 21m#100#"`

3. **Call sequence:**  
   `initDecoCalc(surfInt_minutes, levels, decos, maxtime)` → 0 on success  
   `decoCalc()` → 0 on success  
   Loop: `resultRow(i)` for `i` in `0..getResultRows()-1`  
   Also: `diveReport()` for gas summary, `getWarning(i)` for warnings

4. **Settings passed:** The native engine reads settings from the Settings object that loaded them from `vpm_config.data` at construction. There is no direct way to pass settings per-call — the settings object must be pre-configured before calling `initDecoCalc`.

### Key Constants for LSP D-Planner
- **Model integer mapping:** VPM-B=1, ZHL-B GF=5, ZHL-C GF=6 (matches engine enums)
- **GF defaults:** GFLo=30, GFHi=85
- **ppO2 max table:** `[1.2, 1.3, 1.4, 1.5, 1.6]` ata, default index=4 → **1.6 ata** for deco
- **Ascent rates:** ~~`rateValue(7, false)` = 15 ft/min (imperial default)~~ **CORRECTED (screenshot):** Three separate phase rates — Surface/Deco/Ascent — each defaulting to **9 mpm**; the single `rateValue(7)` field from `Settings.java` is incomplete.
- **Descent rate:** ~~`rateValue(14, false)` = 60 ft/min~~ **CORRECTED (screenshot):** **22 mpm** default.
- **Last stop:** `lastStopValue(0, false)` = **10 ft** (imperial default)
- **Stop step:** index 0 (smallest step)

---

## 12. File Structure Summary

```
com/hhssoftware/multideco/
├── multideco_main.java       ← central hub, CalcTask, launchResultActivity
├── multideco_level.java      ← add/edit bottom segment
├── multideco_deco.java       ← add/edit deco gas
├── multideco_config.java     ← settings screen
├── multideco_result.java     ← plan display, 7-column table
├── multideco_bail.java       ← CCR bailout
├── multideco_maxtime.java    ← max bottom time
├── multideco_bestmix.java    ← best mix tool
├── multideco_eadmod.java     ← EAD/MOD/END tools
├── multideco_about.java      ← version info
├── multideco_agree.java      ← EULA
├── multideco_registration.java ← license entry
├── multideco_toolslist.java  ← tools launcher
├── Settings.java             ← JNI bridge + settings persistence
├── tools_calc.java           ← pure-Java gas math
├── Gastank_setting.java      ← tank/RMV model
├── Theme_setting.java        ← dark/light theme
├── VersionCheck.java         ← remote version check
├── Android_RSA.java          ← RSA license verification
├── Identity.java             ← registration identity
├── C0347R.java               ← resource ID constants (R.java)
└── settank.java              ← tank setting helper
```

---

*Analysis performed on MultiDeco v2.26 APK (`com.hhssoftware.multideco`).  
Decompiled with jadx 1.5.1 from `classes.dex` (2,020 classes total, 20 app-package classes).*
