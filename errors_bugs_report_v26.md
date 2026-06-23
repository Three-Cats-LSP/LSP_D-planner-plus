# LSP D-Planner+CCR — Errors & Bugs Report v26

**App version audited:** v2.30.30  
**Audit date:** 2026-06-21  
**Previous report:** errors_bugs_report_v25.md (v2.30.30 — BUG-76 open)  
**Audit tool:** audit.py — 383 checks, 0 failures  
**Commits audited:** `d9be08c` (v25 baseline) → `b753acb` (v2.30.30)

---

## Summary

Two commits applied the BUG-76 patch:

- `da50845` — `VPMEngine._setHeHT1` added (compartment 0 only)
- `f0e8142` — upgraded to `VPMEngine._syncHeHalfTimes` (all 16 compartments)

**BUG-76 confirmed fixed. 0 new bugs found. All 76 CCR repo bugs now closed.**

---

## BUG-76 Fix Verification ✅

### `VPMEngine._syncHeHalfTimes` (commit `f0e8142`)

```js
_syncHeHalfTimes: function(htArray) {
    for (let i = 0; i < 16 && htArray && i < htArray.length; i++) {
        if (ZHL16C_He[i]) {
            const v = htArray[i];
            ZHL16C_He[i].ht = (v != null && typeof v === 'object') ? v.ht : v;
        }
    }
},
```

- Syncs all 16 `ZHL16C_He[i].ht` in-place ✅
- Handles both raw number (`1.88`) and object (`{ht: 1.88}`) input ✅
- `_setHeHT1` retained as backwards-compatible shortcut ✅

### `updateHeHalfTime` call chain

- Prefers `_syncHeHalfTimes(src)` with fallback to `_setHeHT1(src[0])` ✅
- `src` is the full 16-element `ZHL16C_HE_HT_BAKER` or `ZHL16C_HE_HT_BUHL2003` array ✅
- Only compartment [0] differs between Baker and Bühlmann 2003 (1.88 vs 1.51 min) — all 15 others identical ✅

### Startup sync

`updateHeHalfTime()` is called twice on page load:
1. Immediately after `appSettings.load()` — syncs global `ZHL16C_HE_HT` array and VPMEngine
2. After 1-second render retry — catches the case where VPMEngine wasn't ready on first call

`typeof window.VPMEngine._syncHeHalfTimes === 'function'` guard prevents errors if
VPMEngine is not yet ready on first call — retry at 1 s catches it. ✅

### Parity confirmed

| Setting | Bühlmann He[0] ht | VPMEngine He[0] ht | Match |
|---------|------------------|--------------------|-------|
| `baker` | 1.88 min | 1.88 min | ✅ |
| `buhl2003` | 1.51 min | 1.51 min | ✅ |

---

## Full Audit — All Areas Clean

All areas unchanged from v25 audit — diff is 19 lines in `index.html` (BUG-76 fix only).

- CCR engine logic (pSCR, setpoint, tissue loading): ✅
- Gas plan / gas consumption (CCR/pSCR/imperial): ✅
- Exports (PDF, text, messenger, slate): ✅
- UI / settings / persistence (`DECO_FIELDS` complete): ✅
- VPM vs Bühlmann He half-time parity: ✅ (now fully resolved)
- `audit.py` 383 checks, 0 failures: ✅

---

## New Bugs Found

**None.**

---

## Carry-Over OC Main Bugs (out of scope for CCR repo)

| Bug | Description | Repo |
|-----|-------------|------|
| BUG-40 | Bühlmann emergency gas `sz` not converted cu ft→L (~line 9789) | LSP_D-planner |
| BUG-41 | `appSettings.clear()` only removes `lspDiveSettings_v3` (~line 16449) | LSP_D-planner |

---

## All CCR Repo Bugs — Cumulative Status

| Report | Version | Bugs | Status |
|--------|---------|------|--------|
| v1–v25 | – v2.30.30 | BUG-01–75, BUG-77–84 | ✅ All fixed |
| v25 | v2.30.30 | BUG-76 | ✅ Fixed (v2.30.30, `f0e8142`) |
| **v26** | **v2.30.30** | **0 new bugs** | **✅ Clean — all 84 bugs closed** |
