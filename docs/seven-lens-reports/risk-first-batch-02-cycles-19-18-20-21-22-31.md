# Risk-First Batch 02 Report — Cycles 19, 18, 20, 21, 22, 31

Date: 2026-07-08  
Branch: `dev`  
Batch order: `19, 18, 20, 21, 22, 31`  
Focus: planner mode/state paths, ZHL/VPM schedule invocation, headless engine adapters, and ZHL worker bridge.

## Summary

This batch reviewed the current registered source ranges for:

- Cycle 19: `UI-DECO-PHYSICS`, `UI-SCHEDULE-INPUTS`
- Cycle 18: `UI-ZHL-DELEGATES`, `UI-CCR-DELEGATES`
- Cycle 20: `UI-ZHL-RUNNER-SETUP`, `UI-ZHL-RUNNER-ENGINE`
- Cycle 21: `UI-ZHL-HEADLESS-HELPERS`, `UI-ZHL-HEADLESS-ENGINE`
- Cycle 22: `UI-VPM-RUNNER`
- Cycle 31: `APP-ZHL-WORKER`, `APP-ZHL-WORKER-BRIDGE`

One real defect was found and fixed. No decompression math defect was found in this batch. Existing engine and UI regression coverage remains green after the fix.

## Findings and Fixes

### SL-BATCH2-VPM-ERROR-COLSPAN — LOW — Fixed

Cycle: 22  
Unit: `UI-VPM-RUNNER`  
File: `index.html`

The VPM runner error paths still rendered schedule error rows with `colspan="8"`, while the visible deco schedule table now has seven columns:

`Phase, Depth, Stop, Run, Mix, ppO2, EAD`

This did not affect successful VPM schedules, but invalid VPM/repetitive-state branches could produce a malformed error row and disturb schedule table geometry.

Fix:

- Changed the five VPM runner error rows from `colspan="8"` to `colspan="7"`.
- Added stable regression case `SL-BATCH2-VPM-ERROR-COLSPAN`.
- Registered the case as `REG-131` in `SUITE-UI-VISUAL-CONTRACT-REGRESSION`.

## Cycle Results

### Cycle 19 — Deco Physics and Schedule Inputs

Reviewed:

- Physical/decozone wrapper delegation to `ZhlEngineBundle`
- REC planner NDL path
- Schedule-input helpers, gas fraction readers, trimix validation, deco gas collection
- Tissue saturation rendering helpers

Result: No new defect found.

Notes:

- The reviewed code mostly delegates canonical decompression physics to extracted engine bundles.
- Recent gas-label and schedule-column changes remain consistent in this path.

### Cycle 18 — ZHL and CCR Delegates

Reviewed:

- ZHL bundle environment synchronization
- ZHL thin delegate wrappers
- CCR/pSCR DOM settings merge
- Diluent/bailout validation and gas-label logic

Result: No new defect found.

Notes:

- CCR settings merge continues to normalize through the engine bundle.
- Existing regression coverage covers trimix inert ratios, pSCR loop behavior, and bailout gas selection.

### Cycle 20 — ZHL Runner Setup and Engine Invocation

Reviewed:

- `runDecoSchedule()` validation order
- ZHL/VPM branch selection
- ZHL schedule parameter construction
- GF bailout override restore path
- graph/tissue rendering scheduling

Result: No new defect found.

Notes:

- Existing `finally` restoration for `_scheduleWorkerBusy` and bailout GF restore remains intact.
- ZHL engine full regression passed after the review.

### Cycle 21 — Headless ZHL Helpers and Engine API

Reviewed:

- Input validation for levels/deco gases
- CCR calculation validation
- headless profile splitting and monotonic-depth enforcement
- `ZHLEngine.calculate()` / `calculateInWorker()` error handling
- exposure carry and repetitive-state merge

Result: No new defect found.

Notes:

- Existing validation regression confirms invalid gas/profile cases return structured errors.
- Worker parity cases still pass.

### Cycle 22 — VPM Runner

Reviewed:

- VPM DOM-to-engine settings construction
- VPM repetitive state and prior-dive oxygen carry
- VPM bottom/deco gas conversion
- VPM engine load/error branches
- render handoff to VPM results renderer

Result: One LOW UI/runtime defect fixed: `SL-BATCH2-VPM-ERROR-COLSPAN`.

### Cycle 31 — ZHL Worker and Bridge

Reviewed:

- `zhl-schedule-worker.js`
- `zhl-worker-bridge.js`
- worker timeout, crash handling, pending-promise settlement, permanent-disable guard

Result: No new defect found.

Notes:

- Existing worker timeout/recovery and sync/worker parity tests passed.

## Verification

Commands run:

- `python dev/ui_visual_contract_regression.py` — PASS
- `python engine_validation_regression.py` — PASS, 35/35
- `node dev/vpm_direct_regression.js` — PASS
- `python dev/engine_regression.py` — PASS, 175/175
- `node --check zhl-worker-bridge.js` — PASS
- `node --check gas-cards-core.js` — PASS
- `python -m py_compile engine_validation_regression.py dev/ccr_engine_validation_regression.py tools/build_zhl_bundle.py tools/build_vpm_bundle.py tools/check_engine_parity.py` — PASS

Audit metadata:

- Registered `REG-131` for `SL-BATCH2-VPM-ERROR-COLSPAN`.
- Refreshed affected fingerprints and generated audit docs.

## App Improvements Recommended Next

- Keep one helper for schedule table column count, so error rows and data rows cannot drift when columns change again.
- Add a small direct VPM invalid-input browser probe that checks rendered error-row geometry, not only successful VPM schedules.
- Keep VPM and ZHL runner error paths aligned with the same table rendering helper used by normal schedule rows.
- Continue preserving canonical gas labels at engine output and renderer input boundaries.

## Audit Workflow Improvements

- The simplified batch flow worked better than Cycle 8: one report, one finding, one focused regression, no closure loop.
- Good speed-up target remains `SUITE-COVERAGE`; it is much better than before but still broad enough to slow every batch.
- For future batches, prefer adding small source-level contract checks for simple static UI invariants, and reserve Playwright traces for real behavior/state transitions.
