# Errors & Bugs Report — v29
**Audit date:** 2026-06-21  
**Branch/commit:** `b67b94f` (main, HEAD)  
**Version:** v2.30.30  
**Scope:** Post-v28 delta audit — commits `74b46df` and `b2ecb8d`  
- `74b46df` — "Fix TXT export filenames to include OC/CCR circuit tag"  
- `b2ecb8d` — "Fix BUG-85: update audit.py BUG-49 checks for dynamic circuit tag filenames"  
**Prior baseline:** v28 — 1 bug (BUG-85, stale audit.py tests)

---

## Summary

| Item | Result |
|------|--------|
| `audit.py` checks | **383 passed, 0 failed** ✅ |
| `audit.py` BUG-49 fix | Correct ✅ |
| `exportTXT()` Gas Plan filename | Fixed and correct ✅ |
| `exportTXT()` general filename | Fixed and correct ✅ |
| `_gasRule` scope in gasplan branch | Valid module-level `let` ✅ |
| All `exportTXT` call sites covered | `gasplan`, `deco`, `planner`, `contingency` ✅ |
| New bugs found | **0** |

---

## BUG-85 — FIXED ✅

`audit.py` GROUP 44 BUG-49 tests updated from hardcoded `LSP_CCR_` checks to dynamic
`LSP_${getExportCircuitTag()}_` checks. The fix exactly matches the pattern suggested
in the v28 report. Audit now passes all 383 checks.

---

## Audit Detail — Changed Areas

### 1. `audit.py` — BUG-49 checks updated (`b2ecb8d`) ✅

```python
# Before
if "LSP_CCR_${isoDate}_GasPlan_" in js:
if "LSP_CCR_${isoDate}_Emergency_" in js:

# After
if "LSP_${getExportCircuitTag()}_${isoDate}_GasPlan_" in js:
if "LSP_${getExportCircuitTag()}_${isoDate}_Emergency_" in js:
```

Checks now match the actual code. Both pass. ✅

### 2. `exportTXT()` — TXT export filenames (`74b46df`) ✅

Two filename assignments updated in `exportTXT()` (line 15217):

**Gas Plan branch** (mode `'gasplan'`):
```javascript
// Before
a.download = `LSP_${dateStr}_GasPlan_${_gasRule}.txt`;
// After
a.download = `LSP_${getExportCircuitTag()}_${dateStr}_GasPlan_${_gasRule}.txt`;
```

**General branch** (modes `deco`, `planner`, `contingency`, `multi`, `cns`):
```javascript
// Before
a.download = `LSP_${dateStr}_${tag}.txt`;
// After
a.download = `LSP_${getExportCircuitTag()}_${dateStr}_${tag}.txt`;
```

Both changes are correct:

- `getExportCircuitTag()` is called with no argument, reading DOM state at export time —
  consistent with the PDF filename pattern introduced in `a17f668`.
- `_gasRule` is a module-level `let` (line 13754), always in scope for `exportTXT`.
- All four call sites (`gasplan`, `deco`, `planner`, `contingency`) are handled by the
  function and produce circuit-aware filenames.
- The recreational `planner` mode always operates in OC context, so
  `getExportCircuitTag()` will return `'OC'` there — correct.
- No branch is left using the old bare `LSP_` prefix.

**Filename consistency across all export types is now complete:**

| Export type | Filename pattern |
|-------------|-----------------|
| Gas Plan PDF | `LSP_{OC\|CCR}_{date}_GasPlan_{rule}.pdf` ✅ |
| Emergency PDF | `LSP_{OC\|CCR}_{date}_Emergency_....pdf` ✅ |
| Deco PDF | `LSP_{OC\|CCR}_{date}_Deco_....pdf` ✅ |
| Gas Plan TXT | `LSP_{OC\|CCR}_{date}_GasPlan_{rule}.txt` ✅ |
| Deco TXT | `LSP_{OC\|CCR}_{date}_Deco_....txt` ✅ |
| Planner TXT | `LSP_{OC\|CCR}_{date}_Plan_....txt` ✅ |
| Contingency TXT | `LSP_{OC\|CCR}_{date}_Emergency_....txt` ✅ |

---

## Regression Check

No changes to any algorithm, physics, gas logic, UI, or settings subsystems in these
commits. All 383 regression checks pass.

---

## BUG Count

| Report | Version | New Bugs | Cumulative |
|--------|---------|----------|------------|
| v29 | v2.30.30 | **0** | 85 total (all fixed) |

**BUG-85 CLOSED.** All bugs BUG-01 through BUG-85 are fixed and verified.  
Audit suite: **383/383 passing.**

---

*Clean. No regressions. No new bugs.*
