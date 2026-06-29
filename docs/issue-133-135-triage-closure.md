# Issues #133–#135 — Triage & closure (structured environment)

**Verified at:** `fcfb6c4` (v2.53.04)  
**Method:** Re-run `audit.py` issue-specific gates + `dev/engine_regression.py` sections `issue133`, `issue134`, `issue135`. Overlap with #137/#138 confirmed fixed by the same gates where applicable.

## Summary

| Issue | Audit | Findings | Status | Primary verification |
|-------|-------|----------|--------|----------------------|
| [#133](https://github.com/Three-Cats-LSP/LSP_D-planner-plus/issues/133) | #128 | 25 (4C/5H/8M/8L) | **CLOSED** | `audit.py` lines ~6820–6911; `engine_regression` `issue133` |
| [#134](https://github.com/Three-Cats-LSP/LSP_D-planner-plus/issues/134) | #129 | 19 (1C/4H/7M/7L) | **CLOSED** | `audit.py` lines ~6913–6983; `engine_regression` `issue134` |
| [#135](https://github.com/Three-Cats-LSP/LSP_D-planner-plus/issues/135) | #130 | 21 (10H/10M/1L) | **CLOSED** | `audit.py` lines ~6985–7097; `engine_regression` `issue135` |
| [#136](https://github.com/Three-Cats-LSP/LSP_D-planner-plus/issues/136) | — | extractor hardening | **CLOSED** | `audit.py` marker-based `extract_ui_cores.py` gates |

**Gate results (2026-06-29):** `audit.py` **1167/1167** · `engine_regression.py` **93/93**

---

## #133 (Audit #128) — all 25 fixed

| ID | Fix evidence |
|----|----------------|
| C-1 | `getActiveGas` wrapper arg order matches bundle (`audit.py` issue #133 C-1) |
| C-2 | `validateHypoxicDecoGas` rejects O₂&lt;18 for all gases incl. trimix; CCR exempt on bottom (`validateHypoxicDecoGas` + #137 M-17) |
| C-3 | VPM `cloneVPMState` + `restoreInterLevelDerivedState` before main deco |
| C-4 | `isShallowGradientOn()` reads select `value === 'on'` |
| H-1 | `gfAtDepth` returns `gfH` when `firstStopDepth <= 0` |
| H-2 | `APP_VERSION` bumped (2.53.04) |
| H-3 | `check_engine_parity.py` template-depth + api block + use strict strip |
| H-4 | Worker `onmessage` error delegates to `handleWorkerFailure` |
| H-5 | `engine_regression` `issue133` section |
| M-1 | (C-3 restore) inter-level radii not carried into main deco |
| M-2 | `saturateLinearCCR` setpoint at deep endpoint (#137 M-18) |
| M-3 | `depthAtSetpointCrossing` finite `surfP` guard (#137 L-17) |
| M-4 | `_syncUiAfterRestore` refreshes SI sliders |
| M-5 | `setWaterDensity` before dependent UI sync |
| M-6 | ppO₂ `ERR` path styling in deco table |
| M-7 | `perDiveOtu` carry subtract only on `fromPlan` path |
| M-8 | `runUnifiedPlan` guards unset `mGF` |
| L-1 | Bottom gas `validateHypoxicDecoGas` (#138 H-1 superseded) |
| L-2 | `n2FracFromPercentages` returns null when N₂ invalid (#138 L-9) |
| L-3 | `injectStop` straddle `sToM <= targetDepthM` |
| L-4 | `siGfLow` in `DECO_FIELDS` |
| L-5 | `_restoreInProgress` cleared after change dispatch (#138 M-12) |
| L-6–L-8 | Parity tool + `normalizeCCRSettings` docs |

---

## #134 (Audit #129) — all 19 fixed

| ID | Fix evidence |
|----|----------------|
| C-1 | CCR/pSCR bottom hypoxic diluent exempt; OC deco gases still validated |
| H-1 | Same as #133 H-1 (`gfAtDepth`) |
| H-2 | `injectStop` insertion scan uses `<= targetDepthM` |
| H-3 | `shallowGradient` option `value="on"` aligned with helper |
| H-4 | Worker timeout settles pending when worker null |
| M-1/M-2 | `runUnifiedPlan` uses `ndlClearAtDepth` (GF interpolation + 0.01 m tol) |
| M-3 | Full VPM derived-state snapshot restore |
| M-4 | `appSettings.save` skips during `_restoreInProgress` |
| M-5 | Widget OTU uses `cumulativeOtu` for carry-aware limits |
| M-6 | `resolveGasAtDepth` reverse scan (deepest match) |
| M-7 | `ppO2Check` returns number; index delegate fixed (#135 H-6) |
| L-1–L-7 | Worker bridge hardening + parity `ppO2Check` export + split regression asserts |

---

## #135 (Audit #130) — all 21 fixed

| ID | Fix evidence |
|----|----------------|
| H-1 | `runContingencyScenario` returns `ok:false` when schedule empty |
| H-2 | `calcContingency` DOM restore in `try/finally` |
| H-3 | `calcSurfInt` uses bottom gas fN2 |
| H-4 | `saveZhlRepState` persists CNS/OTU (#137 M-1) |
| H-5 | Emergency PDF restore in `finally` |
| H-6 | `ppO2Check` delegate returns numeric ppO₂ |
| H-7 | `buildZhlScheduleParamsFromDom` hypoxic validation (#138 H-1) |
| H-8 | Contingency uses `parseRunMinutes` |
| H-9 | Rec planner MOD uses `ppo2Bottom` (#138 H-5/H-6) |
| H-10 | Worker timeout increments failure counter when worker null |
| M-1–M-10 | VPM NaN gas warning, contingency validation skip, CCR bailout, OTU carry, EAD table, SAC=0, CNS threshold, ppO₂ boundary, narcoticO2 MND |
| L-1–L-11 | siGfLow save, contingency row tags, duplicate gas detection, calcEAD/END, GF curve units, altitude input, OTU/week warning, etc. |

---

## Overlap with #137 / #138

Several #133–#135 items were re-flagged in later audits and fixed again in #137 (`51f95ac`) and #138 (`fcfb6c4`). The structured-environment gates in `audit.py` for issues #133–#138 are the authoritative regression lock for all of them.

---

## Validation commands

```bash
python audit.py
python dev/engine_regression.py
python tools/audit_coverage.py --check
python tools/extract_ui_cores.py
```
