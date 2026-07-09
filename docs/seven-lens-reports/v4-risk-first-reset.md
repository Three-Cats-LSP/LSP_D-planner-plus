# V4 Risk-First Audit Reset

Date: 2026-07-09

## What Changed

- Created a new active audit epoch: `v4-risk-first-reset`.
- Replaced old numeric active cycles with `R01` through `R42` in risk-first order.
- Archived the previous V3 cycle registry under `frozen_history` in `docs/audit-units.json`.
- Preserved old Cycle 1-42/200/201 records as historical evidence, not the active execution queue.
- Recalculated current unit fingerprints and line counts from the current app structure.
- Regenerated `docs/audit-coverage.md` and `docs/audit-master-plan.md` from the V4 registry.
- Added `docs/seven-lens-records/v4/` as the only canonical JSON record location for new V4 cycles.

## Why It Changed

Recent CSS, markup, extracted runtime blocks, graph rendering, gas-card, warning-banner, MOD-blocking, and schedule-table work changed source boundaries enough that continuing to patch old cycle records would keep creating audit friction. V4 resets the active review queue while keeping historical evidence intact.

The new order reviews production engines and safety paths first, then planner state, results/export/consumption correctness, core renderers, runtime/native paths, and finally lower-risk markup/CSS/design-lock surfaces.

## Workflow From Now On

- Start at `R01`, not old Cycle 1 or old Cycle 33.
- Use one canonical record per V4 cycle under `docs/seven-lens-records/v4/`.
- Produce one Markdown batch report after each batch.
- Fix findings directly with focused regressions.
- Mark a V4 cycle reviewed only after targeted tests, static audit, and CI audit pass.
- Do not reinterpret old records unless an explicit dependency re-review is recorded.

## Design Contracts To Preserve

- Schedule table columns and mobile geometry remain readable.
- Gas consumption uses bars with inline no-gas warnings and distinct low/critical/no-go colors.
- Main and contingency plans use matching schedule/gas-card contracts.
- Light/dark warning colors remain intentional.
- VPM and Buhlmann MOD blocks prevent partial result-shell rendering.
- Graph waypoints remain bounded and sane.
- Tissues tab and tissue color scale remain visible.
- Visible schedule/contingency gas labels use `Air`, `100%`, or `OO/HH`, never `EAN*`.

