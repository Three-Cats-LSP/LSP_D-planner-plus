# Seven-Lens Audit — Cycle 04 (UI-MARKUP-TOOLS + UI-MARKUP-MODALS)

**Branch:** `cursor/seven-lens-cycle-04-tools-modals`  
**Baseline:** `42224fa`  
**Schema:** v2  
**Auditor:** Cursor GPT-5.5 Medium (`cursor/seven-lens-cycle-04-tools-audit`, `cursor/seven-lens-cycle-04-modals-audit`)

## Scope

| Part | Unit | Lines | Session |
|------|------|------:|---------|
| P01 | `UI-MARKUP-TOOLS` | 1–271 | `cursor/seven-lens-cycle-04-tools-audit` |
| P02 | `UI-MARKUP-MODALS` | 1–341 | `cursor/seven-lens-cycle-04-modals-audit` |

**Callers traced:** `gas-table-core.js` (`calcEND_tool`, `renderEADTable`, `renderGasTable`), `surf-interval-core.js` (`calcSurfInt`), `index.html` (`setUnits`, `domDepthToM`), `settings-core.js` (modal Escape/back handling).

## Findings (OPEN)

### SL-C04-H-01: END depth slider unit tuple incomplete

- **Severity:** HIGH  
- **Lenses:** L1, L3, L4, L6, L7  
- **Location:** `ui/markup-tools.html:52-60`; `gas-table-core.js:calcEND_tool`; `index.html:setUnits`  
- **Root cause:** `endDepth` is omitted from `convertNumericInput` and `stampDepthCanonicalBeforeConvert`. `setUnits` relabels display only. `calcEND_tool` divides raw slider by 3.28084 in imperial without a canonical `data-depthM` stamp.  
- **Failure path:** Metric 30 m → switch imperial → display shows 30 ft, consumer receives ~9.14 m ATA → wrong END, MOD, and narcosis risk.  
- **Impact:** Incorrect narcotic/MOD guidance in the END calculator.  
- **Regression ID:** `SL-C04-END-DEPTH-UNITS`  
- **Trace ID:** `SL-C04-END-PHYSICAL-TRACE`

### SL-C04-M-01: Surface-interval depth sliders use conflicting unit models

- **Severity:** MEDIUM  
- **Lenses:** L1, L3, L4, L7  
- **Location:** `ui/markup-tools.html:164-191`; `surf-interval-core.js:calcSurfInt`; `index.html:setUnits`  
- **Root cause:** `siD1Depth` / `siD2Depth` not converted on unit switch. `calcSurfInt` passes raw slider values to `computeSurfIntervalCore` as metres while `fmtD` multiplies by 3.28084 for imperial labels on input — but `setUnits` relabels the raw value as feet without conversion. Slider tick labels remain metric (`30m`).  
- **Failure path:** Imperial mode → slider 30 → `setUnits` shows 30 ft → engine uses 30 m → minimum SI matches a 30 m dive, not 30 ft.  
- **Impact:** Wrong surface-interval recommendations in imperial mode.  
- **Regression ID:** `SL-C04-SI-DEPTH-UNITS`  
- **Trace ID:** `SL-C04-SI-PHYSICAL-TRACE`

### SL-C04-M-02: Confirm modal lacks backdrop dismiss contract

- **Severity:** MEDIUM  
- **Lenses:** L2, L6  
- **Location:** `ui/markup-modals.html:100-108`; `index.html:showConfirm`  
- **Root cause:** `gasRuleModal`, `tipModal`, and preset modals dismiss on overlay click; `confirmModal` does not, though it guards destructive reset via `showConfirm`.  
- **Failure path:** User opens reset confirmation → taps outside dialog → modal stays open with no explicit cancel affordance beyond buttons.  
- **Impact:** Inconsistent modal UX; accidental focus trap on destructive flows.  
- **Regression ID:** `SL-C04-CONFIRM-BACKDROP`

### SL-C04-L-01: END results label typo

- **Severity:** LOW  
- **Location:** `ui/markup-tools.html:95`  
- **Root cause:** Stat label reads `Narcotic ppressure`.  
- **Recommendation:** Correct to `Narcotic pressure`.

### SL-C04-L-02: EAD table copy hardcodes metric depths

- **Severity:** LOW  
- **Location:** `ui/markup-tools.html:121`  
- **Root cause:** Intro text says `12–38 m` while `renderEADTable()` honours display units.  
- **Recommendation:** Use unit-neutral wording or dynamic label sync.

## Lens summary

Both parts reviewed L1–L7 with browser trace specs declared for depth-unit findings. `renderEADTable` / `renderGasTable` correctly honour `units` for output; depth-input defects are in END and surface-interval sliders only. Modals markup is structurally sound; confirm-modal backdrop inconsistency is the primary L2 finding.
