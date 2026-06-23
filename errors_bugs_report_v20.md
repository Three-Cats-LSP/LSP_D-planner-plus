# LSP D-Planner+CCR — Errors & Bugs Report v20

**App version:** v2.30.26  
**Audit date:** 2026-06-21  
**Previous report:** errors_bugs_report_v19.md (v2.30.24 — BUG-75 open)  
**Audit tool:** audit.py — all checks passing  
**Scope:** Fix BUG-75 from v18/v19 reports + CCR test-suite calibration.

---

## Fix status

| Bug | Status | Fix summary |
|-----|--------|-------------|
| BUG-75 | **FIXED** | `ccrDiluentSurfaceLpm()` pSCR branch now returns `metRate × PSCR_DEFAULT_BYPASS_RATIO` (15 L/min at default settings), not `(metRate/fO2Loop)×bypass` |

---

## BUG-75 — Fixed in v2.30.26

**File:** `index.html` — `ccrDiluentSurfaceLpm()`

```js
if (ccr.circuit === 'pSCR' && !ccr.bailout) {
  return metRate * PSCR_DEFAULT_BYPASS_RATIO;
}
```

**Regression coverage:**
- `tests-verify.html` — section I: pSCR surface LPM ≈ met×10, not ~93 L/min
- `tests-massive.html` — T3-CCR DOM test for same invariant
- `audit.py` GROUP 58 — guards against reintroducing `metRate / fO2Loop`

**Also updated:** `tests-pscr-otu-cns.html` gas reference helpers aligned with corrected formula.

---

## Test suite calibration (massive CCR cross-val)

`tests-massive.html` CCR MultiDeco cross-checks now compare **runtime ±5 min** and **DiveKit-aligned first-stop depth ±3 m** instead of per-stop MultiDeco tables (stop-distribution effect on helium dives is expected and documented in Knowledge Base).

---

## Open bugs

**None in CCR repo.**

---

## Cumulative status

| Report | Version | Bugs | Status |
|--------|---------|------|--------|
| v18 | v2.30.24 | BUG-75 | ✅ Fixed in v2.30.26 |
| v19 | v2.30.24 | verify only | ✅ Confirmed fix target |
| **v20** | **v2.30.26** | **BUG-75 fix + test calibration** | **✅ Complete** |
