# Risk-First Engine Batch Report — Cycles 33, 34, 35, 36, 38, 37

Date: 2026-07-08
Branch: `dev`

## Summary

The first risk-first batch reviewed the production engine and safety-critical
core path:

1. Cycle 33 — `ENG-ZHL-PHYSICS`, `ENG-ZHL-GAS`
2. Cycle 34 — `ENG-ZHL-SCHEDULE`
3. Cycle 35 — `ENG-ZHL-CCR`
4. Cycle 36 — `ENG-VPM`
5. Cycle 38 — `ENG-VPM-REFERENCE`
6. Cycle 37 — `ENG-RDP`

Result: one real defect was found and fixed in Cycle 36. The other cycles were
clean under source review plus targeted regression evidence.

## Findings And Fixes

### Cycle 33 — ZHL Physics And Gas

Finding status: no new defects found.

Reviewed areas:

- Buhlmann ZHL-16C N2/He constants and half-time switching.
- Altitude, water-vapor, and water-density environment application.
- Tissue saturation, linear Schreiner loading, ceiling, GF interpolation, NDL,
  and surface-GF helpers.
- Deco gas selection and minimum-deco-profile stop insertion.

Evidence:

- `python dev/engine_regression.py`
- `python engine_validation_regression.py`
- `python dev/gas_core_regression.py`

### Cycle 34 — ZHL Schedule

Finding status: no new defects found.

Reviewed areas:

- Canonical gas label formatter: `Air`, `100%`, `OO/HH`.
- Descent/bottom timing, travel-gas loading, repetitive tissue carry,
  multi-level continuation, first-stop GF anchoring, min-stop rounding,
  whole-minute stops, and final tissue export.
- Existing Cycle 34 bailout/diluent/MOD safety regressions.

Metadata cleanup:

- `ENG-ZHL-SCHEDULE` was still `IN_PROGRESS` from prior invalidation. This
  batch reverified it and restored current fingerprint/evidence status.

Evidence:

- `ZHL-ML-CONT-GAS`
- `ZHL-ML-ASCENT-RATE`
- `CYCLE35-WHOLE-MIN-STOPS-EFFECT`
- Full engine suite pass.

### Cycle 35 — ZHL CCR

Finding status: no new defects found.

Reviewed areas:

- CCR/pSCR setting normalization.
- CCR setpoint zones and setpoint crossing.
- pSCR steady-state inspired gas fractions.
- CCR linear/constant tissue loading and ppO2 paths.

Evidence:

- `python dev/ccr_engine_validation_regression.py`
- Full engine suite CCR/pSCR cases.

### Cycle 36 — VPM Core

Finding status: fixed.

Finding: VPM engine plan output used raw gas labels such as `21/0`, `50/0`,
and `100/0`.

Why it was a bug:

- The app-wide operational gas-label contract is `Air`, `100%`, or zero-padded
  `OO/HH`.
- UI renderers can normalize some labels later, but engine output is consumed by
  schedules, graphing, contingency, export, and tests. The core should not emit
  stale raw labels that downstream code must repeatedly repair.

Fix:

- Added `vpmGasLabel(o2Pct, hePct)` in `vpm-engine-core.js`.
- Replaced all VPM core raw `${o2}/${he}` plan labels and deco-gas labels with
  the canonical formatter.
- Rebuilt `vpm-engine-bundle.js` from the canonical source.
- Added stable regression `CYCLE36-VPM-GAS-LABELS` / `REG-121` to
  `dev/engine_regression.py`.

Evidence:

- Before targeted probe: VPM plan labels were `21/0`, `50/0`, `100/0`.
- After fix: VPM plan labels are `Air`, `50/00`, `100%`.
- `python dev/engine_regression.py` — 175/175 pass.
- `npm.cmd run check:engine-parity` — pass.

### Cycle 38 — VPM Reference

Finding status: no new defects found.

Reviewed areas:

- `vpmb.py` syntax/parse integrity.
- VPM source/reference parity expectations.
- Relationship between canonical VPM core and generated bundle.

Evidence:

- `python -m py_compile vpmb.py tools/build_vpm_bundle.py tools/check_engine_parity.py`
- `npm.cmd run check:engine-parity`

### Cycle 37 — RDP

Finding status: no new defects found.

Reviewed areas:

- PADI table depth ceiling lookup.
- Metric table max-depth rejection.
- Air/EAN32/EAN36 NDL lookup.
- Non-standard rec mixes falling back to air table.

Evidence:

- Browser-global VM probe confirmed:
  - zero depth rejected,
  - 18.1 m ceilings to the 21 m row,
  - 40 m max accepted,
  - >40 m rejected as 0 NDL,
  - custom `ean50` falls back to air.
- Full engine suite RDP cases pass.

## Verification Commands

Passed:

- `python dev/engine_regression.py`
- `python engine_validation_regression.py`
- `python dev/ccr_engine_validation_regression.py`
- `python dev/gas_core_regression.py`
- `python -m py_compile vpmb.py tools/build_vpm_bundle.py tools/check_engine_parity.py`
- `npm.cmd run check:engine-parity`

Final static/coverage gates are recorded in the commit verification output.

## App Improvements Recommended Next

- Keep engine-output gas labels canonical at source. UI renderers should not be
  the first place where `Air`, `100%`, or `OO/HH` formatting becomes correct.
- Add a small standalone Node engine-host fixture for VPM direct API tests. VPM
  has legitimate host dependencies; a reusable fixture would make future engine
  probes faster and less ad hoc.
- Add a direct VPM reference comparison smoke case for one standard OC profile
  and one trimix profile. The full reference file is large, so the comparison
  should be narrow and deterministic.
- Keep RDP intentionally narrow: only Air, EAN32, and EAN36 in rec mode. Custom
  gas fallback should remain covered because accidental custom-rec gas support
  would be a safety-contract change.

## Audit-System Improvements Recommended

- Keep this risk-first batch model: one batch report, one focused set of fixes,
  and one final verification sweep. Do not recreate Cycle 8-style closure loops.
- Implement `tools/seven_lens_ready_to_close.py` when practical, but keep it
  informational for frozen historical cycles.
- Cache or split broad coverage checks so engine-focused cycles do not wait on
  unrelated browser/UI suites unless source changes require them.
- Preserve generated artifact policy: source files are reviewed; generated
  bundles are checked by builders and parity.

## Final Gate Repairs Outside The Engine Batch

Final CI verification exposed two stale UI/audit contracts unrelated to the VPM
engine finding. They were fixed as part of this batch so the branch does not
land with red gates.

### Reviewed CSS Dependency Repair

Finding: `SUITE-UI-RESULTS-CSS-REGRESSION` failed
`SL-C07-CHIP-YELLOW-DISTINCT`.

Root cause:

- The current result-chip design no longer renders a natural yellow chip in the
  standard 40 m / 25 min profile.
- A light-theme foundation override also mapped `.chip-yellow` to
  `var(--status-orange)`, making yellow and orange chip classes visually
  identical when a yellow chip is present.

Fix:

- Restored `body.light-theme .chip-yellow` to `var(--yellow)`.
- Updated `dev/ui_results_css_regression.py` so the regression probes
  `.chip-yellow` and `.chip-orange` directly with temporary chips when the
  current plan does not naturally emit a yellow chip.
- Recorded a narrow Cycle 5 foundation dependency re-review as
  `NO_NEW_FINDING`; the old GF row isolation behavior was not touched.

Evidence:

- `python dev/ui_results_css_regression.py` passes.
- `python dev/ui_visual_contract_regression.py` passes.

### Visual Contract Catalog Repair

Finding: `SUITE-UI-VISUAL-CONTRACT-REGRESSION` exited successfully and emitted
all passing cases, but the audit runner marked the suite failed because four
newer case IDs were not declared in `docs/audit-units.json`.

Fix:

- Added the missing case IDs to `SUITE-UI-VISUAL-CONTRACT-REGRESSION`.
- Added matching stable evidence-catalog entries `REG-122` through `REG-125`.

Evidence:

- `python -m tools.audit run --profile ci` passes with 17/17 suites.
