# LSP D-Planner + CCR — Errors & Bugs Report v2

**Repo:** `Three-Cats-LSP/LSP_D-planner-CCR`  
**Version analysed:** v2.30.0 post-fix (commit `6825330`)  
**Fix commit:** 2026-06-20 — all 6 bugs addressed  
**Audit result:** 271 checks, 0 failures  
**Scope:** Cross-check and verification pass after first report was fixed. All 12 prior bugs confirmed resolved. New bugs found below.

---

## Fix status (2026-06-20)

| # | Status | Fix summary |
|---|---|---|
| BUG-13 | **FIXED** | `renderVPMResults()` uses `vpmDisplayPpo2()` with CCR setpoint via `getEffectivePpo2` |
| BUG-14 | **FIXED** | `addGas()` detects `CCR …` labels; uses metabolic diluent rate instead of OC SAC |
| BUG-15 | **FIXED** | APK links and export footers point to `d-planner-ccr` |
| BUG-16 | **FIXED** | PWA install banner → "Install LSP D-Planner + CCR" |
| BUG-17 | **FIXED** | `calcCNS()` reads `fHe` from `getBottomGasFractions()` for pSCR trimix |
| BUG-18 | **FIXED** | In-app documentation, disclaimer, GitHub/APK labels updated to "+ CCR" |

---

## Original findings (post v1 fix baseline)

## HIGH

### BUG-13 — VPM deco table ppO₂ column shows diluent OC ppO₂, not setpoint (same class of bug as fixed BUG-03, now in VPM path)

**File:** `index.html`  
**Location:** VPM table rendering loop, line ~6928  
```js
const ppO2s = (o2pct / 100 * pAmbS).toFixed(2);
```
`o2pct` is parsed from `seg.gas` which is a diluent gas string (e.g. `"21/0"` for air). There is no CCR setpoint awareness in the VPM plan segment or the VPM table renderer. The `_ccrPpo2Opts` / updated `ppO2Check` fix applied to the Bühlmann path (BUG-03) was **not** applied to the VPM table.  
**Impact:** For any CCR dive planned with VPM-B or VPM-B/GFS, the PPO2 column in the deco table shows the diluent partial pressure (e.g. `1.07 bar` for air at 40 m) instead of the maintained setpoint (`1.30 bar`). This also affects the ppO₂ colour-coding threshold, export text, and PDF for VPM mode.  
**Note:** VPM engine internal CNS/OTU tracking correctly uses `ctx.currentSP` — only the *display* and export ppO₂ is wrong.

---

### BUG-14 — CCR on-loop gas consumption calculated as OC SAC — overstated by ~10×

**File:** `index.html`  
**Location:** `addGas()` calls at lines ~10027, ~10052, ~10069 (Bühlmann deco stop rendering loop)  
```js
addGas(s.gas, s.depth, stepDur, sacDeco);  // s.gas = "CCR AIR" on-loop stops
```
`addGas()` computes `litres = sac × P_amb × duration`. For CCR on-loop stops this treats the diver as consuming diluent at the full SAC rate. In reality a CCR diver on-loop is re-breathing; diluent consumption is only the oxygen metabolised (~0.8–1.0 L/min at rest), not the full SAC (~15 L/min deco SAC).  
**Impact:** Gas consumption for the diluent cylinder will be shown as roughly 15–20× too high for on-loop deco stops (depending on depth and SAC setting). Rule-of-thirds / half calculations based on this will be wildly conservative and may falsely flag the dive as having insufficient diluent.  
**Note:** Bailout (OC) segments would correctly use SAC — this bug only affects on-loop segments.

---

## MEDIUM

### BUG-15 — APK download link and export footer/PDF URL point to OC planner, not CCR

**File:** `index.html`  
**Locations:**  
- Line ~3292: `href="https://threecats-lsp.com/d-planner/download.html"` — APK download icon in footer  
- Line ~3329: same URL, APK download icon in info panel  
- Line ~13293 (gas plan text export footer): `'LSP D-Planner — threecats-lsp.com/d-planner'`  
- Line ~13898 (all export text footer): `'https://threecats-lsp.com/d-planner/'`  

**Impact:** Users tapping "Download APK" from within the CCR app are sent to the OC planner's download page and may install the wrong APK. Export text and gas plan shares identify the app as the OC planner, causing confusion if shared.

---

### BUG-16 — PWA install banner says "Install LSP D-Planner", missing "+ CCR"

**File:** `index.html` line ~17549  
```js
'<div ...>Install LSP D-Planner</div>'
```
**Impact:** Minor branding inconsistency — user sees "LSP D-Planner" in the PWA install prompt instead of "LSP D-Planner + CCR". On a device with both the OC and CCR PWA installed, the names shown during install would be indistinguishable.

---

### BUG-17 — `calcCNS()` hardcodes `fHe = 0` → pSCR + Trimix diluent gives wrong ppO₂ in CNS tab

**File:** `index.html` line ~15328  
```js
const fHe = 0;
```
`getEffectivePpo2()` is called with `fHe=0` always. For pSCR mode, `computePSCRFractions()` receives `fHe=0` regardless of the actual diluent helium fraction. If the user enters a Trimix diluent O₂% (e.g. 21% from Tx21/35) but the He fraction is ignored, the pSCR ppO₂ calculation treats the inert fraction as 100% N₂, which overstates N₂ in the loop and produces a higher computed fO₂ after scrubbing, giving a slightly different (wrong) ppO₂.  
**Impact:** Affects only the standalone CNS tab with pSCR + Trimix diluent. The CNS tab has no He% input field to fix this without a UI addition.

---

### BUG-18 — Several in-app text strings still say "LSP D-Planner" without "+ CCR"

**File:** `index.html`  
**Locations:**
- Line ~2826: Documentation panel heading: `"LSP D-Planner Documentation"`
- Line ~2838: Support text: `"LSP D-Planner is free and open-source..."`
- Line ~3235: Disclaimer text: `"LSP D-Planner and the decompression schedules it produces..."`
- Line ~3290: GitHub link label: `"LSP D-Planner · Open Source on GitHub"`
- Line ~3330: Icon `alt` text: `alt="LSP D-Planner"` (the home screen icon in the footer)

**Impact:** Cosmetic — the product is presented under its OC name in several visible UI locations.

---

## Summary Table

| # | Severity | Area | Description |
|---|---|---|---|
| BUG-13 | HIGH | VPM/CCR display | VPM deco table ppO₂ shows diluent ppO₂ not setpoint |
| BUG-14 | HIGH | CCR/Gas plan | On-loop gas consumption calculated at full OC SAC — ~10–20× overstated |
| BUG-15 | MEDIUM | Branding/Links | APK download links and export footer URLs point to OC planner |
| BUG-16 | MEDIUM | Branding/PWA | PWA install banner missing "+ CCR" |
| BUG-17 | MEDIUM | pSCR/Trimix | `calcCNS()` hardcodes `fHe=0` — Trimix pSCR ppO₂ wrong in CNS tab |
| BUG-18 | LOW | Branding | Multiple in-app text strings still say "LSP D-Planner" without "+ CCR" |

