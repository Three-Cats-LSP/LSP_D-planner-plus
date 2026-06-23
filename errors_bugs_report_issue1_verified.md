# LSP D-Planner + CCR — Issue #1 Fix Verification

**Repo:** `Three-Cats-LSP/LSP_D-planner-CCR`  
**Fix commit:** `18ab1de`  
**Date:** 2026-06-22  
**Audit result:** 401 passed, 0 failed (was 387 before)

All 9 production bugs from Issue #1 confirmed fixed. Details below.

---

## Verification

| # | Bug | Fix | Status |
|---|-----|-----|--------|
| BUG-86 | pSCR trimix fractions sum to ~2.0 | `sourceInert = fHe + fN2src` (not `1-fO2-fHe`); `heShare = fHe/sourceInert` | ✅ Fixed |
| BUG-87 | Unit system not persisted | `__units__` saved in `save()`, restored first in `load()` before field restore | ✅ Fixed |
| BUG-88 | PSCR_MIN_PPO2 model inconsistency | `minLoopO2BarLiters = PSCR_MIN_PPO2 × loopVol` (no pAmb) → true 0.16 bar floor at all depths | ✅ Fixed |
| BUG-89 | No depth/BT input validation | `validateDecoInputs()`: depth 0–100 m/330 ft, BT 0–999 min, blocks on failure | ✅ Fixed |
| BUG-90 | EAN80 missing from gas selects | `<option value="ean80">EAN80 (80%)</option>` added to dg1Mix and dg2Mix | ✅ Fixed |
| BUG-91 | `renderTissueLoadChart` reads wrong DOM IDs | `gfHighInput` and `algorithmSelect` used; fallback to `mGF.high` | ✅ Fixed |
| BUG-92 | Rec export gas reads `'gas'` not `'gasMix'` | `getElementById('gasMix')` | ✅ Fixed |
| BUG-93 | PWA manifest hardcodes GitHub Pages path | `"start_url": "./"`, `"scope": "./"` | ✅ Fixed |
| BUG-94 | SW offline fallback `Promise \|\| Promise` | `.then(cached => cached \|\| caches.match(OFFLINE_INDEX, ...))` | ✅ Fixed |

---

## Key Fix Details

### BUG-86 — pSCR trimix fraction normalization

**Before:** `fInert = 1 - fO2 - fHe` (N₂ only) → `heShare = fHe/fN2` → sum > 1  
**After:** `sourceInert = fHe + fN2src` (total inert) → `heShare = fHe/sourceInert` → sum = 1.0

Verified for Tx 18/45 at t=0: `fHe=0.4500, fN2=0.3700, fO2=0.1800, sum=1.0000` ✓

### BUG-88 — True 0.16 bar ppO₂ floor

**Before:** `minLoopO2 = 0.16 × loopVol × pAmb` → min fO₂=16% → min ppO₂ rises with depth  
**After:** `minLoopO2BarLiters = 0.16 × loopVol` → min ppO₂=0.16 bar at all depths

Verified: pAmb=1 bar → ppO₂_min=0.16; pAmb=4 bar → ppO₂_min=0.16; pAmb=7 bar → ppO₂_min=0.16 ✓

---

## Infrastructure Fixes

| Item | Fix | Status |
|------|-----|--------|
| T-1 — pSCR suite had no He tests | Section G added: 3 trimix pSCR tests with fraction normalization invariants | ✅ Fixed |
| T-3 — Playwright E2E fails via `file://` | `validate_pscr_e2e.py` now starts local HTTP server before test | ✅ Fixed |
| T-4 — No CI safety gates | `.github/workflows/audit.yml` added — runs `audit.py` on push/PR | ✅ Fixed |
| T-5 — Stale audit count in docs | 401 checks (updated in `pSCR_validation_v2.30.30_release.md`) | ✅ Fixed |

## Remaining

**T-2 — `tests-verify.html` 1 failure** (40m/25min Air GF30/85 RT=66 vs pinned 63, delta 3 min): not addressed in this commit. Needs separate investigation (stop-rounding or transit-mode drift).

---

**No new bugs introduced.** The 401-check audit passes clean.

