# Seven-Lens Audit — Cycle 07 (UI-CSS-RESULTS)

**Branch:** `cursor/seven-lens-cycle-07-results-css`
**Baseline:** `6b192cf416e332c2f216762be86cce27bb48485c`
**Schema:** v5
**Auditor:** Cursor GPT-5.5 Medium

## Review sessions

| Session | Unit | Boundary | Lines | Part ID |
|---------|------|----------|------:|---------|
| C07-A | `UI-CSS-RESULTS` | `lsp-dplanner-results.css` | 1–500 | `UI-CSS-RESULTS-P01` |
| C07-B | `UI-CSS-RESULTS` | `lsp-dplanner-results.css` | 501–931 | `UI-CSS-RESULTS-P02` |

**Total canonical lines:** 931 (protocol `end_line` 931; file ends at line 931 with closing brace rule).

**Dependency context traced (not reviewed coverage):** `index.html` / `ui/markup-header.html` results shell, `results-panel.js`, `results-render-core.js`, `export-core.js`, `contingency-core.js`, `gas-plan-core.js`, `plot-core.js`, `planner-shell.js`, stylesheet order (foundation → modes → controls → results).

## Baseline gates

| Command | Exit | Notes |
|---------|-----:|-------|
| `python tools/seven_lens_protocol.py plan --cycle 7 --output docs/seven-lens-reports/cycle-07-record.json` | 0 | HEAD = `origin/dev` = `6b192cf` |
| `python -m tools.audit check --profile static` | 0 | 11 checks, 4 suites PASS |
| `python -m tools.audit run --profile release` | 0 | 20 suites PASS incl. `SUITE-UI-CSS-REGRESSION`, `SUITE-UI-CONTROLS-CSS-REGRESSION` |
| `python tools/seven_lens_protocol.py check-all --require-artifacts` | 0 | Reviewed-cycle gate PASS |
| `git status --short` (pre-audit) | clean | After plan: `?? cycle-07-record.json` only |

**Integration base:** `6b192cf416e332c2f216762be86cce27bb48485c`

## Runtime matrices exercised

Probes used visible `#recGenerateBtn` / `#tecGenerateBtn` clicks with `window._zhlHeadless = false` so DOM writers render. Viewports: 1280×800, 375×667, 667×375 (reduced-motion).

| # | Path | Result |
|---|------|--------|
| 1 | REC NDL (`runRecPlan` 18 m / 20 min) | `has-results`, metric strip, `metric-val--runtime` blue |
| 2 | TEC deco (45 m / 25 min, `#tecGenerateBtn`) | 15 schedule rows, `.schedule-table`, switch rows yellow |
| 3 | ZHL (default algorithm) | Same TEC path with Bühlmann GF |
| 4 | VPM (`algorithmSelect=VPMB`) | 14 rows, results rendered |
| 5 | OC / gas switch | `tr.row-switch` gold `rgb(234,179,8)` |
| 6 | CCR | Not separately exercised (build default open-circuit path) |
| 7 | Contingency tab | `#resultTab-contingency.active`, red calc button |
| 8 | Invalid input | Prior `has-results` persists when validation fails (JS); CSS hides empty state via `.has-results` |
| 9 | Recalculation | Runtime metric changes after depth 45→30 m |
| 10 | Imperial REC | `has-results` after unit switch |
| 11 | Desktop 1280×800 | Tab focus outline auto 3px |
| 12 | Mobile 375×667 | Bottom nav 56px; tabs `overflow-x:auto` |
| 13 | Landscape 667×375 | Reduced-motion query true; tab transitions still `all` |
| 14 | Long schedule overflow | `.schedule-wrap { overflow-x:auto }` |
| 15 | Keyboard focus | `#tecResultTabs .result-tab-btn` focus outline visible (browser default) |
| 16 | Print/PDF CSS | No `@media print` in canonical sheet |
| 17 | Reduced motion | Slider thumb 0s in reduce context; tab/mode transitions active |
| 18 | Light/dark themes | Light `#decoAlerts .alert.deco` red bg `#FF4433`, text `#111` weight 700 |

## Findings (OPEN)

### SL-C07-M-01: Results chip-yellow renders as orange

- **Severity:** MEDIUM | **Lenses:** L1, L6 | **Part:** C07-B | **Location:** `lsp-dplanner-results.css:574`
- **Root cause:** `#resultsPanel .chip-yellow` uses `--status-orange-dim` / `--status-orange`, matching `.chip-orange`.
- **Failure path:** TEC plan → `renderChipRow` → TTS chip `chip-yellow` → computed color equals OTU `chip-orange`.
- **Impact:** Chip row severity tiers not distinguishable by color.
- **Regression ID:** `SL-C07-CHIP-YELLOW-ORANGE-PARITY`

### SL-C07-M-02: PPO2 severity colors neutralized on schedule rows

- **Severity:** MEDIUM | **Lenses:** L4, L6 | **Part:** C07-B | **Location:** `lsp-dplanner-results.css:756-758` (conflicts with `:739-742`)
- **Root cause:** `tr.deco-row/asc-row/safe-row td { color: inherit }` overrides `.ppo2-*` rules written by `decorateDecoTableForV3`.
- **Failure path:** 45 m TEC plan → cells with `ppo2-warn` / `ppo2-crit` → muted gray colors identical across tiers.
- **Impact:** Elevated/critical ppO2 not visually distinct in schedule table.
- **Regression ID:** `SL-C07-PPO2-SEVERITY-COLORS`

### SL-C07-L-01: Dead legacy mobile deco card CSS

- **Severity:** LOW | **Lenses:** L4, L5 | **Part:** C07-A | **Location:** `lsp-dplanner-results.css:184-295` vs `:418`
- **Root cause:** Rules scoped to `.legacy-panels` while V4 hides `.legacy-panels`.
- **Regression ID:** `SL-C07-CSS-DEAD-LEGACY-MOBILE-CARD`

### SL-C07-L-02: Obsolete `.algo-switcher` rules

- **Severity:** LOW | **Lenses:** L4 | **Part:** C07-A | **Location:** `lsp-dplanner-results.css:382-384`
- **Root cause:** Class absent from live `index.html` shell.
- **Regression ID:** `SL-C07-CSS-DEAD-ALGO-SWITCHER`

### SL-C07-L-03: Results transitions ignore reduced motion

- **Severity:** LOW | **Lenses:** L1, L2 | **Part:** C07-B | **Location:** `lsp-dplanner-results.css:308,421,474,560,848`
- **Root cause:** No `@media (prefers-reduced-motion: reduce)` overrides.
- **Regression ID:** `SL-C07-REDUCED-MOTION-RESULTS`

### SL-C07-L-04: No print stylesheet for results panel

- **Severity:** LOW | **Lenses:** L1, L5 | **Part:** C07-B | **Location:** `lsp-dplanner-results.css` (whole unit)
- **Root cause:** No `@media print` block in canonical results CSS.
- **Regression ID:** `SL-C07-PRINT-RESULTS-CSS`

## Lens summary

Full L1–L7 notes are in `cycle-07-record.json` for both parts.

**C07-A highlights:** Deco/gas-plan table geometry, mobile card rules (legacy-only), V4 shell visibility (`.legacy-panels` hidden), slider/NDL/tools layout utilities. Primary defects: dead legacy mobile block, dead `.algo-switcher`.

**C07-B highlights:** `#resultsPanel` V4 schedule presentation, metric/chip/alert styling, contingency card, mobile bottom nav, theme pill. Primary defects: chip-yellow/orange collapse, PPO2 color neutralization, missing reduced-motion and print rules.

**L7:** No computed-style regression suite targets `lsp-dplanner-results.css`. Existing `SUITE-UI-CSS-REGRESSION` covers Cycle 05 foundation/modes only.

## Audit checkpoint

*(filled after audit commit)*

## Attestation

*(filled after attestation commit)*

## Worktree confirmation

No application source (`*.css`, `*.js`, `*.html`) or test files were modified during this audit pass.

---

**Next step:** A fresh **FIXER** chat is required — six OPEN findings remain.
