# LSP D-Planner + CCR — Errors & Bugs Report v8

**Repo:** `Three-Cats-LSP/LSP_D-planner-CCR`  
**Version analysed:** v2.30.8 (commit `988812b`)  
**Date:** 2026-06-21  
**Audit result:** 271 checks, 0 failures  
**Scope:** Eighth verification pass covering commits 52b7e52 → 988812b (v7 fixes, GF preset overhaul, mode switching, SVG icons, Tools panel fixes). All 3 v7 bugs confirmed fixed. New findings below.

---

## HIGH

### BUG-40 — BUG-37 only half-fixed: Bühlmann emergency/contingency gas capacity still uses raw `sz` (no cu ft → L conversion in imperial)

**File:** `index.html`  
**Location:** Bühlmann emergency gas consumption block, line ~10703

```js
const sz  = parseFloat(document.getElementById(sId)?.value) || 0;  // cu ft in imperial — NOT converted
const pr = units === 'imperial' ? prRaw / 14.5038 : prRaw;          // correctly converted to bar
if (sz > 0 && pr > 0) cylCapacity[label] = sz * pr;                 // cu_ft × bar — still WRONG
```

The v7 fix applied `szRaw * 28.3168` to the **VPM** cylinder capacity block (line ~7487), but the identical bug in the **Bühlmann** emergency/contingency cylinder capacity block at line ~10703 was not fixed. Both blocks should apply the same conversion.

**Impact:** In imperial mode, the Bühlmann emergency gas sufficiency check (the table that appears when running the +3m/+5m contingency plan) still produces `cu_ft × bar` instead of `L × bar`, making the sufficiency column meaningless in imperial.

---

## MEDIUM

### BUG-41 — `appSettings.clear()` removes wrong localStorage key — settings never actually cleared

**File:** `index.html`  
**Location:** `appSettings.clear()` line ~17476

```js
clear: function() {
  localStorage.removeItem('lspDiveSettings_v3');  // ← WRONG — this key no longer exists
}
```

Settings are saved to and loaded from `'lspDiveSettings_v6'` (lines 17372, 17395). The cleanup block in `load()` already removes `v3` as an old key. `clear()` therefore silently does nothing when called — user settings persist across the "reset".

Also: a separate `localStorage.removeItem('lspDiveSettings_v6')` exists at line 7035 (inside `runVPMSchedule`), suggesting this was the intended key for `clear()` but was never propagated.

**Impact:** Any future "Reset to defaults" UI button wired to `appSettings.clear()` will appear to succeed (logs "✅ Settings cleared") but leave `lspDiveSettings_v6` intact. On next reload all settings come back. Currently `clear()` is not called from any UI element — but it is a latent bug waiting to surface.

---

## LOW

### BUG-42 — `_restoreFields()` restores every field twice with a 100 ms delay, firing `change` events on the second pass

**File:** `index.html`  
**Location:** `appSettings._restoreFields()` lines ~17450–17455

```js
allPossible.forEach(id => {
  restoreOne(id);           // immediate: sets value, dispatches 'change'
  setTimeout(() => restoreOne(id), 100);  // 100ms later: sets again, dispatches 'change' again
});
```

Each field fires a `change` event twice (immediate + 100ms). Fields with `onchange` handlers that trigger expensive operations (e.g. `updateGasMODDisplays`, `runDecoSchedule`, `updateCcrGasValidation`, `calcGasPlan`) are called twice per field across all ~60 fields in `DECO_FIELDS`. This creates a burst of ~120 change events on every page load and every settings restore.

**Impact:** Noticeable sluggishness on load, especially on mobile (Android APK). The deferred pass is intended as a safety net for fields that are not yet in the DOM at `DOMContentLoaded`, but the 100ms interval is not long enough to be reliable for that purpose anyway. Additionally, if the user begins interacting with the app within 100ms of load, the deferred restore can overwrite their first input.

---

## Summary Table

| # | Severity | Area | Description |
|---|---|---|---|
| BUG-40 | HIGH | Gas plan/Imperial | Bühlmann emergency gas capacity still omits cu ft → L conversion (VPM fixed, Bühlmann not) |
| BUG-41 | MEDIUM | Settings | `appSettings.clear()` removes wrong key `v3` — settings never cleared |
| BUG-42 | LOW | Settings/Performance | `_restoreFields()` restores every field twice, firing ~120 `change` events on every load |

