# LSP D-Planner + CCR — Issue #1 Remaining Findings

**Repo:** `Three-Cats-LSP/LSP_D-planner-CCR`  
**Date:** 2026-06-22  
**Audit result:** 401 passed, 0 failed  
**Scope:** Follow-up on external verifier's partial-pass report. 9 production bugs confirmed fixed. 5 items remain open.

---

## Remaining Issues

### REM-1 — MEDIUM: Imperial restore fixes values but not labels — `setUnits()` never called during `appSettings.load()`

**File:** `index.html` `appSettings.load()` line ~17696

The fix for BUG-87 correctly saves `__units__` and restores it before field values. However, the restore code sets `units = values['__units__']` and updates the selectors directly — it does **not** call `setUnits()`. `setUnits()` is responsible for relabelling all unit-bearing elements (`m` → `ft`, `bar` → `psi`, `L` → `cu ft`, `L/min` → `cu ft/min`, depth/pressure input `max` attributes, NDL table column headers, multi-dive depth sliders, etc.).

Result: after reload in imperial, field *values* are correctly restored as imperial numbers, but all *labels* still say metric (depth shows `131` with label `m`, pressure shows `3000` with label `bar`, SAC shows `0.7` with label `L/min`).

**Fix:** After restoring `__units__`, call `setUnits(values['__units__'])` with a guard to skip numeric conversion (since the restored values are already in the correct unit). The cleanest approach is to call `setUnits()` *before* `_restoreFields()`, using the default metric values that are currently in the DOM — `setUnits` converts them to imperial, then `_restoreFields` overwrites with the correct saved imperial values:

```js
if (values['__units__'] && values['__units__'] !== 'metric') {
  setUnits(values['__units__']);  // relabels everything; converts default values (overwritten next)
}
// …then _restoreFields(values) runs as normal
```

---

### REM-2 — HIGH: Recreational mode accepts negative depth and zero/negative bottom time — `runPlanner()` has no input validation

**File:** `index.html` `runPlanner()` line ~6389

`validateDecoInputs()` was added for the Tec deco path (`runDecoSchedule()`), but `runPlanner()` (Rec mode) reads inputs without any bounds check:

```js
const rawD = parseFloat(document.getElementById('depth').value) || 30;  // -5 passes
const bt   = parseInt(document.getElementById('bt').value)       || 25;  // -1 passes
```

Negative depth generates a plan (NDL lookup on negative depth). Negative BT generates a plan. Extremely large values are also accepted.

**Fix:** Add validation to `runPlanner()`, or extract a shared `validatePlannerInputs(rawD, bt)` function used by both paths. Suggested limits: depth 1–40 m (recreational), BT 1–360 min.

---

### REM-3 — LOW: `validateDecoInputs()` BT limit uses `bt > 999` — BT=999 min is accepted

**File:** `index.html` `validateDecoInputs()` line ~9770

```js
if (bt > 999) {
  return { ok: false, msg: 'Bottom time exceeds the 999 minute limit.' };
}
```

`bt > 999` means BT=999 passes. For reference, 999 minutes = 16.65 hours — far beyond any realistic technical dive. The check should use `>= 999` (or a lower realistic ceiling such as 720 min = 12 hours).

**Fix:** Change `bt > 999` to `bt >= 999` or `bt > 720`.

---

### REM-4 — LOW: `tests-verify.html` pinned regression failure — GF30/85 Air 40m/25min RT=66 vs pinned 63 (delta 3 min, exceeds ±2 tolerance)

**File:** `tests-verify.html` line 102

```js
'zhl_40_25_air_gf3085': { rt: 63, … }
```

The current engine consistently produces RT=66 min. The pinned value of 63 dates from LSP v2.9.0. The `assertRtPinned()` tolerance window is ±2 min (values: `RT_PIN_WARN_MIN=1`, `RT_PIN_WARN_MAX=2`). A delta of 3 min falls outside this window and is raised as a hard **failure**, not a warning.

This failure was partially addressed in commit `4d49de7` ("Treat ±1–2 min RT drift as WARN") but the 3-min delta still triggers the failure path (`d > RT_PIN_WARN_MAX`).

**Fix (option A — preferred):** Update the pinned value to reflect current engine output:
```js
'zhl_40_25_air_gf3085': { rt: 66, … }
```

**Fix (option B):** Extend `RT_PIN_WARN_MAX = 3` to treat up to 3-min drift as a warning. Note that this loosens the regression safety net.

---

### REM-5 — LOW: CI workflow only runs `audit.py` — no browser regression tests in CI

**File:** `.github/workflows/audit.yml`

The new CI workflow runs `audit.py index.html` (static analysis). It does not run any browser-based regression suites (`tests.html`, `tests-verify.html`, `tests-pscr-otu-cns.html`, `tests-massive.html`). The Issue #1 report notes that bugs like BUG-86 (pSCR trimix fractions), BUG-90 (EAN80 missing from select), BUG-91 (wrong DOM IDs in tissue chart), and BUG-92 (wrong element ID in export) were all **invisible to `audit.py`** but would have been caught by browser regression tests.

**Fix:** Add a CI job that uses Playwright or similar to load `index.html` via a local HTTP server and run at minimum `tests.html` and `tests-verify.html`. The `dev/validate_pscr_e2e.py` script (already fixed in the issue #1 PR to use HTTP) would be the natural starting point.

---

## Summary Table

| # | Severity | Area | Description |
|---|---|---|---|
| REM-1 | MEDIUM | Settings / UI | Imperial restore sets values correctly but labels stay metric — `setUnits()` not called |
| REM-2 | HIGH | Rec mode | `runPlanner()` has no depth/BT validation — negative values accepted |
| REM-3 | LOW | Validation | `bt > 999` should be `bt >= 999` — BT=999 min accepted |
| REM-4 | LOW | Tests | `tests-verify.html` pinned 63 vs actual 66 min RT — hard failure (delta > ±2 tolerance) |
| REM-5 | LOW | CI | CI only runs `audit.py` — browser regression suites not in CI pipeline |

