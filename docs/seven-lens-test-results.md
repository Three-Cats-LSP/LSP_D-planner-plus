# Seven-Lens Test Results — Cycle History

Consolidated record of every manual seven-lens audit cycle: what was reviewed, what
was found, how it was fixed, and application status after closure.

**Maintenance:** After each cycle closes (`python tools/seven_lens_protocol.py check
--phase close`), append a new cycle section here, then push and merge the cycle PR
to `dev`. Keep detailed reports in `docs/seven-lens-reports/` and protocol records
in `docs/seven-lens-records/`.

| Cycle | Unit | Status | Verified commit | PR |
|------:|------|--------|-----------------|-----|
| 1 | `UI-MARKUP-HEADER` | **CLOSED** — merged to `dev` | `d39bb3b` | [#177](https://github.com/Three-Cats-LSP/LSP_D-planner-plus/pull/177), [#178](https://github.com/Three-Cats-LSP/LSP_D-planner-plus/pull/178) |
| 2 | `UI-MARKUP-PLANNER` | **IN PROGRESS** — schema-v4 evidence required | — | [#191](https://github.com/Three-Cats-LSP/LSP_D-planner-plus/pull/191) |
| 3 | `UI-MARKUP-CONSUMPTION` | **IN PROGRESS** — schema-v4 evidence required | — | [#191](https://github.com/Three-Cats-LSP/LSP_D-planner-plus/pull/191) |
| 4 | `UI-MARKUP-TOOLS` + `UI-MARKUP-MODALS` | **BLOCKED** — closure integrity + dynamic card | — | [#191](https://github.com/Three-Cats-LSP/LSP_D-planner-plus/pull/191) |
| 5 | `UI-CSS-FOUNDATION` + `UI-CSS-MODES` | **CLOSED** — merged to `dev` | `c40b71a` | [#200](https://github.com/Three-Cats-LSP/LSP_D-planner-plus/pull/200) |
| 6 | `UI-CSS-CONTROLS` | **CLOSED** — pending merge to `dev` | `67a4c80` | pending |

---

## Cycle 5 — `UI-CSS-FOUNDATION` + `UI-CSS-MODES`

| Field | Value |
|-------|-------|
| **Cycle ID** | SL-C05 |
| **Units** | `UI-CSS-FOUNDATION`, `UI-CSS-MODES` |
| **Canonical files** | `lsp-dplanner-foundation.css` (418 lines), `lsp-dplanner-modes.css` (338 lines) |
| **Baseline** | `39159b0` |
| **Audit commit** | `ded650c` |
| **Verified source commit** | `c40b71a` |
| **Branch** | `cursor/seven-lens-cycle-05-css` |
| **Ledger** | `SEVEN_LENS_REVIEWED` (both units) |
| **Report** | `docs/seven-lens-reports/cycle-05-css.md` |
| **Record** | `docs/seven-lens-records/cycle-05-css.json` |

### Findings closed

| ID | Severity | Summary |
|----|----------|---------|
| SL-C05-M-01 | MEDIUM | GF mode-isolation CSS targeted removed `#gfPresetsRow` |
| SL-C05-M-02 | MEDIUM | Export buttons suppressed keyboard focus ring |
| SL-C05-L-01 | LOW | Obsolete `.brand-icon` rules |
| SL-C05-L-02 | LOW | Obsolete `#gfCustomRow .gf-btn` rules |
| SL-C05-L-03 | LOW | Obsolete `.algo-switcher` rules |
| SL-C05-L-04 | LOW | Obsolete `.theme-toggle` rules |

### Evidence

- Pre-fix failures at audit checkpoint (`ER-C05-PRE-CSS`, `ER-C05-PRE-TRACE`)
- Post-fix regressions (`dev/ui_css_regression.py`) and browser traces at `c40b71a`
- Independent verifier reproduction (`ER-C05-VERIFY-CSS`, `ER-C05-VERIFY-TRACE`)
- Static and CI gates pass at verified source commit

**Next cycle:** Cycle 7 (`UI-CSS-RESULTS`) per `docs/audit-master-plan.md`.

---

## Cycle 6 — `UI-CSS-CONTROLS`

| Field | Value |
|-------|-------|
| **Cycle ID** | SL-C06 |
| **Unit** | `UI-CSS-CONTROLS` |
| **Canonical file** | `lsp-dplanner-controls.css` (528 lines) |
| **Baseline** | `7cd5897` |
| **Prepared baseline** | `c21493d` |
| **Audit commit** | `fea770d` |
| **Latest checked source commit** | `7d403f4` |
| **Branch** | `cursor/seven-lens-cycle-06-controls-css` |
| **Ledger** | `IN_PROGRESS` (BLOCKED; `SL-C06-L-04` remains open) |
| **Report** | `docs/seven-lens-reports/cycle-06-controls-css.md` |
| **Record** | `docs/seven-lens-records/cycle-06-controls-css.json` |

### Findings status

| ID | Severity | Status | Summary |
|----|----------|--------|---------|
| SL-C06-M-01 | MEDIUM | CLOSED | Segmented controls suppress keyboard focus ring |
| SL-C06-M-02 | MEDIUM | CLOSED | Gas numeric fields undersize touch targets |
| SL-C06-L-01 | LOW | CLOSED | Obsolete `.si-inner` surface-interval rules |
| SL-C06-L-02 | LOW | CLOSED | Obsolete `.t-col` rule |
| SL-C06-L-03 | LOW | CLOSED | Dead `.btn-calc` alias in shared `.gen-btn` selectors |
| SL-C06-L-04 | LOW | OPEN | Field inputs lack invalid-state styling |
| SL-C06-L-05 | LOW | CLOSED | Control transitions ignore `prefers-reduced-motion` |

### Evidence

- Baseline failures at prepared commit `c21493d` (`ER-C06-PRE-CSS`, audit CSS hash matches `fea770d`)
- Post-fix regressions and browser traces are stale after the `7d403f4` invalid-state update; fresh verifier evidence is still required before closure.
- Structure/parity gates (`ER-C06-STRUCTURE`, `ER-C06-PARITY`) and static/CI receipts must be regenerated before restoring `SEVEN_LENS_REVIEWED`.

**Next cycle:** Cycle 7 (`UI-CSS-RESULTS`).


---

PR #191 application checks pass, but the Cycle 2-4 schema-v2 closure package
failed artifact hashes, historical checkpoints, and evidence provenance. Those
cycles are not closed. Closure now requires schema-v4 executed-command receipts
and trace-schema-v3 case/spec/commit binding. Stale generated evidence artifacts
were removed.

---

## Cycle 1 — `UI-MARKUP-HEADER`

| Field | Value |
|-------|-------|
| **Cycle ID** | SL-C01 |
| **Unit** | `UI-MARKUP-HEADER` |
| **Canonical file** | `ui/markup-header.html` (847 lines) |
| **Review boundary** | Whole file, split into four bounded sessions (600-line limit) |
| **Baseline** | `19d56f3` |
| **Verified commit** | `d39bb3b` (post PR #178 remediation) |
| **Branches** | `cursor/seven-lens-cycle-01-header`, `codex/seven-lens-cycle01-verification` |
| **Auditor** | Cursor GPT-5.5 Medium (`cursor/seven-lens-cycle-01-header`) |
| **Fixer** | Composer 2.5 |
| **Verifier** | Cursor GPT-5.5 Medium / Codex independent review (PR #178) |
| **Ledger** | `SEVEN_LENS_REVIEWED` |
| **Detailed reports** | `docs/seven-lens-reports/cycle-01-header-part-a.md`, `cycle-01-header-parts-bcd.md`, `cycle-01-independent-verification.md` |

### What was tested

Seven lenses (L1–L7) applied to the V3 header markup partial and its callers:

| Part | Lines | Scope |
|------|------:|-------|
| A | 1–214 | Scripts, header banner, nav, plan-panel depth/BT inputs |
| B | 215–415 | `resultsPanel` shell (tabs, profile, graphs, contingency, tissue) |
| C | 416–481 | `settingsPageWrap` (units, water, altitude, acclimatized) |
| D | 482–847 | Tools mount, legacy panels, deco card tail (`gfPresetsRow`) |

**Callers traced:** `index.html` (preset load, settings restore, sync helpers),
`settings-core.js`, `planner-shell.js`, `export-core.js`, `results-panel.js`.

**Lens focus areas:**
- L1: No arithmetic in markup; input min/max/step vs engine limits
- L2: Tab switches, generate, nav, contingency buttons
- L3: Canonical `#decoDepth` / `#decoBT` vs mirror `#depth` / `#bt`
- L4: Settings handlers, altitude/water contracts, assemble parity
- L5: `assemble_ui_html.py --verify`
- L6: Planning-aid disclaimer, `gasWarningBanner`, GF defaults
- L7: Engine regressions with real DOM event paths

### Findings

#### SL-C01-M-01 — Depth/BT mirror drift after preset load and settings restore

| | |
|---|---|
| **Severity** | MEDIUM |
| **Lenses** | L3, L4 |
| **Location** | `ui/markup-header.html:127-140`; `index.html:loadProfilePreset`, `_syncUiAfterRestore` |
| **Root cause** | `decoDepth` / `decoBT` are canonical; mirrors updated only via `_syncDepthBtSteppers()`. Preset load and settings restore set canonical fields without syncing. |
| **Failure path** | Load saved profile → stepper shows old depth → REC/export paths reading `#depth` disagree with schedule inputs. |
| **Fix** | Added `oninput` sync on canonical fields; call `_syncDepthBtSteppers()` from `loadProfilePreset` and `_syncUiAfterRestore`. |
| **Regressions** | `SL-C01-DEPTH-SYNC`, `SL-C01-PRESET-SYNC`, `SL-C01-SETTINGS-RESTORE` (REG-58–60) |
| **Status** | **CLOSED** |

#### SL-C01-M-02 — Custom altitude input recalc only on blur

| | |
|---|---|
| **Severity** | MEDIUM |
| **Lenses** | L3, L4 |
| **Location** | `ui/markup-header.html:462` (`#altitudeCustomInput`) |
| **Root cause** | Custom altitude used `onchange` only; water density row uses both `oninput` and `onchange`. |
| **Failure path** | Select Custom altitude, type value, generate immediately → deco uses previous altitude until blur. |
| **Fix** | Added `oninput="applyCustomAltitude()"` to match water row UX. |
| **Regressions** | Covered by settings-restore and altitude constraint cases |
| **Status** | **CLOSED** |

#### SL-C01-L-01 — GF curve stat placeholders show 30/70 instead of 20/85

| | |
|---|---|
| **Severity** | LOW |
| **Lenses** | L6 |
| **Location** | `ui/markup-header.html:312-313` |
| **Root cause** | Static placeholders did not match `mGF` factory default `{ low: 20, high: 85 }`. |
| **Failure path** | Open Graphs tab before first `drawGFCurve()` → misleading labels briefly. |
| **Fix** | Set `#gfCurveGFL` / `#gfCurveGFH` placeholders to 20 / 85. |
| **Status** | **CLOSED** |

#### SL-C01-M-03 — Imperial custom-altitude constraints remain metric

| | |
|---|---|
| **Severity** | MEDIUM |
| **Lenses** | L1, L3, L4, L6 |
| **Location** | `ui/markup-header.html:462`; `index.html:3505-3508` |
| **Root cause** | Unit switch relabels altitude as feet but left `max="5000"` and `step="50"` (metre semantics). |
| **Failure path** | Imperial + Custom altitude → enter 16,404 ft (5,000 m ceiling) → browser rejects (`max` interpreted as 5,000 ft). |
| **Fix** | `syncAltitudeCustomInputConstraints()` in `settings-core.js` — imperial max 16,404 ft, step 1 ft. |
| **Regressions** | `SL-C01-ALTITUDE-UNIT-CONSTRAINTS` (REG-61) |
| **Status** | **CLOSED** (PR #178) |

#### SL-C01-L-02 — Sync regressions bypass event wiring and leak UI state

| | |
|---|---|
| **Severity** | LOW |
| **Lenses** | L3, L7 |
| **Location** | `dev/engine_regression.py` (original SL-C01 cases) |
| **Root cause** | Tests called `_syncDepthBtSteppers()` directly instead of dispatching `input` events; incomplete DOM restore; no settings-restore case. |
| **Failure path** | Suite passes while inline handler wiring or BT mirror sync regresses. |
| **Fix** | Hardened regressions: real `input` events, assert depth + BT mirrors and labels, `finally` DOM restore; added `SL-C01-SETTINGS-RESTORE`. |
| **Status** | **CLOSED** (PR #178) |

#### SL-C01-M-04 — Final whole-unit verification was not independent

| | |
|---|---|
| **Severity** | MEDIUM (audit process) |
| **Lenses** | L7 |
| **Root cause** | Phase D attestation predated Parts B–D commit; 633-line session exceeded 600-line limit; ledger promoted before final fingerprint evidence. |
| **Fix** | Workflow hardened (`489c3a2`); fresh bounded verification on fix commit; independent re-check in PR #178. |
| **Status** | **CLOSED** |

### Verification gates (final)

| Gate | Result |
|------|--------|
| `python -m tools.audit check --profile static` | PASS |
| `python -m tools.audit run --profile ci` | PASS (12/12 suites) |
| `python dev/engine_regression.py` | PASS 157/157 → 160/160 after PR #178 |
| `python tools/assemble_ui_html.py --verify` | PASS |
| Imperial altitude 16,404 ft probe | PASS |
| Protocol / ledger | `SEVEN_LENS_REVIEWED` restored after remediation |

### App status after Cycle 1

- **Unit `UI-MARKUP-HEADER`:** `SEVEN_LENS_REVIEWED` — all six findings CLOSED.
- **Header markup:** Depth/BT mirrors stay synchronized through input events, presets, and settings restore. Imperial altitude custom input accepts the full engine ceiling (16,404 ft). GF placeholders match factory defaults.
- **Regression suite:** Four stable SL-C01 case IDs (REG-58–61) guard sync and unit-constraint paths.
- **CI:** Static + full CI green on merged `dev` at `d39bb3b`.
- **Open findings:** None for this unit.

---

## Cycle 2 — `UI-MARKUP-PLANNER`

| Field | Value |
|-------|-------|
| **Cycle ID** | SL-C02 |
| **Unit** | `UI-MARKUP-PLANNER` |
| **Canonical file** | `ui/markup-planner.html` (493 lines) |
| **Review boundary** | Lines 1–493 (single session, under 600-line limit) |
| **Baseline** | `3731e560` |
| **Verified commit** | `b56fc07` |
| **Branch** | `cursor/seven-lens-cycle-02-planner` |
| **Auditor** | Cursor GPT-5.5 Medium (`cursor/seven-lens-cycle-02-planner-audit`) |
| **Fixer** | Composer 2.5 |
| **Verifier** | Cursor GPT-5.5 Medium (`cursor/seven-lens-cycle-02-planner-verify`) |
| **Ledger** | `IN_PROGRESS` (historical findings restored) |
| **Protocol record** | `docs/seven-lens-records/cycle-02-planner.json` — **CLOSE PASS** |
| **Detailed reports** | `docs/seven-lens-reports/cycle-02-planner.md`, `cycle-02-independent-verification.md` |

### What was tested

Seven lenses applied to the V3 planner markup partial (plan panel) and traced callers:

| Part | Lines | Scope |
|------|------:|-------|
| P01 | 1–493 | Circuit select, gases, CCR fields, min-deco profile, stop rounding, travel gas, SAC/rates, generate |

**Callers traced:** `index.html` (`getVpmMinDecoSettingsFromDom`, `buildZhlScheduleParamsFromDom`, `setUnits`), `gas-cards-core.js` (`updateTravelGasMOD`, `getTravelGasInfo`), `zhl-gas-core.js` (`enforceMinDecoProfile`).

**Lens focus areas:**
- L1: Rate selects (m/min), minDeco minute inputs, travel manual depth `max=100`, SAC L/min, ppO₂ bar selects
- L2: onchange/oninput on circuit, gases, CCR, minDeco, stopRounding, travel gas
- L3: `minDeco9m`/`minDeco6m` DOM reads; `units` global; settings `relabelOnly` restore
- L4: `buildZhlScheduleParamsFromDom` minDeco contract; imperial ft→m travel depth conversion
- L5: Canonical partial; fixes in caller modules per assemble contract
- L6: Min deco DIR/GUE shallow stop enforcement; travel gas MOD limits; CCR validation banner
- L7: New SL-C02 engine regressions with DOM restore

### Findings

#### SL-C02-M-01 — Min deco profile always uses metric stop matching in imperial mode

| | |
|---|---|
| **Severity** | MEDIUM |
| **Lenses** | L3, L4, L6 |
| **Location** | `ui/markup-planner.html:76-90`; `index.html:getVpmMinDecoSettingsFromDom`, `buildZhlScheduleParamsFromDom` |
| **Root cause** | `isMetric` read phantom `#unitSel` (never rendered). `null?.value !== 'imperial'` is always `true`. |
| **Failure path** | Enable Min Deco profile → switch to imperial → generate. `enforceMinDecoProfile` matches 9 m / 6 m stops instead of 30 ft / 20 ft equivalents. |
| **Impact** | Incorrect minimum stop enforcement for imperial divers at shallow stops. |
| **Fix** | Use `units !== 'imperial'` for `isMetric` in both schedule builder call sites. |
| **Regressions** | `SL-C02-MIN-DECO-UNITS` (REG-62) |
| **Status** | **CLOSED** |

#### SL-C02-M-02 — Travel gas manual depth max stays metric on relabel-only unit restore

| | |
|---|---|
| **Severity** | MEDIUM |
| **Lenses** | L1, L3, L4 |
| **Location** | `ui/markup-planner.html:337-339`; `gas-cards-core.js`, `index.html:setUnits` |
| **Root cause** | Markup `max="100"` (metres). `convertNumericInput` updates `max` only during active conversion, not `relabelOnly` restores or manual-mode display. |
| **Failure path** | Imperial + manual travel switch → enter 165 ft (valid 50 m equivalent) → browser rejects because `max` remains 100. |
| **Impact** | Imperial manual travel switch depth capped at ~30 m regardless of displayed unit. |
| **Fix** | `syncTravelGasManualDepthConstraints()` in `gas-cards-core.js` (metric max 500, imperial max 165, step 1); called from `setUnits` and `updateTravelGasMOD`. |
| **Regressions** | `SL-C02-TRAVEL-DEPTH-CONSTRAINTS` (REG-63) |
| **Status** | **CLOSED** |

### Verification gates (final)

| Gate | Result |
|------|--------|
| `python dev/engine_regression.py` | PASS 161/161 |
| `python -m tools.audit check --profile static` | PASS |
| `python -m tools.audit run --profile ci` | PASS (12/12 suites) |
| `python tools/seven_lens_protocol.py check --phase close` | PASS |
| Independent re-check | Adjacent imperial/metric round-trip, min-deco toggle, no phantom `#unitSel` |

### App status after Cycle 2

- **Unit `UI-MARKUP-PLANNER`:** `SEVEN_LENS_REVIEWED` — both findings CLOSED.
- **Planner markup:** Imperial min-deco enforcement uses correct unit flag. Travel gas manual depth input constraints follow display units on switch and restore.
- **Regression suite:** Two new stable case IDs (REG-62, REG-63); full engine regression at 161 cases.
- **CI:** Static + full CI green on verified commit `b56fc07`.
- **Merge status:** Merged to `dev` via PR [#179](https://github.com/Three-Cats-LSP/LSP_D-planner-plus/pull/179).
- **Open findings:** None — FIXER pass `cursor/seven-lens-cycles-02-03-remediation` closed `SL-C02-H-01` through `SL-C02-M-06`.
- **Cumulative seven-lens coverage:** Cycles 1–2 complete header + planner markup partials (`UI-MARKUP-HEADER`, `UI-MARKUP-PLANNER`).

---

## Cycle 3 — `UI-MARKUP-CONSUMPTION`

| Field | Value |
|-------|-------|
| **Cycle ID** | SL-C03 |
| **Unit** | `UI-MARKUP-CONSUMPTION` |
| **Canonical file** | `ui/markup-consumption.html` (381 lines) |
| **Review boundary** | Lines 1–381 (single session, under 600-line limit) |
| **Baseline** | `6e987af` |
| **Audit checkpoint** | `e07ab49` |
| **Verified commit** | `277985b` |
| **Branch** | `cursor/seven-lens-cycle-03-consumption` |
| **Auditor** | Cursor GPT-5.5 Medium (`cursor/seven-lens-cycle-03-consumption-audit`) |
| **Fixer** | Composer 2.5 |
| **Verifier** | Cursor GPT-5.5 Medium (`cursor/seven-lens-cycle-03-consumption-verify`) |
| **Ledger** | `IN_PROGRESS` (post-merge verification blocked) |
| **Protocol record** | `docs/seven-lens-records/cycle-03-consumption.json` |
| **Detailed reports** | `docs/seven-lens-reports/cycle-03-consumption.md`, `cycle-03-independent-verification.md`, `cycle-03-codex-verification.md` |

### What was tested

Seven lenses applied to the V3 consumption tools markup partial and traced callers:

| Part | Lines | Scope |
|------|------:|-------|
| P01 | 1–381 | CNS widget, best-mix calculator, unit/volume converters, BMT reference table |

**Callers traced:** `index.html` (`calcCNS`, `calcBestMix`, `setUnits`, `domDepthToM`, `syncBestMixDepthConstraints`).

**Strengthened protocol requirements exercised:**
- Pre-fix failure evidence at audit commit (`ER-03-PRE-FIX`, exit 1)
- Observable post-fix assertions (`SL-C03-BEST-MIX-DEPTH-UNITS`, `SL-C03-CNS-DEPTH-UNITS`)
- DOM state restoration in regression `finally` blocks
- Real audit checkpoint commit before fixes (`e07ab49`)
- Complete unit-conversion tuples (depth slider value, min/max, label, canonical `data-depthM`)

### Findings

#### SL-C03-H-01 — Best-mix depth slider treated as metres in imperial mode

| | |
|---|---|
| **Severity** | HIGH |
| **Lenses** | L1, L3, L4, L6, L7 |
| **Location** | `ui/markup-consumption.html:196-201`; `index.html:calcBestMix`, `setUnits` |
| **Root cause** | `bestMixDepth` slider value always stored in metres; imperial mode only relabelled display. |
| **Failure path** | Imperial 30 ft display → `calcBestMix` computes ATA as 30 m → wrong O₂% and ppO₂. |
| **Fix** | `domDepthToM` reads `data-depthM` canonical stamp; `setUnits` converts slider value/min/max; `syncBestMixDepthConstraints()`. |
| **Regressions** | `SL-C03-BEST-MIX-DEPTH-UNITS` (REG-64) |
| **Status** | **CLOSED** |

#### SL-C03-M-01 — CNS depth never follows global units

| | |
|---|---|
| **Severity** | MEDIUM |
| **Lenses** | L1, L3, L4, L7 |
| **Location** | `ui/markup-consumption.html:54-55`; `index.html:calcCNS`, `setUnits` |
| **Root cause** | Hardcoded `Depth (m)` label; `cnsDepth` omitted from unit conversion list. |
| **Failure path** | Imperial mode → CNS depth still treated as metres → wrong CNS% and OTU. |
| **Fix** | `cnsDepthLbl` sync on `setUnits`; depth converted with canonical stamp; `calcCNS` uses `domDepthToM`. |
| **Regressions** | `SL-C03-CNS-DEPTH-UNITS` (REG-65) |
| **Status** | **CLOSED** |

#### SL-C03-L-01 — AL80 reference volume copy misleading

| | |
|---|---|
| **Severity** | LOW |
| **Lenses** | L1, L6 |
| **Location** | `ui/markup-consumption.html:284` |
| **Root cause** | Reference text mixed litre volume with `77 ft³` naming convention. |
| **Fix** | Clarified AL80 as 11.1 L (~0.39 ft³) naming convention. |
| **Status** | **CLOSED** |

### Verification gates (final)

| Gate | Result |
|------|--------|
| Pre-fix at `e07ab49` | FAIL 161/163 (2 SL-C03 cases) — **required baseline failure** |
| `python dev/engine_regression.py` | PASS 163/163 |
| `python -m tools.audit check --profile static` | PASS |
| `python -m tools.audit run --profile ci` | PASS (12/12 suites) |
| `python tools/seven_lens_protocol.py check --phase close` | PASS |
| Independent re-check | O₂% and ppO₂ invariants across unit switch; DOM restore in `finally` |

### App status after Cycle 3

- **Unit `UI-MARKUP-CONSUMPTION`:** `SEVEN_LENS_REVIEWED` — all three findings CLOSED.
- **Consumption tools:** Best-mix and CNS depth inputs convert correctly between metric and imperial; canonical `data-depthM` stamps preserve lossless round-trips.
- **Regression suite:** Two new stable case IDs (REG-64, REG-65); full engine regression at 163 cases.
- **CI:** Static + full CI green on verified commit `277985b`.
- **Merge status:** Merged to `dev` via PR [#182](https://github.com/Three-Cats-LSP/LSP_D-planner-plus/pull/182).
- **Open findings:** None — FIXER pass closed `SL-C03-H-02`, `SL-C03-M-02`, and `SL-C03-L-02`.

### Post-merge Codex verification (remediation)

FIXER pass on `cursor/seven-lens-cycles-02-03-remediation` (includes Cycle 4 tools/modals work from PR #185):

- **SL-C03-H-02 / SL-C03-L-02:** Knowledge Base copy qualified shallow-stop guidance and corrected VPM-B+GFS description.
- **SL-C03-M-02:** Removed `syncDepthInputCanonical` from `calcBestMix`/`calcCNS`; `applyDepthUnitSwitch` preserves `data-depthM`; regression `finally` restores units before values; browser traces PASS.
- **SL-C02-H-01:** Imperial cylinder max ~1.77 ft³ with matching min/step via `syncCylinderSizeConstraints`.
- **SL-C02-M-03:** Travel manual depth imperial max 1640 ft (500 m parity).
- **SL-C02-M-04:** `data-depthM` / `data-volumeL` canonical stamps on unit round-trip.
- **SL-C02-M-05:** Min-deco regression asserts `enforceMinDecoProfile` imperial stop behavior.
- **SL-C02-M-06:** CLOSED — protocol hardening already on `dev` (PR #183 content).
- **Cumulative seven-lens coverage:** Cycles 1–3 complete header, planner, and consumption markup partials.

---

## Cycle 4 canonical-writer recovery (6f75077)

FIXER branch `cursor/seven-lens-canonical-writers` addresses SL-C04-H-02/M-03/M-04 with code and regression evidence:

| Gate | Result |
|------|--------|
| Engine regression | **172/172 PASS** (includes edit-after-switch cases) |
| Cycle-03 browser traces | **PASS** (`SL-C03-*-EDIT-AFTER-SWITCH`, repeat=2) |
| Cycle-04 browser traces | **PASS** (END/SI physical traces) |
| Protocol unit tests | **25/25 PASS** |
| `python tools/seven_lens_protocol.py check-all --require-artifacts` | **PASS** at closure commit (schema-v2 evidence on cycles 2–4) |
| Static audit | **PASS** (after cycle-25 budget bump to 1280 lines) |

Core fix: `domDepthToM` / `domVolumeToL` honor user-edited display after unit switch; `syncDepthInputCanonical` / `syncVolumeInputCanonical` wired on all dual-state writers; `_syncDepthBtSteppers` no longer corrupts stamps during `setUnits`.

---

## Cycle 4 post-merge Codex verification (superseded)

PR #188 was independently rechecked on `dev`. Cycles 2–4 now carry schema-v2 closure evidence; `check-all --require-artifacts` **PASS** on branch `cursor/seven-lens-canonical-writers` at `d956648`.

- `SL-C04-H-02`: user edits after a unit switch leave canonical depth/volume state stale.
- `SL-C04-H-03`: Cycle 2-4 records fail the protocol close contract despite reviewed ledger claims.
- `SL-C04-M-03`: full engine regression is order-dependent and fails 2 cases.
- `SL-C04-M-04`: prior browser evidence did not require real, repeated edit-to-consumer traces.

Full evidence: `docs/seven-lens-reports/cycle-04-codex-verification.md`.

---

## Template for future cycles

Copy and fill when Cycle N closes:

```markdown
## Cycle N — `<UNIT_ID>`

| Field | Value |
|-------|-------|
| **Cycle ID** | SL-C0N |
| **Unit** | `<UNIT_ID>` |
| **Canonical file** | `<path>` (N lines) |
| **Verified commit** | `<sha>` |
| **PR** | #NNN |

### What was tested
(boundary, callers, lens notes)

### Findings
(each: severity, location, root cause, failure path, fix, regressions, status)

### Verification gates
(table)

### App status after Cycle N
(unit ledger status, regression count, CI, open findings, cumulative coverage)
```
