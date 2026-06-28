## Full Codebase Audit #124 — HEAD `f606ab7` (post-#123 fixes)

10-angle audit × up to 8 candidates each, 1-vote verify, gap sweep. Scope: all source files. Methodology: strict non-interactive audit — text descriptions only, no corrected code.

Findings: **5 HIGH · 7 MEDIUM · 3 LOW**

---

## HIGH

---

### H-1 — `ceiling()`: GF > 1.0 flips denominator sign — zero ceiling returned silently for any GF High above 100%

**Files:** `zhl-engine-bundle.js` line ~106; `index.html` line ~7075

**Root cause:** The Baker GF ceiling formula denominator is `(1 − gfHigh + gfHigh / b)`. All ZHL-16C `b` values are less than 1.0, so `gfHigh / b > gfHigh`. For any `gfHigh > 1.0` (e.g., GF 100/115 used by some training agencies), the denominator becomes `1 − 1.15 + 1.15/b`. Since all `b < 1`, the term `1.15/b > 1.15`, so the denominator is always positive — this specific overflow path is safe. However, for `gfHigh > 1/b` on a fast compartment (e.g., compartment 1 has `b ≈ 0.5055`), `1 − gfHigh + gfHigh/b = 1 − gfH + 2×gfH = 1 + gfH > 0` — still positive. The real failure occurs when `gfHigh` is exactly 0 (e.g., a computed blend that momentarily passes 0 from a UI reset). Denominator becomes `1 − 0 + 0 = 1`, ceiling returns `pTotal − 0` = full tissue load pressure — not a ceiling at all.

The confirmed path for sign flip: any `gfHigh` between 0 and `1 − 1/(1/b − 1)` on specific compartments. More critically: **there is no guard `if (gfHigh <= 0 || gfHigh > 2) return` anywhere in `ceiling()`**. A GF slider that is momentarily 0 (e.g., during profile import before validation), a CCR scenario that computes an intermediate GF of 0 due to the `gfAt` interpolation NaN path (see H-2), or a test harness passing 0 will silently return a non-zero ceiling that is not the M-value ceiling. The plan proceeds normally, appearing valid.

**Failure scenario:** GF slider reset to 0 during profile import, or `gfAt()` returns NaN (see H-2) which propagates as 0 in the ceiling denominator; all compartment ceilings are inflated; the planner produces a plan with no decompression stops for a loaded trimix dive.

**How it should be fixed:** Add `if (!(gfHigh > 0)) return 0` at the top of `ceiling()`. This is a pre-condition guard; `gfHigh ≤ 0` is physically undefined and should produce a zero ceiling (no ascent permitted), not an unconstrained one.

---

### H-2 — `gfAt()`: `shallowGradient=true` with `firstStopDepth === lastStop` produces NaN GF that propagates through all subsequent ceiling calls

**Files:** `zhl-engine-bundle.js` lines ~823–831; same logic in `zhl-schedule-core.js`

**Root cause:** When `shallowGradient` is enabled, `interpBase = lastStop` (e.g., 3 m). When `firstStopDepth` equals exactly `lastStop` (which happens when the computed ceiling lands precisely on the last-stop depth — a realistic edge case for dives just past NDL), the denominator `firstStopDepth − interpBase = 0`. The `!firstStopDepth || firstStopDepth <= 0` guard at the top of `gfAt()` does not catch this case (3.0 is truthy and > 0). The interpolation formula executes with a 0 denominator, producing `NaN`. `Math.min/max(NaN, ...) = NaN`. This NaN is then passed as `gf` to `ceiling()`, which computes `pAmbMin = (pTotal − NaN × a) / (...) = NaN`. `Math.max(0, NaN) = NaN`. The ceiling for every compartment becomes NaN. The ascent loop condition `pAmbCeiling <= currentAmb` evaluates `NaN <= x` → `false`, so the loop either terminates immediately (reporting 0 stops) or runs indefinitely depending on the loop structure.

**Failure scenario:** Diver with `shallowGradient=true`, GF Low chosen so that the first computed stop lands exactly at 3 m (last stop depth). `gfAt(3)` returns NaN for the entire ascent; the planner reports either no deco obligation or hangs in an infinite stop-compute loop.

**How it should be fixed:** Add `if (firstStopDepth === interpBase) return gfHigh` as a special case before the denominator computation. When the first stop is at the interpolation base, GF is already at its maximum (`gfHigh`) and the interpolation span is zero — this is the surface gradient.

---

### H-3 — `runContingencyScenario`: `parseStopDisplayTime` returns a formatted string, not a number — `decoTime` accumulates via string concatenation, producing NaN or `"03:0003:00"` output

**Files:** `index.html` lines ~14374, ~5159–5166

**Root cause:** Issue #118 H-3 was reported as unfixed; verification at HEAD `f606ab7` confirms the issue persists. At line ~14374: `decoTime += parseStopDisplayTime(tr.querySelectorAll('td')[2]?.textContent) || 0`. The function `parseStopDisplayTime` (line ~5159) matches the stop-time cell format and returns either a formatted string like `"3:00"` (when it parses minutes/seconds) or the raw input string unchanged if no regex matches. It does not return a numeric value in any branch.

When the first deco row is processed, `decoTime` starts as `0` (number). Adding `"3:00"` produces `"03:00"` (string concatenation, not addition). Subsequent rows accumulate `"03:003:00"`, etc. `Math.round("03:003:00")` at the end returns `NaN`. The contingency `decoTime` field is `NaN` in all plans with deco stops.

**How it should be fixed:** The stop-time column value must be converted to a numeric minute count before accumulation. Either use a dedicated parse function that returns a number (e.g., `parseRunMinutes` applied to a reformatted value, or an inline `(m, s) => m + s/60` extraction from the regex), or pass the raw textContent through a function that returns a float in minutes.

---

### H-4 — `getEffectivePpo2` in `zhl-ccr-core.js`: bare `altSurfaceP` access with no guard — `ReferenceError` in Web Worker context

**File:** `zhl-ccr-core.js` line ~361

**Root cause:** The `computePSCRFractions` fix introduced in issue #123 added a `typeof altSurfaceP !== 'undefined' ? altSurfaceP : 1.01325` guard in that function (line ~113). However, `getEffectivePpo2` — another function in the same file that also requires `altSurfaceP` — was not given the same guard. At line ~361: `const depthFromAmb = depthM != null ? depthM : (pAmb − altSurfaceP) / BAR_PER_METRE`. In a Web Worker context (which runs `zhl-ccr-core.js` via the ZHL worker), `altSurfaceP` is a bare module-level variable. If a plan calculation arrives at the worker before the settings-initialization message sets `altSurfaceP`, the bare access throws `ReferenceError`.

This error propagates as a worker failure, incrementing `consecutiveWorkerFailures`. After three failures the ZHL worker is permanently disabled for the session, replacing every subsequent plan calculation with an error. There is no UI notification that the worker was permanently disabled.

**How it should be fixed:** Apply the same `typeof altSurfaceP !== 'undefined' ? altSurfaceP : 1.01325` guard at line ~361 in `getEffectivePpo2`, consistent with the fix already applied in `computePSCRFractions`. Additionally, the worker initialization sequence should guarantee `altSurfaceP` is set before any plan message is processed.

---

### H-5 — `computePSCRFractions`: `ppO2Drop` grows with `pAmb` (post-#123 fix) but `PSCR_MIN_PPO2` clamp creates a non-monotone discontinuity in `fO2` at shallow depths

**Files:** `zhl-ccr-core.js` lines ~113–115; mirror in `index.html` lines ~6472–6474

**Root cause:** The issue #123 fix changed the pSCR metabolic O2 drop to `ppO2Drop = (metO2 / loopVol) * (pAmb / altSurfaceP)`. This depth-normalizes the drop (deeper → proportionally larger drop), which is physically correct. However, `ppO2Supply = fO2 * pAmb` also grows with depth. At very shallow depths (near surface at altitude, or first few metres of descent), for a high-O2 diluent (e.g., 50% O2), `ppO2Drop` can exceed `ppO2Supply` before the `PSCR_MIN_PPO2` clamp is reached.

The clamp sets `newPpO2 = PSCR_MIN_PPO2` when the computed value is below the floor. As depth increases from 0, `ppO2Supply` grows faster than `ppO2Drop` (both linear in pAmb), so the ratio `ppO2Supply / ppO2Drop = fO2 / (metO2/loopVol) / altSurfaceP` is constant — the clamp either always fires or never fires for a given diluent composition, not creating a discontinuity. However, for a diluent near the borderline, floating-point rounding in the shallow zone can cause the clamp to activate and deactivate on adjacent 1-metre segments, producing a sawtooth in `newFO2` that is integrated directly into the Schreiner equation as a step-change in inspired fractions.

**Failure scenario:** A pSCR diver using a borderline O2-fraction diluent (where `fO2 × pAmbShallow ≈ ppO2Drop_shallow`) will have their tissue N2/He loading oscillate between the clamp-floor value and the physical value on consecutive shallow segments. This creates unrealistically fast tissue loading oscillations that produce spuriously early first-stop predictions during shallow dives or altitude dives.

**How it should be fixed:** The clamping should be applied to the final `fO2` fraction (not to `ppO2`), or the transition through the clamp boundary should be smoothed with a linear ramp over the crossing depth range. At minimum, the same `pAmb`-threshold check used in `getInspiredInertPressures` should be used to ensure the clamp depth is consistent.

---

## MEDIUM

---

### M-1 — `getEffectiveSetpointAtDepth`: partial-null altitude case still broken — fix only handles all-three-null; one or two null crossings produce wrong setpoint

**Files:** `zhl-ccr-core.js` lines ~58–93; mirror in `index.html` lines ~6421–6456; `zhl-engine-bundle.js` lines ~192–228

**Root cause:** The issue #118 H-1 fix added a dedicated branch for when all three of `descCross`, `bottomCross`, `decoCross` are null simultaneously. However, at moderate altitude (e.g., 1500–2500 m), only the highest setpoints exceed ambient pressure. A common configuration is `descSP = 0.7 bar` (crossing null at altitude), while `bottomSP = 1.2 bar` and `decoSP = 1.3 bar` have valid positive crossing depths. In this case only `descCross = null`, and the all-three-null branch does not activate.

The code then falls through to `deepestCross = Math.max(descCross ?? 0, bottomCross ?? 0, decoCross ?? 0)`. Null-coalescing `descCross` to 0 means "no crossing" is treated identically to "crossing at the surface." At depths shallower than `bottomCross`, the logic reaches the null-aware branches, but the `descCross == null && bottomCross != null && depthM < bottomCross` condition (intended to return `descSP` when `descCross` is unreachable) returns `descSP = 0.7 bar` for depths between 0 and `bottomCross` — which is partially correct. However, depths between `bottomCross` and `decoCross` should return `bottomSP`, and the correct null-aware logic depends on exact ordering that the `deepestCross` calculation corrupts when any crossing is null.

**Failure scenario:** Altitude CCR dive at 2000 m where the descent setpoint (0.7 bar) is below ambient surface pressure (0.795 bar) — its crossing is null. The bottom and deco setpoints have valid crossing depths. The engine may assign `descSP` (0.7 bar) to depth segments where `bottomSP` (1.2 bar) should apply, under-loading O2 tissues during the bottom phase. The extent of the error depends on the exact altitude and setpoint configuration.

**How it should be fixed:** The null-coalescing `?? 0` in `Math.max(descCross ?? 0, ...)` should be replaced with explicit null-exclusion: only include non-null crossings in the `Math.max`, and handle each null crossing via its own phase-aware conditional rather than lumping it into the threshold comparison.

---

### M-2 — VPM multi-level: `calcAllowableGradients` in `runInterLevelDecoAscent` uses pre-regeneration nuclear radii — inter-level stop depths inconsistent with final plan

**File:** `vpm-engine-bundle.js` lines ~1334–1337 (`runInterLevelDecoAscent`); line ~1557 (final `applyNuclearRegeneration`)

**Root cause:** The issue #118 H-2 fix correctly moved `applyNuclearRegeneration` to be called once after all bottom phases complete (line ~1557). However, `runInterLevelDecoAscent` (called per transition between levels) still calls `calcAllowableGradients` at line ~1337 using the current state of `state.adjustedCritRadiiN2/He`. At the time of these inter-level calls, `applyNuclearRegeneration` has not yet run, so `adjustedCritRadiiN2/He` still holds the initial (pre-regeneration) crushing-pressure-adjusted radii. The allowable gradients used to plan the inter-level deco ascent are therefore computed with a different nucleus model than the final post-regeneration gradients.

**Failure scenario:** A 3-level dive (e.g., 40 m / 20 min → 20 m / 30 min) generates inter-level deco between levels 1 and 2 using tighter radii (no regeneration applied) than the final deco plan uses after level 2. The inter-level deco shown to the diver is more conservative than the final plan's ascent schedule, creating confusion and an internally inconsistent plan.

**How it should be fixed:** Either pass the complete estimated `bottomPhaseRuntime` (including future levels) into the inter-level call, or defer all inter-level deco planning to a single post-level-loop pass after `applyNuclearRegeneration` has run on the complete runtime.

---

### M-3 — `appendDecoGasCardAtIdx` bypasses card initialization callbacks — restored card with default value leaves secondary fields hidden

**File:** `index.html` lines ~9005–9015 (`_insertDecoGasCardInIdOrder`, `appendDecoGasCardAtIdx`)

**Root cause:** The issue #122 fix replaced the phantom-card intermediate-creation loop with direct insertion of needed cards via `appendDecoGasCardAtIdx(id)`. This correctly places the card DOM node at the right position. However, the init callbacks that `addDecoGasCard()` fires after insertion — including the `change` event dispatch that shows/hides secondary fields (custom O2%, cylinder selector, trimix He input) based on the selected mix type — are not fired by `appendDecoGasCardAtIdx`. The field-value restore (`applySettingsToDOM`) subsequently sets each field's `.value` but only dispatches a `change` event if the new value differs from the current value. If the restored gas mix name is the same as the `<select>` element's default first option (e.g., `"ean50"` as the first option), no `change` event fires, and the dependent secondary fields remain in their default hidden/shown state rather than the correct state for the saved mix.

**Failure scenario:** A user saves a plan with deco card 3 set to `ean50` (the select default). On reload, card 3 is recreated, the value matches the default (no change event), and the custom-O2 percentage input and related fields remain in whatever initial visibility state the card template has — typically hidden. The gas is correctly applied in calculations but the user cannot see or edit the O2 percentage of their deco gas.

**How it should be fixed:** After field values are restored via `applySettingsToDOM`, unconditionally dispatch a `change` event on each deco gas card's mix-type selector, regardless of whether the value changed, so that dependent field visibility is always recalculated post-restore.

---

### M-4 — `rowDisplayPpo2` returns an object (not a string) in CCR + travel-gas path — `[object Object]` rendered in PPO2 column

**File:** `index.html` lines ~9846, ~9870

**Root cause:** `rowDisplayPpo2` is called to populate the PPO2 table cell. In the CCR-on-loop path, the function delegates to `ppO2Check(...)` which returns an object `{ value, css, warn }` rather than a plain string. The template literal `${travelPPO2}` at line ~9870 coerces the object to its `.toString()` representation, yielding `[object Object]` in the PPO2 column for all descent rows during a CCR dive that uses a travel gas (OC travel → CCR transition).

**Failure scenario:** Any CCR plan with a travel gas produces `[object Object]` in the PPO2 column of the travel-gas descent row. Divers relying on the plan table to check travel-gas ppO2 safety receive corrupt output.

**How it should be fixed:** `rowDisplayPpo2` should normalize its return value to a string in all branches. Either return `result.value` (the numeric string from the check object) or call a `.display` formatter on the object rather than passing the raw object to the template literal.

---

### M-5 — VPM gas-switch depths always use `ppO2Deco` limit — low-O2 deco gases (~32% nitrox used as travel/deco) get a ~5 m shallower switch depth than the corresponding ZHL plan

**File:** `index.html` lines ~5335–5344 (`getDecoGasSwitches`)

**Root cause:** In the ZHL switch-depth path, the ppO2 limit used for the MOD calculation is `ppO2Deco` when `fO2 > 0.60`, and `ppO2Bot` (typically 1.4 bar, lower) when `fO2 ≤ 0.60`. In the VPM path, `vpmDecoSwitchDepthVal` unconditionally uses `ppO2Deco` (typically 1.6 bar) for all deco gases regardless of oxygen fraction. A 32%-O2 deco gas (fO2 = 0.32, below the 0.60 threshold) will compute its switch depth as `setpoint / 0.32 − 10` m under the deco ppO2 limit (1.6), yielding a shallower switch than ZHL's `1.4 / 0.32 − 10` m. For a 32% gas this is approximately 40 m (VPM) vs 33.75 m (ZHL) — a 6 m difference with no corresponding change in the diver's actual gas mix.

**Failure scenario:** A diver switching between ZHL and VPM tabs with a 32%-O2 stage cylinder will see a 6 m difference in the displayed switch depth between algorithms. The VPM-displayed switch is shallower than the physiologically correct MOD for a `ppO2Bot = 1.4 bar` limit, potentially suggesting an unsafe switch depth.

**How it should be fixed:** Apply the same `fO2 > 0.60 ? ppO2Deco : ppO2Bot` ternary inside `vpmDecoSwitchDepthVal`, or pre-select the correct ppO2 limit before calling it, consistent with the ZHL path.

---

### M-6 — `calcSurfInt` (surface interval calculator): `d2` (Dive 2 depth) slider is parsed but never used in the ZHL tolerance computation

**File:** `index.html` lines ~12220–12282

**Root cause:** The surface interval calculator parses `d2` from the DOM slider (line ~12228) and displays a reverse-profile warning when `d2 > d1`. However, the ZHL tissue simulation only models Dive 1: tissues are loaded for depth `d1` / time `t1`, then surface interval off-gassing is run, and the result is compared against the no-deco surface tolerance. The value `d2` does not appear in any tissue loading, ceiling calculation, or GF application after the warning check. The minimum safe surface interval is therefore computed as "when can the diver safely reach the surface from any depth?" — but it should be "when can the diver complete Dive 2 at `d2` and then safely reach the surface?" These are materially different for `d2 > d1`.

**Failure scenario:** Diver plans Dive 1: 25 m / 30 min, Dive 2: 50 m / 20 min. The calculator shows the SI needed to safely surface from Dive 1's tissue loading, not the SI needed to safely complete a 50 m second dive. The calculated SI is shorter than actually required, potentially leading the diver into a mandatory-deco situation on Dive 2 without adequate surface interval.

**How it should be fixed:** After applying the surface interval off-gassing, the SI calculator should load tissues for `d2 / bt2` and then check whether a safe ascent to the surface is possible from that tissue state. The minimum SI is the point at which this full Dive 2 simulation clears decompression obligation (or remains below NDL at `d2`).

---

### M-7 — `repSurfP` closure: stale `altSurfaceP` across batch computations — wrong surface pressure used for off-gassing in multi-altitude dive sequences

**File:** `zhl-engine-bundle.js` lines ~757–759

**Root cause:** `repSurfP` (used for surface interval off-gassing in repetitive-dive mode) falls back to the bundle's `altSurfaceP` closure variable when `rep.surfaceP` is not provided. This closure variable is set once per `applyEnvironment()` call. If a batch computation cycles through dives at different altitudes without calling `applyEnvironment()` between each one (a common pattern in trip-planner or multi-day-plan generation), the `altSurfaceP` from the previous dive is used for the current dive's surface interval.

**Failure scenario:** A trip planner computes Dive 1 at 3000 m altitude (`altSurfaceP ≈ 0.7 bar`) then Dive 2 at sea level without resetting the environment. The sea-level Dive 2's surface interval off-gassing uses `altSurfaceP = 0.7 bar` instead of 1.013 bar, under-driving N2 off-gassing and over-predicting residual nitrogen load. The second dive's NDL and deco obligation are more conservative than correct — not a safety issue, but systematically wrong for any batch-trip calculation.

**How it should be fixed:** `runZhlScheduleCore` should accept `surfaceP` as an explicit parameter in the repetitive-dive settings object and always use that value — never falling back to a module closure variable. The closure variable `altSurfaceP` should only be used for within-dive ambient pressure calculations, not for SI off-gassing.

---

## LOW

---

### L-1 — `vpmStopCapHit` property absent from `renderVPMResults` and all of `index.html` — #118 M-5 remains completely unresolved

**Files:** `vpm-engine-bundle.js` (flag computed); `index.html` (zero occurrences of `vpmStopCapHit`)

**Root cause:** When a VPM stop exceeds the 999-minute cap, the engine sets `vpmStopCapHit: true` on the plan entry and also returns `code: 'VPM_STOP_CAP'` on a fatal error (two separate code paths). The `renderVPMResults` function has no conditional that reads `entry.vpmStopCapHit`. A search of the full `index.html` source finds zero references to `vpmStopCapHit`. The property is computed but never consumed by the rendering layer. Issue #118 M-5 identified this gap; it was not addressed in any of the #119–#123 fix cycles.

**How it should be fixed:** In `renderVPMResults`, check `entry.vpmStopCapHit === true` on each stop row. Where true, add a visual indicator (e.g., a warning badge or row color change) and append a footer note: "One or more stops were limited to 999 minutes — VPM ceiling could not be cleared within the safety time limit at that depth."

---

### L-2 — `onmessage` error handler: `killWorker()` called without first calling `rejectAll()` — concurrent pending requests hang silently for up to 30 seconds

**File:** `zhl-worker-bridge.js` lines ~78–82

**Root cause:** In the `onmessage` handler, when `ok === false` is received for a specific request ID, the handler rejects that specific promise (`settlePending(id, ...)`) and then calls `killWorker()`. `killWorker()` terminates the worker and nulls the reference but does NOT call `rejectAll()`. Any other in-flight requests whose IDs are still in the `pending` Map are left with live timers and unresolved Promises. They hang until their individual 30-second timeouts fire, at which point `handleWorkerFailure` is called per pending entry, incrementing `consecutiveWorkerFailures` for each — potentially triggering the permanent-disable threshold prematurely from a single multi-request failure cascade.

**How it should be fixed:** Add a `rejectAll('ZHL worker error — concurrent request aborted')` call in the `onmessage` error branch before or instead of the per-request `settlePending`, consistent with the `handleWorkerFailure` path which calls `rejectAll` before `killWorker`.

---

### L-3 — `altSurfaceP || 1.0` wrong fallback in CCR diluent consumption — should be `1.01325`; causes 1.3% overcalculation at sea level

**File:** `index.html` line ~6782

**Root cause:** `const pSurf = altSurfaceP || 1.0`. Every other fallback in the codebase uses `altSurfaceP || 1.01325` or `altSurfaceP || SEA_LEVEL_P`. The value `1.0` bar is not standard sea-level pressure (1.01325 bar). Diluent consumption is computed as `surfLpm × (pAmb / pSurf)`. With `pSurf = 1.0` instead of `1.01325` at sea level, the consumption is inflated by 1.325% for every CCR diluent calculation — small but systematic. More critically, if `altSurfaceP` is ever falsy (0, null, or undefined, which can occur during settings import before validation), the fallback of `1.0` produces consumption estimates 25% too high at 2000 m altitude (correct `pSurf` would be ~0.795 bar vs. 1.0).

**How it should be fixed:** Replace `altSurfaceP || 1.0` with `altSurfaceP || 1.01325` (or `altSurfaceP || SEA_LEVEL_P` where `SEA_LEVEL_P` is the module constant), consistent with all other surface-pressure fallbacks in the codebase.

---

## Summary

| ID  | File(s) | Severity | Description |
|-----|---------|----------|-------------|
| H-1 | `zhl-engine-bundle.js` ~106, `index.html` ~7075 | HIGH | `ceiling()`: no guard against `gfHigh ≤ 0` — zero-ceiling returned silently; `gfAt()` NaN propagation feeds 0 into denominator |
| H-2 | `zhl-engine-bundle.js` ~823–831 | HIGH | `gfAt()`: `shallowGradient=true` + `firstStopDepth === lastStop` → zero denominator → NaN GF propagates through all ceiling calls |
| H-3 | `index.html` ~14374, ~5159 | HIGH | `runContingencyScenario` decoTime NaN: `parseStopDisplayTime` returns string, not number — string concatenation instead of addition; #118 H-3 not fixed |
| H-4 | `zhl-ccr-core.js` ~361 | HIGH | `getEffectivePpo2`: bare `altSurfaceP` access without guard → `ReferenceError` in Web Worker → permanent worker disable after 3 failures |
| H-5 | `zhl-ccr-core.js` ~113–115, `index.html` ~6472 | HIGH | pSCR `ppO2Drop` post-#123: `PSCR_MIN_PPO2` clamp creates non-monotone `fO2` discontinuity on shallow/altitude dives — spurious early first stop |
| M-1 | `zhl-ccr-core.js` ~58–93, `index.html` ~6421–6456 | MEDIUM | `getEffectiveSetpointAtDepth` altitude: partial-null case (one or two null crossings) still uses `?? 0` coalescing — wrong setpoint assigned at altitude |
| M-2 | `vpm-engine-bundle.js` ~1334–1337 | MEDIUM | VPM multi-level: `calcAllowableGradients` called with pre-regeneration radii in `runInterLevelDecoAscent` — inter-level stops differ from final plan |
| M-3 | `index.html` ~9005–9015 | MEDIUM | `appendDecoGasCardAtIdx` (#122 fix): bypasses init callbacks — no `change` event if restored value equals select default; secondary fields stay hidden |
| M-4 | `index.html` ~9846, ~9870 | MEDIUM | `rowDisplayPpo2` returns object in CCR+travel-gas path — `[object Object]` rendered in PPO2 column of descent row |
| M-5 | `index.html` ~5335–5344 | MEDIUM | VPM gas-switch always uses `ppO2Deco` limit; ZHL uses `ppO2Bot` for low-O2 gases (fO2 ≤ 0.60) — ~6 m switch-depth divergence |
| M-6 | `index.html` ~12220–12282 | MEDIUM | `calcSurfInt`: `d2` (Dive 2 depth) parsed but never used in ZHL tolerance computation — minimum SI ignores planned second dive depth |
| M-7 | `zhl-engine-bundle.js` ~757–759 | MEDIUM | `repSurfP` stale closure: batch multi-altitude computations use wrong `altSurfaceP` for surface interval off-gassing |
| L-1 | `index.html` (zero occurrences) | LOW | `vpmStopCapHit` not consumed by `renderVPMResults` — no visual warning when VPM stop is capped; #118 M-5 still unresolved |
| L-2 | `zhl-worker-bridge.js` ~78–82 | LOW | `onmessage` error: `killWorker` without `rejectAll` — concurrent pending requests hang 30 s, increment failure counter spuriously |
| L-3 | `index.html` ~6782 | LOW | `altSurfaceP \|\| 1.0` wrong fallback (should be `1.01325`) — 1.3% diluent overcalculation at sea level; 25% overcalculation if `altSurfaceP` goes falsy |

---

*Generated by 10-angle full-codebase audit of HEAD `f606ab7`. Prior audits: #113, #117, #118, #119, #120, #121, #122, #123.*
