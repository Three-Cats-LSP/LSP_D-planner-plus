# LSP D-Planner+CCR — Final Safety Certification Memo

**Document ID:** LSP-CCR-CERT-2026-0630  
**Product:** LSP D-Planner + CCR (Rebreather Edition)  
**Release version:** **v2.30.30**  
**Certification date:** 21 June 2026  
**Production URL:** https://threecats-lsp.com/d-planner-ccr/  
**Repository:** https://github.com/Three-Cats-LSP/LSP_D-planner-CCR  
**Audit baseline:** `errors_bugs_report_v27_RELEASE.md` (full-app pre-release audit)  
**Final delta:** `errors_bugs_report_v28.md` — BUG-85 closed (`audit.py` GROUP 44)

---

## 1. Executive Summary

This memo certifies that **LSP D-Planner+CCR v2.30.30** has completed a structured, multi-pass safety verification programme covering the period **v2.30.9 through v2.30.24** (intensive pSCR/CCR hardening) and the final **v2.30.25–30** closure sprint.

Across **28 independent audit reports** (`errors_bugs_report_v1` through `errors_bugs_report_v28`), **85 verified findings (BUG-01 through BUG-85)** were identified and closed. No open safety defects remain in the CCR repository at release sign-off.

**Final verification gate:**

| Layer | Result | Date |
|-------|--------|------|
| Static analysis (`audit.py`) | **383 / 383 passed, 0 failed** | 2026-06-21 |
| Full-app pre-release audit (v27) | **RELEASE READY — 0 bugs** | 2026-06-21 |
| Post-release delta audit (v28) | **BUG-85 fixed — suite clean** | 2026-06-21 |

**Deployment recommendation:** **Approved for production deployment** to https://threecats-lsp.com/d-planner-ccr/ and community distribution (GitHub release tag `v2.30.30`).

---

## 2. Scope & Intended Use

LSP D-Planner+CCR extends the open-circuit LSP D-Planner foundation (v2.20.x) with:

- **CCR** (closed-circuit rebreather) — setpoint-aware tissue loading and gas planning
- **pSCR** (passive SCR) — GUE-style metabolic loop O₂ depletion model
- **Bailout** — OC emergency ascent planning (GF 90/90 Bühlmann)
- **Dual engines** — Bühlmann ZHL-16C+GF and VPM-B / VPM-B/GFS, both with full rebreather paths

This certification covers **computational safety** of decompression schedules, gas consumption estimates, OTU/CNS toxicity tracking, and export fidelity. It does **not** replace diver training, equipment checks, or dive-computer verification.

---

## 3. Audit History — v2.30.9 through v2.30.24

The table below summarises the verification passes that drove the pSCR safety arc from first CCR hardening (v2.30.9) through discovery of the last pre-sprint engine defect (BUG-75 at v2.30.24).

| App version | Audit report | `audit.py` checks | New bugs found | Cumulative bugs | Key safety outcome |
|-------------|--------------|-------------------|----------------|-----------------|-------------------|
| **v2.30.9** | v9 | 271 | BUG-43–50 | 50 | Metabolic rate defaults; pSCR MOD validation; imperial emergency gas; branding/PWA fixes |
| **v2.30.11** | v10 | — | BUG-51–56 | 56 | pSCR Schreiner dimension; loop gas labels; diluent flow formula branch |
| **v2.30.12** | v11 | — | BUG-57–62 | 62 | pSCR double depth-scaling; VPM off-loop conservatism; settings clear completeness |
| **v2.30.13** | v12 | — | BUG-63 | 63 | VPM primary path: diluent ppO₂ used for pSCR OTU/CNS |
| **v2.30.14** | — | — | — | 63 | `vpmAccumPpo2()` helper — primary VPM fix (BUG-63) |
| **v2.30.15** | v13 | **303** | BUG-64–68 | 68 | Full pSCR OTU/CNS path parity; dedicated `tests-pscr-otu-cns.html` suite |
| **v2.30.16** | v14–15 | **323** | BUG-69–71 | 71 | Altitude surface GF; stress reserve depth distribution; imperial SAC conversion |
| **v2.30.17–19** | v16 | **324** | BUG-72 | 72 | Imperial volume display (`gpVolDisp`) in VPM/emergency blocks |
| **v2.30.21–23** | v17–18 | **343–346** | BUG-73–74 | 74 | ZHL headless CCR setpoint ppO₂; version manifest sync |
| **v2.30.24** | v18–19 | **346** | **BUG-75 (open)** | 75 | **Critical pSCR gas formula identified** — `(metRate/fO₂_loop)×bypass` overstated diluent ~6× |

### Post-v2.30.24 closure (v2.30.25 → v2.30.30)

| App version | Report | Checks | Bugs closed | Outcome |
|-------------|--------|--------|-------------|---------|
| v2.30.26 | v20–21 | 363 | BUG-75 | pSCR diluent: `metRate × bypass` |
| v2.30.28 | v21 | 363 | BUG-76–77 | Plan-walk OTU/CNS; massive suite hang |
| v2.30.29 | v22 | 381 | BUG-78–80 | ZHL headless plan integration; iframe guards |
| v2.30.30 | v25–27 | **383** | BUG-76 (He HT), 77–84 | Deco gas persistence; dual-engine OTU parity; version sync |
| v2.30.30 | v28 | **383** | BUG-85 | Audit GROUP 44 updated for dynamic `getExportCircuitTag()` filenames |

**Audit check growth:** 271 (v2.30.9) → 303 (v2.30.15) → 346 (v2.30.24) → **383 (v2.30.30)** — each increment pins regression guards for closed bugs.

---

## 4. Safety Impact Analysis — 85 Closed Bugs

### 4.1 pSCR Metabolic Model (19 bugs)

These fixes ensure the passive SCR loop model (`computePSCRFractions` → `getEffectivePpo2`) is applied consistently for tissue loading, toxicity, ceilings, and display.

| Bug IDs | Improvement |
|---------|-------------|
| BUG-04, 07 | VPM `_scrRuntimeMin` propagation; Trimix He fraction in pSCR ppO₂ |
| BUG-25, 32 | pSCR UI hides non-applicable CCR setpoint fields |
| BUG-43 | Metabolic O₂ default **1.5 L/min** (was 0.85 in headless fallbacks) |
| BUG-44 | pSCR MOD validation uses correct on-loop ppO₂ limit |
| BUG-51 | pSCR Schreiner inert-loading rate — dimensional correction |
| BUG-56 | Diluent surface flow uses inspired loop fraction, not raw diluent fO₂ |
| BUG-57 | Removed double depth-scaling via depth-dependent fO₂_loop |
| BUG-58 | Gas plan uses runtime-aware depleted loop O₂ (not always fresh loop) |
| BUG-60 | VPM no longer treats pSCR as off-loop — ceiling conservatism restored |
| BUG-63–68 | Six VPM sites + four secondary paths route through `vpmAccumPpo2` / `getEffectivePpo2` with per-segment `scrRuntimeMin` |
| BUG-75 | **Gas draw decoupled from loop fO₂** — bypass ratio × metabolic rate only |

**Net effect:** pSCR dives now model O₂ depletion as a function of loop volume, metabolic consumption, ambient pressure, and cumulative on-loop time — with a **0.16 bar floor** — across Bühlmann, VPM, gas plan, CNS tab, headless API, and all export paths.

### 4.2 Gas Consumption Accuracy (18 bugs)

| Bug IDs | Improvement |
|---------|-------------|
| BUG-14, 19 | On-loop segments no longer charged at full OC SAC (~10–20× overstatement removed) |
| BUG-31, 35–36 | Rebreather Adv. Settings wired: stress SAC, deco CCR SAC, stress/problem-solve reserve |
| BUG-34, 70 | Bailout reserve depth-checked; distributed across bottom + deco stops |
| BUG-45–46 | CCR gas-plan label matching; `ccrGasLitres` depth scaling |
| BUG-56–58, 75 | pSCR diluent surface rate corrected end-to-end |
| BUG-61 | VPM transit rows parse max depth from `"0→40m"` arrow format |
| BUG-69 | Surface GF at altitude uses `altSurfaceP` — gas sufficiency context aligned |
| BUG-71 | Imperial SAC converted **cu·ft/min → L/min** before consumption math |
| BUG-72 | Imperial display uses `gpVolDisp()` / `gpPresDisp()` — litres no longer labelled as cu·ft |

**Net effect:** Gas Plan volumes for pSCR dives dropped from ~6–10× overstated (BUG-75) to physically consistent metabolic bypass values (~15 L/min at default 1.5 L/min O₂ × 10× bypass). Imperial-mode sufficiency comparisons are now numerically valid.

### 4.3 CNS / OTU Tracking Consistency (16 bugs)

| Bug IDs | Improvement |
|---------|-------------|
| BUG-03, 08, 13, 17 | Deco table and CNS tab use maintained setpoint / loop ppO₂, not diluent |
| BUG-50 | CNS export header includes + CCR branding |
| BUG-63–68 | Full pSCR OTU/CNS path audit — VPM + Bühlmann + headless |
| BUG-67 | Standalone CNS tab uses end-of-BT depleted loop ppO₂ for pSCR |
| BUG-73 | ZHL headless API: CCR setpoint via `getEffectiveSetpointAtDepth` (was ~40% CNS under-report) |
| BUG-77 *(exposure)* | Shared `computePlanExposureTotals()` — segment-start `scrRuntimeMin`, ascent depth interpolation |
| BUG-80 | ZHL headless reuses Bühlmann step `pO₂` baked by `_ccrPpo2Opts` |
| BUG-82 | ZHL pSCR OTU: full plan walk replaces single bottom sample — **caught by 36-test pSCR suite** |

**Net effect:** Bühlmann and VPM now produce OTU/CNS totals from the **same plan-walk engine** (`computePlanExposureTotals` / `accumulateHeadlessPlanExposure`). Export paths (text, PDF, messenger, slate, banner) source from unified totals — no divergent toxicity numbers between engines or export formats.

### 4.4 Additional Safety-Critical Closures (32 bugs)

| Domain | Bug IDs | Summary |
|--------|---------|---------|
| CCR core engine | 03, 06, 23–24, 27–30, 52, 54–55, 76, 79 | Setpoint phases, bailout GF/MOD, graph ceiling, Multi Dive CCR loading, VPM He HT sync |
| Platform / PWA | 01–02, 05, 10–12, 15–16, 18, 20, 22, 39, 74, 83–84 | Android manifest, offline cache, icons, version sync |
| Settings / UX | 59, 62, 77 *(persist)* | Bailout UI, settings clear, deco gas mix persistence |
| Export labelling | 49, 53, 85 | Circuit-aware filenames (`getExportCircuitTag()`), loop gas labels |
| Test harness | 76 *(suite)*, 78, 81 | Massive suite iframe guards, `vpmEngine()` helper |

---

## 5. Final Verified Test Results

### 5.1 Static Analysis — `audit.py` (383 checks)

**Command:** `python audit.py index.html`  
**Result:** **383 passed · 0 failed · exit code 0**  
**Verified:** 2026-06-21 (post BUG-85 fix, commit `b2ecb8d`)

| Audit group range | Domain | Representative checks |
|-------------------|--------|----------------------|
| GROUP 1–14 | Core engine integrity | Structure, trimix He params, 1−fN₂ pattern, hoisting, export consistency, critical safety rules |
| GROUP 15–33 | OC foundation regressions | Canvas/mobile, altitude VPM radii, repetitive bubble carry, GF anchor, headless holdStep |
| GROUP 34–40 | v2.20.x features | Surface GF, prior carry, banner/PDF refactor, stamp order, plan summary blocks |
| GROUP 41 | **CCR / Rebreather (v2.30.0)** | `getEffectivePpo2`, `computePSCRFractions`, CCR tissue loading |
| GROUP 42–53 | **v2.30.9–19 fixes** | Imperial gas, branding, pSCR OTU helpers, `gpVolDisp`, `sacDomToLpm` |
| GROUP 54–62 | **v2.30.21–30 fixes** | Plan-walk OTU/CNS, BUG-75 regression pin, He HT sync, iframe harness guards |
| GROUP 44 *(updated)* | **BUG-85 / BUG-49** | Dynamic `LSP_${getExportCircuitTag()}_` PDF filename pattern |

### 5.2 Browser Regression Suites

| Suite | Tests | Scope | Status |
|-------|-------|-------|--------|
| [`tests-pscr-otu-cns.html`](https://threecats-lsp.com/d-planner-ccr/tests-pscr-otu-cns.html) | **36** | pSCR OTU/CNS + gas draw — 20/40/60 m × EAN32/EAN36 × VPM + Bühlmann; Sections A–F | Pass |
| [`tests-massive.html`](https://threecats-lsp.com/d-planner-ccr/tests-massive.html) | **376+** | Full engine plans, UI/DOM, travel gas, altitude, gas plan, T3-CCR MultiDeco RT | Pass |
| [`tests-massive-main.html`](https://threecats-lsp.com/d-planner-ccr/tests-massive-main.html) | **376+** (mobile subset) | Same scope, mobile-optimised; iframe + `vpmEngine()` guards | Pass |
| [`tests-verify.html`](https://threecats-lsp.com/d-planner-ccr/tests-verify.html) | Sections A–I | Baker/FORTRAN reference math; **Section I · CCR / Rebreather** | Pass |
| [`tests-extended.html`](https://threecats-lsp.com/d-planner-ccr/tests-extended.html) | Extended | GF, trimix, conservatism ordering, first-stop depths | Pass |
| [`tests.html`](https://threecats-lsp.com/d-planner-ccr/tests.html) | Core | Engine presence, NDL, deco, VPM-B, CNS/OTU, edge cases | Pass |

### 5.3 Validation Documentation

| Document | Purpose |
|----------|---------|
| `pSCR_OTU_CNS_consistency_audit.md` | Code-path audit for all OTU/CNS accumulation sites |
| `pSCR_gas_consumption_validation_v2.30.15.md` | Metabolic draw vs diluent rate sign-off |
| `errors_bugs_report_v1` – `v28` | Complete audit trail (85 bugs, 28 passes) |
| `CHANGELOG.md` | v2.30.30 release notes |
| `dev/validate_pscr_e2e.py` | Optional Playwright smoke (5 pSCR profiles) |

---

## 6. Subsystem Sign-Off Matrix (v27 Full-App Audit)

All 12 subsystems verified clean at v2.30.30 pre-release:

| # | Subsystem | Result |
|---|-----------|--------|
| 1 | Bühlmann ZHL-16C engine | Pass |
| 2 | VPM-B / VPM-B/GFS engine | Pass |
| 3 | **pSCR / CCR tissue loading & OTU/CNS** | Pass |
| 4 | Gas logic (MOD, END, switches) | Pass |
| 5 | **Gas plan / consumption** | Pass |
| 6 | Multi-dive / repetitive carry | Pass |
| 7 | Altitude / water density | Pass |
| 8 | Exports (PDF, text, messenger, slate) | Pass |
| 9 | UI / settings / persistence | Pass |
| 10 | Recreational planner (PADI RDP) | Pass |
| 11 | **Regression suite infrastructure** | Pass |
| 12 | Version / service worker sync | Pass |

---

## 7. Known Limitations & Out-of-Scope Items

1. **OC main repo carry-overs** — BUG-40 and BUG-41 were fixed in the CCR fork but remain open in [LSP D-Planner](https://github.com/Three-Cats-LSP/LSP_D-planner) (OC line). They do not affect this product.

2. **Diver responsibility** — All plans must be verified against the diver's training agency standards, certification level, equipment configuration, and dive computer.

3. **Reference divergence** — MultiDeco cross-validation on trimix helium dives may show ±1–2 min RT drift due to stop-distribution differences (documented; tests use WARN tolerance).

4. **pSCR long-hold simplification** — VPM continuation helpers use end-of-segment runtime for single-point ppO₂ over long stops — known conservative simplification, not a defect.

---

## 8. Certification Statement

Based on:

- **28 independent audit passes** from v2.30.0 through v2.30.30
- **85 closed findings (BUG-01 through BUG-85)** with documented fix verification
- **383 / 383 static analysis checks passing**
- **Browser regression suites green** including the dedicated 36-test pSCR safety suite
- **Full-app pre-release audit v27: RELEASE READY — 0 open bugs**

**LSP D-Planner+CCR v2.30.30 is certified for:**

- Production deployment to https://threecats-lsp.com/d-planner-ccr/
- GitHub community release (`v2.30.30` tag)
- PWA / Android APK distribution via existing CI pipeline

---

## 9. Disclaimer

LSP D-Planner+CCR is planning software for **trained mixed-gas and rebreather divers**. It is not a substitute for proper certification, pre-dive equipment checks, team planning, or independent verification with a dive computer. Decompression planning involves inherent risk; users accept full responsibility for dive safety decisions.

---

*Three Cats LSP · Diver's Toolkit · Part of the LSP open-source diving software family*  
*Document generated from audit reports v9–v28 and `audit.py` v2.30.30 verification run.*
