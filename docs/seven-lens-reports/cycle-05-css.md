# Seven-Lens Audit — Cycle 05 (UI-CSS-FOUNDATION + UI-CSS-MODES)

**Branch:** `cursor/seven-lens-cycle-05-css`  
**Baseline:** `39159b0`  
**Schema:** v4  
**Auditor:** Cursor GPT-5.5 Medium

## Review sessions

| Session | Unit | Boundary | Lines | ID |
|---------|------|----------|------:|----|
| C05-A | `UI-CSS-FOUNDATION` | `lsp-dplanner-foundation.css` | 1–454 | `cursor/seven-lens-cycle-05-foundation-audit` |
| C05-B | `UI-CSS-MODES` | `lsp-dplanner-modes.css` | 1–372 | `cursor/seven-lens-cycle-05-modes-audit` |

**Dependency context traced (not reviewed coverage):** `index.html` stylesheet order, `planner-shell.js` (`initV3Layout`, `setNavMode`), `settings-core.js` (`_showPlannerView`, `toggleTheme`), `ui/markup-header.html`, `ui/markup-tec-planner.html`, `lsp-dplanner-results.css` (downstream cascade for `.header-warn`, `.theme-pill-toggle`, planner visibility).

## Findings (OPEN)

### SL-C05-M-01: Mode-isolation CSS targets removed `#gfPresetsRow`

- **Severity:** MEDIUM  
- **Lenses:** L3, L4, L6, L7  
- **Unit:** UI-CSS-FOUNDATION, UI-CSS-MODES  
- **Location:** `lsp-dplanner-foundation.css:443-454`; `lsp-dplanner-modes.css:13-23`; `planner-shell.js:116-124`  
- **Root cause:** V3 `initV3Layout` reparents GF controls into `#gfPresetsMount` and removes `#gfPresetsRow`, but REC/Tools opacity rules still target the removed id. Runtime GF UI lives under `#gfPresetsRowV3` / `#gfPresetBtns`.  
- **Failure path:** Load app → `initV3Layout()` → `#gfPresetsRow` removed → `body.rec-mode #gfPresetsRow` / `body.algo-tools #gfPresetsRow` never match → `#gfPresetBtns` stays full opacity if parent view were visible.  
- **Impact:** Mode-isolation styling is stale; mitigated today by view-level `.visible` toggles on `#recPlannerView` / `#tecPlannerView`, but CSS no longer enforces GF disable if layout or visibility rules change.  
- **Evidence:** Selector audit; `tests-massive.html:1801-1803` checks row presence only, not computed disable state.  
- **Regression ID:** `SL-C05-GF-ROW-MODE-ISOLATION`  
- **Status:** OPEN

### SL-C05-M-02: Export buttons suppress keyboard focus ring

- **Severity:** MEDIUM  
- **Lenses:** L2, L6  
- **Unit:** UI-CSS-MODES  
- **Location:** `lsp-dplanner-modes.css:275-276`  
- **Root cause:** `.btn-export:focus { outline: none; }` removes the focus indicator with no `:focus-visible` replacement (unlike `.theme-pill-toggle:focus-visible` in `lsp-dplanner-results.css:821`).  
- **Failure path:** Keyboard Tab to `.btn-export` → `:focus` matched → `outline: none` → no visible focus ring.  
- **Impact:** Keyboard users cannot see which export/copy control is focused; safety-critical export actions harder to verify before activation.  
- **Evidence:** Source inspection; no computed-style regression in `SUITE-UI-STRUCTURE`.  
- **Regression ID:** `SL-C05-EXPORT-FOCUS-VISIBLE`  
- **Status:** OPEN

### SL-C05-L-01: Obsolete `.brand-icon` rules

- **Severity:** LOW  
- **Lenses:** L4  
- **Unit:** UI-CSS-FOUNDATION  
- **Location:** `lsp-dplanner-foundation.css:359-372`  
- **Root cause:** Markup uses `.brand-logo` img; `setBrandIcon()` is a no-op stub.  
- **Failure path:** N/A — selectors never match canonical markup.  
- **Impact:** Dead CSS; no runtime effect.  
- **Regression ID:** `SL-C05-CSS-DEAD-BRAND-ICON`  
- **Status:** OPEN

### SL-C05-L-02: Obsolete `#gfCustomRow .gf-btn` rules

- **Severity:** LOW  
- **Lenses:** L4  
- **Unit:** UI-CSS-FOUNDATION  
- **Location:** `lsp-dplanner-foundation.css:396-410`  
- **Root cause:** `#gfCustomRow` contains `<select>` elements only; preset buttons use `.gf-preset-btn` in `#gfPresetBtns`.  
- **Failure path:** N/A — `.gf-btn` not present under `#gfCustomRow`.  
- **Impact:** Dead CSS.  
- **Regression ID:** `SL-C05-CSS-DEAD-GF-BTN`  
- **Status:** OPEN

### SL-C05-L-03: Obsolete `.algo-switcher` rules

- **Severity:** LOW  
- **Lenses:** L3, L4  
- **Unit:** UI-CSS-FOUNDATION, UI-CSS-MODES  
- **Location:** `lsp-dplanner-foundation.css:391-393`; `lsp-dplanner-modes.css:27-35`  
- **Root cause:** V3 header removed `.algo-switcher`; Training/REF now live in `#headerBanner` / `#header-actions`.  
- **Failure path:** Tools-mode “keep REF bright” exception never matches.  
- **Impact:** Dead CSS; REF/disclaimer remain bright via separate DOM placement, not these rules.  
- **Regression ID:** `SL-C05-CSS-DEAD-ALGO-SWITCHER`  
- **Status:** OPEN

### SL-C05-L-04: Obsolete `.theme-toggle` rules

- **Severity:** LOW  
- **Lenses:** L4, L5  
- **Unit:** UI-CSS-MODES  
- **Location:** `lsp-dplanner-modes.css:191-215`  
- **Root cause:** Markup uses `#themeToggle.theme-pill-toggle`; active styles in `lsp-dplanner-results.css:820-821`.  
- **Failure path:** N/A — `.theme-toggle` not in canonical markup.  
- **Impact:** Dead CSS in modes unit; theme control styled by results sheet.  
- **Regression ID:** `SL-C05-CSS-DEAD-THEME-TOGGLE`  
- **Status:** OPEN

## Lens summary

Both units received full L1–L7 notes in `cycle-05-record.json`. Static parity gates pass (`UI-EXTRACT-CSS`, `UI-CSS-LINK-ORDER`, `UI-SW-PRECACHE`). No computed-style or mode-isolation browser regressions exist for these sheets; `SUITE-UI-STRUCTURE` validates extraction and link order only.

**C05-A (foundation):** Token clamp math and safe-area modal padding are sound. Light-theme overrides restore safety colors for gas warnings and metric chips. Bühlmann grid and bubble animations respect `body.algo-buh`. Primary defects are stale `#gfPresetsRow` / `.brand-icon` contracts.

**C05-B (modes):** Tab/panel visibility cascade is coherent with `switchTab()`. `.buh-only` isolation depends on `body.algo-buh` from `settings-core.js`. Specificity split on `#gfLowInput`/`#gfHighInput` is intentional (foundation base !important, modes :focus accent). Primary defects are stale tools/REC row selectors, dead legacy classes, and missing export focus-visible.

## Independent verification (PASSED)

**Verifier:** Cursor Agent (VERIFIER)  
**Sessions:** `C05-V-A` (UI-CSS-FOUNDATION), `C05-V-B` (UI-CSS-MODES)  
**Audit commit:** `ded650c`  
**Verified source commit:** `c40b71a`  
**Verification attestation HEAD:** `7de78b2`  
**verification_status:** `PASSED`

### Branch and worktree

- `HEAD` equals `origin/cursor/seven-lens-cycle-05-css` at `7de78b2`
- PR targets `dev` (branch policy)
- Historical `baseline_findings` intact in `cycle-05-record.json`
- Changes since audit checkpoint limited to: `lsp-dplanner-foundation.css`, `lsp-dplanner-modes.css`, `dev/ui_css_regression.py`, `docs/seven-lens-traces/cycle-05-css.json`, evidence artifacts, and audit metadata

### Pre-fix reproduction (`0e83bcb` execution worktree)

| Finding | Observable failure | Reason confirmed |
|---------|-------------------|------------------|
| SL-C05-M-01 | `recBtnOp`/`toolsBtnOp` = 1.0 | Stale `#gfPresetsRow` selectors; V3 uses `#gfPresetsRowV3`/`#gfPresetBtns` |
| SL-C05-M-02 | `.btn-export` `outlineStyle: none` | `:focus { outline: none }` without `:focus-visible` replacement |
| SL-C05-L-01..04 | Dead CSS rules present in canonical sheets | Selectors have no markup/JS consumers |

Browser trace at pre-fix: `rec-dimmed`/`tools-dimmed` failed (`1 close 0.5`); body mode classes applied correctly.

### Post-fix confirmation (`c40b71a` / current source)

- GF preset opacity: TEC 1.0; REC/Tools 0.5 — both navigation orders (`buh-rec-tools`, `tools-rec-buh`) — desktop 1280×800 and mobile 375×667
- Export keyboard Tab reaches `.btn-export` with `outlineWidth: 2`, `outlineStyle: solid`
- Dead selectors removed; `.brand-logo` and `#themeToggle.theme-pill-toggle` intact
- Browser trace PASS ×2 fresh contexts; `state_before_sha256` == `state_after_sha256`
- `python tools/assemble_ui_html.py --verify` PASS
- `python -m tools.audit check --profile static` PASS
- `python -m tools.audit run --profile ci` PASS (includes `SUITE-UI-CSS-REGRESSION`)
- `python -m tools.audit run --profile release` PASS

### Final fingerprints

| Unit | Fingerprint |
|------|-------------|
| UI-CSS-FOUNDATION | `f1f5eaa00edd3fd382ff98c27985e51d565539079860d7e59d740bce2d6a1944` |
| UI-CSS-MODES | `6d911804be64d352c6d0d74a4db18bb61887de96456f8f4dd3ac59e205f7b096` |

Findings remain **OPEN** in this record for the CLOSER chat. Do not merge until closure gates pass.

## Closure (CLOSED)

**Closer:** Cursor Agent (CLOSER)  
**Closure commit:** pending  
**Merge target:** `dev`  
**verified_source_commit:** `c40b71a` (unchanged)  
**verification_status:** `PASSED`

All six findings marked **CLOSED** with schema-v4 evidence receipts at `c40b71a`:

| Finding | Regression ID(s) | Status |
|---------|------------------|--------|
| SL-C05-M-01 | `SL-C05-GF-ROW-MODE-ISOLATION` | CLOSED |
| SL-C05-M-02 | `SL-C05-EXPORT-FOCUS-VISIBLE` | CLOSED |
| SL-C05-L-01 | `SL-C05-CSS-DEAD-BRAND-ICON` | CLOSED |
| SL-C05-L-02 | `SL-C05-CSS-DEAD-GF-BTN` | CLOSED |
| SL-C05-L-03 | `SL-C05-CSS-DEAD-ALGO-SWITCHER` | CLOSED |
| SL-C05-L-04 | `SL-C05-CSS-DEAD-THEME-TOGGLE` | CLOSED |

Final fingerprints unchanged: `UI-CSS-FOUNDATION` `f1f5eaa…`, `UI-CSS-MODES` `6d911804…`.
