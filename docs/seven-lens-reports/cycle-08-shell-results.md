# Seven-Lens Audit — Cycle 08 (UI-PLANNER-SHELL + UI-RESULTS-PANEL)

**Branch:** `cursor/seven-lens-cycle-08-shell-results`
**Baseline:** `c63dcaf2e9a29f1ff1e179e6c6195ca6fc15452b`
**Schema:** v5
**Auditor:** Cursor GPT-5.5 Medium

## Review sessions

| Session | Unit | Boundary | Lines | Part ID |
|---------|------|----------|------:|---------|
| C08-A | `UI-PLANNER-SHELL` | `planner-shell.js` | 1–201 | `UI-PLANNER-SHELL-P01` |
| C08-A | `UI-RESULTS-PANEL` | `results-panel.js` | 1–301 | `UI-RESULTS-PANEL-P01` |

**Combined canonical lines:** 502 (201 + 301). Single session **C08-A** — under 600-line limit.

**Dependency context traced (not reviewed coverage):** `ui/markup-header.html`, `ui/markup-rec-planner.html`, `ui/markup-tec-planner.html`, `index.html` bootstrap/delegates, `settings-core.js` (`setPlannerAlgo`, `_showPlannerView`, `_clearPlannerResults`), `planner-inputs-core.js`, `results-render-core.js`, `contingency-core.js`, `plot-core.js`, `export-core.js` (`notifyScheduleError`), `lsp-dplanner-results.css` mobile rules, generated `www/` parity.

## Baseline gates

| Command | Exit | Notes |
|---------|-----:|-------|
| `python tools/seven_lens_protocol.py plan --cycle 8 --output docs/seven-lens-reports/cycle-08-record.json` | 0 | HEAD = `origin/dev` = `c63dcaf` |
| `python -m tools.audit check --profile static` | 0 | 11 checks, 4 suites PASS |
| `python -m tools.audit run --profile release` | 0 | 21 suites PASS |
| `python tools/seven_lens_protocol.py check-all --require-artifacts` | 0 | Reviewed-cycle gate PASS |
| `git status --short` (pre-audit) | clean | After plan: `?? cycle-08-record.json` only |

**Integration base:** `c63dcaf2e9a29f1ff1e179e6c6195ca6fc15452b`

## Architecture trace

| Contract | Writers | Consumers |
|----------|---------|-----------|
| Main nav | `setMainNav`, `setNavMode` (`planner-shell.js`) | `index.html` `#mainNavBar` onclick; `settings-core.js` `setPlannerAlgo` |
| VPM variant | `setVpmMode`, `toggleVpmMode`, IIFE `vpmVariant` | `#vpmModeToggle`, `localStorage.vpmVariant`, `setPlannerAlgo` |
| V4 DOM bootstrap | `initV3Layout` (one-shot `window._v3LayoutDone`) | GF/conservatism mounts, result tab reparenting, tools/CNS panels, modals to `body` |
| Mobile plan/results | `setMobilePlanView`, `_initMobilePlanView` | `#planPanel` / `#resultsPanel` `.mobile-active` (CSS `@media max-width 640px`) |
| Result metrics/chips | `_renderResultSummaryStrip`, `renderMetricCards`, `renderChipRow` | `#resultMetricStrip`, `#resultChipRow`, `#resultsPanel.has-results` |
| Result tabs | `switchResultTab` | `#recResultTabs` / `#tecResultTabs` buttons; `#resultTab-*` panes; lazy `calcSurfInt`, `renderNDLTable`, `buildDiveBlocks`, graph/tissue hooks |
| Schedule decoration | `decorateDecoTableForV3`, `decorateContingencyTableForV3` | `#decoTableBody`, `#contingencyTableBody` row classes and phase icons |
| Gas warning banner | `_setGasWarningBanner`, `_updateGasWarningBannerFromCard` | `#gasWarningBanner` role=alert; called from `results-render-core.js` after gas render |
| Post-plan mobile UX | `_onPlanResultsReady` | `#diveGraphCard`, `#decoResult` display; `setMobilePlanView('results')` |

**Globals exported (shell units):** `toggleVpmMode`, `setVpmMode`, `setMainNav`, `setNavMode`, `initV3Layout`, `switchResultTab`, `setMobilePlanView`, `buildScheduleLegendHtml`, `decorateDecoTableForV3`, `decorateContingencyTableForV3`, `window.LSP_V4_SPLIT_PROFILE_SCHEDULE`.

**Mutable module state:** `vpmVariant` (`planner-shell.js`); `window._v3LayoutDone`, `window.LSP_V4_SPLIT_PROFILE_SCHEDULE`.

## Runtime matrices exercised

Probes used visible `#recGenerateBtn` / `#tecGenerateBtn` / nav clicks with `window._zhlHeadless = false`. Browser traces: `docs/seven-lens-traces/cycle-08-shell-results.json` (2 traces × 2 repeats — **FAIL** on pre-fix commit, expected).

| # | Path | Result |
|---|------|--------|
| 1 | Fresh boot (1280×800) | App loads; `initV3Layout` runs once; Bühlmann default |
| 2 | Repeated `initV3Layout` | `_v3LayoutDone` guard; GF mount child count unchanged |
| 3 | REC → TEC → REC (`setMainNav`) | `_showPlannerView` toggles `#recPlannerView` / `#tecPlannerView`; tab bars swap |
| 4 | TEC → Tools → TEC | Tools mode shows `#toolsPageWrap`; return via `#bnavPlanner` |
| 5 | Planner → Results (mobile intent) | **`setMobilePlanView` no-op** — see SL-C08-H-01 |
| 6 | Every result sub-tab | TEC: profile/contingency/graphs/tissue via `switchResultTab`; REC tabs wired in markup |
| 7 | Generate REC → navigate Tools → return | **Results cleared** on return — SL-C08-H-02 |
| 8 | Generate TEC → navigate Tools → return | **Results cleared** — SL-C08-H-02 |
| 9 | Switch algorithm after results | `setPlannerAlgo` clears via `_clearPlannerResults` (intentional on algo change) |
| 10 | Invalid calc after valid TEC | **`has-results` + 15 rows persist** — SL-C08-M-01 |
| 11 | Calc error toast path | `notifyScheduleError` toast only; no strip clear |
| 12 | Contingency tab | `#resultTab-contingency.active` after click |
| 13 | Metric/imperial with results | `units` read in `_renderResultSummaryStrip` for ft/m labels |
| 14 | Light/dark theme with results | Metric/chip classes unchanged; theme via body class |
| 15 | Desktop 1280×800 | Dual-column planner + results visible |
| 16 | Mobile 375×667 | **Both `#tecPlannerView` and `#resultsPanel` display flex** — SL-C08-H-01 |
| 17 | Landscape mobile | Same mobile CSS breakpoint 640px |
| 18 | Keyboard nav | Bottom nav buttons focusable; tab buttons in results panel |
| 19 | Browser back/forward | SPA — not applicable |
| 20 | Headless engine while UI interactive | `_zhlHeadless=false` probes; headless path skips validation block in `runDecoSchedule` |

## Findings (OPEN)

### SL-C08-H-01: Mobile plan/results toggle targets removed `#planPanel`

- **Severity:** HIGH | **Lenses:** L1, L2, L4, L6 | **Part:** C08-A | **Location:** `results-panel.js:125-131`
- **Root cause:** V4 migration replaced the legacy `#planPanel` wrapper with `#recPlannerView` / `#tecPlannerView`, but `setMobilePlanView` still requires `#planPanel`. Early return when `plan` is null leaves both planner and results panels with `mobile-active`. Mobile CSS still keys off `#planPanel` (`lsp-dplanner-results.css:711-714`).
- **Failure path:** Mobile 375×667 boot → `#tecPlannerView` and `#resultsPanel` both `mobile-active` → `setMobilePlanView('plan')` no-op → both panels `display:flex`.
- **Impact:** Mobile users see planner inputs and empty results stack together; post-generate `_onPlanResultsReady` cannot switch to results view.
- **Evidence:** Playwright mobile-init: `planPanel:false`, `tecDisplay:flex`, `resultsDisplay:flex`, `setMobileReturnsEarly`; trace `SL-C08-MOBILE-PLAN-PANEL-TRACE` FAIL.
- **Regression ID:** `SL-C08-MOBILE-PLAN-PANEL`

### SL-C08-H-02: Planner re-entry clears valid results

- **Severity:** HIGH | **Lenses:** L2, L3, L6 | **Part:** C08-A | **Location:** `planner-shell.js:84-88`
- **Root cause:** `setNavMode('planner')` unconditionally calls `setPlannerAlgo(plannerAlgo)`, which invokes `_clearPlannerResults()` in `settings-core.js:770` even when the algorithm is unchanged.
- **Failure path:** TEC generate (45 m / 25 min) → `#resultsPanel.has-results` + 15 schedule rows → `#navBtnTools` → `#bnavPlanner` → `has-results` false, `#decoTableBody` 0 rows, `#decoResult` hidden.
- **Impact:** Valid decompression schedules and safety metrics disappear when visiting Tools or Settings and returning without changing inputs; users may act on stale paper notes while UI shows empty state, or lose export context.
- **Evidence:** Playwright desktop-generate probe; trace `SL-C08-NAV-CLEARS-RESULTS-TRACE` FAIL (assertions expect cleared state — documents defect).
- **Regression ID:** `SL-C08-NAV-CLEARS-RESULTS`

### SL-C08-M-01: Invalid TEC generate leaves stale authoritative results

- **Severity:** MEDIUM | **Lenses:** L2, L6 | **Part:** C08-A | **Location:** `results-panel.js:29-35` (contract); `index.html:5823-5827` (caller)
- **Root cause:** `runDecoSchedule` validation failures call `notifyScheduleError` and return without `_clearPlannerResults` / `_clearResultSummaryStrip`. Success path adds `#resultsPanel.has-results` via `_renderResultSummaryStrip`.
- **Failure path:** Valid 45 m plan → `has-results` + 15 rows → depth 999 → generate → toast error → `has-results` still true, 15 rows unchanged.
- **Impact:** Invalid input cannot invalidate prior schedule; mandatory stops/gas warnings from old plan remain visible as if current.
- **Evidence:** Playwright invalid-after-valid probe; Cycle 07 note same pattern for REC invalid path.
- **Regression ID:** `SL-C08-STALE-INVALID-RESULTS`

### SL-C08-L-01: Dead `prefix` assignment in `switchResultTab`

- **Severity:** LOW | **Lenses:** L4 | **Part:** C08-A | **Location:** `results-panel.js:258`
- **Root cause:** `const prefix = isRec ? '' : ''` assigns empty string in both branches — likely leftover from removed V4 split-profile variant (`window.LSP_V4_SPLIT_PROFILE_SCHEDULE` unused).
- **Failure path:** Any tab switch — no runtime effect today.
- **Impact:** Maintenance hazard; obscures intended REC/TEC pane ID prefix contract.
- **Regression ID:** `SL-C08-SWITCH-TAB-PREFIX-DEAD`

### SL-C08-L-02: Duplicate mobile init from layout bootstrap

- **Severity:** LOW | **Lenses:** L2 | **Part:** C08-A | **Location:** `planner-shell.js:185`; `index.html:9350-9351`
- **Root cause:** `initV3Layout` calls `_initMobilePlanView()` and DOMContentLoaded also calls `_initMobilePlanView()` plus registers `resize` listener.
- **Failure path:** Boot — double call (idempotent when `setMobilePlanView` works; currently both no-op on mobile).
- **Impact:** Redundant work; confusing ownership between shell and bootstrap.
- **Regression ID:** `SL-C08-DUP-MOBILE-INIT`

## Lens summary

Full L1–L7 notes are in `cycle-08-record.json` for both parts.

**UI-PLANNER-SHELL:** Navigation orchestration, V4 DOM reparenting, VPM mode persistence. Primary defects: planner re-entry clears results (H-02); init calls external helpers (`settings-core.js`) for GF/conservatism/circuit sync.

**UI-RESULTS-PANEL:** Metrics, chips, tabs, schedule decoration, gas banner. Primary defects: broken mobile toggle (H-01); stale results on validation failure (M-01); dead prefix (L-01).

**L7:** No leaf suite targets `setMobilePlanView`, `setNavMode` result preservation, or invalid-generate strip clearing. `SUITE-BROWSER` does not assert shell navigation result lifecycle.

## Audit checkpoint

**audit_commit:** `32fda7bbd1896864465f830012a246b58d94109b`

Post-audit static: `python -m tools.audit check --profile static` → FAIL (`SUITE-COVERAGE` release-blocking OPEN SL-C08-H-01/H-02); expected after registry OPEN findings.

Protocol: `python tools/seven_lens_protocol.py check --phase audit --record docs/seven-lens-reports/cycle-08-record.json` → PASS (pre-attestation).

## Attestation

**attestation_commit:** `ceb3514378ed92d61a5b75c8e4448d70f006c0d3` (records `audit_commit` `32fda7b`)

## Worktree confirmation

No application source (`*.js`, `*.html`, `*.css`) or test files were modified during this audit pass. Only audit reports, records, traces, and registry metadata.

---

**Next step:** A fresh **FIXER** chat is required — two HIGH and one MEDIUM OPEN findings remain.
