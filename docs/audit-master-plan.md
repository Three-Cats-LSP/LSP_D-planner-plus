# Audit Master Plan v3.0

> V3 full-audit schedule. Policy, unit metadata, and risk-first execution order live in `docs/audit-units.json`.

**Baseline:** `2f4843b3d4032c07c95a08fa9407130c681998b0`
**Epoch:** `v3-full-reset`
**Units:** 207 total; 0 unread; 92 in progress; 3 read; 112 verified.
**Gate:** `python -m tools.audit check --profile static`

## Operating Rules

- After Cycle 9, execute cycles in the risk-first order below, not numeric order.
- Unit priority is metadata; risk-first cycle order is the audit execution queue.
- A cycle reads the listed application units; `max_new_application_lines` is sized to fit the unit bundle.
- Recalculate cycle line counts from current source before starting a cycle; split each cycle into <=600-line review sessions.
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

## Risk-First Execution Order

| Group | Focus | Cycles |
|---:|---|---|
| 1 | Production engines and safety-critical paths | 33, 34, 35, 36, 38, 37 |
| 2 | Planner mode/state paths | 19, 18, 20, 21, 22, 31 |
| 3 | Results, export, and consumption correctness | 24, 25, 10, 11, 12, 13 |
| 4 | Core UI renderers and interaction surfaces | 17, 14, 15, 16 |
| 5 | Runtime, boot, workers, and storage | 23, 29, 30, 32 |
| 6 | Presets, configuration, tissues, and reference settings | 27, 28, 26, 39 |
| 7 | Lower-risk generated, deployment, and release support | 40, 41, 42 |

Run the first unfinished cycle in this table. The numeric cycle table below remains the coverage registry, not the execution queue.

## Cycles

| Cycle | Application units | New lines | Engine re-verification | Acceptance |
|---:|---|---:|---|---|
| 1 | UI-MARKUP-HEADER | 730 | - | V3 cycle 1: header markup partial READ; SUITE-UI-STRUCTURE must be green; current lines: 730; sessions: 2 |
| 2 | UI-MARKUP-REC-PLANNER, UI-REC-PLANNER | 84 | - | Cycle 2a: REC planner markup + runRecPlan; SL-REC-DEPTH-BT-STEPPER; current lines: 84; sessions: 1 |
| 3 | UI-MARKUP-CONSUMPTION | 381 | - | Consumption markup partial READ; current lines: 381; sessions: 1 |
| 4 | UI-MARKUP-TOOLS, UI-MARKUP-MODALS | 612 | - | Tools and modals markup partials READ; current lines: 612; sessions: 2 |
| 5 | UI-CSS-FOUNDATION, UI-CSS-MODES | 758 | - | Foundation and modes CSS READ; current lines: 758; sessions: 2 |
| 6 | UI-CSS-CONTROLS | 548 | - | Controls CSS READ; current lines: 548; sessions: 1 |
| 7 | UI-CSS-RESULTS | 986 | - | Results CSS READ (2 bounded sessions); current lines: 986; sessions: 2 |
| 8 | UI-PLANNER-SHELL, UI-RESULTS-PANEL | 508 | - | Planner shell and results panel READ; current lines: 526; sessions: 1 |
| 9 | UI-ENVIRONMENT, UI-MODE-STATE | 999 | - | settings-core environment and mode state READ (1002 lines; >=2 bounded sessions); explicitly verify VPM switch behavior; enforce app-wide gas-switch terminology: the diving procedure is labeled and identified as "Gas switch" everywhere, with no user-facing "Gas change" labels or new gas-change IDs/classes/contracts; verify mobile warning/alert banners and gas-consumption warnings wrap inside the viewport without horizontal clipping or overflow; current lines: 999; sessions: 2 |
| 10 | APP-SURFACE-INTERVAL, APP-GAS-TABLE | 679 | - | Surface interval and gas table cores READ; current lines: 679; sessions: 2 |
| 11 | UI-GAS-INPUTS, UI-GAS-CARDS | 507 | ENG-ZHL-GAS | Gas card UI READ; current lines: 534; sessions: 1 |
| 12 | APP-GAS-PLAN | 546 | - | Gas plan core READ; current lines: 546; sessions: 1 |
| 13 | APP-CONTINGENCY | 594 | - | Contingency core READ; current lines: 594; sessions: 1 |
| 14 | APP-EXPORT | 3269 | - | export-core text/PDF READ across at least 6 bounded sessions; current lines: 3269; sessions: 6 |
| 15 | UI-PLOT-RENDER, UI-PLOT-WAYPOINTS | 629 | - | plot-core render and waypoints READ in at least 2 bounded sessions (641 lines total); current lines: 629; sessions: 2 |
| 16 | UI-TOOLS-PROFILE, UI-PLOT-INIT | 755 | - | Profile tool and plot init READ; current lines: 755; sessions: 2 |
| 17 | UI-VPM-RENDER, UI-ZHL-RESULTS | 955 | - | results-render-core READ; current lines: 955; sessions: 2 |
| 18 | UI-ZHL-DELEGATES, UI-CCR-DELEGATES | 511 | ENG-ZHL-SCHEDULE | ZHL/CCR delegate thin layer READ; current lines: 511; sessions: 1 |
| 19 | UI-DECO-PHYSICS, UI-SCHEDULE-INPUTS | 605 | ENG-ZHL-CCR | Deco physics and schedule inputs READ across at least 2 bounded sessions; current lines: 605; sessions: 2 |
| 20 | UI-ZHL-RUNNER-SETUP, UI-ZHL-RUNNER-ENGINE | 480 | ENG-ZHL-SCHEDULE | ZHL runner setup and engine invocation READ; current lines: 480; sessions: 1 |
| 21 | UI-ZHL-HEADLESS-HELPERS, UI-ZHL-HEADLESS-ENGINE | 588 | - | Headless ZHL path READ; current lines: 588; sessions: 1 |
| 22 | UI-VPM-RUNNER | 486 | ENG-VPM | VPM runner READ; current lines: 486; sessions: 1 |
| 23 | UI-RUNTIME-BOOTSTRAP, UI-APP-INIT | 390 | - | Runtime bootstrap and app init READ; current lines: 390; sessions: 1 |
| 24 | UI-ALGORITHM-SETTINGS, UI-SETTINGS-CONTROLS | 692 | - | Algorithm and settings controls READ (692 lines; >=2 bounded sessions); current lines: 692; sessions: 2 |
| 25 | UI-SETTINGS, UI-UNIT-HELPERS, UI-UNIT-SWITCHING | 1312 | - | Settings persistence and unit helpers READ across at least 3 bounded sessions; current lines: 1312; sessions: 3 |
| 26 | UI-TOOLS-TISSUES, UI-TOOLS-EXPOSURE, UI-TOOLS-GF | 851 | - | Tools panels READ in >=2 bounded sessions; implement and verify the tissue-saturation seven-band value scale in docs/tissue-saturation-color-roadmap.md, including UI/export parity and accessibility; current lines: 851; sessions: 2 |
| 27 | UI-PROFILE-PRESETS | 508 | - | Dive profile presets READ (depth/BT/mode ownership); current lines: 508; sessions: 1 |
| 28 | UI-CONFIG-PRESETS | 185 | - | Advanced config presets READ; current lines: 185; sessions: 1 |
| 29 | UI-BOOT | 2403 | - | index.html shell boot region READ; current lines: 2411; sessions: 5 |
| 30 | APP-SERVICE-WORKER, UI-PWA-LIFECYCLE, APP-MANIFEST | 425 | - | PWA and service worker READ; current lines: 425; sessions: 1 |
| 31 | APP-ZHL-WORKER, APP-ZHL-WORKER-BRIDGE | 159 | - | ZHL schedule worker and bridge READ; current lines: 159; sessions: 1 |
| 32 | APP-CAPACITOR-BRIDGE, APP-ANDROID-SELECT | 548 | - | Capacitor and Android select bridge READ; current lines: 548; sessions: 1 |
| 33 | ENG-ZHL-PHYSICS, ENG-ZHL-GAS | 373 | - | ZHL physics and gas canonical cores READ; current lines: 373; sessions: 1 |
| 34 | ENG-ZHL-SCHEDULE | 657 | - | ZHL schedule canonical core READ; current lines: 657; sessions: 2 |
| 35 | ENG-ZHL-CCR | 404 | - | ZHL CCR canonical core READ; current lines: 404; sessions: 1 |
| 36 | ENG-VPM | 2106 | - | VPM canonical core READ; current lines: 2106; sessions: 4 |
| 37 | ENG-RDP | 101 | - | PADI RDP engine READ; current lines: 101; sessions: 1 |
| 38 | ENG-VPM-REFERENCE | 2574 | - | VPM reference implementation READ; current lines: 2574; sessions: 5 |
| 39 | APP-DOWNLOAD | 119 | - | Download page READ; current lines: 119; sessions: 1 |
| 40 | - | 0 | TEST-ENGINE-REGRESSION, TEST-ENGINE-VALIDATION, TEST-GAS-CORE-REGRESSION | Engine and gas regression harnesses re-verified; current lines: 0; no application-source review |
| 41 | - | 0 | TEST-RUN-ALL, TEST-SW-LIFECYCLE, TEST-CCR-VALIDATION, TEST-CCR-DIFF-RUNNER, TEST-PSCR-E2E | Full regression umbrella and release-tier test paths re-verified; current lines: 0; no application-source review |
| 42 | APP-PACKAGE | 40 | CI-AUDIT, CI-MAIN, CI-APK, CI-DEPLOY | Package manifest and CI workflows READ; current lines: 40; sessions: 1 |
| 200 | UI-MARKUP-TEC-PLANNER | 562 | - | Cycle 2b: TECH planner markup; SL-C02-TRAVEL-DEPTH browser trace; current lines: 570; sessions: 1 |
| 201 | UI-PLANNER-INPUTS | 119 | - | Cycle 2c: view swap + persistence; SL-MODE-REC-TEC-ISOLATION; current lines: 119; sessions: 1 |

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
