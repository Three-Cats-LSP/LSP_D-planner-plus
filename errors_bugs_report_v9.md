# LSP D-Planner + CCR — Errors & Bugs Report v9

**Repo:** `Three-Cats-LSP/LSP_D-planner-CCR`  
**Version analysed:** v2.30.9 (commit `a96e77b`)  
**Date:** 2026-06-21  
**Scope:** Ninth verification pass. Full cross-check of ALL prior reports v1–v8 (BUG-01 through BUG-42) plus new CCR-specific analysis. Confirms fix status of every prior bug, identifies carry-overs, and reports new findings.

---

## Prior bug fix verification — all reports v1 through v8

| # | Reported | Area | Fix status in v2.30.9 |
|---|----------|------|----------------------|
| BUG-01 | v1 | Android versionCode/versionName | ✅ Fixed |
| BUG-02 | v1 | Android SDK versions | ✅ Fixed |
| BUG-03 | v1 | Bühlmann deco table ppO₂ shows diluent not setpoint | ✅ Fixed |
| BUG-04 | v1 | `_scrRuntimeMin` never assigned in VPM path — pSCR O₂=0 | ✅ Fixed |
| BUG-05 | v1 | `sw.js` caches `/LSP_D-planner/` paths — offline broken | ✅ Fixed |
| BUG-06 | v1 | `getEffectiveSetpointAtDepth` called without `surfP` | ✅ Fixed |
| BUG-07 | v1 | `ccr.fHe` not a valid field — Trimix pSCR He ignored in `getEffectivePpo2` | ✅ Fixed |
| BUG-08 | v1 | CNS tab computes OC ppO₂ — no CCR setpoint integration | ✅ Fixed |
| BUG-09 | v1 | Near-zero CCR test coverage in main test suites | ✅ Fixed |
| BUG-10 | v1 | `manifest.json` missing 512×512 icon | ✅ Fixed |
| BUG-11 | v1 | `download.html` alt text missing `+ CCR` | ✅ Fixed |
| BUG-12 | v1 | Test page titles not updated for CCR branding | ✅ Fixed |
| BUG-13 | v2 | VPM deco table ppO₂ shows diluent not setpoint | ✅ Fixed |
| BUG-14 | v2 | On-loop gas consumption uses full OC SAC (~10–20× overstated) | ✅ Fixed |
| BUG-15 | v2 | APK download URLs point to OC planner | ✅ Fixed |
| BUG-16 | v2 | PWA install banner missing `+ CCR` | ✅ Fixed |
| BUG-17 | v2 | `calcCNS()` hardcodes `fHe=0` — Trimix pSCR CNS wrong | ✅ Fixed |
| BUG-18 | v2 | Multiple UI strings still say `LSP D-Planner` without `+ CCR` | ✅ Fixed |
| BUG-19 | v3 | VPM gas consumption uses OC SAC for on-loop segments | ✅ Fixed |
| BUG-20 | v3 | PDF header says `LSP D-PLANNER` — missing `+ CCR` | ✅ Fixed |
| BUG-21 | v3 | Dead code branch `seg.setpoint === 0` in `vpmDisplayPpo2` | ✅ Fixed |
| BUG-22 | v3 | Main deco PDF filename uses `LSP_` not `LSP_CCR_` | ✅ Fixed (main deco PDF only — see BUG-49) |
| BUG-23 | v4 | Dive graph ceiling overlay uses OC tissue loading | ✅ Fixed |
| BUG-24 | v4 | Multi Dive Day Plan uses OC air loading | ✅ Fixed |
| BUG-25 | v4 | pSCR circuit shows CCR setpoint UI fields that are unused | ✅ Fixed |
| BUG-26 | v4 | Multi Dive export header missing `+ CCR` | ✅ Fixed |
| BUG-27 | v5 | Bailout GF: `gfL`/`gfH` declared `const` then reassigned — zero effect | ✅ Fixed (`let` at line 9631–9632) |
| BUG-28 | v5 | SP depth fallback returns `descSP=0.7` at 3 m last stop | ✅ Fixed |
| BUG-29 | v5 | VPM engine uses `decoSetpoint` for entire dive — `bottomSetpoint` ignored | ✅ Fixed (`levels[0].setpoint = bottomSetpoint` at line 7220) |
| BUG-30 | v5 | Bailout MOD uses CCR bottom SP (1.2) not OC ppO₂ limit (1.4) | ✅ Fixed (`getBailoutPpo2Limit()` used throughout) |
| BUG-31 | v5 | `sacStress`, `sacDecoCcr`, `stressTimeMin`, `problemSolveMin` stored but never used | ✅ Fixed |
| BUG-32 | v5 | pSCR mode shows all CCR setpoint fields with zero effect | ✅ Fixed |
| BUG-33 | v6 | VPM deco cylinder lookup uses wrong DOM IDs (`decoGas1Mix`) | ✅ Fixed (`dg1Mix`/`dg2Mix`) |
| BUG-34 | v6 | Stress reserve picks `mixes[0]` without depth check | ✅ Fixed (`getBailoutReserveMixLabel()`) |
| BUG-35 | v6 | VPM ignores `sacDecoCcr` for bailout deco gases | ✅ Fixed (`resolveCcrSacForGas()`) |
| BUG-36 | v6 | VPM has no stress/problem-solve bailout reserve | ✅ Fixed |
| BUG-37 | v7 | Imperial emergency gas: cylinder size not converted cu ft → L | ✅ Fixed (both VPM and Bühlmann blocks use `szRaw * 28.3168`) |
| BUG-38 | v7 | `getBailoutReserveMixLabel` uses CCR SP (1.2) not OC ppO₂ limit | ✅ Fixed (`getBailoutPpo2Limit()`) |
| BUG-39 | v7 | `package.json` and `build.gradle` not bumped after version bump | ✅ Fixed (all files at `2.30.9`) |
| BUG-40 | v8 | Bühlmann emergency gas capacity omits cu ft → L conversion | ✅ Fixed in CCR (line 10700); ❌ NOT back-ported to OC main |
| BUG-41 | v8 | `appSettings.clear()` removes wrong key (`v3` only) | ✅ Fixed in CCR; ❌ NOT back-ported to OC main |
| BUG-42 | v8 | `_restoreFields()` restores every field twice, firing ~120 change events | ⚠️ **Still present in both repos** (see section D) |

---

## A — HIGH (new)

### BUG-43 — `ccrDiluentSurfaceLpm()` and `computePSCRFractions()` fall back to 0.85 L/min; DOM default is 1.5 L/min

**File:** `index.html`  
**Location:** `ccrDiluentSurfaceLpm()` line ~5939; `computePSCRFractions()` line ~5754

```js
// ccrDiluentSurfaceLpm():
const metRate = ccr.scrMetabolicO2 || 0.85;   // ← fallback 0.85 L/min

// computePSCRFractions():
const metO2 = ccr.scrMetabolicO2 || 0.85;     // ← same fallback

// getCCRSettingsFromDOM() — DOM default:
parseFloat(document.getElementById('ccrMetabolicO2')?.value) || ... || 1.5;
// DECO_FIELDS default also '1.5'
```

If `ccr.scrMetabolicO2` is falsy (0, null, undefined — e.g. headless mode or a preset load path where the field was not saved), both functions use `0.85` instead of the intended default of `1.5`. This is a 43% underestimate of O₂ consumption in those code paths.

**Impact:** Diluent gas consumption and pSCR loop O₂ fraction both ~43% below the intended default rate in headless/edge cases.

---

### BUG-44 — `validateCcrGasConfiguration()` uses hidden `ccrBottomSetpoint` (stuck at 1.2 bar) as ppO₂ limit for pSCR diluent MOD check

**File:** `index.html`  
**Location:** `validateCcrGasConfiguration()` lines ~6082–6085

```js
const activePpo2 = parseFloat(document.getElementById('ccrBottomSetpoint')?.value)
  || parseFloat(document.getElementById('ppo2Bottom')?.value) || 1.4;
const diluentMod = calcGasMODm(bot.fO2, activePpo2);
```

In pSCR mode, `ccrBottomSetpoint` is hidden (`display:none` — the SP rows are only shown when `isCCR`). The field retains its default value of `1.2 bar`. The diluent MOD check therefore runs against 1.2 bar in pSCR mode instead of the correct OC ppO₂ limit (`ppo2Bottom`, default 1.4 bar).

**Example:** Air diluent: MOD at 1.2 bar = 50 m, MOD at 1.4 bar = 56 m. A 52 m pSCR dive with air diluent falsely triggers a "Diluent MOD shallower than dive depth" error.

**Impact:** False validation errors in pSCR mode; valid pSCR plans incorrectly blocked.

---

## B — MEDIUM (new)

### BUG-45 — Gas Plan diluent cylinder never cross-checked vs plan consumption in CCR/pSCR mode

**File:** `index.html`  
**Location:** `calcGasPlan()` / `gpRequiredFor()` lines ~13545–13560

In CCR on-loop mode, consumed gas is stored under the `loopMixLabelFor()` key (e.g. `"CCR Air"`). The Gas Plan tab calls `gpRequiredFor(botLabel)` with the raw diluent label (e.g. `"AIR"`). The key never matches in `_lastGasConsumed`, so `gpRequiredFor()` always returns `null` — sufficiency always shows "run plan" for the diluent row in CCR/pSCR mode.

**Impact:** Diluent cylinder sufficiency is never validated against actual plan consumption in CCR/pSCR mode — the most safety-critical gas check for rebreather diving is silently skipped.

---

### BUG-46 — `ccrDiluentSurfaceLpm()` ignores depth — diluent consumption modelled at surface-equivalent rate only

**File:** `index.html`  
**Location:** `ccrGasLitres()` line ~5963; `ccrDiluentSurfaceLpm()` line ~5937

```js
function ccrGasLitres(label, depthM, durMin, sac) {
  if (isCcrDiluentGasLabel(label)) return ccrDiluentSurfaceLpm() * durMin;  // depth ignored
  ...
}
```

Diluent consumption is returned as `surface_L/min × duration`. At 40 m the ambient pressure is ~5 bar, so the actual cylinder draw is ~5× higher. This is a modelling simplification from the initial implementation.

**Impact:** Diluent gas requirement shown in Gas Plan substantially underestimated for dives deeper than ~20 m (~5× at 40 m).

---

## C — LOW (new and carry-over)

### BUG-47 — `<meta name="description">` still has OC app description

**File:** `index.html` line 17

```html
<meta content="Professional dive planner with Rec NDL tables and Bühlmann ZH-L16C decompression algorithm." name="description"/>
```

No mention of CCR, pSCR, or rebreather planning. Affects PWA install metadata, Google snippets, and link previews.

---

### BUG-48 — `apple-mobile-web-app-title` is `"D-Planner"` not `"D-Planner+CCR"`

**File:** `index.html` line 14

```html
<meta content="D-Planner" name="apple-mobile-web-app-title"/>
```

`manifest.json` correctly sets `"short_name": "D-Planner+CCR"` and `<title>` is correct, but the iOS-specific meta tag is unchanged. On iOS, the PWA home screen icon label reads "D-Planner" — identical to the OC version.

---

### BUG-49 — Gas Plan PDF and Emergency PDF filenames still use `LSP_` prefix (not `LSP_CCR_`)

**File:** `index.html`  
**Locations:**
- Gas Plan PDF: line ~14000 — `` `LSP_${isoDate}_GasPlan_${gp.rule}.pdf` ``
- Emergency PDF: line ~15507 — `` `LSP_${isoDate}_Emergency_${depth}${du}_${bt}min_${scenarioName}.pdf` ``

BUG-22 (v3) fixed the main deco PDF filename (now `LSP_CCR_…`). Gas Plan PDF and Emergency contingency PDF were not updated.

**Impact:** These two PDF types are indistinguishable by filename from OC app output.

---

### BUG-50 — CNS text export header says `LSP D-PLANNER - CNS O2 TRACKER` (missing `+ CCR`)

**File:** `index.html` line ~14439

```js
lines.push('LSP D-PLANNER - CNS O2 TRACKER');
```

BUG-18 (v2) fixed the main visible UI branding strings. The CNS tab's text export header was not updated.

**Impact:** CNS export text file is branded as the OC version.

---

## D — LSP_D-planner (main, v2.20.21) — Carry-over bugs NOT back-ported

| Bug | Status in CCR v2.30.9 | Status in OC main v2.20.21 |
|-----|-----------------------|---------------------------|
| BUG-40 — Bühlmann emergency gas `sz` not converted cu ft → L | ✅ Fixed (line 10700) | ❌ Still present (line ~9789 — raw `sz` × bar) |
| BUG-41 — `appSettings.clear()` removes only `lspDiveSettings_v3` | ✅ Fixed (removes v6+v3+v2+v1) | ❌ Still present (line ~16449) |
| BUG-42 — `_restoreFields()` fires `checkAndRestore` twice per field | ⚠️ Still present in CCR (line ~17456) | ❌ Still present in OC main (line ~16442) |

**BUG-42 detail:** Each field fires a `change` event twice on every settings restore and page load (immediate + 100ms `setTimeout`), generating ~120 change events across all `DECO_FIELDS`. Was reported fixed in v8 but the deferred second pass is still present in both repos.

---

## Summary — new bugs only

| # | Severity | Repo | Area | Description |
|---|----------|------|------|-------------|
| BUG-43 | HIGH | CCR | pSCR/CCR gas | `ccrDiluentSurfaceLpm()` / `computePSCRFractions()` fallback 0.85 L/min vs DOM default 1.5 — 43% underestimate |
| BUG-44 | HIGH | CCR | pSCR validation | `validateCcrGasConfiguration()` uses hidden `ccrBottomSetpoint` (1.2) for pSCR MOD check; should use `ppo2Bottom` |
| BUG-45 | MEDIUM | CCR | Gas Plan | Diluent cylinder never cross-checked vs plan in CCR/pSCR (`AIR` vs `CCR Air` label mismatch) |
| BUG-46 | MEDIUM | CCR | Gas Plan | Diluent consumption depth-independent — underestimates ~5× at 40 m |
| BUG-47 | LOW | CCR | Metadata | `<meta name="description">` still has OC text — no CCR/pSCR mention |
| BUG-48 | LOW | CCR | iOS PWA | `apple-mobile-web-app-title` is `"D-Planner"` not `"D-Planner+CCR"` |
| BUG-49 | LOW | CCR | PDF files | Gas Plan PDF and Emergency PDF filenames use `LSP_` not `LSP_CCR_` |
| BUG-50 | LOW | CCR | CNS export | CNS text export header missing `+ CCR` |
| BUG-40 | HIGH | OC main | Gas plan/Imperial | Bühlmann emergency gas `sz` not converted (fixed in CCR, not back-ported) |
| BUG-41 | MEDIUM | OC main | Settings | `appSettings.clear()` removes only `v3` key (fixed in CCR, not back-ported) |
| BUG-42 | LOW | Both | Settings/Perf | `_restoreFields()` fires `change` event twice per field on every load (both repos) |
