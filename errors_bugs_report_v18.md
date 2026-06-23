# LSP D-Planner + CCR — Errors & Bugs Report v18

**Repo:** `Three-Cats-LSP/LSP_D-planner-CCR`  
**Version analysed:** v2.30.24 (commit `3b02b5d`)  
**Date:** 2026-06-21  
**Audit result:** 346 checks, 0 failures  
**Scope:** Verification pass 18. BUG-73/74 confirmed fixed. One new bug found.

---

## Verification

| Bug | Status |
|---|---|
| BUG-73 — CCR headless CNS/OTU used OC ppO₂ | ✅ Fixed — `hCcrOnLoop` branch added to `headlessPpo2()` using `getEffectiveSetpointAtDepth` with correct phase ('descent'/'bottom'/'deco') |
| BUG-74 — `package.json`/`build.gradle` version lag | ✅ Fixed — all files at `2.30.24` |

BUG-73 fix is thorough: `hCcrConfig` extracts all three setpoints from `settings`, `headlessPpo2()` receives `phase` parameter at every call site (descent/bottom/deco/ascent), and `getEffectiveSetpointAtDepth` applies the phase-aware setpoint correctly.

---

## New Bug

### BUG-75 — pSCR gas consumption formula incorrect: `(metRate / fO2Loop) × bypassRatio` instead of `metRate × bypassRatio`

**File:** `index.html`  
**Severity:** MEDIUM  
**Location:** `ccrDiluentSurfaceLpm()` line ~5958

```js
const fr = computePSCRFractions(pSurf, bot.fO2, bot.fHe, runtimeMin, ccr);
const fO2Loop = Math.max(0.01, fr.fO2);
return (metRate / fO2Loop) * PSCR_DEFAULT_BYPASS_RATIO;  // ← wrong
```

**Correct formula:** `metRate * PSCR_DEFAULT_BYPASS_RATIO`

The bypass ratio in a pSCR means: for every 1 L of O₂ consumed by metabolism, `bypassRatio` litres of fresh gas flow through the scrubber. Therefore:

```
fresh_gas_flow (L/min) = metabolic_O2_rate (L/min) × bypass_ratio
                       = 1.5 × 10 = 15 L/min  (at surface)
```

The current formula introduces `fO2Loop` (the O₂ fraction remaining in the loop after metabolic consumption) in the denominator:

```
current = (1.5 / fO2Loop) × 10
```

When `fO2Loop` is low (stale loop, e.g. 0.16 bar / 1.0 bar = 0.16), this gives:
```
(1.5 / 0.16) × 10 = 93.75 L/min  ← ~6× too high
```

`fO2Loop` is the *output* of the bypass process (what the diver ends up breathing), not an input that should scale the bypass flow. Dividing by it creates an inverse relationship where a more-depleted loop produces a higher gas consumption estimate — the opposite of physical reality.

**Impact:** pSCR diluent gas consumption in the Gas Plan is overstated by approximately 6–10×. A 40 m / 20 min pSCR dive shows diluent consumption of ~7,000 L instead of the correct ~750 L. The Gas Plan sufficiency check will always show a massively insufficient diluent cylinder, making the gas plan unusable for pSCR dives.

**Context:** Introduced in commit `8cefc72` (v2.30.13) as the fix for BUG-56. BUG-56 correctly identified that pSCR needs the bypass ratio — but the formula was assembled incorrectly.

**Fix:**
```js
// Delete the computePSCRFractions and fO2Loop lines; replace return with:
return metRate * PSCR_DEFAULT_BYPASS_RATIO;
// = 1.5 × 10 = 15 L/min at surface (correct)
```

---

## Summary Table

| # | Severity | Area | Description |
|---|---|---|---|
| BUG-75 | MEDIUM | pSCR / Gas plan | Gas consumption formula `(metRate/fO2Loop)×bypass` should be `metRate×bypass` — overstates pSCR diluent by 6–10× |

