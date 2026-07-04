# Audit Master Plan v3.0

> V3 full-audit schedule (cycles 1+). Policy and unit metadata live in `docs/audit-units.json`.

**Baseline:** `2f4843b3d4032c07c95a08fa9407130c681998b0`
**Epoch:** `v3-full-reset`
**Units:** 188 total; 0 unread; 62 in progress; 1 read; 125 verified.
**Gate:** `python -m tools.audit check --profile static`

## Operating Rules

- Audit P0 before P1, then P2/P3. Unit priority is not finding severity.
- A cycle reads the listed application units; `max_new_application_lines` is sized to fit the unit bundle.
- Record actual findings only; there are no finding quotas or projections.
- `VERIFIED` requires a current fingerprint and evidence that passes in the current audit profile.
- Generated artifacts are validated by their generator and parity command, not manual READ coverage.
- Open CRITICAL or HIGH findings fail the coverage gate and block release.

## Seven Lenses

1. Arithmetic and physics
2. Control flow
3. State and mutation
4. API contracts
5. Canonical/generated parity
6. Safety regression
7. Tooling and CI

## Cycles

| Cycle | Application units | New lines | Engine re-verification | Acceptance |
|---:|---|---:|---|---|
| 1 | UI-MARKUP-HEADER | 750 | - | V3 cycle 1: header markup partial READ; SUITE-UI-STRUCTURE must be green |
| 2 | UI-MARKUP-REC-PLANNER, UI-REC-PLANNER | 84 | - | Cycle 2a: REC planner markup + runRecPlan; SL-REC-DEPTH-BT-STEPPER |
| 3 | UI-MARKUP-CONSUMPTION | 381 | - | Consumption markup partial READ |
| 4 | UI-MARKUP-TOOLS, UI-MARKUP-MODALS | 612 | - | Tools and modals markup partials READ |
| 5 | UI-CSS-FOUNDATION, UI-CSS-MODES | 756 | - | Foundation and modes CSS READ |
| 6 | UI-CSS-CONTROLS | 528 | - | Controls CSS READ |
| 7 | UI-CSS-RESULTS | 931 | - | Results CSS READ |
| 8 | UI-PLANNER-SHELL, UI-RESULTS-PANEL | 487 | - | Planner shell and results panel READ |
| 9 | UI-ENVIRONMENT, UI-MODE-STATE | 992 | - | settings-core environment and mode state READ |
| 10 | APP-SURFACE-INTERVAL, APP-GAS-TABLE | 679 | - | Surface interval and gas table cores READ |
| 11 | UI-GAS-INPUTS, UI-GAS-CARDS | 516 | ENG-ZHL-GAS | Gas card UI READ |
| 12 | APP-GAS-PLAN | 546 | - | Gas plan core READ |
| 13 | APP-CONTINGENCY | 562 | - | Contingency core READ |
| 14 | APP-EXPORT | 3255 | - | export-core text/PDF READ |
| 15 | UI-PLOT-RENDER, UI-PLOT-WAYPOINTS | 621 | - | plot-core render and waypoints READ |
| 16 | UI-TOOLS-PROFILE, UI-PLOT-INIT | 755 | - | Profile tool and plot init READ |
| 17 | UI-VPM-RENDER, UI-ZHL-RESULTS | 1064 | - | results-render-core READ |
| 18 | UI-ZHL-DELEGATES, UI-CCR-DELEGATES | 511 | ENG-ZHL-SCHEDULE | ZHL/CCR delegate thin layer READ |
| 19 | UI-DECO-PHYSICS, UI-SCHEDULE-INPUTS | 597 | ENG-ZHL-CCR | Deco physics and schedule inputs READ |
| 20 | UI-ZHL-RUNNER-SETUP, UI-ZHL-RUNNER-ENGINE | 479 | ENG-ZHL-SCHEDULE | ZHL runner setup and engine invocation READ |
| 21 | UI-ZHL-HEADLESS-HELPERS, UI-ZHL-HEADLESS-ENGINE | 588 | - | Headless ZHL path READ |
| 22 | UI-VPM-RUNNER | 473 | ENG-VPM | VPM runner READ |
| 23 | UI-RUNTIME-BOOTSTRAP, UI-APP-INIT | 393 | - | Runtime bootstrap and app init READ |
| 24 | UI-ALGORITHM-SETTINGS, UI-SETTINGS-CONTROLS | 674 | - | Algorithm and settings controls READ |
| 25 | UI-SETTINGS, UI-UNIT-HELPERS, UI-UNIT-SWITCHING | 1281 | - | Settings persistence and unit helpers READ |
| 26 | UI-TOOLS-TISSUES, UI-TOOLS-EXPOSURE, UI-TOOLS-GF | 851 | - | Tools panels READ |
| 27 | UI-PROFILE-PRESETS | 506 | - | Dive profile presets READ (depth/BT/mode ownership) |
| 28 | UI-CONFIG-PRESETS | 185 | - | Advanced config presets READ |
| 29 | UI-BOOT | 2418 | - | index.html shell boot region READ |
| 30 | APP-SERVICE-WORKER, UI-PWA-LIFECYCLE, APP-MANIFEST | 440 | - | PWA and service worker READ |
| 31 | APP-ZHL-WORKER, APP-ZHL-WORKER-BRIDGE | 159 | - | ZHL schedule worker and bridge READ |
| 32 | APP-CAPACITOR-BRIDGE, APP-ANDROID-SELECT | 548 | - | Capacitor and Android select bridge READ |
| 33 | ENG-ZHL-PHYSICS, ENG-ZHL-GAS | 373 | - | ZHL physics and gas canonical cores READ |
| 34 | ENG-ZHL-SCHEDULE | 657 | - | ZHL schedule canonical core READ |
| 35 | ENG-ZHL-CCR | 404 | - | ZHL CCR canonical core READ |
| 36 | ENG-VPM | 2099 | - | VPM canonical core READ |
| 37 | ENG-RDP | 101 | - | PADI RDP engine READ |
| 38 | ENG-VPM-REFERENCE | 2574 | - | VPM reference implementation READ |
| 39 | APP-DOWNLOAD | 119 | - | Download page READ |
| 40 | - | 0 | TEST-ENGINE-REGRESSION, TEST-ENGINE-VALIDATION, TEST-GAS-CORE-REGRESSION | Engine and gas regression harnesses re-verified |
| 41 | - | 0 | TEST-RUN-ALL, TEST-SW-LIFECYCLE, TEST-CCR-VALIDATION, TEST-CCR-DIFF-RUNNER, TEST-PSCR-E2E | Full regression umbrella and release-tier test paths re-verified |
| 42 | APP-PACKAGE | 40 | CI-AUDIT, CI-MAIN, CI-APK, CI-DEPLOY | Package manifest and CI workflows READ |
| 200 | UI-MARKUP-TEC-PLANNER | 557 | - | Cycle 2b: TECH planner markup; SL-C02-TRAVEL-DEPTH browser trace |
| 201 | UI-PLANNER-INPUTS | 119 | - | Cycle 2c: view swap + persistence; SL-MODE-REC-TEC-ISOLATION |

## Definition of Done

- Every registered unit is READ and at least 85% are VERIFIED.
- No open CRITICAL or HIGH findings remain.
- `python -m tools.audit run --profile release` passes with every required leaf suite.
- No tracked source is unregistered, stale, overlapping, or uncovered.
- Generated bundles and deployment mirrors reproduce cleanly from canonical sources.

## Session Card

1. Pull `main`; run `python -m tools.audit check --profile static`.
2. Read each selected unit in full and apply all seven lenses.
3. Record unit ID, exact lines, lens, severity, issue, and regression case ID.
4. Re-read fixed units, run the relevant suite, refresh fingerprints, and regenerate these reports.
5. Close the cycle only when the registry and worktree are clean.
