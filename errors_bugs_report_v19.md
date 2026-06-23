# LSP D-Planner+CCR — Errors & Bugs Report v19

**App version audited:** v2.30.24  
**Audit date:** 2026-06-21  
**Previous report:** errors_bugs_report_v18.md (v2.30.24 — 1 bug: BUG-75)  
**Audit tool:** audit.py — 346 checks, 0 failures  
**Scope:** Verification of BUG-75 (v18 report) + full deep audit of v2.30.24.

---

## Summary

BUG-75 found in v18 report is **not yet fixed** — still present in v2.30.24.  
Full deep audit finds **0 additional bugs** beyond BUG-75.

---

## BUG-75 Verification — Still Present

**Status:** ❌ Not yet fixed (present in v2.30.24 at commit `60fc6b6`)

`ccrDiluentSurfaceLpm()` line ~5958:

```js
const fr = computePSCRFractions(pSurf, bot.fO2, bot.fHe, runtimeMin, ccr);
const fO2Loop = Math.max(0.01, fr.fO2);
return (metRate / fO2Loop) * PSCR_DEFAULT_BYPASS_RATIO;  // ← wrong
```

The pSCR gas consumption formula is `(metRate / fO2Loop) × bypassRatio` but it should be
`metRate × bypassRatio`. The bypass ratio defines fresh gas flow as a multiple of metabolic
O₂ consumption — `fO2Loop` (the depleted loop O₂ fraction from `computePSCRFractions`) is
the *result* of that process, not an input that should scale it.

**Numerical impact (EAN32, 40 m, runtimeMin=20):**
- `computePSCRFractions(1.01325, 0.32, 0, 20, ccr)` → `fO2 ≈ 0.16` (depleted loop)
- Current: `(1.5 / 0.16) × 10 = 93.75 L/min`
- Correct: `1.5 × 10 = 15 L/min`
- **Error factor: ~6.25×** — Gas Plan shows ~6× too much diluent required

**Context — OC path comparison:**  
`return metRate / fO2Dil` on line 5960 is the correct formula for OC/CCR diluent flow
(volume of gas needed to supply `metRate` L/min O₂ from a gas with `fO2Dil` fraction).
The pSCR path incorrectly mirrors this structure but replaces `fO2Dil` with the output
loop fraction `fO2Loop` — a physically different quantity.

**Fix:**
```js
// Replace lines 5956–5958 with:
return metRate * PSCR_DEFAULT_BYPASS_RATIO;
// Optionally expose surface vs depth-adjusted variant in ccrGasLitres.
```

---

## Audit Scope — All Other Areas Clean

### CCR engine logic
- `computePSCRFractions`: correct metabolic depletion model ✅
- `getEffectivePpo2` pSCR branch: `fr.fO2 * pAmb`, floored at `PSCR_MIN_PPO2` ✅
- `vpmAccumPpo2` (9 call sites): correct OC/bailout fallback ✅
- `hCcrOnLoop` + `hCcrConfig` + phase-aware `headlessPpo2`: correct after BUG-73 fix ✅
- `ctxUseOCForPpo2(settings)` ReferenceError fix intact ✅
- `_zhlHeadless` preserved across `ZHLEngine.calculate()` re-entries ✅

### Gas plan / gas consumption
- BUG-75 aside, `ccrGasLitres` itself is correct: `sac × pAmb × durMin` where `sac` is
  in L/min — the error is only in the L/min value returned by `ccrDiluentSurfaceLpm` for pSCR ✅
- `sacDomToLpm` imperial conversion: correct for `sacBottom`/`sacDeco` ✅
- `addBailoutStressReserve`: correct depth distribution, `ccrSacStress` stays in L/min ✅
- `gpVolDisp` imperial conversion used in all gas display paths ✅
- `gpSizeL`/`gpPresBar`/`gpPresDisp` imperial conversions correct ✅

### Exports
- All export paths source `totalCNS/totalOTU` from engine results ✅
- Both engines now correct for CCR/pSCR headless OTU/CNS ✅

### UI / settings / persistence
- `appSettings.clear()` — all 19 app-owned keys cleared ✅
- Version sync: all four files at `2.30.24` ✅

### VPM vs Bühlmann parity
- Both engines route pSCR/CCR OTU/CNS through `getEffectivePpo2` ✅
- OTU and CNS formulae consistent across all engines ✅

### Regression suite
- `audit.py` 346 checks, 0 failures ✅
- `tests-pscr-otu-cns.html`, `tests-verify.html` section I, `ndlSettings()` NDL fix all intact ✅
- **Coverage gap:** No regression test for `ccrDiluentSurfaceLpm` pSCR gas flow value.
  A test asserting `ccrDiluentSurfaceLpm(40)` ≈ 15 L/min (not 93 L/min) would catch BUG-75.

---

## New Bugs Found

**None** (beyond BUG-75 which was already reported in v18 and remains unfixed).

---

## Open Bug

| Bug | Severity | Status |
|-----|----------|--------|
| BUG-75 | MEDIUM | ❌ Not yet fixed — `ccrDiluentSurfaceLpm` pSCR formula `(metRate/fO2Loop)×bypass` should be `metRate×bypass` |

---

## Carry-Over OC Main Bugs (out of scope for CCR repo)

| Bug | Description | Repo |
|-----|-------------|------|
| BUG-40 | Bühlmann emergency gas `sz` not converted cu ft→L (~line 9789) | LSP_D-planner |
| BUG-41 | `appSettings.clear()` only removes `lspDiveSettings_v3` (~line 16449) | LSP_D-planner |

---

## All CCR Repo Bugs — Cumulative Status

| Report | Version | Bugs | Status |
|--------|---------|------|--------|
| v1–v9 | early | BUG-01–50 | ✅ All fixed |
| v10 | v2.30.11 | BUG-51–56 | ✅ All fixed |
| v11 | v2.30.12 | BUG-57–62 | ✅ All fixed |
| v12–v13 | v2.30.13–15 | BUG-63 | ✅ Fixed |
| v14 | v2.30.15 | BUG-69–70 | ✅ Fixed |
| v15 | v2.30.16 | BUG-71 | ✅ Fixed |
| v16 | v2.30.17 | BUG-72 | ✅ Fixed |
| v17 | v2.30.23 | BUG-73–74 | ✅ Fixed |
| v18 | v2.30.24 | BUG-75 | ❌ Open |
| **v19** | **v2.30.24** | **0 new bugs** | **BUG-75 still open** |
