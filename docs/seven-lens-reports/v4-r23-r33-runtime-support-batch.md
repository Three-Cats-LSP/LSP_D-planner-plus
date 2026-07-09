# V4 Risk-First Batch Report: R23-R33

Date: 2026-07-09  
Branch: dev  
Baseline before this pass: `c6daedb9c63c8e2217d0f3f8f5979cc517f346b0`

## Summary

This pass handled the final V4 risk-first batches:

- Batch 5: runtime boot, PWA/service worker, Capacitor, Android select
- Batch 6: presets, tools/tissues/exposure/GF, download page
- Batch 7: regression harnesses, release umbrella, package/CI metadata

No new app defects were found in R23-R33. Before running the batches, the requested workflow improvements were implemented.

## Improvements Implemented Before The Batch

### REG-139 worker regression ID

Added stable registry case `REG-139` for `ZHL-WORKER-CALC-ERROR-SINGLE-REQUEST`. The engine validation suite now emits this specific case in addition to the broad `engine-input-validation` case.

This protects the R12 worker bridge fix from becoming an anonymous test inside a generic suite.

### Parallel-safe UI test serving

`dev/test_http.py` already served from a per-process temp copy, but multiple browser suites could still run `sync_www.py` against the shared `www/` directory at the same time. The server helper now holds a cross-process lock around `sync_www.py` and the `www` snapshot copy.

Validation: `dev/ui_shell_results_regression.py` and `dev/ui_results_css_regression.py` passed while running in parallel.

### Export coverage kept pragmatic

No new broad export trace was added. Export remains covered by the dedicated export regression, native bridge regression, assembly/parity/static gates, and visual contracts. This keeps the fast V4 workflow from growing another slow audit branch without a concrete export defect.

### Pages build made parallel-safe

The first release-profile attempt exposed another shared-output race when CI and release profiles were run together: both tried to rebuild `_pages/` at the same time. `tools/build_pages_site.py` now holds a cross-process lock while writing `_pages/` and `site-assets-manifest.txt`.

## Cycle Results

| Cycle | Units | Result |
|---|---|---|
| R23 | `UI-RUNTIME-BOOTSTRAP`, `UI-APP-INIT` | No findings |
| R24 | `UI-BOOT` | No findings |
| R25 | `APP-SERVICE-WORKER`, `UI-PWA-LIFECYCLE`, `APP-MANIFEST` | No findings |
| R26 | `APP-CAPACITOR-BRIDGE`, `APP-ANDROID-SELECT` | No findings |
| R27 | `UI-PROFILE-PRESETS` | No findings |
| R28 | `UI-CONFIG-PRESETS` | No findings |
| R29 | `UI-TOOLS-TISSUES`, `UI-TOOLS-EXPOSURE`, `UI-TOOLS-GF` | No findings |
| R30 | `APP-DOWNLOAD` | No findings |
| R31 | Engine and gas regression harnesses | No findings |
| R32 | Full regression umbrella and release-tier tests | No findings |
| R33 | Package manifest and CI workflows | No findings |

## Verification

Passed:

- `python engine_validation_regression.py` — 36/36 passed, including `REG-139`
- Parallel browser-suite smoke:
  - `python dev/ui_shell_results_regression.py`
  - `python dev/ui_results_css_regression.py`
- `python tools/assemble_ui_html.py --verify`
- `python tools/run_ui_structure_suite.py`
- `python dev/run_native_regression.py`
- `python dev/sw_lifecycle_test.py`
- `python dev/ui_visual_contract_regression.py`
- `python dev/surf_interval_regression.py`
- `python dev/gas_core_regression.py`
- `python tools/build_pages_site.py`
- `python dev/engine_regression.py` — 177/177 passed
- `python dev/ccr_engine_validation_regression.py` — 28/28 passed
- `SKIP_AUDIT=1 python dev/validate_pscr_e2e.py`
- `python dev/run_ccr_differential.py`
- `python dev/run_android_compile_check.py` — skipped locally because no Android SDK is configured
- `node dev/vpm_direct_regression.js`
- `python tools/audit_coverage.py --write-docs`
- `python tools/seven_lens_protocol.py check-all --require-artifacts`
- `python -m tools.audit check --profile static`
- `python -m tools.audit run --profile ci`
- `python -m tools.audit run --profile release`

## Recommendations

- Keep `sync_www` serialization in place unless all browser suites move to fully isolated build directories.
- Keep `build_pages_site.py` serialized unless release/profile gates stop sharing `_pages/`.
- Keep pSCR E2E on the registered `SKIP_AUDIT=1` path locally; the old `audit.py` path is not part of the simplified V4 loop.
- Local Android compile remains dependent on a configured SDK. Treat GitHub Actions as the authoritative Android compile gate when the SDK is absent locally.
