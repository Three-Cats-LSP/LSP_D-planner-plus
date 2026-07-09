# Cycle 03 Codex Verification

**Branch:** `dev`
**Verified head:** `601fda8`
**Merged cycle:** PR #182
**Verdict:** **BLOCKED**

## Summary

The three findings reported by the Cycle 3 audit were changed in source, and the
legacy engine regression, static profile, and old protocol close check all pass.
The cycle is not clean: browser-level value tracing found exact physical-depth
drift hidden by rounded UI assertions, the regression cleanup does not restore
its own state correctly, and two safety/copy defects remain in the reviewed
markup. Audit continuity was also broken when the cycle baseline deleted five
unresolved Cycle 2 findings and rewrote that prior cycle as passed.

## Findings

### SL-C03-H-02: Shallow-stop guidance makes an unconditional safety claim

- **Location:** `ui/markup-consumption.html:364`
- **Root cause:** The Knowledge Base says extending 6 m and 3 m stops "is safe"
  without bounding that statement by oxygen exposure, remaining gas, or a
  recalculated plan.
- **Failure path:** A user extends an oxygen-rich shallow stop while relying on
  the safety claim and does not re-check CNS/OTU or gas reserve.
- **Impact:** Safety-sensitive guidance can encourage an exposure-changing action
  without the limits the rest of the planner models.
- **Recommendation:** Remove the universal safety characterization and state the
  operational conditions that must remain within the generated plan's limits.

### SL-C03-M-02: Rounded assertions hide physical-depth drift and bad cleanup

- **Locations:** `index.html:2885-2903`, `index.html:3472-3486`,
  `index.html:3626-3629`, `index.html:7084-7087`, `index.html:7609-7612`, and
  `dev/engine_regression.py:1861-1893`
- **Root cause:** `setUnits` first records the exact metre value, but
  `calcBestMix` and `calcCNS` call `syncDepthInputCanonical` again and replace it
  from a rounded display value. The regression compares only `34%` and `0.84`,
  whose display precision is too coarse to reveal the changed consumer input.
  Its `finally` block restores depth strings while still in imperial mode and
  only then restores units, so those strings are interpreted as feet.
- **Failure path:** Start at 30 m. Best Mix becomes 98 ft and its consumer receives
  29.87039904414723 m. CNS returns from metric to imperial to metric as 29.9 m
  with the same 29.87039904414723 m canonical value. Existing displayed results
  remain unchanged.
- **Impact:** Unit switching silently changes physical input state, and repeated
  regression runs can contaminate later cases while claiming clean restoration.
- **Recommendation:** Maintain canonical depth separately from display rounding.
  Browser regressions must capture the event, canonical value, consumer value,
  and observable output, then compare hashed state snapshots after cleanup.

### SL-C03-L-02: GFS recommendation describes the opposite use case

- **Location:** `ui/markup-consumption.html:378`
- **Root cause:** The text recommends GFS when VPM-B shallow stops feel "too long."
- **Failure path:** A user enables GFS expecting shorter shallow decompression.
- **Impact:** This contradicts the header's accurate statement that GFS adds a
  conservative surfacing ceiling and is useful when pure VPM-B feels too
  aggressive.
- **Recommendation:** Align the Knowledge Base text with the actual GFS constraint
  and the existing header explanation.

## Audit Integrity

Commit `6e987af` deleted `SL-C02-H-01` and `SL-C02-M-03` through
`SL-C02-M-06`, changed the Cycle 2 ledger from blocked to passed, and removed the
same findings from the Cycle 2 record. It then became Cycle 3's baseline. This is
not a valid resolution path and made green CI possible by removing open evidence.
The findings and blocked ledger state have been restored.

## Verification Evidence

- `python dev/engine_regression.py`: **163/163 passed**, demonstrating why the
  previous rounded checks did not detect the defect.
- `python -m tools.audit check --profile static`: **passed** before findings were
  restored.
- Old `seven_lens_protocol.py ... --phase close`: **passed** before hardening.
- `python tools/seven_lens_browser_trace.py --spec
  docs/seven-lens-traces/cycle-03-consumption.json`: **failed both traces** with
  exact value captures and state hashes.

Cycle 4 must not begin until Cycle 2 and Cycle 3 are both returned to verified
status under protocol schema v2.
