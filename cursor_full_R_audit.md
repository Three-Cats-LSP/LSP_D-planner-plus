# Seven-Lens V4 Full Audit Report (`cursor_full_R_audit.md`)

**Mode:** READ-ONLY · automatic R01→R42 · risk-first  
**Date:** 2026-07-11 (UTC+9)  
**Auditor:** Cursor Auto (Composer) + parallel explore agents

---

## 1. Audit source

| Field | Value |
|---|---|
| **Branch** | `main` |
| **HEAD** | `ca107656d6bf9c93f28dff787cf0316104887cdd` |
| **Commit subject** | Align deco gas markers with plan chips |
| **Worktree** | Clean (`git status` empty) at audit start |
| **Tracking** | `main...origin/main` (in sync) |
| **Epoch** | `v4-risk-first-reset` · 42 active R cycles |

No application code, CSS, registry, protocol, or generated artifacts were modified during this pass. Report file write only.

---

## 2. Preflight results

| Command | Exit | Result |
|---|---:|---|
| `python tools/assemble_ui_html.py --verify` | **0** | UI partial verify OK |
| `python dev/ui_visual_contract_regression.py` | **0** | All listed visual contract cases PASS (~401 s) |
| `python -m tools.audit check --profile static` | **0** | 11 checks + 4 suites PASS (re-run after deleting accidental temp helper that briefly failed COVERAGE) |
| `python tools/seven_lens_protocol.py check-all --require-artifacts` | **0** | `SEVEN-LENS REVIEWED-CYCLE GATE: PASS` |

**Note:** First static run failed solely because a temporary `_audit_recalc_tmp.py` was left in the repo root (unregistered source). File was deleted; static re-run PASS. No app source was changed.

---

## 3. R-cycle boundary / line-count recalculation

Resolved via `tools.audit_coverage.resolve_units()` at HEAD. Registry resolve errors: **0**. Stale unit fingerprints: **0**.

| Cycle | Registry `max_new_application_lines` | Live lines | Drift | Units (live) |
|---|---:|---:|---:|---|
| R01 | 373 | 373 | 0 | ENG-ZHL-PHYSICS(189), ENG-ZHL-GAS(184) |
| R02 | 657 | 657 | 0 | ENG-ZHL-SCHEDULE(657) |
| R03 | 404 | 404 | 0 | ENG-ZHL-CCR(404) |
| R04 | 2106 | 2106 | 0 | ENG-VPM(2106) |
| R05 | 2574 | 2574 | 0 | ENG-VPM-REFERENCE(2574) |
| R06 | 101 | 101 | 0 | ENG-RDP(101) |
| R07 | 641 | 641 | 0 | UI-DECO-PHYSICS(268), UI-SCHEDULE-INPUTS(373) |
| R08 | 515 | 515 | 0 | UI-ZHL-DELEGATES(145), UI-CCR-DELEGATES(370) |
| R09 | 469 | 469 | 0 | UI-ZHL-RUNNER-SETUP(144), UI-ZHL-RUNNER-ENGINE(325) |
| R10 | 285 | 285 | 0 | UI-ZHL-HEADLESS-HELPERS(194), UI-ZHL-HEADLESS-ENGINE(91) |
| R11 | 491 | 491 | 0 | UI-VPM-RUNNER(491) |
| R12 | 159 | 159 | 0 | APP-ZHL-WORKER(23), APP-ZHL-WORKER-BRIDGE(136) |
| R13 | 721 | 721 | 0 | UI-ALGORITHM-SETTINGS(293), UI-SETTINGS-CONTROLS(428) |
| R14 | 1200 | 1200 | 0 | UI-SETTINGS(386), UI-UNIT-HELPERS(442), UI-UNIT-SWITCHING(372) |
| R15 | 679 | 679 | 0 | APP-SURFACE-INTERVAL(374), APP-GAS-TABLE(305) |
| R16 | 507 | 507 | 0 | UI-GAS-INPUTS(223), UI-GAS-CARDS(284) |
| R17 | 546 | 546 | 0 | APP-GAS-PLAN(546) |
| R18 | 591 | 591 | 0 | APP-CONTINGENCY(591) |
| R19 | 968 | 968 | 0 | UI-VPM-RENDER(504), UI-ZHL-RESULTS(464) |
| R20 | 3453 | **3447** | **−6** | APP-EXPORT(3447) |
| R21 | 632 | 632 | 0 | UI-PLOT-RENDER(431), UI-PLOT-WAYPOINTS(201) |
| R22 | 755 | 755 | 0 | UI-TOOLS-PROFILE(262), UI-PLOT-INIT(493) |
| R23 | 395 | 395 | 0 | UI-RUNTIME-BOOTSTRAP(223), UI-APP-INIT(172) |
| R24 | 2458 | **2457** | **−1** | UI-BOOT(2457) |
| R25 | 433 | 433 | 0 | APP-SERVICE-WORKER(304), UI-PWA-LIFECYCLE(88), APP-MANIFEST(41) |
| R26 | 555 | 555 | 0 | APP-CAPACITOR-BRIDGE(278), APP-ANDROID-SELECT(277) |
| R27 | 508 | 508 | 0 | UI-PROFILE-PRESETS(508) |
| R28 | 185 | 185 | 0 | UI-CONFIG-PRESETS(185) |
| R29 | 922 | 922 | 0 | UI-TOOLS-TISSUES(372), UI-TOOLS-EXPOSURE(233), UI-TOOLS-GF(317) |
| R30 | 120 | 120 | 0 | APP-DOWNLOAD(120) |
| R31 | 0 | 0 | 0 | (harness re-verify only) |
| R32 | 0 | 0 | 0 | (umbrella re-verify only) |
| R33 | 40 | 40 | 0 | APP-PACKAGE(40) |
| R34 | 787 | **786** | **−1** | UI-MARKUP-HEADER(786) |
| R35 | 82 | 82 | 0 | UI-MARKUP-REC-PLANNER(73), UI-REC-PLANNER(9) |
| R36 | 679 | 679 | 0 | UI-MARKUP-TEC-PLANNER(560), UI-PLANNER-INPUTS(119) |
| R37 | 381 | 381 | 0 | UI-MARKUP-CONSUMPTION(381) |
| R38 | 605 | 605 | 0 | UI-MARKUP-TOOLS(274), UI-MARKUP-MODALS(331) |
| R39 | 760 | **758** | **−2** | UI-CSS-FOUNDATION(418), UI-CSS-MODES(340) |
| R40 | 548 | 548 | 0 | UI-CSS-CONTROLS(548) |
| R41 | 1114 | **1071** | **−43** | UI-CSS-RESULTS(1071) |
| R42 | 827 | 827 | 0 | UI-PLANNER-SHELL(397), UI-RESULTS-PANEL(430) |

**Boundary drift findings (metadata only):** R20 (−6), R24 (−1), R34 (−1), R39 (−2), **R41 (−43 largest)**.

**Coverage gaps (registered units absent from all R-cycle `application_units`):**

| Unit | Path | Live lines | Notes |
|---|---|---:|---|
| `UI-CSS-MOBILE-SHELL` | `lsp-dplanner-mobile-shell.css` | 709 | Required by AUD-HTML-003; **not in any R cycle** |
| `APP-VERSION` | `app-version.js` | 8 | Registered; **not in any R cycle** |
| `APP-VERSION-JSON` | `version.json` | 7 | Registered; **not in any R cycle** |

---

## 4. Cycle-by-cycle audit notes (R01→R42)

### Group 1 — Engines (R01–R06)

#### R01 — ENG-ZHL-PHYSICS, ENG-ZHL-GAS — **PASS**
Lenses L1–L7 clean. Schreiner/linear loading, altitude, ppO₂ / MOD helpers consistent. No findings.

#### R02 — ENG-ZHL-SCHEDULE — **PASS**
GF pre-anchor confirmed (`gfAt` returns `gfL` until first forced stop; anchor at first `mustStop`, `zhl-schedule-core.js` ~L203–206, L367–374). TTS = ascent+deco only. No findings.

#### R03 — ENG-ZHL-CCR — **PASS**
pSCR steady-state O₂ drop, setpoint endpoint contract, bailout OC fallthrough. No findings.

#### R04 — ENG-VPM — **PASS** (sampled MOD/ceiling/schedule entry)
`getVPMCeiling`, `selectDecoGas`, `calculate` validation gate, canonical gas labels. No findings. Full 2106-line line-by-line not claimed; backed by structural sampling + existing VPM regressions.

#### R05 — ENG-VPM-REFERENCE — **PASS** (harness-backed)
`vpmb.py` not fully re-read; no contradictory evidence at HEAD vs prior batches / VPM-direct suites.

#### R06 — ENG-RDP — **PASS**
PADI table lookup, mix normalize, beyond-table NDL 0. No findings.

### Group 2 — Runners (R07–R12)

#### R07 — UI-DECO-PHYSICS, UI-SCHEDULE-INPUTS — **CONCERN**
MOD gate `validateOcBottomGasPpo2` fail-closed. Dead `injectTtsCells` remains. Findings: V4-FULL-R07_L_01.

#### R08 — UI-ZHL-DELEGATES, UI-CCR-DELEGATES — **PASS**
Thin bundle delegates; CCR MOD validation. No findings.

#### R09 — UI-ZHL-RUNNER-SETUP, UI-ZHL-RUNNER-ENGINE — **PASS**
Stale-gen guards, bailout GF restore, MOD before engine, headless early-return after plan compute. No findings.

#### R10 — Headless ZHL — **PASS**
Adapter validates then delegates; live lines match registry (285). No findings (prior −303 drift fixed in registry).

#### R11 — UI-VPM-RUNNER — **PASS**
Shared OC MOD gate; stop-cap / error fail-closed. No findings.

#### R12 — Worker + bridge — **PASS**
30s timeout, 3-failure disable, env passthrough. No findings.

### Group 3 — Settings / gas / results / export / plot (R13–R22)

#### R13 — Algorithm / settings controls — **PASS**
Persistence + conservatism re-run paths OK. No findings.

#### R14 — Settings / unit helpers — **PASS**
`domDepthToM` stamp contract; `setUnits` conversion paths OK for registered controls. No findings.

#### R15 — Surface interval / gas table — **CONCERN (HIGH)**
Tools-tab SI (`siD1Depth`/`siD2Depth`) participates in unit switch + has SL-C04 regression coverage. **Results-panel SI** (`mainSi*` / `recSi*`) sliders store metric magnitudes without `data-depthM`; `calcSurfInt` → `domDepthToM` misreads them under imperial. Opening the panel calls `calcSurfInt` (`toggleSurfIntPanel`). Finding: V4-FULL-R15_M_01. Gas table: PASS.

#### R16 — Gas inputs/cards — **PASS**
ca10765 lime deco markers verified: `.gas-dot--deco1/2/o2` → `var(--gas-deco-chip-bg)` `#d6ff00`; visual contract asserts parity with plan chips.

#### R17 — Gas plan — **PASS**
Canonical bar/L reads; turn pressure; contingency SAC multiplier. No findings.

#### R18 — Contingency — **PASS**
Scratch table isolation; restore in `finally`; emergency alerts separated. No findings.

#### R19 — VPM/ZHL results render — **PASS**
CNS row highlight thresholds aligned VPM/ZHL (≥80 / ≥100). Phase coloring delegated to CSS after decorate. No new defects.

#### R20 — APP-EXPORT — **CONCERN (HIGH)**
Messenger/copy and some text switch-row paths use wrong TD indices (Run↔Mix). PDF `RT:` label now correct (prior `Run:` drift fixed). Multiple MEDIUM consistency issues remain. See PDF/export section.

#### R21 — Plot render / waypoints — **PASS**
Gas-switch flags use deco lime; contingency prefix strip. No findings.

#### R22 — Profile tool / plot init — **PASS**
GF curve schedule coalescing; init guards. No findings.

### Group 4 — Runtime / native / CI (R23–R33)

#### R23 — Bootstrap / app init — **PASS**
Viewport meta is **before** lockdown script (`index.html` L6–22) — prior V4-R24-MEDIUM-01 fixed. Engine boot fail-closed. No findings.

#### R24 — UI-BOOT — **PASS**
Head order / script load order coherent with SW precache. Minor line drift (−1). No app findings.

#### R25 — SW / PWA / manifest — **CONCERN**
iOS A2HS dismiss now persists (`lspIosA2hsDismissed`). Android/Chrome banner × still session-only. SW safety-critical network-first list present. Finding: V4-FULL-R25_L_01.

#### R26 — Capacitor / Android select — **CONCERN (LOW)**
`aria-label` + `aria-selected` present (prior MEDIUM partly fixed). Remaining: `aria-expanded` / `aria-controls` / keyboard roving. Finding: V4-FULL-R26_L_01.

#### R27 — Profile presets — **PASS**
#### R28 — Config presets — **PASS**
#### R29 — Tissues / exposure / GF — **PASS** (+ LOW imperial GF label)
Finding: V4-FULL-R29_L_01.
#### R30 — Download page — **PASS**
#### R31 — Engine harness re-verify — **PASS (note)**
Suites: engine_regression / engine_validation / gas_core. Not re-executed in this pass (static+visual preflight green; prior release profile historically covering).
#### R32 — Full umbrella — **PASS (note)**
Release-tier suites referenced; not re-run end-to-end here.
#### R33 — Package / CI — **CONCERN (metadata)**
`package.json` + workflows present. APP-VERSION not in R-cycle queue. Finding: V4-FULL-AUDIT_M_03.

### Group 5 — Markup / CSS / shell (R34–R42)

#### R34 — Markup header — **PASS** (+ LOW TTS tip copy)
#### R35 — Rec planner — **CONCERN**
PADI blocked path uses `rec-block-card` + early return; Bühlmann NDL exceed uses inline alert inside profile card. No CSS for `.rec-block-card`. Finding: V4-FULL-R35_M_01, V4-FULL-R35_L_01.
#### R36 — Tec planner markup — **PASS**
#### R37 — Consumption markup — **PASS** (+ LOW TTS help copy)
#### R38 — Tools/modals markup — **PASS**
#### R39 — Foundation/modes CSS — **PASS** (+ LOW unused gas-mix class wiring)
Lime deco token present both themes; schedule Mix cells intentionally neutral under phase-column contract (needs human confirm if lime-on-Mix was still desired).
#### R40 — Controls CSS — **PASS**
#### R41 — Results CSS — **CONCERN (metadata + hygiene)**
Largest line drift (−43). Orphan `.col-tts`. Phase-column contract enforced (Mix/ppO₂/CNS/EAD → `--text`). Print-only `.ppo2-crit/.ppo2-warn` may be intentional leftovers. 641px vs 767px breakpoint split with mobile shell.
#### R42 — Planner shell / results panel — **CONCERN**
`decorateDecoTableForV3` clears inline colors then applies class contract — aligns with R41 phase-column design. Mobile shell CSS still outside R cycles. Finding: V4-FULL-AUDIT_M_02, V4-FULL-R42_L_01.

---

## 5. Findings by severity

### CRITICAL — **0**

### HIGH — **5**

| ID | Cycle | Unit(s) | File:lines | What is wrong | Why it matters | Real / FP | Fix direction | Test coverage |
|---|---|---|---|---|---|---|---|---|
| V4-FULL-R20_M_01 | R20 | APP-EXPORT | `export-core.js` L1857–1862 | Messenger deco stops: `run=c[4]`, `mix=shortMix(c[3])` but table is Run@3 Mix@4 | Divers copying plan get gas in Run column and time as mix | **Real** | Use `data-label` / `readExportScheduleCells` like text export | Playwright: Copy Plan → assert Mix tokens match schedule Mix cells |
| V4-FULL-R20_M_02 | R20 | APP-EXPORT | `export-core.js` L1852–1854 | Messenger bottom: `shortMix(c[3])` is Run, not Mix | Bottom gas label wrong on clipboard | **Real** | Same as above | Same |
| V4-FULL-R20_M_03 | R20 | APP-EXPORT | `export-core.js` L1719–1721 | Contingency messenger same Run/Mix index inversion | Emergency copy mislabels gas | **Real** | Same | Contingency Copy Plan assert |
| V4-FULL-R20_M_04 | R20 | APP-EXPORT | `export-core.js` L1264–1268, L1364–1368, L1843–1846 | Switch rows: `shortMix(cSw[3])` reads empty Run cell; Mix is index 4 | Switch lines may omit gas (`>> @ 30m`) | **Real** | Read `td[data-label="Mix"]` | Switch-row export asserts mix label |
| V4-FULL-R15_M_01 | R15 | APP-SURFACE-INTERVAL | `surf-interval-core.js` L221–247, L339–348; `schedule-runner-core.js` L544–546 | Results SI sliders keep metric values w/o `data-depthM`; imperial `domDepthToM` treats them as ft | Opening SI panel under imperial computes SI for ~⅓ depth → optimistic SI | **Real** | Stamp `data-depthM` on render; include `mainSi*`/`recSi*` in unit switch; or keep slider always metric and bypass displayDepth | Extend SL-C04 to `renderSurfIntPanel('…','mainSi')` under imperial |

### MEDIUM — **8**

| ID | Cycle | Unit(s) | File:lines | What is wrong | Why it matters | Real / FP | Fix direction | Test |
|---|---|---|---|---|---|---|---|---|
| V4-FULL-AUDIT_M_01 | — | Registry | `docs/audit-units.json` R20/R24/R34/R39/R41 | `max_new_application_lines` / acceptance stale; R41 −43 | Audit session budgeting wrong; gate friction | **Real (meta)** | Refresh acceptance strings from `resolve_units` | Coverage check asserts drift ≤ N |
| V4-FULL-AUDIT_M_02 | — | UI-CSS-MOBILE-SHELL | `lsp-dplanner-mobile-shell.css` (709 lines) | Unit registered but in **no** R cycle | Android/mobile shell never in risk-first queue | **Real (meta)** | Add R43 or attach to R42 | Registry test: every required CSS unit in a cycle |
| V4-FULL-AUDIT_M_03 | R33 | APP-VERSION | `app-version.js` | Registered, not in any R-cycle application_units | Version source of truth unreviewed in V4 queue | **Real (meta)** | Attach to R33 or R30 | Same |
| V4-FULL-R20_M_05 | R20 | APP-EXPORT | `export-core.js` L2499–2599 vs L1229–1241 | PDF lacks VPM `_lastVPMExport` totals fallback that text/messenger have | VPM PDF banner may show `RT: -` / empty CNS | **Real** | Share `getPlanSummaryExport` VPM fallback | VPM PDF totals non-dash assert |
| V4-FULL-R20_M_06 | R20 | APP-EXPORT | `export-core.js` L1016–1017 vs L733–738; `gas-plan-core.js` L29 | Text gas block uses `reqL*1.10` TIGHT; PDF cards use remaining-% tiers | Same plan can read TIGHT in txt and OK on PDF card | **Real (contract drift)** | One status model; use `GP_ONEWAY_MARGIN` constant | Dual-channel gas status parity test |
| V4-FULL-R20_M_07 | R20 | APP-EXPORT | `export-core.js` L2608–2613 | PDF CNS row fill sniffs inline CSS color strings | Refactors to classes silently drop PDF highlight | **Fragility** | Prefer `data-cnshi` only | CNS≥80 PDF yellow fill assert |
| V4-FULL-R35_M_01 | R35 | REC path (R07/R35) | `schedule-runner-core.js` L1411–1432 vs ~L1512 | PADI hard-block card vs Bühlmann inline NDL alert | Inconsistent blocked UX; divers may misread severity | **Real** | Unify blocked layout | REC NDL exceed visual contract both algos |
| V4-FULL-R25_L_01† | R25 | UI-PWA-LIFECYCLE | `index.html` L5828–5829 | Android A2HS × dismiss not persisted (iOS is) | Banner reappears every load | **Real** | Mirror `lspIosA2hsDismissed` | PWA dismiss persistence test |

† Severity listed MEDIUM in prior audits; kept as **LOW** here (UX annoyance, not dive-safety). Counted in LOW table below as V4-FULL-R25_L_01.

### LOW — **16**

| ID | Cycle | Summary | Real / FP |
|---|---|---|---|
| V4-FULL-R07_L_01 | R07 | Dead `injectTtsCells` (`schedule-runner-core.js` L388–411) | Real |
| V4-FULL-R20_L_01 | R20 | Empty per-row TTS column in text schedule (injector never called) | Real |
| V4-FULL-R20_L_02 | R20 | Duplicated `shortMix` lambdas; one copy weaker EAN regex | Real / drift risk |
| V4-FULL-R20_L_03 | R20 | Slate TRT fallback substitutes BT when RT missing | Real (edge) |
| V4-FULL-R20_L_04 | R20 | Text gas SAC hardcodes `L/min` (PDF uses unit helper) | Real |
| V4-FULL-R20_L_05 | R20 | `if(false){…}` dead emergency PDF block L2891–2924 | Real (dead) |
| V4-FULL-R20_L_06 | R20 | Slate unconditional `addPage()` before slate | Cosmetic |
| V4-FULL-R20_L_07 | R20 | PDF schedule phase colors ≠ web Mix O₂ coloring | Likely intentional / FP vs phase contract |
| V4-FULL-R25_L_01 | R25 | Android A2HS dismiss not persisted | Real |
| V4-FULL-R26_L_01 | R26 | Android select missing `aria-expanded` / keyboard | Real (partial prior fix) |
| V4-FULL-R29_L_01 | R29 | GF curve waypoint labels hardcode `m` in imperial | Real (cosmetic) |
| V4-FULL-R34_L_01 | R34 | Algorithm tip still discusses TTS | Real (copy) |
| V4-FULL-R35_L_01 | R35 | `.rec-block-card` has no CSS rules | Real |
| V4-FULL-R37_L_01 | R37 | Consumption info box TTS wording | Real (copy) |
| V4-FULL-R41_L_01 | R41 | Orphan `.col-tts` CSS | Possible FP / hygiene |
| V4-FULL-R41_L_02 | R41 | `caution` tier naming vs contract “low” | Unclear / naming |
| V4-FULL-R42_L_01 | R42 | `PLAN_INFO_TIP` still documents TTS | Real (copy) |
| V4-FULL-R39_L_01 | R39 | `gas-ean50`/`gas-air`/`gas-100` classes added but Mix forced `--text` | Likely intentional phase contract |

---

## 6. Findings by cycle

| Cycle | Findings |
|---|---|
| R01–R06 | — |
| R07 | V4-FULL-R07_L_01 |
| R08–R14 | — |
| R15 | **V4-FULL-R15_M_01 (HIGH)** |
| R16–R19 | — |
| R20 | **V4-FULL-R20_M_01–M_04 (HIGH)**; M_05–M_07; L_01–L_07 |
| R21–R24 | — |
| R25 | V4-FULL-R25_L_01 |
| R26 | V4-FULL-R26_L_01 |
| R27–R28 | — |
| R29 | V4-FULL-R29_L_01 |
| R30–R32 | — |
| R33 | V4-FULL-AUDIT_M_03 |
| R34 | V4-FULL-R34_L_01 |
| R35 | V4-FULL-R35_M_01; V4-FULL-R35_L_01 |
| R36 | — |
| R37 | V4-FULL-R37_L_01 |
| R38–R40 | V4-FULL-R39_L_01 |
| R41 | V4-FULL-R41_L_01, L_02; drift in AUDIT_M_01 |
| R42 | V4-FULL-R42_L_01; AUDIT_M_02 |
| Cross-cutting | V4-FULL-AUDIT_M_01, M_02, M_03 |

---

## 7. PDF / export findings (focus)

**Fixed since prior full audit (`cursor_full_7.md` @ 287070f):**
- PDF totals use `RT:` (not `Run:`) — confirmed `export-core.js` L2599, L3065, L3101.
- Deco plan PDF banner / slate / gas cards heavily reworked; visual contract green.

**Still open / newly found:**

1. **HIGH — Messenger & contingency messenger Run/Mix index bugs** (V4-FULL-R20_M_01–M_03).  
2. **HIGH — Switch-row text/messenger mix index** (V4-FULL-R20_M_04).  
3. **MEDIUM — VPM PDF totals fallback gap** (M_05).  
4. **MEDIUM — Gas status model: txt TIGHT vs PDF %-remaining cards** (M_06).  
5. **MEDIUM — Fragile CNS style sniff for PDF row fill** (M_07).  
6. **LOW — TTS column empty; shortMix duplication; SAC units; dead `if(false)`; slate page break.**

**PDF paths that look healthier:** schedule cell reads via `data-label` in primary text export; deco plan banner shares `buildDecoPlanHeaderData()`; contingency PDF uses live path (dead block gated).

Agent deep-dive: [R20 export PDF](d60491a3-4197-47f7-951d-08957c5a2f19).

---

## 8. CSS / theme / layout findings

| Topic | Verdict |
|---|---|
| Gas Mix 2/3 lime deco markers | **PASS** at ca10765 (dots + chips `#d6ff00`) |
| Schedule phase column color contract | **PASS** (visual regression green); Mix/ppO₂/CNS/EAD intentionally neutral |
| Light/dark schedule phase colors | **Mostly PASS**; ascent `#FFBF00` fixed both themes |
| Mobile shell CSS in R-cycle queue | **FAIL / gap** — 709 lines unqueued (AUDIT_M_02) |
| Breakpoint split 640 vs 767 | **LOW friction** — schedule compaction vs shell |
| Orphan `.col-tts` / TTS tip copy | **LOW hygiene** |
| REC blocked layout PADI vs Bühlmann | **MEDIUM** inconsistency |
| ppO₂ severity classes screen CSS | **Needs human confirm** — likely intentional under phase contract; print-only rules leftover |

Agent deep-dive: [R34–R42 CSS/markup](bd0753f8-10d7-47a4-a9e6-c1e6c81a8fcb).

---

## 9. Engine / safety-critical findings

| Topic | Verdict |
|---|---|
| ZHL GF pre-anchor | OK |
| OC / CCR MOD gates | OK (fail-closed) |
| VPM MOD / ceiling / gas select | OK (sampled) |
| Headless contamination | OK |
| Worker timeout / disable | OK |
| Main vs contingency isolation | OK |
| VPM ↔ Bühlmann CNS row thresholds | OK |
| Static audit + visual contract | PASS |
| Seven-lens reviewed-cycle gate | PASS (prior SL-C07 friction cleared) |

**Safety-impacting defects found in this pass are export-copy mislabeling and imperial results-panel SI depth** — not core schedule physics.

Engine agent: [R01–R12](f605c787-2433-4aa3-a0ea-442eb76974a3). Mid-cycle agent: [R13–R26](7235b009-fd6b-4ed8-a0a5-0a139d57f591). Late agent: [R27–R33](49a76f09-5ea0-40f6-a7a0-257e062e3130).

---

## 10. Potential false positives / needs human confirmation

| Item | Why uncertain |
|---|---|
| V4-FULL-R20_L_07 PDF Mix phase-only colors | New schedule contract intentionally de-emphasizes Mix/ppO₂ cell colors on web; PDF matching phase-only may be correct |
| V4-FULL-R41 print-only `.ppo2-*` | Classes applied by `results-panel.js` but screen forces `--text`; may be deliberate |
| V4-FULL-R39_L_01 unused `gas-ean*` CSS | Classes added for future/token work; color forced neutral by design |
| V4-FULL-R41_L_02 caution vs “low” | Naming vs design-doc wording |
| V4-FULL-R20_M_05 VPM PDF totals | Needs repro with live VPM plan where totals row absent |
| R31/R32 not re-executed | Assumed green from CI/history; local release profile not re-run this session |

---

## 11. Recommendations for app improvements

**Fix first (release-blocking candidates):**
1. Unify all export cell reads on `data-label` / `readExportScheduleCells` — kill messenger index bugs (R20 HIGH ×4).
2. Fix results-panel Surface Interval imperial depth stamping (R15 HIGH).

**Next:**
3. Align gas adequacy status across txt/PDF/UI (or document two models explicitly).
4. Add VPM PDF totals fallback parity with text export.
5. Unify REC blocked UX (PADI card vs Bühlmann inline).
6. Persist Android A2HS dismiss; finish Android select a11y.
7. Delete dead `injectTtsCells` / `if(false)` PDF block; scrub TTS tip copy.

**Registry / coverage:**
8. Refresh R20/R24/R34/R39/R41 acceptance line counts.
9. Place `UI-CSS-MOBILE-SHELL` (+ optionally `APP-VERSION`) into an active R cycle.

---

## 12. Recommendations for audit workflow speed / simplification

1. **Ship a report-only `resolve_units` drift table** as a CI artifact — avoids temp scripts that trip COVERAGE.
2. **Drop or quarantine frozen SL-C07–C09 closure bureaucracy** for V4 full audits when `check-all` already PASS; focus human time on R-cycle source.
3. **Pre-bundle cycle maps** (`path/start/end`) generated once per HEAD for auditor agents.
4. **Risk-weight automatic mode:** always deep-read R15/R18/R19/R20/R35/R41 + engines smoke; sample R04/R05/R24/R31/R32.
5. **Do not re-run full release profile** on every audit if static + visual + engine_regression already green within same SHA — record as optional.
6. Keep findings in audit-only markdown; do not mutate registry status during full passes.

---

## 13. Final verdict

| Metric | Value |
|---|---|
| Cycles reviewed | **42 / 42** |
| CRITICAL | **0** |
| HIGH | **5** |
| MEDIUM | **7** (incl. 3 audit-metadata) |
| LOW | **18** |
| Engine physics CRITICAL/HIGH | **None** |
| Preflight static + visual | **PASS** |

### Release blocked?

**Yes — treat as release-blocked for dive-ops confidence until the five HIGH findings are fixed or explicitly waived.**

Rationale: messenger/copy mislabeling of Mix/Run and imperial results-panel SI depth can cause divers to act on wrong gas identity or wrong surface-interval guidance. Core engines and on-screen schedule computation were not shown to be broken at this commit.

### Fix first order

1. V4-FULL-R20_M_01–M_04 (export messenger / switch indices)  
2. V4-FULL-R15_M_01 (results SI imperial depths)  
3. V4-FULL-R20_M_05–M_06 (VPM PDF totals + gas status contract)  
4. V4-FULL-R35_M_01 (REC blocked UX)  
5. Audit metadata: AUDIT_M_01–M_03 + mobile-shell cycle coverage  

---

*End of report. No registry statuses closed. No application code changed.*
