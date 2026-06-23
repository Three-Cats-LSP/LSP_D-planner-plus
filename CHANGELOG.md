# Changelog

All notable changes to LSP D-Planner+ are documented here.

---

## v2.50.00 — 2026-06-24

### Release — LSP D-Planner+ unified OC + CCR

- **Merge** — CCR edition (circuit select, setpoints, pSCR, diluent/bailout gas cards, CCR-aware VPM/ZHL) combined with OC Tier-3 ZHL engine (`zhl-engine-bundle.js` + Web Worker bridge).
- **ZHLEngine** — OC open-circuit headless path uses `ZhlEngineBundle.calculate` / `calculateInWorker`; CCR/pSCR delegates to DOM-based `runDecoSchedule` with full loop physics.
- **Offline shell** — Self-hosted fonts, vendored jsPDF, local Get In Water icon (from OC 2.40).
- **Branding** — `LSP D-Planner+`, app id `com.threecats.lsp.dplannerplus`, site `threecats-lsp.com/d-planner-plus`.

- **`APP_VERSION`** — bumped to `2.50.00`.

---

## v2.40.02 — 2026-06-23

### Fixed — fully self-contained offline shell (PWA + Android APK)

- **UI fonts** — Bebas Neue, JetBrains Mono, and Outfit self-hosted under `vendor/fonts/` (no Google Fonts CDN).
- **PDF fonts** — DejaVu Sans vendored locally; Unicode PDF export works offline.
- **Partner icon** — Get In Water footer icon vendored to `vendor/icons/giw-icon-192.png`.
- **Service worker** — Install precaches all vendored fonts and icons.
- **Android APK** — `tools/sync_www.py` copies full offline asset tree (ZHL bundle, worker, vendor/) into `www/` before Capacitor sync.

- **`APP_VERSION`** — bumped to `2.40.02`.

---

## v2.40.01 — 2026-06-23

### Fixed — startup and offline risks from v2.40.00 audit (GitHub #10)

- **jsPDF** — Vendored locally at `vendor/jspdf.umd.min.js` with `defer`; app no longer blocks on cdnjs during startup.
- **Service worker** — Install precaches Tier-3 ZHL assets (`zhl-engine-bundle.js`, worker bridge, worker script), `capacitor-bridge.js`, jsPDF, manifest, and icons.
- **`zhl-schedule-core.js`** — Documented as build-source-only (not loaded at runtime).

- **`APP_VERSION`** — bumped to `2.40.01`.

---

## v2.40.00 — 2026-06-23

### Refactor — Tier 3 ZHL engine isolation (Web Worker + shared bundle)

- **`zhl-engine-bundle.js`** — Self-contained Bühlmann module (`runZhlScheduleCore`, `ZHLEngine.calculate` logic, physics tables); loaded on main thread and in the worker via `importScripts`.
- **`zhl-schedule-worker.js` + `zhl-worker-bridge.js`** — Optional async `ZHLEngine.calculateInWorker()` for isolated heap; sync `ZHLEngine.calculate()` unchanged for harnesses.
- **`index.html`** — Removed ~700-line inline core; DOM param builder stays on main thread with `environment` passed into the bundle.
- **Regression** — Worker parity probe in `engine_validation_regression.py`.

- **`APP_VERSION`** — bumped to `2.40.00`.

---

## v2.20.33 — 2026-06-23

### Refactor — Tier 2 ZHL schedule core (pure engine path)

- **`runZhlScheduleCore(params)`** — Extracted Bühlmann computation into a DOM-free function; live UI and headless API share one code path.
- **`buildZhlScheduleParamsFromDom()` / `buildZhlScheduleParamsFromEngine()`** — Adapters read the form or test settings into a params object.
- **`ZHLEngine.calculate()`** — Calls the pure core directly; no DOM save/restore, no `_zhlHeadless` wiring, no `runDecoSchedule()` mutation.
- **`runDecoSchedule()`** — Bühlmann branch delegates to core; render path unchanged.

- **`APP_VERSION`** — bumped to `2.20.33`.

---

## v2.20.32 — 2026-06-19

### Fixed — headless ZHL DOM field restore (GitHub #8 / BUG-1)

- **ZHLEngine.calculate()** — Save and restore `ascentRate`, `decoAscentRate`, `surfaceAscentRate`, `descentRate`, `minStopTime`, `decoStep`, `lastDecoStop`, `ppo2Bottom`, and `ppo2Deco` on all exit paths so repeated headless calls no longer overwrite the live UI.
- **Regression** — `engine_validation_regression.py` probes DOM field restore after a successful headless calculation.

- **`APP_VERSION`** — bumped to `2.20.32`.

---

## v2.20.31 — 2026-06-23

### Fixed — harness headless guard + dead error path (comparative bench BUG-2/BUG-3)

- **ZHLEngine** — Removed unreachable `No levels` return after `validateEngineInputs()` (empty profiles already return `INVALID_PROFILE`).
- **`lsp-test-harness.js` / `tests.html`** — Reassert `ctx.win._zhlHeadless = true` before and after each harness `calc()` call so repeated ZHL invocations do not leak the headless guard.

- **`APP_VERSION`** — bumped to `2.20.31`.

---

## v2.20.30 — 2026-06-21

### Fixed (GitHub #7 — invalid gas fraction validation)

- **`validateEngineInputs()`** — Shared validator for dive levels and deco gases; rejects non-finite, out-of-range, and O2+He>100% mixtures with stable codes (`INVALID_GAS_FRACTIONS`, `INVALID_DEPTH`, `INVALID_TIME`, `INVALID_PROFILE`).
- **`ZHLEngine.calculate()` / `VPMEngine.calculate()`** — Validate before any engine or DOM mutation; return structured error instead of silently clamping N2 to zero.
- **UI path** — `validateDomDecoGases()` blocks `runDecoSchedule()` when saved/restored gas fields are invalid.
- **Tests** — Section G in `tests-verify.html` covers ZHL and VPM rejection and boundary cases.
- **CI** — `engine_validation_regression.py` runs malformed-input probes on every push/PR.

- **`APP_VERSION`** — bumped to `2.20.30`.

---

## v2.20.29 — 2026-06-21

### Fixed (GitHub #5 follow-up — imperial test step size)

- **Imperial harness tests** — After v2.20.28 converted imperial depths to metres with `metric:true`, several tests still passed `stepSize:10, lastStop:10` (imperial foot defaults). Those were interpreted as 10 m stops, inflating VPM-B/GFS runtime (~1044 min). All imperial engine tests now use `stepSize:3, lastStop:3` (metre defaults) in `tests.html`, `tests-extended.html`, `tests-massive.html`, and `tests-massive-main.html`.

### Fixed (GitHub #6 — production audit)

- **Settings reload** — Persist `__units__` and restore the unit system (labels only, no value conversion) before unit-dependent fields on load.
- **Input validation** — `runPlanner()` and `runDecoSchedule()` reject empty, non-finite, non-positive, and out-of-range depth/bottom-time values with a blocking error.
- **Recreational export** — Plain-text export reads `#gasMix` instead of retired `#gas`.
- **Tissue load chart** — Uses `gfHighInput` and `algorithmSelect` instead of retired `gfHighSel` / `algoSel`.
- **PWA manifest** — `start_url` / `scope` set to `./` for deployment-relative install paths.
- **Service worker** — Offline navigation fallback chains cache lookups with `.then()` instead of `||` on Promises.

- **`APP_VERSION`** — bumped to `2.20.29`.

---

## v2.20.28 — 2026-06-21

### Fixed (GitHub #5 — test infrastructure & Android metadata)

- **Pinned ZHL regression checks** — Updated `LSP_PINNED` Bühlmann values in `tests-verify.html` for MultiDeco transit default (v2.20.25+): RT 66/96/35 for air/air/EAN50 scenarios; EAN50 first stop now 6 m.

- **Imperial engine tests** — All harness tests now pass depth in metres (`ft / 3.28084`); `metric:false` no longer misread as 130 m dives. Tightened RT range assertions in `tests.html`, `tests-extended.html`, `tests-massive.html`, and `tests-massive-main.html`.

- **Android `build.gradle`** — `versionCode`/`versionName` synced to `22028` / `2.20.28` (was stuck at 2.10.12).

- **`audit.py` Windows** — UTF-8 stdout/stderr reconfigure prevents `UnicodeEncodeError` on cp1252 consoles.

- **Audit** — GROUP 56 adds `build.gradle` version alignment check. Total: 375 checks.

- **`APP_VERSION`** — bumped to `2.20.28`.

---

## v2.20.27 — 2026-06-19

### Fixed — contingency PrT includes extra depth

- **`calcContingency()` PrT** — `_emDepthM` now adds `contExtraDepth` (metres) after `domDepthToM()`, so “went deeper” scenarios report correct PrT in live footer and all exports (text, messenger, slate, PDF).

### Added — CI

- **`.github/workflows/ci.yml`** — runs `audit.py` (374 checks) and `export_regression.py` (Playwright export/PrT suite) on push and pull requests to `main`.

- **`APP_VERSION`** — bumped to `2.20.27`.

---

## v2.20.26 — 2026-06-19

### Fixed — dynamic deco gas persistence (dg3–dg8)

- **`DECO_FIELDS`** — Added `dg3`–`dg8` mix, custom O₂, trimix O₂/He, and cylinder size/pressure fields so all dynamic deco gas cards are tracked by settings persistence.

- **`__decoGasIds__`** — `appSettings.save()` now stores the list of active deco gas card indices alongside field values.

- **`_restoreDecoGasCards()`** — New helper recreates missing dynamic cards (via `addDecoGasCard(forcedIdx)`) before field values are restored, preventing dg3+ data loss on page reload.

- **`addDecoGasCard(forcedIdx)`** — Optional index parameter supports restoring cards with saved slot IDs (including non-contiguous layouts after card removal).

- **Audit** — GROUP 59 added. Total: 373 checks, 0 failures.

- **`APP_VERSION`** — bumped to `2.20.26`.

---

## v2.20.25 — 2026-06-21

### Fixed (GitHub #4 — imperial display + reset gaps)

- **Imperial PrT fallback** — Export/messenger PrT fallbacks and contingency PrT display now convert DOM depth from feet to metres via `domDepthToM()` before `BAR_PER_METRE` multiplication (was ~3.28× too large in imperial).

- **Imperial export header rates/stops** — `buildDecoPlanHeaderData()` converts metric-stored select `.value` fields to ft for display (`domMetricValToDisp`); fixes ascent/descent rates, last stop, deco step, and min-deco depths showing wrong ft values.

- **Imperial altitude label in exports** — `altLabelDisp()` shows ft in imperial mode instead of always metres.

- **Reset to defaults gaps** — `_doResetToDefaults()` now restores `decoTransitMode`, `shallowGradient`, and `o2AtMODSelect`; calls `setAllowO2AtMOD()` after reset.

- **`decoTransitMode` fallback** — `runDecoSchedule()` default aligned with HTML default (`multideco`, was `schreiner`).

- **Advanced summary units** — Collapsed header shows ft/min and ft when in imperial mode.

- **Audit** — GROUP 58 added. Total: 332 checks, 0 failures.

- **`APP_VERSION`** — bumped to `2.20.25`.

---

## v2.20.23 — 2026-06-21

### Fixed

- **Narcosis and O₂-at-MOD settings not persisted on reload** — `n2NarcSel`, `o2NarcSel`, and `o2AtMODSelect` were in `_ADV_FIELDS` (Advanced Config presets only) but missing from `appSettings.DECO_FIELDS`, so the main save/restore path did not remember them across page loads. Added all three to `DECO_FIELDS`; `change` events on restore call `setNarcosis()` / `setAllowO2AtMOD()` as on user interaction.

- **First-run localStorage key typo** — Init block checked `lspDiveSettingsv6` (no underscore) so advanced defaults were re-applied on every load after `appSettings.load()`. Fixed to `lspDiveSettings_v6`; restored CCR first-run `setGF(20,85)` + `gfPresetSelect` / `handleGFSelect('20/85')`.

- **VPM He half-time sync (BUG-76 slice)** — Export `VPMEngine._syncHeHalfTimes()` + `_setHeHT1()`; `updateHeHalfTime()` syncs all 16 He compartments when switching Baker ↔ Bühlmann 2003.

- **VPM gas consumption in imperial (BUG-61 slice)** — Depth scrape uses `endParseDepthM()` so `"120 ft"` cells parse correctly.

- **GF preset sync** — `_gfSyncSilent`, `_findGfPresetOption()`, `syncGfPresetFromValues()`; post-load GF dropdown stays aligned with `mGF`.

- **ZHLEngine headless nesting (BUG-74 slice)** — Preserve `_zhlHeadless` via `_headlessEntry` for nested headless/API calls.

- **`shortMixLabel` (BUG-53)** — Exact `^air$` match instead of broad `/air/i`.

### Design sync (CCR shared layer)

- **Advanced Settings layout** — Replaced multi-column `form-grid` with vertical `adv-stack` / `adv-row` layout (label left, control right, one setting per row), matching CCR edition. Min-deco sub-fields use nested `adv-row`s instead of inline grid.

### Test harness

- **`lsp-test-harness.js`** — Shared dual-engine boot helper (VPM + ZHL).
- **`tests.html`** — Inlined harness, `ndlSettings()` (GF 100/100 for NDL tests), routes Bühlmann via `ZHLEngine`.
- **`tests-massive.html` / `tests-massive-main.html`** — `refreshFrameWin`, `vpmEngine`, `keepHeadless`, `_suiteRunId` run guard, SW `SKIP_WAITING`; main suite adds `MIN_APP_VERSION` + `about:blank` iframe.

- **Audit** — GROUP 8/9/41/57 extended. Total: 318 checks, 0 failures.

- **`APP_VERSION`** — bumped to `2.20.23`.

---

## v2.20.22 — 2026-06-21

### Design sync (CCR shared layer)

- **Header branding** — Default Tec icon is 🫧; extracted `setBrandIcon()` helper; Tools button text-only; `aria-hidden` on brand icon.
- **PDF deco banner** — Warning indicator uses ⚠ (`\u26A0`) to match on-screen banner.
- **PWA** — Dynamic `getAppBasePath()` in service worker; version-keyed cache migration; `sw.js?v=` registration with `SKIP_WAITING`; added `icon-512.png` to manifest.

### Fixed (back-ported from CCR audit)

- **BUG-33** — VPM gas summary uses correct `dg1Mix`/`dg2Mix` DOM IDs for deco cylinder lookup.
- **BUG-40** — Bühlmann emergency gas: imperial cylinder size converted cu ft → L.
- **BUG-41/62** — `appSettings.clear()` removes all settings keys including v6 and app-owned prefs.
- **BUG-42** — Removed duplicate deferred `_restoreFields()` pass that fired spurious change events on load.
- **BUG-69** — `computeSurfaceGF()` uses `altSurfaceP` for altitude-aware surface GF.
- **BUG-71** — `sacDomToLpm()` converts imperial SAC to L/min before gas math (Bühlmann + VPM).
- **BUG-72** — VPM gas summary and emergency card use `gpVolDisp()` for imperial volume display.
- **BUG-76** — Massive test suite guards: early headless mode, `installMassiveSuiteGuards()`, `massiveSuite=1` iframe load.

### Other

- **Settings persistence** — Added `dg1Mix`, `dg1CustomO2`, `dg2Mix`, `dg2CustomO2` to `DECO_FIELDS`.
- **Reference panel** — Link to LSP D-Planner + CCR Rebreather Edition.
- **Audit** — GROUPs 41–42, 46, 53–56 added. Total: 294 checks, 0 failures.

- **`APP_VERSION`** — bumped to `2.20.22`.

---

## v2.20.21 — 2026-06-20

### Fixed

- **Plan summary stats wrap across three lines in all text exports** — `formatPlanSummaryBlock()` previously returned a single long string, causing all stats (Run Time, TTS, Deco, CNS, OTU, PrT, Surf GF, Decozone, First deco) to run together on one line in text export, messenger, and contingency outputs. Refactored to return an array of three lines: `Run Time / TTS / Deco`, `CNS / OTU / PrT`, `Surf GF / Decozone / First deco`. All five call sites updated to spread the array (`push(...)`). Both compact and non-compact variants split the same way.

- **Audit** — GROUP 40 added (2 checks). Total: 265 checks, 0 failures. Covers: `formatPlanSummaryBlock` returns array in both branches; all call sites use spread operator.

- **`APP_VERSION`** — bumped to `2.20.21`.

---

## v2.20.20 — 2026-06-20

### Fixed

- **Contingency and messenger export stamp YYYY/DD/MM** — `buildMessengerText()` contingency branch and deco branch still assembled dates as year/day/month. `buildContingencySlateText()` same issue. Fixed to `YYYY/MM/DD` to match banner, text export, and slate.

- **Version docs** — `README.md` and `package.json` synced to current release.

- **Audit** — GROUP 39 added (3 checks). Total: 263 checks, 0 failures.

- **`APP_VERSION`** — bumped to `2.20.20`.

---

## v2.20.19 — 2026-06-20

### Fixed

- **`handleGFSelect('custom')` resets GF inputs to stale saved values** — When the user selected "Custom" from the GF preset dropdown (after loading a preset like Abysner 60/70), both the Low and High inputs were populated from `localStorage.getItem('gfCustomLow/High')` — whatever the user had last typed manually — instead of the currently active `mGF.low/high`. This meant loading Abysner (60/70) then clicking Custom would silently reset inputs to 20/85 (or any previous custom entry), not 60/70. Fixed in both the Bühlmann branch and the VPM-B/GFS branch: inputs now seed from `mGF.low`/`mGF.high` first, falling back to localStorage only when mGF is unavailable.

- **Audit** — GROUP 38 added (2 checks). Total: 260 checks, 0 failures. Covers: `handleGFSelect` custom branch (Bühlmann) uses `mGF.low/high`; VPM-B/GFS custom branch uses `mGF.high`.

- **`APP_VERSION`** — bumped to `2.20.19`.

---

## v2.20.18 — 2026-06-20

### Fixed

- **`buildDecoPlanHeaderData()` ReferenceError on `densityMap`** — The `densityMap` lookup object was removed from the function body during the v2.20.17 refactor but still referenced on the same line. Every call to the dive plan info banner, text export header, and PDF banner crashed with `ReferenceError: densityMap is not defined`. Fixed by defining `_densityMap` locally inside the function.

- **`buildDecoPlanHeaderData()` returns `du: undefined`** — The `du` variable (`'m'`/`'ft'`) was also removed from the function body during the same refactor but kept in the return object. All callers using `data.du` (banner HTML, PDF banner, text export lines) produced output like `30undefined` for depths and rates. Fixed by restoring `const du = units === 'imperial' ? 'ft' : 'm'` inside the function.

- **`buildExportText()` stamp YYYY/DD/MM** — The date stamp in text export was never updated when `buildDecoPlanHeaderData` was fixed in v2.20.17; `buildExportText` still assembled `${_yy}/${_dd}/${_mm}` producing e.g. `2026/20/06`. Fixed to `${_yy}/${_mm}/${_dd}`.

- **`buildSlateText()` stamp YYYY/DD/MM** — Same issue in the slate export: assembled `${_sNow.getFullYear()}/${_sD}/${_sMo}` (day before month). Fixed to `${_sMo}/${_sD}` order.

- **Audit** — GROUP 37 added (4 checks). Total: 258 checks, 0 failures. Covers: `buildDecoPlanHeaderData` local `densityMap` and `du`, `buildExportText` stamp order, `buildSlateText` stamp order.

- **`APP_VERSION`** — bumped to `2.20.18`.

---

## v2.20.17 — 2026-06-19

### Added

- **Dive plan info banner** — New styled `DECO PLAN` summary banner rendered above the decompression table after every plan run. Shows timestamp, algorithm/GF settings, bottom/deco/travel gas chips, descent/ascent rates, stop settings, environment, and plan totals. Shared data model (`buildDecoPlanHeaderData`) feeds the on-screen banner (`renderDecoPlanHeaderHtml`), text export header (`buildDecoPlanHeaderLines`), and PDF banner (`drawDecoPlanBannerPdf`).

- **PDF table layout refactor** — `_pdfDecoTableLayout` gains `tblMl`/`tblCw` (padded margins), extracted header/phase-label helpers `_pdfDrawDecoTableHeader` and `_pdfDrawDecoPhaseLabel`. Gas-switch rows use fill-only style (no border). Column widths adjusted. Both main and emergency PDF tables use the new helpers.

### Fixed

- **`getDecoGasSwitches()` ReferenceError** — Called closure-scoped `optimalSwitchDepth()` (local to `runDecoSchedule()`) which is unavailable globally. Crashed banner on page load and settings restore. Replaced with inline equivalent reading DOM globals (`ppO2Deco`, `ppO2Bottom`, `lastDecoStop`, `decoStep`).

- **Stamp YYYY/DD/MM** — `buildDecoPlanHeaderData` assembled stamp as `YYYY/_dd/_mm` (month and day swapped). Fixed to `YYYY/_mm/_dd`.

- **Audit** — GROUP 36 added (20 checks). Total: 254 checks, 0 failures.

- **`APP_VERSION`** — bumped to `2.20.17`.

---

## v2.20.16 — 2026-06-19

### Fixed

- **PDF export bloated to 100–190 MB on high-DPI mobile** — jsPDF `addImage()` embeds raw pixel data uncompressed. On 3× DPR devices the dive profile and GF curve canvases were ~2100×900 px each (~7.5 MB raw per image). Added `_canvasToDataURLForPDF()` to re-draw each canvas at 150 DPI print resolution before embedding. All four `addImage()` call sites updated (main plan + emergency PDF). Typical output now ~3–8 MB.

- **`APP_VERSION`** — bumped to `2.20.16`.

---

## v2.20.15 — 2026-06-19

### Fixed

- **Contingency exports missing Surf GF** — `getContingencySummaryExport()` did not return `surfGF`, so contingency text, slate, messenger, and emergency PDF showed Surf GF in the live footer but omitted it from every export. `_lastContingency` now stores `surfGF`; export reads `totRow.dataset.surfgf` with fallback to `_lastContingency.surfGF`. Emergency PDF footer includes Surf GF between PrT and Decozone.

- **`APP_VERSION`** — bumped to `2.20.15`.

---

## v2.20.14 — 2026-06-19

### Fixed

- **GF dropdown missing 50/80 and 60/70 after switching from VPM-B to Bühlmann** — `setDecoAlgorithm` rebuilds the GF preset dropdown when switching back to Bühlmann (after VPM-B replaces it with `hi/N` options). The hardcoded rebuild template was missing the `50/80` and `60/70` options that were added in v2.20.7. Both options are now included in the rebuild template.

- **GF dropdown not restoring current selection after VPM-B → Bühlmann switch** — After the dropdown innerHTML was rebuilt, the selected value defaulted to the first option (`20/85`) even if `mGF` held different values (e.g. `60/70` from a loaded preset). Fixed by finding the matching option from current `mGF.low/mGF.high` after the rebuild and setting `sel.value` accordingly, falling back to `'custom'` if no match.

- **`APP_VERSION`** — bumped to `2.20.14`.

---

## v2.20.13 — 2026-06-19

### Added

- **1.2 bar ppO₂ option** — added to both `ppo2Bottom` and `ppo2Deco` selects (below 1.4 bar), enabling accurate GUE DecPlanner preset loading.

### Changed

- **GUE DecPlanner preset** — restored to `ppo2Bottom`/`ppo2Deco` = 1.2 bar (correct GUE standard); summary updated accordingly.

- **`APP_VERSION`** — bumped to `2.20.13`.

---

## v2.20.12 — 2026-06-19

### Fixed

- **App-default preset invalid select values** — `loadAppPreset()` silently failed when preset values did not match available `<select>` options:
  - `stopRounding: 'whole'` → fixed to `'wholeminute'` (valid options: `fractional` / `wholeminute`).
  - `o2AtMODSelect: 'yes'` → fixed to `'on'` (valid options: `on` / `off`).
  - GUE DecPlanner `ppo2Bottom`/`ppo2Deco: '1.2'` → temporarily set to `'1.4'` until the 1.2 bar option was added in v2.20.13.

- **`APP_VERSION`** — bumped to `2.20.12`.

---

## v2.20.11 — 2026-06-19

### Fixed

- **Text export (.txt) crash on Deco mode** — `buildExportText('deco')` referenced `cnsExpVal`, a variable that was never defined anywhere, causing a `ReferenceError` that silently aborted the export. Fixed by replacing `cnsExpVal` with `planSum.cns`, which is already read from the totals row data-attributes earlier in the same function block.

- **PDF export missing final info row under the ascent schedule table** — The `data-phase="totals"` row in `#decoTableBody` is `display:none` and stores all values in `data-*` attributes (not in text content). The PDF renderer was trying to read `span` text content / `textContent` from this hidden row and getting empty strings. Fixed by using the already-fetched `planSumPdf` object (from `getPlanSummaryExport()`) to build the totals summary line directly.

- **Emergency plan PDF missing final info row** — Same root cause as above: `exportContingencyPDF` read the hidden `totals` row's empty text content. Fixed by calling `getContingencySummaryExport()` before the table loop and using the returned summary object to render the totals line.

- **`APP_VERSION`** — bumped to `2.20.11`.

---

## v2.20.10 — 2026-06-19

### Fixed

- **GF preset dropdown still showing "Custom" after loading preset on returning users** — Two root causes addressed:
  1. `gfPresetSelect` was not in `_ADV_FIELDS`, so `_snapshotAdvConfig()` never captured the dropdown value in user-saved config presets. Added `gfPresetSelect` as the first entry in `_ADV_FIELDS` so it is saved, restored, and included in reset-to-defaults paths.
  2. `loadAppPreset()` and `loadConfigPreset()` called `setGF()` which schedules `appSettings.save(false)` via `setTimeout(..., 100)`. A deferred `appSettings.load()` runs 1000 ms after init and could overwrite localStorage with the stale `'custom'` value before the 100 ms save completed. Fixed by adding an immediate synchronous `appSettings.save(false)` call at the end of both loaders, flushing the correct `gfPresetSelect` value to localStorage before any deferred reload fires.

- **`APP_VERSION`** — bumped to `2.20.10`.

---

## v2.20.9 — 2026-06-19

### Changed

- **Moved GF controls from Advanced Settings into main card area** — `gfPresetsRow` (GF preset dropdown) and `gfCustomRow` (GF Low / High custom inputs) are now always-visible in the Decompression Schedule card, directly below the Algorithm row. GF is a core Bühlmann parameter that pairs directly with the algorithm selection; it no longer requires opening Advanced Settings to reach. The GF row uses the same inline flex layout as the Algorithm row. GF Low and High custom inputs are wrapped in a `gfLowPair` span for clean show/hide in VPM-B/GFS mode.

- **Moved Advanced Settings presets button next to dive profile presets button** — `advConfigPresetsBtn` (previously a floppy-disk icon at the bottom of the Advanced Settings panel) is now in the depth/BT button row next to `presetsHeaderBtn`. Its icon changed from a floppy disk to a hamburger (≡ three horizontal lines) to distinguish it from the dive-profile save button. The two buttons sit side by side: floppy = save/load depth & BT profile; hamburger = save/load advanced settings config.

- **`APP_VERSION`** — bumped to `2.20.9`.

---

## v2.20.8 — 2026-06-19

### Changed

- **Moved Algorithm controls from header into Decompression Schedule card** — Algorithm select (Bühlmann / VPM-B / VPM-B+GFS) and VPM-B Conservatism row are now in a new `algoRow` div at the top of the Decompression Schedule card, directly above the subtitle line and depth/BT inputs. The user no longer needs to jump between the header and the card to change algorithm. The ENV toggle button (Water / Units / Altitude) remains in the header in its own `envRow` div, as those are location settings rather than algorithm settings. All `setAlgo()` show/hide logic updated to reference `algoRow` + `envRow` instead of the old `algorithmRow`. Element IDs for `algorithmSelect`, `conservatismRow`, `conservatismSelect` unchanged.

- **`APP_VERSION`** — bumped to `2.20.8`.

---

## v2.20.7 — 2026-06-19

### Changed

- **Added missing GF preset options to dropdown** — `gfPresetSelect` was missing `50/80` (DiveKit preset) and `60/70` (Abysner preset), causing those presets to always show "Custom" in the dropdown after loading even though their GF values are standard named options. Both values added in sorted order: `50/80` between `50/75` and `55/80`; `60/70` between `55/80` and `100/75`.

- **`APP_VERSION`** — bumped to `2.20.7`.

---

## v2.20.6 — 2026-06-19

### Fixed

- **GF preset dropdown shows "Custom" after loading any app or config preset** — `loadAppPreset()` and `loadConfigPreset()` called `setCustomGF()` to commit GF Low/High values into `mGF`. However `setCustomGF()` unconditionally sets `gfPresetSelect.value = 'custom'` regardless of whether the loaded values match a named preset, and never calls `handleGFSelect()`, so `gfCustomRow` was never shown. Result: after loading any preset whose GF matched a named option (e.g. 20/85), the dropdown showed "Custom" instead of "20/85", and the Low/High inputs remained hidden. Fixed by replacing the `setCustomGF()` call in both loaders with `setGF(low, high)`, which correctly matches a preset option in the dropdown (or falls back to "Custom" + shows the custom inputs only when no match exists), and commits the values to `mGF`.

- **`APP_VERSION`** — bumped to `2.20.6`.

---

## v2.20.5 — 2026-06-19

### Changed

- **Moved GF controls from header into Advanced Settings** — `gfPresetsRow` (GF preset selector) and `gfCustomRow` (GF Low / GF High custom inputs) relocated from the algorithm header row into the top of the Advanced Settings panel. GF now appears as the first group in the Advanced Settings form-grid, above Descent Rate. Rationale: GF is the most algorithmically significant parameter and belongs with the other deco-model tuning controls rather than cluttering the always-visible header. All save/restore, CSS visibility (rec-mode / algo-tools opacity), and JS logic (`setDecoAlgorithm`, `handleGFSelect`, `setGF`) updated for the new structure; element IDs unchanged.

- **`APP_VERSION`** — bumped to `2.20.5`.

---

## v2.20.4 — 2026-06-19

### Changed

- **Renamed "Shallow Gradient" to "Shallow GF"** — label and tooltip title updated. Internal ID `shallowGradient` and code comments unchanged.

- **Removed gear (Set as My Default) and reset buttons from Advanced Settings** — both actions are now superseded by the Save/Load presets floppy-disk button. The underlying `saveAsMyDefault()` / `resetToDefaults()` functions are retained for backwards compatibility but no longer exposed in the UI.

- **Added "LSP Default" preset to App Reference Presets** — first entry in the built-in preset list. Loads LSP's own factory defaults: GF 20/85, WV 0.0577, MultiDeco transit, whole-min rounding, Baker HT, 20↓/10↑/3 deco, min stop 2 min. Useful for quickly returning to LSP baseline from any reference-app preset.

- **Fixed misspelling in Advanced Configs modal description** — "diver profiles" → "dive profiles".

- **`APP_VERSION`** — bumped to `2.20.4`.

---

## v2.20.3 — 2026-06-19

### Fixed

- **GF not committed to runtime state when loading app-default or user-saved config presets** — `loadAppPreset()` and `loadConfigPreset()` set `gfLowInput`/`gfHighInput` DOM values directly (bypassing `change` events) but never called `setCustomGF()`, so `mGF.low`/`mGF.high` — the live variables the engine actually reads — were not updated. Loading a preset would show the correct GF in the UI but the engine would silently continue using the previous GF until the user manually touched the GF control. Fixed by calling `setCustomGF()` at the end of both loaders when GF fields are present in the preset. (Introduced in v2.20.1 when `gfLowInput`/`gfHighInput` were added to `_ADV_FIELDS`; `appSettings._restoreFields()` was unaffected as it already dispatches `change` events.)

### Changed

- **`APP_VERSION`** — bumped to `2.20.3`.

---

## v2.20.2 — 2026-06-19

### Fixed

- **OTU exponent `0.833` in `calcCNS()` (CNS tab standalone calculator)** — Roman's v2.20.1 fix converted the three engine-path sites to `OTU_EXPONENT = 0.8333` but missed a fourth copy in `calcCNS()` (the OTU readout in the CNS Oxygen Toxicity Tracker tab). That function displayed a slightly low OTU value for the same ppO₂/time input compared to what the deco plan footer showed. Fixed: now uses `OTU_EXPONENT` like all other sites.

### Changed

- **Audit** — Added 2 checks (34.25: `OTU_EXPONENT` constant defined; 34.26: no stale `0.833` 3-digit copies remain). Total: 218 checks, 0 failures.
- **`APP_VERSION`** — bumped to `2.20.2`.

---

## v2.20.1 — 2026-06-19

### Fixed

- **Contingency gas-loss incorrect gas silenced** — `calcContingency()` compared `contGasLose` (which stores the actual deco-gas card ID, e.g. `"1"`, `"2"`) against `getAllDecoGasIds().indexOf(idx)+1` (a list-position index). These diverge whenever card IDs are non-contiguous. Fixed to compare directly: `contGasLose === String(idx)`.

- **OTU exponent split across three independent copies** — VPM `calculateOTU()` used `0.8333`, ZHL `segOTU()` used `0.833`, and ZHL headless fallback also used `0.833`. Introduced a single top-level constant `OTU_EXPONENT = 0.8333` and replaced all three sites. Roadmap item 2 had flagged this; it was not resolved before shipping.

- **App-default presets did not load GF Low / GF High** — `gfLowInput` and `gfHighInput` were missing from `_ADV_FIELDS`, so `loadAppPreset()` silently left GF unchanged. Added both fields to `_ADV_FIELDS` and added the correct GF values to all five presets (MultiDeco 30/85, Abysner 60/70, Subsurface 30/70, GUE DecPlanner 20/85, DiveKit 50/80).

- **DiveKit preset: `lastDecoStop` wrong, ascent rates wrong** — preset shipped with `lastDecoStop: '3'` (should be `'6'` per confirmed JS bundle default) and `decoAscentRate: '3'` (should be `'9'` — DiveKit uses a two-tier split 9 m/min deep / 3 m/min surface, not a flat 3 m/min throughout). Fixed.

- **MultiDeco preset: `descentRate` wrong, ascent rates wrong** — preset shipped with `descentRate: '20'` (screenshot-confirmed value is 22 m/min) and flat `ascentRate: '10'` (MultiDeco uses three equal tiers at 9 m/min for surface/deco/ascent). Fixed to `descentRate: '22'`, `ascentRate/decoAscentRate/surfaceAscentRate: '9'`.

- **Subsurface preset: ascent rates wrong** — preset used flat 3 m/min for all tiers; Subsurface's confirmed three-tier rates are 9 m/min deep / 6 m/min between stops / 3 m/min surface. Fixed `decoAscentRate: '6'`.

- **GUE DecPlanner preset: ppO2 limits wrong** — preset used 1.4/1.6 bar; GUE's confirmed limits are 1.2 bar for both bottom and deco gas. Fixed.

- **Contingency `emInfoRow` missing Surf GF** — `buildPlanInfoRowHtml` renders Surf GF when `o.surfaceGF` is passed, but `calcContingency()` never passed it. `runContingencyScenario()` now captures `lp.surfaceGF` as `contSurfaceGF` and returns it; `calcContingency()` forwards it to `buildPlanInfoRowHtml`.

- **ZHL headless path did not pick up `_priorDiveCarry`** — the prior-dive O2 carry set in the CNS tab (v2.20.0) was only wired into the live DOM render path. `ZHLEngine.calculate()` now mirrors `s._preOTU`/`s._preCNS` into `window._priorDiveCarry` before the headless `runDecoSchedule()` call and restores it afterwards (including error paths), so test harnesses that pass prior-carry state see consistent CNS/OTU values.

- **OTU exponent also wrong in ZHL headless fallback** — the per-step OTU accumulator inside `ZHLEngine.calculate()`'s CNS/OTU fallback computation used `0.833`; updated to `OTU_EXPONENT`.

### Changed

- **`gfLowInput` / `gfHighInput` added to `_ADV_FIELDS`** — GF settings are now included in "Set as My Default" saves and user-saved config presets alongside all other advanced fields.

- **`APP_VERSION`** — bumped to `2.20.1`.

---

## v2.20.0 — 2026-06-19

### Added

- **Surface GF (Surf GF)** — new read-only metric in the deco plan footer (both ZHL and VPM paths). Computed as `max_i((pN2_i + pHe_i − 1.0 bar) / (a_i + 1.0/b_i − 1.0))` using the end-of-dive tissue snapshot and the weighted composite a/b for trimix. Shows how close the leading compartment is to the raw Bühlmann M-value at surface pressure. 0% = fully desaturated; 100% = exactly at the M-value limit (no GF conservatism). Colour-coded: green < 70%, yellow 70–85%, orange 85–100%, red ≥ 100%. Also written to `data-surfgf` in the hidden totals row and included in all export paths (text, slate, PDF). `window._lastPlan.surfaceGF` is the authoritative value.

- **CNS/OTU dual-method audit** — verified and documented that both CNS calculation methods (NOAA table with 0.1-bar steps in the ZHL path; `CNS_RATE_ANDROID` fine-grained 0.01-bar lookup in the VPM path) agree within ±2% at all NOAA breakpoints. Cross-check comment added near `CNS_LIMITS`. No code change required — tables are consistent.

- **Prior Dive O₂ Load Carry (Last Dive input)** — new UI section in the CNS tab. Enter days/hours/minutes since the last dive ended, plus the OTU and CNS% from that dive. LSP computes the remaining carry and seeds both the ZHL and VPM plan engines:
  - **OTU**: NOAA day-boundary rule — resets to 0 if the last dive ended ≥ 24 hours ago; otherwise carried in full (OTU has no half-life within a day).
  - **CNS**: decays with a 90-minute half-life regardless of day boundary.
  - Carry is displayed in the CNS tab before running a plan and reflected in the plan footer's CNS% and OTU values.

- **Shallow Gradient toggle** — new Advanced Settings field (`id="shallowGradient"`, default `off`). When `on` (MultiDeco-compatible), `gfAt()` applies GF High from the last stop depth onwards (clamped at `lastStop`), and the GF ramp from first stop to last stop uses `lastStop` as the interpolation base rather than 0 (surface). Effect: GF at intermediate stops is higher → intermediate stops are shorter; GF at last stop is always GFHi → last stop may be tighter. Off by default = standard Bühlmann GF behaviour (GF interpolates all the way to the surface). Field persisted in `_ADV_FIELDS` and loaded/saved with advanced config presets.

- **Emergency contingency: went deeper** — new "🔽 Went Deeper" button group in the Contingency Plans card with +0m/+3m/+5m options. Adds a depth offset to the dive before running the emergency scenario. `contExtraDepth` variable added alongside `contExtraBT`; `selectContDepth()` function handles button state. Depth is saved as `origDepth` and restored after the contingency run.

- **Settings profiles — 5 app-default presets** — the Advanced Configs modal now shows a "📐 App Reference Presets" section with 5 built-in, read-only configurations that load the closest LSP equivalent of each tool's default settings:
  - **MultiDeco** — WV 0.0577, MultiDeco transit, whole-min rounding, Baker HT, 20↓/10↑/3 deco
  - **Abysner** — WV 0.0627, Schreiner transit, whole-min rounding, 25↓/9↑/3 deco
  - **Subsurface** — WV 0.0627, Schreiner transit, fractional stops, Bühlmann 2003 HT, 20↓/9↑/3 deco
  - **GUE DecPlanner** — WV 0.0627, MultiDeco transit, whole-min rounding, Baker HT, 20↓/9↑/3 deco
  - **DiveKit** — WV 0.0577, Schreiner transit, fractional stops, Baker HT, 20↓/9↑/3 deco
  - User-saved configs appear below in a "👤 My Saved Configs" section as before.

### Changed
- **`buildPlanInfoRowHtml`** — Surf GF span added between PrT and Decozone.
- **`getPlanSummaryExport`** — reads `data-surfgf` attribute and falls back to `_lastPlan.surfaceGF`.
- **`formatPlanSummaryBlock`** — includes Surf GF in both compact and full text export formats.
- **`buildSlateText`** — includes Surf GF in footer line.
- **PDF export stats grid** — Surf GF added as a stat tile (now 3 rows of 6 instead of 2+).
- **`PLAN_INFO_TIP`** — Surf GF bullet added with full explanation.
- **Audit** — Added GROUP 34 (24 checks). Total: 216 checks, 0 failures.
- **`APP_VERSION`** — bumped to `2.20.0`.

---

## v2.10.44 — 2026-06-18

### Fixed
- **Headless test mode silently changed computed RT/TTS, not just rendering** — found via a from-scratch 16-compartment tissue diff against ApexDeco (a separate, real open-source ZHL-16C+GF engine) on a plain air dive (S2: 45m/22min). Tissue states matched ApexDeco's almost exactly at every stop (noise-level differences, <0.13 bar across all 16 compartments), ruling out the deco math itself — but the first deco stop's reported duration was consistently ~0.5-0.7 min longer than it should be.
  - Root cause: `holdStep` (the while-loop's ceiling-check granularity used to determine how long to hold at each stop) was forced to a coarse 1-minute resolution in headless mode, even for the first stop — which the real (non-headless) app deliberately gives a fine 1/6-minute (10-second) resolution, since the first stop's duration is meant to be fractional (matching ApexDeco/MultiDeco's "RT-snap" convention), not floored to a whole minute.
  - This was the **only** `_zhlHeadless` branch in the file that changes a computed result rather than skipping DOM rendering — every other usage of the flag just skips a render call, so this one slipped through as if it were purely a speed optimization (6x fewer loop iterations) when it was actually also silently producing different RT/TTS numbers in headless tests (and in every prior session's headless verification scripts) than the live app would show for identical inputs.
  - Fixed: `holdStep` now always uses fine resolution for the first stop regardless of headless mode; non-first stops keep the coarser 1-minute resolution (which already matched the real app's own behavior, so no change there). Performance impact is negligible — only one stop per dive uses the finer loop.
  - This explains roughly 10-15% of the previously-unexplained RT/TTS gap on plain air/nitrox baseline scenarios (S2, S7, FS2) — most of the remaining gap on those and the trimix/Extended-Stops scenarios is still open, now narrowed down to small per-stop floor-rounding accumulation rather than any tissue-tracking or formula discrepancy (confirmed via the same tissue-diff method).

### Changed
- **Audit** — Added GROUP 33 (1 check): headless mode no longer forces coarse first-stop resolution. Total: 192 checks, 0 failures.
- **`APP_VERSION`** — bumped to `2.10.44`.

---

## v2.10.13 — 2026-06-18

### Fixed
- **Missing final surface-ascent leg in ZHL engine** — the ascent loop treated
  surfacing as instantaneous (zero time, zero off-gassing) once the last deco
  stop finished. `surfaceRate` existed and was correctly wired into VPM but was
  never used in the ZHL loop. Added a proper `finalAscentDur = cur / surfaceRate`
  leg with `saturateLinear` off-gassing pushed as its own visible step. Effect:
  +1 min RT/TTS on 3 m last-stop dives, +2 min on 6 m last-stop dives. Confirmed
  via DiveKit's published `inputs.json` which lists `surfaceAscentMPerMin` as a
  dedicated separate field distinct from deep- and deco-ascent rates.
- Audit: 3 new checks added (GROUP 32). Total: 191 checks, 0 failures.

---

## v2.10.12 — 2026-06-17

### Fixed
- **`getActiveGas()` max-fO₂ criterion** — The gas selector used a min-fN₂ rule, which preferred Tx21/35 travel gas (fN₂=0.44) over EAN50 (fN₂=0.50) despite EAN50 having 50% O₂ vs 21%. Switched to **max-fO₂** (highest O₂ gas that is MOD-safe). Trimix + nitrox deco plans now pick the correct deco gas.
- **ZHL headless repetitive dive tissue carry** — `runDecoSchedule()` always called `initTissues()` fresh, so multi-dive ZHL plans could not carry tissue state. Added `window._zhlRepState` hook: `ZHLEngine.calculate()` injects `_preTissues` / `_surfaceInterval` before the headless run and clears it after (including error paths). `finalTissues` added to `_lastPlan` and forwarded in the headless return object.

### Changed
- **`APP_VERSION`** — bumped to `2.10.12`; `build.gradle` `versionCode` updated to `21012`.

---

## v2.10.11 — 2026-06-17

### Fixed
- **Bottom gas trimix He ignored in headless wrapper** — `ZHLEngine.calculate()` mapped trimix to non-existent `decoCustomHe` elements instead of `decoGas='trimix'` + `botTrimixO2` / `botTrimixHe`. Tx15/55 dives loaded as Tx15/00 (zero He).
- **Deco gas trimix He ignored in headless wrapper** — Same bug on deco gas cards (`dgCustomHe` vs `dgTrimixO2` / `dgTrimixHe`). Travel gases like Tx21/35 were treated as air.
- **Third deco gas silently dropped** — Headless wrapper only populated pre-built DOM slots 1–2; O₂ (3rd gas) was never added on S5/S6/A2-style dives. Wrapper now calls `addDecoGasCard()` for gases beyond slot 2 and cleans up on restore.

Root cause found via S6 (Tx15/55, 80m/16min) CNS discrepancy: headless reported ~40% vs MultiDeco 65% / DiveKit 77% with He zeroed. Air/nitrox scenarios were unaffected.

### Changed
- **`APP_VERSION`** — bumped to `2.10.11`.

---

## v2.10.10 — 2026-06-17

### Added
- **TTS (time-to-surface) metric** — LSP had no TTS field at all, despite MultiDeco and DiveKit both reporting it as a primary metric in the 3-way comparison. Added `tts = rt - bt` (ascent+deco only, excluding descent and bottom time), computed inside `runDecoSchedule()` before the headless early-return so it's available both in the live app and in headless tests. Stored on `window._lastPlan.tts`, exposed via `ZHLEngine.calculate()`'s return object, and displayed in the footer between Run time and Deco time.

### Fixed
- **Decozone start was GF-dependent — should not be** — LSP's `decoZoneStart` was an alias for `firstStopDepth` (the GF-anchored first mandatory stop), not the GF-independent "ambient-crossing depth" that MultiDeco and DiveKit report. Per DiveKit's own documentation, gradient factors move the M-value line, not the ambient line, so the same physical dive at two different GF settings must report the *same* decozone value even though their first stops differ. LSP was instead reporting `firstStopDepth` directly, which is GF-dependent by definition — producing reported decozone values 9-11m shallower than MultiDeco/DiveKit on every scenario in the comparison set.
  - Added `ambientCrossingDepth(tissues)`: a purely physical calculation (no Bühlmann M-value or GF involved) that finds the depth where any tissue compartment's raw inert-gas tension (pN2+pHe) first exceeds ambient pressure, evaluated at the end-of-bottom tissue snapshot.
  - Replaced `_lastPlan.decoZoneStart` and the footer display to use this new value instead of `firstStopDepth`. Fixed a stale tooltip that described the old (incorrect) definition.
  - Verified the fix reproduces DiveKit's own documented GF-independence test case exactly: S2 (GF30/70) and S7 (GF50/80) — the same 45m/22min air dive — both now report decozone ≈32.0m identically, while their first stops correctly differ (21m vs 15m).
  - Confirmed LSP's separate VPM engine already computed its own decozone correctly via a continuous Schreiner-ascent tissue-vs-ambient comparison (`calcStartOfDecoZone`) — only the ZHL+GF engine had this bug.

### Changed
- **Audit** — Added GROUP 31 (7 checks): TTS computation, storage, exposure, and display; decozone GF-independent function, storage, and display. Total: 188 checks, 0 failures.
- **`APP_VERSION`** — bumped to `2.10.10`.

---

## v2.10.9 — 2026-06-17  ★ Critical fix

### Fixed
- **GF anchor regression: first stop landing 1-3 steps shallower than correct, deco time silently under-counted** — Found via a full 3-way comparison run against divekit.app's published MultiDeco/DiveKit reference dataset (26 scenarios). The v2.10.7 `gfAt()` fix returned `gfH` (GF High) when `firstStopDepth` was unanchored, intending it as "the liberal, no-stop-yet" test. But per Baker's published gradient-factor algorithm — and DAN's own description of it — **GF Low is what determines the first stop**, not GF High; GF High only bounds the final approach to the surface. Returning `gfH` pre-anchor meant the ascent-and-test loop only required a stop once the *loose* GF-High M-value was itself violated, which happens much deeper into supersaturation than the GF-Low M-value. The result: the GF line anchored 1-3 deco steps shallower than correct, and the intermediate stops above that depth were skipped entirely — along with their deco time.
  - Confirmed via an independent `ceiling()` sweep against a 30m/23min air GF30/70 profile (S1 in the comparison set): `ceiling(tissues, gfLow=0.30) = 11.76m` (correctly rounds to the 12m first stop matching MultiDeco and DiveKit exactly), while `ceiling(tissues, gfHigh=0.70) = 5.44m` was what the regressed `gfAt()` was actually testing against — explaining the spurious anchor at 6m and the missing 12m/9m stops.
  - Fixed: `gfAt()` now returns `gfL` (not `gfH`) when unanchored. The dynamic-anchor mechanism from v2.10.7 (anchoring at the actual depth where `mustStop` first fires, rather than a pre-computed bottom-tissue snapshot) is otherwise unchanged and remains correct — only the pre-anchor test GF was wrong.
  - Re-verified against the full 21-scenario runnable subset of the comparison set: every air/nitrox profile (S1-S4, FS1, FS3, FS4, R1) now matches MultiDeco's and DiveKit's first-stop depth exactly. Trimix profiles (S5, S6, A2, A3, FS5) land shallower than MultiDeco by 1-4 steps, matching DiveKit's own documented "stop distribution" explanation (continuous tissue recompute during ascent lets helium off-gas faster than the diver climbs on deep-helium dives) rather than indicating a remaining bug.
  - Also re-verified this fix does not reintroduce the original v2.10.7 bug (pre-computed-snapshot rounding overshoot): the dynamic anchor still fires at the live, correctly-resolved depth during the ascent loop, not from a single bottom-tissue snapshot.

### Changed
- **Audit** — Added GROUP 30 (1 check): `gfAt()` returns `gfL` (not `gfH`) pre-anchor. Total: 181 checks, 0 failures.
- **`APP_VERSION`** — bumped to `2.10.9`.

---

## v2.10.8 — 2026-06-17

### Fixed
- **Headless CNS/OTU silently omitted descent and bottom-time exposure** — Found via a 3-way LSP/MultiDeco/DiveKit comparison run (divekit.app cross-reference dataset, 26 scenarios). `window._lastPlan.steps` only ever contains ascent/deco segments; descent and bottom time are rendered straight to DOM in the live app and never pushed into `steps`. `ZHLEngine.calculate()`'s headless CNS/OTU fallback summed only `lp.steps`, so every headless-computed CNS%/OTU value silently excluded descent and the full bottom-time exposure — typically the majority of a dive's total O₂ load. A 40m/25min air dive that should read ~10% CNS / ~29 OTU was reporting 0.8% / 2.
  - This was a **test-infrastructure bug only**: the live app's DOM-rendering path (`runDecoSchedule`'s non-headless branch) already accumulates CNS/OTU correctly across the full table, including descent and bottom rows. Divers using the app were never shown wrong numbers.
  - It went undetected because the existing automated suites (`tests-massive.html` etc.) only assert finiteness and relative ordering ("longer dive ≥ CNS", "deeper dive ≥ CNS") — never magnitude against a known-correct reference value, so the systematic ~80-95% under-count never tripped a test.
  - Fixed: added explicit descent (average depth = `level.depth / 2`, duration = `level.depth / descentRate`) and bottom-time (full `level.time` at full depth) exposure terms before summing the ascent/deco steps, refactored into a shared `addExposure()` helper.
  - Verified post-fix against the relative-ordering tests (still pass) and against the 3-way comparison dataset: LSP's recomputed CNS/OTU now land in the same range as MultiDeco's and DiveKit's reported values for equivalent profiles.

### Changed
- **Audit** — Added GROUP 29 (3 checks): `addExposure()` helper present, descent exposure included, bottom-time exposure included. Total: 180 checks, 0 failures.
- **`APP_VERSION`** — bumped to `2.10.8`.

---

## v2.10.7 — 2026-06-17

### Added
- **Deco zone in profile footer and exports** — Deco zone depth shown on profile totals row (Bühlmann + VPM), emergency plans, copy, TXT, slate, and PDF exports.

### Fixed
- **GF first-stop anchor used a pre-computed ceiling instead of the actual first stop** — `firstStopDepth` was computed once from `ceiling(bottom_tissues, gfLow)` *before* ascent began, rounded up to the nearest stop-step. For Air+EAN50-style profiles this pre-computed value could land one step shallower than the depth where a stop is actually required (e.g. rounding to 21m when the real ceiling search finds no stop needed until 18m or shallower), producing a spurious mandatory stop that neither MultiDeco nor a from-scratch Baker/Bühlmann implementation would generate.
  - Fixed: `firstStopDepth` is now a mutable `let`, initialised to `0`. `gfAt()` returns `gfH` (the liberal, pre-anchor ceiling) until the GF line is actually anchored. The anchor is set dynamically, the moment `mustStop` first fires during the real ascent-and-test loop, at the actual depth where a stop is required — matching Baker's published algorithm and MultiDeco's behaviour.
  - `candidateFirstStop` (still `gfLow`-derived) is retained only to build the candidate stop-depth list for the ascent loop to iterate; since `gfLow ≤ gfHigh` always holds, this candidate is always at or deeper than the true first stop, so the loop can never miss it.
  - `minStopZoneDepth` follows the same dynamic-anchor pattern — minimum-stop-time enforcement does not begin until the real first stop is known.
  - `decoZoneStart` footer/export now reports the actual first-stop depth rather than the pre-computed estimate.
- Verified via a live jsdom run against the engine across NDL dives, a flat GF50/50 line, GF30/100 (no surfacing conservatism), and a TMX18/45 trimix profile — all produced clean, spurious-stop-free schedules with correct monotonic runtimes.

### Changed
- **Audit** — Added GROUP 28 (5 checks): `firstStopDepth` mutability, `candidateFirstStop` usage, dynamic anchor assignment, `minStopZoneDepth` mutability and dynamic assignment. Total: 177 checks, 0 failures.

---

## v2.10.6 — 2026-06-16  ★ Milestone

Multideco/DiveKit alignment milestone — unified water pressure factors (ZHL + VPM), O₂-band ppO₂ caps, Baker He HT default, repetitive VPM CNS/OTU carry, `BAR_PER_METRE` consistency, VPM render fixes (altitude ppO₂, imperial switch depth). Audit: 172 checks; regression: 68/68 verify + 50/50 tests.

### Fixed
- **VPM ppO₂ display uses hardcoded sea-level pressure** — All pressure calculations in `renderVPMResults` used `1.013` (sea level) instead of `altSurfaceP`. Altitude dives showed incorrect ppO₂ values in the VPM deco table (gas switch rows, descent, bottom, ascent, and stop rows). Fixed: `surfP = altSurfaceP || 1.01325` declared at function top, used throughout.
- **VPM gas tag switch depth wrong in imperial** — The formula `/ (BAR_PER_METRE * 0.3048) / 3.28084` algebraically cancels to `/ BAR_PER_METRE` (result in metres), but was then rounded to a 10 ft grid — showing e.g. `20 ft` for EAN50 instead of the correct `70 ft`. Fixed to `/ BAR_PER_METRE * 3.28084` (metres → feet) with pure O₂ fixed at 20 ft.

### Changed
- **Audit** — Added check 27.4: VPM gas tag imperial switch depth formula correctness. Total: 172 checks, 0 failures.
- **`APP_VERSION`** — bumped to `2.10.6`.

---

## v2.10.5 — 2026-06-16

### Fixed
- **BAR_PER_METRE init** — After v2.10.4 changed salt to `0.10000 bar/m`, the global init was still `1/10.078 = 0.09923`. Any code that runs before `setWaterDensity()` (startup race, unit tests) used a stale value. Fixed: `BAR_PER_METRE` now initialises directly to `0.10000`.
- **Hardcoded `/ 10.078` in display and calculation code** — 12 instances of the old salt constant remained in VPM result rendering (ppO₂ column, gas switch ppO₂, PrT footer), copy/export PrT, emergency plan PrT, and GF tissue display. All replaced with `BAR_PER_METRE` so fresh/EN13319 dives show correct ppO₂ and PrT values.
- **VPM render imperial branch** — `pAmb` for VPM stops had a dead `seg.depth * 0.0305` imperial branch (VPM depths are always in metres internally). Removed; `BAR_PER_METRE` is now used unconditionally.

### Changed
- **Audit** — Added GROUP 27 (3 new checks): `BAR_PER_METRE` init value, no hardcoded `/ 10.078` in live code, VPM render uses `BAR_PER_METRE`. Total: 171 checks, 0 failures.
- **`APP_VERSION`** — bumped to `2.10.5`.

---

## v2.10.4 — 2026-06-16

### Fixed
- **ZHL ↔ VPM salt factor mismatch** — ZHL used `WATER_DENSITY.salt = 0.10020` (9.980 m/bar) while VPM used `SLP_SW_M = 10.078`. Both now use **10.000 m/bar** (`0.10000 bar/m`), matching MultiDeco/DiveKit/ApexDeco.
- **VPM EN13319 water type ignored** — `en13319` was silently mapped to salt (`waterType=0`). Now maps to `waterType=2`; `getSLP()` returns `SLP_EN_M = 10.080` / `SLP_EN_F = 33.071`.

### Changed
- **WATER_DENSITY** — salt `0.10000`, EN13319 `0.09921` (10.080 m/bar); VPM fresh factors aligned (`SLP_FW_M = 10.330`).
- **Audit** — Added GROUP 26 (8 checks): SLP constants, EN13319 `waterType===2`, `getSLP()` usage. Total: 168 checks, 0 failures.
- **`APP_VERSION`** — bumped to `2.10.4`.

---

## v2.10.3 — 2026-06-16

### Fixed
- **He HT default → Baker 1.88 (root fix)** — v2.10.2 corrected the HTML attribute order but left `buhl2003` as the selected value. The actual default was still Bühlmann 2003 (1.51 min) at runtime. Now the `<select>` has `selected=""` on the Baker option, `ZHL16C_HE_HT` is initialised from `ZHL16C_HE_HT_BAKER`, the factory preset is `'baker'`, and all four `|| 'buhl2003'` fallbacks in `updateHeHalfTime`, export, and PDF code are changed to `|| 'baker'`. The engine now starts with Baker 1.88 min by default, matching VPM-B canonical (Baker FORTRAN 1998), ApexDeco, and MultiDeco.
- **Repetitive dive CNS/OTU carry** — When VPM repetitive mode is active, CNS and OTU were always re-initialized to 0 for the second dive, ignoring the oxygen exposure from the first. Fixed: `_lastVPMResult` now stores `finalCNS` and `finalOTU`; on the next dive, `settings._preCNS` is injected with the first-dive CNS decayed on a 90-minute half-life (Baker/NOAA standard), and `settings._preOTU` carries OTU as a daily accumulator (no decay within the same day). `calculate()` initialises `totalCNS` and `totalOTU` from these pre-dive values instead of zero.

### Changed
- **Audit** — Added GROUP 25 (6 new checks): `_lastVPMResult` stores `finalCNS`/`finalOTU`, `_preCNS` decay formula present, `_preOTU` injection present, `calculate()` initialises from `_preCNS`/`_preOTU`. Total: 160 checks, 0 failures.
- **`APP_VERSION`** — bumped to `2.10.3`.

---

## v2.10.2 — 2026-06-16

### Fixed
- **ppO2 mid-band limit** — `ppo2Mid` in `runDecoSchedule` was incorrectly set to `ppo2Bottom` (1.4 bar). Gases with 28–44% O₂ (e.g. EAN32, EAN36) now correctly use 1.5 bar, producing the right MOD and switch depth. Previously EAN32 switch depth was 3 m too shallow.
- **O₂-band boundary conditions** — inner engine `getPPO2Limit` used `<=28` and `<=45` thresholds. Fixed to `<28` and `<45`: exactly 28% O₂ is now correctly treated as mid-band (1.5 bar), and exactly 45% O₂ as rich (1.6 bar). Aligns with ApexDeco / DiveKit spec.
- **He HT HTML attribute order** — `selected` attribute on the `heHalfTimeMode` select was `selected="" value="buhl2003"` (wrong order), causing the audit to fail detection. Corrected to `value="buhl2003" selected=""`.
- **`updateHeHalfTime` logic** — condition was inverted: `mode === 'buhl2003'` selected the Bühlmann array and anything else selected Baker. Corrected to `mode === 'baker'` selects Baker, fallback is Bühlmann 2003.
- **Fallback mode strings** — export and PDF code used `|| 'buhlmann2003'` (non-existent key) as fallback; normalized to `|| 'buhl2003'`.

### Changed
- **Audit** — added GROUP 24 (3 new checks): `ppo2Mid = 1.5` correctness, `<28` O₂ boundary, `<45` O₂ boundary. Total: 154 checks, 0 failures.
- **`APP_VERSION`** — bumped to `2.10.2`.

---

## v2.10.1 — 2026-06-15

### Changed
- **`APP_VERSION`** — bumped to `2.10.1`; `build.gradle` `versionCode` updated to `21001`

---

## v2.10.0 — 2026-06-13  ★ Milestone

### Added
- **@capacitor/status-bar plugin** — native Android status bar control; transparent/edge-to-edge layout with `WindowCompat.setDecorFitsSystemWindows`
- **Status bar icon color sync** — dark icons in light theme, white icons in dark theme; theme preference written to `document.cookie` on every toggle and startup so native Java reads the correct value on cold launch via `CookieManager`
- **Collapsible ENV settings group** — environment settings (altitude, water type, acclimatization) collapse/expand; state persisted in `localStorage`
- **Collapsible Advanced Settings group** — advanced algorithm settings collapse/expand; state persisted in `localStorage`
- **Dive profile presets** — quick-select common dive profiles (depth + bottom time combinations); applied to both Rec and Tec modes
- **Advanced config presets** — quick-select common algorithm/GF configurations; one-tap apply
- **Water type tooltip** — inline `?` explanation of density values and effect on deco obligation per water type
- **Per-algorithm tooltips** — inline `?` on algorithm selector explains ZHL-16C+GF, VPM-B, and VPM-B/GFS; includes conservatism note
- **Planning Aid Only banner** — prominent banner displayed when a non-default conservatism or GF is in use

### Changed
- **`APP_VERSION`** — bumped to `2.10.0`; `build.gradle` `versionCode` updated to `21000`
- **`windowLightStatusBar`** — set to `true` in `styles.xml` (dark icons as safe XML default); Java flips to white icons at startup if dark theme cookie is present
- **`windowTranslucentStatus`** — removed from `styles.xml`; edge-to-edge now handled exclusively by `WindowCompat.setDecorFitsSystemWindows(false)` in `MainActivity`
- **CI workflow** — added `git reset --hard HEAD` before `git pull --rebase` to clear unstaged `cap sync` changes that were causing the APK commit step to fail

### Fixed
- **Status bar bg color** — `#f0f4ff` → `#ffffff` in `StatusBar.setBackgroundColor` for light theme (was creamy off-white)
- **`.algo-label` in light theme** — `#00d9ff` (invisible cyan on white) → `#0055aa` (dark blue, matches `--padi-accent` token)
- **`onResume` access modifier** — changed from `protected` to `public` to correctly override `BridgeActivity.onResume()`; was causing compile error
- **Removed broken `applyStatusBarStyle()`** — was reading `diveTheme` from `CapacitorStorage` SharedPreferences which is never populated by `localStorage.setItem()`; JS `loadThemePreference()` now owns all status bar styling

---

## v2.9.1 — 2026-06-12

### Fixed
- ZHL CNS renderer: `bottomFO2` used instead of `(1-bottomFN2)` for trimix ppO₂ on descent/bottom rows
- Custom bottom gas cap raised 40% → 100%; MOD display now updates live on O₂% input
- `segCNSfrac`, `rowCNS`, ZHLEngine headless `hCNSfrac`: ppO₂ > 1.6 now clamps to 45-min NOAA limit instead of returning 100% per segment
- Gas switch flags on dive graph: colour changed to yellow/green (#FFD700 / #007A33) to match deco table switch row style; same fix applied to PDF deco table (3 locations)
- Dive graph card tooltip added — explains all visual elements (profile line, Bühlmann ceiling, gas switch flags, stop dots, ppO₂ halos, interaction)
- Multi TXT export (`mode=multi`) rewired from orphaned `#multiCards`/`#multiWarnings` to live `#unifiedDivePlan` renderer
- Static inline-SVG favicon replaces dynamically injected one (was broken after `initPWA` removal)

### Changed
- Dead code cleanup: 14 unused functions removed (`ftToM`, `setNDLUnits`, `setMultiUnits`, `updateGF`, `floorPPO2`, `depthFromPressure`, `getEl`, `switchMultiMode`, `runMulti`, `buildBuhRef`, `initPWA`, `calcMaxDepth`, `exportContingencyTXT`, `buildPdfGasCards`); archived to `dev/legacy.js`
- 12 dead CSS classes and 22 utility CSS rules removed
- Whitespace and separator comment cleanup (-5.7 KB)

### Added
- Proper PWA: `manifest.json` + `sw.js` (cache-first, offline-capable); Android Chrome install banner; iOS Safari Add-to-Home-Screen instructions
- `CHANGELOG.md` — full version history from v2.7
- `dev/legacy.js` — archive of removed functions for reference

---

## v2.9.0 — 2026-06-09

### Added
- **PDF Export section picker** — dialog before export lets you choose which sections to include (Dive Plan PDF and Emergency Plan PDF)
- **Emergency Plan PDF** — full PDF export for contingency plans: emergency gas consumption, ascent schedule, dive profile, GF curve, tissue saturation, emergency slate
- **DejaVu Sans Unicode font** — all PDFs now use a single DejaVu Sans (regular + bold) font; correct rendering of ✓ ✗ ⚠ ↑ ↓ and all Unicode symbols
- **Copy preview modal** — copy button opens a preview modal showing the full formatted plan text before copying to clipboard (Deco Plan and Emergency Plan)
- **Timestamps on all exports** — `YYYY/DD/MM HH:MM` date/time stamp added to all copy, slate, and TXT exports
- **CNS/OTU/PrT footer line** — second footer line added to all deco and emergency slates and copy exports
- **Math Verification Suite** (`tests-verify.html`) — ZHL-16C Bühlmann + VPM-B cross-check against Baker/FORTRAN reference; 68 tests across sections A–H
- **Tissue saturation chart** — per-compartment saturation bars in a dedicated collapsible card
- **Contingency shortcut buttons** — quick links to contingency scenarios from the results area

### Changed
- Collapsible result cards — Gas Consumption, Contingency Plans, Dive Graph, Tissue Saturation, GF Curve
- Card order reordered: Dive Profile → Gas Consumption → Contingency Plans → Dive Graph → Tissue Saturation → GF Curve
- Slate footer: TBT → TRT (Total Run Time); `TRT: MM'SS" | DECO: MM'SS"`
- Copy footer split into two lines
- Export headers: `DECO PLAN` / `EMERGENCY PLAN` title lines added
- END column in PDF deco table — all 9 columns exported

### Fixed
- ZHL CNS renderer trimix ppO₂ fix
- Custom bottom gas cap raised 40% → 100%
- Test harness: `gfs:hi` double-division fix, `WATER_VAPOR` NaN-safe re-sync

---

## v2.8.9 — 2026-06-09

### Added
- **Gas Consumption card** — rule-of-thirds table integrated into deco schedule results
- **Gas Rule toggle** — Rule of Thirds / Half Tank; updates live
- **Travel gas pooling** — pools with bottom gas when same mix
- **Warning row colours** — SHORT / TIGHT rows highlighted
- **Best Mix tab (Tec)** — trimix optimizer
- **END Calculator** — Tools tab: depth + O₂/He% → END and narcotic ppO₂
- **EAD Table** — MOD and MND reference for common mixes
- **Gas Table** — MOD @ 1.4 / MOD @ 1.6 / MND columns
- **PayPal donate button** — footer and Ref modal

### Changed
- Tec mode default on startup
- Main tab order: Deco > Gas Plan > Surf Int > Dive Planner > Multi Dive > CNS > NDL

### Fixed
- `calcSurfInt` tolTension: uses surface pAmb (not Dive 2 depth)
- Preset button placement
- Gas Plan cross-checks and max BT suggestion

---

## v2.8.0 — 2026-06-09

### Added
- **Gas Table** — MOD reference table for common mixes in Tools tab
- **Surface Interval Calculator** — full tissue-model SI calculation
- **Deco Slate** — compact waterproof-slate format export
- **Named Presets** — save and recall up to 20 full dive setups
- **END column toggle** — Equivalent Narcotic Depth in deco table

---

## v2.7.6 — 2026-06-09

### Added
- **Min Deco Profile** — enforce minimum stop times at 9 m and 6 m

---

## v2.7.4 — 2026-06-09

- Android APK: external links open in system browser
- `APP_VERSION` propagated to Android `versionName`/`versionCode` at build time
- Custom Android UA string: `LSPDPlanner/Android`

---

## v2.7 — 2026-06-08

Milestone release. See git log for earlier history.

---
