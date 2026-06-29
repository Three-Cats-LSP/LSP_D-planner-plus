# LSP D-Planner+ — Codebase Audit Strategy & Algorithm v2.0

**Prepared:** 2026-06-29  
**Applies to:** v2.53.00 onward  
**Purpose:** Replace the current ad-hoc 10-angle approach with a structured, coverage-tracked, reproducible audit algorithm that converges rather than repeats.

---

## 1. The Problem With the Current Approach

The 10-angle method has been effective for the engine layer (≥70% clean) but has fundamental structural weaknesses:

- **No coverage tracking.** Each audit starts from zero knowledge of what was already read. Lines already verified are re-read; unread lines are never systematically reached.
- **No file decomposition.** `index.html` at ~17,000 lines is treated as a monolith. Audits sample it at specific reported line ranges and leave ~85% unread.
- **Bug density is not used to schedule effort.** Dense areas (CCR tissue loading, contingency scenario) are repeatedly sampled; sparse areas (gas blending UI, equipment panels) are never touched.
- **Mirror-rule compliance is manual.** Dual-file checks (CCR core ↔ bundle, VPM core ↔ bundle) are remembered by prompt, not enforced by algorithm.
- **No regression linkage.** Findings are not tied back to specific test cases in `engine_regression.py`, so a fix can regress a related edge case that has no coverage.

The result: after 4 audit cycles, the engine is converging but `index.html` has had maybe 2,500 of its ~17,000 lines actually read. At current sampling rates, it will never converge.

---

## 2. Definitions

**Audit unit:** A single logical section of a source file, defined by function boundary or by a 200-line window in `index.html`. Each unit has one of three states: `UNREAD`, `READ`, `VERIFIED`.

**READ:** The unit has been fetched and analysed in at least one audit pass.  
**VERIFIED:** The unit is READ, all findings from that read are fixed, and a regression test covers the corrected logic.  
**Coverage %:** `READ / TOTAL` units per file. Convergence target: 100% READ, ≥80% VERIFIED.

**Audit cycle:** One full session consisting of a READ pass, a findings triage, a fix pass by the owner, and a verification pass. Produces one closed issue and one updated coverage ledger.

---

## 3. File Decomposition and Coverage Ledger

Before the first structured audit cycle, decompose every source file into audit units. Maintain a coverage ledger committed to `docs/audit-coverage.md` and updated at the end of every cycle.

### 3.1 Engine layer decomposition (function-boundary units)

Each exported or top-level function = one audit unit.

| File | ~Lines | Approx. units | Current coverage |
|------|--------|---------------|-----------------|
| `zhl-physics-core.js` | 191 | ~12 | ~90% READ |
| `zhl-gas-core.js` | 170 | ~10 | ~90% READ |
| `zhl-ccr-core.js` | 380 | ~18 | ~90% READ |
| `zhl-schedule-core.js` | 580 | ~22 | ~55% READ |
| `zhl-engine-bundle.js` | 1,600 | ~40 (parity + api block) | ~40% READ |
| `vpm-engine-core.js` | 1,900 | ~35 | ~25% READ |
| `vpm-engine-bundle.js` | 1,900 | ~35 (parity) | ~25% READ |
| `zhl-worker-bridge.js` | 130 | ~6 | ~85% READ |
| `sw.js` | 200 | ~8 | ~80% READ |
| `tools/*.py` | 500 | ~15 | ~80% READ |
| `ci.yml` | 150 | ~8 | ~85% READ |
| `dev/engine_regression.py` | 1,100 | ~20 | ~20% READ |

### 3.2 `index.html` decomposition (section-boundary units, ~200-line windows)

`index.html` at ~17,000 lines is too large to treat as a function-boundary file. Instead, decompose by logical UI section. Each section becomes one audit unit of ~150–300 lines.

Proposed section map (to be confirmed by reading the file's comment headers):

| Unit ID | Section name | Approx. lines | Current coverage |
|---------|-------------|---------------|-----------------|
| UI-01 | State declarations & constants | 3,900–4,100 | READ (partial) |
| UI-02 | Settings persistence (`AppSettings`, `DECO_FIELDS`) | 4,100–4,500 | READ (partial) |
| UI-03 | Unit system & environment sync | 4,500–4,800 | UNREAD |
| UI-04 | Gas input & MOD display | 4,800–5,400 | UNREAD |
| UI-05 | CCR panel & setpoint UI | 5,400–6,000 | UNREAD |
| UI-06 | Engine delegate layer (`_syncZhlBundleEnv`, all delegates) | 6,000–7,600 | READ (partial, ~25%) |
| UI-07 | ZHL plan runner & result renderer | 7,600–8,800 | UNREAD |
| UI-08 | VPM plan runner & result renderer | 8,800–9,600 | READ (sections ~7780–7880) |
| UI-09 | NDL / OTU / CNS widget | 9,600–10,400 | READ (specific lines) |
| UI-10 | Surface interval calculator | 10,400–11,000 | READ (specific lines) |
| UI-11 | Deco table rendering & export | 11,000–12,500 | UNREAD |
| UI-12 | Gas consumption calculator | 12,500–13,200 | UNREAD |
| UI-13 | Contingency scenario runner | 13,200–13,900 | READ (partial) |
| UI-14 | Dive history & repeat dive | 13,900–14,800 | UNREAD |
| UI-15 | Gas blending calculator | 14,800–15,400 | UNREAD |
| UI-16 | Equipment / cylinder panels | 15,400–16,000 | UNREAD |
| UI-17 | PDF / print export | 16,000–16,600 | UNREAD |
| UI-18 | `DOMContentLoaded` init sequence | 16,600–17,000 | UNREAD |

**18 `index.html` units × average 300 lines = ~5,400 lines in structured scope.** At the estimated ~1 bug per 100 unread lines, expect ~140 more UI findings total across all 18 units.

---

## 4. Audit Algorithm — Per Cycle

Each audit cycle follows this fixed algorithm. Deviation is allowed only for P0 hot-fixes.

### Step 0: Select units for this cycle

From the coverage ledger, select:
- All `UNREAD` engine units adjacent to recently-fixed areas (spillover risk)
- The next 2–3 `UNREAD` `index.html` units in section order
- Any `READ` unit whose finding was fixed in the previous cycle but has no regression test yet (re-verify)

Target: **400–600 lines of new `index.html` per cycle** + **full re-read of any engine unit touched by the last fix**.

### Step 1: Fetch each selected unit in full

Use `get_file_contents` with explicit line ranges matching the unit boundaries. Never sample — fetch the entire unit. Record the exact line range fetched.

### Step 2: Apply the 7-lens analysis to each unit

Each unit is evaluated against all 7 lenses. Record findings by unit ID, line number, lens ID, and severity.

| Lens | What to look for |
|------|-----------------|
| **L1 — Arithmetic & physics** | Wrong formula, wrong units, wrong sign, divide-by-zero, float rounding, infinite loop |
| **L2 — Control flow** | Unreachable branches, early returns that skip required work, missing `try/finally`, wrong column/index |
| **L3 — State & mutation** | Shared mutable globals, stale closures, missing `appSettings.save()`, DOM state not restored |
| **L4 — API contract** | Wrong argument order, missing parameter, wrong delegate normalization, missing `_syncZhlBundleEnv()` |
| **L5 — Mirror parity** | Any change to `zhl-ccr-core.js` must be in `zhl-engine-bundle.js`; same for VPM pair |
| **L6 — Safety regression** | Non-conservative deco result: wrong GF, wrong tissue loading, wrong setpoint, suppressed toxicity warning |
| **L7 — Tooling & CI** | Parity checker blind spots, CI job ordering, missing precache entries, dead export names |

### Step 3: Severity triage

| Severity | Criteria | Action |
|----------|---------|--------|
| **CRITICAL** | Produces a non-conservative deco schedule or suppresses a safety warning silently | Block release; fix before next cycle |
| **HIGH** | Incorrect result in a reachable user path; DOM corruption; safety-adjacent | Fix in current cycle |
| **MEDIUM** | Wrong result only in edge cases; missing persistence; misleading UI | Fix in current cycle or next |
| **LOW** | Dead code; misleading docs; robustness gap with no current user-visible failure | Batch into a cleanup commit |

### Step 4: Mirror rule enforcement (mandatory before any fix)

Before writing any fix for a finding in `zhl-ccr-core.js`, `zhl-physics-core.js`, or `zhl-gas-core.js`:
1. Check the corresponding function in `zhl-engine-bundle.js` for the identical bug.
2. Record both locations in the finding.
3. Fix canonical source first, then run `build_zhl_bundle.py` to regenerate the bundle.
4. Verify with `check_engine_parity.py`.

Same rule for `vpm-engine-core.js` ↔ `vpm-engine-bundle.js` (pending H-09: `build_vpm_bundle.py`).

### Step 5: Regression linkage

For every CRITICAL or HIGH finding:
- Identify the closest existing test case in `dev/engine_regression.py` that exercises the corrected path.
- If none exists, add a targeted test case before closing the finding.
- Annotate the finding with the test case ID.

This is the most important step that the current process skips. Without it, fixing C-04 (inert PP denominator) leaves no test that catches a regression back to `(1 - fO2)`.

### Step 6: Post-fix verification pass

After the owner applies fixes:
1. Re-read each fixed unit in full (not just the changed lines).
2. Re-apply the 7 lenses to the fixed unit.
3. Run `audit.py` and report the pass count.
4. Confirm `check_engine_parity.py` passes.
5. Confirm relevant regression test cases pass.
6. Update coverage ledger: fixed units → `VERIFIED`.

### Step 7: Issue hygiene

- Open one GitHub issue per audit cycle, titled `Code Audit #NNN — <scope description>`.
- Close it only after Step 6 is complete.
- Cross-link regression test additions in the closing comment.
- Commit updated `docs/audit-coverage.md` in the same closing commit.

---

## 5. `index.html` Specific Strategy

`index.html` requires a different approach from the engine files because it mixes HTML, CSS, and JavaScript in a 17,000-line file with no module boundary.

### 5.1 Read order priority

Read units in this order, based on bug density risk and safety relevance:

1. **UI-06** (Engine delegate layer) — highest risk: missing `_syncZhlBundleEnv()` calls affect every calculation
2. **UI-07** (ZHL plan runner) — direct interface to engine, unread
3. **UI-13** (Contingency scenario) — partially read, known bugs, H-04 just fixed; re-verify full section
4. **UI-08** (VPM runner) — partially read, M-06 just fixed; re-verify full section
5. **UI-09 / UI-10** (NDL/OTU/CNS + surface interval) — partially read, M-01/M-02 fixed; re-verify
6. **UI-04 / UI-05** (Gas input + CCR panel) — unread, feeds the delegate layer
7. **UI-11** (Deco table + export) — unread, large section
8. **UI-12** (Gas consumption) — unread
9. **UI-14** (Dive history) — unread
10. **UI-15** (Gas blending) — unread
11. **UI-16 / UI-17** (Equipment + PDF export) — lower safety relevance
12. **UI-01–03, UI-18** (State/settings/init) — partially read; fill gaps last

### 5.2 Anti-patterns to look for in `index.html`

In addition to the 7 lenses, apply these `index.html`-specific checks to every unit:

- **Delegate missing `_syncZhlBundleEnv()`** — any call to `ZhlEngineBundle.*` not preceded by a sync
- **Column index assumptions** — `querySelectorAll('td')[N]` hardcoded; verify against actual table structure
- **`DECO_FIELDS` completeness** — any slider/input whose value should persist but is not in the list
- **`mergeCCRSettings` bypass** — any CCR-consuming delegate that passes raw `opts.ccr`
- **`parseRunMinutes` misuse** — applied to integer-only columns
- **`try/finally` absence** — any DOM swap-call-restore pattern without a `finally` restore block
- **Event suppression during restore** — any `dispatchEvent` gated by `_restoreInProgress`
- **`appSettings.save()` missing from `oninput`** — any input whose value should be saved

---

## 6. Regression Test Strategy

`dev/engine_regression.py` is ~20% read and likely covers the happy path for ZHL/VPM but lacks targeted edge-case coverage for the bugs found so far.

### 6.1 Missing test classes (to be added per finding)

| Test class | Covers | Priority |
|-----------|--------|----------|
| CCR trimix inert PP | C-04: `fN2d + fHe` denominator for 21/35 diluent | P0 |
| CCR setpoint zone selection | C-03: `decoSP` returned above bottomCross depth | P0 |
| ppO2Check float rounding | H-02: 10/90 trimix ppO2 not suppressed | P1 |
| trimix fHe ascent | H-01: He off-gassing accounted for on ascent before first deco gas | P1 |
| NDL shallowGradient=false | H-03: NDL not optimistic vs. schedule ceiling | P1 |
| pSCR altitude | H-05: inert loading at altitude not understated | P1 |
| Multi-level VPM | H-10: nuclear regen not applied twice | P1 |
| Contingency DOM integrity | H-04: DOM restored correctly after engine throw | P2 |
| Deco ascent rate 3 m/min | C-02: direct `runZhlScheduleCore` call uses 3, not 9 | P0 |

### 6.2 Test format for each new case

```python
def test_<finding_id>_<short_description>(self):
    """
    Regression for audit finding <ID> (<issue #>).
    Verifies: <one-sentence description of the correct behavior>.
    """
    # arrange
    # act
    # assert — specific numeric bound or exact value, not just "no exception"
```

Every test must have a numeric assertion, not just `assertIsNotNone` or `assertNoException`. A deco schedule that is wrong but non-null passes a no-exception test.

---

## 7. Parallel Tooling Improvements

These tooling improvements should be done in parallel with the audit cycles, not after:

### 7.1 `build_vpm_bundle.py` (H-09, open)

Until this exists, the VPM mirror must be manually checked at the end of every cycle. This takes 15–20 minutes per cycle and will eventually miss a divergence.

**Target:** Implement before audit cycle 6.

### 7.2 `check_engine_parity.py` rewrites (M-11, open)

Three defects make the parity checker ineffective (skip list, dead CCR body comparison, substring export check). Fixing these makes the automated parity guard trustworthy.

**Target:** Fix all three defects before audit cycle 5.

### 7.3 Coverage ledger automation

Add a `tools/audit_coverage.py` script that:
- Reads `docs/audit-coverage.md` (the unit ledger)
- Parses `dev/engine_regression.py` to count test functions per unit
- Outputs a coverage summary table and highlights `READ-but-unverified` units

**Target:** Implement before audit cycle 5.

### 7.4 CI integration

Add a `coverage-gate` CI job that:
- Runs `tools/audit_coverage.py`
- Fails if any `CRITICAL`-tagged unit is `UNVERIFIED` (no regression test)

---

## 8. Projected Convergence Schedule

Based on current reading rate (~400–600 new `index.html` lines per cycle) and estimated bug density (~1 per 100 unread lines):

| Cycle | Units targeted | New lines read | Projected findings | Cumulative coverage |
|-------|---------------|----------------|---------------------|---------------------|
| **Current (post-#134)** | — | — | — | engine ~75%, UI ~15% |
| **Cycle 5** | UI-06, UI-07, UI-13 re-verify | ~900 | 8–12 | engine ~80%, UI ~25% |
| **Cycle 6** | UI-08 re-verify, UI-04, UI-05 | ~800 | 8–10 | UI ~35% |
| **Cycle 7** | UI-11, UI-12 | ~1,000 | 10–14 | UI ~50% |
| **Cycle 8** | UI-14, UI-15 | ~900 | 8–12 | UI ~63% |
| **Cycle 9** | UI-16, UI-17, UI-18 | ~900 | 5–8 | UI ~78% |
| **Cycle 10** | UI-01–03 gap fill + `vpm-engine-core.js` unread sections | ~1,200 | 4–8 | UI ~90%, VPM ~60% |
| **Cycle 11** | Full `dev/engine_regression.py` read + `vpm-engine-core.js` remainder | ~1,500 | 3–6 | All files ~90% |
| **Cycle 12** | Final gap-fill + all VERIFIED confirmation | ~800 | 0–3 | All files ~100% READ |

**Estimated completion:** ~7–8 more audit cycles from current state (cycles 5–12).  
**Total remaining findings estimate:** 60–100 (down from earlier estimate of 100–140, as some UI sections share anti-patterns that will batch into single findings).

---

## 9. Definition of Done

The codebase audit is complete when:

1. **Coverage ledger:** 100% of all audit units are `READ`; ≥85% are `VERIFIED`.
2. **`audit.py`:** 1043/1043 (or higher if new tests are added) passes on `main`.
3. **Release regression:** 9/9 suites pass including altitude, CCR, trimix, and multi-level VPM suites.
4. **No open `CRITICAL` or `HIGH` findings** in any GitHub issue.
5. **`check_engine_parity.py`:** Passes with the M-11 defects fixed — meaning the check is actually trustworthy.
6. **`build_vpm_bundle.py`** exists and runs in CI (H-09 resolved).
7. **All CRITICAL/HIGH regression tests** from Section 6.1 are committed and passing.

---

## 10. Quick-Reference Card for Each Audit Session

```
Before starting:
  1. Pull latest main — confirm audit.py and regression pass count
  2. Open docs/audit-coverage.md — identify next UNREAD units
  3. Note any units touched by the last fix batch (re-verify these first)

During each unit read:
  4. Fetch the full unit (exact line range, not a sample)
  5. Apply all 7 lenses (L1–L7)
  6. Record: unit ID, line numbers, lens, severity, description, fix recommendation
  7. Apply mirror rule for any engine finding

After reading all units:
  8. Triage: CRITICAL/HIGH require regression test linkage before closing
  9. Open one GitHub issue with all findings
 10. After owner applies fixes: re-read fixed units, run audit.py, update coverage ledger
 11. Commit updated docs/audit-coverage.md
 12. Close issue with regression confirmation
```

---

*This document supersedes the informal 10-angle method. It should be updated at the end of each audit cycle to reflect actual coverage, revised projections, and any new anti-patterns discovered.*
