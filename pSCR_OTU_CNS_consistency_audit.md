# pSCR OTU/CNS Consistency Audit — LSP D-Planner+CCR

**App version audited:** v2.30.15  
**Status:** BUG-63–68 addressed in v2.30.14–v2.30.15

---

## Executive summary

BUG-63 fixed the **primary VPM single-level schedule path** (`VPMEngine.calculate()` level loop) by routing six OTU/CNS accumulation sites through `vpmAccumPpo2()` → `getEffectivePpo2()` → `computePSCRFractions()`.

This audit found **four additional code paths** that still used the pre-fix diluent formula — **fixed in v2.30.15 (BUG-64–68)**. See Section 4 for resolution status.

---

## 1. Reference model (correct pSCR ppO₂)

### 1.1 Metabolic loop depletion (`computePSCRFractions`)

Given ambient pressure `pAmb`, diluent fractions `fO2`/`fHe`, cumulative on-loop time `scrRuntimeMin`, loop volume `V` (default 10 L DOM / 7 L fallback), metabolic rate `ṀO₂` (default 1.5 L/min):

```
O₂_consumed = ṀO₂ × scrRuntimeMin
loopO₂_bar·L = fO2 × V × pAmb
minLoopO₂    = PSCR_MIN_PPO2 (0.16) × V × pAmb
newLoopO₂    = max(minLoopO₂, loopO₂_bar·L − O₂_consumed)
fO2_loop     = newLoopO₂ / (V × pAmb)
```

Inspired loop ppO₂ (what the diver breathes):

```
ppO2_loop = max(PSCR_MIN_PPO2, fO2_loop × pAmb)    // getEffectivePpo2, pSCR branch
```

**Incorrect (pre BUG-63) fallback when setpoint = 0:**

```
ppO2_wrong = fO2_diluent × pAmb                         // OC / diluent ppO₂
```

### 1.2 OTU accumulation (both engines)

```js
OTU += duration_min × ((ppO2 − 0.5) / 0.5)^0.8333     // OTU_EXPONENT; ppO2 ≤ 0.5 → 0
```

### 1.3 CNS accumulation — engines differ

| Engine | Formula | Location |
|--------|---------|----------|
| **VPM** | `CNS += duration × getCNSRate(ppO2)` | `VPMEngine.calculateCNS()` ~8537 |
| **Bühlmann** | `CNS_frac += duration / NOAA_limit(ppO2)` | `segCNSfrac()` ~10411 |

Cross-engine CNS totals are **not expected to match numerically** even with identical ppO₂ inputs. OTU formulas are aligned.

### 1.4 Bühlmann reference path (correct routing)

```
rowDisplayPpo2 → ppO2Check(onLoop) → getEffectivePpo2(pAmb, sp, fO2, ccr, depth, fHe)
```

OTU/CNS in `runDecoSchedule()` accumulate using `rowDisplayPpo2` / step `pO2` values (~10439–10627).

---

## 2. OTU/CNS accumulation path audit

### 2.1 Legend

| Status | Meaning |
|--------|---------|
| ✅ | Uses `getEffectivePpo2` / `vpmAccumPpo2` for pSCR on-loop |
| ⚠️ | Uses correct function but `scrRuntimeMin` not synced to segment time |
| ❌ | Still uses diluent `fO2 × pAmb` for pSCR |

### 2.2 VPMEngine — primary schedule (`calculate()` level loop)

| Site | Phase | Function | Status | Notes |
|------|-------|----------|--------|-------|
| ~8964 | Direct ascent to target | `vpmAccumPpo2` | ✅ | Uses `settings._scrRuntimeMin` |
| ~9016 | Ascent to first stop | `vpmAccumPpo2` | ✅ | Uses `depthSeg` |
| ~9062 | Deco stop hold | `vpmAccumPpo2` | ✅ | |
| ~9083 | Inter-stop ascent | `vpmAccumPpo2` | ✅ | Uses `depthSeg` |
| ~9105 | Descent to level | `vpmAccumPpo2` | ✅ | Respects `forcedOCMode \|\| nextLevelOffLoop` |
| ~9130 | Bottom hold | `vpmAccumPpo2` | ✅ | Respects OC/bailout flags |

**BUG-63 fix verified** for standard single-bottom VPM profiles.

### 2.3 VPMEngine — continuation / multi-level helpers (BUG-64 — OPEN)

| Site | Function | Pattern | Status |
|------|----------|---------|--------|
| ~8613 | `addExposureToContext` | `ctx.currentSP > 0 ? min(sp,pAmb) : ctx.currentO2 × pAmb` | ❌ |
| ~8621 | `addConstantExposure` | same | ❌ |
| ~8712 | `runRoundedDecoStop` | same for stop OTU/CNS | ❌ |

**Called from:** `runAscentSegment`, `runStopSequenceToDepth`, `appendLevelHold` (multi-level / continuation dives), `runContinuationSchedule`.

**Impact:** Multi-level pSCR VPM dives and continuation-schedule convergence passes still **overstate OTU/CNS** on bottom holds, deco stops, and linear ascents that use these helpers. Single-level recreational profiles (one depth + BT) are unaffected.

**Expected fix:** Replace the three inline formulas with `vpmAccumPpo2(pAmb, ctx.currentSP, ctx.currentO2, ctx.currentHe, settings, depth, forcedOC)` (pass appropriate `useOC` when bailout/OC segment).

### 2.4 VPM table display vs accumulation (BUG-65 — OPEN, LOW)

| Site | Function | Status | Notes |
|------|----------|--------|-------|
| ~7313 | `vpmDisplayPpo2` | ⚠️ | Calls `getEffectivePpo2` but `_vpmCcr` has **no `scrRuntimeMin`** — always shows undepleted loop ppO₂ in table |
| ~7407 | Row `_cumCNS` | ✅/⚠️ | Cumulative values from engine; correct on BUG-63 path, wrong on BUG-64 path |

Table ppO₂ column may **disagree with** toxicity integrator on long pSCR dives even after BUG-63.

### 2.5 Bühlmann `runDecoSchedule()` (BUG-66 — OPEN, MEDIUM)

| Site | Function | Status | Notes |
|------|----------|--------|-------|
| ~10439 | `rowDisplayPpo2` | ⚠️ | Routes to `getEffectivePpo2` ✅ |
| ~9739 | `_ccrPpo2Opts` | ⚠️ | Passes `_ccrSettings` **without** `scrRuntimeMin: diveRuntimeMin` |
| ~9716 | `zhlLoadLinear/Const` | ✅ | Tissue loading uses `{..._ccrSettings, scrRuntimeMin: diveRuntimeMin}` |

**Impact:** Bühlmann **tissue loading** tracks metabolic depletion, but **OTU/CNS ppO₂** for each segment uses `scrRuntimeMin = 0` → loop fractions stay at diluent values for toxicity math. Less severe than old VPM bug at depth (still uses `getEffectivePpo2`), but **under-estimates depletion** on long bottom times → **overstates** OTU/CNS vs a runtime-aware model.

**Expected fix:** `_ccrPpo2Opts` should pass `ccr: { ..._ccrSettings, scrRuntimeMin: diveRuntimeMin }`.

### 2.6 CNS tab standalone calculator (BUG-67 — OPEN, LOW)

| Site | Function | Status |
|------|----------|--------|
| ~15951 | `calcCNS()` | ⚠️ Uses `getEffectivePpo2` but `getCCRSettingsFromDOM()` never sets `scrRuntimeMin`; does not use BT as depletion proxy |

Educational CNS tab shows **undepleted loop ppO₂** for entire BT — not integrated over dive profile.

### 2.7 ZHLEngine headless fallback (BUG-68 — OPEN, LOW)

| Site | Function | Status |
|------|----------|--------|
| ~11093–11120 | Headless OTU/CNS backfill | ❌ `(hAltP + depth × BAR) × fO2bot` for descent/bottom; step loop same |

Affects automated tests / API only when `lp.totalCNS == null`.

### 2.8 Non-issues confirmed

| Item | Status |
|------|--------|
| VPM `offLoopPath` for pSCR (BUG-60) | ✅ Fixed — does not affect OTU/CNS |
| VPM gas consumption depth parsing (BUG-61) | ✅ Separate from toxicity |
| Bühlmann uses different CNS formula than VPM | By design — compare ppO₂ inputs, not raw CNS% |

---

## 3. Pre-fix overcalculation quantification (BUG-63)

Assumptions: metric, salt water (`altSurfaceP ≈ 1.013 bar`), loop 10 L, `ṀO₂ = 1.5 L/min`, descent 20 m/min included in runtime before bottom, **bottom phase only** (isolates ppO₂ model error).

| Profile | Depth | Diluent | BT | Dil ppO₂ @ depth | Loop ppO₂ @ end BT | OTU (old) | OTU (corrected) | Overcalc |
|---------|-------|---------|-----|------------------|-------------------|-----------|-----------------|----------|
| A | 20 m | Air 21% | 45 min | 0.64 bar | 0.49 bar* | 15.4 | 0.0* | **∞** (old above OTU floor, new below 0.5 bar) |
| B | 40 m | EAN32 | 30 min | 1.62 bar | 0.81 bar | 58.8 | 20.2 | **~2.9×** |
| C | 60 m | EAN36 | 20 min | 2.55 bar | 1.14 bar | 64.9 | 24.4 | **~2.7×** |
| D | 60 m | TX 18/45 | 15 min | 1.28 bar | 1.14 bar | 21.7 | 18.3 | **~1.2×** |

\*Profile A: depleted loop ppO₂ falls below the 0.5 bar OTU threshold — corrected OTU for bottom segment ≈ 0, while old model reported ~15 OTU. This is the most extreme case.

**VPM CNS% (same profiles, bottom-only, VPM rate table):** approximate overcalculation factors **5× (40 m EAN32)**, **229× (60 m EAN36)** when old ppO₂ exceeded 1.6 bar CNS clamp region — highly non-linear.

Full-dive totals (descent + bottom + deco) will differ; use Section 5 to capture live app values.

---

## 4. Recommended follow-up bugs (for next release)

| ID | Severity | Summary |
|----|----------|---------|
| **BUG-64** | MEDIUM | ✅ Fixed v2.30.15 — `vpmAccumPpo2` in continuation helpers |
| **BUG-65** | LOW | ✅ Fixed v2.30.15 — `vpmDisplayPpo2` uses `seg.runtime` |
| **BUG-66** | MEDIUM | ✅ Fixed v2.30.15 — `_ccrPpo2Opts` passes `diveRuntimeMin` |
| **BUG-67** | LOW | ✅ Fixed v2.30.15 — `calcCNS()` uses BT for pSCR |
| **BUG-68** | LOW | ✅ Fixed v2.30.15 — headless `headlessPpo2()` helper |

---

## 5. pSCR OTU/CNS validation test plan

### 5.1 Goals

1. Confirm BUG-63 fix on **single-level VPM** profiles (footer OTU/CNS drop vs v2.30.13).
2. Detect remaining **BUG-64** on multi-level VPM profiles.
3. Compare **Bühlmann vs VPM** ppO₂ inputs (not necessarily equal CNS% due to different formulas).
4. Verify table ppO₂ column vs toxicity integrator (BUG-65).

### 5.2 Standard test configuration

Apply to all scenarios unless noted:

| Parameter | Value |
|-----------|-------|
| Circuit | **pSCR** |
| Bailout | **Off** |
| Loop volume | 10 L |
| Metabolic O₂ | 1.5 L/min |
| Descent rate | 20 m/min |
| GF | 30/70 (Bühlmann) / VPM conservatism 0 |
| Algorithm | Run **both** Bühlmann ZH-L16C+GF and VPM-B |
| Units | Metric, salt water |

### 5.3 Test scenarios

#### Scenario 1 — Shallow air (OTU threshold edge)

- Depth **20 m**, diluent **Air**, BT **45 min**
- **Expected loop ppO₂ @ end of bottom:** ~0.49 bar (at `PSCR_MIN_PPO2` floor × pAmb)
- **Expected diluent ppO₂:** ~0.64 bar
- **Corrected bottom OTU (45 min @ 0.49 bar):** **0** (ppO₂ < 0.5 bar)
- **Pre-fix VPM bottom OTU:** ~**15**

#### Scenario 2 — Moderate nitrox

- Depth **40 m**, diluent **EAN32**, BT **30 min**
- Runtime at bottom end ≈ 32 min (2 min descent + 30 min BT)
- **Diluent ppO₂:** ~1.62 bar | **Loop ppO₂:** ~0.81 bar
- **Corrected bottom OTU:** ~**20** | **Pre-fix:** ~**59** (~**190% overcalc**)

#### Scenario 3 — Deep nitrox

- Depth **60 m**, diluent **EAN36**, BT **20 min**
- **Diluent ppO₂:** ~2.55 bar | **Loop ppO₂:** ~1.14 bar
- **Corrected bottom OTU:** ~**24** | **Pre-fix:** ~**65** (~**170% overcalc**)

#### Scenario 4 — Trimix (He dilution)

- Depth **60 m**, diluent **TX 18/45**, BT **15 min**
- **Diluent ppO₂:** ~1.28 bar | **Loop ppO₂:** ~1.14 bar
- Smaller relative error (~**20%** OTU overcalc pre-fix) — higher diluent fO₂ partially masks error

#### Scenario 5 — Multi-level (BUG-64 detector)

- Level 1: 30 m × 20 min, Level 2: 45 m × 15 min, pSCR on-loop, VPM-B
- Compare footer OTU to **sum of manual calculation** using `vpmAccumPpo2` per segment
- **Pass:** totals match manual sum within ±2 OTU
- **Fail (BUG-64 present):** footer OTU closer to diluent-based manual sum on level-2 bottom

#### Scenario 6 — pSCR bailout ON (OC segment)

- 40 m EAN32, BT 20 min, bailout **On**, deco on **EAN50**
- OTU during bailout/deco must use **OC ppO₂** (`fO2 × pAmb` or deco gas), not loop model
- **Pass:** switching to bailout increases reported OTU vs on-loop pSCR at same depth/gas

### 5.4 Manual validation checklist (BUG-63)

Use app v2.30.14+ at https://threecats-lsp.com/d-planner-ccr/

- [ ] **Setup:** Circuit = pSCR, bailout Off, loop 10 L, metabolic 1.5 L/min
- [ ] **Scenario 2 (40 m / EAN32 / 30 min):** Algorithm = VPM-B → Run plan
- [ ] **Footer OTU** is **≤ 25** (order-of-magnitude check; full dive includes deco)
- [ ] Compare to v2.30.13 same profile: footer OTU **decreases** materially
- [ ] **Table PPO2 column** on bottom row: compare to diluent ppO₂ — should be **lower** on long BT (may still show undepleted value if BUG-65 open)
- [ ] Switch algorithm to **Bühlmann** same profile → Run plan
- [ ] Bühlmann footer OTU **≤ VPM** for same pSCR profile (Bühlmann uses runtime-aware tissues but may still overstate OTU until BUG-66)
- [ ] **CNS tab:** enter 40 m / 32% O₂ / 30 min — note ppO₂; compare to deco table (expect mismatch until BUG-67)
- [ ] **Scenario 5:** two-level VPM profile — if footer OTU ≈ diluent-based estimate, **BUG-64 still open**

### 5.5 Automated / console validation (optional)

After running a VPM plan in browser console:

```js
// Reference: compute expected loop ppO₂ at depth with runtime
function auditPpo2(depthM, fO2, runtimeMin, fHe = 0) {
  const pAmb = altSurfaceP + depthM * BAR_PER_METRE;
  const ccr = { circuit: 'pSCR', scrRuntimeMin: runtimeMin,
    scrLoopVolume: parseFloat(document.getElementById('ccrLoopVolume')?.value) || 10,
    scrMetabolicO2: parseFloat(document.getElementById('ccrMetabolicO2')?.value) || 1.5 };
  const loop = getEffectivePpo2(pAmb, 0, fO2, ccr, depthM, fHe);
  const dil = fO2 * pAmb;
  return { pAmb: pAmb.toFixed(3), diluent: dil.toFixed(3), loop: loop.toFixed(3),
           ratio: (dil / loop).toFixed(2) };
}
// Example: 40 m, EAN32, 32 min on-loop
auditPpo2(40, 0.32, 32);
```

Compare `window._lastVPMResult?.totalOTU` or footer OTU to manual integration using `loop` ppO₂ values per segment.

### 5.6 Test suite integration (recommended)

**Dedicated suite:** `tests-pscr-otu-cns.html` (36 tests, v2.30.15) — supersedes the inline checklist below for automated CI/browser runs. Validation report: `pSCR_gas_consumption_validation_v2.30.15.md`.

Add to `tests-verify.html` Section I · CCR (optional smoke):

| Test ID | Description | Pass criterion |
|---------|-------------|----------------|
| **C4-OTU-1** | VPM pSCR 40 m EAN32 30 min footer OTU | OTU < 80 (sanity); OTU < v2.30.13 baseline if regression stored |
| **C4-OTU-2** | `auditPpo2(40, 0.32, 32).loop` < diluent | loop ppO₂ < fO2×pAmb |
| **C4-OTU-3** | Multi-level VPM pSCR | Footer OTU within 10% of `vpmAccumPpo2` segment sum (post BUG-64) |
| **C4-OTU-4** | Bühlmann pSCR same profile | Footer OTU ≤ VPM footer OTU + 15 (tolerance until BUG-66) |

Add audit.py GROUP 48 guard: `addExposureToContext` must call `vpmAccumPpo2` (post BUG-64).

### 5.7 Sign-off criteria for next release

| Criterion | Required |
|-----------|----------|
| BUG-63 paths (6 sites) pass checklist §5.4 | ✅ Done v2.30.14 |
| BUG-64 fixed or documented waiver | Required for multi-level pSCR accuracy |
| Scenario 2 OTU drop ≥ 50% vs pre-fix VPM | ✅ Expected |
| No regression: OC / CCR / bailout OTU unchanged | Required |
| Bühlmann + VPM same ppO₂ routing architecture | Target v2.30.15 |

---

## 6. Appendix — file locations

| Symbol | File | Lines (approx.) |
|--------|------|-----------------|
| `computePSCRFractions` | `index.html` | 5757 |
| `getEffectivePpo2` | `index.html` | 5864 |
| `vpmAccumPpo2` | `index.html` | 8496 |
| `addExposureToContext` | `index.html` | 8605 |
| `rowDisplayPpo2` | `index.html` | 10439 |
| `_ccrPpo2Opts` | `index.html` | 9739 |
| `vpmDisplayPpo2` | `index.html` | 7313 |
| `calcCNS` | `index.html` | 15951 |

---

*Audit prepared for pre-release pSCR OTU/CNS consistency review. Implement BUG-64–68 before declaring full cross-model parity.*
