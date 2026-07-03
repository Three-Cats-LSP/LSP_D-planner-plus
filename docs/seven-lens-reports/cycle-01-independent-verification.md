# Seven-Lens Cycle 01 - Independent Verification

**Target branch:** `dev`  
**Verified merge commit:** `a249536`  
**Unit:** `UI-MARKUP-HEADER`  
**Canonical boundary:** `ui/markup-header.html` lines 1-847  
**Verifier:** Codex, fresh post-merge review  
**Verdict:** BLOCKED

## Summary

The depth and bottom-time synchronization repair works through real DOM `input`
events, profile preset loading, and settings restoration. The GF placeholder repair
also matches the 20/85 default. Static audit and the full engine regression pass.

Cycle 1 cannot be closed yet. One application defect remains in the reviewed unit,
the new regression coverage does not prove every repaired path, and the recorded
independent verification predates the final Parts B-D commit.

## Findings

### SL-C01-M-03: Imperial custom-altitude constraints remain metric

- **Severity:** MEDIUM
- **Lens:** L1, L3, L4, L6
- **Unit:** `UI-MARKUP-HEADER` with unit-switch caller context
- **Location:** `ui/markup-header.html:462`; assembled `index.html:3505-3508`
- **Root cause:** Unit switching converts the custom-altitude value and relabels the
  field as feet, but does not convert its metric `max="5000"` or `step="50"`
  attributes.
- **Failure path:** Switch to imperial units, select Custom altitude, and enter the
  supported 5,000 m ceiling as 16,404 ft. Browser constraint validation rejects the
  value because the unchanged maximum is interpreted as 5,000 ft.
- **Impact:** Imperial users can enter only about 1,524 m through a constraint-valid
  field, while metric users can enter the engine's full 5,000 m range. The displayed
  unit and accepted range describe different physical limits.
- **Evidence:** Headless Chromium reported `max=5000`, `step=50`, label `ft`, and
  `checkValidity() === false` for 16,404 ft.
- **Recommendation:** Derive the custom-altitude input constraints from the canonical
  metre limits whenever units change, preserving the same physical range and step in
  both unit systems. Add metric/imperial boundary regressions.
- **Regression ID:** proposed `SL-C01-ALTITUDE-UNIT-CONSTRAINTS`
- **Status:** OPEN

### SL-C01-L-02: Sync regressions bypass event wiring and leak UI state

- **Severity:** LOW
- **Lens:** L3, L7
- **Unit:** Cycle 1 regression evidence
- **Location:** `dev/engine_regression.py:1671-1704`
- **Root cause:** `SL-C01-DEPTH-SYNC` assigns values and calls
  `_syncDepthBtSteppers()` directly instead of dispatching the `input` events whose
  inline handlers were part of the fix. Neither case restores all changed DOM state.
  `SL-C01-PRESET-SYNC` checks only the depth mirror and label, not bottom time, and no
  case exercises the settings-restore path named by `SL-C01-M-01`.
- **Impact:** The suite can pass if inline event wiring or bottom-time/settings-restore
  synchronization regresses. Later tests inherit mutated profile values, reducing
  isolation and repeatability.
- **Recommendation:** Exercise actual `input`, profile-preset, and settings-restore
  entry paths; assert both canonical fields, both mirrors, and both labels; restore
  DOM, storage, globals, and modal state in `finally`.
- **Regression ID:** retain `SL-C01-DEPTH-SYNC` and `SL-C01-PRESET-SYNC`; add a stable
  settings-restore case ID.
- **Status:** OPEN

### SL-C01-M-04: Final whole-unit verification was not independent

- **Severity:** MEDIUM (audit process)
- **Lens:** L7
- **Unit:** Cycle 1 audit evidence
- **Location:** `docs/seven-lens-reports/cycle-01-header-part-a.md:75-84`;
  `docs/seven-lens-reports/cycle-01-header-parts-bcd.md:5-14`;
  `docs/seven-lens-manual-ledger.json`
- **Root cause:** Phase D records verification at commit `50e3ea1`, before the final
  Parts B-D implementation commit `1f7c000`. Parts B-D total 633 lines and were
  reviewed as one session despite the 600-line limit. The ledger then promoted the
  entire 847-line unit to `SEVEN_LENS_REVIEWED`.
- **Impact:** The ledger claims independent final-fingerprint verification that the
  recorded commit/session evidence does not establish.
- **Recommendation:** Split Parts B-D into verification sessions no larger than 600
  lines, verify the final fix commit in a fresh context, and promote the whole unit
  only after all part fingerprints and evidence are current.
- **Status:** OPEN

## Verification Evidence

| Check | Result |
|---|---|
| `python -m tools.audit check --profile static` | PASS: 6 checks, 4 suites |
| `python dev/engine_regression.py` | PASS: 157/157 |
| Real `input` event depth/BT mirror probe | PASS |
| Imperial altitude constraint probe | FAIL: 16,404 ft rejected |
| Tracked worktree after commands | CLEAN |

## Closure Requirements

1. Resolve `SL-C01-M-03` and add metric/imperial boundary evidence.
2. Resolve `SL-C01-L-02` with isolated event-path and settings-restore regressions.
3. Reverify the final PR HEAD in bounded fresh sessions and update per-part ledger
   evidence.
4. Run static, CI, and release profiles on the same final commit before restoring
   `SEVEN_LENS_REVIEWED`.
