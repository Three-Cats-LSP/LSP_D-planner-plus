# LSP D-Planner + CCR — Errors & Bugs Report v3

**Repo:** `Three-Cats-LSP/LSP_D-planner-CCR`  
**Version analysed:** v2.30.0 post-fix-2 (commit `e001a09`)  
**Fix commit:** 2026-06-20 — all 4 report bugs + runtime TDZ crash fixed  
**Audit result:** 271 checks, 0 failures  
**Scope:** Third verification pass. All 6 bugs from report v2 confirmed fixed. New bugs found below.

---

## Fix status (2026-06-20)

| # | Status | Fix summary |
|---|---|---|
| BUG-19 | **FIXED** | VPM gas consumption uses shared `ccrGasLitres()` / `isCcrDiluentGasLabel()` for on-loop bottom diluent |
| BUG-20 | **FIXED** | Deco + gas-plan PDF headers → `LSP D-PLANNER + CCR` |
| BUG-21 | **FIXED** | Removed dead `seg.setpoint === 0` branch from `vpmDisplayPpo2()` |
| BUG-22 | **FIXED** | PDF filename prefix → `LSP_CCR_` |
| — | **FIXED** | Generate Schedule crash: `zhlLoadLinear`/`zhlLoadConst` used `rt` before `let rt` init — now uses `diveRuntimeMin` |

---

## Original findings (post v2 fix baseline)

## HIGH

### BUG-19 — VPM gas consumption still uses OC SAC for on-loop CCR segments

**File:** `index.html`  
**Location:** VPM gas consumption block, line ~7033  
```js
gasConsVPM[gasKey] = (gasConsVPM[gasKey] || 0) + sac * absP * durMin;
```
The Bühlmann gas consumption path was fixed (BUG-14) with `isCcrOnLoopGasLabel()` and `ccrDiluentSurfaceLpm()`. That fix was **not** applied to the VPM gas consumption block, which reads directly from rendered table cells and always applies `sac × P_amb × duration` regardless of circuit.  

In the VPM table the Mix column shows the diluent label (e.g. `AIR`) not `CCR AIR`, so `isCcrOnLoopGasLabel()` would not match anyway — a different detection approach is needed for the VPM path (checking `_vpmOnLoop` and whether the gas is the bottom gas).  

**Impact:** On a CCR dive with VPM-B/VPM-B+GFS, diluent consumption is shown as full deco SAC × depth-pressure × time — typically 10–20× the realistic value. Rule-of-thirds / sufficiency check will falsely flag the dive as having insufficient diluent.

---

## MEDIUM

### BUG-20 — PDF header says `LSP D-PLANNER`, missing `+ CCR`

**File:** `index.html` line ~16139  
```js
doc.text('LSP D-PLANNER', ML, 5.5);
```
**Impact:** Every exported PDF is branded as "LSP D-PLANNER" in the header. If a CCR diver shares or files a PDF plan, it is indistinguishable from an OC plan header. Should read `LSP D-PLANNER + CCR`.

---

### BUG-21 — Dead code branch in `vpmDisplayPpo2`: `seg.setpoint === 0` can never be true

**File:** `index.html` line ~6852  
```js
if (_vpmOnLoop && seg && seg.setpoint === 0 && _vpmCcr.circuit === 'CCR') {
  return ppO2Check(depthM, fN2, fHe);  // falls back to OC ppO2
}
```
VPM plan segments (`appendPlan`) never store a `setpoint` field — `seg.setpoint` is always `undefined`. `undefined === 0` is `false` in JavaScript, so this branch never executes. The intent (fall back to OC ppO₂ when below setpoint crossover) is never triggered.  

**Impact:** The branch is dead code — no wrong output currently, because the main path at line 6855 (`_vpmOnLoop` true without the `setpoint===0` guard) correctly calls `getEffectiveSetpointAtDepth()` which already handles the descent-SP crossover. However the dead branch is misleading and could mask a real future bug if someone adds `setpoint` to plan segments expecting this guard to work.

---

### BUG-22 — PDF filename not branded for CCR (`LSP_…` not `LSP_CCR_…`)

**File:** `index.html` line ~16121  
```js
const fileName = `LSP_${isoDate}_Deco_${depthVal}${du}_${btVal}min_${algoTag}.pdf`;
```
**Impact:** PDF files saved from the CCR version are named identically to those from the OC version. A diver with plans from both apps in the same folder cannot distinguish them by filename.

---

## Summary Table

| # | Severity | Area | Description |
|---|---|---|---|
| BUG-19 | HIGH | VPM/Gas plan | VPM gas consumption uses OC SAC for on-loop CCR segments — same as fixed BUG-14 but unfixed in VPM path |
| BUG-20 | MEDIUM | PDF/Branding | PDF header says `LSP D-PLANNER` — missing `+ CCR` |
| BUG-21 | MEDIUM | VPM/Code quality | Dead code branch `seg.setpoint === 0` in `vpmDisplayPpo2` — can never fire |
| BUG-22 | LOW | PDF/Branding | PDF filename uses `LSP_` prefix same as OC version — no CCR distinction |

