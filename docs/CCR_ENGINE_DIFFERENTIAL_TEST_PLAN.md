# CCR Engine Differential Test Plan

Tracking issue: [#2 - Cursor: implement CCR differential tests](https://github.com/Three-Cats-LSP/LSP_D-planner-CCR/issues/2)

## Purpose

Implement a reproducible differential test suite for closed-circuit rebreather (CCR) dive plans produced by:

- LSP D-planner CCR
- MultiDeco 2.26
- DiveKit (divekit.app open captures, ApexDeco-family reference)
- Abysner (open ZHL-16C CCR reference planner, Abysner preset)
- Subsurface (open ZHL-16C CCR reference planner, Subsurface preset)

The suite must distinguish genuine LSP defects from expected differences caused by model constants, ascent integration, stop rounding, setpoint handling, or proprietary MultiDeco behavior.

> This is software verification and comparative analysis. Passing these tests does not certify any generated dive plan as safe and does not remove the need for qualified diver judgment and independent validation.

## Reference Strategy

### LSP

Run the production LSP engine through its existing headless calculation interface. Do not reproduce LSP calculations in a separate test-only implementation.

Record:

- repository commit
- application version
- model and all engine settings
- normalized plan and final tissue state

### DiveKit

Use open captures from [divekit.app cross-reference](https://divekit.app/data/cross-reference/) (`Knowledge Base/divekit-cross-reference/divekit-results.json`). DiveKit is an ApexDeco-family open reference; disclose this provenance in reports.

### Abysner

Use the open CCR reference planner in `tests/ccr-differential/lib/ccr_open_reference.py` with the **Abysner preset** (WV 0.0627, Schreiner transit, fixture ascent rates). This is a Bühlmann ZHL-16C implementation aligned with the [NeoTech-Software/Abysner](https://github.com/NeoTech-Software/Abysner) engine family — not a live vendored Abysner build. Regenerate goldens via `python tests/ccr-differential/build_assets.py`.

### Subsurface

Use the same open reference module with the **Subsurface preset** (WV 0.0627, 9/6/3 m/min ascent between deco stops, whole-minute stops). This extends the OC-focused `Knowledge Base/subsurface_engine.py` analysis with CCR inspired-gas loading. Regenerate goldens via `build_assets.py`. Not a live Subsurface binary capture.

### MultiDeco

Use actual MultiDeco 2.26 application results as behavioral goldens. For every capture, retain:

- application version
- screenshots or raw export
- every visible input and setting
- normalized result JSON
- checksum of the raw evidence

Use the decompiled Java sources and native-library disassembly in `MultiDeco Binary/` only to explain observed behavior. Do not treat reconstructed code as more authoritative than the captured application output, and do not attempt to make LSP imitate a demonstrated MultiDeco defect.

## Canonical Scenario Schema

Store scenarios as data rather than embedding them in test functions. Each fixture must include:

```json
{
  "id": "CCR-C1",
  "description": "Air diluent baseline",
  "profile": {
    "levels": [{ "depthM": 40, "timeMin": 28 }],
    "timeConvention": "at-depth"
  },
  "circuit": {
    "type": "CCR",
    "diluent": { "o2": 0.21, "he": 0.0 },
    "setpointsBar": { "descent": 0.7, "bottom": 1.3, "deco": 1.3 }
  },
  "decompression": {
    "model": "ZHLC_GF",
    "gfLow": 50,
    "gfHigh": 80,
    "stepM": 3,
    "lastStopM": 3
  },
  "environment": {
    "surfacePressureBar": 1.01325,
    "waterColumnMPerBar": 10.0,
    "waterVaporPressureBar": 0.0577,
    "altitudeM": 0,
    "acclimatized": true
  },
  "ratesMPerMin": {
    "descent": 22,
    "deepAscent": 9,
    "decoAscent": 9,
    "surfaceAscent": 3
  },
  "rounding": {
    "mode": "whole-minute",
    "minimumStopSec": 60,
    "gasSwitchSec": 0
  },
  "bailoutGases": []
}
```

The schema must represent multilevel profiles, repetitive-dive initial tissues, surface intervals, altitude, bailout time/depth, unavailable gases, and precise stop mode. Reject incomplete fixtures instead of silently applying engine-specific defaults.

## Normalized Result Schema

Each adapter must return:

- engine name, version, commit/build, and input checksum
- ordered profile segments with type, start/end depth, duration, runtime, gas, diluent, and setpoint
- ordered decompression stops with depth, duration, arrival runtime, and active gas
- first-stop depth, total stop time, TTS, and total runtime
- gas-switch depths and bailout gas requirements where available
- final N2/He pressure for all 16 compartments where available
- ceiling, controlling compartment, and gradient factor at checkpoints where available
- CNS and OTU where available
- warnings, rejected inputs, and non-finite values

Unsupported comparator fields must be marked `not_available`, never synthesized.

## Scenario Matrix

Implement the following fixtures:

1. **CCR-C1:** air diluent, 40 m/28 min, SP 0.7/1.3/1.3, GF 50/80.
2. **CCR-C2:** Tx18/45, 55 m/22 min, SP 0.7/1.3/1.3, GF 35/75.
3. **CCR-C3:** Tx12/60, 80 m/16 min, SP 0.7/1.3/1.3, GF 40/80.
4. **CCR-NDL:** shallow no-decompression CCR profile.
5. **CCR-SP:** distinct descent, bottom, and deco setpoints, including the ambient-pressure crossing where the requested setpoint becomes physically possible.
6. **CCR-ML:** Tx18/45 multilevel profile, 60 m/20 min followed by 42 m/8 min.
7. **CCR-GF-A/B:** identical profile at GF 50/80 and 50/50.
8. **CCR-LAST-A/B:** identical profile with 3 m and 6 m last stops.
9. **CCR-BO:** planned bailout to OC with Tx18/45, EAN50, and oxygen.
10. **CCR-LOST-GAS:** bailout variant with one decompression gas unavailable.
11. **CCR-REP:** two identical CCR dives separated by a 60-minute surface interval.
12. **CCR-ALT:** acclimatized dive at 1,500 m altitude.
13. **CCR-PRECISE-A/B:** one-second minimum stops versus whole-minute stop rounding.
14. **CCR-INVALID:** impossible setpoint, invalid diluent fractions, hypoxic surface use, excessive ppO2, and an unsurfaceable ceiling.

Preserve the existing C1-C3 MultiDeco evidence, but verify and migrate it into the canonical fixture format.

## Comparison Rules

### Exact failures

Fail a result for:

- invalid or reversed segment order
- negative inspired inert pressure
- negative, non-finite, or missing tissue values
- ascent through a calculated ceiling
- gas use below minimum ppO2 or above the configured maximum ppO2
- ignored setpoint, GF, rate, altitude, water, timing, or rounding settings
- state leakage between independent runs
- nondeterministic output from identical inputs
- unexpected engine exception, hang, or missing plan

### Differential tolerances

For inputs whose semantics are aligned:

- first-stop depth: within one configured stop step
- rounded stop duration: within 60 seconds at each stop
- rounded TTS: within `max(2 minutes, 5% of reference TTS)`
- precise stop duration: within 15 seconds at each stop
- precise TTS: within 60 seconds
- tissue pressures between open-source engines: absolute tolerance 0.01 bar at matching checkpoints
- gas-switch depth: exact configured stop depth

Do not broaden global tolerances to accommodate one discrepant profile. Any larger accepted difference requires a scenario-specific exception containing:

- affected engines and versions
- exact observed delta
- source, disassembly, or configuration evidence
- explanation of why the difference is not an LSP defect
- reviewer approval

### Classifications

Every engine pair/scenario must be classified as exactly one of:

- `PASS`
- `EXPECTED_DIFFERENCE`
- `LSP_SUSPECT`
- `COMPARATOR_SUSPECT`
- `INCONCLUSIVE`

A missing comparator result is `INCONCLUSIVE`, not `PASS`.

## Metamorphic Tests

Add engine-level assertions independent of comparator goldens:

- increasing depth or bottom time must not shorten decompression obligation
- lowering GF high must not shorten decompression
- increasing a valid CCR setpoint must not increase inspired inert pressure
- changing a phase setpoint must affect only the applicable profile phases
- earlier bailout must not reduce OC bailout gas demand
- removing a bailout gas must not produce a shorter equivalent bailout schedule without explanation
- residual tissues must increase the second dive's obligation relative to a clean-state equivalent
- identical runs must produce identical normalized output
- no valid calculation may create negative gas fractions or tissue pressures

## Harness and Reports

Implement a runner with separate adapters for LSP, DiveKit, Abysner, Subsurface, and MultiDeco goldens. Keep engine-specific input translation outside the canonical fixtures.

Generate:

- a machine-readable JSON report
- a Markdown summary grouped by scenario
- per-field deltas for stop schedules and tissues
- provenance and checksums
- documented expected differences
- a non-zero exit status for exact failures, `LSP_SUSPECT`, unexpected missing evidence, or tolerance breaches

The Markdown report must make setting mismatches visible before presenting output differences.

## Regression Integration

- Add focused automated regression tests for every confirmed LSP defect.
- Integrate the automated LSP/comparator comparison into the normal test command or CI workflow.
- Keep MultiDeco capture verification deterministic and offline; do not require the proprietary application in CI.
- Run the existing app, engine, massive, verification, and regression suites unchanged.
- Do not modify production decompression behavior merely to make a comparator test pass without root-cause evidence.

## Implementation Checklist

- [ ] Define and validate canonical scenario/result schemas.
- [ ] Implement the LSP production-engine adapter.
- [x] Abysner and Subsurface open-reference goldens via `ccr_open_reference.py`.
- [x] DiveKit captures from divekit.app cross-reference.
- [ ] Normalize existing C1-C3 MultiDeco captures.
- [ ] Capture missing MultiDeco scenarios with raw evidence.
- [ ] Implement all 14 scenario groups.
- [ ] Add exact safety/integrity assertions.
- [ ] Add differential comparisons and classifications.
- [ ] Add metamorphic tests.
- [ ] Generate JSON and Markdown reports.
- [ ] Integrate automated checks with the existing regression workflow.
- [ ] Run all existing suites and record results.
- [ ] Document every expected difference with evidence.
- [ ] Add regression fixtures for every discovered LSP defect.

## Pull Request Requirements

The implementation PR must include:

- the pinned versions and commits for all three engines
- complete test output and the generated Markdown report
- a list of discovered LSP defects and their regression tests
- a list of expected engine differences with supporting evidence
- unresolved or inconclusive comparisons
- confirmation that existing suites pass
- confirmation that tolerances were not weakened to obtain a passing result
