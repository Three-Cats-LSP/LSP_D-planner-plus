# Audit Master Plan v4.0

> V4 risk-first reset schedule. Policy, unit metadata, frozen history, and active R-cycle order live in `docs/audit-units.json`.

**Baseline:** `2f4843b3d4032c07c95a08fa9407130c681998b0`
**Epoch:** `v4-risk-first-reset`
**Units:** 208 total; 0 unread; 110 in progress; 3 read; 95 verified.
**Gate:** `python -m tools.audit check --profile static`

## Operating Rules

- Execute active V4 `Rxx` cycles in the risk-first order below.
- Earlier `SL-Cxx` records are frozen historical evidence and are not the active execution queue.
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
| 1 | Production engines and safety-critical paths | R01, R02, R03, R04, R05, R06 |
| 2 | Planner mode/state and runner paths | R07, R08, R09, R10, R11, R12 |
| 3 | Results, export, and consumption correctness | R13, R14, R15, R16, R17, R18 |
| 4 | Core renderers and graph/export surfaces | R19, R20, R21, R22 |
| 5 | Runtime, boot, workers, and native | R23, R24, R25, R26 |
| 6 | Presets, tissues, lower-risk support | R27, R28, R29, R30, R31, R32, R33 |
| 7 | Markup, base CSS, and current design-lock re-review | R34, R35, R36, R37, R38, R39, R40, R41, R42 |

Run the first unfinished `Rxx` cycle in this table. The cycle table below is the active V4 coverage registry.

## Cycles

| Cycle | Application units | New lines | Engine re-verification | Acceptance |
|---:|---|---:|---|---|
| R01 | ENG-ZHL-PHYSICS, ENG-ZHL-GAS | 373 | - | V4 R01: ZHL physics and gas canonical cores risk-first READ; current lines: 373; sessions: 1 |
| R02 | ENG-ZHL-SCHEDULE | 657 | - | V4 R02: ZHL schedule canonical core risk-first READ; current lines: 657; sessions: 2 |
| R03 | ENG-ZHL-CCR | 404 | - | V4 R03: ZHL CCR canonical core risk-first READ; current lines: 404; sessions: 1 |
| R04 | ENG-VPM | 2106 | - | V4 R04: VPM canonical core risk-first READ; current lines: 2106; sessions: 4 |
| R05 | ENG-VPM-REFERENCE | 2574 | - | V4 R05: VPM reference implementation risk-first READ; current lines: 2574; sessions: 5 |
| R06 | ENG-RDP | 101 | - | V4 R06: PADI RDP engine risk-first READ; current lines: 101; sessions: 1 |
| R07 | UI-DECO-PHYSICS, UI-SCHEDULE-INPUTS | 637 | ENG-ZHL-CCR | V4 R07: Deco physics and schedule inputs risk-first READ; current lines: 637; sessions: 2 |
| R08 | UI-ZHL-DELEGATES, UI-CCR-DELEGATES | 515 | ENG-ZHL-SCHEDULE | V4 R08: ZHL/CCR delegate thin layer risk-first READ; current lines: 515; sessions: 1 |
| R09 | UI-ZHL-RUNNER-SETUP, UI-ZHL-RUNNER-ENGINE | 469 | ENG-ZHL-SCHEDULE | V4 R09: ZHL runner setup and engine invocation risk-first READ; current lines: 478; sessions: 1 |
| R10 | UI-ZHL-HEADLESS-HELPERS, UI-ZHL-HEADLESS-ENGINE | 285 | - | V4 R10: Headless ZHL path risk-first READ; current lines: 588; sessions: 1 |
| R11 | UI-VPM-RUNNER | 491 | ENG-VPM | V4 R11: VPM runner risk-first READ; current lines: 491; sessions: 1 |
| R12 | APP-ZHL-WORKER, APP-ZHL-WORKER-BRIDGE | 159 | - | V4 R12: ZHL schedule worker and bridge risk-first READ; current lines: 159; sessions: 1 |
| R13 | UI-ALGORITHM-SETTINGS, UI-SETTINGS-CONTROLS | 721 | - | V4 R13: Algorithm and settings controls risk-first READ; current lines: 721; sessions: 2 |
| R14 | UI-SETTINGS, UI-UNIT-HELPERS, UI-UNIT-SWITCHING | 1200 | - | V4 R14: Settings persistence and unit helpers risk-first READ; current lines: 1200; sessions: 2 |
| R15 | APP-SURFACE-INTERVAL, APP-GAS-TABLE | 679 | - | V4 R15: Surface interval and gas table cores risk-first READ; current lines: 679; sessions: 2 |
| R16 | UI-GAS-INPUTS, UI-GAS-CARDS | 507 | ENG-ZHL-GAS | V4 R16: Gas input/card UI risk-first READ; current lines: 507; sessions: 1 |
| R17 | APP-GAS-PLAN | 546 | - | V4 R17: Gas plan core risk-first READ; current lines: 546; sessions: 1 |
| R18 | APP-CONTINGENCY | 594 | - | V4 R18: Contingency core risk-first READ; current lines: 594; sessions: 1 |
| R19 | UI-VPM-RENDER, UI-ZHL-RESULTS | 968 | - | V4 R19: VPM/ZHL results rendering risk-first READ; current lines: 968; sessions: 2 |
| R20 | APP-EXPORT | 3269 | - | V4 R20: Export text/PDF risk-first READ; current lines: 3269; sessions: 6 |
| R21 | UI-PLOT-RENDER, UI-PLOT-WAYPOINTS | 632 | - | V4 R21: Plot render and waypoint graph risk-first READ; current lines: 632; sessions: 2 |
| R22 | UI-TOOLS-PROFILE, UI-PLOT-INIT | 755 | - | V4 R22: Profile tool and plot init risk-first READ; current lines: 755; sessions: 2 |
| R23 | UI-RUNTIME-BOOTSTRAP, UI-APP-INIT | 390 | - | V4 R23: Runtime bootstrap and app init risk-first READ; current lines: 390; sessions: 1 |
| R24 | UI-BOOT | 2452 | - | V4 R24: index.html shell boot region risk-first READ; current lines: 2414; sessions: 5 |
| R25 | APP-SERVICE-WORKER, UI-PWA-LIFECYCLE, APP-MANIFEST | 429 | - | V4 R25: PWA/service-worker lifecycle risk-first READ; current lines: 428; sessions: 1 |
| R26 | APP-CAPACITOR-BRIDGE, APP-ANDROID-SELECT | 548 | - | V4 R26: Capacitor and Android bridge risk-first READ; current lines: 548; sessions: 1 |
| R27 | UI-PROFILE-PRESETS | 508 | - | V4 R27: Dive profile presets risk-first READ; current lines: 508; sessions: 1 |
| R28 | UI-CONFIG-PRESETS | 185 | - | V4 R28: Advanced config presets risk-first READ; current lines: 185; sessions: 1 |
| R29 | UI-TOOLS-TISSUES, UI-TOOLS-EXPOSURE, UI-TOOLS-GF | 903 | - | V4 R29: Tools tissues/exposure/GF risk-first READ; current lines: 904; sessions: 2 |
| R30 | APP-DOWNLOAD | 120 | - | V4 R30: Download page risk-first READ; current lines: 120; sessions: 1 |
| R31 | - | 0 | TEST-ENGINE-REGRESSION, TEST-ENGINE-VALIDATION, TEST-GAS-CORE-REGRESSION | V4 R31: Engine and gas regression harnesses re-verified; no application-source review; current lines: 0; no application-source review |
| R32 | - | 0 | TEST-RUN-ALL, TEST-SW-LIFECYCLE, TEST-CCR-VALIDATION, TEST-CCR-DIFF-RUNNER, TEST-PSCR-E2E | V4 R32: Full regression umbrella and release-tier test paths re-verified; no application-source review; current lines: 0; no application-source review |
| R33 | APP-PACKAGE | 40 | CI-AUDIT, CI-MAIN, CI-APK, CI-DEPLOY | V4 R33: Package manifest and CI workflows risk-first READ; current lines: 40; sessions: 1 |
| R34 | UI-MARKUP-HEADER | 787 | - | V4 R34: Header markup risk-first READ; current lines: 787; sessions: 2 |
| R35 | UI-MARKUP-REC-PLANNER, UI-REC-PLANNER | 82 | - | V4 R35: REC planner markup and runner risk-first READ; current lines: 84; sessions: 1 |
| R36 | UI-MARKUP-TEC-PLANNER, UI-PLANNER-INPUTS | 679 | - | V4 R36: TEC planner markup and planner input ownership risk-first READ; current lines: 681; sessions: 2 |
| R37 | UI-MARKUP-CONSUMPTION | 381 | - | V4 R37: Consumption markup risk-first READ; current lines: 381; sessions: 1 |
| R38 | UI-MARKUP-TOOLS, UI-MARKUP-MODALS | 604 | - | V4 R38: Tools and modal markup risk-first READ; current lines: 612; sessions: 2 |
| R39 | UI-CSS-FOUNDATION, UI-CSS-MODES | 760 | - | V4 R39: Foundation and mode CSS risk-first READ; current lines: 760; sessions: 2 |
| R40 | UI-CSS-CONTROLS | 548 | - | V4 R40: Controls CSS risk-first READ; current lines: 548; sessions: 1 |
| R41 | UI-CSS-RESULTS | 1044 | - | V4 R41: Results CSS risk-first design-lock READ; current lines: 1044; sessions: 2 |
| R42 | UI-PLANNER-SHELL, UI-RESULTS-PANEL | 805 | - | V4 R42: Planner shell and results panel design-lock READ; current lines: 805; sessions: 2 |

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
