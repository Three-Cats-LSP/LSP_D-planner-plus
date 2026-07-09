# Seven-Lens Audit — Cycle 01 Parts B–D (UI-MARKUP-HEADER)

**Branch:** `cursor/seven-lens-cycle-01-header`  
**Unit:** `UI-MARKUP-HEADER`  
**Boundaries reviewed:**

| Part | Lines | Content |
|------|------:|---------|
| B | 215–415 | `resultsPanel` shell (tabs, profile, graphs, contingency, tissue) |
| C | 416–481 | `settingsPageWrap` (units, water, altitude, acclimatized) |
| D | 482–847 | `toolsPageWrap` mount, `legacy-panels`, deco card tail (`gfPresetsRow`) |

**Reviewer:** Cursor GPT-5.5 Medium  
**Note:** Unit ends at line 847 at the legacy deco-card boundary; advanced-settings continuation lives in `UI-MARKUP-PLANNER` (cycle 2).

## Lens notes (Parts B–D)

### L1 — Arithmetic / physics
No calculations in markup. Settings tips document barometric formula and water density constants consistent with `settings-core.js`. Contingency depth buttons store metres internally (`selectContDepth`); imperial labels updated via `syncContDepthLabels` on unit switch.

### L2 — Control flow
Result tabs delegate to `switchResultTab` (lazy-mount surf int, NDL, multi, graphs redraw). Jump buttons (`tissueChartToggleBtn`, `contingencyJumpBtn`) guard on card visibility before tab switch. Legacy panels are relocated at `initV3Layout()` in `planner-shell.js`; markup order is bootstrap input, not runtime layout.

### L3 — State / mutation
`#decoResult`, `#decoTableBody`, `#algorithmSelect`, `#gfPresetSelect` are canonical DOM anchors consumed by results/settings cores. V3 mounts (`gfPresetsMount`, `planPanelTecMount`) receive moved children at init — IDs remain stable post-bootstrap.

### L4 — API contracts
Settings handlers: `setUnits`, `setWaterDensity`/`applyCustomWaterDensity`, `handleAltitudeSelect`/`applyCustomAltitude`, `setAltitude`. Contingency buttons call `selectContBT`/`selectContDepth`/`calcContingency`. Export actions call `copyDiveProfile`, `exportTXT`, PDF dialogs — all traced to `export-core.js`.

### L5 — Canonical / generated parity
Edits in `ui/markup-header.html`; `python tools/assemble_ui_html.py --assemble` + `--verify` OK.

### L6 — Safety regression
`gasWarningBanner` uses `role="alert"`. Planning-aid disclaimer unchanged. GF curve stat placeholders should match factory `mGF` default (20/85) before first `drawGFCurve` call.

### L7 — Tooling / CI
Part A regressions `SL-C01-DEPTH-SYNC` / `SL-C01-PRESET-SYNC` remain valid. No new engine cases required for markup-only altitude handler parity.

---

## Findings

### SL-C01-M-02: Custom altitude input recalc only on blur

- **Severity:** MEDIUM
- **Lens:** L3, L4
- **Location:** `ui/markup-header.html:462` (`#altitudeCustomInput`)
- **Root cause:** Custom water density input uses both `oninput` and `onchange`; custom altitude used `onchange` only. Typed values did not call `setAltitude()` until blur.
- **Failure path:** User selects Custom altitude, types a value, immediately generates schedule — deco still uses previous altitude until field loses focus.
- **Impact:** Stale altitude correction on deco/NDL until blur; inconsistent with water-custom UX.
- **Recommendation:** Add `oninput="applyCustomAltitude()"` to match water row.
- **Status:** CLOSED (fix in this PR)

### SL-C01-L-01: GF curve stat placeholders show 30/70 instead of 20/85

- **Severity:** LOW
- **Lens:** L6
- **Location:** `ui/markup-header.html:312-313` (`#gfCurveGFL`, `#gfCurveGFH`)
- **Root cause:** Static HTML placeholders did not match `mGF` factory default `{ low: 20, high: 85 }` in `settings-core.js`.
- **Impact:** Brief misleading GF labels if user opens Graphs tab before first `drawGFCurve()`; corrected once chart renders.
- **Recommendation:** Set placeholders to 20/85.
- **Status:** CLOSED (fix in this PR)

## Fix summary

1. `#altitudeCustomInput` — added `oninput="applyCustomAltitude()"`.
2. `#gfCurveGFL` / `#gfCurveGFH` — placeholder text 20 / 85.

## Verification

| Gate | Result |
|------|--------|
| `python tools/assemble_ui_html.py --verify` | PASS |
| `python -m tools.audit check --profile static` | PASS |
| `python -m tools.audit run --profile ci` | PASS (12/12 suites) |
