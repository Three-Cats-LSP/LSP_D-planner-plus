# LSP D-Planner + CCR — Errors & Bugs Report v24

**Repo:** `Three-Cats-LSP/LSP_D-planner-CCR`  
**Version analysed:** v2.30.30 (commit `86e5135`)  
**Date:** 2026-06-21  
**Audit result:** 376 passed, **1 failed** (stale version pin in audit.py — see below)  
**Scope:** Verification pass 24. BUG-77 still partially open. Two new low-severity findings.

---

## Verification

### BUG-82 — ZHL pSCR OTU plan walk (fixed in v2.30.30)
`accumulateHeadlessPlanExposure()` now builds a proper plan array (descent + bottom + deco steps) and delegates to `computePlanExposureTotals()`, matching the VPM path exactly. Prior-dive O₂ carry is handled correctly with no double-counting. Analysis confirmed consistent: `ZHLEngine.calculate()` adds carry once from `s._preOTU`, and `computePlanExposureTotals` itself has no carry awareness. ✅

### BUG-81 — VPM test harness iframe resolve (fixed in d610f1d)
Tests-only fix — no index.html change. ✅

---

## Open Bug (from v22 report)

### BUG-77 — `dg1Mix` and `dg2Mix` still not in `DECO_FIELDS`

**Status:** ⚠️ Still open in v2.30.30

`'dg1Mix'`, `'dg2Mix'`, `'dg1CustomO2'`, `'dg2CustomO2'` remain absent from `DECO_FIELDS`. Users lose deco gas 1/2 selections on every page reload. Unchanged since first reported.

**Fix:** Add to `DECO_FIELDS`:
```js
'dg1Mix', 'dg1CustomO2', 'dg2Mix', 'dg2CustomO2',
```

---

## New Bugs

### BUG-83 — `audit.py` version pin stale: checks for `2.30.29` but `APP_VERSION` is `2.30.30` — 1 audit failure

**File:** `audit.py`  
**Severity:** LOW  
**Location:** Lines ~2485–2554

```python
if "const APP_VERSION = '2.30.29'" in js:
    ok("APP_VERSION bumped to 2.30.29")
else:
    fail("APP_VERSION not bumped to 2.30.29")   # ← fails because it's now 2.30.30
```

The audit hardcodes the version string `2.30.29` as the expected value. After `index.html` was bumped to `2.30.30`, this check fails. The audit reports 376 passed / **1 failed** instead of all passing.

**Impact:** The audit is not a clean pass — any CI or QA gating on `audit.py` exit code will fail. The check should use a pattern match or the version should be bumped in `audit.py`.

---

### BUG-84 — Version mismatch: `APP_VERSION` at `2.30.30`, all other files still at `2.30.29`

**Severity:** LOW

| File | Value |
|---|---|
| `index.html` `APP_VERSION` | `2.30.30` ✓ |
| `package.json` `version` | `2.30.29` ✗ |
| `android/app/build.gradle` `versionName` | `2.30.29` ✗ |
| `android/app/build.gradle` `versionCode` | `23029` ✗ |
| `sw.js` `CACHE_VERSION` | `lsp-dplanner-ccr-v2.30.29` ✗ |

Repeat of BUG-01/39/74 pattern. APK and PWA cache will report v2.30.29 while the web app shows v2.30.30.

---

## Summary Table

| # | Severity | Status | Description |
|---|---|---|---|
| BUG-77 | LOW | ⚠️ Open | `dg1Mix`/`dg2Mix` not in `DECO_FIELDS` — deco gas mix selectors lost on reload |
| BUG-83 | LOW | NEW | `audit.py` version pin stale at `2.30.29` — causes 1 audit failure |
| BUG-84 | LOW | NEW | `package.json`/`build.gradle`/`sw.js` still at `2.30.29` while `index.html` is `2.30.30` |

