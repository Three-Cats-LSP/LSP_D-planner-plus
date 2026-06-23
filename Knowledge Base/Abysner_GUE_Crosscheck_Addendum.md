# Addendum — Abysner & GUE DecPlanner Cross-Checks

**Date:** June 2026
**Purpose:** Three independent cross-checks have now landed on the same finding from
different angles. This doc ties them together, flags one labeling error that hasn't
been corrected yet, and notes one possible future enhancement spotted along the way.
No LSP code changes result from this doc — it's a synthesis note for the knowledge base.

---

## 1. MultiDeco's N2/He half-time swap — now confirmed by 3 independent sources

| Source | Method | Finding |
|---|---|---|
| Claude, direct binary disassembly (`MultiDeco_Verified_Findings_2_Claude.md`) | Pointer-traced `GAS_LOADINGS_CONST_DEPTH` in the actual `.so`, independently re-extracted every byte | `0x15c00` (feeds `pN2_tissue`) holds canonical **He** half-times; `0x15c80` (feeds `pHe_tissue`) holds canonical **N2** half-times |
| Abysner (`Abysner_Analysis.md`, §10) | Reading Abysner's own open Kotlin source and comparing its standard tables against MultiDeco's documented behavior | "MultiDeco uses a non-standard N2 halftime set derived from He halftimes via the diffusion ratio (×2.6595). Abysner uses the canonical published N2 halftimes." |
| GUE DecPlanner (`GUE_DecPlanner_Analysis.md`, §11) | Reading GUE's open (unminified-after-beautify) JS source tables | "MultiDeco uses custom non-standard halftimes; all others use standard published values" |

All three arrived at the same conclusion independently, using three different methods
(native ARM64 disassembly, reading one open-source competitor's Kotlin, reading another
open-source-engine competitor's JS). This is now well-triangulated, not a single-source
claim. **Standing recommendation unchanged: LSP should not replicate this.** It's the
most likely explanation for RT/TTS gaps specifically on trimix/He-bearing scenarios in
the cross-reference suite, and does not touch air/nitrox-only gaps.

No further verification work is needed on this specific point — consider it closed.

---

## 2. Column-label error in `GUE_DecPlanner_Analysis.md` §4.2 — not yet corrected

**The error:** Section 4.2's coefficient table is headed `[He_t½, N2_t½, aN2 (bar), bN2,
aHe (bar), bHe]`, but the values listed under the **"aN2"** column are actually the
canonical **He** a-values, and the values under **"aHe"** are actually the canonical
**N2** a-values. The header and the data are swapped relative to each other.

**Verification (independent, this session):**
```python
# Values the doc lists under "aN2": 16.189, 13.83, 11.919, 10.458, 9.220, 8.205, 7.305, 6.502...
# These exactly match canonical ZHL-16C He a-values x10 (Baker): 1.6189, 1.383, 1.1919...x10
# Confirmed against MultiDeco's own 0x15e00 table (verified in MultiDeco_Verified_Findings_2_Claude.md)

# Values the doc lists under "aHe": 11.696, 10.0, 8.618, 7.562, 6.200, 5.043, 4.410, 4.000...
# These exactly match canonical ZHL-16C N2 a-values x10, "C" variant (a5=0.62): 1.1696, 1.0, 0.8618...
# Confirmed against MultiDeco's own 0x15d80 table
```
Both columns' *numbers* are fine and match the cross-app consensus (the same a5=0.6200
value the rest of the analysis correctly highlights as the shared ZHL-16C variant) — it's
specifically the **header-to-column mapping** that's backwards. This is the same class
of mistake as the false-positive a5 reading at `0x16230` corrected in
`MultiDeco_Verified_Findings_2_Claude.md` — easy to make when transcribing wide tables
by hand, doesn't affect any conclusion drawn elsewhere in the doc (the rest of
`GUE_DecPlanner_Analysis.md`, including §4.2's own "critical finding" callout about
comp 5 = 6.200, and the cross-application comparison tables in §11, all use the correct
values under correct labels — only the §4.2 table header row itself is swapped).

**Action:** None needed for LSP — this doesn't touch any LSP code path. Flagging here so
whoever next references `GUE_DecPlanner_Analysis.md` §4.2 directly doesn't propagate the
swapped header. Worth a one-line fix to that doc's table header next time it's open for
edits, but not urgent enough to justify a standalone commit on its own.

---

## 3. Possible future enhancement (not scoped, not urgent) — TTS worst-point check

`Abysner_Analysis.md` §8 describes Abysner's reserve-gas algorithm: rather than assuming
the worst point for time-to-surface is always end-of-bottom-time, it computes TTS at
**every segment boundary** and takes the maximum. This correctly catches multi-level
profiles where a shallower-but-longer section accumulates more deco obligation than the
deep portion — a case where "TTS at end of bottom time" alone would under-report the
true reserve-gas requirement.

This is **not** added to the v2.20.0 roadmap and isn't urgent — LSP's current multi-level
profile support is itself deferred (per the existing roadmap), so this enhancement has
no LSP scenario to apply to yet. Worth keeping in mind once multi-level profiles are
picked back up: when that happens, "where is TTS evaluated" should be reconsidered
alongside it rather than assuming end-of-bottom-time is always the worst point. No
action item created for this session — just a flag for future reference.

---

## Net effect on the v2.20.0 roadmap

None of the above changes any roadmap item's scope or status. This addendum exists to:
1. Close out the half-time investigation with triangulated confidence (item 1).
2. Prevent a documentation error from propagating (item 2).
3. Leave a breadcrumb for future multi-level-profile work (item 3).

See `Roadmap_2.20.0.md` for the actual implementation plan; see
`MultiDeco_Verified_Findings_2_Claude.md` for the primary binary-verification evidence
this addendum builds on.
