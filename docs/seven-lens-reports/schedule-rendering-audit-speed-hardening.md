# Schedule Rendering and Audit-Speed Hardening Report

Date: 2026-07-08  
Branch: `dev`

## What Was Done

- Added a canonical visible schedule-table contract:
  `Phase, Depth, Stop, Run, Mix, PPO2, EAD`.
- Added shared runtime helpers for schedule column count, table cells, and schedule error rows.
- Replaced VPM runner schedule-table error rows with the shared helper so the error row `colspan` follows the table contract.
- Added three stable visual-contract cases:
  - `SCHEDULE-ERROR-ROW-COLUMN-CONTRACT`
  - `VPM-INVALID-ERROR-ROW-GEOMETRY`
  - `SCHEDULE-CANONICAL-GAS-LABELS`
- Added a browser probe that exercises the VPM runner error renderer and verifies the error row geometry on desktop and mobile.
- Added explicit `--fast` support to `tools/run_audit_coverage_suite.py` for simplified local batch preflight while keeping the default CI/release suite full strength.
- Refreshed affected fingerprints and regenerated audit coverage/master-plan docs.

## Why It Was Done

The previous batch found a real drift bug: VPM error rows still used an old table width after the schedule table changed. This pass removes that failure mode by making error rows depend on a single schedule-column source of truth instead of hard-coded `colspan` values.

The audit workflow also needed a practical speed path. Full `SUITE-COVERAGE` remains available for CI/release, but simplified batch work can use the explicit fast coverage mode plus focused regressions instead of paying for the full historical/browser-heavy gate every time.

## Effect On Future Audit Workflow

- Schedule table changes now have a single contract to update.
- VPM and future ZHL table error paths can share the same helper instead of hand-building incompatible rows.
- Simple table-shape invariants are protected by source-level and lightweight browser checks.
- Playwright/browser traces should stay reserved for true interaction/state bugs.
- Frozen historical cycles remain frozen; this pass updates only current affected units and forward-looking regression coverage.

## Verification

- `python dev/ui_visual_contract_regression.py` - PASS
- `python dev/engine_regression.py` - PASS, 175/175
- `node dev/vpm_direct_regression.js` - PASS
- `python tools/assemble_ui_html.py --verify` - PASS
- `python tools/run_audit_coverage_suite.py --fast` - PASS, about 41 seconds locally
- `python tools/audit_coverage.py --write-docs` - PASS
- `python tools/seven_lens_protocol.py check-all --require-artifacts` - PASS
- `python -m tools.audit check --profile static` - PASS
- `python -m tools.audit run --profile ci` - PASS, 18/18 suites
