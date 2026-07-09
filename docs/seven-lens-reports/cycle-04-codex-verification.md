# Cycle 4 Post-Merge Verification Report

**Branch reviewed:** `dev`

**Merged source:** PR #188 / `d747ccc`

**Current reviewed HEAD:** `df717c0`
**Verdict:** **BLOCKED — 2 HIGH, 2 MEDIUM**

## Summary

The END and Surface Interval fixes behave correctly in their declared browser traces. The combined Cycle 2-4 remediation is not ready to close, however. Canonical physical-value state is not updated by several real user input paths, the engine regression suite is order-dependent and currently red, and the manual ledger reports completed reviews whose records fail the protocol close gate.

## Findings

### SL-C04-H-02 — User edits after unit switching do not reach physical consumers

**Severity:** HIGH

**Locations:** `ui/markup-consumption.html:55`, `ui/markup-consumption.html:200`, `ui/markup-header.html:127`, `ui/markup-planner.html:305`, `settings-core.js:516-533`, `index.html:2897-2903`, `index.html:3491-3515`

**Root cause:** `setUnits()` introduced canonical `data-depth-m` and `data-volume-l` state, but the application has multiple writers for the corresponding display values. Best Mix, CNS, planner depth steppers, travel depth, and cylinder-size inputs do not all refresh canonical state. Downstream code prefers the stale dataset over the edited display value.

**Failure path:** Start metric, switch to imperial, enter a new physical value, then invoke the calculator or switch units again. Independent Chromium probes produced:

- Best Mix: visible `120 ft`, consumer remains `30 m`, then display returns to `30 m`.
- CNS: visible `120 ft`, consumer remains `30 m`, ppO2 remains `0.84`, then display returns to `30 m`.
- Planner depth: stepper reaches `134 ft`, consumer remains `40 m`.
- Cylinder size: visible `0.5 ft3`, canonical volume remains `12 L`.

**Why it matters:** Best Mix and CNS can show calculations for a different depth than the user entered. Contingency, export, planner, and gas-volume paths can likewise consume stale physical values.

**Recommendation:** Define one canonical writer contract for each dual-state control. Every input, stepper, settings restore, preset, dynamic-card, and unit-switch path must update display and canonical state atomically. Regressions must assert the final safety consumer, not only the label or dataset.

### SL-C04-H-03 — Completed review claims are not backed by closable records

**Severity:** HIGH

**Locations:** `docs/seven-lens-manual-ledger.json`; `docs/seven-lens-records/cycle-02-planner.json`; `cycle-03-consumption.json`; `cycle-04-tools-modals.json`

**Root cause:** The manual ledger could be changed to `SEVEN_LENS_REVIEWED` without a repository gate validating every reviewed cycle record.

**Failure path:** Run `python tools/seven_lens_protocol.py check --phase close` against the three records. Cycles 2 and 3 have incomplete legacy evidence. Cycle 4 has no `evidence_runs`; all five closed findings have empty `evidence_ids`; one lens lacks boundary cases; and its audit/baseline/verification checkpoints are inconsistent.

**Why it matters:** Documentation and CI can claim a safety review is complete while the evidence contract says it is not.

**Recommendation:** Run `check-all` from the static audit suite. Require record schema, evidence, commit, unit, finding, and ledger parity before accepting `SEVEN_LENS_REVIEWED`. Preserve Cycle 1 only through an explicit legacy exemption until it is migrated.

### SL-C04-M-03 — Full engine regression is stateful and currently fails

**Severity:** MEDIUM

**Locations:** `dev/engine_regression.py:1824-1992`, `dev/engine_regression.py:2411`, `dev/engine_regression.py:2421`

**Root cause:** Cycle 2/3 tests mutate canonical datasets, units, local storage, and travel-depth state without restoring the complete pre-test snapshot.

**Failure path:** `python dev/engine_regression.py` reports **166 passed, 2 failed**: `CYCLE31-CONTINGENCY-MOD` and `CYCLE33-PPO2-TOXICITY`. A full browser suite probe leaves `travelGasManualDepth` at `322 ft`.

**Why it matters:** Results depend on test order. A focused case can pass while the release sequence fails, and later cases can validate the wrong state.

**Recommendation:** Wrap every DOM regression in a common state transaction that restores values, datasets, units, globals, local/session storage, and dynamic nodes. Add repeated and shuffled-order runs plus an invariant that the suite leaves the initial state unchanged.

### SL-C04-M-04 — Browser evidence protocol allowed false-green traces

**Severity:** MEDIUM

**Locations:** `tools/seven_lens_browser_trace.py`; `docs/seven-lens-traces/cycle-03-consumption.json`

**Root cause:** The trace runner previously accepted forced tested actions, an empty trace/assertion set, a single run, non-finite captures, and console/page errors. Cycle 3 tested unit conversion but not editing after conversion.

**Failure path:** A forced hidden input can bypass visibility and user-event behavior. `all([])` style success and rounded observable comparisons can then produce a green artifact without exercising the failing writer-to-consumer path.

**Recommendation:** Require schema-v2 traces, two or more fresh-context runs, visible unforced tested actions, finite captures, non-empty assertions, exact state restoration, console/page-error cleanliness, and artifact hashes. Every dual-unit control must include an edit-after-switch and roundtrip trace.

## Verification Results

| Check | Result |
|---|---|
| Protocol/browser unit tests | PASS, 25/25 |
| Cycle 4 END/SI hardened traces | PASS, repeatable |
| Cycle 3 edit-after-switch traces | FAIL, reproduces stale canonical state |
| Engine regression | FAIL, 166/168 |
| V3 CI profile | FAIL through engine suite |
| Static profile | BLOCKED by the two open HIGH findings |
| Cycle 2-4 protocol close | FAIL |

No application source was modified during this verification.
