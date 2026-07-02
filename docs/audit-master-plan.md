# Audit Master Plan v3.0

> V3 full-audit schedule (cycles 1+). Policy and unit metadata live in `docs/audit-units.json`.

**Baseline:** `2f4843b3d4032c07c95a08fa9407130c681998b0`
**Epoch:** `v3-full-reset`
**Units:** 168 total; 101 unread; 41 in progress; 24 read; 2 verified.
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
| 1 | UI-MARKUP-HEADER | 837 | - | V3 cycle 1: header markup partial READ; SUITE-UI-STRUCTURE must be green |
| 2 | UI-MARKUP-PLANNER | 493 | - | Planner markup partial READ |
| 3 | UI-MARKUP-CONSUMPTION | 381 | - | Consumption markup partial READ |
| 4 | UI-MARKUP-TOOLS, UI-MARKUP-MODALS | 612 | - | Tools and modals markup partials READ |
| 5 | UI-CSS-FOUNDATION, UI-CSS-MODES | 826 | - | Foundation and modes CSS READ |
| 6 | UI-CSS-CONTROLS | 528 | - | Controls CSS READ |
| 7 | UI-CSS-RESULTS | 924 | - | Results CSS READ |
| 8 | UI-PLANNER-SHELL, UI-RESULTS-PANEL | 506 | - | Planner shell and results panel READ |
| 9 | UI-ENVIRONMENT, UI-MODE-STATE | 932 | - | settings-core environment and mode state READ |
| 10 | APP-SURFACE-INTERVAL, APP-GAS-TABLE | 674 | - | Surface interval and gas table cores READ |
| 11 | UI-GAS-INPUTS, UI-GAS-CARDS | 497 | ENG-ZHL-GAS | Gas card UI READ |
| 12 | APP-GAS-PLAN | 546 | - | Gas plan core READ |
| 13 | APP-CONTINGENCY | 562 | - | Contingency core READ |
| 14 | APP-EXPORT | 3252 | - | export-core text/PDF READ |
| 15 | UI-PLOT-RENDER, UI-PLOT-WAYPOINTS | 621 | - | plot-core render and waypoints READ |
| 16 | UI-TOOLS-PROFILE, UI-PLOT-INIT | 701 | - | Profile tool and plot init READ |
| 17 | UI-VPM-RENDER, UI-ZHL-RESULTS | 1064 | - | results-render-core READ |
| 18 | UI-ZHL-DELEGATES, UI-CCR-DELEGATES | 511 | ENG-ZHL-SCHEDULE | ZHL/CCR delegate thin layer READ |
| 19 | UI-DECO-PHYSICS, UI-SCHEDULE-INPUTS | 597 | ENG-ZHL-CCR | Deco physics and schedule inputs READ |
| 20 | UI-ZHL-RUNNER-SETUP, UI-ZHL-RUNNER-ENGINE | 479 | ENG-ZHL-SCHEDULE | ZHL runner setup and engine invocation READ |
| 21 | UI-ZHL-HEADLESS-HELPERS, UI-ZHL-HEADLESS-ENGINE | 588 | - | Headless ZHL path READ |
| 22 | UI-VPM-RUNNER | 473 | ENG-VPM | VPM runner READ |
| 23 | UI-RUNTIME-BOOTSTRAP, UI-APP-INIT | 393 | - | Runtime bootstrap and app init READ |
| 24 | UI-ALGORITHM-SETTINGS, UI-SETTINGS-CONTROLS | 671 | - | Algorithm and settings controls READ |
| 25 | UI-SETTINGS, UI-UNIT-HELPERS, UI-UNIT-SWITCHING | 1163 | - | Settings persistence and unit helpers READ |
| 26 | UI-TOOLS-TISSUES, UI-TOOLS-EXPOSURE, UI-TOOLS-GF | 851 | - | Tools panels READ |
| 27 | UI-PROFILE-PRESETS, UI-CONFIG-PRESETS | 559 | - | Profile and config presets READ |
| 28 | UI-BOOT | 2366 | - | index.html shell boot region READ |
| 29 | APP-SERVICE-WORKER, UI-PWA-LIFECYCLE, APP-MANIFEST | 438 | - | PWA and service worker READ |
| 30 | APP-ZHL-WORKER, APP-ZHL-WORKER-BRIDGE | 159 | - | ZHL schedule worker and bridge READ |
| 31 | APP-CAPACITOR-BRIDGE, APP-ANDROID-SELECT | 548 | - | Capacitor and Android select bridge READ |
| 32 | ENG-ZHL-PHYSICS, ENG-ZHL-GAS | 373 | - | ZHL physics and gas canonical cores READ |
| 33 | ENG-ZHL-SCHEDULE | 657 | - | ZHL schedule canonical core READ |
| 34 | ENG-ZHL-CCR | 404 | - | ZHL CCR canonical core READ |
| 35 | ENG-VPM | 2099 | - | VPM canonical core READ |
| 36 | ENG-RDP | 101 | - | PADI RDP engine READ |
| 37 | ENG-VPM-REFERENCE | 2574 | - | VPM reference implementation READ |
| 38 | APP-DOWNLOAD | 119 | - | Download page READ |
| 39 | - | 0 | TEST-ENGINE-REGRESSION, TEST-ENGINE-VALIDATION, TEST-GAS-CORE-REGRESSION | Engine and gas regression harnesses re-verified |
| 40 | - | 0 | TEST-RUN-ALL, TEST-SW-LIFECYCLE, TEST-CCR-VALIDATION, TEST-CCR-DIFF-RUNNER, TEST-PSCR-E2E | Full regression umbrella and release-tier test paths re-verified |
| 41 | APP-PACKAGE | 40 | CI-AUDIT, CI-MAIN, CI-APK, CI-DEPLOY | Package manifest and CI workflows READ |

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
