# LSP D-Planner + CCR — Issue #1 Response: Deep Audit Findings

**Repo:** `Three-Cats-LSP/LSP_D-planner-CCR`  
**Version analysed:** v2.30.30 (post-release external audit)  
**Date:** 2026-06-22  
**Source:** GitHub Issue #1 — external deep audit  
**Audit result:** 387 checks, 0 failures (static checks do not catch runtime bugs)

All 9 production findings independently verified against the codebase. Results below.

---

## CRITICAL

### BUG-86 — pSCR trimix fractions sum to ~2.0 — `computePSCRFractions()` uses N₂ fraction as inert denominator

**File:** `index.html` line ~5800  
**Status:** ✅ Confirmed

```js
const fInert = Math.max(0, 1 - fO2 - fHe);  // ← this is fN2, not total inert
const heShare = fHe / Math.max(0.001, fInert);   // fHe / fN2 — > 1 for trimix
const n2Share = (1 - fO2 - fHe) / Math.max(0.001, fInert);  // = 1.0 always
```

For Tx 18/45 at 4 bar, runtime 0:
- `fInert = 0.37` (N₂ only)
- `heShare = 0.45 / 0.37 = 1.216`
- `n2Share = 0.37 / 0.37 = 1.000`
- Result: `fO2=0.18, fHe=0.997, fN2=0.820` — **sum = 1.997**

The impossible fractions propagate into Schreiner inspired inert pressures for both engines, making pSCR trimix tissue loading and OTU/CNS tracking incorrect.

**Fix:** Use total inert fraction `(1 - fO2)` as denominator:
```js
const srcInert = Math.max(0.001, 1 - fO2);
const heShare = fHe / srcInert;
const n2Share = (1 - fO2 - fHe) / srcInert;
```

---

### BUG-87 — Unit system not persisted — imperial values restored as metric on reload

**File:** `index.html` `DECO_FIELDS` ~line 17541  
**Status:** ✅ Confirmed

`DECO_FIELDS` saves converted depth/pressure/SAC values but does not include the unit selector field. On reload the app starts in metric and restores raw converted numbers as metric values (131 ft → 131 m, 3000 psi → 3000 bar, 0.7 cu ft/min → 0.7 L/min).

**Fix:** Add `'units'` (or equivalent unit selector ID) to `DECO_FIELDS`, and in `appSettings.load()` restore units *before* restoring numeric field values.

---

## HIGH

### BUG-88 — `PSCR_MIN_PPO2 = 0.16` applied as fraction floor at tissue level, not ppO₂ floor — inconsistent with documentation

**File:** `index.html` lines 5696, 5796, 5902  
**Status:** ✅ Confirmed

Line 5796: `minLoopO2 = PSCR_MIN_PPO2 * loopVol * pAmb` → minimum loop fO₂ = 0.16 (fraction floor)  
Line 5902: `Math.max(PSCR_MIN_PPO2, fr.fO2 * pAmb)` → minimum ppO₂ = 0.16 bar (pressure floor)

These are two different models. The documentation and safety certification describe a "0.16 bar ppO₂ floor", but the tissue-loading path (line 5796) implements a 0.16 fraction floor, making the effective minimum ppO₂ rise linearly with depth (0.16 bar at 10m → 1.12 bar at 70m).

**Decision required:** Choose one model and make all code + documentation consistent:
- **Fraction floor (current tissue path):** minimum loop fO₂ = 16% — physiologically reasonable as a scrubber-CO₂-limited floor
- **Pressure floor (display path):** minimum ppO₂ = 0.16 bar — matches the documented "0.16 bar" language

---

### BUG-89 — No input validation for depth and bottom time — negative/extreme values generate plans

**File:** `index.html` lines ~9759–9762  
**Status:** ✅ Confirmed

```js
const rawD = parseFloat(document.getElementById('decoDepth').value) || 40;  // -10 passes
const bt   = parseInt(document.getElementById('decoBT').value) || 30;        // -5 passes
```

Verified: `-10 m / 30 min` produces a plan (zero stops). `40 m / -5 min` produces a 1-min plan. `999 m / 999 min` produces a 5894-min 265-stop plan.

**Fix:** Add guards before either engine runs:
```js
if (depthM <= 0 || !isFinite(depthM) || depthM > 330) { /* alert and return */ }
if (bt <= 0 || !isFinite(bt) || bt > 600) { /* alert and return */ }
```

---

### BUG-90 — `EAN80` option missing from dg1Mix/dg2Mix selects — ZHLEngine headless silently uses wrong gas

**File:** `index.html` lines 2242–2248, 11260, 7229  
**Status:** ✅ Confirmed

`ZHLEngine.calculate()` sets `mixEl.value = 'ean80'` (line 11260) but the `dg1Mix` select has no `'ean80'` option — only `none`, `ean50`, `o2`, `custom`, `trimix`. Setting `.value` to a non-existent option silently leaves the select at its previous value; ZHLEngine continues with the previous gas instead of EAN80.

VPM engine correctly computes `fO2 = 0.80` directly from the gas array and does not use the DOM select — hence the cross-engine divergence described in the issue.

Line 7229: `mixEl.value === 'ean80' ? 20` — also references the non-existent value.

**Fix:** Add `<option value="ean80">EAN80 (80%)</option>` to both dg1Mix and dg2Mix selects, and update `toggleDecoCustomO2` handling. Alternatively: use the `custom` mode with O₂%=80 in the headless setter.

---

### BUG-91 — `renderTissueLoadChart()` reads non-existent DOM IDs — always uses GF High 80

**File:** `index.html` line 13478  
**Status:** ✅ Confirmed

```js
const gfHigh = (parseFloat(document.getElementById('gfHighSel')?.value) || 80) / 100;
const algo   = document.getElementById('algoSel')?.value || 'ZHLC_GF';
```

Neither `gfHighSel` nor `algoSel` exist. The actual elements are `gfHighInput` and `algorithmSelect`. The `?.value` optional chain returns `undefined`, falling through to the `|| 80` default. Tissue saturation chart always calculates against GF High = 80% regardless of the user's configured value.

**Fix:** Replace with `document.getElementById('gfHighInput')` and `document.getElementById('algorithmSelect')`.

---

### BUG-92 — Rec mode text export reads `getElementById('gas')` — element is `'gasMix'` — gas line always blank

**File:** `index.html` lines ~14318, 1488  
**Status:** ✅ Confirmed

```js
const gasEl  = document.getElementById('gas');           // ← doesn't exist
const gasStr = gasEl?.options[gasEl?.selectedIndex]?.text || '';  // always ''
```

The actual Rec mode gas selector has `id="gasMix"`. The export therefore always emits an empty gas line.

**Fix:** Change to `document.getElementById('gasMix')`.

---

## MEDIUM

### BUG-93 — PWA manifest hardcodes GitHub Pages path — app doesn't install correctly at threecats-lsp.com

**File:** `manifest.json` lines 5–6  
**Status:** ✅ Confirmed

```json
"start_url": "/LSP_D-planner-CCR/",
"scope":     "/LSP_D-planner-CCR/"
```

The production URL is `https://threecats-lsp.com/d-planner-ccr/`. The manifest scope at `/LSP_D-planner-CCR/` means the PWA install prompt and service worker scope don't match the actual origin path.

**Fix:** Use relative paths (`"./"`) or deploy separate manifests per origin.

---

### BUG-94 — Service worker offline fallback: `Promise || Promise` is always truthy — OFFLINE_INDEX never served

**File:** `sw.js` lines 95–96  
**Status:** ✅ Confirmed

```js
return caches.match(event.request, { ignoreSearch: true })
  || caches.match(OFFLINE_INDEX, { ignoreSearch: true });
```

`caches.match()` returns a `Promise` — a Promise object is always truthy. The `||` short-circuits on the first promise, meaning `OFFLINE_INDEX` is never tried when the primary cache lookup misses.

**Fix:**
```js
return caches.match(event.request, { ignoreSearch: true })
  .then(r => r || caches.match(OFFLINE_INDEX, { ignoreSearch: true }));
```

---

## Test / Infrastructure Findings

### T-1 — pSCR regression suite has zero helium scenarios — BUG-86 passes all 36 tests

**File:** `tests-pscr-otu-cns.html`  
All 36 tests use EAN32 or EAN36 (`he: 0`). The trimix fraction bug (BUG-86) produces sum=2.0 only for fHe > 0, which is why the suite passes despite the live bug. Trimix pSCR tests (e.g. Tx 18/45, Tx 21/35) must be added with fraction normalization invariants.

### T-2 — `tests-verify.html` has 1 failure: `40m/25min Air GF30/85 RT=66` vs pinned 63 min (delta 3 min, tolerance ±2)

Likely a stop-rounding or transit-mode drift. Needs investigation — the 3-min delta exceeds the ±2 min WARN threshold and is filed as a failure.

### T-3 — `dev/validate_pscr_e2e.py` fails via `file://` — engine bootstrap timeout

The Playwright script loads via `file://` URL; cross-origin restrictions block Capacitor/WASM bootstrap. Must serve via local HTTP (`python -m http.server` or equivalent) and test through `http://localhost`.

### T-4 — No CI workflow runs safety tests before Android build

`audit.py`, browser suites, and `validate_pscr_e2e.py` are not part of any CI workflow. APK is built without safety gates. A required pre-build CI step should run at minimum `audit.py` and `tests.html`.

### T-5 — README and safety certification state 383 audit checks; actual count is 387

Minor doc discrepancy — update counts in `README.md` and `SAFETY_CERTIFICATION_v2.30.30.md`.

---

## Summary Table

| # | Severity | Area | Description |
|---|---|---|---|
| BUG-86 | CRITICAL | pSCR/Trimix | `computePSCRFractions` uses N₂ as inert denominator — fractions sum to ~2.0 for any fHe > 0 |
| BUG-87 | CRITICAL | Settings | Unit system not persisted — imperial values reload as metric |
| BUG-88 | HIGH | pSCR model | `PSCR_MIN_PPO2`: fraction floor at tissue level vs ppO₂ floor at display — inconsistent with docs |
| BUG-89 | HIGH | Input | No depth/time validation — negative and extreme values produce plans |
| BUG-90 | HIGH | ZHLEngine | `EAN80` missing from gas selects — headless uses wrong gas silently |
| BUG-91 | HIGH | UI | `renderTissueLoadChart` reads wrong DOM IDs — always GF High 80 |
| BUG-92 | HIGH | Export | Rec export reads `getElementById('gas')` not `'gasMix'` — gas line always blank |
| BUG-93 | MEDIUM | PWA | Manifest hardcodes GitHub Pages path — wrong scope at threecats-lsp.com |
| BUG-94 | MEDIUM | SW | Offline fallback `Promise \|\| Promise` — OFFLINE_INDEX never served |
| T-1 | — | Tests | pSCR suite has zero He scenarios — BUG-86 undetectable by current tests |
| T-2 | — | Tests | `tests-verify.html` 1 failure: GF30/85 Air RT delta 3 min beyond ±2 tolerance |
| T-3 | — | Tests | Playwright e2e fails via `file://` — needs local HTTP server |
| T-4 | — | CI | No CI runs safety tests before Android build |
| T-5 | — | Docs | README/cert audit count stale (383 vs actual 387) |

