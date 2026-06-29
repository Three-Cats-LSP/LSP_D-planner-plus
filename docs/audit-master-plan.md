# Audit Master Plan v1.0

**Repo:** Three-Cats-LSP/LSP_D-planner-plus  
**Created:** 2026-06-30  
**Baseline commit:** `77149c2` (post-UI extraction)  
**Ledger:** [docs/audit-coverage.md](audit-coverage.md)  
**Strategy:** [docs/codebase-audit-strategy-v2.md](codebase-audit-strategy-v2.md)

---

## Scope at a Glance

| Layer | Files | Audit units | Units VERIFIED | Gap |
|-------|-------|-------------|----------------|-----|
| Engine cores | `zhl-physics-core.js`, `zhl-gas-core.js`, `zhl-ccr-core.js`, `zhl-schedule-core.js` | 37 | 27 | 10 |
| Bundles | `zhl-engine-bundle.js`, `vpm-engine-core.js`, `vpm-engine-bundle.js` | 3 | 0 | 3 |
| Worker / SW | `zhl-worker-bridge.js`, `sw.js` | 9 | 6 | 3 |
| Extracted UI cores | `surf-interval-core.js`, `gas-table-core.js`, `gas-plan-core.js`, `export-core.js`, `contingency-core.js` | 21 | 14 | 7 |
| `index.html` inline | 18 sections | 18 | 4 | 14 |
| Tooling | `audit.py`, `tools/*.py`, `dev/engine_regression.py`, `ci.yml` | 43 | ~28 | ~15 |
| **Total** | | **~131** | **~79** | **~52** |

> **59 units remain unverified.** This plan schedules them across 8 cycles, targeting full READ coverage by Cycle 8 and ≥85% VERIFIED by Cycle 10.

---

## The 7 Lenses (applied to every unit, every cycle)

| ID | Lens | Primary questions |
|----|------|------------------|
| **L1** | Arithmetic & physics | Wrong formula, wrong sign, divide-by-zero, float rounding, infinite loop, wrong units |
| **L2** | Control flow | Unreachable branches, early returns skipping required work, missing `try/finally`, wrong array index |
| **L3** | State & mutation | Shared mutable globals, stale closures, missing `appSettings.save()`, DOM state not restored on error |
| **L4** | API contract | Wrong argument order, missing parameter, wrong delegate normalization, missing `_syncZhlBundleEnv()` |
| **L5** | Mirror parity | Canonical source change not reflected in bundle; `check_engine_parity.py` blind spots |
| **L6** | Safety regression | Non-conservative deco result: wrong GF, wrong tissue loading, wrong setpoint, suppressed toxicity warning |
| **L7** | Tooling & CI | Parity checker blind spots, CI job ordering, missing precache entries, dead export names |

---

## The 59 Unverified Units

### Engine layer (10 open)

| Unit | File | Symbol / range | Gap type | Priority |
|------|------|----------------|----------|----------|
| PHY-03 | `zhl-physics-core.js` | `initTissues`, `saturate`, `saturateLinear` | No regression test | P1 |
| PHY-04 | `zhl-physics-core.js` | `ceiling`, `computeSurfaceGF` | No regression test | P1 |
| PHY-05 | `zhl-physics-core.js` | `gfAtDepth`, `ndlClearAtDepth` | No regression test | P1 |
| GAS-01 | `zhl-gas-core.js` | `enforceMinDecoProfile` | No regression test | P2 |
| GAS-03 | `zhl-gas-core.js` | fraction validators | No regression test | P2 |
| CCR-04 | `zhl-ccr-core.js` | `saturateCCR`, `loadTissuesWithCCR` | No regression test | P1 |
| SCH-01 | `zhl-schedule-core.js` | `runZhlScheduleCore` | Only 55% read; no ascent-rate regression | P0 |
| VPM-01 | `vpm-engine-core.js` | full file | UNREAD entirely | P0 |
| VPMB-01 | `vpm-engine-bundle.js` | parity vs core | UNREAD entirely | P0 |
| ZB-01 | `zhl-engine-bundle.js` | bundle parity | No formal parity test (M-11 open) | P1 |

### Extracted UI cores (7 open)

| Unit | File | Symbol | Gap type | Priority |
|------|------|--------|----------|----------|
| GT-04 | `gas-table-core.js` | tip constants | No regression test | P3 |
| GP-02 | `gas-plan-core.js` | `calcGasPlan` | No regression test | P2 |
| GP-03 | `gas-plan-core.js` | `buildGasPlanText`, `copyGasPlan` | No regression test | P2 |
| GP-04 | `gas-plan-core.js` | `buildGasPlanPDF` | No regression test | P2 |
| EXP-04 | `export-core.js` | `showToast`, `copyFallback` | Not regression-linked | P3 |
| EXP-05 | `export-core.js` | `exportPDF`, dialog | Not regression-linked | P2 |
| CONT-03 | `contingency-core.js` | `calcContingency` | Partial regression only | P1 |
| CONT-04 | `contingency-core.js` | contingency PDF/slate | Partial regression only | P2 |

### `index.html` inline (14 open)

| Unit | Section | Lines (approx) | Gap type | Priority |
|------|---------|----------------|----------|----------|
| UI-03 | Units & environment sync | 4226–4760 | UNREAD | P1 |
| UI-04 | Gas input / MOD display | 8550–8816 | UNREAD | P1 |
| UI-05 | CCR panel UI | 6309–6788 | UNREAD | P1 |
| UI-06 | Engine delegate layer | 6256–10114 | READ ~25% only | P0 |
| UI-07 | ZHL plan runner | 6802–9020 | UNREAD | P0 |
| UI-08 | VPM runner | ~7780+ | READ partial | P1 |
| UI-09 | NDL / OTU / CNS | 6953–7059 | READ partial, no regression | P1 |
| UI-11 | Deco table rendering | 9021–9884 | UNREAD | P1 |
| UI-12 | Gas consumption / SAC | 9319+ | READ partial | P2 |
| UI-14 | Multi-dive / history | 10193–11160 | UNREAD | P2 |
| UI-15 | Tools: MOD / best-mix | 11161–11500 | UNREAD | P2 |
| UI-18 | Init / DOMContentLoaded | 17200–17387 | UNREAD | P1 |
| UI-01 | State & constants | 3769–4394 | READ partial | P2 |
| UI-02 | Settings persistence | 16335+ | READ partial | P2 |

### Tooling (15 open — tracked separately, lower safety weight)

| Unit | File | Gap type | Priority |
|------|------|----------|----------|
| M-11a | `tools/check_engine_parity.py` | skip-list bypass not fixed | P1 |
| M-11b | `tools/check_engine_parity.py` | CCR body comparison dead | P1 |
| M-11c | `tools/check_engine_parity.py` | substring export check | P1 |
| H-09 | `tools/build_vpm_bundle.py` | does not exist yet | P1 |
| COV-01 | `tools/audit_coverage.py` | needs integration test | P3 |
| REG-01 | `dev/engine_regression.py` | CCR trimix inert PP test missing | P0 |
| REG-02 | `dev/engine_regression.py` | CCR setpoint zone selection test missing | P0 |
| REG-03 | `dev/engine_regression.py` | ppO2Check float rounding test missing | P1 |
| REG-04 | `dev/engine_regression.py` | trimix fHe ascent test missing | P1 |
| REG-05 | `dev/engine_regression.py` | NDL shallowGradient=false test missing | P1 |
| REG-06 | `dev/engine_regression.py` | pSCR altitude test missing | P1 |
| REG-07 | `dev/engine_regression.py` | multi-level VPM test missing | P1 |
| REG-08 | `dev/engine_regression.py` | contingency DOM integrity test missing | P2 |
| REG-09 | `dev/engine_regression.py` | deco ascent rate 3 m/min test missing | P0 |
| CI-01 | `ci.yml` | coverage-gate job not present | P2 |

---

## 8-Cycle Schedule

Each cycle = one audit session. Target: **400–600 new lines read** from `index.html` + **full read of any engine unit touched by last fix** + **regression test additions for all CRITICAL/HIGH findings**.

### Cycle 5 (next)

**Theme:** Engine delegate layer + ZHL plan runner + `vpm-engine-core.js` first pass

| Action | Units | Expected findings |
|--------|-------|------------------|
| Full read: UI-06 (remaining ~75%) | ~1,200 lines | 8–14 |
| Full read: UI-07 | ~1,200 lines | 6–10 |
| Full read: VPM-01 (first half, lines 1–950) | ~950 lines | 5–8 |
| Re-verify: SCH-01 (read missing 45%) | ~260 lines | 2–4 |
| Add regression tests: REG-01, REG-02, REG-09 | — | P0 blockers |
| Fix M-11a/b/c in `check_engine_parity.py` | — | tooling |

**Acceptance:** `audit.py` passes · `check_engine_parity.py` passes (with M-11 fixed) · REG-01/02/09 green · ledger updated

---

### Cycle 6

**Theme:** VPM completion + CCR panel + gas inputs

| Action | Units | Expected findings |
|--------|-------|------------------|
| Full read: VPM-01 (second half, lines 950–1900) | ~950 lines | 4–8 |
| Full read: VPMB-01 parity check | — | 3–6 |
| Full read: UI-05 (CCR panel UI) | ~480 lines | 4–6 |
| Full read: UI-04 (Gas input / MOD) | ~266 lines | 2–4 |
| Add regression tests: REG-03, REG-04, REG-05 | — | P1 |
| Implement `build_vpm_bundle.py` (H-09) | — | tooling |

**Acceptance:** VPM-01 + VPMB-01 → READ · H-09 resolved · REG-03/04/05 green

---

### Cycle 7

**Theme:** Deco table + environment sync + NDL/VPM runners

| Action | Units | Expected findings |
|--------|-------|------------------|
| Full read: UI-11 (Deco table rendering) | ~860 lines | 6–10 |
| Full read: UI-03 (Units & environment) | ~534 lines | 3–5 |
| Full read: UI-08 (VPM runner, unread portion) | ~400 lines | 3–5 |
| Full read: UI-09 (NDL/OTU/CNS, unread portion) | ~106 lines | 1–3 |
| Add regression tests: REG-06, REG-07 | — | P1 |

**Acceptance:** UI-11, UI-03 → READ · REG-06/07 green · ledger updated

---

### Cycle 8

**Theme:** Gas consumption + multi-dive history + ZHL schedule completion

| Action | Units | Expected findings |
|--------|-------|------------------|
| Full read: UI-12 (Gas consumption / SAC, unread portion) | ~400 lines | 3–5 |
| Full read: UI-14 (Multi-dive / history) | ~967 lines | 5–8 |
| Full read: SCH-01 (remaining; re-verify with new regression) | ~260 lines | 1–3 |
| Full read: CCR-04 re-verify with regression | ~80 lines | 0–2 |
| Add regression tests: REG-08 | — | P2 |

**Acceptance:** UI-12 gap closed · UI-14 → READ · SCH-01 → VERIFIED

---

### Cycle 9

**Theme:** Tools MOD / best-mix + init sequence + settings

| Action | Units | Expected findings |
|--------|-------|------------------|
| Full read: UI-15 (Tools: MOD / best-mix) | ~339 lines | 2–4 |
| Full read: UI-18 (Init / DOMContentLoaded) | ~187 lines | 2–4 |
| Full read: UI-01 gap fill | ~200 lines | 1–3 |
| Full read: UI-02 gap fill | ~200 lines | 1–3 |
| Add CI coverage-gate job (CI-01) | — | tooling |

**Acceptance:** UI-15, UI-18 → READ · CI-01 merged · ledger updated

---

### Cycle 10

**Theme:** Gas plan + export regressions + `engine_regression.py` full read

| Action | Units | Expected findings |
|--------|-------|------------------|
| Full read: `dev/engine_regression.py` (unread 80%) | ~880 lines | 2–5 |
| Re-verify: GP-02, GP-03, GP-04 with regression | — | 1–3 |
| Re-verify: EXP-05 with regression | — | 0–2 |
| Re-verify: CONT-03, CONT-04 with regression | — | 0–2 |
| Fill COV-01 integration test | — | tooling |

**Acceptance:** `dev/engine_regression.py` → READ · all GP/EXP/CONT units → VERIFIED

---

### Cycle 11

**Theme:** Final engine gaps + VERIFIED sweep

| Action | Units | Expected findings |
|--------|-------|------------------|
| Re-verify: PHY-03, PHY-04, PHY-05 with regression | — | 0–2 |
| Re-verify: GAS-01, GAS-03 with regression | — | 0–2 |
| Re-verify: ZB-01 (parity) with fixed M-11 | — | 0–1 |
| Any cycle 5–10 findings still open → close or defer | — | — |

**Acceptance:** All P0/P1 tooling items resolved · no open CRITICAL or HIGH findings

---

### Cycle 12 — Definition of Done

**Theme:** Final gap-fill + release-clean declaration

| Criterion | Target |
|-----------|--------|
| Coverage ledger | 100% of all units READ; ≥85% VERIFIED |
| `audit.py` | All tests pass (≥1043 if no new tests added) |
| Release regression | 9/9 suites pass (altitude, CCR, trimix, multi-level VPM) |
| Open issues | Zero CRITICAL or HIGH findings |
| `check_engine_parity.py` | M-11a/b/c fixed — guard is trustworthy |
| `build_vpm_bundle.py` | Exists and runs in CI |
| Regression tests | All 9 missing test classes (REG-01–09) committed and passing |
| CI coverage gate | `coverage-gate` job blocks merges with CRITICAL UNVERIFIED units |

---

## Severity Reference

| Severity | Criteria | Release impact |
|----------|---------|---------------|
| **CRITICAL** | Non-conservative deco schedule or suppressed safety warning | Blocks release immediately |
| **HIGH** | Incorrect result in reachable user path; DOM corruption; safety-adjacent | Fix in current cycle |
| **MEDIUM** | Wrong result in edge case; missing persistence; misleading UI | Fix current or next cycle |
| **LOW** | Dead code; misleading docs; robustness gap with no visible failure | Batch cleanup commit |

---

## `index.html` Anti-Pattern Checklist

Apply to every `index.html` unit in addition to the 7 lenses:

- [ ] Delegate missing `_syncZhlBundleEnv()` — any `ZhlEngineBundle.*` call not preceded by sync
- [ ] Column index assumption — `querySelectorAll('td')[N]` hardcoded; verify against actual table DOM
- [ ] `DECO_FIELDS` completeness — any slider/input that should persist but is absent from the list
- [ ] `mergeCCRSettings` bypass — CCR-consuming delegate passing raw `opts.ccr`
- [ ] `parseRunMinutes` misuse — applied to an integer-only column
- [ ] `try/finally` absence — any DOM swap-call-restore pattern without a `finally` restore block
- [ ] Event suppression during restore — `dispatchEvent` gated by `_restoreInProgress`
- [ ] `appSettings.save()` missing from `oninput` — any input whose value should be saved

---

## Per-Session Quick-Reference

```
Before starting:
  1. Pull latest main — confirm audit.py pass count and regression suite
  2. Open docs/audit-coverage.md — identify the cycle's target units
  3. Note units touched by the last fix batch (re-verify these first)

For each unit:
  4. Fetch entire unit — full line range, never a sample
  5. Apply L1–L7 (+ index.html checklist if applicable)
  6. Record: unit ID · line number(s) · lens · severity · description · fix
  7. Apply mirror rule for any engine finding (canonical source → bundle)

After reading all units:
  8. Triage: CRITICAL/HIGH require regression test linkage before closing
  9. Open GitHub issue: "Code Audit #NNN — <scope>"
 10. After fixes: re-read fixed units, run audit.py, check parity, run regression
 11. Update docs/audit-coverage.md — mark units READ or VERIFIED
 12. Commit ledger update and close issue with regression confirmation
```

---

*Update this file at the end of every cycle. When a cycle completes ahead of schedule, pull the next cycle's units forward. When a cycle reveals more findings than projected, defer its lowest-priority units to the next cycle.*
