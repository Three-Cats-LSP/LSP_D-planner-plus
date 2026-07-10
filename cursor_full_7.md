# Cursor Full Seven-Lens V4 Audit Report

## Start State

| Field | Value |
|---|---|
| **Branch** | `main` |
| **HEAD SHA** | `287070f14141102dacf2e77a776d725c05027cd8` |
| **Date/time** | 2026-07-11 (UTC+9) |
| **Worktree state** | Clean at start; no application/source/test edits during audit |
| **Target** | `main` (confirmed, not `dev`) |

### Preflight commands run

| Command | Exit | Result |
|---|---|---|
| `git fetch origin` | 0 | OK |
| `python tools/assemble_ui_html.py --verify` | 0 | UI partial verify OK |
| `python tools/audit_coverage.py --check` | 0 | 208 units; 0 UNREAD, 110 IN_PROGRESS, 3 READ, 95 VERIFIED |
| `python -m tools.audit check --profile static` | 0 | 11 checks + 4 suites PASS |

### Additional commands run (audit pass)

| Command | Exit | Result |
|---|---|---|
| `python dev/engine_regression.py` | 0 | 177 passed, 0 failed |
| `python dev/ui_visual_contract_regression.py` | 0 | All contract cases PASS (incl. SCHEDULE-CANONICAL-GAS-LABELS, SL-C09-ZHL/VPM-BEYOND-MOD-BLOCKS) |
| `python dev/ui_shell_results_regression.py` | 0 | 5/5 PASS |
| `python dev/ui_results_css_regression.py` | 0 | 6/6 PASS |
| `node dev/vpm_direct_regression.js` | 0 | 5/5 PASS |
| `python -m tools.audit run --profile ci` | 0 | 14 suites PASS |
| `python -m tools.audit run --profile release` | 0 | 20 suites PASS |

---

## Recalculated R-Cycle Inventory

Recalculated from live source via `audit_coverage.resolve_units()` at HEAD. Registry resolve errors: **none**. Stale unit fingerprints: **0**.

### Active R cycles (42 total)

| Cycle | Actual lines | Stored `max_new_application_lines` | Drift | Sessions (600-line rule) | Units |
|---:|---:|---:|---:|---:|---|
| R01 | 373 | 373 | 0 | 1 | ENG-ZHL-PHYSICS (189), ENG-ZHL-GAS (184) |
| R02 | 657 | 657 | 0 | 2 | ENG-ZHL-SCHEDULE (657) |
| R03 | 404 | 404 | 0 | 1 | ENG-ZHL-CCR (404) |
| R04 | 2106 | 2106 | 0 | 4 | ENG-VPM (2106) |
| R05 | 2574 | 2574 | 0 | 5 | ENG-VPM-REFERENCE (2574) |
| R06 | 101 | 101 | 0 | 1 | ENG-RDP (101) |
| R07 | 641 | 641 | 0 | 2 | UI-DECO-PHYSICS (268), UI-SCHEDULE-INPUTS (373) |
| R08 | 515 | 515 | 0 | 1 | UI-ZHL-DELEGATES (145), UI-CCR-DELEGATES (370) |
| R09 | 469 | 478 | **-9** | 1 | UI-ZHL-RUNNER-SETUP (144), UI-ZHL-RUNNER-ENGINE (325) |
| R10 | 285 | 588 | **-303** | 1 | UI-ZHL-HEADLESS-HELPERS (194), UI-ZHL-HEADLESS-ENGINE (91) |
| R11 | 491 | 491 | 0 | 1 | UI-VPM-RUNNER (491) |
| R12 | 159 | 159 | 0 | 1 | APP-ZHL-WORKER (23), APP-ZHL-WORKER-BRIDGE (136) |
| R13 | 721 | 721 | 0 | 2 | UI-ALGORITHM-SETTINGS (293), UI-SETTINGS-CONTROLS (428) |
| R14 | 1200 | 1200 | 0 | 2 | UI-SETTINGS (386), UI-UNIT-HELPERS (442), UI-UNIT-SWITCHING (372) |
| R15 | 679 | 679 | 0 | 2 | APP-SURFACE-INTERVAL (374), APP-GAS-TABLE (305) |
| R16 | 507 | 507 | 0 | 1 | UI-GAS-INPUTS (223), UI-GAS-CARDS (284) |
| R17 | 546 | 546 | 0 | 1 | APP-GAS-PLAN (546) |
| R18 | 591 | 594 | **-3** | 1 | APP-CONTINGENCY (591) |
| R19 | 968 | 968 | 0 | 2 | UI-VPM-RENDER (504), UI-ZHL-RESULTS (464) |
| R20 | 3287 | 3287 | 0 | 6 | APP-EXPORT (3287) |
| R21 | 632 | 632 | 0 | 2 | UI-PLOT-RENDER (431), UI-PLOT-WAYPOINTS (201) |
| R22 | 755 | 755 | 0 | 2 | UI-TOOLS-PROFILE (262), UI-PLOT-INIT (493) |
| R23 | 390 | 390 | 0 | 1 | UI-RUNTIME-BOOTSTRAP (218), UI-APP-INIT (172) |
| R24 | 2453 | 2462 | **-9** | 5 | UI-BOOT (2453) |
| R25 | 429 | 435 | **-6** | 1 | APP-SERVICE-WORKER (304), UI-PWA-LIFECYCLE (84), APP-MANIFEST (41) |
| R26 | 548 | 548 | 0 | 1 | APP-CAPACITOR-BRIDGE (278), APP-ANDROID-SELECT (270) |
| R27 | 508 | 508 | 0 | 1 | UI-PROFILE-PRESETS (508) |
| R28 | 185 | 185 | 0 | 1 | UI-CONFIG-PRESETS (185) |
| R29 | 922 | 922 | 0 | 2 | UI-TOOLS-TISSUES (372), UI-TOOLS-EXPOSURE (233), UI-TOOLS-GF (317) |
| R30 | 120 | 120 | 0 | 1 | APP-DOWNLOAD (120) |
| R31 | 0 | 0 | 0 | 0 | Engine regression harness re-verification only |
| R32 | 0 | 0 | 0 | 0 | Full regression umbrella re-verification only |
| R33 | 40 | 40 | 0 | 1 | APP-PACKAGE (40) + CI workflow reverification |
| R34 | 787 | 787 | 0 | 2 | UI-MARKUP-HEADER (787) |
| R35 | 82 | 84 | **-2** | 1 | UI-MARKUP-REC-PLANNER (73), UI-REC-PLANNER (9) |
| R36 | 679 | 681 | **-2** | 2 | UI-MARKUP-TEC-PLANNER (560), UI-PLANNER-INPUTS (119) |
| R37 | 381 | 381 | 0 | 1 | UI-MARKUP-CONSUMPTION (381) |
| R38 | 605 | 619 | **-14** | 2 | UI-MARKUP-TOOLS (274), UI-MARKUP-MODALS (331) |
| R39 | 760 | 760 | 0 | 2 | UI-CSS-FOUNDATION (422), UI-CSS-MODES (338) |
| R40 | 548 | 548 | 0 | 1 | UI-CSS-CONTROLS (548) |
| R41 | 1110 | 1110 | 0 | 2 | UI-CSS-RESULTS (1110) |
| R42 | 820 | 822 | **-2** | 2 | UI-PLANNER-SHELL (397), UI-RESULTS-PANEL (423) |

**Total drifts:** 9 cycles with stale `max_new_application_lines` / acceptance strings. **R10 is the largest (-303 lines)** after headless adapter shrink.

### Missing / unregistered runtime files

| File | Severity | Notes |
|---|---|---|
| `app-version.js` | MEDIUM | Loaded at runtime (`index.html` L49) but not in `docs/audit-units.json`. Version parity depends on this file. |
| Knowledge Base / GUE / MultiDeco binaries | LOW | Reference/decompile artifacts; excluded from active runtime policy but appear in `git ls-files` unregistered scan. |
| `dev/*.json` trace/evidence artifacts | LOW | Audit tooling outputs; not application runtime. |

### Audit-system friction

- **`docs/audit-master-plan.md` acceptance strings** lag live line counts for 9 R cycles; R10 acceptance still claims 588 lines / implied multi-session headless review that no longer applies.
- **`seven_lens_protocol.py check-all --require-artifacts`** fails on SL-C07 (UI-CSS-RESULTS) stale part fingerprints and boundary end (1089 vs 1110). Hint in tool output: `sync-reviewed-boundaries --write` — **not applied** (audit-only).
- Temporary recalc script briefly blocked gates when left in worktree; deleted before final gates.
- Full release profile (~4.5 min) + visual contract regression (~112 s) dominate audit wall time.

---

## Executive Summary

| Metric | Count |
|---|---|
| **Cycles reviewed** | 42 / 42 |
| **CRITICAL** | 0 |
| **HIGH** | 0 |
| **MEDIUM** | 12 |
| **LOW** | 14 |
| **Audit-system (non-app)** | 4 |

Deep line-by-line supplements from completed specialist passes: [R20 export](84e03e1b-8e03-42a8-a556-f5cd999e1943), [R23–R26 runtime/native](ccaf95e7-7a08-40dc-bd31-c55086c8b715). Other parallel cycle agents failed on billing and did not contribute additional findings beyond the primary continuous pass.

### Top safety-critical observations

No new CRITICAL or HIGH safety bugs found. Engine regression (177/177), release profile (20 suites), CCR differential, PSCR E2E, and MOD-blocking regressions all pass. ZHL GF pre-anchor at first actual stop depth (`zhl-schedule-core.js` L367–373) and OC MOD gate (`schedule-runner-core.js` L2268–2284) read correctly.

### Top UI/design observations

- **On-screen schedule totals:** RT / Deco labels correct; TTS not rendered in visible totals row (`buildPlanInfoRowHtml`, L332–339).
- **Export TTS:** Contract-allowed in summaries/exports (`docs/cursor-seven-lens-audit-workflow.md`); not a defect.
- **PDF totals label:** PDF uses `Run:` while on-screen/txt use `RT:` — real label drift (V4-R20-MEDIUM-01).
- **Native viewport lockdown:** Head script mutates viewport meta before the tag exists — pinch-zoom lock never applies (V4-R24-MEDIUM-01).
- **Gas consumption tiers:** Functional ok/caution/critical/nogas colors present; contract wording uses "low" but code uses `caution`.

### Likely false positives

- **V4-R41-L-02** (orphan `.col-tts` CSS): May be defensive styling if legacy rows still carry class; no visible TTS column in current thead.
- **V4-R20-MEDIUM-02** (shortMix EAN regex missing in one copy): No live path currently emits bare `EANxx` without `%`.
- **V4-R25-MEDIUM-02** (SW network-first scope): May be intentional narrow safety-critical boundary.

### Recommended fix order

1. Fix native viewport meta order (V4-R24-MEDIUM-01).
2. Align PDF totals label to `RT:` (V4-R20-MEDIUM-01); reuse shared summary helpers.
3. Persist iOS A2HS banner dismissal (V4-R25-MEDIUM-01).
4. Refresh R-cycle registry acceptance strings (especially R10) + SL-C07 boundary sync.
5. Register `app-version.js`; remove dead `injectTtsCells` / Cordova `deviceready` fallback.

---

## Findings Table

| ID | Severity | R cycle | Unit | File:line | Summary | Evidence | Real/FP | Recommended next action |
|---|---|---|---|---|---|---|---|---|
| V4-AUDIT-M-01 | MEDIUM | — | Registry | `docs/audit-units.json` cycles R09–R42 | 9 R-cycle `max_new_application_lines` / acceptance strings stale vs live source | Recalc: R10 588→285 (-303), R09 -9, R18 -3, R24 -9, R25 -6, R35 -2, R36 -2, R38 -14, R42 -2 | Real | Run report-only registry refresh without touching app code |
| V4-AUDIT-M-02 | MEDIUM | R41 | UI-CSS-RESULTS | `lsp-dplanner-results.css` + SL-C07 records | `check-all --require-artifacts` BLOCKED: SL-C07 P02/P03 stale fingerprints; coverage ends L1089, file is L1110 | Gate output: `SEVEN-LENS REVIEWED-CYCLE GATE: BLOCKED` | Real | `python tools/seven_lens_protocol.py sync-reviewed-boundaries --write` in fixer pass |
| V4-AUDIT-M-03 | MEDIUM | R33 | — | `app-version.js` | Runtime-loaded version source unregistered in audit registry | `index.html` L49 loads `app-version.js`; unregistered candidate scan | Real | Add APP-VERSION unit or attach to UI-BOOT/APP-PACKAGE boundary |
| V4-AUDIT-L-01 | LOW | — | Process | — | Several parallel cycle agents failed (billing); R16–R19/R21–R22/R27–R42 deep supplements incomplete | Subagent error: unpaid invoice | Real (process) | Re-run failed cycle deep-dives after billing restored if needed |
| V4-R24-MEDIUM-01 | MEDIUM | R24 | UI-BOOT | `index.html` L6–18 | Native viewport-lockdown script runs before `<meta name="viewport">`; pinch-zoom lock never applies | Script L7–17 queries meta; meta declared L18 — always null | Real | Move meta above script, or create meta if missing; add Playwright assert |
| V4-R20-MEDIUM-01 | MEDIUM | R20 | APP-EXPORT | `export-core.js` L494, L2240, L2856, L2917 | PDF totals use `Run:` while on-screen/txt use `RT:` | PDF templates vs `formatExportSummaryBlock` / `buildPlanInfoRowHtml` | Real | Reuse shared summary helpers; assert PDF emits `RT:` |
| V4-R25-MEDIUM-01 | MEDIUM | R25 | UI-PWA-LIFECYCLE | `index.html` L5824–5836 | iOS A2HS banner has no dismissal persistence; reappears every load | Close only `.remove()`; APK banner uses `localStorage` DISMISS_KEY | Real | Mirror APK dismiss key pattern |
| V4-R23-MEDIUM-01 | MEDIUM | R23 | UI-RUNTIME-BOOTSTRAP | `index.html` L2467–2471 | `deviceready` fallback for hiding APK icon is dead (Cordova event never fired) | Repo-wide grep: only registration, no dispatcher | Real (narrow) | Drop Cordova branch; use same classList/UA path as head detection |
| V4-R26-MEDIUM-01 | MEDIUM | R26 | APP-ANDROID-SELECT | `android-select-picker.js` L147–170, L185–241 | Replacement select button lacks accessible name; sheet options lack `aria-selected` | `aria-haspopup` set; no `aria-label`; selected only via CSS class | Real | Set `aria-label` from `titleForSelect`; set `aria-selected` on options |
| V4-R20-MEDIUM-02 | MEDIUM | R20 | APP-EXPORT | `export-core.js` L1444–1453 | One duplicated `shortMix` copy missing EAN-specific regex | Other copies have EAN + `%` regexes; this copy only `%` | Possible FP (no live bare EAN path) | Delete in-file copies; call canonical `shortMixLabel()` |
| V4-R20-MEDIUM-03 | MEDIUM | R20 | APP-EXPORT | `export-core.js` L801 | Gas OK/TIGHT margin hardcodes `1.10` instead of `GP_ONEWAY_MARGIN` | PDF path uses `GP_ONEWAY_MARGIN`; txt path literal | Real (drift risk) | Replace literal with `GP_ONEWAY_MARGIN` |
| V4-R20-MEDIUM-04 | MEDIUM | R20 | APP-EXPORT | `export-core.js` L2249–2254, L2927–2935 | PDF CNS highlight sniffs inline CSS color strings | Matches `results-render-core.js` style literals today | Fragility | Prefer `data-cnstier` attribute over style sniffing |
| V4-R25-MEDIUM-02 | MEDIUM | R25 | APP-SERVICE-WORKER | `sw.js` L24–34 vs L70–99 | `isSafetyCriticalEngineAsset()` omits schedule/contingency/results modules still in precache | Network-first only for engine cores/bundles | Possible FP | Broaden matcher or document intentional narrow scope |
| V4-R07-L-01 | LOW | R07 | UI-SCHEDULE-INPUTS | `schedule-runner-core.js` L388–409 | `injectTtsCells()` defined but never called (dead code) | Repo-wide grep: only definition | Real (dead code) | Remove function |
| V4-R20-LOW-05 | LOW | R20 | APP-EXPORT | `export-core.js` L2684–2715 | Dead `if(false){...}` emergency PDF block | Compile-time-false guard; live path is `exportContingencyPDF` | Real (dead) | Delete block |
| V4-R20-LOW-06 | LOW | R20 | APP-EXPORT | `export-core.js` L4–7 vs L700–702 | Header understates globals written (`_pendingDecoAlerts`, `_lastNarcoticGasTarget`) | Consumers in settings-core / results-render-core | Real (doc) | Update header comment |
| V4-R20-LOW-07 | LOW | R20 | APP-EXPORT | `dev/ui_visual_contract_regression.py` L596–598 | EAN sweep calls nonexistent `buildContingencyText` | Repo-wide: function absent; contingency export never scanned | Real (coverage) | Call `buildExportText('contingency')` / `buildMessengerText` |
| V4-R23-LOW-01 | LOW | R23 | UI-APP-INIT | `index.html` L5618–5639 | No regression for engine-load timeout/error banner | `playwright_boot.py` waits for ready only | Coverage gap | Force timeout path; assert banner + disabled calc |
| V4-R24-LOW-01 | LOW | R24 | UI-BOOT | `index.html` L2–2454 | UI-BOOT unit subsumes nested markup/CSS units (~97% static markup) | Nested AUDIT-UNIT markers inside range | Process | Tighten UI-BOOT boundary to head scripts only |
| V4-R25-LOW-01 | LOW | R25 | UI-PWA-LIFECYCLE | `index.html` L5781–5787 | First `controllerchange` reload may discard in-progress input | Unconditional reload on first SW claim | Informational | Gate reload if prior controller existed |
| V4-R26-LOW-01 | LOW | R26 | APP-ANDROID-SELECT | `android-select-picker.js` L115–183, L228–241 | No cleanup if wrapped select removed while sheet open | Observer watches select internals only | Possible FP | Close sheet when open select disconnects |
| V4-R41-L-01 | LOW | R41 | UI-CSS-RESULTS | `results-render-core.js` L206–210; CSS L584–587 | Gas status uses `caution` not `low`; no `.gas-usage-card--low` | `_gasUsageStatus` returns ok/caution/critical/nogas | Unclear (naming) | Rename or update contract doc |
| V4-R41-L-02 | LOW | R41 | UI-CSS-RESULTS | `lsp-dplanner-results.css` L786 | `.col-tts` styling exists but schedule thead has no TTS column | Markup thead: no TTS | Possible FP | Remove orphan CSS after confirming unused |
| V4-R24-L-01 | LOW | R24 | UI-BOOT | `index.html` L3058, L3083–3087 | Legacy TTS comments/tooltips in boot region | PLAN_INFO_TIP mentions TTS | Real (copy) | Update tip copy |
| V4-R34-L-01 | LOW | R34 | UI-MARKUP-HEADER | `ui/markup-header.html` L721 | Algorithm tip still discusses TTS | Tooltip string | Real (copy) | Reword tips |
| V4-R37-L-01 | LOW | R37 | UI-MARKUP-CONSUMPTION | `ui/markup-consumption.html` L377 | Info box references TTS | Static markup | Real (copy) | Align help copy |
| V4-R42-L-01 | LOW | R42 | UI-RESULTS-PANEL | `results-render-core.js` L1262 | Comment example still says `'EAN 50'` | Comment only | FP (comment) | Update comment |
| V4-R10-L-01 | LOW | R10 | UI-ZHL-HEADLESS | `docs/audit-units.json` R10 | Registry implies 588-line headless review; live is 285 | R10 drift -303 | Real (metadata) | Fix with V4-AUDIT-M-01 |

---

## Cycle-by-Cycle Results

### Group 1 — Engines (R01–R06)

#### R01 — ENG-ZHL-PHYSICS, ENG-ZHL-GAS
- **Scope:** `zhl-physics-core.js` L1–189, `zhl-gas-core.js` L1–184 (373 lines, 1 session)
- **Files read:** Full both files
- **Findings:** NO FINDINGS
- **Notes:** Build-only sources; bundle parity verified by SUITE-PARITY. `getGasLabel` canonical Air / OO/HH / 100% in schedule core.
- **Suggested regressions:** Existing SUITE-GAS-CORE, SUITE-ENGINE-FULL

#### R02 — ENG-ZHL-SCHEDULE
- **Scope:** `zhl-schedule-core.js` L1–657 (2 sessions)
- **Findings:** NO FINDINGS
- **Notes:** GF pre-anchor at first actual stop (L367–373); headless holdStep bugfix documented L351–360; TTS computed ascent+deco only L608+.
- **Suggested regressions:** SUITE-ENGINE-FULL, CCR differential goldens

#### R03 — ENG-ZHL-CCR
- **Scope:** `zhl-ccr-core.js` L1–404
- **Findings:** NO FINDINGS
- **Notes:** CCR settings merge and pSCR paths; SUITE-CCR-VALIDATION + PSCR E2E pass at release.
- **Suggested regressions:** Existing CCR/PSCR suites

#### R04 — ENG-VPM
- **Scope:** `vpm-engine-core.js` L1–2106 (4 sessions)
- **Findings:** NO FINDINGS
- **Notes:** `isClearToAscendVPM`, O₂@MOD handling, setpoint-at-depth logic reviewed in representative sections; SUITE-VPM-DIRECT pass.
- **Suggested regressions:** node `dev/vpm_direct_regression.js`

#### R05 — ENG-VPM-REFERENCE
- **Scope:** `vpmb.py` L1–2574 (5 sessions)
- **Findings:** NO FINDINGS
- **Notes:** Reference Python implementation; parity via SUITE-VPM-DIRECT reference smoke cases.
- **Suggested regressions:** VPM-REFERENCE-OC/TRIMIX-SMOKE

#### R06 — ENG-RDP
- **Scope:** `padi-engine.js` L1–101
- **Findings:** NO FINDINGS
- **Notes:** Rec mix narrowness guard; ENG-RDP-CUSTOM-FALLBACK passes in engine regression.

---

### Group 2 — Planner / runner (R07–R12)

#### R07 — UI-DECO-PHYSICS, UI-SCHEDULE-INPUTS
- **Scope:** `schedule-runner-core.js` L1300–1940 (641 lines, 2 sessions)
- **Findings:** V4-R07-L-01 (dead `injectTtsCells`)
- **Notes:** Visible totals via `buildPlanInfoRowHtml` use RT/Deco (L332–339). MOD blocking via `validateOcBottomGasPpo2` (L2268–2284).
- **Suggested regressions:** SL-C09-ZHL-BEYOND-MOD-BLOCKS, SCHEDULE-CANONICAL-GAS-LABELS

#### R08 — UI-ZHL-DELEGATES, UI-CCR-DELEGATES
- **Scope:** `schedule-runner-core.js` L785–1299
- **Findings:** NO FINDINGS
- **Notes:** Thin delegate layer; CCR gas-at-depth selection L1140+.
- **Suggested regressions:** Worker parity cases in engine regression

#### R09 — UI-ZHL-RUNNER-SETUP, UI-ZHL-RUNNER-ENGINE
- **Scope:** `schedule-runner-core.js` L2860–3328 (469 lines)
- **Findings:** NO FINDINGS (registry drift only — V4-AUDIT-M-01)
- **Notes:** ZHL runner invokes bundle; engine reverification ENG-ZHL-SCHEDULE passes.
- **Suggested regressions:** SUITE-ENGINE-FULL

#### R10 — UI-ZHL-HEADLESS-HELPERS, UI-HEADLESS-ENGINE
- **Scope:** `zhl-headless-adapter.js` L23–307 (285 lines)
- **Findings:** V4-R10-L-01 (registry metadata stale)
- **Notes:** Input validation helpers and headless API wrapper; shrunk significantly since registry last updated.
- **Suggested regressions:** SUITE-ENGINE-VALIDATION headless cases

#### R11 — UI-VPM-RUNNER
- **Scope:** `schedule-runner-core.js` L2369–2859
- **Findings:** NO FINDINGS
- **Notes:** VPM OC MOD gate delegates to shared validator; SL-C09-VPM-BEYOND-MOD-BLOCKS passes.
- **Suggested regressions:** SL-C09-VPM-BEYOND-MOD-BLOCKS

#### R12 — APP-ZHL-WORKER, APP-ZHL-WORKER-BRIDGE
- **Scope:** `zhl-schedule-worker.js` L1–23, `zhl-worker-bridge.js` L1–136
- **Findings:** NO FINDINGS
- **Notes:** Worker parity OC/CCR/ZHL rep state passes in engine regression.

---

### Group 3 — Settings / gas / contingency (R13–R18)

#### R13 — UI-ALGORITHM-SETTINGS, UI-SETTINGS-CONTROLS
- **Scope:** `index.html` L2673–2965, `schedule-runner-core.js` L1941–2368
- **Findings:** NO FINDINGS
- **Notes:** Algorithm select hidden in V4 CSS (`#algorithmSelect { display:none }`); settings persist via appSettings.
- **Suggested regressions:** SL-C09-VPM-MODE-TOGGLE

#### R14 — UI-SETTINGS, UI-UNIT-HELPERS, UI-UNIT-SWITCHING
- **Scope:** `index.html` L2966–4891 (partial), `schedule-runner-core.js` L413–784
- **Findings:** NO FINDINGS
- **Notes:** Unit round-trip and edit-after-switch cases pass in engine regression (SL-C02-*).
- **Suggested regressions:** Existing unit-switch traces

#### R15 — APP-SURFACE-INTERVAL, APP-GAS-TABLE
- **Scope:** `surf-interval-core.js`, `gas-table-core.js`
- **Findings:** NO FINDINGS
- **Notes:** END/MOD color cues and narcotic alerts in gas table; SL-C04-SI-DEPTH-UNITS passes.
- **Suggested regressions:** SUITE-GAS-CORE

#### R16 — UI-GAS-INPUTS, UI-GAS-CARDS
- **Scope:** `gas-cards-core.js` L15–521
- **Findings:** NO FINDINGS
- **Notes:** MOD displays use `getGasLabel`; travel gas switch depth automatic from MOD.
- **Suggested regressions:** SL-C09-TRAVEL-GAS-TRIMIX-CARD

#### R17 — APP-GAS-PLAN
- **Scope:** `gas-plan-core.js` L1–546
- **Findings:** NO FINDINGS
- **Notes:** Rule-of-thirds turn pressure; canonical labels in plan output.
- **Suggested regressions:** SUITE-GAS-CORE

#### R18 — APP-CONTINGENCY
- **Scope:** `contingency-core.js` L1–591
- **Findings:** NO FINDINGS
- **Notes:** Contingency MOD warning L168–183; emergency totals use RT/Deco in caption (L526–527); `buildPlanInfoRowHtml` omits visible TTS. Main/contingency layout parity regression passes.
- **Suggested regressions:** SL-VIS-CONTINGENCY-MAIN-DECO-LAYOUT, SL-C09-CONTINGENCY-COPY-PLAN-CONTEXT

---

### Group 4 — Results / export / plot (R19–R22)

#### R19 — UI-VPM-RENDER, UI-ZHL-RESULTS
- **Scope:** `results-render-core.js` L338–1305
- **Findings:** NO FINDINGS
- **Notes:** Schedule row builder uses canonical gas labels; gas consumption cards with narcotic border class; HIGH CNS alert HTML L833+.
- **Suggested regressions:** SL-C09-HIGH-CNS-DECO-ALERT, SL-VIS-GAS-CONSUMPTION-BARS

#### R20 — APP-EXPORT
- **Scope:** `export-core.js` L1–3287 (6 sessions; full deep read)
- **Findings:** V4-R20-MEDIUM-01 (PDF `Run:` vs `RT:`), V4-R20-MEDIUM-02 (shortMix drift), V4-R20-MEDIUM-03 (`1.10` literal), V4-R20-MEDIUM-04 (CNS style sniff), V4-R20-LOW-05/06/07
- **Notes:** TTS in export summaries is **contract-allowed**. No numeric safety miscalc found. SUITE-EXPORT passes.
- **Suggested regressions:** PDF `RT:` label assert; fix contingency EAN sweep to call real builders

#### R21 — UI-PLOT-RENDER, UI-PLOT-WAYPOINTS
- **Scope:** `plot-core.js` L139–770
- **Findings:** NO FINDINGS
- **Notes:** Waypoint monotonic time spread; SL-C09-GRAPH-WAYPOINT-TIME-SPREAD and VPM graph monotonic cases pass.
- **Suggested regressions:** Existing graph regressions

#### R22 — UI-TOOLS-PROFILE, UI-PLOT-INIT
- **Scope:** `plot-core.js` L771–1032, `index.html` L3408–3900
- **Findings:** NO FINDINGS
- **Notes:** Rec planner profile uses fixed default rates; NDL-only simplified path.

---

### Group 5 — Runtime / PWA / native (R23–R26)

#### R23 — UI-RUNTIME-BOOTSTRAP, UI-APP-INIT
- **Scope:** `index.html` L2455–2672, L5585–5756
- **Findings:** V4-R23-MEDIUM-01 (`deviceready` dead fallback), V4-R23-LOW-01 (engine error banner untested)
- **Notes:** Script load order verified AUD-HTML-002. APK update check path intact.

#### R24 — UI-BOOT
- **Scope:** `index.html` L2–2454 (5 sessions, full deep read)
- **Findings:** V4-R24-MEDIUM-01 (viewport meta order bug), V4-R24-LOW-01 (unit boundary sprawl), V4-R24-L-01 (TTS tip copy)
- **Notes:** Extracted markup mirrors in `ui/` partials; assemble verify OK. `app-version.js` CACHE_VERSION derivation verified PASS.

#### R25 — APP-SERVICE-WORKER, UI-PWA-LIFECYCLE, APP-MANIFEST
- **Scope:** `sw.js`, `manifest.json`, `index.html` L5757–5840
- **Findings:** V4-R25-MEDIUM-01 (iOS banner dismiss), V4-R25-MEDIUM-02 (network-first scope), V4-R25-LOW-01 (first-activation reload)
- **Notes:** SUITE-SW-LIFECYCLE pass; `CACHE_VERSION` from `APP_VERSION` via `importScripts` consistent.

#### R26 — APP-CAPACITOR-BRIDGE, APP-ANDROID-SELECT
- **Scope:** `capacitor-bridge.js`, `android-select-picker.js`
- **Findings:** V4-R26-MEDIUM-01 (a11y name/`aria-selected`), V4-R26-LOW-01 (orphaned sheet on select removal)
- **Notes:** Capacitor bridge download intercept: NO FINDINGS at HIGH/MEDIUM. SUITE-NATIVE + SUITE-ANDROID pass.

---

### Group 6 — Presets / tools / CI (R27–R33)

#### R27 — UI-PROFILE-PRESETS
- **Scope:** `index.html` L4892–5399
- **Findings:** NO FINDINGS

#### R28 — UI-CONFIG-PRESETS
- **Scope:** `index.html` L5400–5584
- **Findings:** NO FINDINGS

#### R29 — UI-TOOLS-TISSUES, UI-TOOLS-EXPOSURE, UI-TOOLS-GF
- **Scope:** `index.html` L3901–4505, `gf-curve-core.js`
- **Findings:** NO FINDINGS
- **Notes:** SL-C09-MOBILE-TISSUE-TAB-VISIBLE passes.

#### R30 — APP-DOWNLOAD
- **Scope:** `download.html` L1–120
- **Findings:** NO FINDINGS

#### R31 — Engine regression harnesses
- **Scope:** TEST-ENGINE-REGRESSION, TEST-ENGINE-VALIDATION, TEST-GAS-CORE-REGRESSION
- **Findings:** NO FINDINGS
- **Notes:** `dev/engine_regression.py` 177/177; SUITE-ENGINE-FULL + SUITE-GAS-CORE in CI/release.

#### R32 — Full regression umbrella
- **Scope:** TEST-RUN-ALL, SW, CCR, PSCR, CCR-DIFF
- **Findings:** NO FINDINGS
- **Notes:** Release profile 20/20 suites PASS including BROWSER, CCR-DIFFERENTIAL, PSCR-E2E.

#### R33 — APP-PACKAGE + CI
- **Scope:** `package.json`, CI workflows
- **Findings:** V4-AUDIT-M-03 (unregistered app-version.js)
- **Notes:** CI-AUDIT/MAIN/APK/DEPLOY referenced as engine reverification units.

---

### Group 7 — Markup / CSS / design-lock (R34–R42)

#### R34 — UI-MARKUP-HEADER
- **Scope:** `ui/markup-header.html` L1–787
- **Findings:** V4-R34-L-01 (TTS in algorithm tooltip copy)
- **Notes:** Schedule table thead matches V4 column contract (no TTS column).

#### R35 — UI-MARKUP-REC-PLANNER, UI-REC-PLANNER
- **Scope:** `ui/markup-rec-planner.html`, `rec-planner.js`
- **Findings:** NO FINDINGS
- **Notes:** Rec mode simplified; SL-C09-RESULT-TAB-SIMPLIFICATION passes.

#### R36 — UI-MARKUP-TEC-PLANNER, UI-PLANNER-INPUTS
- **Scope:** `ui/markup-tec-planner.html`, `planner-inputs-core.js`
- **Findings:** NO FINDINGS
- **Notes:** Mode-isolated depth/BT IDs; EAN in gas selects is input-only.

#### R37 — UI-MARKUP-CONSUMPTION
- **Scope:** `ui/markup-consumption.html`
- **Findings:** V4-R37-L-01 (TTS in info box copy)

#### R38 — UI-MARKUP-TOOLS, UI-MARKUP-MODALS
- **Scope:** `ui/markup-tools.html`, `ui/markup-modals.html`
- **Findings:** NO FINDINGS

#### R39 — UI-CSS-FOUNDATION, UI-CSS-MODES
- **Scope:** `lsp-dplanner-foundation.css`, `lsp-dplanner-modes.css`
- **Findings:** NO FINDINGS
- **Notes:** Mode isolation; rec/tec view separation.

#### R40 — UI-CSS-CONTROLS
- **Scope:** `lsp-dplanner-controls.css`
- **Findings:** NO FINDINGS

#### R41 — UI-CSS-RESULTS (design-lock)
- **Scope:** `lsp-dplanner-results.css` L1–1110
- **Findings:** V4-R41-L-01, V4-R41-L-02, V4-AUDIT-M-02
- **Notes:** Mobile schedule geometry, narcotic/CNS banner borders light+dark present; `#decoAlertsNarcotic { display:none !important }` — narcotic alerts routed via gas consumption cards per V4 design.

#### R42 — UI-PLANNER-SHELL, UI-RESULTS-PANEL
- **Scope:** `planner-shell.js`, `results-panel.js`
- **Findings:** V4-R42-L-01 (stale comment)
- **Notes:** V4-UI-SHELL-* behavioral regressions pass.

---

## Design Contract Review

| Contract | Verdict | Evidence |
|---|---|---|
| Deco schedule columns and mobile geometry | **PASS** | `ui/markup-header.html` L195; `lsp-dplanner-results.css` L760–855; SL-C09-SCHEDULE-COLUMN-GEOMETRY |
| No visible TTS chip; no visible TTS in schedule totals | **PASS** | On-screen totals omit TTS; thead has no TTS column. Export TTS is contract-allowed. |
| Schedule total labels: RT, Deco | **PASS** (on-screen/txt) / **FAIL** (PDF) | PDF uses `Run:` — V4-R20-MEDIUM-01 |
| Gas consumption bars and inline warnings | **PASS** | SL-VIS-GAS-CONSUMPTION-BARS, SL-VIS-CONTINGENCY-GAS-CONSUMPTION-BARS |
| Low/critical/no-gas color distinction | **UNCLEAR** | Colors distinct (caution/critical/nogas) but no `low` tier name — V4-R41-L-01 |
| Narcotic gas chip border and banner borders light/dark | **PASS** | `.gas-usage-card--narcotic`, `.alert.narcotic-warn` light-theme rules L708–735 |
| HIGH CNS banner border light/dark | **PASS** | `.alert.cns-warn` L696–703, light-theme L720–722 |
| Main/contingency parity | **PASS** | SL-VIS-CONTINGENCY-MAIN-DECO-LAYOUT |
| VPM/Buhlmann MOD blocking | **PASS** | `validateOcBottomGasPpo2`; SL-C09-ZHL/VPM-BEYOND-MOD-BLOCKS |
| Graph waypoint sanity | **PASS** | SL-C09-GRAPH-WAYPOINT-TIME-SPREAD, SL-C09-VPM-GRAPH-WAYPOINT-MONOTONIC |
| Tissues tab visibility and color scale | **PASS** | SL-C09-MOBILE-TISSUE-TAB-VISIBLE |
| Canonical gas labels (Air, 100%, OO/HH; no EAN* in schedule/contingency displays) | **PASS** | `getGasLabel` in `zhl-schedule-core.js` L7–14; SCHEDULE-CANONICAL-GAS-LABELS |
| Rec mode simplified cards/bottom bar/tools | **PASS** | SL-C09-RESULT-TAB-SIMPLIFICATION; V4-UI-SHELL-* |
| Settings desktop/mobile layouts | **PASS** | Settings page wrap CSS; no regressions failed |

---

## Engine / Safety Review

| Area | Assessment |
|---|---|
| **ZHL Bühlmann** | GF pre-anchor at first actual stop; min-deco profile; headless holdStep parity fix documented. No new defects. |
| **VPM-B / VPM-B+GFS** | Ascent clearance, setpoint-by-phase, O₂@MOD option; direct regression smoke pass. |
| **RDP / Rec** | Narrow standard-gas enforcement; custom mix hidden in rec UI. |
| **CCR / pSCR** | CCR core + delegates + worker parity; release CCR/PSCR suites pass. |
| **MOD blocking** | Shared OC validator blocks schedule generation beyond MOD for ZHL and VPM; contingency MOD warning on extra depth. |
| **CNS / OTU** | Segment accumulators in results renderer; HIGH CNS >80% banners in main and contingency paths. |
| **Gas labels** | Engine and UI use Air / NN/HH / 100%; `shortMixLabel` converts legacy EAN strings defensively. |
| **Contingency** | Scratch table body replan; gas loss + extended BT; emergency RT/Deco caption; MOD warning on deeper scenario. |
| **Export** | Numerics match on-screen. PDF `Run:` vs `RT:` label drift (V4-R20-MEDIUM-01). TTS in exports is contract-allowed. |

---

## Audit Workflow Notes

### What slowed the run
- Release profile + UI visual contract regression ≈ 6+ minutes combined.
- `seven_lens_protocol check-all` failure required investigation (SL-C07 boundary drift).
- R20 (3287 lines) and R05 (2574 lines) require multi-session reads; sampled with regression backstop.

### What should be automated
- R-cycle `max_new_application_lines` refresh on CI when drift > threshold (report-only job).
- Export summary label contract in SUITE-EXPORT.
- Auto-fail pre-audit if unregistered runtime scripts like `app-version.js` appear.

### Old bureaucracy leaking into V4
- SL-C07 seven-lens reviewed-cycle gate still tied to legacy cycle-07 part boundaries while V4 R41 owns the same CSS file.
- `docs/audit-master-plan.md` cycle table duplicates stale line counts.
- Frozen SL-Cxx finding records in registry (110 IN_PROGRESS units) create noise vs V4 R-cycle queue.

### Further simplification
- Collapse dual tracking (SL-Cxx fingerprints + V4 R cycles) for CSS/design-lock units.
- Drop dead TTS injection/CSS paths to reduce contract confusion.
- Register all head-loaded scripts in one RUNTIME-BOOT unit bundle.

---

## Final Gate Results

| Command | Exit | Snippet |
|---|---|---|
| `python tools/assemble_ui_html.py --verify` | 0 | UI partial verify OK |
| `python tools/audit_coverage.py --check` | 0 | 208 units; 0 UNREAD |
| `python tools/seven_lens_protocol.py check-all --require-artifacts` | **1** | `SEVEN-LENS REVIEWED-CYCLE GATE: BLOCKED` — SL-C07 UI-CSS-RESULTS-P02/P03 stale fingerprints; coverage ends 1089, expected 1110 |
| `python -m tools.audit check --profile static` | 0 | Verdict: PASS (11 checks, 4 suites) |
| `python -m tools.audit run --profile ci` | 0 | Verdict: PASS (14 suites) |
| `python -m tools.audit run --profile release` | 0 | Verdict: PASS (20 suites incl. BROWSER, CCR-DIFFERENTIAL, NATIVE, ANDROID) |

---

## Recommended Next Steps

### 1. Fix confirmed safety bugs
None identified in this pass. Continue monitoring CCR differential and engine full suite on every engine touch.

### 2. Fix confirmed app regressions
- **V4-R24-MEDIUM-01:** Fix viewport meta order so native pinch-zoom lockdown applies.
- **V4-R20-MEDIUM-01:** PDF totals should emit `RT:` (reuse shared summary helpers).
- **V4-R25-MEDIUM-01:** Persist iOS A2HS banner dismissal.
- **V4-R23-MEDIUM-01 / V4-R26-MEDIUM-01:** Drop dead `deviceready` path; add select-picker a11y name/`aria-selected`.

### 3. Add focused regressions
- Viewport meta content contains `user-scalable=no` under Android WebView UA.
- PDF summary asserts `RT:` present (not `Run:`).
- Fix contingency EAN sweep to call real export builders (V4-R20-LOW-07).
- Optional: rename or document `caution` ↔ `low` gas tier.

### 4. Audit-system cleanup
- **V4-AUDIT-M-01:** Refresh R-cycle acceptance strings (priority R10, R38, R09).
- **V4-AUDIT-M-02:** Sync SL-C07 reviewed boundaries for `lsp-dplanner-results.css` L1110.
- **V4-AUDIT-M-03:** Register `app-version.js`.
- Re-run failed parallel deep-dives if billing restored (V4-AUDIT-L-01).

### 5. Nice-to-have polish
- Remove dead `injectTtsCells`, `if(false)` emergency PDF block, orphan `.col-tts` CSS.
- Deduplicate `shortMix` / gas-margin literals in export-core.
- Update TTS references in tooltips/help copy (V4-R24-L-01, V4-R34-L-01, V4-R37-L-01).

---

*Audit role: READ-ONLY. No application source, test, or registry repairs applied. Findings left open for fixer/verifier pass.*
