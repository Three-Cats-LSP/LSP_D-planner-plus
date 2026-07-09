# Decompression Planner Domain References

This note records external reference material that should inform future LSP D-Planner+ engine, UI, and audit work. These are not normative standards by themselves, but they are useful domain references for planner behavior, user-facing explanations, and safety-oriented checks.

## Sources

- Dive Scuba: Technical diving: Planning decompression dives  
  https://www.dive-scuba.com/planning-deco-dives/

- Dive Scuba: Diving theory: Gradient Factors  
  https://www.dive-scuba.com/gradient-factors/

- Dive Scuba: Building a decompression planner - What it takes  
  https://www.dive-scuba.com/building-a-decompression-planner-what-it-takes/

## App Implications

### Planning Workflow

- A decompression plan is not only a stop table. The app should keep the complete planning loop visible: target depth/time, gases, environmental assumptions, decompression model, limiting factors, contingency plans, and gas limits.
- Contingency planning should remain first-class: deeper/longer scenarios, lost gas scenarios, gas sufficiency, CNS, OTU, and total decompression time all need to be checked before a plan is considered usable.
- Multi-level support is an expected planner capability. Engine and UI tests should continue covering multi-level profiles, deepest-first validation, and no re-descend constraints.

### Gas Planning

- Gas planning should be cylinder-specific and volume-first. The most useful display is required volume versus available volume, with pressure shown as a secondary conversion.
- The rule of thirds is an important planning mode, but the app should continue to make reserves and thresholds explicit instead of hiding them inside a table.
- Warning text should name the exact cylinder or gas role that is short, not just report a generic gas failure.

### Oxygen Exposure

- CNS and OTU should remain visible limiting factors, not buried export-only values.
- The UI should make it clear that exposure is accumulated per segment, including ascent/descent segments where average depth is used.
- High CNS/OTU states should be treated as plan issues, not only visual summary chips.

### Gradient Factors

- GF High controls the allowed surfacing gradient and overall conservatism near the surface.
- GF Low controls first-stop depth and the shape of the ascent from first stop to surface.
- The GF curve in the app should keep explaining the ramp from GF Low at first stop toward GF High at the surface, and should emphasize the leading compartment concept.
- User-facing copy should avoid implying there is one universally correct GF pair; the choice depends on dive context, training, conditions, frequency, and risk tolerance.

### Engine / Validation

- Input validation is safety-critical. Water density, altitude, gases, depth, time, rates, cylinder pressures, and fractions must be validated before engine execution.
- Environment parameters are real model inputs, not UI preferences. Audit cycles touching environment/unit state should include engine-consumer traces.
- Planner construction should continue to be tested as a pipeline:
  - pressure model
  - inert gas loading
  - tissue limit / M-value handling
  - ascent/depth grid generation
  - stop placement
  - gas switch handling
  - toxicity and gas consumption calculations
  - contingency output

### Audit Notes

- Future high-priority audit cycles should favor production safety paths: engine execution, gas sufficiency, contingency, unit/environment state, graph/schedule consumers, and export parity.
- Visual audits should not only check styling. They should verify that the UI exposes the correct planning concepts: gas switch, schedule, graph, gas reserves, CNS/OTU, and contingency failures.
- Protocol checks should remain fast enough that these domain checks do not get replaced by bookkeeping work.
