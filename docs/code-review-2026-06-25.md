# LSP D-Planner Plus — Code Review Report
**Date:** 2026-06-25  
**Repo:** [Three-Cats-LSP/LSP_D-planner-plus](https://github.com/Three-Cats-LSP/LSP_D-planner-plus)  
**HEAD:** `6a7a029`  
**Reviewer:** Perplexity AI automated code review  
**Scope:** Full codebase review following closure of Issues #15–#18. All engine files, bridge, service worker, CSS, and HTML audited.

---

## Executive Summary

All six issues flagged in the initial v2.50 review are **confirmed resolved** in the current HEAD. The codebase is in a clean, production-ready state for continued v2.50/v2.51 development. No new safety-critical or correctness bugs were found in this pass.

One low-severity observation is noted (see §4).

---

## 1. Previously Reported Issues — Resolution Status

| Issue ID | File(s) | Description | Status |
|---|---|---|---|
| 🔴 VPM build-source guard | `vpm-engine-core.js` | Missing "BUILD SOURCE ONLY" header → risk of accidental direct load | ✅ **Fixed** |
| 🔴 `vpmAccumPpo2` scope | `vpm-engine-core.js`, `vpm-engine-bundle.js` | Function nested inside `calculate()` instead of module scope | ✅ **Fixed** |
| 🟡 `runInterLevelDecoAscent` runtime | `vpm-engine-core.js`, `vpm-engine-bundle.js` | `runtime +=` recalculated from depth delta instead of using `ascSegTime` return value | ✅ **Fixed** |
| 🟡 Continuation level guard | `zhl-schedule-core.js` | No depth-ordering guard on `_zhlContLevels` — deeper continuation silently under-loads tissues | ✅ **Fixed** |
| 🟡 Worker lifecycle | `zhl-worker-bridge.js` | No `terminate()` exposed — worker leaked on page destroy, pending map could accumulate | ✅ **Fixed** |
| 🟡 SW cache / APP_VERSION decoupling | `sw.js` | `CACHE_VERSION` was a hardcoded string, not derived from `APP_VERSION` | ✅ **Fixed** |

### Issue #18 CSS fix (`#decoAlerts` / `#decoAlertsEmergency`)
The CSS stretch bug caused by both alert containers living **outside** `.deco-schedule-stack` (and therefore not matched by the Issue #17 rules) is confirmed resolved via:

```css
#decoResult #decoAlerts,
#decoResult #decoAlertsEmergency {
  width: fit-content;
  max-width: 100%;
}
```

Selector scope is now correct — both IDs are children of `#decoResult`, not `.deco-schedule-stack`. The audit counter `477/477` confirms full CSS selector coverage.

---

## 2. Fix Verification Details

### 2.1 `sw.js` — Cache version now derived from `APP_VERSION`

```js
// BEFORE (hardcoded — stale assets risk on version bump)
const CACHE_VERSION = 'lsp-dplanner-plus-v2.50.00';

// AFTER (dynamic — single source of truth)
importScripts('app-version.js');
const CACHE_VERSION = 'lsp-dplanner-plus-v' + APP_VERSION;
```

`app-version.js` is the single source of truth (`APP_VERSION = '2.51.05'` at HEAD). The SW `importScripts` call runs synchronously at worker install time, so `APP_VERSION` is guaranteed available before `CACHE_VERSION` is evaluated. ✅

### 2.2 `zhl-worker-bridge.js` — `terminate()` now exposed

```js
function terminate() {
  [...pending.entries()].forEach(([id]) => {
    settlePending(id, false, new Error('ZHL worker terminated'));
  });
  if (worker) {
    worker.terminate();
    worker = null;
  }
}

global.ZhlWorkerBridge = { calculateInWorker, terminate };
```

All pending promises are rejected with a typed `Error` before the worker is terminated and nulled. `getWorker()` will recreate cleanly on next call. ✅

### 2.3 `vpm-engine-core.js` — Build-source header present

```js
/**
 * VPM engine core (Tier 3) — BUILD SOURCE ONLY.
 * Not loaded by index.html at runtime.
 * Rebuilt into vpm-engine-bundle.js via tools/build_vpm_bundle.py.
 */
```

Mirrors the ZHL equivalent. ✅

### 2.4 `vpmAccumPpo2` — Now at module scope

Function is defined at the same indentation level as `calculate()` in both `vpm-engine-core.js` and `vpm-engine-bundle.js`. The refactor trap (accidental scope loss on `calculate()` boundary movement) is eliminated. ✅

### 2.5 `runInterLevelDecoAscent` — Uses `ascSegTime` return value

```js
// BEFORE
runtime += Math.abs(stopDepth - nextStopClamped) / decoAscentRate;

// AFTER
const ascSegTime = loadTissuesLinear(...);
runtime += ascSegTime;
```

CCR profiles with setpoint crossings mid-segment will now accumulate runtime correctly. ✅

### 2.6 `zhl-schedule-core.js` — Continuation level depth guard

```js
if (cont.depth > cur) {
  throw new Error('continuationLevel must be shallower than current depth');
}
```

Invalid profiles that would silently under-load tissues now fail explicitly. ✅

---

## 3. Engine Correctness — Full Re-verification

All decompression algorithm constants and logic paths re-checked at HEAD:

### ZH-L16C Engine (`zhl-engine-bundle.js`)

| Check | Result |
|---|---|
| ZHL16C_N2 / ZHL16C_He tissue tables | ✅ Match Bühlmann ZH-L16C (Baker 2003) |
| GF anchor at first required stop | ✅ Dynamic — Baker/ApexDeco compliant |
| CNS/OTU above 1.6 bar ppO2 | ✅ No longer silently clamps to 45 min |
| Surface interval off-gassing | ✅ `WATER_VAPOR` fallback dead code removed |

### CCR Core (`zhl-ccr-core.js`)

| Check | Result |
|---|---|
| pSCR Baker drop formula | ✅ `ppO2_loop = ppO2_supply - VO2/loopVol` (steady-state) |
| Descent setpoint threshold | ✅ `pAmb <= bottomSP` (was `pAmb <= descSP + 0.76`) |
| CCR setpoint transitions | ✅ `getEffectiveSetpointAtDepth` correct |

### VPM-B Engine (`vpm-engine-bundle.js`)

| Check | Result |
|---|---|
| Physical constants | ✅ `GAMMA=0.0179`, `GAMMA_C=0.257`, `r_N2=0.55e-6`, `r_He=0.45e-6` |
| Altitude radii (Feature A) | ✅ `r_alt = r_0 × (P_SL/P_alt)^(1/3)` applied at init and conservatism override |
| Repetitive bubble regeneration (Feature B) | ✅ Exponential decay toward `initRadN2/He`, `REGEN_TIME=20160 min` |
| Boyle's law compensation | ✅ Bisection solver: 80 iterations, `1e-18` tolerance — numerically stable |
| `selectDecoGas` `allowO2AtMOD` | ✅ Reads `settings.allowO2AtMOD !== false` — pure O2 at MOD reachable |
| `calculateOTU` `OTU_EXPONENT` | ✅ Hardcoded `0.8333` — no longer a free variable |
| `calcSurfacePhaseVolumeTime` log guard | ✅ `logArg <= 0` guard prevents `-Infinity` |

---

## 4. New Observations (Low Severity)

### OBS-1: `zhl-worker-bridge.js` — `onerror` does not null worker before iterating pending

```js
worker.onerror = function (err) {
  const msg = (err && err.message) || 'Worker error';
  [...pending.entries()].forEach(([id]) => {
    settlePending(id, false, new Error(msg));   // ← settlePending calls pending.delete(id)
  });
  worker = null;   // ← nulled after iteration (correct)
};
```

This is safe — `settlePending` removes from `pending` by ID, and the spread `[...pending.entries()]` is a snapshot taken before iteration begins. No race condition exists in single-threaded JS. No change required; noted for clarity.

### OBS-2: `capacitor-bridge.js` — `uniqueFilename` loops up to 999

The collision-avoidance loop (`for i = 1; i <= 999`) will fall back to the original filename if 999 duplicates exist. This is a cosmetic edge case with no safety impact.

### OBS-3: `app-version.js` — Double CRLF line endings (`\r\r\n`)

The file contains `\r\r\n` line endings (visible in raw content). This is harmless at runtime but may cause diff noise. A one-time `dos2unix` pass would clean it up.

---

## 5. Overall Verdict

| Category | Status |
|---|---|
| Engine correctness (ZHL, VPM, CCR) | ✅ Clean |
| Worker lifecycle and error handling | ✅ Clean |
| Service worker cache management | ✅ Clean |
| CSS layout (decoAlerts scope) | ✅ Clean |
| Build source file guards | ✅ Clean |
| New issues found (safety/correctness) | ✅ None |
| New issues found (low severity) | 3 observations (cosmetic / no action required) |

The repository is confirmed production-ready at HEAD `6a7a029` for continued v2.51 development. All previously reported engine, worker, SW, and UI bugs are resolved.

---

*Report generated by Perplexity AI automated code review · LSP D-Planner Plus v2.51.05*
