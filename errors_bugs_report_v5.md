# LSP D-Planner + CCR — Errors & Bugs Report v5

**Repo:** `Three-Cats-LSP/LSP_D-planner-CCR`  
**Version analysed:** v2.30.0 post-fix-4 (commit `2a96bbe`)  
**Date:** 2026-06-20  
**Audit result:** 271 checks, 0 failures  
**Scope:** Fifth verification pass covering the new commits: v4 bug fixes, full on-loop profile labels (889ec9a), Rebreather Adv. Settings with phase-aware setpoints (4cf2209), CCR diluent/bailout gas UI with MOD validation (2a96bbe). All 4 v4 bugs confirmed fixed. New bugs found below.

---

## CRITICAL

### BUG-27 — Bailout GF not applied: `gfL`/`gfH` declared `const` but reassigned in bailout branch — silently fails or throws TypeError

**File:** `index.html`  
**Location:** lines 9531–9532 (declarations) and 9566–9567 (assignments)

```js
// Line 9531-9532 — declared as const:
const gfL = mGF.low  / 100;
const gfH = mGF.high / 100;

// ... later, inside bailout branch (line 9566-9567):
mGF.low  = boLo;  mGF.high = boHi;   // ← mGF updated correctly
gfL = boLo / 100;                      // ← TypeError: assignment to constant variable
gfH = boHi / 100;                      // ← same
```

**Impact:** In sloppy mode the assignments silently fail — `gfL`/`gfH` retain the pre-bailout values (e.g. 0.30/0.85) while `mGF` is updated. In strict mode it throws `TypeError` and the entire schedule aborts. Either way, the configurable Bailout GF feature (lines 5631–5632, UI fields `ccrBailoutGfLow`/`ccrBailoutGfHigh`) has **zero effect** on the actual deco calculation. `gfL` and `gfH` drive every critical GF operation in the algorithm: first-stop search (`ceiling(tissues, gfL)` line 9756), GF interpolation (`gfAt()` lines 9810–9821), and all intermediate ceiling checks. The schedule silently runs with the configured plan GF instead of the intended bailout GF.

---

## HIGH

### BUG-28 — `getEffectiveSetpointAtDepth()` depth-based fallback returns `descSP` (0.7) at shallow last stops when called without `phase`

**File:** `index.html`  
**Location:** `getEffectiveSetpointAtDepth()` lines 5685–5686 (no-phase fallback path)

```js
// No phase given — depth-only heuristic:
const pAmb = (surfP || altSurfaceP) + depthM * BAR_PER_METRE;
if (pAmb <= decoSP + WATER_VAPOR) return descSP;   // ← triggers at 3m/6m last stops
return bottomSP;
```

With `decoSP=1.3` and `WATER_VAPOR=0.0627`: crossing depth = `(1.363 − 1.0) / 0.1 = 3.63 m`. So at the 3 m last stop (`pAmb=1.30`), `1.30 ≤ 1.363` is true → returns `descSP=0.7`.

**Affected callers (all called without `phase`):**
- `ppO2Check()` with CCR opts → line 7003: deco table ppO₂ display shows `0.70` at 3 m stop instead of `1.30`
- `vpmDisplayPpo2()` → line 7202: same wrong display in VPM table
- `getEffectivePpo2()` → line 5805: `Math.min(1.30, Math.max(0.70, 0.21×1.30))=0.70` — exported ppO₂ is 0.70
- `calcCNS()` → line 15796: CNS calculation uses ppO₂=0.70 for last stop, understating CNS/OTU by a large margin

**Impact:** Any CCR dive with `decoSP > lastStop×0.1 + 0.9` (i.e. decoSP higher than the ambient pressure at the last stop) will show grossly wrong ppO₂ in the deco table and export, and will calculate near-zero CNS contribution for the last stop.

---

### BUG-29 — VPM engine receives only `decoSetpoint` for the entire dive — bottom phase uses wrong setpoint

**File:** `index.html`  
**Location:** VPM `settings` object build line ~7093 (`...getCCRSettingsFromDOM()`) and VPM `levels` array line 7131

```js
levels = [{ depth: depthM, time: bt, o2: bottomO2pct, he: bottomHePct,
  setpoint: settings.setpoint,   // ← settings.setpoint = decoSP (e.g. 1.3)
  oc: settings.bailout,
}];
```

`getCCRSettingsFromDOM()` sets `settings.setpoint = decoSP` (the deco/high setpoint). The VPM engine uses `settings.setpoint` (and `levels[0].setpoint`) for **all** tissue loading — descent, bottom, and deco — with no phase distinction. There is no `bottomSetpoint` field read by the VPM engine.

**Impact:** For a CCR dive with bottomSP=1.2 and decoSP=1.3, the entire VPM dive is planned at SP=1.3 instead of SP=1.2 during bottom time. This overstates inspired ppO₂ during bottom phase → less inert gas loading → shorter deco than correct. For dives with larger SP differentials the error is proportionally larger.

---

### BUG-30 — Bailout gas MOD display and validation use `ccrBottomSetpoint` (1.2) instead of OC ppO₂ limit (`ppo2Bottom`, 1.4)

**File:** `index.html`  
**Location:** `getConfiguredBailoutMixes()` line ~5970 and deco gas MOD display line ~9289

```js
// getConfiguredBailoutMixes():
const activePpo2 = parseFloat(document.getElementById('ccrBottomSetpoint')?.value) || 1.4;
const modM = calcGasMODm(fracs.fO2, activePpo2);   // ← uses 1.2, not 1.4

// Deco gas MOD display (CCR mode):
const bailoutPpo2 = parseFloat(document.getElementById('ccrBottomSetpoint')?.value) || 1.4;
```

Bailout is open-circuit breathing. The correct ppO₂ limit for MOD calculation is the OC ppO₂ limit (`ppo2Bottom`, typically 1.4 bar), not the CCR on-loop bottom setpoint (1.2 bar).

**Example:** EAN50 bailout MOD at 1.2 bar = 14 m; at 1.4 bar = 18 m. The validation blocks schedule generation if no bailout gas covers the dive depth — with this bug, a valid EAN50 bailout for an 18 m dive is flagged as insufficient (MOD shown as 14 m).

---

## MEDIUM

### BUG-31 — Four Rebreather Adv. Settings fields stored and saved but never affect any calculation: `sacStress`, `sacDecoCcr`, `stressTimeMin`, `problemSolveMin`

**File:** `index.html`  
**Fields:** `ccrSacStress`, `ccrSacDeco`, `ccrStressTime`, `ccrProblemSolve`

All four fields are:
- Shown in the Rebreather Adv. Settings panel
- Read in `getCCRSettingsFromDOM()` into `sacStress`, `sacDecoCcr`, `stressTimeMin`, `problemSolveMin`
- Saved/loaded via `DECO_FIELDS` and preset system
- **Never read by `ccrDiluentSurfaceLpm()`, `addGas()`, `ccrGasLitres()`, or any deco engine function**

**Impact:** User configures Stress SAC (50 L/min), Deco SAC (25 L/min), Stress Time (10 min), and Problem Solve Time (3 min) — none of these affect gas consumption estimates or any other output. The gas plan always uses the main `sacDeco` field regardless. This is undocumented in the UI.

---

## LOW

### BUG-32 — pSCR circuit still shows Setpoint and Descent Setpoint input fields (now `ccrBottomSetpoint` and `ccrDescentSetpoint`) that are unused for pSCR

**File:** `index.html`  
**Location:** `toggleCircuitFields()` line ~5766

BUG-25 from report v4 was partially fixed by removing the old `ccrSetpointRow`, but the new fields (`ccrBottomSetpoint`, `ccrDecoSetpoint`) are inside the same collapsible panel which remains visible for all rebreather circuits. `getEffectiveSetpointAtDepth()` returns `0` immediately for pSCR (`if (ccr.circuit === 'pSCR') return 0`), so all three setpoint fields are silently unused when pSCR is selected.  
**Impact:** UI confusion — user adjusting setpoints on pSCR sees no effect. No label, tooltip, or visual indicator explains this.

---

## Summary Table

| # | Severity | Area | Description | Status |
|---|---|---|---|---|
| BUG-27 | CRITICAL | Bailout/GF | `gfL`/`gfH` declared `const` then reassigned — bailout GF silently has zero effect | FIXED |
| BUG-28 | HIGH | CCR/Display | Depth-based SP fallback returns `descSP=0.7` at 3 m last stop — wrong ppO₂ display, CNS, and export | FIXED |
| BUG-29 | HIGH | VPM/CCR | VPM engine uses `decoSetpoint` for entire dive — `bottomSetpoint` ignored, shorter deco than correct | FIXED |
| BUG-30 | HIGH | CCR/Gas UI | Bailout MOD uses CCR bottom SP (1.2) not OC ppO₂ limit (1.4) — valid bailout gases incorrectly blocked | FIXED |
| BUG-31 | MEDIUM | CCR/Gas plan | `sacStress`, `sacDecoCcr`, `stressTimeMin`, `problemSolveMin` stored but never used in any calculation | FIXED |
| BUG-32 | LOW | pSCR/UX | pSCR mode shows all CCR setpoint fields (bottom, deco, descent SP) which have zero effect on pSCR | FIXED |

---

## FIXED in this pass (2026-06-20)

### BUG-27 — Bailout GF `const gfL`/`gfH` reassignment

**Fix:** Declared `gfL` and `gfH` as `let` in `runDecoSchedule()` so bailout GF overrides apply to the Bühlmann engine.

### BUG-28 — `getEffectiveSetpointAtDepth()` depth fallback returned descent SP at shallow deco stops

**Fix:** No-phase fallback now steps descSP → bottomSP → decoSP by ambient pressure instead of returning descent SP at last stop depths.

### BUG-29 — VPM bottom phase used deco setpoint

**Fix:** VPM `levels[0].setpoint` uses `bottomSetpoint`; VPM `getEffectiveSetpoint()` passes full phase setpoints to `getEffectiveSetpointAtDepth()`.

### BUG-30 — Bailout MOD used CCR bottom SP instead of OC ppO₂ limit

**Fix:** Bailout mix MOD display and validation use `ppo2Bottom` via `getBailoutPpo2Limit()`. Diluent MOD still uses active loop setpoint.

### BUG-31 — Adv. Settings SAC/stress fields unused

**Fix:** `sacDecoCcr` used for OC bailout gas consumption; stress + problem-solving minutes reserve gas on primary bailout mix at bottom depth using `sacStress`.

### BUG-32 — pSCR setpoint fields visible

**Status:** Already fixed — setpoint rows hidden when `circuit !== 'CCR'` in `toggleCircuitFields()`.

