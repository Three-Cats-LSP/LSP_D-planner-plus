# DiveKit Deco Engine — Knowledge Base for LSP D-Planner

**Source:** https://divekit.app/docs/ (studied June 2026)  
**Primary comparison:** https://divekit.app/docs/engine/compared-to-multideco/  
**Cross-reference JSON (local copy):** `divekit-cross-reference/` in this folder

DiveKit is a commercial mobile **Bühlmann ZH-L16C + GF** planner cross-validated against **MultiDeco** across **26 published scenarios**. Their documentation explains every modeling choice; differences from MultiDeco are documented openly; full inputs and both engines' outputs are published as JSON for reproducibility.

---

## Cross-reference dataset

| File | Contents |
|------|----------|
| `inputs.json` | 26 dive scenarios (depth, BT, gases, GF, water type, etc.) |
| `divekit-results.json` | DiveKit engine output per scenario |
| `multideco-results.json` | MultiDeco output per scenario |
| `notes.json` | Per-scenario commentary on where/why engines diverge |

Download originals: https://divekit.app/data/cross-reference/

Use this dataset for 3-way LSP vs MultiDeco vs DiveKit regression runs. LSP fixes in v2.10.7–v2.10.12 were driven largely by this comparison.

---

## Where MultiDeco and DiveKit agree

- **Gas switch depths** — EAN50 @ 21 m, O₂ @ 6 m match exactly on standard profiles
- **Decozone start** — within ~one 3 m step on 25/26 scenarios (after LSP `ambientCrossingDepth` fix)
- **CNS/OTU and TTS** — within a few percent / few minutes on most air and nitrox dives
- **CCR loop deco** — oxygen clocks within ~1–2%

---

## Documented differences (not bugs)

### Stop distribution on deep trimix

On deep helium dives, **first mandatory stop depth** can differ by 1–4 steps between MultiDeco and DiveKit. DiveKit documents this as **continuous tissue recompute during ascent**: helium off-gasses faster in tissue than the diver climbs on some profiles. LSP ZHL+GF behaviour after v2.10.9 matches DiveKit on air/nitrox first stops; trimix may land shallower than MultiDeco in the same way DiveKit does.

### GF and decozone

**Gradient factors move the M-value line, not the ambient line.** The decozone (ambient-crossing depth) must be **GF-independent** for the same physical dive. LSP incorrectly aliased decozone to `firstStopDepth` until v2.10.10; fixed with `ambientCrossingDepth(tissues)`.

### GF Low vs GF High for first stop

Per Baker's GF algorithm and DAN descriptions: **GF Low determines the first stop**; GF High bounds the surface approach. LSP v2.10.7 briefly used GF High pre-anchor (`gfAt()` regression in v2.10.7→2.10.9), which skipped mandatory stops — fixed in v2.10.9.

### Integration timestep

DiveKit uses **1-second** Schreiner integration. MultiDeco uses coarser steps in places. Small RT/TTS differences at stop boundaries are expected.

### Water vapor

MultiDeco default: **0.0577 bar**. Bühlmann canonical: **0.0627 bar**. LSP defaults to 0.0577 for MultiDeco alignment; user-configurable.

### Salt water pressure

Industry / MultiDeco / DiveKit / ApexDeco standard: **10.000 m/bar** (`0.10000 bar/m`). LSP aligned in v2.10.4–v2.10.5 (was split between ZHL 9.980 and VPM 10.078).

---

## LSP settings to match MultiDeco output

| Setting | MultiDeco-aligned value |
|---------|-------------------------|
| Transit Mode | MultiDeco compatible |
| Stop Rounding | Yes (whole minute) |
| Water Vapor | 0.0577 bar |
| Water Type | Salt (10.000 m/bar) |
| He HT Comp 1 | Baker 1.88 min (VPM-B) |

For **ApexDeco**-style fractional output: Schreiner transit + fractional stops + 0.0627 bar.

---

## LSP intentional differences from ApexDeco / MultiDeco

| Topic | LSP default | Match ApexDeco strict |
|-------|-------------|------------------------|
| O₂ @ 6 m | Allow at MOD (1.608 bar accepted) | Strict ppO₂ toggle |
| Stop rounding | Whole minute (MultiDeco) | Fractional |
| Transit | MultiDeco compatible | Schreiner |

---

## Key metrics (MultiDeco / DiveKit / LSP)

| Metric | Definition |
|--------|------------|
| **Run time (RT)** | Descent + bottom + ascent + deco |
| **Deco time** | Time at mandatory stops only |
| **TTS** | Time to surface = RT − bottom time (ascent + deco only). Added LSP v2.10.10 |
| **Deco zone** | Depth where leading compartment inert-gas tension exceeds ambient (GF-independent). Fixed LSP v2.10.10 |
| **First stop** | First mandatory GF-anchored stop depth (GF-dependent) |

Do not confuse **deco zone** with **first stop**.

---

## Related LSP reference codebases

| Repo | Use |
|------|-----|
| [ApexDeco](https://github.com/VlasovAlexey/ApexDeco) | VPM-B, ppO₂ bands, transit modes |
| [DiveProMe](https://github.com/VlasovAlexey/DiveProMe) | Bühlmann ZHL-16C coefficients |
| [Subsurface](https://github.com/subsurface/subsurface) | Open-source Bühlmann planner |

---

## Verification in LSP

| Suite | Purpose |
|-------|---------|
| `audit.py` | 188 static checks (GROUP 31: TTS + decozone) |
| `tests-verify.html` | 68 tests — Baker/FORTRAN + MultiDeco pins (section H) |
| `tests.html` | 50 core regression tests |

Re-run a 3-way comparison against `divekit-cross-reference/` after any engine change affecting ZHL+GF ascent logic, headless wrapper, or gas selection.

---

## DiveKit doc index (online)

- https://divekit.app/docs/engine/how-it-works/
- https://divekit.app/docs/engine/design-decisions/
- https://divekit.app/docs/engine/gradient-factors/
- https://divekit.app/docs/engine/compared-to-multideco/
- https://divekit.app/docs/engine/assumptions-and-limits/
- https://divekit.app/docs/engine/what-changes-your-deco/
- https://divekit.app/docs/engine/impossible-plans/

---

*Last synced with LSP D-Planner v2.10.12 — June 2026*
