# LSP D-Planner + CCR — Errors & Bugs Report v4

**Repo:** `Three-Cats-LSP/LSP_D-planner-CCR`  
**Version analysed:** v2.30.0 post-fix-4  
**Date:** 2026-06-20  
**Audit result:** 271 checks (run after fix commit)  
**Scope:** Fourth verification pass + full on-loop CCR profile fix.

---

## FIXED in this pass

### CCR-PROFILE — On-loop CCR plans incorrectly showed OC deco gas switches (EAN50, O2)

**Root cause:** `zhlOnLoopAt()` returned `false` when configured OC deco gases had higher ppO₂ than the CCR setpoint, causing the Bühlmann engine to switch to OC gases during deco stops. Export/header always listed deco gases via `getDecoGasSwitches()`.

**Fix:** Stay on-loop for entire non-bailout CCR profile; use diluent via `zhlGasAt()`; suppress deco gas header/export/table switch rows; VPM `maybeSwitchDecoGas()` and legacy loop skip OC switches when on-loop.

---

### BUG-23 — Dive graph ceiling overlay uses OC tissue loading for CCR dives

**Status:** FIXED — ceiling waypoints use `zhlLoadLinear` / `zhlLoadConst` when `_zhlOnLoop`.

---

### BUG-24 — Multi Dive Day Plan tab uses OC air tissue loading

**Status:** FIXED — `runUnifiedPlan()` uses `loadTissuesWithCCR()` for CCR/pSCR on-loop; dynamic disclaimer in info box.

---

### BUG-25 — pSCR circuit shows CCR setpoint UI fields that are unused

**Status:** FIXED — setpoint rows shown only when `circuit === 'CCR'`, not pSCR.

---

### BUG-26 — Multi Dive export header missing `+ CCR`

**Status:** FIXED — header now `LSP D-PLANNER + CCR - MULTI DIVE DAY PLAN`.

---

## Summary Table

| # | Severity | Area | Description | Status |
|---|---|---|---|---|
| CCR-PROFILE | HIGH | CCR/Engine | OC deco gas switches in on-loop CCR plans | FIXED |
| BUG-23 | HIGH | CCR/Graph | Ceiling overlay used OC loading | FIXED |
| BUG-24 | MEDIUM | CCR/Multi-dive | Multi Dive used hardcoded OC air | FIXED |
| BUG-25 | MEDIUM | pSCR/UX | Setpoint UI shown for pSCR (no effect) | FIXED |
| BUG-26 | LOW | Branding | Multi Dive export missing + CCR | FIXED |
