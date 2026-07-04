# Seven-Lens Audit — Cycle 06 (UI-CSS-CONTROLS)

**Branch:** `cursor/seven-lens-cycle-06-controls-css`  
**Baseline:** `7cd5897`  
**Schema:** v4  
**Auditor:** Cursor GPT-5.5 Medium

## Review session

| Session | Unit | Boundary | Lines | ID |
|---------|------|----------|------:|----|
| C06-A | `UI-CSS-CONTROLS` | `lsp-dplanner-controls.css` | 1–528 | `C06-A` |

Protocol planner split the unit into `UI-CSS-CONTROLS-P01` (1–500) and `UI-CSS-CONTROLS-P02` (501–528) for the 500-line chunk gate; both parts were reviewed in session **C06-A** (528 lines, one bounded session).

**Dependency context traced (not reviewed coverage):** `index.html` stylesheet order (foundation → modes → controls → results), `gas-plan-core.js` (`setGasRule`), `planner-shell.js` (`toggleVpmMode`, `_syncVpmModeUI`), `index.html` inline writers (`toggleStopDepth`, `setDiveCount`, `buildUnifiedPlan`, `buildDiveBlocks`), `gas-cards-core.js` (dynamic gas cards), `android-select-picker.js`, `export-core.js` / `contingency-core.js` / `results-render-core.js` (`.alert`, `.dive-plan-banner`, `.result-card`), `results-panel.js` (`switchTab` → `buildDiveBlocks`).

## Findings (OPEN)

### SL-C06-M-01: Segmented controls suppress keyboard focus ring

- **Severity:** MEDIUM  
- **Lenses:** L2, L6  
- **Unit:** UI-CSS-CONTROLS  
- **Location:** `lsp-dplanner-controls.css:23-38`  
- **Root cause:** `.seg-btn` defines `:hover` and `.active` states only; no `:focus` or `:focus-visible` replacement. Browser default outline is suppressed when focus lands on the control.  
- **Failure path:** Keyboard Tab to `#gpRuleThirds` / `#dc2` → `element.focus()` → `getComputedStyle(el).outlineStyle === 'none'`.  
- **Impact:** Keyboard users cannot see which gas-rule or dive-count segment is focused before activating a safety-relevant rule change.  
- **Evidence:** Playwright probe at 375×667 and 1280×800 (`outlineStyle: none`, `outlineWidth: 3`); contrast with `.option-pill-toggle:focus-visible` at `:42-43` which does expose a ring.  
- **Regression ID:** `SL-C06-SEG-FOCUS-VISIBLE`  
- **Status:** OPEN

### SL-C06-M-02: Gas numeric fields undersize touch targets

- **Severity:** MEDIUM  
- **Lenses:** L1, L6  
- **Unit:** UI-CSS-CONTROLS  
- **Location:** `lsp-dplanner-controls.css:127-129`  
- **Root cause:** `.gas-card-grid .gas-f-num` locks width to `4.25rem` (~68px) with no minimum height; combined field padding yields ~35px tall inputs on mobile.  
- **Failure path:** Navigate to TEC planner → inspect `#cylBot_size` at 375px width → `getBoundingClientRect()` ≈ 68×35px.  
- **Impact:** Cylinder size/pressure edits on narrow mobile fall below common 44×44px touch-target guidance; adjacent flex-wrapped controls increase mis-tap risk during gas setup.  
- **Evidence:** Playwright computed geometry on `#cylBot_size`; imperial value `1766` fits without scroll clipping (`scrollWidth` 66 ≤ `clientWidth` 66) — clipping is not the defect, target size is.  
- **Regression ID:** `SL-C06-GAS-NUM-TOUCH-TARGET`  
- **Status:** OPEN

### SL-C06-L-01: Obsolete `.si-inner` surface-interval rules

- **Severity:** LOW  
- **Lenses:** L3, L4  
- **Unit:** UI-CSS-CONTROLS  
- **Location:** `lsp-dplanner-controls.css:488-499`  
- **Root cause:** `buildDiveBlocks()` still emits `.si-inner`, but `#diveBlocks` was removed from assembled markup; `setDiveCount()` now calls `buildUnifiedPlan()` which renders slider-based SI connectors without `.si-inner`.  
- **Failure path:** Multi Dive tab → `setDiveCount(3)` → `document.querySelectorAll('.si-inner').length === 0`.  
- **Impact:** Dead CSS; SI styling contract is split between obsolete numeric rules and inline slider layout.  
- **Regression ID:** `SL-C06-CSS-DEAD-SI-INNER`  
- **Status:** OPEN

### SL-C06-L-02: Obsolete `.t-col` rules

- **Severity:** LOW  
- **Lenses:** L4  
- **Unit:** UI-CSS-CONTROLS  
- **Location:** `lsp-dplanner-controls.css:526`  
- **Root cause:** No canonical markup or runtime generator emits `.t-col`.  
- **Failure path:** N/A — selector never matches.  
- **Impact:** Dead CSS.  
- **Regression ID:** `SL-C06-CSS-DEAD-T-COL`  
- **Status:** OPEN

### SL-C06-L-03: `.btn-calc` alias unused in live shell

- **Severity:** LOW  
- **Lenses:** L4, L5  
- **Unit:** UI-CSS-CONTROLS  
- **Location:** `lsp-dplanner-controls.css:262-282`; `index.html:9287-9293`  
- **Root cause:** Assembled `index.html` uses `.gen-btn` only; `disableDuringCalc` toggles `.btn-calc` but `document.querySelectorAll('.btn-calc').length === 0` at runtime. Legacy `ui/markup-planner.html` still pairs both classes but is not in the live shell boundary.  
- **Failure path:** Schedule calculation busy state → `.btn-calc:disabled` rules never apply; only elements that also carry `.gen-btn` receive disabled styling via the shared selector list.  
- **Impact:** Misleading disable contract; dead half of paired selector unless markup is regenerated from obsolete partial.  
- **Regression ID:** `SL-C06-CSS-DEAD-BTN-CALC`  
- **Status:** OPEN

### SL-C06-L-04: No invalid-state styling on shared field controls

- **Severity:** LOW  
- **Lenses:** L2, L6  
- **Unit:** UI-CSS-CONTROLS  
- **Location:** `lsp-dplanner-controls.css:109-152`  
- **Root cause:** `.field input` / `.field select` style default, focus, and disabled states but omit `:invalid`, `:user-invalid`, or warning classes for HTML5 constraint failures.  
- **Failure path:** Set `#cylBot_size` below `min` → browser validity false → border remains default `var(--border)` without distinct error chrome.  
- **Impact:** Invalid gas/cylinder values may look editable/normal until engine validation or alerts appear later in the flow.  
- **Regression ID:** `SL-C06-FIELD-INVALID-STATE`  
- **Status:** OPEN

### SL-C06-L-05: Motion transitions ignore `prefers-reduced-motion`

- **Severity:** LOW  
- **Lenses:** L1, L2  
- **Unit:** UI-CSS-CONTROLS  
- **Location:** `lsp-dplanner-controls.css:31,67,118,271,296,454`  
- **Root cause:** `.seg-btn`, `.option-pill-thumb`, `.field input`, `.gen-btn`, `.stat`, and `.bar-fill` animate without `@media (prefers-reduced-motion: reduce)` overrides.  
- **Failure path:** OS reduced-motion preference → controls still apply `transition`/`transform` on hover/active/pill slide.  
- **Impact:** Vestibular/accessibility preference not honored on control affordances.  
- **Regression ID:** `SL-C06-REDUCED-MOTION`  
- **Status:** OPEN

## Lens summary

Full L1–L7 notes are in `cycle-06-record.json` for both bounded parts.

**Highlights:** Numeric layout for gas cards, pill thumb `translateX(100%)`, and android-select sheet `min(70vh, 520px)` math are internally consistent. Cascade order is foundation → modes → controls → results; light-theme emergency `.alert.deco` / `.narcotic-warn` overrides match results-panel scoping. `.option-pill-toggle:focus-visible` and `.gen-btn` default browser focus remain usable. Primary defects are missing `seg-btn` focus-visible, undersized gas numerics on mobile, and several dead or incomplete selector contracts (`.si-inner`, `.t-col`, standalone `.btn-calc`).

**L7:** `SUITE-UI-STRUCTURE` (`UI-EXTRACT-CSS`, `UI-CSS-LINK-ORDER`) and `EXT-03`/`EXT-06`/`COV-01` validate extraction and link order only. `dev/ui_css_regression.py` targets Cycle 05 foundation/modes sheets, not controls computed behavior. No browser regression asserts `seg-btn` focus, gas touch geometry, or invalid field chrome.

## Baseline

| Command | Result |
|---------|--------|
| `python -m tools.audit check --profile static` | PASS (11 checks, 4 suites) |
| `git status --short` (pre-audit) | clean except new record |

**Integration base:** `7cd58978d7b151c74e99cd65b79148d09b223658` (= `origin/dev` at plan time).
