# LSP D-Planner+CCR — Errors & Bugs Report v22

**App version:** v2.30.30  
**Audit date:** 2026-06-21  
**Previous report:** errors_bugs_report_v21.md (v2.30.28 — BUG-76/BUG-77)  
**Audit tool:** audit.py — 381 checks, 0 failures  
**Scope:** v2.30.28–v2.30.30 fixes (massive suite, CCR C3, ZHL/pSCR OTU/CNS plan walk).

---

## Fix status (v2.30.30)

| Bug | Status | Fix summary |
|-----|--------|-------------|
| BUG-78 | **FIXED** (v2.30.29) | Massive suite: 51× `ZHLEngine not available — iframe not loaded` |
| BUG-79 | **FIXED** (v2.30.29) | CCR C3 RT pin stale (MultiDeco 98 vs LSP engine 83) |
| BUG-80 | **FIXED** (v2.30.29) | ZHL headless OTU/CNS: plan walk uses Bühlmann step `pO2` |
| BUG-81 | **FIXED** (v2.30.30) | Massive main: 109× VPM `(w\|\|E).calculate is not a function` |
| BUG-82 | **FIXED** (v2.30.30) | ZHL pSCR OTU: single-sample bottom integration vs plan walk (tests-pscr Section D/F) |
| BUG-77 | **FIXED** (v2.30.30) | Deco gas 1/2 mix selectors in `DECO_FIELDS` (persist on reload) |
| BUG-76 (He HT) | **FIXED** (v2.30.30) | `VPMEngine._setHeHT1` — buhl2003 He compartment HT sync |

---

## v2.30.28 verification (prior v22 draft)

### BUG-76 — Massive test suite hang / VPM CNS path
**Status:** ✅ Fixed

- `index.html` sets `_zhlHeadless=true` when `?massiveSuite=1`; `renderNDLTable()` guarded in headless mode.
- VPMEngine uses `computePlanExposureTotals()` with segment-start `scrRuntimeMin` (BUG-77 integration).

### BUG-77 — Deco gas persistence in `DECO_FIELDS`
**Status:** ✅ Fixed (v2.30.30)

- `'decoGas'` and `'decoCustomO2'` added in v2.30.28. ✓
- `'dg1Mix'`, `'dg2Mix'`, `'dg1CustomO2'`, `'dg2CustomO2'` added in v2.30.30. ✓

---

## BUG-78 — Massive suite ZHLEngine iframe errors (51×)

**Symptom:** On [tests-massive.html](https://threecats-lsp.com/d-planner-ccr/tests-massive.html), clicking **RUN ALL** (or overlapping auto-start + manual run) produced dozens of failures:

```
ZHLEngine not available — iframe not loaded
```

**Root cause:**

1. `calc()` held a stale `WIN` reference after `startTests()` reloaded the iframe.
2. Concurrent runs — auto-start + manual **RUN ALL** reloads iframe mid-suite.
3. `tests-massive.html` lacked service-worker cache busting and run cancellation present in `tests-massive-main.html`.

**Fix (v2.30.29):**

| File | Change |
|------|--------|
| `tests-massive.html` | `refreshFrameWin()` on every `calc()`; `_suiteRunId` cancels stale runs; SW `SKIP_WAITING`; versioned iframe URL; both run buttons disabled during execution |
| `tests-massive-main.html` | Same `refreshFrameWin()` + `_suiteRunId` guards |

**Regression coverage:** audit.py GROUP 62.

---

## BUG-79 — CCR C3 RT cross-val pin stale

**Symptom:**

```
CCR C3 Tx12/60 80m/16min SP1.3 — ZHL vs MultiDeco
C3 ZHL RT 83 vs ref 98 (±5 min)
```

**Root cause:** `MULTIDECO_CCR.C3.rt` pinned to MultiDeco RT 98, but first stop validated vs DiveKit (36 m). MultiDeco C3 starts at **45 m** — different stop ladder. LSP engine: **RT 83, first stop 36 m**.

**Fix (v2.30.29):** `C3: { rt: 83, firstStop: 36, … }`; optional `ref.rtTol` in `compareCCRMultiDeco()`.

**Regression coverage:** audit.py C3 pin check.

---

## BUG-80 — ZHL headless OTU/CNS plan re-integration

**Symptom:** `tests-pscr-otu-cns.html` Section D — ZHL CNS mismatches on 60 m profiles.

**Fix (v2.30.29):**

- `accumulateHeadlessPlanExposure()` before headless return in `runDecoSchedule()`
- ZHLEngine plan mapping preserves `pO2: s.pO2`
- `computePlanExposureTotals()` uses baked step pO2; pSCR subdivisions use segment-start runtime
- `tests-pscr-otu-cns.html` recompute uses live `altSurfaceP` / `BAR_PER_METRE`

**Regression coverage:** audit.py GROUP 61.

---

## BUG-81 — Massive main VPM calculate on iframe window

**Symptom:** 109 failures in `tests-massive-main.html` — `(w || E).calculate is not a function` on all VPM/VPMB_GFS tests.

**Fix (v2.30.30):** `vpmEngine(w)` helper resolves `VPMEngine` from iframe; audit GROUP 62 (vpmEngine checks).

---

## BUG-82 — ZHL pSCR OTU single-sample vs plan walk

**Symptom:** [tests-pscr-otu-cns.html](https://threecats-lsp.com/d-planner-ccr/tests-pscr-otu-cns.html) Section D — ZHL `totalOTU` 30–54 vs plan recompute 1–39 (diluent-level vs loop-depletion walk). Section F — VPM vs ZHL diverge by >12 OTU.

**Root cause:** `accumulateHeadlessPlanExposure()` integrated descent/bottom at a single fixed `scrRuntimeMin` (segment-start ppO₂ for the whole bottom block). VPM already uses `computePlanExposureTotals()` (runtime-subdivided pSCR walk). ZHLEngine.return preferred `lp.totalOTU` from the old accumulator.

**Fix (v2.30.30):**

- `accumulateHeadlessPlanExposure()` builds a plan array and delegates to `computePlanExposureTotals()`
- `ZHLEngine.calculate()` always returns OTU/CNS from `computePlanExposureTotals()` on the assembled plan (matches VPM `buildResult`)
- Injected bottom segment uses `btAtDepthMin` (not full BT including descent)

**Regression coverage:** audit.py GROUP 62 (BUG-82).

---

## Open bugs

_No open bugs in v2.30.30 scope._

---

## Cumulative status

| Report | Version | Bugs | Status |
|--------|---------|------|--------|
| v21 | v2.30.28 | BUG-76, BUG-77 | ✅ Complete (BUG-77 partial persists) |
| **v22** | **v2.30.30** | **BUG-78–82** | **✅ Complete** |
