# Audit Master Plan v2.0

> Generated schedule and totals. Policy and unit metadata live in `docs/audit-units.json`.

**Baseline:** `fd805111eab2fba349a9303a6e208106b798f82b`
**Units:** 167 total; 50 unread; 76 in progress; 35 read; 6 verified.
**Gate:** `python -m tools.audit check --profile static`

## Operating Rules

- Audit P0 before P1, then P2/P3. Unit priority is not finding severity.
- A cycle may read at most 600 new application-source lines plus one bounded engine re-verification unit.
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

## Cycles 5-12

| Cycle | Application units | New lines | Engine re-verification | Acceptance |
|---:|---|---:|---|---|
| 5 | UI-ZHL-DELEGATES, UI-CCR-DELEGATES | 511 | ENG-ZHL-SCHEDULE | Delegate units fully READ; schedule findings linked to regression IDs |
| 6 | UI-DECO-PHYSICS, UI-SCHEDULE-INPUTS | 597 | ENG-ZHL-CCR | Physics and schedule input paths READ; no unresolved P0 finding |
| 7 | UI-SETTINGS-CONTROLS, UI-VPM-RUNNER | 860 | ENG-VPM | Settings restoration and VPM invocation contracts READ |
| 8 | UI-VPM-RENDER | 531 | ENG-VPM | VPM rendering and safety warning propagation READ |
| 9 | UI-GAS-CARDS | 280 | ENG-ZHL-GAS | Dynamic gas-card units and persistence READ |
| 10 | UI-GAS-INPUTS, UI-ZHL-RUNNER-SETUP | 344 | ENG-ZHL-SCHEDULE | Gas validation and ZHL parameter construction READ |
| 11 | UI-ZHL-RUNNER-ENGINE | 352 | ENG-ZHL-SCHEDULE | Canonical ZHL execution path READ with parity evidence |
| 12 | UI-ZHL-RESULTS | 533 | ENG-ZHL-PHYSICS | Result construction, exposure totals, and safety fields READ |
| 13 | UI-ZHL-HEADLESS-HELPERS | 201 | - | Headless ZHL helper path READ; issue #152 |
| 14 | UI-ZHL-HEADLESS-ENGINE | 387 | - | Headless ZHL engine invocation READ; issue #153 |
| 15 | UI-PLOT-INIT, UI-PLOT-RENDER | 878 | - | Profile plot init and render READ; issue #154 |
| 16 | UI-PLOT-WAYPOINTS | 182 | - | Waypoint plot interaction READ; issue #155 |
| 17 | UI-TOOLS-TISSUES, UI-TOOLS-EXPOSURE | 535 | - | Tissue and exposure tools READ; issue #156 |
| 18 | UI-TOOLS-GF, UI-TOOLS-PROFILE | 578 | - | GF and profile tools READ; issue #157 |
| 19 | UI-SETTINGS | 368 | - | Settings persistence READ; issue #158 |
| 20 | UI-PROFILE-PRESETS, UI-CONFIG-PRESETS | 559 | - | Profile and config presets READ; issue #159 |
| 21 | UI-APP-INIT | 175 | - | App init and boot hooks READ; issue #160 |
| 22 | - | 0 | UI-ZHL-DELEGATES | ZHL delegate re-read READ; issue #161 |
| 23 | UI-RUNTIME-BOOTSTRAP | 218 | - | Runtime bootstrap READ; issue #162 |
| 24 | UI-ALGORITHM-SETTINGS | 284 | - | Algorithm settings READ; issue #163 |
| 25 | - | 0 | APP-CONTINGENCY | Contingency core READ; issue #164 |
| 26 | - | 0 | APP-EXPORT, APP-SERVICE-WORKER | Export and service worker READ; issue #165 |
| 27 | - | 0 | ENG-VPM | VPM engine re-read READ; issue #166 |
| 28 | APP-PACKAGE | 40 | CI-AUDIT, CI-APK, CI-MAIN, CI-DEPLOY, CI-NOTIFY | Package manifest and CI workflows READ; issue #167 |
| 29 | - | 0 | NATIVE-MAIN-ACTIVITY, NATIVE-BUILD-APP, NATIVE-FILE-PATHS, TEST-CCR-VALIDATION, TEST-CCR-DIFF-RUNNER | Native Android and CCR test paths READ; issue #168 |
| 30 | - | 0 | TEST-RUN-ALL, TEST-ENGINE-REGRESSION, TEST-ENGINE-VALIDATION, TEST-GAS-CORE-REGRESSION | Test runner suite READ; issue #169 |
| 31 | - | 0 | ENG-ZHL-CCR, UI-ZHL-HEADLESS-ENGINE, APP-CONTINGENCY, APP-SERVICE-WORKER, TEST-ENGINE-REGRESSION, TEST-SW-LIFECYCLE | C-04 trimix inert parity, pSCR environment sync, contingency MOD, CCR repetitive NDL phase, and deployed SW runtime assets verified by REG-39 through REG-42 and REG-45 |
| 32 | - | 0 | APP-CONTINGENCY, APP-GAS-PLAN, UI-SETTINGS, TEST-ENGINE-REGRESSION, TEST-PSCR-E2E | Contingency stress SAC, eligible bailout inventory, gas-switch review, error recovery, and settings restore cleanup verified by REG-43 and REG-44 |
| 33 | - | 0 | APP-CONTINGENCY, APP-GAS-PLAN, TEST-ENGINE-REGRESSION | Contingency ppO2 warning, primary gas state immutability, full-precision gas sufficiency, and primary table isolation verified by REG-47 through REG-50 |
| 34 | - | 0 | UI-GAS-INPUTS, UI-CCR-DELEGATES, TEST-ENGINE-REGRESSION | Historical UI-04/UI-05 scope: richest breathable bailout reserve selection, directionally safe diluent guidance, and invalid custom-gas MOD suppression verified by REG-51 through REG-53 |
| 35 | - | 0 | UI-GAS-CARDS, UI-ZHL-RUNNER-SETUP, ENG-ZHL-SCHEDULE, TEST-ENGINE-REGRESSION | Imperial pure-O2 switch depth stays in metres; headless/worker ZHL API propagates wholeMinStops; gas cards and runner setup READ clean verified by REG-54 and REG-55 |
| 36 | UI-MARKUP-HEADER | 837 | - | Header markup partial READ; SUITE-UI-STRUCTURE green |
| 37 | UI-MARKUP-PLANNER | 493 | - | Planner markup partial READ |
| 38 | UI-MARKUP-CONSUMPTION | 381 | - | Consumption markup partial READ |
| 39 | UI-MARKUP-TOOLS, UI-MARKUP-MODALS | 612 | - | Tools and modals markup partials READ |
| 40 | UI-CSS-FOUNDATION, UI-CSS-MODES, UI-CSS-CONTROLS, UI-CSS-RESULTS | 2278 | - | Split CSS design system READ |
| 41 | UI-RESULTS-PANEL, UI-PLANNER-SHELL | 506 | - | Results panel and planner shell READ |
| 42 | UI-ENVIRONMENT, UI-MODE-STATE | 932 | APP-EXPORT, ENG-ZHL-GAS | settings-core environment/mode READ; export-core and gas engine re-verified |

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
