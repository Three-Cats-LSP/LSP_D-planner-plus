# Seven-Lens Audit — Cycle 02 (UI-MARKUP-PLANNER)

**Branch:** `cursor/seven-lens-cycle-02-planner`  
**Baseline commit:** `3731e560`  
**Unit:** `UI-MARKUP-PLANNER`  
**Boundary:** `ui/markup-planner.html` lines 1–493 (493 lines, single session)  
**Auditor:** Cursor GPT-5.5 Medium (`cursor/seven-lens-cycle-02-planner-audit`)  
**Verifier:** Cursor GPT-5.5 Medium (`cursor/seven-lens-cycle-02-planner-verify`)

## Findings

### SL-C02-M-01: Min deco profile always uses metric stop matching in imperial mode

- **Severity:** MEDIUM
- **Lens:** L3, L4, L6
- **Location:** `ui/markup-planner.html:76-90`; callers `index.html:getVpmMinDecoSettingsFromDom`, `index.html:buildZhlScheduleParamsFromDom`
- **Root cause:** `isMetric` read phantom `#unitSel` (never rendered). Expression `null?.value !== 'imperial'` is always `true`.
- **Failure path:** Enable Min Deco profile, switch to imperial, generate schedule. `enforceMinDecoProfile` matches 9 m / 6 m stops instead of 30 ft / 20 ft equivalents.
- **Impact:** Imperial divers get wrong minimum stop enforcement at shallow stops.
- **Regression ID:** `SL-C02-MIN-DECO-UNITS`
- **Status:** CLOSED — use `units !== 'imperial'`

### SL-C02-M-02: Travel gas manual depth max stays metric on relabel-only unit restore

- **Severity:** MEDIUM
- **Lens:** L1, L3, L4
- **Location:** `ui/markup-planner.html:337-339`; `gas-cards-core.js`, `index.html:setUnits`
- **Root cause:** Markup `max="100"` (metres). `convertNumericInput` only updates `max` during active unit conversion, not `relabelOnly` restores or manual-mode display.
- **Failure path:** Imperial mode + manual travel switch → enter 165 ft (valid 50 m equivalent). Browser rejects because `max` remains 100.
- **Impact:** Imperial manual travel switch depth capped at ~30 m regardless of label.
- **Regression ID:** `SL-C02-TRAVEL-DEPTH-CONSTRAINTS`
- **Status:** CLOSED — `syncTravelGasManualDepthConstraints()` in `gas-cards-core.js`

## Verification

| Gate | Result |
|------|--------|
| `python dev/engine_regression.py` | PASS 161/161 |
| `python -m tools.audit check --profile static` | PASS |
| `python -m tools.audit run --profile ci` | PASS (12/12 suites) |

Independent verification: `docs/seven-lens-reports/cycle-02-independent-verification.md`
