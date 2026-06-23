# Errors & Bugs Report — v28
**Audit date:** 2026-06-21  
**Branch/commit:** `a17f668` (main, HEAD)  
**Version:** v2.30.30  
**Scope:** Post-release delta audit — changes introduced in commit `a17f668`  
("Release v2.30.30: circuit-aware exports, PDF fixes, changelog")  
**Prior baseline:** v27_RELEASE full app audit — 383 checks, 0 bugs, RELEASE READY

---

## Summary

| Item | Result |
|------|--------|
| `audit.py` checks | 381 passed, **2 failed** (stale tests — see below) |
| New functions audited | `isOcExportMode()`, `getDecoPlanTitle()`, `getExportCircuitTag()` ✅ |
| Export path regressions | None ✅ |
| PDF ⚠ unicode change | Correct ✅ |
| `buildExportText()` hardcoded OC title | Correct ✅ |
| Filename dynamic prefix | Correct ✅ |
| `buildMessengerText()` `_msgGasHdr` ordering | Correct ✅ |
| `dev/validate_pscr_e2e.py` | Script structure valid; Playwright not installed in CI sandbox (expected) ✅ |
| `CHANGELOG.md` | Accurate — one stale audit-count claim (see BUG-85) |
| New bugs found | **1** (BUG-85) |

---

## BUG-85 — audit.py BUG-49 tests are stale after filename refactor

**Severity:** Low (test suite false-failure; no runtime impact)  
**File:** `audit.py`, lines 2208–2215  
**Status:** OPEN

### Description

The BUG-49 regression tests in `audit.py` (GROUP 44) check for the hardcoded string
`LSP_CCR_${isoDate}_GasPlan_` and `LSP_CCR_${isoDate}_Emergency_` in `index.html`.

Commit `a17f668` intentionally replaced those hardcoded prefixes with a dynamic pattern:

```javascript
// Gas Plan PDF (line 14254)
const fileName = `LSP_${getExportCircuitTag()}_${isoDate}_GasPlan_${gp.rule}.pdf`;

// Emergency PDF (line 15761)
const fileName = `LSP_${getExportCircuitTag()}_${isoDate}_Emergency_${depth}...`;

// Main Deco PDF (line 16930)
const fileName = `LSP_${getExportCircuitTag()}_${isoDate}_Deco_...`;
```

The old static string `LSP_CCR_${isoDate}_GasPlan_` no longer exists in `index.html`,
so both audit checks fail with:

```
✗ Gas Plan PDF filename still uses LSP_ prefix (BUG-49)
✗ Emergency PDF filename still uses LSP_ prefix (BUG-49)
```

This is a false failure — the filenames are more correct now (circuit-aware), not worse.
The audit tests need to be updated to match the new dynamic pattern.

**Fix needed in `audit.py`:**

```python
# Replace GROUP 44 checks (lines ~2208–2215) with:

if "LSP_${getExportCircuitTag()}_${isoDate}_GasPlan_" in js:
    ok("Gas Plan PDF filename uses dynamic circuit tag (BUG-49 updated)")
else:
    fail("Gas Plan PDF filename does not use getExportCircuitTag() (BUG-49)")

if "LSP_${getExportCircuitTag()}_${isoDate}_Emergency_" in js:
    ok("Emergency PDF filename uses dynamic circuit tag (BUG-49 updated)")
else:
    fail("Emergency PDF filename does not use getExportCircuitTag() (BUG-49)")
```

---

## Audit Detail — Changed Areas

### 1. New helpers: `isOcExportMode()`, `getDecoPlanTitle()`, `getExportCircuitTag()` ✅

All three functions are logically correct:

- `isOcExportMode(ccr)`: accepts an optional pre-built CCR config object; falls back cleanly
  to `getCCRSettingsFromDOM()` when no arg is passed. Returns `true` when
  `circuit === 'OC'` or bailout is on. Bailout DOM read uses
  `ccrBailoutToggle.value === 'on'`, consistent with every other bailout read in the
  codebase (lines 6034, 5703). No issue.

- `getDecoPlanTitle(ccr)`: thin wrapper around `isOcExportMode`. Returns
  `'DECO PLAN (OC)'` or `'DECO PLAN (CCR)'`. Correct.

- `getExportCircuitTag(ccr)`: returns `'OC'` or `'CCR'`. Matches title logic. Correct.

- All three receive `d` (the result of `buildDecoPlanHeaderData()`) from their callers,
  so they never need to call `getCCRSettingsFromDOM()` redundantly in export paths. ✅

### 2. `buildDecoPlanHeaderLines()` — title update ✅

`lines[0]` is now `getDecoPlanTitle(d)` where `d = buildDecoPlanHeaderData()`.
`d` carries `.circuit` and `.ccrBailout`, so `isOcExportMode` resolves from the
pre-built object, not the DOM. No regression.

### 3. `renderDecoPlanHeaderHtml()` — on-screen banner title ✅

`getDecoPlanTitle(data)` called inside the HTML template. Same `data` object as the
rest of the function. Consistent with text export path.

### 4. `drawDecoPlanBannerPdf()` — `'!'` → `'\u26A0'` (⚠) ✅

```javascript
doc.text(hasDeco ? '\u26A0' : 'OK', boxX + padX, cy);
```

The font is `DejaVuSans` (loaded for PDF). DejaVuSans covers U+26A0 (WARNING SIGN ⚠)
in its standard character set. The change from ASCII `'!'` is correct and will render
properly in jsPDF with the embedded DejaVuSans font. No issue.

`getDecoPlanTitle(data)` is used on the next line for the title — same `data` object
passed into the function. No regression.

### 5. `buildExportText()` recreational branch — hardcoded `'DECO PLAN (OC)'` ✅

```javascript
lines.push('DECO PLAN (OC)');  // line ~14322
```

This branch is only reached for the recreational planner, which is always OC — there is
no CCR mode in recreational planning. The hardcode is intentional and correct.
No issue.

### 6. Filename prefix — `LSP_${getExportCircuitTag()}_` (3 PDFs) ✅

- Gas Plan PDF (line 14254): `LSP_${getExportCircuitTag()}_${isoDate}_GasPlan_${gp.rule}.pdf` ✅
- Emergency PDF (line 15761): `LSP_${getExportCircuitTag()}_${isoDate}_Emergency_...pdf` ✅
- Main Deco PDF (line 16930): `LSP_${getExportCircuitTag()}_${isoDate}_Deco_...pdf` ✅

All three call `getExportCircuitTag()` with no argument, so the function reads the DOM at
export time. Circuit state at that point matches the active plan. Correct.

### 7. `buildMessengerText()` — `_msgGasHdr` declaration moved earlier ✅

`_msgGasHdr = buildDecoPlanHeaderData()` is now declared at line ~15085,
before its first use at line 15088 (`getDecoPlanTitle(_msgGasHdr)`).
All subsequent uses of `_msgGasHdr` (lines 15102–15111) are downstream. No TDZ issue.

### 8. UI label: `"🔄 REBREATHER"` → `"🔄 DIVE TYPE"` ✅

Cosmetic rename only. No logic changes.

---

## New Files

### `dev/validate_pscr_e2e.py` (416 lines) ✅

Script structure is valid Python. Imports are standard library + `playwright`.
When Playwright is not installed (as in the CI/audit sandbox), the script catches the
`ImportError` and falls back gracefully. The `run_audit()` helper calls `audit.py` as a
subprocess and reports pass/fail counts. The pSCR reference math (OTU, metabolic O₂,
gas depleted-loop calculation) correctly reflects the formulae verified in BUG-75.
No issues found.

**Note:** Playwright is not installed in the sandbox environment where `audit.py` runs.
The script is designed to be run locally with a browser context or a Playwright-enabled
CI environment. No action needed.

### `CHANGELOG.md` (762 lines) ✅ with note

Content is accurate. The v2.30.30 entry correctly lists all 84 bugs, the fix categories,
and the new export helper functions.

**Minor inaccuracy:** The v2.30.30 intro line states **"381/381 `audit.py` checks passing"**.
After the filename refactor in this same commit, the actual result is **381 passed, 2 failed**
(the stale BUG-49 tests). This is tracked as BUG-85 above and will be corrected once
`audit.py` is updated.

---

## Regression Check — All Previously Verified Subsystems

No changes were made to any of the following subsystems in this commit:

- Bühlmann ZHL-16C, Schreiner, GF, ceiling, NDL ✅ unchanged
- VPM-B bubble model, radii, constants, conservatism, repetitive state ✅ unchanged
- pSCR/CCR tissue loading, OTU/CNS engines ✅ unchanged
- Gas logic: MOD, EAD/END, gas switching ✅ unchanged
- Gas plan / consumption ✅ unchanged
- Multi-dive tissue carry, SI offgassing ✅ unchanged
- Altitude / water density ✅ unchanged
- UI / settings / persistence (DECO_FIELDS, clear()) ✅ unchanged
- Recreational planner ✅ unchanged

---

## BUG Count

| Report | Version | New Bugs | Cumulative |
|--------|---------|----------|------------|
| v28 | v2.30.30 | **1** (BUG-85) | 85 total |

**BUG-85:** `audit.py` BUG-49 tests check for stale hardcoded filename string after the
dynamic `getExportCircuitTag()` refactor — false-failure, no runtime impact.

---

*All prior bugs BUG-01 through BUG-84 remain fixed and verified. No regressions introduced.*
