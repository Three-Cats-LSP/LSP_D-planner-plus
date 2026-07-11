# V4 Full R-cycle FIXER report

Source: `cursor_full_R_audit.md`  
Branch: `main`  
Date: 2026-07-11

## Verdict

Confirmed HIGH release blockers and targeted MEDIUM/LOW findings are fixed with focused regressions. Decompression math unchanged.

---

## Finding status

### HIGH

| ID | Status | Notes |
|---|---|---|
| V4-FULL-R20_M_01 | **Fixed** | Messenger deco stops use `readExportScheduleCells` (`data-label` Run/Mix). |
| V4-FULL-R20_M_02 | **Fixed** | Messenger bottom rows same helper. |
| V4-FULL-R20_M_03 | **Fixed** | Contingency messenger same helper. |
| V4-FULL-R20_M_04 | **Fixed** | Switch rows read Mix via `data-label`; gas present on `>> mix @ depth`. |
| V4-FULL-R15_M_01 | **Fixed** | Results SI (`mainSi*`/`recSi*`) stamp `data-si-metric` + `dataset.depthM`; imperial display converts correctly. |

### MEDIUM

| ID | Status | Notes |
|---|---|---|
| V4-FULL-R20_M_05 | **Fixed** | PDF uses shared `applyVpmPlanSummaryFallback(...)`. |
| V4-FULL-R20_M_06 | **Fixed** | Text/PDF/UI adequacy via `gasPlanAdequacyStatus` + `GP_ONEWAY_MARGIN`. |
| V4-FULL-R20_M_07 | **Fixed** | PDF CNS styling uses `exportCnsHighlightTier` / `data-cns-tier` (no CSS color sniff). |
| V4-FULL-R35_M_01 | **Fixed** | Bühlmann REC beyond-MOD / NDL-no-deco uses same `rec-block-card` layout as PADI. |
| V4-FULL-AUDIT_M_01 | **Fixed** | R-cycle acceptance / line budgets refreshed. |
| V4-FULL-AUDIT_M_02 | **Fixed** | `UI-CSS-MOBILE-SHELL` assigned to **R43**. |
| V4-FULL-AUDIT_M_03 | **Fixed** | `APP-VERSION` + `APP-VERSION-JSON` attached to **R33**. |

### LOW

| ID | Status | Notes |
|---|---|---|
| V4-FULL-R07_L_01 | **Fixed** | Removed dead `injectTtsCells`. |
| V4-FULL-R20_L_01 | **Fixed** | Empty TTS column leftovers cleaned with injector removal / tip copy. |
| V4-FULL-R20_L_02 | **Fixed** | Shared `exportShortMix` for export/messenger paths. |
| V4-FULL-R20_L_03 | **Fixed** | Slate TRT uses the plan summary / VPM fallback path and no longer substitutes bottom time when RT is missing. |
| V4-FULL-R20_L_04 | **Fixed** | Text gas SAC uses `lspSacUnit()`. |
| V4-FULL-R20_L_05 | **Fixed** | Removed dead `if(false){…}` emergency PDF block. |
| V4-FULL-R20_L_06 | **Fixed** | Slate PDF section page start is conditional, avoiding an unconditional extra page break. |
| V4-FULL-R20_L_07 | **False positive** | PDF phase-only Mix colors match current web schedule contract. |
| V4-FULL-R25_L_01 | **Fixed** | Android A2HS dismiss persists (`lspAndroidA2hsDismissed`). |
| V4-FULL-R26_L_01 | **Fixed** | Android select picker: `aria-expanded` / `aria-controls`. |
| V4-FULL-R29_L_01 | **Fixed** | GF curve waypoint labels use unit-aware `_gfDu`. |
| V4-FULL-R34_L_01 | **Fixed** | Algorithm / plan tip TTS wording softened (export-only note). |
| V4-FULL-R35_L_01 | **Fixed** | `.rec-block-card` CSS added. |
| V4-FULL-R37_L_01 | **Fixed** | Consumption help TTS copy updated. |
| V4-FULL-R41_L_01 | **Fixed** | Orphan `.col-tts` removed. |
| V4-FULL-R41_L_02 | **Fixed** | Gas-supply middle tier now uses product wording `low` while preserving the orange visual tier. |
| V4-FULL-R42_L_01 | **Fixed** | `PLAN_INFO_TIP` documents TTS as export-only (also repaired a corrupted string that blocked engine boot). |
| V4-FULL-R39_L_01 | **False positive** | Neutral Mix coloring is intentional phase-column contract. |

---

## Files changed

- `export-core.js` — label-based schedule reads; VPM fallback; CNS tiers; gas status; `exportShortMix`; dead block removed; slate stop rows use helpers; TRT fallback and slate PDF page-start cleanup
- `surf-interval-core.js` — metric depth stamp for results SI
- `results-render-core.js` — `data-cns-tier`; gas low-tier naming
- `gas-plan-core.js` — `gasPlanAdequacyStatus`
- `schedule-runner-core.js` — REC block-card parity; remove `injectTtsCells`
- `lsp-dplanner-results.css` — `.rec-block-card`; drop `.col-tts`; `.gas-usage-card--low`
- `index.html` — A2HS persistence; tip copy repair
- `android-select-picker.js` — a11y attrs
- `gf-curve-core.js` — imperial depth labels
- `ui/markup-header.html`, `ui/markup-consumption.html` — TTS help copy
- `docs/audit-units.json`, `docs/audit-coverage.md`, `docs/audit-master-plan.md` — R33/R43 + budgets
- `docs/seven-lens-records/*`, `docs/seven-lens-reports/cycle-07-record.json` — boundary sync after CSS/markup edits
- `tools/test_v4_full_r_fixes.py` — static regression
- `tools/test_v4_cursor_full_7_fixes.py` — tip assertion update
- `dev/v4_full_r_export_si_regression.py` — Playwright behavioral coverage

---

## Regressions / tests added

**Static** (`tools/test_v4_full_r_fixes.py`):
- messenger/export no fragile Run/Mix indexes
- VPM PDF fallback + CNS tier helpers
- gas adequacy helper shared
- slate TRT does not fall back to bottom time
- slate PDF page break is conditional
- gas low-tier wording replaces `caution`
- SI metric stamp
- REC block-card + no `injectTtsCells`
- A2HS / select a11y
- `.rec-block-card` CSS / no `.col-tts`

**Behavioral** (`dev/v4_full_r_export_si_regression.py`):
- messenger Stop/Bottom/Switch Run↔Mix correctness
- contingency messenger Run/Mix
- SI imperial depth (`40 m` → `131 ft`, `dataset.depthM=40`)
- VPM fallback fill when totals are `-`
- REC PADI NDL block + Bühlmann beyond-MOD block cards

---

## Commands run (results)

| Command | Result |
|---|---|
| `python tools/test_v4_full_r_fixes.py` | PASS |
| `python dev/v4_full_r_export_si_regression.py` | PASS |
| `python tools/assemble_ui_html.py --verify` | PASS |
| `python dev/ui_visual_contract_regression.py` | PASS |
| `python dev/engine_regression.py` | PASS |
| `node dev/vpm_direct_regression.js` | PASS |
| `python tools/audit_coverage.py --refresh-fingerprints` | PASS |
| `python tools/audit_coverage.py --write-docs` | PASS |
| `python tools/seven_lens_protocol.py sync-reviewed-boundaries --write` | PASS (3 records) |
| `python tools/seven_lens_protocol.py check-all --require-artifacts` | PASS |
| `python -m tools.audit check --profile static` | PASS |
| `python -m tools.audit run --profile ci` | Suites PASS; overall FAIL only for dirty workspace (`tracked status lines changed`) before commit |
| `python -m tools.audit run --profile release` | PASS (clean tree after commit) |
| `git push origin main` | PASS (`80d9f9f`) |
| GitHub Actions (`main` @ `80d9f9f`) | All success: CI, Build Offline ZIP, Deploy Pages, Android APK, Notify Site |

---

## Remaining risks

- Slate TRT←BT fallback and slate page-break cosmetic items remain deferred.
- Bühlmann REC still shows a deco-required card when NDL is exceeded **with** a ceiling (by design); only beyond-MOD / no-ceiling NDL cases hard-block like PADI.
- New behavioral suite is local/dev; wire into CI suite catalog in a follow-up if desired.
