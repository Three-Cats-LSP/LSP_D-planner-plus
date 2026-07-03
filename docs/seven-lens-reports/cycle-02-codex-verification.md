# Seven-Lens Cycle 02 - Codex Independent Verification

**Verified merge:** `b37d836` on `dev`  
**Reviewed source commit:** `b56fc07`  
**Unit:** `UI-MARKUP-PLANNER` (`ui/markup-planner.html:1-493`)  
**Verdict:** BLOCKED

## Summary

The Cycle 2 protocol record passes the original closure checker and all automated
CI checks are green, but the substantive review is not complete. The min-deco
regression asserts an unused adapter property rather than schedule behavior, the
travel-depth repair creates physically inconsistent metric/imperial limits, and
two additional unit/state defects remain in the reviewed controls and callers.

## Findings

### SL-C02-H-01: Imperial cylinder size constraints permit impossible volumes

- **Severity:** HIGH
- **Lenses:** L1, L3, L4, L6
- **Location:** `ui/markup-planner.html:305-307,347-353,403-405,445-447`;
  `index.html:3464-3475`
- **Root cause:** Cylinder values are converted from litres to cubic feet, but the
  imperial maximum is set to `1766` instead of approximately `1.77`. Metric
  `min=1` and `step=0.5` also remain active after values such as `0.4 ft3` are
  produced.
- **Failure path:** Switch to imperial. A default 12 L cylinder becomes 0.4 ft3,
  which is below the unchanged minimum of 1, while an input of 2 ft3 or hundreds
  of ft3 remains below the erroneous maximum.
- **Impact:** Browser validity rejects normal cylinders yet permits physically
  enormous cylinder volumes that can grossly overstate gas availability.
- **Evidence:** Chromium reported value `0.4`, min `1`, max `1766`; `2 ft3` was
  constraint-valid.
- **Recommendation:** Define one canonical physical min/max/step tuple and derive
  metric and imperial constraints for fixed, dynamic, and gas-plan cylinders.
- **Proposed regression:** `SL-C02-CYLINDER-PHYSICAL-CONSTRAINTS`
- **Status:** OPEN

### SL-C02-M-03: Travel switch-depth limits are not physically equivalent

- **Severity:** MEDIUM
- **Lenses:** L1, L3, L4, L6
- **Location:** `ui/markup-planner.html:337-339`; `index.html:3456-3459`;
  `gas-cards-core.js:514-521`
- **Root cause:** The markup declares 100 m, unit conversion restores 500 m, and
  the new synchronizer caps imperial input at 165 ft (about 50 m).
- **Failure path:** A 16% travel gas can have an approximately 77 m usable MOD.
  `77 m` is accepted, but the equivalent `253 ft` is rejected after switching to
  imperial.
- **Impact:** Valid manual travel switches are accepted or rejected solely from
  display units; the claimed Cycle 2 parity fix is incomplete.
- **Evidence:** Chromium: metric max 500 and 77 m valid; imperial max 165 and
  253 ft invalid.
- **Recommendation:** Select one canonical metre maximum and derive the imperial
  maximum from it everywhere, including restore-only paths.
- **Proposed regression:** `SL-C02-TRAVEL-DEPTH-PHYSICAL-PARITY`
- **Status:** OPEN

### SL-C02-M-04: Unit round trips mutate the active dive plan

- **Severity:** MEDIUM
- **Lenses:** L1, L3, L6
- **Location:** `index.html:3352-3480`
- **Root cause:** Display-rounded values are converted back as canonical values.
  Integer feet and one-decimal cubic feet discard enough precision to alter the
  original metric inputs.
- **Failure path:** With defaults, switch metric -> imperial -> metric.
- **Impact:** `40 m` becomes `39.9 m`; 12 L bottom/travel cylinders become 11 L.
  Merely viewing another unit system silently changes the plan and gas reserves.
- **Evidence:** Fresh Chromium state snapshot reproduced all three mutations.
- **Recommendation:** Preserve canonical physical values separately or retain
  sufficient conversion precision; add bidirectional non-default round-trip tests.
- **Proposed regression:** `SL-C02-UNIT-ROUNDTRIP-IMMUTABLE`
- **Status:** OPEN

### SL-C02-M-05: Min-deco regression does not test the reported behavior

- **Severity:** MEDIUM (audit/test evidence)
- **Lenses:** L4, L7
- **Location:** `dev/engine_regression.py:1815-1851`; `index.html:4759-4765,5620-5625`;
  `zhl-schedule-core.js:66-68,242-246`; `vpm-engine-bundle.js:1206-1233`
- **Root cause:** `SL-C02-MIN-DECO-UNITS` only checks that a DOM adapter returns
  `isMetric === false`. Current ZHL and VPM min-deco engines operate on internal
  metre depths and do not consume this property for stop enforcement.
- **Impact:** The test passes even if schedule output is unchanged or wrong. The
  report's claimed failure was not demonstrated before the fix.
- **Recommendation:** Replace the flag assertion with metric/imperial schedule
  probes that assert physically equivalent 9 m/30 ft and 6 m/20 ft minimum stops,
  and prove the case fails on the pre-fix commit.
- **Status:** OPEN

### SL-C02-M-06: Protocol accepted a nonexistent audit checkpoint

- **Severity:** MEDIUM (audit process)
- **Lens:** L7
- **Location:** `docs/seven-lens-records/cycle-02-planner.json`;
  `tools/seven_lens_protocol.py:237-271` before this verification
- **Root cause:** `audit_commit` equals `baseline_commit` (`3731e56`), while the
  first Cycle 2 commit combines report, fixes, tests, and metadata. The checker
  validated only that the field was nonempty.
- **Impact:** The read-only Audit phase, fix separation, and pre-fix behavioral
  evidence could all be skipped while closure still returned PASS.
- **Recommendation:** Require a distinct report-only audit commit descended from
  baseline and require observable pre-fix failure, post-fix success, emitted case
  IDs, and state-restoration evidence for every medium-or-higher finding.
- **Status:** OPEN

## Verification

| Check | Result |
|---|---|
| GitHub PR #179 CI and Release Gates | PASS |
| Original protocol close check | PASS (demonstrates gate weakness) |
| Full 493-line source reread | COMPLETE |
| Travel-depth physical parity probe | FAIL |
| Cylinder constraint probe | FAIL |
| Unit round-trip state snapshot | FAIL |
| Min-deco observable regression review | FAIL |

Cycle 2 must remain `IN_PROGRESS` until these findings receive a separate fix
pass and fresh independent verification.

