/**
 * Environment (altitude, water density, narcosis) and app mode/planner state orchestration.
 * Loaded by index.html before other UI runtime cores.
 * Globals read: ZhlEngineBundle, VPMEngine, ZHL16C_HE_HT, ZHL16C_HE_HT_BAKER, ZHL16C_HE_HT_BUHL2003,
 *   runDecoSchedule, runPlanner, renderNDLTable, buildDiveBlocks, setDecoAlgorithm, switchResultTab,
 *   _clearResultSummaryStrip, _setGasWarningBanner, _applyGasWarningStyles, refreshTravelGasFractionWarning,
 *   _travelGasFractionWarning, updateGasMODDisplays, updateTravelGasMOD, calcMODTool, renderModRefTable,
 *   calcBestMixTec, calcBestMix, renderEADTable, renderGasTable, calcCNS, onConservatismChange,
 *   updateCcrGasValidation, calcContingency, syncRecGasMixDisplay, toggleCustomO2, _syncVpmModeUI,
 *   handleGFSelect, setGF, scheduleDecoScheduleStackSync, decorateDecoTableForV3, drawPlannerProfile,
 *   drawDecoProfile, drawDecoProfileFull, drawGFCurve, setMainNav, appSettings
 * Globals written: BAR_PER_METRE, altSurfaceP, altitudeM, altAcclimatized, WATER_VAPOR, narcoticN2, narcoticO2,
 *   navMode, plannerAlgo, algo, units, mGF, allowO2AtMOD, lastTissues, _pendingDecoAlerts,
 *   _pendingDecoAlertsNarcotic, _vpmHeHtSyncFailed, window._lastPlan, _lastVPMResult, window._lastVPMExport
 */

const SEA_LEVEL_P = 1.01325; // ISA sea-level pressure (bar)
const SURFACE_P = SEA_LEVEL_P; // alias — runtime pressure uses altSurfaceP
let altSurfaceP   = 1.01325; // actual surface pressure at current altitude (bar)
let altitudeM     = 0;       // current altitude in metres
let altAcclimatized = false;  // false unless user explicitly saved 'yes'
// Expose altitude globals for test harnesses (let doesn't land on window automatically)
if (typeof window !== 'undefined') {
  Object.defineProperties(window, {
    altSurfaceP:   { get: () => altSurfaceP,   set: v => { altSurfaceP = v; },   configurable: true },
    altitudeM:     { get: () => altitudeM,     set: v => { altitudeM = v; },     configurable: true },
    altAcclimatized:{ get: () => altAcclimatized, set: v => { altAcclimatized = v; }, configurable: true },
  });
}
let WATER_VAPOR = 0.0577; // LSP default (MultiDeco); synced from #waterVapor via updateWaterVapor()
window.WATER_VAPOR = WATER_VAPOR; // expose for test harnesses

// Water density pressure factors (bar per metre)
const WATER_DENSITY = {
  fresh:    0.09681,  // 10.330 m/bar — matches VPM SLP_FW_M
  en13319:  0.09921,  // 10.080 m/bar — EN13319 standard (DiveKit/MultiDeco)
  salt:     0.10000,  // 10.000 m/bar — industry standard (MultiDeco/DiveKit/ApexDeco)
};
// AUDIT-UNIT:UI-ENVIRONMENT
// NOTE: WATER_DENSITY values are canonical m/bar-derived constants matching MultiDeco/DiveKit:
//   salt:    10.000 m/bar = 0.10000 bar/m (MultiDeco/DiveKit/ApexDeco standard)
//   fresh:   10.330 m/bar = 0.09681 bar/m
//   EN13319: 10.080 m/bar = 0.09921 bar/m (EN13319 standard — DiveKit compatible)
// Strict SI:  1000 kg/m³ × 9.80665 / 100000 = 0.09807 bar/m (fresh)
//             1025 kg/m³ × 9.80665 / 100000 = 0.10052 bar/m (standard ocean)
// Init = salt default (0.10000); overwritten by setWaterDensity() on startup.
let BAR_PER_METRE = 0.10000; // salt default (10.000 m/bar); updated by setWaterDensity()
window.BAR_PER_METRE = BAR_PER_METRE;

// ── Narcosis settings ──
let narcoticN2 = true;   // N₂ always narcotic by default
let narcoticO2 = true;   // O₂ narcotic by default (NOAA/IANTD standard)

// Shared narcotic depth tooltip content
const _narcoticTipTitle = 'Narcotic Depth (END)';
window._narcoticTipTitle = _narcoticTipTitle;
const _narcoticTipText  =
`Equivalent Narcotic Depth (END) measures the narcotic effect of a gas mix by comparing it to the depth at which breathing air would produce the same narcotic partial pressure.

Why 30 m?
Most technical training agencies (PADI TecRec, IANTD, TDI) recommend keeping END ≤ 30 m (100 ft) as a practical working limit. At this depth on air, narcosis is typically mild and manageable for trained divers. Beyond 30 m equivalent, cognitive impairment, delayed reaction times and poor decision-making become increasingly likely.

Why 40 m?
40 m is often cited as the absolute recreational air diving limit, where narcotic effects are significant for most divers. An END above 40 m on a technical dive is considered high-risk.

Helium is non-narcotic. Adding helium to a mix displaces nitrogen and reduces the narcotic partial pressure, lowering END. For example, a 21/35 trimix at 60 m has an END of roughly 35 m — equivalent to an air dive to 35 m.

N₂ narcotic setting: whether O₂ counts toward END is configurable on the Deco Schedule tab (N₂ Narcotic / O₂ Narcotic toggles). NOAA/IANTD count both; some agencies exclude O₂.`;
window._narcoticTipText = _narcoticTipText;

const _toolsBmtFaqTitle = 'Nitrox Best Mix — FAQ';
window._toolsBmtFaqTitle = _toolsBmtFaqTitle;
const _toolsBmtFaqText  =
`What does "best mix" mean?
The best nitrox mix is the blend whose O₂ fraction keeps ppO₂ at exactly the limit (e.g. 1.4 bar) at your target depth — highest O₂ without exceeding the safe ppO₂, reducing nitrogen and extending no-deco bottom time vs. air.

Why is ppO₂ 1.4 bar the standard limit?
Above 1.6 bar the risk of CNS oxygen toxicity rises sharply — convulsions can occur with little warning, which is fatal underwater. Most agencies recommend 1.4 bar for bottom gas and up to 1.6 bar only for brief shallow deco stops.

What is EAD (Equivalent Air Depth)?
EAD is the air depth with the same nitrogen partial pressure as your nitrox at a given depth. Because nitrox has less N₂ than air, EAD is always shallower — you accumulate nitrogen as if diving shallower, extending NDL limits.

What is MOD (Maximum Operating Depth)?
MOD is the deepest depth at which a mix can be used without exceeding the ppO₂ limit. Going deeper risks oxygen toxicity. Formula: MOD = (ppO₂ ÷ O₂ fraction − 1) × 10 m at sea level.

Can I use these mixes on a standard dive computer?
Yes — set the O₂% to match the analysed cylinder fill. The computer applies the EAD automatically for NDL calculations. Always analyse your cylinder before every dive.

Why does the O₂% stay the same across several depths?
Best mix is rounded down to the nearest whole %. At shallow depths the limit allows up to 40% O₂, so EAN40 appears optimal across multiple rows until depth is great enough to require a lower fraction.`;

function setNarcosis(gas, isNarc) {
  if (gas === 'n2') {
    narcoticN2 = isNarc;
    const sel = document.getElementById('n2NarcSel');
    if (sel) sel.value = isNarc ? 'yes' : 'no';
  } else {
    narcoticO2 = isNarc;
    const sel = document.getElementById('o2NarcSel');
    if (sel) sel.value = isNarc ? 'yes' : 'no';
  }
}

/**
 * Equivalent Narcotic Depth (END)
 * END = ((ppNarcotic / ppNarcotic_air_at_surface) - 1) / BAR_PER_METRE  ... simplified:
 * Standard formula: END = (pNarc / pNarc_air_surface) * 10 - 10  (in metres)
 * pNarc = total narcotic partial pressure at depth
 * pNarc_air_surface = narcotic pp of air at surface (reference)
 *
 * fNarcN2: N₂ fraction in gas (0–1), used if narcoticN2
 * fNarcO2: O₂ fraction in gas (0–1), used if narcoticO2
 * depthM : actual depth
 * returns END in metres (0 if no narcotic component)
 */
function calcEND(depthM, fN2, fHe) {
  // He is non-narcotic; fO2 = 1 - fN2 - fHe for trimix
  const fH = fHe || 0;
  const fO2 = Math.max(0, 1 - fN2 - fH);
  const pAmb = altSurfaceP + depthM * BAR_PER_METRE;

  // Narcotic partial pressures at depth (He excluded — non-narcotic)
  const pNarcN2 = narcoticN2 ? pAmb * fN2 : 0;
  const pNarcO2 = narcoticO2 ? pAmb * fO2 : 0;
  const pNarc   = pNarcN2 + pNarcO2;

  // Reference: narcotic pp of air at surface
  const fN2air = FN2_AIR;
  const fO2air = 1 - FN2_AIR;
  const pNarcAirSurface = (narcoticN2 ? altSurfaceP * fN2air : 0) +
                           (narcoticO2 ? altSurfaceP * fO2air : 0);

  if (pNarcAirSurface <= 0) return null;

  // END = depth at which air would produce same narcotic pp
  // pNarcAirSurface + END * BAR_PER_METRE * (fN2air*(narcoticN2?1:0) + fO2air*(narcoticO2?1:0)) = pNarc
  const narcoticFracAir = (narcoticN2 ? fN2air : 0) + (narcoticO2 ? fO2air : 0);
  const end = narcoticFracAir > 0
    ? (pNarc / narcoticFracAir - altSurfaceP) / BAR_PER_METRE
    : 0;
  if (end < 0) return null;
  return end;
}

/** Total narcotic partial pressure (bar) at depth — shares narcoticN2/narcoticO2 with calcEND. */
function calcNarcPP(depthM, fN2, fHe) {
  const fH = fHe || 0;
  const fO2 = Math.max(0, 1 - fN2 - fH);
  const pAmb = altSurfaceP + depthM * BAR_PER_METRE;
  const pNarcN2 = narcoticN2 ? pAmb * fN2 : 0;
  const pNarcO2 = narcoticO2 ? pAmb * fO2 : 0;
  return pNarcN2 + pNarcO2;
}

// Parse the deepest depth (m) from a rendered Depth-cell, converting ft→m if needed.
function endParseDepthM(text) {
  if (!text) return null;
  const isFt = /ft/i.test(text);
  const nums = (text.match(/[\d.]+/g) || []).map(parseFloat).filter(n => !isNaN(n));
  if (!nums.length) return null;
  let d = Math.max.apply(null, nums);
  if (isFt) d = d / 3.28084;
  return d;
}

function _envSettingsSummary() {
  const waterLabel = waterDensityDisplayLabel();
  const u     = document.getElementById('unitsSelect')?.value || 'metric';
  const alt   = document.getElementById('altitudeSelect')?.value || '0';
  const parts = [];
  if (waterLabel !== 'Salt') parts.push(waterLabel);
  if (u     !== 'metric') parts.push('ft');
  if (alt   !== '0')     parts.push(alt + 'm');
  return parts.length ? parts.join(' · ') : '';
}

function syncEnvRowDisplay() {
  const body = document.getElementById('envSettingsBody');
  if (body) body.style.display = navMode === 'settings' ? 'flex' : '';
}

function _updateEnvToggleTitle() {
  /* legacy no-op — settings live on dedicated page */
}

function _updateEnvSummary() {
  const body = document.getElementById('envSettingsBody');
  if (!body || body.style.display !== 'none') return;
  _updateEnvToggleTitle();
}

function setWaterDensity(type, customKgM3) {
  if (type === 'custom') {
    const kg = parseFloat(customKgM3 || document.getElementById('waterCustomInput')?.value || 1025);
    BAR_PER_METRE = (kg * 9.80665) / 100000;
  } else {
    BAR_PER_METRE = WATER_DENSITY[type] || WATER_DENSITY.salt;
  }
  window.BAR_PER_METRE = BAR_PER_METRE; // keep window reference in sync
  const sel = document.getElementById('waterDensitySelect');
  if (sel) sel.value = type;
  const customRow = document.getElementById('waterCustomRow');
  if (customRow) customRow.style.display = type === 'custom' ? 'flex' : 'none';
  localStorage.setItem('waterDensity', type);
  if (type === 'custom') localStorage.setItem('waterDensityCustom', customKgM3 || document.getElementById('waterCustomInput')?.value || 1025);
  replanAfterEnvChange();
}

function replanAfterEnvChange() {
  if (window._zhlHeadless) return;
  renderNDLTable();
  const decoRes = document.getElementById('decoResult');
  if (decoRes && decoRes.style.display !== 'none' && decoRes.innerHTML.trim()) {
    runDecoSchedule();
  }
  const planRes = document.getElementById('plannerResult');
  if (planRes && planRes.style.display !== 'none' && planRes.innerHTML.trim()) {
    runPlanner();
  }
}

function waterDensityDisplayLabel() {
  // Canonical default is Salt (matches waterDensitySelect, BAR_PER_METRE init, setWaterDensity on load).
  const key = localStorage.getItem('waterDensity') || document.getElementById('waterDensitySelect')?.value || 'salt';
  if (key === 'custom') {
    const kg = localStorage.getItem('waterDensityCustom') || document.getElementById('waterCustomInput')?.value;
    return kg ? 'Custom (' + kg + ' kg/m³)' : 'Custom';
  }
  const map = { fresh: 'Fresh', en13319: 'EN13319', salt: 'Salt' };
  return map[key] || 'Salt';
}

function applyCustomWaterDensity(inputId) {
  const val = parseFloat(document.getElementById(inputId)?.value);
  if (!val || val < 900 || val > 1100) return;
  const inp = document.getElementById('waterCustomInput');
  if (inp) inp.value = val;
  setWaterDensity('custom', val);
}

// ═══════════════════════════════════════════════
// ALTITUDE
// ═══════════════════════════════════════════════

// Barometric formula: p = 1.01325 * exp(-alt_m / 8434)
function altToPressure(altM) {
  return SEA_LEVEL_P * Math.exp(-altM / 8434);
}

function refreshAltitudeDependentUI() {
  if (window._zhlHeadless) return;
  updateGasMODDisplays?.();
  updateTravelGasMOD?.();
  calcMODTool?.();
  renderModRefTable?.();
  calcBestMixTec?.();
  calcBestMix?.();
  renderEADTable?.();
  renderGasTable?.();
}

function setAltitude() {
  // Read altitude from UI (custom input is in display units; presets are metres)
  const sel = document.getElementById('altitudeSelect');
  const customInput = document.getElementById('altitudeCustomInput');
  const selVal = sel ? sel.value : '0';
  const altM = selVal === 'custom'
    ? altitudeMFromCustomDisplay(customInput?.value)
    : parseFloat(selVal) || 0;

  // Acclimatized setting
  const acclSel = document.getElementById('acclimatizedSelect');
  altAcclimatized = !acclSel || acclSel.value === 'yes';

  // Store
  altitudeM   = Math.max(0, Math.min(5000, altM));
  altSurfaceP = altToPressure(altitudeM);

  // Update pressure badge
  const badge = document.getElementById('altitudePressureDisplay');
  if (badge) {
    if (altitudeM === 0) {
      badge.textContent = '';
    } else {
      badge.textContent = altSurfaceP.toFixed(3) + ' bar';
    }
  }

  // Save to localStorage
  try { localStorage.setItem('lspAltitude', altitudeM); } catch(e) {}
  try { localStorage.setItem('lspAcclimatized', altAcclimatized ? 'yes' : 'no'); } catch(e) {}

  // Re-run active calculation if result is showing (skip in headless test mode)
  if (!window._zhlHeadless) renderNDLTable();
  const decoRes = document.getElementById('decoResult');
  if (!window._zhlHeadless && decoRes && decoRes.style.display !== 'none' && decoRes.innerHTML.trim()) {
    runDecoSchedule();
  }
  const planRes = document.getElementById('plannerResult');
  if (planRes && planRes.style.display !== 'none' && planRes.innerHTML.trim()) {
    runPlanner();
  }
  calcCNS();

  refreshAltitudeDependentUI();
}

function handleAltitudeSelect(val) {
  const customRow = document.getElementById('altitudeCustomRow');
  const unitSpan  = document.getElementById('altitudeCustomUnit');
  if (val === 'custom') {
    if (customRow) customRow.style.display = 'flex';
    if (unitSpan)  unitSpan.textContent = units === 'imperial' ? 'ft' : 'm';
  } else {
    if (customRow) customRow.style.display = 'none';
  }
  setAltitude();
}

function applyCustomAltitude() {
  setAltitude();
}

function altitudeMFromCustomDisplay(raw) {
  const v = parseFloat(raw) || 0;
  return units === 'imperial' ? v / 3.28084 : v;
}

function altitudeMToCustomDisplay(m) {
  return units === 'imperial' ? Math.round(m * 3.28084) : Math.round(m);
}

function loadAltitudeFromStorage() {
  try {
    const savedAlt  = parseFloat(localStorage.getItem('lspAltitude')) || 0;
    const savedAccl = localStorage.getItem('lspAcclimatized') === 'yes';
    altitudeM   = savedAlt;
    altSurfaceP = altToPressure(altitudeM);
    altAcclimatized = savedAccl;
    // Sync dropdowns
    const sel = document.getElementById('altitudeSelect');
    if (sel) {
      const matchOpt = Array.from(sel.options).find(o => parseFloat(o.value) === altitudeM);
      sel.value = matchOpt ? String(altitudeM) : 'custom';
      const customRow = document.getElementById('altitudeCustomRow');
      const customInp = document.getElementById('altitudeCustomInput');
      if (!matchOpt) {
        if (customRow) customRow.style.display = 'flex';
        if (customInp) customInp.value = altitudeMToCustomDisplay(altitudeM);
      }
    }
    const acclSel = document.getElementById('acclimatizedSelect');
    if (acclSel) acclSel.value = altAcclimatized ? 'yes' : 'no';
    // Update badge
    const badge = document.getElementById('altitudePressureDisplay');
    if (badge && altitudeM > 0) badge.textContent = altSurfaceP.toFixed(3) + ' bar';
  } catch(e) {}
  refreshAltitudeDependentUI();
}

function setAllowO2AtMOD(val) {
  allowO2AtMOD = (val === true || val === 'on');
  const sel = document.getElementById('o2AtMODSelect');
  if (sel) sel.value = val ? 'on' : 'off';
}
function updateWaterVapor() {
  const val = parseFloat(document.getElementById('waterVapor')?.value) || 0.0627;
  WATER_VAPOR = val;
  window.WATER_VAPOR = val; // keep window reference in sync
}

function updateHeHalfTime() {
  const mode = document.getElementById('heHalfTimeMode')?.value || 'baker';
  const src = mode === 'baker' ? ZHL16C_HE_HT_BAKER : ZHL16C_HE_HT_BUHL2003;
  // Update global array in-place (preserves all references)
  for (let i = 0; i < 16; i++) ZHL16C_HE_HT[i] = src[i];
  if (window.ZhlEngineBundle && typeof ZhlEngineBundle.setHeHalfTimeMode === 'function') {
    ZhlEngineBundle.setHeHalfTimeMode(mode);
  }
  // Patch VPMEngine's internal ZHL16C_He[].ht to match (comp [0] differs: 1.88 vs 1.51)
  _vpmHeHtSyncFailed = false;
  if (window.VPMEngine && typeof window.VPMEngine._syncHeHalfTimes === 'function') {
    window.VPMEngine._syncHeHalfTimes(src);
  } else if (window.VPMEngine && typeof window.VPMEngine._setHeHT1 === 'function') {
    window.VPMEngine._setHeHT1(src[0]);
  } else if (window.VPMEngine) {
    console.warn('[LSP] VPMEngine He half-time sync skipped — _syncHeHalfTimes not available');
    _vpmHeHtSyncFailed = true;
  }
}
let _vpmHeHtSyncFailed = false;
function appendHeHtSyncAlert(container) {
  if (!_vpmHeHtSyncFailed || !container) return;
  container.insertAdjacentHTML('beforeend',
    '<div class="alert" style="margin-top:8px;background:rgba(255,165,0,0.15);border-color:orange;color:var(--text);">' +
    '<span>⚠</span><div><strong>He half-time sync unavailable.</strong> VPM engine could not receive Bühlmann He HT updates — VPM schedules may use stale He compartment times until refresh.</div></div>');
}
let _pendingDecoAlerts = '';
let _pendingDecoAlertsNarcotic = '';
// AUDIT-UNIT:UI-MODE-STATE
function renderDecoAlerts(container, cnsHtml) {
  if (!container) return;
  refreshTravelGasFractionWarning();
  container.innerHTML = (_pendingDecoAlerts || '') + (_travelGasFractionWarning || '') + (cnsHtml || '');
  appendHeHtSyncAlert(container);
  const narcContainer = document.getElementById('decoAlertsNarcotic');
  if (narcContainer) {
    narcContainer.innerHTML = _pendingDecoAlertsNarcotic || '';
    if (!narcContainer.innerHTML.trim()) narcContainer.style.display = 'none';
    else narcContainer.style.display = '';
  }
}
const FN2_AIR   = 0.79;
const FN2_EAN32 = 0.68;
const FN2_EAN36 = 0.64;

// ═══ STATE ═══
let navMode     = 'planner';
let plannerAlgo = 'ZHLC_GF';
let algo        = 'buh'; // compat shim: padi|buh|tools
let units      = 'metric';
let ndlUnits   = 'metric';
let multiUnits = 'metric';
let diveCount  = 2;
let stopDepthM = 6;
    let allowO2AtMOD = true;
let stopDurMin = 3;
let mGF        = { low: 20, high: 85 }; // matches default preset 20/85
window._gfSyncSilent = false; // suppress gfLow/gfHigh onchange while setGF syncs programmatically

const GF_BUHLMANN_PRESETS = [
  { value: '20/85', label: '20/85' },
  { value: '30/70', label: '30/70' },
  { value: '40/85', label: '40/85' },
  { value: '50/75', label: '50/75' },
  { value: 'custom', label: 'Custom' },
];

const GF_VPMGFS_PRESETS = [
  { value: 'hi/70', label: '70' },
  { value: 'hi/80', label: '80' },
  { value: 'hi/85', label: '85' },
  { value: 'custom', label: 'Custom' },
];

function _ensureBuhlmannGfSelectOptions() {
  const sel = document.getElementById('gfPresetSelect');
  if (!sel || document.getElementById('algorithmSelect')?.value === 'VPMB_GFS') return;
  const need = GF_BUHLMANN_PRESETS.map(p => p.value);
  const have = Array.from(sel.options).map(o => o.value);
  if (need.join('|') !== have.join('|')) {
    sel.innerHTML = GF_BUHLMANN_PRESETS.map(p =>
      `<option value="${p.value}">${p.label}</option>`
    ).join('');
  }
}

function _ensureVpmGfsGfSelectOptions() {
  const sel = document.getElementById('gfPresetSelect');
  if (!sel || document.getElementById('algorithmSelect')?.value !== 'VPMB_GFS') return;
  const need = GF_VPMGFS_PRESETS.map(p => p.value);
  const have = Array.from(sel.options).map(o => o.value);
  if (need.join('|') !== have.join('|')) {
    sel.innerHTML = GF_VPMGFS_PRESETS.map(p =>
      `<option value="${p.value}">${p.label}</option>`
    ).join('');
  }
}

function _findGfPresetOption(low, high) {
  const sel = document.getElementById('gfPresetSelect');
  if (!sel) return null;
  const isVPMBGFS = document.getElementById('algorithmSelect')?.value === 'VPMB_GFS';
  const presetVal = isVPMBGFS ? `hi/${high}` : `${low}/${high}`;
  return Array.from(sel.options).find(o => o.value === presetVal) || null;
}

function syncGfPresetFromValues() {
  setGF(mGF.low, mGF.high);
}
let lastTissues = null;

// ═══════════════════════════════════════════════
// ALGO SWITCH
// ═══════════════════════════════════════════════
function setBrandIcon(_mode) {
  /* Static Three Cats LSP logo — mode-specific emoji icons removed. */
}

function _syncDepthBtSteppers() {
  const d = parseFloat(document.getElementById('decoDepth')?.value) || 40;
  const b = parseFloat(document.getElementById('decoBT')?.value) || 30;
  const dEl = document.getElementById('depth'); if (dEl) dEl.value = d;
  const bEl = document.getElementById('bt'); if (bEl) bEl.value = b;
  const dv = document.getElementById('depthStepperVal'); if (dv) dv.textContent = Math.round(d);
  const bv = document.getElementById('btStepperVal'); if (bv) bv.textContent = Math.round(b);
  const du = document.getElementById('depthUnitLbl'); if (du) du.textContent = units === 'imperial' ? 'ft' : 'm';
}

function stepDepthBt(field, delta) {
  const isDepth = field === 'depth';
  const id = isDepth ? 'decoDepth' : 'decoBT';
  const el = document.getElementById(id);
  if (!el) return;
  let v = parseFloat(el.value) || (isDepth ? 40 : 30);
  if (isDepth) {
    const step = units === 'imperial' ? 3 : 1;
    const maxD = units === 'imperial' ? 394 : 120;
    v = Math.max(1, Math.min(maxD, v + delta * step));
  } else {
    v = Math.max(1, Math.min(300, v + delta));
  }
  el.value = v;
  _syncDepthBtSteppers();
  updateCcrGasValidation?.();
  updateGasMODDisplays?.();
  if (window._lastContingency) calcContingency?.();
}

function setConservatismBtn(val, btn) {
  const sel = document.getElementById('conservatismSelect');
  if (sel) { sel.value = String(val); onConservatismChange?.(); }
  document.querySelectorAll('#conservatismBtns .cons-btn').forEach(b => b.classList.toggle('active', b === btn));
}

function _syncConservatismBtns() {
  const v = document.getElementById('conservatismSelect')?.value || '2';
  document.querySelectorAll('#conservatismBtns .cons-btn').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-val') === v);
  });
}

function _syncGfCustomRowVisible() {
  const customRow = document.getElementById('gfCustomRow');
  const sel = document.getElementById('gfPresetSelect');
  if (!customRow) return;
  const showGF = plannerAlgo === 'ZHLC_GF' || plannerAlgo === 'VPMB_GFS';
  const isCustom = sel?.value === 'custom';
  const open = showGF && isCustom;
  customRow.style.display = open ? 'flex' : 'none';
  customRow.classList.toggle('is-open', open);
  if (!open) return;
  const isVPMBGFS = document.getElementById('algorithmSelect')?.value === 'VPMB_GFS';
  const lowField = document.getElementById('gfLowPair');
  if (lowField) lowField.style.display = isVPMBGFS ? 'none' : '';
}

function _buildGfPresetBtns() {
  const wrap = document.getElementById('gfPresetBtns');
  const sel = document.getElementById('gfPresetSelect');
  if (!wrap || !sel) return;
  const isVPMBGFS = document.getElementById('algorithmSelect')?.value === 'VPMB_GFS';
  if (!isVPMBGFS) _ensureBuhlmannGfSelectOptions();
  else _ensureVpmGfsGfSelectOptions();
  const presets = isVPMBGFS ? GF_VPMGFS_PRESETS : GF_BUHLMANN_PRESETS;
  const cur = sel.value;
  wrap.innerHTML = '';
  presets.forEach(opt => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'gf-preset-btn' + (cur === opt.value ? ' active' : '');
    btn.dataset.value = opt.value;
    btn.textContent = opt.label;
    btn.onclick = () => { sel.value = opt.value; handleGFSelect(opt.value); };
    wrap.appendChild(btn);
  });
}

function _highlightGfPresetBtn(val) {
  const sel = document.getElementById('gfPresetSelect');
  const v = val || sel?.value;
  document.querySelectorAll('#gfPresetBtns .gf-preset-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.value === v);
  });
}

function runGenerateSchedule() {
  if (plannerAlgo === 'rec') runPlanner();
  else runDecoSchedule();
}

function _clearPlannerResults() {
  ['decoResult','gasConsumptionSummary','contingencyCard','contingencyResult','diveGraphCard','fullDiveGraphCard','gfCurveInlineCard','tissueLoadCard',
   'plannerProfileCanvas-wrap','recSurfIntContainer','tecSurfIntContainer','graphsDiveSectionHead','graphsGfSectionHead'].forEach(id => {
    const el = document.getElementById(id); if (el) el.style.display = 'none';
  });
  const contExport = document.getElementById('contingencyExportActions');
  if (contExport) contExport.style.display = 'none';
  _clearResultSummaryStrip();
  _setGasWarningBanner('');
  const totalsEl = document.getElementById('decoTotals');
  if (totalsEl) { totalsEl.innerHTML = ''; totalsEl.style.display = 'none'; }
  const _pr2 = document.getElementById('plannerResult'); if(_pr2){_pr2.style.display='none';_pr2.innerHTML='';}
  window._lastPlan = null;
  _lastVPMResult = null;
  window._lastContingency = null;
  window._lastVPMExport = null;
}

function _plannerShowsGfCurve() {
  return plannerAlgo === 'ZHLC_GF' || plannerAlgo === 'VPMB_GFS';
}
function _syncGfCurveCardVisibility() {
  const gfc = document.getElementById('gfCurveInlineCard');
  const gfHead = document.getElementById('graphsGfSectionHead');
  const hasPlan = document.getElementById('decoResult')?.style.display !== 'none';
  const show = _plannerShowsGfCurve() && hasPlan && !_contingencyRunning;
  if (gfc) {
    gfc.style.display = show ? 'block' : 'none';
    if (show) gfc.classList.add('card-open');
  }
  if (gfHead) gfHead.style.display = show ? 'flex' : 'none';
}
function _syncGraphsSectionHeads() {
  const hasPlan = document.getElementById('decoResult')?.style.display !== 'none';
  const diveHead = document.getElementById('graphsDiveSectionHead');
  const fdgc = document.getElementById('fullDiveGraphCard');
  if (diveHead) diveHead.style.display = (hasPlan && fdgc?.style.display !== 'none') ? 'flex' : 'none';
  _syncGfCurveCardVisibility();
}

function _updatePlannerSubtitle() {
  const labels = {
    rec: ['REC NDL', 'PADI recreational tables'],
    ZHLC_GF: ['BÜHLMANN', 'ZH-L16C · Gradient Factors'],
    VPMB: ['VPM-B', 'Bubble Model'],
    VPMB_GFS: ['VPM-B+GFS', 'Gradient Factor Surfacing'],
  };
  const [lbl, sub] = labels[plannerAlgo] || labels.ZHLC_GF;
  const el = document.getElementById('algoLabel'); if (el) el.textContent = lbl;
  const subEl = document.getElementById('algoSubtitle'); if (subEl) subEl.textContent = sub;
}

function _updatePlanPanelSections() {
  const isRec = plannerAlgo === 'rec';
  const recSec = document.getElementById('planPanelRecSection');
  const tecSec = document.getElementById('planPanelTecSection');
  const gfV3 = document.getElementById('gfPresetsRowV3');
  const consV3 = document.getElementById('conservatismRowV3');
  const vpmModeV3 = document.getElementById('vpmModeRowV3');
  const isVpm = plannerAlgo === 'VPMB' || plannerAlgo === 'VPMB_GFS';
  if (recSec) recSec.classList.toggle('visible', isRec);
  if (tecSec) tecSec.classList.toggle('visible', !isRec);
  if (gfV3) gfV3.style.display = (!isRec && (plannerAlgo === 'ZHLC_GF' || plannerAlgo === 'VPMB_GFS')) ? '' : 'none';
  if (consV3) consV3.classList.toggle('visible', isVpm);
  if (vpmModeV3) vpmModeV3.classList.toggle('visible', isVpm);
  const recTabs = document.getElementById('recResultTabs');
  const tecTabs = document.getElementById('tecResultTabs');
  if (recTabs) recTabs.style.display = isRec ? 'flex' : 'none';
  if (tecTabs) tecTabs.style.display = isRec ? 'none' : 'flex';
  if (!isRec) _syncGfCurveCardVisibility();
  else {
    const gfCard = document.getElementById('gfCurveInlineCard');
    if (gfCard) gfCard.style.display = 'none';
    const gfHead = document.getElementById('graphsGfSectionHead');
    if (gfHead) gfHead.style.display = 'none';
  }
  document.querySelectorAll('#resultsPanel #resultTab-dive, #resultsPanel #resultTab-surfint, #resultsPanel #resultTab-avgdepth, #resultsPanel #resultTab-multi, #resultsPanel #resultTab-ndlref').forEach(p => {
    p.classList.remove('active');
  });
  document.querySelectorAll('#resultsPanel #resultTab-profile, #resultsPanel #resultTab-contingency, #resultsPanel #resultTab-graphs, #resultsPanel #resultTab-tissue').forEach(p => {
    p.classList.remove('active');
  });
  const firstRec = document.querySelector('#recResultTabs .result-tab-btn');
  const firstTec = document.querySelector('#tecResultTabs .result-tab-btn');
  if (isRec && firstRec) switchResultTab(firstRec.getAttribute('data-tab'), firstRec);
  else if (!isRec && firstTec) switchResultTab(firstTec.getAttribute('data-tab'), firstTec);
  setBrandIcon(isRec ? 'rec' : 'planner');
  document.body.classList.toggle('rec-mode', isRec);
  document.body.classList.toggle('algo-buh', !isRec);
  _updatePlannerSubtitle();
}

function _updatePlanPanelTip(model) {
  const tip = document.getElementById('planPanelDecoTip');
  if (!tip) return;
  const algo = model || plannerAlgo;
  let desc;
  if (algo === 'rec') {
    desc = 'Recreational dive planning: depth, bottom time, breathing gas, and optional safety stop. NDL limits are computed from PADI recreational tables.';
  } else if (algo === 'VPMB') {
    desc = 'Generates a full ascent profile using VPM-B (Variable Permeability Model). Bubble mechanics determine stop depths — conservatism 0–5 scales initial bubble radii. No gradient factors.';
  } else if (algo === 'VPMB_GFS') {
    desc = 'VPM-B+GFS (Gradient Factor Surfacing). VPM-B sets deep stop depths; GF High applies a Bühlmann-style ceiling blend at shallow stops — less aggressive surface obligation than pure VPM-B.';
  } else {
    desc = 'Generates a full ascent profile with deco stops using Bühlmann ZH-L16C + Gradient Factors. Configure up to two decompression gases below — they switch automatically at the specified depths during ascent and are factored into tissue off-gassing.';
  }
  tip.setAttribute('onclick', `showTip('Dive Parameters','${desc.replace(/'/g, "\\'")}')`);
}

function setPlannerAlgo(model, btn) {
  plannerAlgo = model;
  if (model === 'VPMB' || model === 'VPMB_GFS') {
    vpmVariant = model;
    try { localStorage.setItem('vpmVariant', model); } catch (e) {}
    _syncVpmModeUI?.(model);
  }
  document.querySelectorAll('#mainNavBar .main-nav-btn').forEach(b => b.classList.remove('active'));
  const navMap = { rec: 'navBtnRec', ZHLC_GF: 'navBtnBuh', VPMB: 'navBtnVpm', VPMB_GFS: 'navBtnVpm' };
  if (btn && btn.classList?.contains('main-nav-btn')) btn.classList.add('active');
  else {
    const id = navMap[model];
    if (id) document.getElementById(id)?.classList.add('active');
  }
  if (model === 'rec') {
    algo = 'padi';
    syncRecGasMixDisplay?.();
    toggleCustomO2?.();
  } else {
    algo = 'buh';
    setDecoAlgorithm(model, true);
  }
  _clearPlannerResults();
  _updatePlanPanelSections();
  _updatePlanPanelTip(model);
  renderNDLTable?.();
  buildDiveBlocks?.();
  if (typeof appSettings !== 'undefined' && appSettings.save) setTimeout(() => appSettings.save(false), 100);
}

function setAlgo(a) {
  // Compat shim for tests / persisted settings
  window._lastVPMExport = null;
  if (a === 'tools') { setMainNav('tools'); return; }
  setMainNav('buh');
  if (a === 'padi') setPlannerAlgo('rec');
  else setPlannerAlgo(plannerAlgo === 'rec' ? 'ZHLC_GF' : (document.getElementById('algorithmSelect')?.value || 'ZHLC_GF'));
}

// ═══════════════════════════════════════════════
// THEME TOGGLE
// ═══════════════════════════════════════════════
// ═══════════════════════════════════════════════
// TABLE VIEW TOGGLE (mobile)
// ═══════════════════════════════════════════════
function toggleTableView() {
  const table  = document.querySelector('#decoTableBody')?.closest('table');
  const btn    = document.getElementById('tableViewToggle');
  if (!table || !btn) return;
  const isTable = table.classList.toggle('table-view');

  // Wrap in scroll container when switching to table view
  if (isTable) {
    if (!table.parentElement.classList.contains('table-scroll-wrap')) {
      const wrap = document.createElement('div');
      wrap.className = 'table-scroll-wrap';
      wrap.style.cssText = 'overflow-x:auto;-webkit-overflow-scrolling:touch;';
      table.parentNode.insertBefore(wrap, table);
      wrap.appendChild(table);
    }
  } else {
    if (table.parentElement.classList.contains('table-scroll-wrap')) {
      const wrap = table.parentElement;
      wrap.parentNode.insertBefore(table, wrap);
      wrap.remove();
    }
  }

  btn.textContent = isTable ? '⊟ Table' : '⊞ Cards';
  btn.style.color = isTable ? 'var(--accent)' : 'var(--muted)';
  btn.style.borderColor = isTable ? 'var(--accent)' : 'var(--border)';
  localStorage.setItem('decoTableView', isTable ? 'table' : 'cards');
  scheduleDecoScheduleStackSync();
  decorateDecoTableForV3();
}

function loadTableViewPreference() {
  const saved = localStorage.getItem('decoTableView');
  // Default is 'table' — only switch to cards if explicitly saved
  if (saved !== 'cards') {
    const table = document.querySelector('#decoTableBody')?.closest('table');
    const btn   = document.getElementById('tableViewToggle');
    if (table) table.classList.add('table-view');
    if (btn) {
      btn.textContent = '⊟ Table';
      btn.style.color = 'var(--accent)';
      btn.style.borderColor = 'var(--accent)';
    }
  }
}

// ── Info tip popup (click/tap tooltips) ──
function _modalIsOpen(id) {
  const el = document.getElementById(id);
  if (!el) return false;
  const d = el.style.display;
  return d === 'flex' || d === 'block';
}

function handleNativeBackForModals() {
  const sheet = document.getElementById('lsp-android-select-sheet');
  if (sheet) {
    sheet.remove();
    document.body.classList.remove('lsp-android-select-open');
    return true;
  }
  if (_modalIsOpen('confirmModal')) { closeConfirmModal(false); return true; }
  if (_modalIsOpen('configPresetModal')) { closeAdvConfigPresets(); return true; }
  if (_modalIsOpen('profilePresetModal')) { closeDiveProfilePresets(); return true; }
  if (_modalIsOpen('slateModal')) { closeSlate(); return true; }
  if (_modalIsOpen('copyModal')) { closeCopyModal(); return true; }
  if (_modalIsOpen('presetModal')) { closePresetModal(); return true; }
  if (_modalIsOpen('tipModal')) { closeTip(); return true; }
  if (_modalIsOpen('gasRuleModal')) { closeGasRuleInfo(); return true; }
  if (_modalIsOpen('warningModal')) { toggleWarningModal(); return true; }
  if (_modalIsOpen('settingsHelpModal')) {
    document.getElementById('settingsHelpModal').style.display = 'none';
    return true;
  }
  if (_modalIsOpen('referenceModal')) { toggleReference(); return true; }
  if (document.getElementById('pdfExportDialog')) { document.getElementById('pdfExportDialog').remove(); return true; }
  if (document.getElementById('contingencyPDFDialog')) { document.getElementById('contingencyPDFDialog').remove(); return true; }
  return false;
}

function initNativeModalBackHandler() {
  try {
    if (!window.Capacitor?.isNativePlatform?.()) return;
    const App = window.Capacitor.Plugins?.App;
    if (!App || window._lspModalBackHooked) return;
    window._lspModalBackHooked = true;
    App.addListener('backButton', function() {
      if (handleNativeBackForModals()) return;
      App.exitApp();
    });
  } catch (e) {}
}

function showTip(title, text) {
  const titleEl = document.getElementById('tipModalTitle');
  const bodyEl = document.getElementById('tipModalBody');
  const m = document.getElementById('tipModal');
  if (!titleEl || !bodyEl || !m) return;
  titleEl.textContent = title;
  bodyEl.textContent = text;
  m.style.display = 'block';
  bodyEl.scrollTop = 0;
}
function closeTip() {
  const m = document.getElementById('tipModal');
  if (m) m.style.display = 'none';
}
window.showTip = showTip;
window.closeTip = closeTip;

function showGasRuleInfo() {
  const m = document.getElementById('gasRuleModal');
  m.style.display = 'block';
}
function closeGasRuleInfo() {
  document.getElementById('gasRuleModal').style.display = 'none';
}

function toggleWarningModal() {
  const modal = document.getElementById('warningModal');
  if (!modal) return;
  modal.style.display = modal.style.display === 'none' ? 'block' : 'none';
}

function toggleReference() {
  const modal = document.getElementById('referenceModal');
  modal.style.display = modal.style.display === 'none' ? 'block' : 'none';
}

function _lspCssVar(name, fallback) {
  const bodyV = getComputedStyle(document.body).getPropertyValue(name).trim();
  const rootV = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return bodyV || rootV || fallback;
}

function toggleTheme() {
  const body = document.body;
  const isLight = body.classList.toggle('light-theme');
  const toggle = document.getElementById('themeToggle');
  if (toggle) toggle.setAttribute('aria-pressed', isLight ? 'true' : 'false');
  
  // Save preference
  localStorage.setItem('diveTheme', isLight ? 'light' : 'dark');
  // Also write to cookie so native Java can read theme on next startup
  document.cookie = 'diveTheme=' + (isLight ? 'light' : 'dark') + '; path=/; max-age=31536000';
  
  // Update PWA theme color (target the active/non-media meta tag)
  const metaThemeColor = document.getElementById('theme-color-active');
  if (metaThemeColor) {
    metaThemeColor.setAttribute('content', isLight ? '#f0f4f8' : '#0f1117');
  }
  
  console.log('[LSP] Theme switched to:', isLight ? 'LIGHT' : 'DARK');

  // Sync Android status bar color with theme (Capacitor native only)
  try {
    if (window.Capacitor?.isNativePlatform() && window.Capacitor?.Plugins?.StatusBar) {
      window.Capacitor.Plugins.StatusBar.setStyle({ style: isLight ? 'LIGHT' : 'DARK' }); // LIGHT=dark icons, DARK=white icons
      window.Capacitor.Plugins.StatusBar.setBackgroundColor({ color: isLight ? '#ffffff' : '#161b24' });
    }
  } catch(e) {}

  // Re-apply JS-forced warning row colors for new theme
  ['gasConsumptionSummary','emergencyGasConsumption'].forEach(id => {
    const el = document.getElementById(id);
    if (el && el.style.display !== 'none') _applyGasWarningStyles(el);
  });

  // Redraw canvases for new theme
  setTimeout(() => {
    drawPlannerProfile();
    drawDecoProfile();
    drawDecoProfileFull();
    drawGFCurve();
  }, 50);
}

// Load theme preference on page load
function loadThemePreference() {
  const savedTheme = localStorage.getItem('diveTheme');
  const body = document.body;
  const toggle = document.getElementById('themeToggle');
  const isLight = savedTheme === 'light';

  if (isLight) {
    body.classList.add('light-theme');
  } else {
    body.classList.remove('light-theme');
  }
  if (toggle) toggle.setAttribute('aria-pressed', isLight ? 'true' : 'false');

  // Write cookie on startup so Java has it even on first cold launch after fresh install
  document.cookie = 'diveTheme=' + (isLight ? 'light' : 'dark') + '; path=/; max-age=31536000';

  // Update theme-color meta on load for correct status bar icon color
  const _tcMeta = document.getElementById('theme-color-active');
  if (_tcMeta) _tcMeta.setAttribute('content', isLight ? '#f0f4f8' : '#0f1117');

  // Ensure status bar is visible and styled correctly on startup
  try {
    if (window.Capacitor?.isNativePlatform() && window.Capacitor?.Plugins?.StatusBar) {
      window.Capacitor.Plugins.StatusBar.show();
      window.Capacitor.Plugins.StatusBar.setOverlaysWebView({ overlay: false });
    }
  } catch(e) {}

  // Sync Android status bar icon color with initial theme
  // Use a helper so it can be called again after the bridge is ready
  function _applyStatusBarTheme() {
    try {
      if (window.Capacitor?.isNativePlatform() && window.Capacitor?.Plugins?.StatusBar) {
        // LIGHT style = dark icons (for light app bg), DARK style = light icons (for dark app bg)
        window.Capacitor.Plugins.StatusBar.setStyle({ style: isLight ? 'LIGHT' : 'DARK' });
        window.Capacitor.Plugins.StatusBar.setBackgroundColor({ color: isLight ? '#ffffff' : '#161b24' });
      }
    } catch(e) {}
  }
  // Call immediately (may be too early if bridge not ready yet)
  _applyStatusBarTheme();
  // Call again after 500ms to ensure bridge is fully initialised
  setTimeout(_applyStatusBarTheme, 500);
  // Also re-apply when app resumes from background
  try {
    if (window.Capacitor?.isNativePlatform()) {
      window.Capacitor.Plugins.App?.addListener('appStateChange', function(state) {
        if (state.isActive) _applyStatusBarTheme();
      });
      initNativeModalBackHandler();
    }
  } catch(e) {}
}

// ═══════════════════════════════════════════════
// GF SELECTOR
// ═══════════════════════════════════════════════
