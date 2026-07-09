# V4 Risk-First Batch Report: R11-R22

Date: 2026-07-09  
Branch: dev  
Baseline before this pass: `6d18dd60c2203cf1eb8d683d0c52e6a4671582c8`

## Summary

This V4 batch reviewed planner mode/state paths, ZHL/VPM runner paths, gas and contingency paths, result rendering, export, and plot surfaces.

One real defect was found and fixed in the ZHL worker bridge. The rest of the batch held under targeted engine, visual, gas, contingency, export/native, and assembly checks.

## Cycle Results

| Cycle | Units | Result |
|---|---|---|
| R11 | `UI-VPM-RUNNER` | No findings |
| R12 | `APP-ZHL-WORKER`, `APP-ZHL-WORKER-BRIDGE` | 1 finding fixed |
| R13 | `UI-ALGORITHM-SETTINGS`, `UI-SETTINGS-CONTROLS` | No findings |
| R14 | `UI-SETTINGS`, `UI-UNIT-HELPERS`, `UI-UNIT-SWITCHING` | No findings |
| R15 | `APP-SURFACE-INTERVAL`, `APP-GAS-TABLE` | No findings |
| R16 | `UI-GAS-INPUTS`, `UI-GAS-CARDS` | No findings |
| R17 | `APP-GAS-PLAN` | No findings |
| R18 | `APP-CONTINGENCY` | No findings |
| R19 | `UI-VPM-RENDER`, `UI-ZHL-RESULTS` | No findings |
| R20 | `APP-EXPORT` | No findings |
| R21 | `UI-PLOT-RENDER`, `UI-PLOT-WAYPOINTS` | No findings |
| R22 | `UI-TOOLS-PROFILE`, `UI-PLOT-INIT` | No findings |

## Finding Fixed

### R12-WORKER-01 — ZHL worker calculation errors killed the worker bridge

Severity: HIGH  
File: `zhl-worker-bridge.js`

The worker bridge treated a normal worker response with `ok:false` as a worker crash. That path called `handleWorkerFailure(...)`, which rejects all pending jobs, terminates the worker, increments the consecutive failure counter, and can eventually disable worker use. A calculation error should reject only the matching request.

Fix: the `ok:false` branch now calls `settlePending(id, false, new Error(...))` and leaves the worker alive.

Regression: `engine_validation_regression.py` now scripts a worker that returns one synthetic calculation error, then a successful second result. The test passes only if the first request rejects and the second request still succeeds through the worker bridge.

## Verification

Passed:

- `python engine_validation_regression.py` — 36/36 passed
- `python dev/engine_regression.py` — 177/177 passed
- `node dev/vpm_direct_regression.js`
- `npm.cmd run check:engine-parity`
- `python dev/ui_visual_contract_regression.py`
- `python dev/ui_shell_results_regression.py`
- `python dev/ui_results_css_regression.py`
- `python dev/ui_css_regression.py`
- `python dev/gas_core_regression.py`
- `python dev/surf_interval_regression.py`
- `python dev/run_native_regression.py`
- `python tools/assemble_ui_html.py --verify`
- `python tools/audit_coverage.py --write-docs`
- `python tools/seven_lens_protocol.py check-all --require-artifacts`
- `python -m tools.audit check --profile static`
- `python -m tools.audit run --profile ci`

## Workflow Notes

The simplified V4 flow avoided the old closure loop: review, fix, targeted regression, then gates. One practical speed issue showed up: `sync_www`-backed browser tests should not run in parallel because they share the `www` staging directory and can create false missing-file failures. Sequential runs were clean.

## Recommendations

- Add a stable registry case ID for the new worker calculation-error bridge regression during the next lightweight registry cleanup.
- Consider letting `dev/test_http.py` publish to an isolated temp directory per test process, so UI suites can run safely in parallel.
- Keep export coverage pragmatic: native bridge, static, visual, and assembly checks are enough unless a specific export bug appears.
