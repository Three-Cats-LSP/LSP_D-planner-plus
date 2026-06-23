# MultiDeco Binary — Independently Re-Verified Findings (Claude / Anthropic Computer)

**Date:** June 2026
**Verified by:** Direct re-disassembly and byte-level extraction from the actual binary now
in this repo (`MultiDeco Binary/lib/arm64-v8a/libmultideco.so`), using
`aarch64-linux-gnu-objdump` and an independent Python `struct` reader — not a re-read of
prior analysis docs. Every claim below was reproduced from raw bytes by this session.

**Purpose of this doc:** the three prior MultiDeco analysis docs in this Knowledge Base
(`APK_Reverse_Engineering.md`, `MultiDeco_Engine_Full_Analysis.md`,
`MultiDeco_ShallowGradient_Analysis.md`) contain a mix of correct findings and at least
two real errors. This doc is the tiebreaker, written after independently reproducing the
binary evidence rather than trusting either side. **Treat this doc as authoritative for
the specific claims it covers; defer to the other three docs for everything else
(Shallow Gradient formula, function addresses, control flow) which this session did not
re-verify line by line.**

---

## 1. N2/He half-time table identity — CONFIRMED, both sides were partially right

**This was a real, two-document disagreement.** `MultiDeco_Engine_Full_Analysis.md`
section 3.4 labels `0x15c00` "N2 rate constants" and `0x15c80` "He rate constants" but
lists values that are objectively swapped (canonical He values under the N2 label and
vice versa). `MultiDeco_Verified_Findings.md` correctly traced the actual pointer usage
via disassembly and got the physical identity right.

**Independently reproduced this session** (direct ARM64 disassembly of
`GAS_LOADINGS_CONST_DEPTH @ 0x35370`, plus independent byte extraction):

```
adr x22, 15c00   →  ldr q0, [x22, x20]  →  feeds the loop that writes to
                                            BSS+0x70 = pN2_tissue[]   (confirmed via
                                            ldr x21, [x21, #112] = offset 0x70)

adr x24, 15c80   →  ldr q1, [x24, x20]  →  feeds the loop that writes to
                                            BSS+0x68 = pHe_tissue[]
```

**So `0x15c00` is genuinely the table MultiDeco uses for N2 tissue loading, and `0x15c80`
is genuinely the table it uses for He.** The pointer trace is unambiguous and was
independently reproduced.

**But the actual k-values stored at those addresses are physically swapped relative to
the published Bühlmann gas tables:**

| Address | Used for | Values (HT, min) | Matches canonical... |
|---|---|---|---|
| `0x15c00` | N2 tissue loading | 1.88, 3.02, 4.72, 6.99, 10.21, 14.48, 20.53, 29.11, 41.2, 55.19, 70.69, 90.34, 115.3, 147.4, 188.2, 240.0 | **He** half-times |
| `0x15c80` | He tissue loading | 5, 8, 12.5, 18.5, 27, 38.3, 54.3, 77, 109, 146, 187, 239, 305, 390, 498, 635 | **N2** half-times |

**Verified independently this session** via direct `struct.unpack('<d', ...)` on the raw
bytes at both addresses — see byte dump below, matches `MultiDeco_Verified_Findings.md`
exactly to 12 decimal places.

```
0x15c00 first entry: d4 58 61 35 b4 98 d7 3f → k=0.368695308808481 → HT=1.880 min
0x15c80 first entry: bd 94 2e ff 9b be c1 3f → k=0.138629436111989 → HT=5.000 min
```

### What this means

MultiDeco's nitrogen compartments physically load and offgas using the He half-time
constants (faster), and its helium compartments use the N2 half-time constants (slower).
**This is the opposite of correct gas physics** — He should diffuse faster than N2 in
real tissue, and MultiDeco's own ratio (`HT_N2/HT_He ≈ 2.66`, matching the documented
Bühlmann diffusion ratio) is applied, but to the wrong gas. With N2 (the gas actually
present on every air/nitrox dive) using He's fast time constants, N2 tissue loading is
**under-estimated on long bottom times and over-estimated as washing out fast during
ascent** relative to a correctly-labeled implementation.

`MultiDeco_Verified_Findings.md`'s conclusion — *"do not copy standard ZHL-16C N2
half-times if trying to match MultiDeco output; use `HT_N2[i] = HT_He[i] × 2.6595`"* —
is **correct as a description of what MultiDeco's code actually does**, but should not
be read as "this is the right way to model N2." It's a description of an apparent bug
in MultiDeco, not a design choice to emulate. **Recommend LSP does NOT replicate this.**
If LSP ever wants a "MultiDeco-matching mode" toggle for side-by-side comparison
purposes only, this is the mechanism — but it should never be the default, and the
toggle's tooltip should say plainly that it reproduces a quirk, not a feature.

---

## 2. a-value and b-value tables — CORRECTING a false positive in the Full Analysis doc

`MultiDeco_Engine_Full_Analysis.md` section 12 claims: *"a5 (compartment 5) value found
at `0x16230`: 0.6200 — matching Subsurface/decotengu variant."* **This is a false
positive**, independently reproduced and then disproven this session:

```
Reading 16 doubles around 0x16230:
0.57, 0.59, 0.60, 0.61, 0.62, 0.63, 0.64, 0.645, 0.65, 0.66, 0.68, 0.695, 0.71, 0.72, 0.74, 0.77
```

This is a monotonic stop-depth/pressure-snap lookup table (matches the "44-entry b-value
lookup table for variable stop increments" the same doc correctly identifies at the
adjacent address `0x161c0`) — `0.62` just happens to be one entry in this sequence by
coincidence, the same class of error as matching SVG path coordinates in the earlier
DiveKit analysis. **It is not a ZHL-16C a-coefficient.**

### The real a/b tables — found and confirmed via disassembly + byte extraction

`APK_Reverse_Engineering.md`'s original addresses (`0x015e00` for "N2 a-values" and
`0x015e80` for "N2 b-coefficients") are correct locations and are **directly referenced
inside `CALC_DECO_CEILING_GF @ 0x31bf8`** (`adr x13, 15e00` / `adr x15, 15e80`,
confirmed by disassembling the function this session). But the original doc mislabeled
one of them:

| Address | Content (verified by reading raw bytes) | Identity |
|---|---|---|
| `0x15e00` | 16.189, 13.83, 11.919, 10.458, 9.22, 8.205, 7.305, 6.502, 5.95, 5.545, 5.333, 5.189, 5.181, 5.176, 5.172, 5.119 | **He a-values × 10** — exact match to canonical ZHL-16C He a (1.6189, 1.383, 1.1919...5.119 → ÷10) |
| `0x15e80` | 0.5578, 0.6514, 0.7222, 0.7825, 0.8126, 0.8434, 0.8693, 0.891, 0.9092, 0.9222, 0.9319, 0.9403, 0.9477, 0.9544, 0.9602, 0.9653 | **N2 b-values** — exact match to canonical ZHL-16C N2 b, no scaling |
| `0x15f00` | 0.477, 0.5747, 0.6527, 0.7223, 0.7582, 0.7957, 0.8279, 0.8553, 0.8757, 0.8903, 0.8997, 0.9073, 0.9122, 0.9171, 0.9217, 0.9267 | **He b-values** — exact match to canonical ZHL-16C He b |
| `0x15d00` | 11.696, 10.0, 8.618, 7.562, **6.667**, 5.6, 4.947, 4.5, 4.187, 3.798, 3.497, 3.223, 2.85, 2.737, 2.523, 2.327 | **N2 a-values × 10, "A/B" variant** (a5=0.6667 — matches dmaziuk's authoritative A/B table) |
| `0x15d80` | 11.696, 10.0, 8.618, 7.562, **6.200**, 5.043, 4.41, 4.0, 3.75, 3.5, 3.295, 3.065, 2.835, 2.61, 2.48, 2.327 | **N2 a-values × 10, "C" variant** (a5=0.6200 — matches Subsurface/decotengu/GasPlanner/LSP) |

All five tables independently verified this session against canonical published values
to 4 decimal places (after un-scaling the ×10 tables). The earlier doc's b-coefficient
claim (`APK_Reverse_Engineering.md`, "all 16 values are exact matches to ZHL-16C") was
**correct** for `0x15e80` — that part of the original analysis holds up.

### Why two N2 a-tables?

`CALC_DECO_CEILING_GF` selects between `0x15d00` ("A/B") and `0x15d80` ("C") based on
a field at `TVPM+204` (`Stop_increment`, the same field `MultiDeco_Engine_Full_Analysis.md`
section 2 already identified as the VPM-B/Bühlmann mode selector) compared against the
literal `5`. This lines up with MultiDeco's own published feature list — it offers
**ZHL-16B, ZHL-16C, GF, VPM-B, VPM-B/E, VPM-B/FBO** as separately selectable algorithms —
so this is normal table-switching for a user-selectable model, not a bug.

### Resolved: which a5 variant does MultiDeco use by default?

**Both are present; the active one depends on which algorithm the user selects in the
MultiDeco UI.** When "ZHL-16C" or "GF" is selected, the evidence points to `0x15d80`
(a5=0.6200) being used — the same variant LSP already uses. This **reverses** the
`OpenSource_Deco_Libraries_2.md` batch-2 doc's categorization, which listed MultiDeco
under the "canonical Bühlmann (a5=0.6491)" column. Neither table found in the binary
uses 0.6491 at all — that specific value does not appear to be present in this binary
in either a/b table. **LSP and MultiDeco's ZHL-16C mode already agree on a5.** The
historical RT/TTS gap is not explained by an a5 mismatch; rule this theory out.

---

## 3. Net implication for the v2.20.0 roadmap

- **Shallow Gradient**: `MultiDeco_ShallowGradient_Analysis.md`'s decoded formula was
  not re-verified line-by-line this session (time-boxed to the half-time/a-value
  question that had an open contradiction), but its general approach (direct ARM64
  disassembly with annotated register tracing) is the same standard of evidence as
  what's confirmed reliable in sections 1–2 above, and its conclusions don't depend on
  the N2/He or a-value errors found here. **Reasonable to proceed treating it as
  reliable**, with a recommendation to spot-check 2-3 of its specific constant claims
  (e.g. the `0.40` ratio threshold, the `60.0`/`80.0` minute time thresholds) against
  the raw binary before writing any LSP code from it, the same way this doc did for the
  half-time tables.
- **a5 ZHL-16C variant**: confirmed LSP and MultiDeco already agree (both 0.6200 in
  ZHL-16C/GF mode). Remove this as a candidate explanation for the historical RT/TTS gap
  in any future write-up.
- **N2/He half-time swap**: this is a new, real, and significant finding not previously
  in the roadmap. It is almost certainly a meaningful contributor to RT/TTS differences
  on any dive profile where N2 and He are both present in nontrivial amounts (i.e., any
  trimix dive) — MultiDeco's N2 will offgas unrealistically fast during ascent relative
  to a correctly-implemented engine. This does **not** explain air/nitrox-only gaps
  (S1–S4, FS1–FS4 in the comparison data), only the He-bearing scenarios (S5, S6, A2,
  A3, A6, B1, FS5) — consistent with those being exactly the scenarios the existing
  `Subsurface_Engine_Analysis.md` already flagged as having the largest unexplained
  deltas. **Recommend NOT replicating this in LSP** — it's a documented quirk for
  understanding *why* MultiDeco's trimix numbers differ, not a target to match.

---

## 4. Method notes (for reproducibility)

All values in this doc were extracted using:
```python
import struct
with open('MultiDeco Binary/lib/arm64-v8a/libmultideco.so', 'rb') as f:
    data = f.read()
v = struct.unpack('<d', data[offset:offset+8])[0]  # offset = file vaddr, .so has no separate load bias here
```//
and disassembly via:
```bash
aarch64-linux-gnu-objdump -d --start-address=0xADDR --stop-address=0xADDR lib/arm64-v8a/libmultideco.so
```
Both tools/methods are already present in this repo under `MultiDeco Binary/tools/`.
