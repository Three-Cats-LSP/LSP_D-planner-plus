# V4 Risk-First Batch Report: R01-R10

Date: 2026-07-09  
Branch: dev  
Baseline before this pass: `799a47eb3fa228b776484049ff6d1d7594ffad63`

## Summary

The first V4 risk-first batch reviewed the production decompression engines, engine reference paths, RDP narrowness, ZHL/VPM runner setup, and the newly extracted ZHL headless adapter.

No new app defects were found in R01-R10. The main implementation work was structural cleanup requested before resuming the batch: the remaining ZHL headless/browser adapter was extracted from `index.html` into `zhl-headless-adapter.js`, matching the cleaner VPM layout.

## Infrastructure Implemented

- Added `zhl-headless-adapter.js`.
- Removed the remaining ZHL headless adapter block from `index.html`.
- Kept public browser APIs unchanged:
  - `window.ZHLEngine.calculate(...)`
  - `window.ZHLEngine.calculateInWorker(...)`
  - `window.validateGasFractionsPct`
  - `window.validateEngineInputs`
  - `window.validateCcrCalculationInputs`
  - `window.validateZhlHeadlessProfile`
- Added the adapter to canonical runtime/deployment asset lists:
  - `ui/markup-header.html`
  - `tools/extract_ui_cores.py`
  - `tools/ui_assets.py`
  - `tools/build_pages_site.py`
  - `tools/sync_www.py`
  - `tools/check_engine_parity.py`
  - `sw.js`
- Added extractor protection so `index.html` fails structure checks if ZHL headless definitions are reintroduced inline.
- Recalculated active V4 audit unit boundaries and fingerprints.

## Cycle Results

| Cycle | Units | Result |
|---|---|---|
| R01 | `ENG-ZHL-PHYSICS`, `ENG-ZHL-GAS` | No findings |
| R02 | `ENG-ZHL-SCHEDULE` | No findings |
| R03 | `ENG-ZHL-CCR` | No findings |
| R04 | `ENG-VPM` | No findings |
| R05 | `ENG-VPM-REFERENCE` | No findings |
| R06 | `ENG-RDP` | No findings |
| R07 | `UI-DECO-PHYSICS`, `UI-SCHEDULE-INPUTS` | No findings |
| R08 | `UI-ZHL-DELEGATES`, `UI-CCR-DELEGATES` | No findings |
| R09 | `UI-ZHL-RUNNER-SETUP`, `UI-ZHL-RUNNER-ENGINE` | No findings |
| R10 | `UI-ZHL-HEADLESS-HELPERS`, `UI-ZHL-HEADLESS-ENGINE` | No findings; adapter extracted |

## Verification

Passed:

- `python tools/extract_ui_cores.py`
- `python tools/assemble_ui_html.py --verify`
- `python tools/audit_coverage.py --write-docs`
- `python dev/engine_regression.py` — 177/177 passed
- `node dev/vpm_direct_regression.js`
- `npm.cmd run check:engine-parity`
- `python dev/ui_visual_contract_regression.py`
- `python tools/seven_lens_protocol.py check-all --require-artifacts`
- `python -m tools.audit check --profile static`
- `python -m tools.audit run --profile ci`

## Recommendations

- Keep `index.html` as markup/bootstrap only. Runtime adapters should stay in extracted JS files.
- Continue V4 batches in risk-first order, with narrow app regressions first and broad CI gates second.
- Keep broad `SUITE-COVERAGE` out of the inner edit loop where possible; use it as a gate, not as the main debugging tool.
- If deeper VPM reference review is needed later, use narrow deterministic smoke comparisons rather than full reference-plan equivalence.

