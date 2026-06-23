# LSP D-Planner+CCR — Errors & Bugs Report v11

**App version**: v2.30.12 (commit `30e996c`)  
**Audit date**: 2026-06-21  
**Auditor**: Deep code audit (static analysis)  
**Previous report**: errors_bugs_report_v10.md (BUG-51–56, all fixed in v2.30.12)  
**Scope**: Full deep audit of `index.html` — CCR/pSCR engine, gas plan, exports, UI/settings, VPM parity

---

## Summary

6 new bugs found (BUG-57 through BUG-62).  
All v10 bugs (BUG-51–56) confirmed fixed.  
No regressions introduced by the v2.30.12 fixes.

---

## BUG-57 — `ccrDiluentSurfaceLpm` pSCR: double-depth-scaling of diluent consumption

**Severity**: HIGH  
**Area**: CCR engine — gas consumption  
**File location**: `ccrDiluentSurfaceLpm` (~line 5946), `ccrGasLitres` (~line 5980)

### Description

The new pSCR branch in `ccrDiluentSurfaceLpm` returns a surface-equivalent LPM value:

```js
const fr = computePSCRFractions(pAmb, bot.fO2, bot.fHe, ccr.scrRuntimeMin || 0, ccr);
const fO2Loop = Math.max(0.01, fr.fO2);
return (metRate / fO2Loop) * PSCR_DEFAULT_BYPASS_RATIO;
```

`computePSCRFractions(pAmb, ...)` is called with `pAmb = altSurfaceP + depthM * BAR_PER_METRE`,
so `fO2Loop` is already depth-dependent — it decreases as depth increases (lower loop O₂ partial
pressure at depth relative to total loop pressure). This makes the surface LPM estimate
implicitly depth-scaled via fO2Loop.

Then `ccrGasLitres` multiplies the result by the pressure ratio again:

```js
return ccrDiluentSurfaceLpm(depthM) * (pAmb / pSurf) * durMin;
```

This second multiplication converts surface-LPM to actual litres at depth — correct for a true
surface-LPM. But since `fO2Loop` already embedded a depth-dependent factor, the pressure
conversion partially double-counts depth. The deeper the dive, the more overstated the
pSCR diluent consumption estimate.

### Expected behaviour

`ccrDiluentSurfaceLpm` should return a pure surface-LPM that is depth-independent, so that
`ccrGasLitres` can correctly convert it to actual litres with `* (pAmb / pSurf)`.  
OR `ccrDiluentSurfaceLpm` should return actual litres-per-minute (already pressure-converted),
and `ccrGasLitres` should not multiply by `(pAmb / pSurf)` for the pSCR case.

---

## BUG-58 — `ccrDiluentSurfaceLpm` pSCR: `scrRuntimeMin` is always 0 at gas-plan time

**Severity**: LOW–MEDIUM  
**Area**: CCR engine — gas consumption  
**File location**: `ccrDiluentSurfaceLpm` (~line 5946), `computePSCRFractions` (~line 5757)

### Description

```js
const fr = computePSCRFractions(pAmb, bot.fO2, bot.fHe, ccr.scrRuntimeMin || 0, ccr);
```

`ccr.scrRuntimeMin` is set by `getCCRSettingsFromDOM()`:

```js
scrRuntimeMin: 0  // not read from DOM; only set internally during schedule generation
```

At gas-plan calculation time (when `calcGasPlan()` → `ccrDiluentSurfaceLpm()` is called),
`scrRuntimeMin` is always 0. This means `computePSCRFractions` always uses the initial
(undepleted) loop O₂ fraction, as if no O₂ has been metabolised yet.

For shallow short dives the error is negligible. For long/deep pSCR dives the loop O₂
is meaningfully depleted mid-dive, so using `runtimeMin=0` slightly overestimates `fO2Loop`,
which slightly underestimates the required flow rate / gas consumption.

### Note

This is an inherent limitation of computing gas plan from a single-point snapshot rather
than integrating over the schedule. It is a minor accuracy issue, not a logic crash.
Documenting for awareness.

---

## BUG-59 — `toggleCircuitFields` BUG-55 fix hides bailout GF group for pSCR bailout-ON

**Severity**: MEDIUM  
**Area**: UI — circuit field visibility  
**File location**: `toggleCircuitFields` (~line 5990)

### Description

The BUG-55 fix added:

```js
const boGrp = document.getElementById('ccrBailoutSettingsGroup');
const bailoutOn = document.getElementById('ccrBailoutToggle')?.value === 'on';
if (boGrp) boGrp.style.display = (isCCR && bailoutOn) ? '' : 'none';
```

The condition `isCCR` is `circuit === 'CCR'` — it is `false` when `circuit === 'pSCR'`.
Therefore when pSCR mode has `ccrBailoutToggle = 'on'`, `ccrBailoutSettingsGroup` is hidden.

However `runDecoSchedule` does apply the bailout GF for **any** circuit with `_ccrSettings.bailout`:

```js
if (_ccrSettings.bailout) {
    _zhlPrevGF = { low: mGF.low, high: mGF.high };
    const boLo = _ccrSettings.bailoutGfLow ?? 50;
    const boHi = _ccrSettings.bailoutGfHigh ?? 85;
    mGF.low = boLo;
    mGF.high = boHi;
    ...
}
```

And `getCCRSettingsFromDOM` reads `bailout` from `ccrBailoutToggle` regardless of circuit.

So pSCR bailout-ON dives use the bailout GF selectors but the user cannot see or set them
because `ccrBailoutSettingsGroup` is hidden. The dive runs with whatever the previous hidden
values are (default 50/85).

### Expected behaviour

`ccrBailoutSettingsGroup` should be shown when `(isRB && bailoutOn)` — i.e. for both CCR and
pSCR when bailout is on — since both circuits apply the bailout GF.

---

## BUG-60 — VPM `getEffectiveSetpoint` hardcodes `circuit: 'CCR'` — pSCR gets wrong setpoint

**Severity**: MEDIUM  
**Area**: VPM engine — pSCR tissue loading  
**File location**: VPMEngine `getEffectiveSetpoint` (~line 8482)

### Description

Inside VPMEngine, `getEffectiveSetpoint` builds a local `ccr` object:

```js
const ccr = {
    circuit: settings?.circuit || 'CCR',   // ← hardcoded default 'CCR'
    descentSetpoint: settings?.descentSetpoint ?? 0.7,
    bottomSetpoint:  settings?.bottomSetpoint ?? 1.2,
    decoSetpoint:    settings?.decoSetpoint ?? settings?.setpoint ?? 1.3,
    setpoint:        settings?.setpoint ?? 1.3,
    bailout: false,
};
return getEffectiveSetpointAtDepth(depthM != null ? depthM : 0, ccr, surfP);
```

When `settings.circuit` is `'pSCR'`, the circuit is correctly propagated.
However `getEffectiveSetpointAtDepth` for pSCR returns `0` (no setpoint):

```js
// getEffectiveSetpointAtDepth (~line 5737):
if (!ccr || ccr.bailout || !isRebreatherCircuit(ccr.circuit)) return 0;
if (ccr.circuit === 'pSCR') return 0;
```

This is correct for pSCR (pSCR has no electronic setpoint). The problem is that the computed
`curSP = 0` then flows into `loadTissuesConstant / loadTissuesLinear` via `setpoint=curSP`,
and those functions call `getInspiredInertPressures(pAmb, setpoint=0, fO2, fHe, ccr)`.

`getInspiredInertPressures` with `setpoint=0` and a `pSCR` circuit correctly enters the
pSCR branch and calls `computePSCRFractions` — so tissue loading itself is correct.

BUT `getEffectiveSetpoint` also gates whether VPM treats the dive as `offLoopPath`:

```js
let curSP = forcedOCMode ? 0 : getEffectiveSetpoint(levels[0], isCCR, settings, levels[0].depth);
...
const offLoopPath = isCCR && (forcedOCMode || curSP <= 0);
```

`isCCR = isRebreatherCircuit(settings.circuit) && !settings.bailout` — for pSCR this is
`true`. `curSP = 0` (correct for pSCR), so `offLoopPath = true`. The VPM engine therefore
treats pSCR as OC/off-loop for ceiling and conservatism calculations (`interLevelConservatism`
is reduced by 1 for offLoopPath). This is likely **not** the intended behaviour for pSCR —
pSCR is on-loop (semi-closed), not open-circuit, and should not get the off-loop ceiling
relaxation.

### Expected behaviour

pSCR should be treated as on-loop (not offLoopPath) in VPM. `offLoopPath` should only be
true for actual bailout mode or forced OC segments, not for normal pSCR on-loop operation.

---

## BUG-61 — VPM gas consumption: `gasKey` uses display label (e.g. `"CCR Air"`) but `isCcrDiluentGasLabel` may not match it

**Severity**: MEDIUM  
**Area**: VPM engine — gas consumption  
**File location**: `renderVPMResults` gas consumption loop (~line 7487)

### Description

VPM gas consumption is computed post-render by reading the table DOM:

```js
const gasKey = mixRaw; // labels now always in O2/He format (e.g. '50/00', '21/35', '100/00')
gasConsVPM[gasKey] = (gasConsVPM[gasKey] || 0) + ccrGasLitres(gasKey, depthM2, durMin, sac);
```

The comment says labels are "always in O2/He format", but for on-loop CCR/pSCR the table
renders `gasDisp` as the loop label:

```js
const gasDisp = _vpmOnLoop
    ? loopMixLabelFor(getGasLabel(o2pct/100, hepct/100), _vpmCcr)  // e.g. "CCR Air"
    : getGasLabel(o2pct/100, hepct/100);  // e.g. "21/00"
```

So for on-loop CCR/pSCR, `mixRaw` read from `tds[3].textContent` will be `"CCR Air"` or
`"pSCR Air"` (the `gasDisp` value written to the cell), not `"21/00"`.

`ccrGasLitres(gasKey = "CCR Air", ...)` then calls `isCcrDiluentGasLabel("CCR Air")`.
That function calls `isCcrOnLoopGasLabel("CCR Air")` first, which checks:

```js
return u.startsWith('CCR ') || u.startsWith('PSCR ');
```

This matches `"CCR Air"` → returns `true` → `ccrDiluentSurfaceLpm(depthM)` is called ✓.

**However**, the `depthM2` parsed from `tds[1].textContent` for descent/ascent rows contains
strings like `"0→40m"` or `"40→0m"`, so `parseFloat("0→40m") = 0` — giving depth=0 for
those rows. Stop rows show e.g. `"9m"` which parses correctly.

For on-loop bottom/ascent/descent rows, `depthM2 = 0` is passed to `ccrDiluentSurfaceLpm`,
making `pAmb = altSurfaceP` (surface pressure) for all movement phases. This causes
`ccrGasLitres` to underestimate gas consumption for bottom and transit phases — the
`(pAmb / pSurf)` multiplier becomes 1.0 regardless of actual depth.

### Expected behaviour

`depthM2` for descent/ascent rows should use the midpoint or target depth, not a raw parse
of the arrow-format depth string.

---

## BUG-62 — `appSettings.clear()` misses several localStorage keys written by the app

**Severity**: LOW  
**Area**: Settings persistence  
**File location**: `appSettings.clear()` (~line 17515)

### Description

`appSettings.clear()` only removes:
- `lspDiveSettings_v6`
- `lspDiveSettings_v3`
- `lspDiveSettings_v2`
- `lspDiveSettings`

But the app writes to additional localStorage keys that are not cleared:
- `waterDensity` (set by `setWaterDensity`)
- `waterDensityCustom` (set by `setWaterDensity` for custom density)
- `lspAltitude` / `lspAcclimatized` (set by altitude change)
- `gfCustomLow` / `gfCustomHigh` (set by GF preset handler)
- `lspCcrAdvOpen` (CCR advanced section open/closed state)
- `lspEnvOpen` / `lspAdvancedOpen` (section collapse states)
- `lspUserAdvDefaults` (user's personal advanced defaults — set via "Save as my defaults")
- `decoTableView` (table vs card view toggle)
- `diveTheme` (light/dark theme)
- `lspDiveSettings_v4` / `lspDiveSettings_v5` (if any users have these from intermediate versions)

`fullResetApp()` manually clears `lspAltitude`, `lspAcclimatized`, `gfCustomLow`,
`gfCustomHigh`, and `lspDiveSettings_v6` separately, but does not clear the others either.

A user calling `appSettings.clear()` directly (e.g. from the settings reset button) will
retain stale `waterDensity`, altitude, theme, and CCR advanced defaults, leading to
unexpected settings state after the clear.

### Expected behaviour

`appSettings.clear()` should also remove all app-owned localStorage keys, or at minimum
those that are part of the dive configuration state (`waterDensity`, `lspAltitude`,
`lspAcclimatized`, `gfCustomLow`, `gfCustomHigh`, `lspUserAdvDefaults`).

---

## Carry-Over Observations (not new bugs, from v10)

These were noted in v10 and remain unresolved in this release — kept for tracking:

- **OC Main BUG-40**: Bühlmann emergency gas `sz` not converted cu ft→L in OC main ~line 9789  
  *(Out of scope — OC main repo only)*
- **OC Main BUG-41**: `appSettings.clear()` only removes `lspDiveSettings_v3` in OC main ~line 16449  
  *(Out of scope — OC main repo)*

---

## Previously Fixed (confirmed in v2.30.12)

| Bug | Description | Status |
|-----|-------------|--------|
| BUG-51 | `getCCRInertSchreinerParams` pSCR rate had spurious `* pressureRate` | ✅ Fixed |
| BUG-52 | `isCcrOnLoopGasLabel` only checked `'CCR '` prefix, missed `'PSCR '` | ✅ Fixed |
| BUG-53 | `shortMix()` `/air/i` matched partial strings (e.g. "EAN 32" contains no "air" but "Fairy" would) | ✅ Fixed → `/^air$/i` |
| BUG-54 | `ZHLEngine` `prevCCR` did not save/restore `diluentUseAsBailout` | ✅ Fixed |
| BUG-55 | `ccrBailoutSettingsGroup` shown for pSCR even without bailout | ✅ Fixed |
| BUG-56 | `ccrDiluentSurfaceLpm` had no pSCR branch — used CCR O₂ fraction for pSCR | ✅ Fixed |

---

## New Bugs Summary

| Bug | Area | Severity | Description |
|-----|------|----------|-------------|
| BUG-57 | CCR engine / gas consumption | HIGH | pSCR diluent consumption double-depth-scaled (`fO2Loop` depth-dependent + `pAmb/pSurf` multiplier) |
| BUG-58 | CCR engine / gas consumption | LOW | `scrRuntimeMin=0` at gas-plan time → always uses undepleted loop O₂ for pSCR flow estimate |
| BUG-59 | UI / circuit fields | MEDIUM | `ccrBailoutSettingsGroup` hidden for pSCR bailout-ON despite bailout GF being applied |
| BUG-60 | VPM engine / pSCR | MEDIUM | VPM treats pSCR as `offLoopPath` (OC-like) due to `curSP=0`, reducing ceiling conservatism |
| BUG-61 | VPM gas consumption | MEDIUM | On-loop VPM rows: `depthM2` parses `"0→40m"` as `0`, underestimates gas for bottom/transit phases |
| BUG-62 | Settings persistence | LOW | `appSettings.clear()` misses several localStorage keys (`waterDensity`, altitude, GF custom, `lspUserAdvDefaults`, etc.) |
