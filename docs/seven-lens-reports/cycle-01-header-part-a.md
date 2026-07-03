# Seven-Lens Audit — Cycle 01 Part A (UI-MARKUP-HEADER)

**Branch:** `cursor/seven-lens-cycle-01-header`  
**Baseline commit:** `19d56f3`  
**Unit:** `UI-MARKUP-HEADER`  
**Boundary:** `ui/markup-header.html` lines **1–214** (part A; full file 847 lines — parts B–D pending)  
**Reviewer:** Cursor GPT-5.5 Medium  
**Static gate (baseline):** PASS (6 checks, 4 suites; workspace tracked-status note from staged workflow doc)

## Scope split

Cycle 1 exceeds the 600-line manual session limit. This report covers:

| Part | Lines | Status |
|------|------:|--------|
| A — scripts, header, nav, planPanel inputs | 1–214 | **Reviewed this session** |
| B — resultsPanel shell | 215–415 | Pending |
| C — settingsPageWrap | 416–481 | Pending |
| D — legacy-panels + deco card tail | 482–847 | Pending |

## Lens notes (Part A)

### L1 — Arithmetic / physics
No calculations in markup. Default depth 40 m / BT 30 min match factory defaults. Trimix REC fields use `min`/`max` consistent with `validateDomDecoGases` (O₂ ≤ 40% on bottom trimix).

### L2 — Control flow
Steppers call `stepDepthBt`; generate calls `runGenerateSchedule`; nav calls `setMainNav` / `switchTool`. VPM mode toggle calls `toggleVpmMode`. No orphan handlers in scoped region.

### L3 — State / mutation
Canonical tec inputs are `#decoDepth` / `#decoBT`. Legacy mirrors `#depth` / `#bt` and stepper labels must stay aligned via `_syncDepthBtSteppers`.

### L4 — API contracts
**Finding:** preset load and settings restore updated `decoDepth` without syncing mirrors (see below). Script extract markers match `tools/extract_ui_cores.py` order.

### L5 — Canonical / generated parity
Edited `ui/markup-header.html`; ran `python tools/assemble_ui_html.py --assemble` + `--verify` OK.

### L6 — Safety regression
“Planning Aid Only” disclaimer present in header banner. No change to safety copy in this fix pass.

### L7 — Tooling / CI
Added engine regression cases `SL-C01-DEPTH-SYNC` and `SL-C01-PRESET-SYNC`.

---

## Findings

### SL-C01-M-01: Depth/BT mirror drift after preset load and settings restore

- **Severity:** MEDIUM
- **Lens:** L3, L4
- **Unit:** UI-MARKUP-HEADER (+ callers in index.html shell)
- **Location:** `ui/markup-header.html:127-140`, `index.html:loadProfilePreset`, `index.html:_syncUiAfterRestore`
- **Root cause:** `decoDepth` / `decoBT` are canonical; `#depth` / `#bt` and stepper labels are mirrors updated only via `_syncDepthBtSteppers`. `loadProfilePreset` and `_syncUiAfterRestore` set `decoDepth` without calling sync.
- **Failure path:** User loads a saved dive profile → stepper still shows old depth → REC `runPlanner` / export paths reading `#depth` use stale values while schedule uses `decoDepth`.
- **Impact:** Incorrect displayed depth/BT; REC mode and export snippets can disagree with tec schedule inputs.
- **Evidence:** Source trace; engine regression `SL-C01-PRESET-SYNC`.
- **Recommendation:** Call `_syncDepthBtSteppers` after programmatic depth/BT changes; include sync in hidden-field `oninput`.
- **Regression ID:** `SL-C01-DEPTH-SYNC`, `SL-C01-PRESET-SYNC`
- **Status:** CLOSED (fix in this PR)

## Fix summary

1. `ui/markup-header.html` — `decoDepth` / `decoBT` `oninput` calls `_syncDepthBtSteppers()`.
2. `index.html` — `loadProfilePreset` and `_syncUiAfterRestore` call `_syncDepthBtSteppers()`.
3. `dev/engine_regression.py` — behavioral regressions for sync and preset load.

## Verification

- [x] `python -m tools.audit check --profile static` — PASS
- [x] `python -m tools.audit run --profile ci` — PASS (12 suites)
- [x] Fingerprints synced for UI-MARKUP-HEADER, UI-BOOT, UI-SETTINGS, UI-PROFILE-PRESETS, TEST-ENGINE-REGRESSION
