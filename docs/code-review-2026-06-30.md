# Audit Cycle 5 — gas-plan-core.js & gas-table-core.js
**Date:** 2026-06-30  
**Files audited:** `gas-plan-core.js` (~370 lines), `gas-table-core.js` (~170 lines)  
**Lenses applied:** Arithmetic/Physics · Control Flow · State/Mutation · API Contract · Mirror Parity · Safety Regression · Tooling/CI  
**Total findings:** 12 (2 HIGH · 4 MEDIUM · 6 LOW)

---

## Coverage Ledger Update

| File | Pre-cycle status | Lines newly read | Post-cycle status |
|------|-----------------|------------------|-------------------|
| `gas-plan-core.js` | UNREAD | ~370 (full file) | READ |
| `gas-table-core.js` | UNREAD | ~170 (full file) | READ |

Both files are fully read. Mark VERIFIED after regression tests are green.

---

## Findings

---

### GP-01 · HIGH · gas-plan-core.js · Arithmetic/Physics
**Location:** ~lines 155–165 — `portionL` / `travelPooledL` / `turnBar` computation  
**Title:** Travel-pooled turn pressure calculated on wrong denominator

When travel gas is pooled into bottom (same mix), `botShareL` is computed as:

```js
const botShareL = travelPooledL > 0
  ? portionL * ((botFill - botRes) * botSize) / usableL
  : portionL;
const turnBar = botFill - portionL / botSize;   // ← uses portionL, not botShareL
```

`botShareL` is computed but **never fed into `turnBar`**. The turn pressure always uses `portionL / botSize`, which is the rule-fraction of the combined pool divided by the bottom cylinder volume. When travel gas is pooled this is too aggressive — the turn pressure is too low (too early), and the displayed value does not represent the physical bottom-cylinder turn point.

**Fix:**
```js
const botCylUsableL = (botFill - botRes) * botSize;
const botCylPortionL = botCylUsableL * fraction;
const turnBar = botFill - botCylPortionL / botSize;
// portionL (the full pool portion) is still used for plan cross-check
```

---

### GP-02 · MEDIUM · gas-plan-core.js · Arithmetic/Physics
**Location:** ~lines 175–185 — `maxBTmin` back-calculation  
**Title:** Max-BT suggestion uses total consumption rate, not bottom-phase rate

`ratePerMin = reqL / plannedBT` treats total bottom-gas consumed (including deco ascent on bottom gas) as a linear function of BT. For trimix dives where bottom gas is breathed during long deco stops, `reqL` is inflated → `maxBTmin` is under-estimated → diver shown a shorter max BT than actually available.

**Fix:** Expose `window._lastBottomPhaseConsumedL` from the deco engine (bottom + descent phase only). Use it for the rate calculation. If unavailable, annotate the displayed warning as `"(conservative estimate)"`.

---

### GP-03 · MEDIUM · gas-plan-core.js · Control Flow
**Location:** ~lines 105–115 — `oneWayFiltered` travel deduplication  
**Title:** Dedup keyed on `.name === 'Travel'` — fragile for future pool dimensions

Filter removes travel from the one-way list only when pooled (`travelPooledL > 0`). A deco gas set to the same mix as the bottom gas is never deduplicated. Adding a second pool dimension (stage, CCR bailout) will silently double-count gas.

**Fix:** Dedup by label:
```js
const oneWayFiltered = travelPooledL > 0
  ? oneWay.filter(g => g.label !== botLabel)
  : oneWay;
```

---

### GP-04 · LOW · gas-plan-core.js · State/Mutation
**Location:** ~lines 22–30 — `setGasRule → runDecoSchedule`  
**Title:** `setGasRule` fires `runDecoSchedule` without checking worker-busy flag

If the user switches rule while a CCR schedule computation is in-flight, `runDecoSchedule()` is called a second time, racing the in-flight worker. Displayed schedule may reflect old rule; gas plan reflects new rule.

**Fix:** Guard call: `if (!window._scheduleWorkerBusy) runDecoSchedule();`

---

### GP-05 · LOW · gas-plan-core.js · Safety Regression
**Location:** ~lines 237–244 — one-way sufficiency thresholds  
**Title:** 10% tight-margin threshold is a magic number; bottom-gas row has no margin check

`r.totalL >= r.reqL * 1.10` for "ok" vs "tight" is undocumented. Bottom-gas surplus row shows green for any positive margin, even 1 litre.

**Fix:**
```js
const GP_ONEWAY_MARGIN = 1.10;   // at file top
```
Apply same margin check to bottom-gas surplus display.

---

### GP-06 · LOW · gas-plan-core.js · API Contract
**Location:** ~lines 65–80 — `gpRequiredFor` → `loopMixLabelFor`  
**Title:** Undocumented globals; `loopMixLabelFor` called without existence guard

`loopMixLabelFor`, `getCCRSettingsFromDOM`, `getBottomGasFractions`, `getDecoCardFractions`, `getAllDecoGasIds`, `isTravelGasConfigured`, `getDecoGasLabel`, `validateDomDecoGases` all missing from header `Globals read` list. `loopMixLabelFor` call throws `ReferenceError` in headless test contexts.

**Fix:** Add all missing globals to header comment. Wrap call: `if (typeof loopMixLabelFor === 'function') { ... }`.

---

### GT-01 · HIGH · gas-table-core.js · Arithmetic/Physics
**Location:** ~lines 87–95 — `pNarcDisplay` computation in `calcEND_tool`  
**Title:** `pNarcDisplay` diverges from `calcEND` when O2-narcotic setting is toggled at runtime

`calcEND_tool` computes the displayed narcotic-load bar value (`pNarcDisplay`) using a locally-derived `pNarcAirSurface` that reads `FN2_AIR` at call time. `calcEND()` (physics core) independently re-reads `narcoticN2`/`narcoticO2` flags every call. When the user toggles the O2-narcotic setting post-load:

- The END depth display (from `calcEND`) updates correctly  
- The "Narcotic Load" bar value stays stale

**Fix:** Expose `calcNarcPP(depth, fN2, fHe)` from `zhl-physics-core.js`. Replace the local re-derivation in `calcEND_tool` with a call to that function, ensuring both outputs share one code path.

---

### GT-02 · MEDIUM · gas-table-core.js · Arithmetic/Physics
**Location:** ~lines 131–140 — `mndM()` in `renderGasTable`  
**Title:** MND formula hardcodes 3.5 bar narcotic threshold; inconsistent with END tool

`pAmbTarget = 3.5 / narcFrac` is a fixed constant. The END tool uses the user's configured ppO2 limit for MOD, but there is no user-configurable narcosis limit. 3.5 bar = ~30 m END on air — a reasonable default, but should be a named constant.

**Fix:** `const GT_NARC_PP_TARGET = 3.5;` at file top. Document the 30 m END rationale in a comment.

---

### GT-03 · MEDIUM · gas-table-core.js · Arithmetic/Physics
**Location:** ~lines 70–75 — `ppO2Surf` hypoxia check  
**Title:** Hypoxia threshold 0.16 bar contradicts engine minimum 0.18 bar

Gas table warns at ppO2 < 0.16 bar. The deco engine rejects mixes with ppO2 < 0.18 bar. A user entering 18% O2 trimix sees no warning from the gas table but the engine refuses to schedule it.

**Fix:** Raise threshold to 0.18 bar (or import `MIN_BREATHABLE_PPO2` from `zhl-physics-core.js`).

---

### GT-04 · LOW · gas-table-core.js · Control Flow
**Location:** ~lines 103–112 — MOD colour thresholds in `renderGasTable`  
**Title:** MOD colour thresholds (red < 20 m, yellow < 30 m) inconsistent with END risk colours (moderate = 31–40 m)

`renderGasTable` colours MOD yellow for < 30 m. `calcEND_tool` colours END moderate for 31–40 m, low for ≤ 30 m. The two tools emit opposite colour signals in the 20–30 m range.

**Fix:** Extract shared depth-severity constants and use them in both render functions.

---

### GT-05 · LOW · gas-table-core.js · Mirror Parity
**Location:** ~lines 116–127 — fixed gas array in `renderGasTable`  
**Title:** Hard-coded gas list excludes user-configured custom trimix mixes

Gas table shows 9 fixed gases only. Gas plan tab auto-detects all configured mixes. Low priority, but the two tabs are inconsistent in scope.

**Fix (low priority):** After building the fixed gases array, optionally append user mixes from `getBottomGasFractions()` and `getDecoCardFractions()`.

---

### GT-06 · LOW · gas-table-core.js · API Contract
**Location:** Lines 1–10 — header globals comment  
**Title:** `FN2_AIR` and `BAR_PER_METRE` missing from `Globals read` list

Both are used in the file body but absent from the header documentation.

**Fix:** Add `FN2_AIR`, `BAR_PER_METRE` to `Globals read` in the file header comment.

---

## Required Regression Tests Before VERIFIED

| Test ID | Covers | Finding |
|---------|--------|---------|
| T-GP-01 | Turn pressure equals `botFill - (botCylUsable * fraction) / botSize` when travel pooled | GP-01 |
| T-GP-02 | maxBTmin > 0 when plan uses bottom gas in deco; labelled "conservative" | GP-02 |
| T-GP-03 | One-way list excludes pooled label regardless of `.name` value | GP-03 |
| T-GT-01 | `pNarcDisplay` matches `calcNarcPP` output after O2-narcotic toggle | GT-01 |
| T-GT-03 | Hypoxic warning fires at fO2=0.18 surface mix | GT-03 |

---

## Cumulative Audit Tracker

| File | Lines | Coverage after C5 | Status |
|------|-------|-------------------|--------|
| `zhl-physics-core.js` | ~191 | 90% | READ |
| `zhl-gas-core.js` | ~170 | 90% | READ |
| `zhl-worker-bridge.js` | ~130 | 85% | READ |
| `zhl-ccr-core.js` | ~380 | 90% | READ |
| `sw.js` | ~200 | 80% | READ |
| `zhl-schedule-core.js` | ~580 | 55% | PARTIAL |
| `gas-plan-core.js` | ~370 | 100% | READ → needs VERIFIED |
| `gas-table-core.js` | ~170 | 100% | READ → needs VERIFIED |
| `vpm-engine-core.js` | ~1,900 | 25% | PARTIAL |
| `zhl-engine-bundle.js` | ~1,600 | 40% | PARTIAL |
| `tools/*.py` | ~500 | 80% | READ |
| `ci.yml` | ~150 | 85% | READ |
| `dev/engine_regression.py` | ~1,100 | 20% | PARTIAL |
| `index.html` | ~17,000 | ~15% | PARTIAL — UI layer priority next |

**Next cycle priority:** `index.html` UI-06 (engine delegate layer) → UI-07 (multi-gas table management) → `zhl-schedule-core.js` lines 300–580.
