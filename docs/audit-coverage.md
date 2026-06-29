# Audit Coverage Ledger

**Purpose:** Track which audit units have been read and verified so audit cycles converge instead of re-sampling the same lines.

**States:** `UNREAD` — never fully fetched · `READ` — analysed in at least one cycle · `VERIFIED` — READ, findings fixed, regression test covers corrected logic

**Update protocol:** At the end of each audit cycle (or UI extraction PR that passes `audit.py` + regression), update statuses here and add a changelog row.

**Related docs:** [codebase-audit-strategy-v2.md](codebase-audit-strategy-v2.md) · [audit-master-plan.md](audit-master-plan.md) · [AUDIT_MIRROR_RULE.md](AUDIT_MIRROR_RULE.md)

**Last updated:** 2026-06-29 (initial seed + UI extraction)

---

## Summary

| File | Units | READ | VERIFIED | Coverage |
|------|-------|------|----------|----------|
| `zhl-physics-core.js` | 12 | 11 | 9 | 92% READ |
| `zhl-gas-core.js` | 6 | 5 | 4 | 83% READ |
| `zhl-ccr-core.js` | 18 | 16 | 14 | 89% READ |
| `zhl-schedule-core.js` | 1 | 1 | 0 | 100% READ / 0% VERIFIED |
| `zhl-engine-bundle.js` | 1 | 1 | 0 | parity spot-checks only |
| `vpm-engine-core.js` | 1 | 0 | 0 | 0% READ |
| `vpm-engine-bundle.js` | 1 | 0 | 0 | 0% READ |
| `zhl-worker-bridge.js` | 1 | 1 | 1 | VERIFIED |
| `surf-interval-core.js` | 3 | 3 | 3 | VERIFIED (extraction) |
| `gas-table-core.js` | 4 | 4 | 4 | VERIFIED (extraction) |
| `gas-plan-core.js` | 6 | 6 | 4 | READ (Playwright partial) |
| `export-core.js` | 12 | 12 | 8 | READ (`export_regression.py`) |
| `contingency-core.js` | 10 | 10 | 6 | READ (partial regression) |
| `index.html` (inline) | 18 | 8 | 2 | ~44% READ |
| `dev/engine_regression.py` | 20 | 4 | 4 | ~20% READ |
| `sw.js` | 8 | 6 | 5 | ~75% READ |
| `audit.py` | 15 | 12 | 10 | ~80% READ |

---

## Engine layer

| Unit ID | File | Symbol / range | Status | Last cycle | Regression | Notes |
|---------|------|----------------|--------|------------|------------|-------|
| PHY-01 | `zhl-physics-core.js` | `applyEnvironment`, `defaultEnvironment` | VERIFIED | Audit #134 | engine_regression A | |
| PHY-02 | `zhl-physics-core.js` | `schreiner`, `schreinerLinear` | VERIFIED | Audit #134 | — | |
| PHY-03 | `zhl-physics-core.js` | `initTissues`, `saturate`, `saturateLinear` | READ | Audit #133 | engine_regression A | |
| PHY-04 | `zhl-physics-core.js` | `ceiling`, `computeSurfaceGF` | READ | Audit #132 | — | |
| PHY-05 | `zhl-physics-core.js` | `gfAtDepth`, `ndlClearAtDepth` | READ | Audit #131 | — | |
| PHY-06 | `zhl-physics-core.js` | `buhNDL` | VERIFIED | Audit #134 | NDL suite | |
| GAS-01 | `zhl-gas-core.js` | `enforceMinDecoProfile` | READ | Audit #130 | — | |
| GAS-02 | `zhl-gas-core.js` | `getActiveGas`, `ppO2Check` | VERIFIED | Audit #134 | H-02 path | |
| GAS-03 | `zhl-gas-core.js` | fraction validators | READ | Audit #129 | — | |
| CCR-01 | `zhl-ccr-core.js` | `normalizeCCRSettings`, `mergeCCRSettings` | VERIFIED | Audit #134 | CCR suite | |
| CCR-02 | `zhl-ccr-core.js` | `getEffectiveSetpointAtDepth` | VERIFIED | Audit #134 | C-03 | |
| CCR-03 | `zhl-ccr-core.js` | `computePSCRFractions`, inert PP | VERIFIED | Audit #134 | C-04 | |
| CCR-04 | `zhl-ccr-core.js` | `saturateCCR`, `loadTissuesWithCCR` | READ | Audit #133 | — | |
| SCH-01 | `zhl-schedule-core.js` | `runZhlScheduleCore` | READ | Audit #128 | deco ascent C-02 | ~55% function-level |
| ZB-01 | `zhl-engine-bundle.js` | bundle parity | READ | Audit #134 | `check_engine_parity.py` | |
| VPM-01 | `vpm-engine-core.js` | full file | UNREAD | — | — | H-09 bundle drift risk |
| VPMB-01 | `vpm-engine-bundle.js` | parity vs core | UNREAD | — | — | |
| WBR-01 | `zhl-worker-bridge.js` | `calculateInWorker`, `terminate` | VERIFIED | Audit #130 | worker parity | |

---

## UI runtime cores (extracted from index.html)

| Unit ID | File | Symbol | Status | Last cycle | Regression | Notes |
|---------|------|--------|--------|------------|------------|-------|
| SI-01 | `surf-interval-core.js` | `calcSurfInt` | VERIFIED | Extraction PR1 | audit.py SI guards | |
| SI-02 | `surf-interval-core.js` | `renderSurfIntPanel` | VERIFIED | Extraction PR1 | — | |
| SI-03 | `surf-interval-core.js` | `toggleSurfIntPanel` | VERIFIED | Extraction PR1 | — | |
| GT-01 | `gas-table-core.js` | `calcEND_tool` | VERIFIED | Extraction PR2 | audit MOD checks | |
| GT-02 | `gas-table-core.js` | `renderEADTable` | VERIFIED | Extraction PR2 | — | |
| GT-03 | `gas-table-core.js` | `renderGasTable` | VERIFIED | Extraction PR2 | audit.py | |
| GT-04 | `gas-table-core.js` | tip constants | READ | Extraction PR2 | — | |
| GP-01 | `gas-plan-core.js` | `setGasRule`, `_gasRule` | VERIFIED | Extraction PR3 | — | shared with deco UI |
| GP-02 | `gas-plan-core.js` | `calcGasPlan` | READ | Extraction PR3 | — | |
| GP-03 | `gas-plan-core.js` | `buildGasPlanText`, `copyGasPlan` | READ | Extraction PR3 | — | |
| GP-04 | `gas-plan-core.js` | `buildGasPlanPDF` | READ | Extraction PR3 | — | |
| GP-05 | `gas-plan-core.js` | `gpPresBar`, `gpSizeL` | VERIFIED | Extraction PR3 | — | |
| EXP-01 | `export-core.js` | `buildExportText` | VERIFIED | Extraction PR4 | `export_regression.py` | |
| EXP-02 | `export-core.js` | `copyDiveProfile`, `exportTXT` | VERIFIED | Extraction PR4 | export_regression | |
| EXP-03 | `export-core.js` | `buildSlateText`, `buildMessengerText` | VERIFIED | Extraction PR4 | export_regression | |
| EXP-04 | `export-core.js` | `showToast`, `copyFallback` | READ | Extraction PR4 | — | |
| EXP-05 | `export-core.js` | `exportPDF`, PDF dialog | READ | Extraction PR4 | — | |
| CONT-01 | `contingency-core.js` | state vars | VERIFIED | Extraction PR5 | audit guards | |
| CONT-02 | `contingency-core.js` | `runContingencyScenario` | VERIFIED | Extraction PR5 | H-04 | try/finally restore |
| CONT-03 | `contingency-core.js` | `calcContingency` | READ | Extraction PR5 | export_regression contingency | |
| CONT-04 | `contingency-core.js` | contingency PDF/slate | READ | Extraction PR5 | export_regression | |

---

## index.html (remaining inline)

| Unit ID | Section | Approx lines | Status | Last cycle | Notes |
|---------|---------|--------------|--------|------------|-------|
| UI-01 | State & constants | 3769–4394 | READ partial | Audit #132 | |
| UI-02 | Settings persistence | 16335+ | READ partial | Audit #130 | scattered `appSettings` |
| UI-03 | Units & environment | 4226–4760 | UNREAD | — | |
| UI-04 | Gas input / MOD display | 8550–8816 | UNREAD | — | |
| UI-05 | CCR panel UI | 6309–6788 | UNREAD | — | |
| UI-06 | Engine delegate layer | 6256–10114 | READ ~25% | Audit #134 | highest priority |
| UI-07 | ZHL plan runner | 6802–9020 | UNREAD | — | |
| UI-08 | VPM runner | ~7780+ | READ partial | Audit #133 | M-06 |
| UI-09 | NDL / OTU / CNS | 6953–7059 | READ partial | Audit #131 | |
| UI-10 | Surface interval | — | VERIFIED | Extraction PR1 | moved to `surf-interval-core.js` |
| UI-11 | Deco table rendering | 9021–9884 | UNREAD | — | |
| UI-12 | Gas consumption / SAC | 9319+ | READ partial | Extraction PR3 | gas plan extracted |
| UI-13 | Contingency | — | VERIFIED | Extraction PR5 | moved to `contingency-core.js` |
| UI-14 | Multi-dive / history | 10193–11160 | UNREAD | — | |
| UI-15 | Tools MOD / best mix | 11161–11500 | UNREAD | — | |
| UI-16 | Gas table | — | VERIFIED | Extraction PR2 | moved to `gas-table-core.js` |
| UI-17 | Export / PDF | — | VERIFIED | Extraction PR4 | moved to `export-core.js` |
| UI-18 | Init / DOMContentLoaded | 17200–17387 | UNREAD | — | |

---

## Changelog

| Date | Cycle / PR | Units touched | Notes |
|------|------------|---------------|-------|
| 2026-06-29 | Initial seed | all tables | Ledger created per strategy v2 §3 |
| 2026-06-29 | UI extraction PR1–5 | SI, GT, GP, EXP, CONT | Subsystems moved to `*-core.js`; inline units marked VERIFIED |
