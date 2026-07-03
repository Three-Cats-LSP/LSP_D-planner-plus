# Seven-Lens Test Results — Cycle History

Consolidated record of every manual seven-lens audit cycle: what was reviewed, what
was found, how it was fixed, and application status after closure.

**Maintenance:** After each cycle closes (`python tools/seven_lens_protocol.py check
--phase close`), append or update the cycle section here, then push and merge the
cycle PR to `dev`. If independent verification later finds residual defects, set the
cycle back to **BLOCKED**, record new findings, and do not mark complete until a
fresh FIXER + VERIFIER pass closes them. Keep detailed reports in
`docs/seven-lens-reports/` and protocol records in `docs/seven-lens-records/`.

| Cycle | Unit | Status | Source commit | PR |
|------:|------|--------|---------------|-----|
| 1 | `UI-MARKUP-HEADER` | **CLOSED** — merged to `dev` | `d39bb3b` | [#177](https://github.com/Three-Cats-LSP/LSP_D-planner-plus/pull/177), [#178](https://github.com/Three-Cats-LSP/LSP_D-planner-plus/pull/178) |
| 2 | `UI-MARKUP-PLANNER` | **BLOCKED** — post-merge verification failed | `b56fc07` / merge `b37d836` | [#179](https://github.com/Three-Cats-LSP/LSP_D-planner-plus/pull/179) merged; [#180](https://github.com/Three-Cats-LSP/LSP_D-planner-plus/pull/180) draft (block + protocol) |

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
| **Merge on dev** | `b37d836` (PR #179) |
| **Independent verifier** | Codex post-merge (`codex/cycle02-independent-verification`, `74dcf45`) |
| **Ledger** | `IN_PROGRESS` (was prematurely `SEVEN_LENS_REVIEWED`) |
| **Protocol record** | `docs/seven-lens-records/cycle-02-planner.json` — **BLOCKED** |
| **Detailed reports** | `cycle-02-planner.md`, `cycle-02-independent-verification.md` (Cursor, insufficient), `cycle-02-codex-verification.md` (authoritative block) |
| **Remediation PR** | [#180](https://github.com/Three-Cats-LSP/LSP_D-planner-plus/pull/180) — protocol hardening + open findings; **do not merge** until FIXER/VERIFIER close defects |

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
| **Fix attempted** | `units !== 'imperial'` for `isMetric` in schedule builders |
| **Regressions** | `SL-C02-MIN-DECO-UNITS` (REG-62) — flag only, not schedule output |
| **Status** | **BLOCKED** — original fix insufficient; regression coverage gap |

#### SL-C02-M-02 — Travel gas manual depth max stays metric on relabel-only unit restore

| | |
|---|---|
| **Severity** | MEDIUM |
| **Lenses** | L1, L3, L4 |
| **Location** | `ui/markup-planner.html:337-339`; `gas-cards-core.js`, `index.html:setUnits` |
| **Root cause** | Markup `max="100"` (metres). `convertNumericInput` updates `max` only during active conversion, not `relabelOnly` restores or manual-mode display. |
| **Failure path** | Imperial + manual travel switch → enter 165 ft (valid 50 m equivalent) → browser rejects because `max` remains 100. |
| **Impact** | Imperial manual travel switch depth capped at ~30 m regardless of displayed unit. |
| **Fix attempted** | `syncTravelGasManualDepthConstraints()` — partial; see SL-C02-M-03 |
| **Regressions** | `SL-C02-TRAVEL-DEPTH-CONSTRAINTS` (REG-63) — browser constraint only, not physical parity |
| **Status** | **BLOCKED**

#### SL-C02-H-01 — Imperial cylinder size constraints permit impossible volumes

| | |
|---|---|
| **Severity** | HIGH |
| **Lenses** | L1, L3, L4, L6 |
| **Location** | `ui/markup-planner.html` cylinder fields; `index.html:3464-3475`; `gas-cards-core.js:defaultDecoCylFieldValues` |
| **Root cause** | Litres→ft³ conversion applied to values but imperial `max=1766` (should be ~1.77 ft³ for 50 L). Metric `min=1` / `step=0.5` remain after values like `0.4 ft³`. |
| **Failure path** | Switch to imperial → default 12 L → 0.4 ft³ rejected (below min 1); 2 ft³ or hundreds of ft³ accepted. |
| **Impact** | Normal cylinders invalid; physically impossible volumes accepted → gas reserve overestimate. |
| **Fix** | `a5bc972` derives metric/imperial cylinder size constraints from 1-50 L physical bounds for static, dynamic, and gas-plan inputs. |
| **Regressions** | `SL-C02-CYLINDER-PHYSICAL-CONSTRAINTS` (REG-64) |
| **Status** | **CLOSED**

#### SL-C02-M-03 — Travel switch-depth limits not physically equivalent

| | |
|---|---|
| **Severity** | MEDIUM |
| **Lenses** | L1, L3, L4, L6 |
| **Location** | Markup `max=100` m; `syncTravelGasManualDepthConstraints` metric `500` m, imperial `165` ft (~50 m) |
| **Root cause** | Three conflicting maxima; no single canonical metre ceiling. |
| **Failure path** | 77 m travel MOD valid in metric; equivalent 253 ft rejected in imperial. |
| **Impact** | Valid manual travel depths accepted/rejected by display unit alone. |
| **Fix needed** | One canonical metre maximum (e.g. 100 m from markup); derive imperial feet everywhere. |
| **Regressions** | `SL-C02-TRAVEL-DEPTH-PHYSICAL-PARITY` (proposed) |
| **Status** | **OPEN**

#### SL-C02-M-04 — Unit round trips mutate the active dive plan

| | |
|---|---|
| **Severity** | MEDIUM |
| **Lenses** | L1, L3, L6 |
| **Location** | `index.html:3352-3480` (`setUnits`, `convertNumericInput`) |
| **Root cause** | Display-rounded values written back as canonical; integer ft and one-decimal ft³ lose precision. |
| **Failure path** | Metric → imperial → metric with defaults. |
| **Impact** | 40 m → 39.9 m; 12 L cylinders → 11 L without user action. |
| **Fix needed** | Preserve canonical physical values or higher-precision conversion; bidirectional round-trip tests. |
| **Regressions** | `SL-C02-UNIT-ROUNDTRIP-IMMUTABLE` (proposed) |
| **Status** | **OPEN**

#### SL-C02-M-05 — Min-deco regression does not test schedule behavior

| | |
|---|---|
| **Severity** | MEDIUM (test evidence) |
| **Lenses** | L4, L7 |
| **Location** | `dev/engine_regression.py` `sevenLensCycle02`; ZHL/VPM min-deco engines |
| **Root cause** | `SL-C02-MIN-DECO-UNITS` asserts unused `isMetric` adapter flag; engines use internal metre depths. |
| **Failure path** | Schedule output can be wrong while regression passes. |
| **Fix needed** | Assert observable metric/imperial schedule stops (9 m/30 ft, 6 m/20 ft parity); prove pre-fix failure. |
| **Regressions** | `SL-C02-MIN-DECO-OBSERVABLE-PARITY` (proposed) |
| **Status** | **OPEN**

#### SL-C02-M-06 — Protocol accepted nonexistent audit checkpoint

| | |
|---|---|
| **Severity** | MEDIUM (audit process) |
| **Lens** | L7 |
| **Root cause** | `audit_commit` equalled baseline; audit/fix/tests combined; old protocol still returned CLOSE PASS. |
| **Fix** | Protocol hardened in `74dcf45` / PR #180: distinct report-only audit commit, pre-fix failure + post-fix observable assertions, state restoration evidence, full unit-conversion tuples. |
| **Regressions** | `SEVEN-LENS-AUDIT-CHECKPOINT` (protocol unit tests) |
| **Status** | **OPEN** (process — addressed in PR #180, not yet on `dev`) |

### Verification gates

| Gate | Cursor verify (PR #179) | Codex independent (PR #180) |
|------|-------------------------|------------------------------|
| `python dev/engine_regression.py` | PASS 161/161 | PASS — demonstrates coverage gap |
| `python -m tools.audit check --profile static` | PASS | BLOCKED (open HIGH `SL-C02-H-01`) |
| `python -m tools.audit run --profile ci` | PASS 12/12 | PASS |
| `python tools/seven_lens_protocol.py check --phase close` | PASS (weak) | BLOCKED (strengthened checker) |
| Chromium physical probes | not run | FAIL (cylinder, travel parity, round-trip) |

### App status after Cycle 2 (current)

- **Unit `UI-MARKUP-PLANNER`:** **BLOCKED** — 7 open/blocked findings (2 original repairs insufficient, 5 residual).
- **On `dev`:** PR #179 merged; unit-conversion defects remain in production code paths.
- **Protocol:** Strengthened on `codex/cycle02-independent-verification` (`74dcf45`); awaits merge via PR #180 after code fixes.
- **Next step:** FIXER branch from `dev` → resolve H-01, M-03–M-05 → fresh VERIFIER → merge remediation PR → then merge #180 protocol/ledger updates.
- **Cumulative coverage:** Cycle 1 closed; Cycle 2 **not** closed despite earlier ledger promotion.

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
