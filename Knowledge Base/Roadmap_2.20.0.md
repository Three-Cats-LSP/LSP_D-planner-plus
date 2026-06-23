# LSP D-Planner — Roadmap to v2.20.0

**Baseline:** `v2.10.44-milestone` tag (192/192 audit checks passing)
**Status:** Planning — scoped after deep-dive verification against current `index.html`, not assumptions from prior session summaries.

---

## Important correction before this roadmap was written

Two items originally proposed for 2.20.0 turned out to already be implemented after checking the actual code (not just the comparison docs, which were stale/wrong on these two points). Recording this so we don't re-litigate it later.

### ❌ NOT a gap: Schreiner vs Haldane
LSP already uses the **true Schreiner equation** for changing-depth segments:
- `schreinerLinear()` (line ~4808, ZHL engine) — exact textbook form: `P(t) = P_i + R(t - 1/k) - (P_i - P_0 - R/k)e^{-kt}`
- `schreiner()` (line ~6608, VPM engine) — same equation, used inside `makeScheduleContext`
- Plain `saturate()` (closed-form Haldane) is correctly reserved for constant-depth segments (bottom time, stop holds) — this is the same `stagnate()`/`descend()` split AquaBSD's libbuhlmann uses, which the comparison doc called "the most clearly structured" reference implementation.

**No work item needed.** The earlier framing ("LSP uses Haldane for everything") was incorrect — likely a stale claim carried over from an old session summary that was never re-verified against the live file. There's nothing to add here, and no per-algorithm-tab "Schreiner vs Haldane" choice is needed since both are already used where each is mathematically correct.

### ❌ NOT a gap: Altitude pre-saturation toggle
Already implemented, and arguably more rigorous than MultiDeco's version:
- "Acclimatized: Yes/No" select, in the main ENV row (`acclimatizedRow`, next to Altitude), with a full tooltip explaining the Cross-correction and VPM bubble-radius scaling.
- `initTissues()` (line ~4776): Acclimatized → tissues initialize at altitude surface pressure (lower N2 load). Not acclimatized → tissues initialize at sea-level pressure (conservative, models "just arrived, still carrying sea-level N2").

**Only open question:** should this toggle move from the main ENV row into the Advanced Settings panel for consistency? This is a UI placement decision, not a feature gap — see Item 4 below for a recommendation.

---

## Update — MultiDeco binary fully obtained and independently re-verified

Roman provided the actual `MultiDeco_226.apk` and both `libmultideco.so` builds (arm64-v8a, armeabi-v7a), now in `MultiDeco Binary/` in this repo, along with two analysis docs (`MultiDeco_Engine_Full_Analysis.md`, `MultiDeco_ShallowGradient_Analysis.md`). Claude independently re-disassembled and byte-verified the contested claims directly against the binary (not by re-reading the docs) — see `MultiDeco_Verified_Findings_2_Claude.md` for full method and evidence. Two things this changes for the roadmap:

1. **Item 4 (Shallow Gradient) is now unblocked** — formula confirmed instruction-for-instruction against the real binary. See the rewritten Item 4 below.
2. **The a5=0.6491 theory for the RT/TTS gap is retired.** Both of MultiDeco's stored N2 a-tables were found and verified (`0x15d00` = "A/B" variant a5=0.6667, `0x15d80` = "C" variant a5=0.6200) — neither uses 0.6491, and the "C"/GF mode table matches LSP's existing 0.6200 exactly. This is good news (one less unexplained discrepancy) but means the `OpenSource_Deco_Libraries_2.md` batch-2 doc's categorization of MultiDeco under the "canonical Bühlmann a5=0.6491" column was incorrect and should be disregarded.
3. **New finding, not on the original roadmap:** MultiDeco's N2 and He tissue compartments use each other's half-time constants — confirmed via direct pointer-tracing through `GAS_LOADINGS_CONST_DEPTH`'s disassembly, not inference. N2 tissue loading uses canonical *He* half-times (faster), He tissue loading uses canonical *N2* half-times (slower). This looks like a genuine bug in MultiDeco, not a design choice, and would explain RT/TTS gaps specifically on trimix dives (consistent with `Subsurface_Engine_Analysis.md` already flagging He-bearing scenarios as having the largest deltas) while leaving air/nitrox-only gaps unexplained by this mechanism. **Recommendation: do not replicate this in LSP.** No action item needed beyond noting it as a resolved piece of the historical gap investigation — this doesn't require any LSP code change, since LSP already has correct N2/He half-time assignment.

---

## Item 1 — Surface GF display

**Status:** Scoped, ready to implement.

**What it is:** A read-only diagnostic metric showing how close the diver's leading tissue compartment is to the raw (GF-unmodified) M-value at surface pressure, expressed as a percentage. **It is not an algorithm input** — confirmed in `OpenSource_Deco_Libraries.md`, tl5915's `DecoResult.surfGF` is populated after the schedule is computed, purely for display.

**Formula (tl5915, confirmed correct):**
```
denom = a + (P_surface / b) - P_surface
surfGF = (tissue_load - P_surface) / denom * 100
```
Computed per-compartment at end-of-dive tissue state; report `max()` over all 16 compartments (the controlling/leading compartment), same convention as the existing Compartment Detail table's "Sat %" column (line ~2230) — in fact this is closely related to that existing column. Surface GF is essentially "Sat % of the single worst compartment, using GF=100% (no conservatism) as the reference" rather than the GF-adjusted M-value already shown there.

**Where it goes:** The results footer (`decoTotals`, line ~2148), alongside the existing TTS / CNS / OTU / PrT / Decozone / First-deco fields (see `buildExportText`-style summary at line ~4452). Also include in TXT/PDF export per the existing **export consistency rule** — any new summary field must appear in all export modes/formats, not just the live DOM.

**Acceptance:**
- New `surfaceGF` field on the result object from both ZHL and VPM engines.
- Shown in the on-screen summary footer.
- Included in TXT export, PDF export (deco mode), and Messenger-text export.
- Audit check: confirm `surfaceGF` is present and a number 0–~150% on a representative dive.

---

## Item 2 — CNS/OTU dual-method audit

**Status:** Needs verification, not "implementation" — the two existing methods may already agree, this is about confirming it and documenting which is authoritative.

**What was found:** Two independent CNS computation paths exist:
1. **VPM engine scope** (line ~7085): `CNS_RATE_ANDROID`, a 131-point Android-dive-computer-style instantaneous rate table, accumulated via `calculateCNS(ppO2, time)`.
2. **ZHL/display scope** (line ~8848): `rowCNS()` / `segCNSfrac()`, an 11-point NOAA single-dive CNS-limit table, used for the deco table's per-row CNS% column.

These are two legitimate, different CNS methodologies (rate-accumulation vs limit-interpolation) and they're scoped to different algorithm tabs (VPM vs ZHL), so this is not necessarily a bug — but nobody has verified they produce consistent CNS% for the same ppO2/duration input, and a diver switching between the ZHL and VPM tabs on the same profile shouldn't see materially different CNS%.

**Task:**
1. Write a test harness that feeds identical ppO2/duration pairs through `calculateCNS()`/`getCNSRate()` and `rowCNS()`/`segCNSfrac()` across the full ppO2 range (0.5–1.8 bar) and diffs the output.
2. If they diverge meaningfully, decide on one authoritative table (the 131-point table is more granular and matches what most real dive computers ship — likely the better candidate) and use it in both places.
3. Confirm OTU is consistent too — both `calculateOTU()` (VPM scope) and `segOTU()` (ZHL scope) use the same NOAA formula (`time * ((ppO2-0.5)/0.5)^0.833` vs `^0.8333` — note the exponent differs in the 4th decimal between the two copies in the file, worth normalizing to one constant).
4. Add audit checks (new GROUP) once the authoritative method is confirmed/fixed, to catch future drift between the two CNS/OTU copies.

**Acceptance:** Single source of truth for CNS rate table and OTU exponent constant, referenced from both engine scopes, with a regression test proving ZHL-tab and VPM-tab CNS% match for identical ppO2/duration inputs.

---

## Item 3 — Multi-day residual loading ("Last Dive" / surface interval in dd/hh:mm)

**Status:** Real, scoped gap. New item added per Roman's request.

**What exists today:**
- VPM engine has a single repetitive-dive carry mechanism (`vpmRepMode` checkbox + `vpmSurfaceInterval` numeric minutes input, max 10080 = 7 days expressed awkwardly as raw minutes). Carries: N2/He tissue state, VPM bubble state (critical radii), CNS (90-min half-life decay — correct), OTU (carried with **no decay or day-boundary reset** — this is the actual bug-shaped gap).
- ZHL engine has **no repetitive-dive carry at all** — its "Surface Interval" feature (line ~2785) is a one-way calculator ("how long until I *can* dive again"), not a state-carry mechanism like VPM's.
- Everything is keyed to a single prior dive. There's no concept of a multi-day dive trip history (e.g. "day 4 of a liveaboard, last dive ended 14h22m ago").

**What MultiDeco/dive computers do that LSP doesn't:** track elapsed real time since the last dive in a human dd/hh:mm format, and use that to determine:
- Residual N2/He loading (already physically correct in LSP's math — the gap is purely the *input format and multi-day framing*, not the underlying Haldane offgassing math, which already handles arbitrarily long surface intervals correctly via `Math.exp(-k * si)`)
- Whether CNS has fully decayed (at 90-min half-life, ~9 hours ≈ 6 half-lives ≈ <2% residual — effectively zero for any interval beyond ~12h, so this is mostly about *not having to know that*, the UI should just handle it)
- Whether OTU should reset (daily-dose model — should reset at a real calendar-day boundary, not carry indefinitely as it does today)

**Proposed scope for 2.20.0:**
1. Replace the single `vpmSurfaceInterval` minutes-only input with a `dd/hh:mm` formatted "Last Dive" input (e.g. `02/14:30` = 2 days, 14 hours, 30 minutes since last dive surfaced). Parse to total minutes internally — the existing tissue-offgassing math (`Math.exp(-kN2 * settings._surfaceInterval)`) needs no change, since it already correctly handles arbitrarily large `si` values; this is purely an input-format and OTU-reset fix.
2. Fix OTU carry: if elapsed time crosses a real day boundary (>24h, or per a configurable "OTU day" convention — confirm whether NOAA defines this as calendar day or rolling 24h window before implementing), reset `_preOTU` to 0 instead of carrying forward unconditionally.
3. At 5+ days (or some explicit threshold — confirm a sensible value, e.g. when N2 in the slowest compartment (635 min half-time) has decayed to <1% above baseline, which is ~10 half-lives ≈ 4.4 days), treat the diver as "fully clean" — this may already fall out naturally from the existing exponential decay math once arbitrary multi-day `si` values can actually be entered; verify rather than special-case it.
4. Decide whether to extend this same carry mechanism to the **ZHL engine** (currently VPM-only) — recommend yes, for parity between the two algorithm tabs, since residual N2 loading is policy-relevant regardless of which model the diver is planning with.
5. Update the repetitive-dive badge/tooltip (line ~6321) to show the parsed dd/hh:mm rather than just raw minutes.

**Acceptance:**
- `dd/hh:mm` input parses correctly (including edge cases: `00/00:30`, `05/00:00`, single-digit days).
- OTU resets correctly across a day boundary; does not reset spuriously within a day.
- ZHL engine gains the same repetitive carry VPM already has, or an explicit documented decision for why not.
- Existing VPM repetitive dive tests (tissue/bubble carry) still pass unchanged — this is additive, not a rewrite of the carry math itself.

---

## Item 4 — Shallow Gradient (MultiDeco proprietary feature)

**Status:** Unblocked. Formula confirmed via direct ARM64 disassembly of the real binary, independently re-verified instruction-for-instruction by Claude (not just transcribed from the original analysis doc). Ready to scope an implementation.

**What it actually is (confirmed, not symbol-name guesswork):** Shallow Gradient is **not** an additional conservatism layer on the ceiling itself — the GF-derived ceiling is unchanged. It's a stop-scheduling smoothness adjustment with two independent triggers, both of which set a single `Apply_Shallow_Grad` flag:

**Trigger 1 — tissue-loading ratio** (`ShallowGradDepthTest`, confirmed at binary address `0x3251c`):
```
ratio = mean(N2_Press[i] - He_Press[i], i=0..15) / 32.0 / first_stop_depth_bar
Apply_Shallow_Grad = (ratio > 0.40)
if Apply_Shallow_Grad:
    Shallow_Grad_Max_ATA_Factor = min((ratio - 0.40) * 10.0, 1.0)   // 0→1 as ratio goes 0.40→0.50
```
Also applies a Boyle's Law compensation call (`BOYLES_LAW_COMPENSATION(depth/3, depth/3)`) as a side effect before computing the ratio — this dependency is itself a separate, already-disassembled function (`0x342ac`) if exact parity is wanted, though it's plausible the Boyle's-law call matters more for the VPM-B path than the ratio computation itself; needs a decision on whether to port it or treat the ratio check as Bühlmann/GF-only.

**Trigger 2 — stop-time-based** (`ShallowGradTimeTest`, confirmed at `0x35710`):
```
Apply_Shallow_Grad |= (current_stop_time_min > 60.0)
if overtime:
    Shallow_Grad_Time_Factor = min((current_stop_time_min - 60.0) * 0.05, 1.0)  // 0→1 as time goes 60→80 min
```

**Effect when active** (in `DECOMPRESS_STOP`): bypasses a fractional ceiling-to-stop-depth snap-extension check — when the computed ceiling falls awkwardly between two standard stop depths, the algorithm normally adds an extra rounding cycle; Shallow Gradient skips that check. **Net effect is usually a slightly shorter or smoother shallow-stop schedule, not a longer one** — this corrects an earlier assumption (carried in `MultiDeco_ShallowGradient_Analysis.md`'s own framing and in this roadmap's first draft) that the feature adds conservatism. It does the opposite in the common case.

**Confirmed constants (independently re-verified against raw binary bytes by Claude, not just transcribed):**
- Ratio threshold: `0.40` (rodata, confirmed)
- Ratio-to-factor scale: `×10`, capped at `1.0`
- Time threshold: `60.0` minutes (confirmed)
- Time-to-factor scale: `×0.05`, capped at `1.0` (reaches cap at 80 min)

**Proposed scope for 2.20.0:**
1. Implement the ratio-trigger and time-trigger as a single `shouldApplyShallowGrad(tissues, firstStopDepthBar, currentStopTimeMin)` helper in LSP's ZHL engine, following the LSP convention of pure functions operating on the existing `tissues` array shape (no need for the `Apply_Shallow_Grad` global flag pattern — keep it functional).
2. Implement the bypass effect: in LSP's own stop-time loop, identify the equivalent fractional-rounding logic (if LSP has one — needs a code-read first, since LSP's stop loop architecture differs from MultiDeco's; this may be a no-op if LSP doesn't have an equivalent snap-extension check to begin with, in which case the toggle would have no effect and that should be stated plainly in the tooltip rather than silently doing nothing).
3. Advanced Settings toggle, **off by default**, named clearly as MultiDeco-compatible behavior (not a Bühlmann/VPM-B standard feature), consistent with the existing "MultiDeco compatible" labeling pattern already used for Transit Mode / Stop Rounding.
4. Decide on the Boyle's Law compensation dependency (open question above) before finalizing — may be VPM-B-only in practice, which would simplify the Bühlmann/GF-mode implementation to just the ratio/time triggers with no Boyle's-law side effect.

**Acceptance:**
- New toggle in Advanced Settings, off by default, with tooltip stating plainly what it does (smooths/shortens shallow stops under high tissue loading or long stop times) and that it's MultiDeco-specific behavior, not a standard algorithm feature.
- Audit check confirming the toggle defaults to off and that enabling it only affects shallow-stop rounding, not the underlying ceiling.
- Regression test on at least one scenario from the existing cross-reference suite where the ratio trigger is expected to activate (a long/deep dive with high tissue loading relative to first-stop depth — S6 or A2 from the existing 21-scenario suite are good candidates given their already-large MultiDeco deltas) to confirm the toggle moves LSP's output in the expected direction (shorter/smoother, not longer).

---

## Item 5 — Emergency Contingency: went deeper than planned (+3m / +5m)

**Status:** Scoped, small, ready to implement. Fits naturally into the existing contingency mechanism.

**What exists today:** The Contingency Plans card already has two independent scenario axes — Gas Loss (buttons: None / Lose Gas 1 / Lose Gas 2 / Lose Both) and Extended Bottom Time (buttons: +3 / +5 / +10 min). These combine: you can select a gas loss *and* extra BT simultaneously, and `calcContingency()` re-runs the engine with both modifications applied before restoring the original values.

The implementation pattern is clean and already confirmed in the code (`calcContingency()`, line ~13685): the function saves the original form values, temporarily mutates them (e.g. `decoBT += contExtraBT`), calls `runContingencyScenario()`, then restores. A depth scenario is exactly the same pattern — temporarily set `decoDepth += extraDepth`, run, restore.

**What's being added:** A third scenario axis: **went deeper** — +3m or +5m beyond the planned bottom depth. Same combinations apply: can be selected simultaneously with gas loss and/or extended BT (e.g. "lost deco gas 1 AND went 5m deeper AND ran 5 minutes long" as a worst-case combined scenario).

**UI:** A new row in the contingency panel, directly below Extended Bottom Time, styled consistently with the existing two rows:

```
⬇️ Went Deeper
[ None ] [ +3m ] [ +5m ]
```

**Implementation:** Add `contExtraDepth` state variable (mirrors existing `contExtraBT`). In `calcContingency()`:
```js
const origDepth = document.getElementById('decoDepth')?.value;
// ...in scenario mutation block:
if (contExtraDepth > 0 && origDepth)
  document.getElementById('decoDepth').value = parseFloat(origDepth) + contExtraDepth;
// ...restore block:
if (origDepth) document.getElementById('decoDepth').value = origDepth;
```

The scenario label generator (the `parts.push(...)` chain in `calcContingency()`) needs a `contExtraDepth` entry, e.g. `"+5m depth"`. The severity/icon logic should treat extra depth the same as extra BT (warning-level, not emergency-level unless combined with gas loss).

**Export consistency rule applies:** The "Went deeper" label must appear in the emergency plan's scenario header across all export formats that currently show the contingency label (TXT, PDF, Messenger) — same as BT and gas-loss labels already do.

**Acceptance:**
- New "Went Deeper" row with None/+3m/+5m buttons, consistently styled, combinable with gas loss and extended BT.
- Selecting +3m or +5m and calculating produces a correct schedule at the modified depth, with tissue loading and ceiling computed from the deeper profile.
- Scenario label in results and exports correctly shows the depth change (e.g. "Lost EAN50 and +5m depth and +5 min BT").
- `selectContDepth(0)` called on plan recalculation (same pattern as `selectContBT(0)` and `selectContGas('none', ...)` in `buildContingencyButtons()`).
- Audit check confirming `contExtraDepth` resets to 0 on main plan recalc.

---

## Item 6 — Advanced Settings profiles: save/load, plus pre-built app-default presets

**Status:** Scoped, ready to implement. Builds directly on an existing mechanism rather than introducing new architecture.

**Preset list (per Roman's decision):** MultiDeco, Abysner, Subsurface, GUE DecPlanner, DiveKit, and LSP's own defaults. **ApexDeco intentionally excluded** — LSP is itself an ApexDeco-line app, so an "ApexDeco preset" would be redundant with LSP's own defaults rather than offering a genuinely different reference point.

**What exists today:** `appSettings` (line ~15717) already has exactly the right shape for this — `DECO_FIELDS` is a maintained list of every relevant setting's element ID, and `save()`/`load()` already serialize all of them to/from a single `localStorage` slot (`lspDiveSettings_v6`) as one JSON blob. This is a single implicit "current settings" slot, not a named multi-profile system — that's the actual gap.

**What's being added:**
1. **Named user profiles:** instead of one implicit slot, support N named profiles (e.g. "My Cave Setup", "Conservative Travel"), each storing the same field set `DECO_FIELDS` already tracks. Store as `lspDiveProfiles_v1: { profileName: { ...fields }, ... }` alongside (not replacing) the existing auto-save slot, which continues to behave as "last used settings" exactly as today. Add Save/Load/Delete/Rename UI in the Advanced Settings panel — a profile selector dropdown plus "Save as new profile" / "Save changes to current profile" / "Load" / "Delete" actions.
2. **Pre-built app-default presets:** a fixed, non-editable set of "load these values" buttons, one per reference app already studied, populating the *same* `DECO_FIELDS` that user profiles use — selecting one just pre-fills the form, exactly like loading a user profile, and the diver can then tweak and optionally save their own variant from there. Confirmed default values to seed each preset (already documented in the knowledge base, not invented for this item):

| Setting | LSP (current default) | MultiDeco | Abysner | Subsurface | GUE DecPlanner | DiveKit |
|---|---|---|---|---|---|---|
| GF Low | 40 (confirmed: `gfLowInput` selected option) | 30 | 60 | 30 (confirmed: `subsurface_engine.py` `dive.get('gfLow', 30)`) | 20 (OC) | **50** (confirmed: JS bundle `gfLow: 50`) |
| GF High | 80 (confirmed: `gfHighInput` selected option) | 85 | 70 | 70 (confirmed: `dive.get('gfHigh', 70)`) | 85 (OC) | **80** (confirmed: `gfHigh: 80`) |
| Descent rate | 20 m/min | **22 mpm** (confirmed via screenshot, MultiDeco config screen) | 20 m/min | 20 m/min (confirmed, `Subsurface_Engine_Analysis.md` line 186) | 20 m/min | 20 m/min (confirmed: `descentRate: 20`) |
| Ascent rate | 10 m/min | **Three-tier**: Surface/Deco/Ascent all **9 mpm** (confirmed via screenshot) | 5 m/min | **Three-tier**: 9 m/min deep / 6 m/min between stops / 3 m/min last 3m (confirmed) | 9 m/min | **Two-tier**: 9 m/min deep / 3 m/min shallow, split at 6m (confirmed: `ascentRateDeep: 9, ascentRateShallow: 3, ascentRateChangeDepth: 6`) |
| Deco step size | 3 m | (smallest index, ~1m / 3.3ft) | 3 m | 3 m (confirmed) | 3 m | 3 m (confirmed: `decoStepSize: 3`) |
| Last deco stop | 3 m | ~3 m (10 ft) | 3 m | 3 m (confirmed) | 3 m | **6 m** (confirmed: `lastStopDepth: 6`) |
| Min stop time | 2 min (confirmed: `minStopTime` selected option) | n/a documented | 1 min | 1 min (confirmed) | 1 min | 1 min (confirmed: whole-minute planning, 1 min minimum stop per Abysner design) |
| Max ppO2 (bottom) | 1.4 bar (confirmed: `ppo2Bottom` selected option) | n/a (deco-only table documented) | 1.4 bar | 1.4 bar (confirmed: `max_ppo2_for()`, ≤22% O2) | 1.2 bar | 1.4 bar (confirmed: `maxPO2Lean: 1.4`) |
| Max ppO2 (deco) | 1.6 bar (confirmed: `ppo2Deco` selected option) | 1.6 ata | 1.6 bar | 1.6 bar (confirmed: `max_ppo2_for()`, >22% O2) | 1.2 bar (deco) / 1.5 bar (Max O2) | 1.6 bar (confirmed: `maxPO2Rich: 1.6`) |

   **DiveKit notes:** All DiveKit values sourced directly from the JS bundle default settings object in `Divekit_Analysis.md` (confirmed from v2.8.5 bytecode, not inferred). Key differences vs Abysner (its upstream): DiveKit ships GF 50/80 (Abysner ships 60/70), last stop 6m (Abysner: 3m), and a two-tier split ascent rate at 6m changepoint (Abysner: flat 5 m/min). **Last stop 6m confirmed present** in LSP's `lastDecoStop` dropdown (options: 6m / 3m [default] / 1m — verified from live markup). DiveKit's two-tier ascent (9 deep / 3 shallow, split at 6m) maps onto LSP's fields as: `ascentRate=9, surfaceAscentRate=3` — the 6m split depth is hardcoded in both DiveKit and Abysner, so no new LSP field needed for this specifically. The `decoAscentRate` field defaults to 9 (same as `ascentRate`) for DiveKit since no separate between-stops rate is specified.

   **Correction (screenshot evidence, supersedes earlier static-analysis inference):** Roman provided an actual screenshot of MultiDeco's "Descent / ascent rates" config screen. It shows **four independently adjustable rate fields** — Descent (22 mpm default), Surface (9 mpm), Deco (9 mpm), and Ascent (9 mpm) — confirming MultiDeco's ascent-phase rate structure is three-tier like Subsurface's, not the single value `MultiDeco_GUI_Planner_Analysis.md` §11 implied (`rateValue(7, false)` = 15 ft/min ≈ 4.6 m/min, sourced from a single `ascent` field in the decompiled `Settings.java`). That doc's table only captured one `ascent`/`descent` pair of settings fields — either the jadx decompile missed the other two rate fields, or they're named differently than expected in the Java source. **Action for whoever implements this preset:** don't trust `MultiDeco_GUI_Planner_Analysis.md`'s single ascent-rate value; use this screenshot-confirmed structure instead (Descent 22 mpm; Surface/Deco/Ascent all 9 mpm by default, each independently editable in the real app). Worth a follow-up read of the decompiled `Settings.java` to find the other two rate fields and correct that doc directly, since this is the second time a MultiDeco doc's table has needed a correction from independent evidence — not urgent enough to block this item, but good hygiene before relying on that doc's other settings-table rows uncritically.

   **One open design question this raises:** Subsurface's ascent rate is genuinely three separate values (deep/between-stops/last-stop-segment), not the single `ascentRate` value LSP's current UI model assumes. LSP does already have separate `ascentRate` / `decoAscentRate` / `surfaceAscentRate` fields (confirmed in `DECO_FIELDS`, all three already exist in the UI) — so this is actually a clean three-way mapping, not a gap, but worth calling out explicitly so whoever implements this doesn't assume Subsurface only has one ascent-rate value to copy. **The same now applies to MultiDeco's preset, given the screenshot correction above** — its Surface/Deco/Ascent fields map onto LSP's `surfaceAscentRate`/`decoAscentRate`/`ascentRate` the same way Subsurface's three tiers do, and at 9 mpm flat across all three, MultiDeco's mapping is actually simpler than Subsurface's (no per-tier value differences to reconcile).

   **This table still needs one more verification pass before implementation** — exact metric conversions for any remaining imperial-sourced values should be recomputed precisely. LSP's own current defaults (descent/ascent/step/last-stop/min-stop/ppO2) are now all confirmed directly from the live `<select>` markup; GF Low/High were also just confirmed (40/80) and should replace any stale "Lo=30/Hi=85" reference elsewhere in this knowledge base that was actually describing MultiDeco's (or, as it turns out, Subsurface's — they happen to share the same GF Low default) defaults, not LSP's — worth a search-and-check across other docs for this mix-up before this item ships.
3. **Known constraint to design around:** several of these settings are `<select>` dropdowns with a *fixed* list of options (e.g. `ascentRate` only offers 3/6/9/10/12/15/18 m/min), not free-text numeric inputs. A reference app's exact default may not exist as an option. Decide per-field whether to (a) snap to the nearest existing option, (b) add the missing option to the dropdown itself if it's a value worth offering generally, or (c) convert affected fields to free-text numeric inputs. Recommend (b) where the missing value is a reasonable thing to offer generally — note that **none of the four presets need any snapping at all for descent or ascent rate**: confirmed live `descentRate` options are 10/15/18/20/22/25/30 m/min (22 already present for MultiDeco), and 9/6/3 m/min are all already valid options in LSP's three existing ascent-rate dropdowns (covering Subsurface's three tiers and MultiDeco's flat-9 default across all three). GUE's GF Low of 20 is also confirmed present in the live `gfLowInput` options list. So far every value across all four presets lands on an existing option — if any snapping case turns up once the rest of the table is double-checked, apply (a) and document it, since "preset says one thing, loaded value is slightly different" needs a clear UI explanation (e.g. a small note "(rounded to nearest available value)") rather than silently snapping.
4. **Tooltip/labeling:** each preset button should be labeled by app name and have a tooltip noting it's an approximation of that app's *defaults*, not a guarantee of identical computed results (the underlying algorithm differences documented elsewhere in this knowledge base, e.g. MultiDeco's N2/He half-time swap, mean two apps with "the same settings" can still produce different schedules) — avoid implying these presets make LSP compute identically to the named competitor.

**Where it goes:** New subsection within the existing Advanced Settings panel (`advancedSettingsBody`, line ~1757) — a "Settings Profiles" group, likely near the top of the panel given it can replace everything below it.

**Acceptance:**
- User can save current Advanced Settings as a named profile, reload it later, and delete/rename it.
- All five app-default presets (MultiDeco, Abysner, Subsurface, GUE DecPlanner, DiveKit) load correctly with verified-accurate values, including DiveKit's last stop 6m and two-tier ascent rate, Subsurface's three-tier ascent (9/6/3 m/min) and MultiDeco's flat three-tier (9/9/9 m/min), all mapped onto LSP's three existing ascent-rate fields.
- Loading any preset does not silently fail on fields where the target value isn't an available dropdown option — it either snaps with a visible note, or the dropdown gains the option.
- Existing single-slot auto-save/auto-load behavior (today's `appSettings.save()`/`.load()`) is unchanged for anyone not using the new named-profile UI — this is additive.
- Audit check confirming the new `lspDiveProfiles_v1` storage key round-trips correctly (save → reload page → load → values match).

---

## Suggested implementation order for 2.20.0

1. **Item 1 (Surface GF)** — smallest, self-contained, no architectural decisions pending.
2. **Item 2 (CNS/OTU audit)** — should happen before Item 3, since Item 3's OTU-reset fix depends on knowing which OTU formula is authoritative.
3. **Item 3 (Last Dive dd/hh:mm + OTU day-boundary fix)** — the most user-facing win Roman specifically asked for.
4. **Item 5 (Emergency: went deeper)** — tiny, self-contained, fits the existing contingency pattern exactly. Can be done any time.
5. **Item 6 (Settings profiles)** — straightforward extension of an existing mechanism (`appSettings`), no dependency on anything else in this list.
6. **Item 4 (Shallow Gradient)** — unblocked (formula confirmed against the real binary). Needs one design decision before starting (the Boyle's Law compensation dependency) plus a code-read of LSP's existing stop-time loop.

Each item gets its own audit GROUP and CHANGELOG entry per existing project convention. Run the full `tests-massive.html` / `tests-massive-main.html` / `tests-verify.html` suite after each item, not just `audit.py`.

---

## Deferred to v2.25.0 — Multi-level dive profile support

**Deferred per Roman's decision:** multi-level is a full engine/UI overhaul that would dominate the 2.20.0 release and delay everything else. Targeted for v2.25.0 as its own milestone.

**What exists today:** LSP's entire planning pipeline is single-level — `decoDepth` (a single numeric field) drives one descent→bottom→ascent schedule. Multi-level dives today have to be approximated by running LSP multiple times, which doesn't correctly track tissue loading across level transitions.

**What's needed when picking this up:**
1. **Input model:** replace the single depth/time pair with an ordered segment list. UI needs an "Add Level" affordance. Gas-per-segment is a related-but-separable concern — decide whether to scope together or defer gas-switching-between-levels to later.
2. **Engine driving loop:** the underlying Schreiner/Haldane physics already handles multi-segment correctly (each level transition is another Schreiner depth change + Haldane constant-depth hold). The work is in `runDecoSchedule()`'s control flow, which currently assumes a single bottom phase. Read that function end-to-end first before estimating effort.
3. **TTS worst-point:** compute TTS at every segment boundary (Abysner's approach), not just end-of-bottom-time. Catches cases where a shallower-but-longer trailing segment accumulates more deco obligation than the deep phase.
4. **Result display and exports:** row-type system, profile graph, TXT/PDF/Messenger all need to reflect multi-segment structure.
5. **Backward compat:** existing single-level saved dives must behave identically (default to 1 segment).

**Strongly recommended first step:** read `runDecoSchedule()` end-to-end and write a short breakdown of which parts assume single-level vs which are already segment-agnostic, before writing any code. Don't estimate effort from this doc alone.

**Acceptance (when it ships):** 2+ segment plans with correct continuous tissue loading, TTS worst-point per boundary, zero behavior change for existing single-level users, all three test suites pass plus new multi-level test cases.

---

## Deferred to v2.30+ — CCR/SCR support

Explicitly deferred to a future version (2.30+ or later) per Roman's instruction. For when it is picked up, the formula is already verified and ready from `OpenSource_Deco_Libraries.md` (tl5915):
```
pN2_alv = P_amb - ppO2_setpoint - WATER_VAPOR   (CCR mode)
```
and MultiDeco's full CCR/SCR/bailout symbol set is documented in `APK_Reverse_Engineering.md` for reference (`CALC_O2_LOADINGS_CLOSED`, `SCRO2Drop`, `ppO2Above/Below/Deep/ReallyDeep/Swaps`, etc.) if/when this is picked back up. DiveKit's CCR implementation (`Buhlmann.kt` / `BuhlmannUtilities.kt` CCR Schreiner path, segment-split-at-setpoint logic) is now also available in Abysner open source as a clean reference implementation.
