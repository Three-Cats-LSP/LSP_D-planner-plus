# Seven-Lens Audit — Cycle 03 (UI-MARKUP-CONSUMPTION)

**Branch:** `cursor/seven-lens-cycle-03-consumption`  
**Baseline commit:** `6e987af`  
**Unit:** `UI-MARKUP-CONSUMPTION`  
**Boundary:** `ui/markup-consumption.html` lines 1–381 (381 lines, single session)  
**Auditor:** Cursor GPT-5.5 Medium (`cursor/seven-lens-cycle-03-consumption-audit`)

## Scope

CNS toxicity panel, MOD / Best Mix tools, unit converter (pressure, volume, depth, temperature, weight), and knowledge-base tail. Callers in `index.html` (`calcCNS`, `calcBestMix`, `calcMODTool`, `convertDepth`, `setUnits`).

## Findings

### SL-C03-H-01: Best Mix depth slider uses metres in physics while imperial mode labels feet

- **Severity:** HIGH
- **Lens:** L1, L3, L4, L6
- **Location:** `ui/markup-consumption.html:196-201`; `index.html:calcBestMix`, `index.html:setUnits` (relabel-only)
- **Root cause:** `#bestMixDepth` slider value is always interpreted as metres in `calcBestMix` (`depth * BAR_PER_METRE`). `setUnits` relabels the display suffix to `ft` without converting value or min/max.
- **Failure path:** Switch to imperial → slider shows `30 ft` → Best Mix calculates as 30 m (~98 ft actual) → wrong O₂% and ppO₂.
- **Impact:** Imperial divers get materially wrong best-mix recommendations and reference-table highlight.
- **Regression ID:** `SL-C03-BEST-MIX-DEPTH-UNITS`
- **Status:** OPEN

### SL-C03-M-01: CNS depth input never follows display units

- **Severity:** MEDIUM
- **Lens:** L1, L3, L4, L6
- **Location:** `ui/markup-consumption.html:54-55`; `index.html:calcCNS`, `index.html:setUnits`
- **Root cause:** Markup label hardcoded `Depth (m)`; `max=60`; `setUnits` does not convert `#cnsDepth`. `calcCNS` always treats value as metres.
- **Failure path:** Imperial mode → user enters 100 (expecting ft) or keeps 30 while label still says m → ppO₂/CNS% wrong by ~3×.
- **Impact:** CNS tracker and OTU estimates wrong for imperial users.
- **Regression ID:** `SL-C03-CNS-DEPTH-UNITS`
- **Status:** OPEN

### SL-C03-L-01: Volume converter AL80 reference conflates tank name with water volume

- **Severity:** LOW
- **Lens:** L1, L6
- **Location:** `ui/markup-consumption.html:284`
- **Root cause:** Reference text `AL80 = 11.1L (77 ft³)` pairs litre water volume with 77 (naming cu ft), not converted volume (~0.39 ft³).
- **Failure path:** User reads reference while planning gas.
- **Impact:** Misleading education copy only; converter math is correct.
- **Regression ID:** (markup copy fix only)
- **Status:** OPEN
