# LSP D-Planner + CCR — Errors & Bugs Report v14

**Repo:** `Three-Cats-LSP/LSP_D-planner-CCR`  
**Version analysed:** v2.30.15 (commit `ea3c069`)  
**Date:** 2026-06-21  
**Audit result:** 303 checks, 0 failures  
**Scope:** Full independent deep-audit pass. All prior bugs (BUG-01 through BUG-68) verified fixed. New findings below.

---

## Verification Summary (BUG-01 — BUG-68)

All 68 prior reported bugs confirmed fixed:

| Range | Area | Status |
|---|---|---|
| BUG-01–12 | Version mismatches, Android SDK, ppO2 display, gas consumption, branding | ✅ All fixed |
| BUG-13–22 | VPM gas consumption, diluent MOD, gas plan, pSCR setpoint UI | ✅ All fixed |
| BUG-23–32 | Graph ceiling overlay, multi-dive CCR, settings clear/restore, gas reserve | ✅ All fixed |
| BUG-33–42 | VPM cylinder mapping, imperial gas capacity, double restore pass | ✅ All fixed |
| BUG-43–56 | Metabolic rate, pSCR MOD, diluent cylinder cross-check, Schreiner dim, gas labels | ✅ All fixed |
| BUG-57–68 | VPM continuation helpers, scrRuntimeMin propagation, pSCR OTU/CNS parity | ✅ All fixed |

---

## New Bugs

### BUG-69 — `computeSurfaceGF()` hardcodes `P_surf = 1.0 bar` — surface GF display wrong at altitude

**File:** `index.html`  
**Location:** `computeSurfaceGF()` line ~6256

```js
function computeSurfaceGF(tissues) {
  const P_surf = 1.0; // bar  ← hardcoded sea-level
  // ...
  const mValue = a + P_surf / b - P_surf;
  const gf = (pTotal - P_surf) / mValue;
}
```

The M-value denominator and the numerator both use `P_surf = 1.0`. For altitude dives `altSurfaceP` is already set correctly (e.g. 0.8 bar at ~2000 m) and the deco engine `ceiling()` function correctly uses `altSurfaceP`. Only `computeSurfaceGF` uses the hardcoded constant.

**Impact (example):** At 2000 m altitude (`altSurfaceP ≈ 0.80 bar`), a leading compartment with `pN2 = 1.5 bar` (air dive), `a = 0.45`, `b = 0.80`:

| | P\_surf = 1.0 (current) | P\_surf = 0.80 (correct) |
|---|---|---|
| mValue | 0.700 | 0.650 |
| Surface GF | **71%** | **108%** |

The surface GF footer metric shows 71% when the diver actually surfaces at 108% of the M-value — significantly understating the risk. The diver sees a "safe-looking" surface GF on an altitude dive where they are actually above their M-value at the surface.

**Fix:** Replace `const P_surf = 1.0;` with `const P_surf = altSurfaceP;`.

**Note:** The comment in the code states "P_surf = 1.0 bar (sea-level ambient)" suggesting this may be an intentional Baker formula convention. However, the Baker Surface GF formula uses the *actual* surface pressure the diver ascends to — not a fixed sea-level reference. The `ceiling()` function in the same file correctly uses `altSurfaceP`, making `computeSurfaceGF()` the only function inconsistent with the altitude-aware architecture.

---

### BUG-70 — Stress/problem-solve bailout reserve always computed at bottom depth; deco stop–level bail-out not covered

**File:** `index.html`  
**Location:** Bühlmann gas reserve block line ~10474; VPM gas reserve block line ~7428

```js
// Both paths:
const reserveLabel = getBailoutReserveMixLabel(depthM, bottomFO2, bottomFHe);
if (reserveLabel) {
  addGas(reserveLabel, depthM, reserveMin, sacStress);  // depthM = bottom depth
}
```

The stress/problem-solve reserve is added as a fixed volume at the bottom depth (`rawD` / `depthM`). However, an emergency bailout is statistically most likely to occur anywhere in the dive — including during the ascent phase when the diver is at a shallow deco stop.

**Impact:** The reserve volume is calculated at the highest ambient pressure (bottom), producing the largest possible reserve. This is conservative, but the gas assigned to the reserve is the deepest-capable bailout gas at the bottom depth. If that gas is OC-viable at the bottom but the stress event happens at a shallow stop where a richer (shallower-MOD) deco gas would be breathable, the gas plan allocates all the reserve to the deep-capable gas and zero to the shallow gas.

**Example:** 40 m dive with EAN32 (MOD 30 m, deep bailout), EAN50 (MOD 18 m, shallow bailout). The entire stress reserve is attributed to EAN32 at 40 m. If the actual bailout happens at 9 m, the diver would breathe EAN50, but EAN50 has no reserve volume allocated. EAN32 reserve is over-sized for a 9 m stop.

**Severity:** Low — the plan is conservative (reserve volume is maximised at depth) and the total gas error is generally small. But it creates a discrepancy between which gas has the reserve allocated vs which gas the diver would actually breathe in a shallow emergency.

---

## Summary Table

| # | Severity | Area | Description |
|---|---|---|---|
| BUG-69 | MEDIUM | Surface GF / Altitude | `computeSurfaceGF()` uses `P_surf=1.0` — surface GF wrong at altitude (shows safe when above M-value) |
| BUG-70 | LOW | Gas plan / Reserve | Stress reserve always at bottom depth; reserve gas attribution diverges from actual shallow bail-out gas |

