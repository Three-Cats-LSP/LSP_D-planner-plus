# V5 Pre-R Legacy Migration

## What Was Done

- Set the active audit epoch to `v5-risk-first-active`.
- Promoted useful live `SL-Cxx-*` regression case IDs into V5/R-era IDs.
- Preserved old IDs as `legacy_aliases` in `docs/audit-units.json` for searchability.
- Marked pre-R cycle records, trace specs, and evidence receipts as archive-only historical data.
- Added `tools/v5_audit_recalc.py --write/--check` to recalculate active R-cycle line counts and reject live pre-R IDs.

## Why

The old Cycle 1-9/200 closure system kept reinterpreting historical records whenever modern source files moved. V5 keeps the useful regression checks, but removes old closure bookkeeping from the active release path.

## Promote

| Legacy case | V5 case |
|---|---|
| `SL-C01-ALTITUDE-UNIT-CONSTRAINTS` | `V5-TOOLS-ALTITUDE-UNIT-CONSTRAINTS` |
| `SL-C01-DEPTH-SYNC` | `V5-TOOLS-DEPTH-SYNC` |
| `SL-C01-PRESET-SYNC` | `V5-TOOLS-PRESET-SYNC` |
| `SL-C01-SETTINGS-RESTORE` | `V5-TOOLS-SETTINGS-RESTORE` |
| `SL-C02-CYLINDER-PHYSICAL-CONSTRAINTS` | `V5-TOOLS-CYLINDER-PHYSICAL-CONSTRAINTS` |
| `SL-C02-CYLINDER-SIZE-EDIT-AFTER-SWITCH` | `V5-TOOLS-CYLINDER-SIZE-EDIT-AFTER-SWITCH` |
| `SL-C02-MIN-DECO-UNITS` | `V5-TOOLS-MIN-DECO-UNITS` |
| `SL-C02-TRAVEL-DEPTH-CONSTRAINTS` | `V5-TOOLS-TRAVEL-DEPTH-CONSTRAINTS` |
| `SL-C02-TRAVEL-DEPTH-EDIT-AFTER-SWITCH` | `V5-TOOLS-TRAVEL-DEPTH-EDIT-AFTER-SWITCH` |
| `SL-C02-UNIT-ROUNDTRIP-IMMUTABLE` | `V5-TOOLS-UNIT-ROUNDTRIP-IMMUTABLE` |
| `SL-C03-BEST-MIX-DEPTH-UNITS` | `V5-TOOLS-BEST-MIX-DEPTH-UNITS` |
| `SL-C03-BEST-MIX-EDIT-AFTER-SWITCH` | `V5-TOOLS-BEST-MIX-EDIT-AFTER-SWITCH` |
| `SL-C03-CNS-DEPTH-UNITS` | `V5-TOOLS-CNS-DEPTH-UNITS` |
| `SL-C03-CNS-EDIT-AFTER-SWITCH` | `V5-TOOLS-CNS-EDIT-AFTER-SWITCH` |
| `SL-C04-CONFIRM-BACKDROP` | `V5-TOOLS-CONFIRM-BACKDROP` |
| `SL-C04-DYNAMIC-DECO-CYL-IMPERIAL` | `V5-TOOLS-DYNAMIC-DECO-CYL-IMPERIAL` |
| `SL-C04-END-DEPTH-UNITS` | `V5-TOOLS-END-DEPTH-UNITS` |
| `SL-C04-SI-DEPTH-UNITS` | `V5-TOOLS-SI-DEPTH-UNITS` |
| `SL-C05-CSS-DEAD-ALGO-SWITCHER` | `V5-CSS-DEAD-ALGO-SWITCHER` |
| `SL-C05-CSS-DEAD-BRAND-ICON` | `V5-CSS-DEAD-BRAND-ICON` |
| `SL-C05-CSS-DEAD-GF-BTN` | `V5-CSS-DEAD-GF-BTN` |
| `SL-C05-CSS-DEAD-THEME-TOGGLE` | `V5-CSS-DEAD-THEME-TOGGLE` |
| `SL-C05-EXPORT-FOCUS-VISIBLE` | `V5-CSS-EXPORT-FOCUS-VISIBLE` |
| `SL-C05-GF-ROW-MODE-ISOLATION` | `V5-CSS-GF-ROW-MODE-ISOLATION` |
| `SL-C06-CSS-DEAD-BTN-CALC` | `V5-CSS-DEAD-BTN-CALC` |
| `SL-C06-CSS-DEAD-SI-INNER` | `V5-CSS-DEAD-SI-INNER` |
| `SL-C06-CSS-DEAD-T-COL` | `V5-CSS-DEAD-T-COL` |
| `SL-C06-FIELD-INVALID-STATE` | `V5-CSS-FIELD-INVALID-STATE` |
| `SL-C06-GAS-NUM-TOUCH-TARGET` | `V5-CSS-GAS-NUM-TOUCH-TARGET` |
| `SL-C06-REDUCED-MOTION` | `V5-CSS-REDUCED-MOTION` |
| `SL-C06-SEG-FOCUS-VISIBLE` | `V5-CSS-SEG-FOCUS-VISIBLE` |
| `SL-C07-CHIP-YELLOW-DISTINCT` | `V5-CSS-CHIP-YELLOW-DISTINCT` |
| `SL-C07-CSS-DEAD-ALGO-SWITCHER` | `V5-CSS-RESULTS-DEAD-ALGO-SWITCHER` |
| `SL-C07-CSS-DEAD-LEGACY-CARDS` | `V5-CSS-DEAD-LEGACY-CARDS` |
| `SL-C07-PPO2-SEVERITY-COLORS` | `V5-CSS-PPO2-SEVERITY-COLORS` |
| `SL-C07-PRINT-RESULTS` | `V5-CSS-PRINT-RESULTS` |
| `SL-C07-REDUCED-MOTION` | `V5-CSS-RESULTS-REDUCED-MOTION` |
| `SL-C09-CONTINGENCY-COPY-PLAN-CONTEXT` | `V5-RESULTS-CONTINGENCY-COPY-PLAN-CONTEXT` |
| `SL-C09-GAS-SWITCH-TERMINOLOGY` | `V5-RESULTS-GAS-SWITCH-TERMINOLOGY` |
| `SL-C09-GRAPH-WAYPOINT-TIME-SPREAD` | `V5-RESULTS-GRAPH-WAYPOINT-TIME-SPREAD` |
| `SL-C09-HIGH-CNS-DECO-ALERT` | `V5-RESULTS-HIGH-CNS-DECO-ALERT` |
| `SL-C09-MOBILE-TISSUE-TAB-VISIBLE` | `V5-SHELL-MOBILE-TISSUE-TAB-VISIBLE` |
| `SL-C09-MOBILE-WARNING-WRAP` | `V5-SHELL-MOBILE-WARNING-WRAP` |
| `SL-C09-RESULT-TAB-SIMPLIFICATION` | `V5-SHELL-RESULT-TAB-SIMPLIFICATION` |
| `SL-C09-RESULT-TABS-GAP` | `V5-SHELL-RESULT-TABS-GAP` |
| `SL-C09-SCHEDULE-COLUMN-GEOMETRY` | `V5-RESULTS-SCHEDULE-COLUMN-GEOMETRY` |
| `SL-C09-SUMMARY-CHIP-PALETTE` | `V5-RESULTS-SUMMARY-CHIP-PALETTE` |
| `SL-C09-SWITCH-ROW-BACKGROUND-PARITY` | `V5-RESULTS-SWITCH-ROW-BACKGROUND-PARITY` |
| `SL-C09-TRAVEL-GAS-TRIMIX-CARD` | `V5-RESULTS-TRAVEL-GAS-TRIMIX-CARD` |
| `SL-C09-VPM-BEYOND-MOD-BLOCKS` | `V5-RESULTS-VPM-BEYOND-MOD-BLOCKS` |
| `SL-C09-VPM-CONTINGENCY-GAS-LOSS-STABLE` | `V5-RESULTS-VPM-CONTINGENCY-GAS-LOSS-STABLE` |
| `SL-C09-VPM-GRAPH-WAYPOINT-MONOTONIC` | `V5-RESULTS-VPM-GRAPH-WAYPOINT-MONOTONIC` |
| `SL-C09-VPM-MODE-TOGGLE` | `V5-SHELL-VPM-MODE-TOGGLE` |
| `SL-C09-ZHL-BEYOND-MOD-BLOCKS` | `V5-RESULTS-ZHL-BEYOND-MOD-BLOCKS` |

## Archive Only Records

- `docs/seven-lens-records/cycle-02-rec-planner.json`
- `docs/seven-lens-records/cycle-03-consumption.json`
- `docs/seven-lens-records/cycle-04-tools-modals.json`
- `docs/seven-lens-records/cycle-05-css.json`
- `docs/seven-lens-records/cycle-06-controls-css.json`
- `docs/seven-lens-records/cycle-07-results-css.json`
- `docs/seven-lens-records/cycle-08-shell-results.json`
- `docs/seven-lens-records/cycle-09-environment-mode-state.json`
- `docs/seven-lens-records/cycle-200-tec-planner.json`
- `docs/seven-lens-records/cycle-201-mode-isolation.json`

## Archive Only Reports

- `docs/seven-lens-reports/cycle-05-record.json`
- `docs/seven-lens-reports/cycle-06-record.json`
- `docs/seven-lens-reports/cycle-07-record.json`
- `docs/seven-lens-reports/cycle-08-record.json`

## Archive Only Trace Specs

- `docs/seven-lens-traces/cycle-02-mode-isolation.json`
- `docs/seven-lens-traces/cycle-02-planner.json`
- `docs/seven-lens-traces/cycle-02-rec-planner.json`
- `docs/seven-lens-traces/cycle-02-tec-planner.json`
- `docs/seven-lens-traces/cycle-03-consumption.json`
- `docs/seven-lens-traces/cycle-04-tools-modals.json`
- `docs/seven-lens-traces/cycle-05-css.json`
- `docs/seven-lens-traces/cycle-05-export-focus.json`
- `docs/seven-lens-traces/cycle-06-controls.json`
- `docs/seven-lens-traces/cycle-07-results.json`
- `docs/seven-lens-traces/cycle-08-shell-results.json`

## Archive Only Evidence Receipts

- `dev/seven-lens-evidence-c03-ER-03-POST-BESTMIX.json`
- `dev/seven-lens-evidence-c03-ER-03-POST-CNS.json`
- `dev/seven-lens-evidence-c03-ER-03-POST-PHYSICAL.json`
- `dev/seven-lens-evidence-c03-ER-03-POST-SAFETY.json`
- `dev/seven-lens-evidence-c03-ER-03-PRE-FIX.json`
- `dev/seven-lens-evidence-c03-ER-03-RESTORE-BESTMIX.json`
- `dev/seven-lens-evidence-c03-ER-03-RESTORE-CNS.json`
- `dev/seven-lens-evidence-c03-ER-03-RESTORE-PHYSICAL.json`
- `dev/seven-lens-evidence-c03-ER-03-RESTORE-SAFETY.json`
- `dev/seven-lens-evidence-c03-ci.json`
- `dev/seven-lens-evidence-c03-static.json`
- `dev/seven-lens-evidence-c04-ER-04-POST-CANONICAL.json`
- `dev/seven-lens-evidence-c04-ER-04-POST-CONFIRM.json`
- `dev/seven-lens-evidence-c04-ER-04-POST-END.json`
- `dev/seven-lens-evidence-c04-ER-04-POST-PROTOCOL.json`
- `dev/seven-lens-evidence-c04-ER-04-POST-SI.json`
- `dev/seven-lens-evidence-c04-ER-04-POST-TRACE.json`
- `dev/seven-lens-evidence-c04-ER-04-PRE-CANONICAL.json`
- `dev/seven-lens-evidence-c04-ER-04-PRE-MODALS.json`
- `dev/seven-lens-evidence-c04-ER-04-PRE-PROTOCOL.json`
- `dev/seven-lens-evidence-c04-ER-04-PRE-TOOLS.json`
- `dev/seven-lens-evidence-c04-ER-04-RESTORE-CANONICAL.json`
- `dev/seven-lens-evidence-c04-ER-04-RESTORE-CONFIRM.json`
- `dev/seven-lens-evidence-c04-ER-04-RESTORE-END.json`
- `dev/seven-lens-evidence-c04-ER-04-RESTORE-PROTOCOL.json`
- `dev/seven-lens-evidence-c04-ER-04-RESTORE-SI.json`
- `dev/seven-lens-evidence-c04-ER-04-RESTORE-TRACE.json`
- `dev/seven-lens-evidence-c04-ci.json`
- `dev/seven-lens-evidence-c04-static.json`
- `dev/seven-lens-evidence-c05-ER-C05-POST-CSS.json`
- ... 49 more archived paths

## Delete

- `font-readability-mockups.html (deleted; implemented temporary mockup)`

## Active Workflow From Now On

- Run `python tools/v5_audit_recalc.py --write` after source restructuring.
- Run `python tools/v5_audit_recalc.py --check` in gates to catch stale R-cycle metadata and active old IDs early.
- Do not repair old `cycle-*` line boundaries during normal development; they are frozen history.
- Keep `index.html` generated from canonical `ui/*.html`, runtime `.js`, and source `.css`.
