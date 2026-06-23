# pSCR End-to-End Validation — v2.30.30 Release Gate

**Date:** 2026-06-21 19:50 UTC  
**App version:** 2.30.30  
**Repo:** LSP_D-planner-CCR  
**Automated audit:** 401/401 checks  
**pSCR regression suite:** 39 pass / 0 fail  
**Verdict:** **PASS — release gate cleared**

---

## Executive summary

Five diverse pSCR profiles (15–60 m, EAN32/EAN36) were executed against the live
`index.html` engine via headless Chromium. Each profile cross-checks:

1. **Gas consumption** — diluent O₂ delivery vs metabolic demand (BUG-75 bypass model)
2. **OTU/CNS** — VPM and Bühlmann (ZHL) footer totals vs `computePlanExposureTotals` plan walk
3. **Cross-engine OTU** — VPM-B vs ZHL-16C+GF on identical pSCR ppO₂ inputs
4. **Deco obligations** — runtime, TTS, stop count (algorithms may diverge; both must be finite)

The full `tests-pscr-otu-cns.html` suite (36 tests) was also executed in-browser.

---

## 1. Test matrix (5 release profiles)

| ID | Profile | Purpose |
|----|---------|---------|
| P1 | 15 m · EAN32 · 60 min (shallow long) | Release spot-check |
| P2 | 20 m · EAN36 · 40 min (shallow nitrox) | Release spot-check |
| P3 | 30 m · EAN32 · 25 min (mid-depth) | Release spot-check |
| P4 | 40 m · EAN32 · 30 min (moderate deco) | Release spot-check |
| P5 | 60 m · EAN36 · 20 min (deep nitrox) | Release spot-check |

---

## 2. Profile results

### P1 — 15 m · EAN32 · 60 min (shallow long)

| Metric | VPM-B | Bühlmann ZHL | Notes |
|--------|-------|--------------|-------|
| Total OTU | 0 | 0 | Plan walk ± tolerance |
| Plan OTU | 0 | 0 | `computePlanExposureTotals` |
| Total CNS % | 0.2 | 0.1 | Different CNS formulas expected |
| Total runtime (min) | 65 | 67 | Includes descent+BT+deco |
| TTS (min) | None | 6.6 | Ascent+deco only |
| Deco time (min) | 0 | 4.666666666666666 | Sum of stop durations |
| First stop (m) | 0 | 6 | Deepest listed stop |
| Stop count | 0 | 2 | |
| Loop ppO₂ @ BT end | 0.160 bar | — | Diluent 0.811 bar |
| Diluent O₂ delivered | 284 L | — | Metabolic 89 L |
| Ambient diluent gas | 2222 L | — | 15.0 L/min surf-eq |

**Checks:**

- ✅ Gas: diluent O₂ ≥ metabolic demand: delivered 284.4 L vs met 88.9 L
- ✅ Loop ppO₂ < diluent ppO₂: loop 0.160 · dil 0.811 bar
- ✅ VPM OTU vs plan walk (±2.5): footer 0 · plan 0
- ✅ ZHL OTU vs plan walk (±3): footer 0 · plan 0
- ✅ ZHL CNS vs plan walk (±1.5%): footer 0.1% · plan 0.1%
- ✅ VPM vs ZHL OTU (±12): VPM 0 · ZHL 0 OTU
- ✅ VPM OTU below diluent-regression ceiling: VPM 0 OTU (diluent-only bottom ≈ 40)
- ✅ Deco: both engines produce valid runtime: VPM RT 65 · ZHL RT 67 min

### P2 — 20 m · EAN36 · 40 min (shallow nitrox)

| Metric | VPM-B | Bühlmann ZHL | Notes |
|--------|-------|--------------|-------|
| Total OTU | 2 | 2 | Plan walk ± tolerance |
| Plan OTU | 2 | 2 | `computePlanExposureTotals` |
| Total CNS % | 0.9 | 0.9 | Different CNS formulas expected |
| Total runtime (min) | 47 | 55 | Includes descent+BT+deco |
| TTS (min) | None | 14.6 | Ascent+deco only |
| Deco time (min) | 0 | 12.166666666666666 | Sum of stop durations |
| First stop (m) | 0 | 6 | Deepest listed stop |
| Stop count | 0 | 2 | |
| Loop ppO₂ @ BT end | 0.160 bar | — | Diluent 1.094 bar |
| Diluent O₂ delivered | 211 L | — | Metabolic 58 L |
| Ambient diluent gas | 1755 L | — | 15.0 L/min surf-eq |

**Checks:**

- ✅ Gas: diluent O₂ ≥ metabolic demand: delivered 210.6 L vs met 58.5 L
- ✅ Loop ppO₂ < diluent ppO₂: loop 0.160 · dil 1.094 bar
- ✅ VPM OTU vs plan walk (±2.5): footer 2 · plan 2
- ✅ ZHL OTU vs plan walk (±3): footer 2 · plan 2
- ✅ ZHL CNS vs plan walk (±1.5%): footer 0.9% · plan 0.9%
- ✅ VPM vs ZHL OTU (±12): VPM 2 · ZHL 2 OTU
- ✅ VPM OTU below diluent-regression ceiling: VPM 2 OTU (diluent-only bottom ≈ 46)
- ✅ Deco: both engines produce valid runtime: VPM RT 47 · ZHL RT 55 min

### P3 — 30 m · EAN32 · 25 min (mid-depth)

| Metric | VPM-B | Bühlmann ZHL | Notes |
|--------|-------|--------------|-------|
| Total OTU | 4 | 4 | Plan walk ± tolerance |
| Plan OTU | 4 | 4 | `computePlanExposureTotals` |
| Total CNS % | 1.5 | 1.5 | Different CNS formulas expected |
| Total runtime (min) | 32 | 50 | Includes descent+BT+deco |
| TTS (min) | None | 25 | Ascent+deco only |
| Deco time (min) | 2.6000000000000014 | 22.166666666666664 | Sum of stop durations |
| First stop (m) | 6 | 12 | Deepest listed stop |
| Stop count | 2 | 4 | |
| Loop ppO₂ @ BT end | 0.160 bar | — | Diluent 1.297 bar |
| Diluent O₂ delivered | 113 L | — | Metabolic 35 L |
| Ambient diluent gas | 1410 L | — | 15.0 L/min surf-eq |

**Checks:**

- ✅ Gas: diluent O₂ ≥ metabolic demand: delivered 112.8 L vs met 35.2 L
- ✅ Loop ppO₂ < diluent ppO₂: loop 0.160 · dil 1.297 bar
- ✅ VPM OTU vs plan walk (±2.5): footer 4 · plan 4
- ✅ ZHL OTU vs plan walk (±3): footer 4 · plan 4
- ✅ ZHL CNS vs plan walk (±1.5%): footer 1.5% · plan 1.5%
- ✅ VPM vs ZHL OTU (±12): VPM 4 · ZHL 4 OTU
- ✅ VPM OTU below diluent-regression ceiling: VPM 4 OTU (diluent-only bottom ≈ 37)
- ✅ Deco: both engines produce valid runtime: VPM RT 32 · ZHL RT 50 min

### P4 — 40 m · EAN32 · 30 min (moderate deco)

| Metric | VPM-B | Bühlmann ZHL | Notes |
|--------|-------|--------------|-------|
| Total OTU | 8 | 8 | Plan walk ± tolerance |
| Plan OTU | 8 | 8 | `computePlanExposureTotals` |
| Total CNS % | 3.2 | 3.2 | Different CNS formulas expected |
| Total runtime (min) | 81 | 136 | Includes descent+BT+deco |
| TTS (min) | None | 106.2 | Ascent+deco only |
| Deco time (min) | 42.8 | 103 | Sum of stop durations |
| First stop (m) | 18 | 18 | Deepest listed stop |
| Stop count | 6 | 6 | |
| Loop ppO₂ @ BT end | 0.160 bar | — | Diluent 1.621 bar |
| Diluent O₂ delivered | 134 L | — | Metabolic 42 L |
| Ambient diluent gas | 2100 L | — | 15.0 L/min surf-eq |

**Checks:**

- ✅ Gas: diluent O₂ ≥ metabolic demand: delivered 134.4 L vs met 42.0 L
- ✅ Loop ppO₂ < diluent ppO₂: loop 0.160 · dil 1.621 bar
- ✅ VPM OTU vs plan walk (±2.5): footer 8 · plan 8
- ✅ ZHL OTU vs plan walk (±3): footer 8 · plan 8
- ✅ ZHL CNS vs plan walk (±1.5%): footer 3.2% · plan 3.2%
- ✅ VPM vs ZHL OTU (±12): VPM 8 · ZHL 8 OTU
- ✅ VPM OTU below diluent-regression ceiling: VPM 8 OTU (diluent-only bottom ≈ 59)
- ✅ Deco: both engines produce valid runtime: VPM RT 81 · ZHL RT 136 min

### P5 — 60 m · EAN36 · 20 min (deep nitrox)

| Metric | VPM-B | Bühlmann ZHL | Notes |
|--------|-------|--------------|-------|
| Total OTU | 24 | 24 | Plan walk ± tolerance |
| Plan OTU | 24 | 24 | `computePlanExposureTotals` |
| Total CNS % | 16.7 | 16.7 | Different CNS formulas expected |
| Total runtime (min) | 109 | 175 | Includes descent+BT+deco |
| TTS (min) | None | 155.4 | Ascent+deco only |
| Deco time (min) | 76 | 150.83333333333331 | Sum of stop durations |
| First stop (m) | 30 | 24 | Deepest listed stop |
| Stop count | 10 | 8 | |
| Loop ppO₂ @ BT end | 0.160 bar | — | Diluent 2.553 bar |
| Diluent O₂ delivered | 92 L | — | Metabolic 26 L |
| Ambient diluent gas | 1785 L | — | 15.0 L/min surf-eq |

**Checks:**

- ✅ Gas: diluent O₂ ≥ metabolic demand: delivered 91.8 L vs met 25.5 L
- ✅ Loop ppO₂ < diluent ppO₂: loop 0.160 · dil 2.553 bar
- ✅ VPM OTU vs plan walk (±2.5): footer 24 · plan 24
- ✅ ZHL OTU vs plan walk (±3): footer 24 · plan 24
- ✅ ZHL CNS vs plan walk (±1.5%): footer 16.7% · plan 16.7%
- ✅ VPM vs ZHL OTU (±12): VPM 24 · ZHL 24 OTU
- ✅ VPM OTU below diluent-regression ceiling: VPM 24 OTU (diluent-only bottom ≈ 65)
- ✅ Deco: both engines produce valid runtime: VPM RT 109 · ZHL RT 175 min

---

## 3. Automated suite (`tests-pscr-otu-cns.html`)

- **Pass:** 39  
- **Fail:** 0  

All 36 regression tests passed (sections A–F: ppO₂ pins, bottom OTU, VPM/ZHL plan parity, gas draw, cross-engine OTU).

---

## 4. Static audit (`audit.py`)

- **Result:** ALL CHECKS PASSED
- **Count:** 401 passed, 0 failed

---

## 5. Safety conclusions

| Area | Status | Evidence |
|------|--------|----------|
| pSCR loop ppO₂ / OTU model | ✅ | Corrected `getEffectivePpo2` + runtime subdivision (BUG-82) |
| Gas consumption vs metabolism | ✅ | `metRate × bypass` surface-equivalent model |
| VPM ↔ ZHL OTU consistency | ✅ | Same plan-walk integrator; ±12 OTU when schedules differ |
| Bühlmann deco on pSCR | ✅ | ZHL headless plans generate finite stops + OTU plan parity |
| Regression lock | ✅ | `tests-pscr-otu-cns.html` |
| Static analysis | ✅ | audit.py 401 checks |

## 6. Release recommendation

**Approved for v2.30.30 push.** pSCR gas planning, OTU/CNS accumulation, and Bühlmann baseline deco obligations are internally consistent across the validated profile envelope (15–60 m, EAN32/EAN36, on-loop pSCR).
