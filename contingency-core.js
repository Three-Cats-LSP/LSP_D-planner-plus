/**
 * Emergency contingency scenario runner — RUNTIME UI CORE.
 * Loaded by index.html before main inline script.
 * Globals read: runDecoSchedule, getBottomGasFractions, getCCRSettingsFromDOM, isRebreatherCircuit,
 *   domDepthToM, parseRunMinutes, getPlanSummaryExport, formatDecoZoneStart, units, mGF, and DOM
 * Globals written: _contingencyRunning, contGasLose, contExtraBT, contExtraDepth, window._lastContingency
 */

let _contingencyRunning = false; // flag to suppress contingency side effects
let contGasLose = 'none'; // contingency: 'none' | '1' | '2' | 'both'
let contExtraBT = 0;      // contingency extra BT: 0 | 3 | 5 | 10
let contExtraDepth = 0;   // contingency went deeper: 0 | 3 | 5 (metres)
function buildContingencySlateText() {
  const cc = window._lastContingency;
  if (!cc || !cc.newRows) return null;
  const du = units === 'metric' ? 'm' : 'ft';
  const clean = t => (t || '').replace(/[📋⚠️🤿✓⚡🔵🔴🟢🚨⏱ℹ⇄↓↑]/g,'').replace(/\s*·\s*/g,' ').replace(/ppO₂/g,'ppO2').replace(/O₂/g,'O2').replace(/[—–]/g,'-').replace(/Bühlmann/g,'Buhlmann').replace(/\s+/g,' ').trim();
  const shortMix = m => {
    const s = clean(m);
    if (!s) return '-';
    if (/^\d+\/\d+$/.test(s)) return s;
    if (s === '100%' || /^100/i.test(s)) return '100%';
    if (/^air$/i.test(s)) return 'Air';
    const ean = s.match(/[Ee][Aa][Nn]\s*(\d+)/); if (ean) return ean[1] + '/00';
    const pct = s.match(/(\d+)\s*%/); if (pct) return pct[1] + '/00';
    return s;
  };
  // Parse rows from HTML string using a temporary DOM fragment
  const tmp = document.createElement('tbody');
  tmp.innerHTML = cc.newRows;
  const rows = tmp.querySelectorAll('tr[data-phase]');
  if (!rows.length) return null;
  const _ecNow = new Date();
  const _ecD = String(_ecNow.getDate()).padStart(2,'0'), _ecMo = String(_ecNow.getMonth()+1).padStart(2,'0');
  const _ecH = String(_ecNow.getHours()).padStart(2,'0'), _ecMi = String(_ecNow.getMinutes()).padStart(2,'0');
  const ecStamp = `${_ecNow.getFullYear()}/${_ecMo}/${_ecD} ${_ecH}:${_ecMi}`;
  const algoSel = document.getElementById('algorithmSelect')?.value || 'ZHLC_GF';
  const algoNames = { ZHLC_GF: 'Buhlmann GF', VPMB: 'VPM-B', VPMB_GFS: 'VPM-B+GFS' };
  const algoName = algoNames[algoSel] || algoSel;
  const algoLine = algoSel === 'ZHLC_GF'
    ? `${algoName} ${mGF.low}/${mGF.high}`
    : algoSel === 'VPMB'
      ? `${algoName} +${document.getElementById('conservatismSelect')?.value ?? '0'}`
      : `${algoName} GF Hi ${mGF.high}`;
  const botFracs = cc.scenarioBotFracs || getBottomGasFractions();
  if (!botFracs) return null;
  const botLabel = shortMix(getGasLabel(botFracs.fO2, botFracs.fHe));
  const gswRows = Array.from(rows).filter(tr => tr.dataset.phase === 'switch');
  const switchParts = gswRows.map(tr => {
    const txt = clean(tr.querySelector('td[colspan]')?.textContent || '');
    const gasM = txt.match(/^([^@]+)@/);
    const depM = txt.match(/@\s*([\d.]+)\s*(m|ft)/i);
    const gas = gasM ? shortMix(gasM[1]) : '';
    const dep = depM ? `${depM[1]}${depM[2] || du}` : '';
    return gas ? `${gas} @ ${dep}` : '';
  }).filter(Boolean);
  const mixLine = `${botLabel} (BTM) [EMRG: ${cc.label}]` + (switchParts.length ? ' | ' + switchParts.join(' | ') : '');
  const out = [];
  const cellText = (tr, label) => clean(tr.querySelector(`td[data-label="${label}"]`)?.textContent);
  rows.forEach(tr => {
    const ph = tr.dataset.phase;
    if (ph !== 'deco' && ph !== 'safety') return;
    const depRaw = (cellText(tr, 'Depth') || '').replace(/(m|ft)$/i, '');
    const dep = (depRaw + du).padStart(5);
    const run = (cellText(tr, 'Run') || '').padStart(5);
    const gas = shortMix(cellText(tr, 'Mix')).padEnd(6);
    const ppo2 = (cellText(tr, 'PPO2') || '').padStart(4);
    out.push(`${dep}  ${run}  ${gas} ${ppo2}`);
  });
  const _ecSum = getContingencySummaryExport();
  const ecSlateSum = {
    ..._ecSum,
    decozone: typeof compactExportDepth === 'function' ? compactExportDepth(_ecSum.decozone) : _ecSum.decozone,
    decoStop: typeof compactExportDepth === 'function' ? compactExportDepth(_ecSum.decoStop) : _ecSum.decoStop,
  };
  const summaryLines = formatPlanSummaryBlock(ecSlateSum, true);
  summaryLines[0] = summaryLines[0].replace(/^RT:/, 'TRT:');
  const bar = '========================';
  const lines = ['EMERGENCY SLATE', ecStamp, bar,
    `Algo: ${algoLine}`, `Mix: ${mixLine}`, '',
    'DEPTH  TIME   GAS    PPO2'];
  if (out.length) out.forEach(l => lines.push(l));
  else lines.push('  (no decompression stops)');
  lines.push(bar);
  lines.push(...summaryLines);
  return lines.join('\n');
}

function showContingencySlate() {
  if (!window._lastContingency?.newRows) { showToast('Run an emergency plan first', 'slate', true); return; }
  if (!getBottomGasFractions()) { notifyInvalidGasExport('slate'); return; }
  const text = buildContingencySlateText();
  if (!text) { showToast('Run an emergency plan first', 'slate', true); return; }
  document.getElementById('slateModalBody').textContent = text;
  document.getElementById('slateModal').style.display = 'flex';
}

/** Render against a scratch #decoTableBody so the live schedule table is never mutated. */
function withScratchDecoTableBody(fn, prefillHtml) {
  const mainTbody = document.getElementById('decoTableBody');
  if (!mainTbody) return typeof fn === 'function' ? fn() : undefined;
  const table = mainTbody.closest('table');
  const scratchTbody = document.createElement('tbody');
  scratchTbody.id = 'decoTableBody';
  if (prefillHtml) scratchTbody.innerHTML = prefillHtml;
  mainTbody.removeAttribute('id');
  const mainDisplay = mainTbody.style.display;
  mainTbody.style.display = 'none';
  if (table) table.appendChild(scratchTbody);
  try {
    return typeof fn === 'function' ? fn(scratchTbody) : undefined;
  } finally {
    scratchTbody.remove();
    mainTbody.id = 'decoTableBody';
    mainTbody.style.display = mainDisplay;
  }
}

/** Gas-switch / MOD warning when contingency ceiling is deeper than primary plan. */
function revalidateContingencyGasSwitchDepth(primaryPlan, contPlan) {
  if (!primaryPlan || !contPlan) return '';
  const pStop = primaryPlan.firstStopDepth;
  const cStop = contPlan.firstStopDepth;
  if (pStop == null || cStop == null || cStop <= pStop + 0.5) return '';
  if (typeof updateGasMODDisplays === 'function') updateGasMODDisplays();
  const parts = [];
  const travel = typeof getTravelGasInfo === 'function' ? getTravelGasInfo() : null;
  if (travel && travel.switchDepthM < cStop - 0.5) {
    const du = units === 'metric' ? 'm' : 'ft';
    const sw = units === 'metric' ? Math.round(travel.switchDepthM) : Math.round(travel.switchDepthM * 3.28084);
    const cs = units === 'metric' ? Math.round(cStop) : Math.round(cStop * 3.28084);
    parts.push(`Travel gas switch at ${sw}${du} is above contingency first stop (${cs}${du}) — verify gas switches.`);
  }
  if (typeof getConfiguredBailoutMixes === 'function') {
    const shallow = getConfiguredBailoutMixes().filter(m => m.modM < cStop - 0.5);
    if (shallow.length) {
      const du = units === 'metric' ? 'm' : 'ft';
      const cs = units === 'metric' ? Math.round(cStop) : Math.round(cStop * 3.28084);
      const names = shallow.map(m => m.label).join(', ');
      parts.push(`${names} MOD is below contingency first stop (${cs}${du}) — gas may be unavailable at depth.`);
    }
  }
  if (!parts.length) return '';
  return `<div class="alert warn" style="margin-top:8px;"><span>⚠</span><div><strong>GAS SWITCH REVIEW.</strong> ${parts.join(' ')}</div></div>`;
}

/** Bailout volumetric sufficiency for contingency profile (pass-2 dual-check). */
function buildContingencyBailoutGasAlert(contGasConsumed) {
  if (!contGasConsumed || typeof calculateGasRequirementsFromConsumed !== 'function') {
    return { html: '', warningBailoutContingency: false };
  }
  const mult = typeof getContingencySacMultiplier === 'function' ? getContingencySacMultiplier() : 1.5;
  const req = calculateGasRequirementsFromConsumed(contGasConsumed, { sacMultiplier: 1, bailoutFocus: true });
  if (!req.warningBailoutContingency) return { html: '', warningBailoutContingency: false };
  const volU = (typeof lspVolUnit === 'function') ? lspVolUnit() : (units === 'imperial' ? 'ft³' : 'L');
  const fmtVol = (typeof gpVolWithUnit === 'function')
    ? gpVolWithUnit
    : (l) => `${typeof gpVolDisp === 'function' ? gpVolDisp(l) : Math.round(l)}${volU}`;
  const lines = req.bailoutShortfalls.map((s) =>
    `${s.label}: need ${fmtVol(s.reqL)}, have ${fmtVol(s.availL)} (short ${fmtVol(s.shortL)})`
  ).join('; ');
  return {
    warningBailoutContingency: true,
    html: `<div class="alert dang" style="margin-top:8px;" data-warning="bailout-contingency"><span>⚠</span><div><strong>BAILOUT INSUFFICIENT FOR CONTINGENCY.</strong> ${lines} — calculated at ${mult}× stress SAC.</div></div>`,
  };
}

/** MOD / ppO₂ warning when contingency "went deeper" exceeds bottom-gas MOD at new depth. */
function buildContingencyModViolationAlert(extraDepthM) {
  if (!extraDepthM || extraDepthM <= 0) return '';
  if (typeof getBottomGasFractions !== 'function' || typeof calcGasMODm !== 'function' || typeof domDepthToM !== 'function') return '';
  const bot = getBottomGasFractions();
  if (!bot || !Number.isFinite(bot.fO2)) return '';
  const depthM = domDepthToM('decoDepth') + extraDepthM;
  const ppo2Limit = parseFloat(document.getElementById('ppo2Bottom')?.value) || 1.4;
  const modM = calcGasMODm(bot.fO2, ppo2Limit);
  if (depthM <= modM + 0.01) return '';
  const ppO2 = (altSurfaceP + depthM * BAR_PER_METRE) * bot.fO2;
  const du = units === 'metric' ? 'm' : 'ft';
  const depthDisp = units === 'metric' ? Math.round(depthM) : Math.round(depthM * 3.28084);
  const modDisp = units === 'metric' ? modM : Math.floor(modM * 3.28084);
  const gasLabel = typeof getGasLabel === 'function' ? getGasLabel(bot.fO2, bot.fHe) : 'bottom gas';
  return `<div class="alert dang" style="margin-top:8px;"><span>⚠</span><div><strong>BEYOND MOD.</strong> Contingency depth ${depthDisp}${du} exceeds ${gasLabel} MOD of ${modDisp}${du} at ${ppo2Limit.toFixed(1)} bar ppO₂ (actual ${ppO2.toFixed(2)} bar). CNS oxygen toxicity risk.</div></div>`;
}

/**
 * Run a contingency schedule without mutating the main deco table DOM.
 * modifyFn may adjust planner inputs (depth, BT, deco gases, bailout, circuit) — all are restored in finally.
 */
function runContingencyScenario(modifyFn) {
  const empty = {
    ok: false, newRows: '', lastRun: 0, decoTime: 0, lastRunFmt: null, decoTimeFmt: null,
    totalCNS: null, totalOTUc: null, decoZoneStart: 0, decozoneDisp: null, decoStop: null,
    tts: null, planSum: null, contSurfaceGF: null, scenarioDepth: null, scenarioBT: null,
    scenarioBotFracs: null, contLastPlan: null, contLastTissues: null, contLastGasConsumed: null,
    primaryFirstStopDepth: null,
  };
  const mainTbody = document.getElementById('decoTableBody');
  if (!mainTbody) return empty;

  const savedSummary = document.getElementById('decoSummary')?.innerHTML || '';
  const savedLastPlan = window._lastPlan;
  const primaryFirstStopDepth = savedLastPlan?.firstStopDepth ?? null;
  const origDepth = document.getElementById('decoDepth')?.value;
  const origBT = document.getElementById('decoBT')?.value;
  const origDgVals = {};
  for (const idx of getAllDecoGasIds()) {
    const el = document.getElementById(`dg${idx}Mix`);
    if (el) origDgVals[idx] = el.value;
  }
  const origBailout = document.getElementById('ccrBailoutToggle')?.value;
  const origCircuit = document.getElementById('circuitSelect')?.value;

  _contingencyRunning = true;
  let ok = false;
  let scenarioDepth, scenarioBT, scenarioBotFracs, newRows = '', lastRun, decoTime;
  let lastRunFmt, decoTimeFmt, totalCNS, totalOTUc, tts, decoStop, decozoneDisp;
  let decoZoneStart, contSurfaceGF, planSum, contLastPlan, contLastTissues, contLastGasConsumed;
  let error = null;
  try {
    withScratchDecoTableBody((scratchTbody) => {
      if (typeof modifyFn === 'function') modifyFn();
      if (contExtraDepth > 0 && typeof updateGasMODDisplays === 'function') updateGasMODDisplays();
      runDecoSchedule();

      const rows = scratchTbody.querySelectorAll('tr[data-phase]');
      if (!rows.length) return;

      ok = true;
      scenarioDepth = document.getElementById('decoDepth')?.value;
      scenarioBT = document.getElementById('decoBT')?.value;
      scenarioBotFracs = getBottomGasFractions();
      newRows = scratchTbody.innerHTML;
      lastRun = 0;
      decoTime = 0;
      rows.forEach(tr => {
        const run = parseRunMinutes(tr.querySelector('td[data-label="Run"]')?.textContent) || 0;
        if (run > lastRun) lastRun = run;
        if (tr.dataset.phase === 'deco' || tr.dataset.phase === 'safety') {
          const stopTxt = tr.querySelector('td[data-label="Stop"]')?.textContent || '';
          decoTime += parseRunMinutes(stopTxt) || 0;
        }
      });

      const totalsRow = scratchTbody.querySelector('tr[data-phase="totals"] td');
      planSum = getPlanSummaryExport(totalsRow);
      const lp = window._lastPlan || {};
      lastRunFmt = planSum.runTime !== '-' ? planSum.runTime : null;
      decoTimeFmt = planSum.decoTime !== '-' ? planSum.decoTime : null;
      totalCNS = planSum.cns !== '-' ? planSum.cns : null;
      totalOTUc = planSum.otu !== '-' ? planSum.otu : null;
      tts = planSum.tts;
      decoStop = planSum.decoStop;
      decozoneDisp = planSum.decozone;
      decoZoneStart = lp.decoZoneStart ?? 0;
      contSurfaceGF = lp.surfaceGF ?? null;
      contLastPlan = window._lastPlan ? JSON.parse(JSON.stringify(window._lastPlan)) : null;
      const tissueSrc = window._lastPlan?.finalTissues;
      contLastTissues = tissueSrc && tissueSrc.length
        ? tissueSrc.map(t => ({ pN2: t.pN2, pHe: t.pHe || 0, mv: t.mv }))
        : null;
      contLastGasConsumed = window._contingencyScratchGasConsumed
        ? Object.assign({}, window._contingencyScratchGasConsumed)
        : null;
    });
  } catch (e) {
    error = e.message;
  } finally {
    if (origBT != null) {
      const btEl = document.getElementById('decoBT');
      if (btEl) btEl.value = origBT;
    }
    if (origDepth != null) {
      const depthEl = document.getElementById('decoDepth');
      if (depthEl) depthEl.value = origDepth;
    }
    for (const [idx, val] of Object.entries(origDgVals)) {
      const el = document.getElementById(`dg${idx}Mix`);
      if (el) el.value = val;
    }
    if (origBailout != null) {
      const boEl = document.getElementById('ccrBailoutToggle');
      if (boEl) boEl.value = origBailout;
    }
    if (origCircuit != null) {
      const cEl = document.getElementById('circuitSelect');
      if (cEl) cEl.value = origCircuit;
    }
    const summEl = document.getElementById('decoSummary');
    if (summEl) summEl.innerHTML = savedSummary;
    window._lastPlan = savedLastPlan;
    _contingencyRunning = false;
    delete window._contingencyScratchGasConsumed;
  }

  if (!ok) return empty;
  return {
    ok, newRows, lastRun, decoTime: Math.round(decoTime), lastRunFmt, decoTimeFmt, totalCNS, totalOTUc,
    decoZoneStart, decozoneDisp, decoStop, tts, planSum, contSurfaceGF, scenarioDepth, scenarioBT, scenarioBotFracs,
    contLastPlan, contLastTissues, contLastGasConsumed, primaryFirstStopDepth, error,
  };
}

// Contingency state
// contingency state is declared at top of script

function buildContingencyButtons() {
  const btns = document.getElementById('gasLossButtons');
  if (!btns) { console.error('[Contingency] gasLossButtons not found'); return; }
  btns.innerHTML = '';
  contGasLose = 'none';

  const gases = [];
  for (const idx of getAllDecoGasIds()) {
    const el    = document.getElementById('dg' + idx + 'Mix');
    const label = el?.selectedOptions[0]?.text || '';
    console.log('[Contingency] dg'+idx+'Mix:', el?.value, 'label:', label);
    if (el && el.value !== 'none') {
      const gasName = label.replace(/\(.*?\)/g,'').trim() || ('Gas ' + idx);
      gases.push({ id: idx, name: gasName });
    }
  }
  console.log('[Contingency] gases found:', gases.length);
  // None button
  const noneBtn = document.createElement('button');
  noneBtn.id = 'contGas-none';
  noneBtn.textContent = 'None';
  noneBtn.className = 'cont-gas-btn';
  noneBtn.style.cssText = 'padding:8px 14px;background:rgba(0,200,255,0.1);color:var(--accent);border:1px solid var(--accent);border-radius:6px;cursor:pointer;font-family:JetBrains Mono,monospace;font-size:11px;font-weight:600;';
  noneBtn.onclick = () => selectContGas('none', gases);
  btns.appendChild(noneBtn);

  if (gases.length === 0) { selectContGas('none', gases); return; }

  gases.forEach(g => {
    const btn = document.createElement('button');
    btn.id = 'contGas-' + g.id;
    btn.textContent = 'Lose ' + g.name;
    btn.className = 'cont-gas-btn';
    btn.style.cssText = 'padding:8px 14px;background:rgba(255,71,87,0.08);color:var(--muted);border:1px solid var(--border);border-radius:6px;cursor:pointer;font-family:JetBrains Mono,monospace;font-size:11px;font-weight:600;';
    btn.onclick = () => selectContGas(String(g.id), gases);
    btns.appendChild(btn);
  });

  if (gases.length >= 2) {
    const btn = document.createElement('button');
    btn.id = 'contGas-both';
    btn.textContent = gases.length > 2 ? 'Lose All' : 'Lose Both';
    btn.className = 'cont-gas-btn';
    btn.style.cssText = 'padding:8px 14px;background:rgba(255,71,87,0.08);color:var(--muted);border:1px solid var(--border);border-radius:6px;cursor:pointer;font-family:JetBrains Mono,monospace;font-size:11px;font-weight:700;';
    btn.onclick = () => selectContGas('both', gases);
    btns.appendChild(btn);
  }

  selectContGas('none', gases);
  selectContBT(0);
  selectContDepth(0);
}

function selectContGas(val, gases) {
  contGasLose = val;
  document.querySelectorAll('.cont-gas-btn').forEach(b => {
    const isActive = b.id === 'contGas-' + val;
    const isRed = val !== 'none' && isActive;
    b.style.background  = isActive ? (isRed ? 'rgba(255,71,87,0.18)' : 'rgba(0,200,255,0.1)') : 'var(--surface)';
    b.style.color       = isActive ? (isRed ? 'var(--red)' : 'var(--accent)') : 'var(--text)';
    b.style.borderColor = isActive ? (isRed ? 'var(--red)' : 'var(--accent)') : 'var(--border-hi)';
    b.style.opacity     = '1';
  });
}

function selectContBT(mins) {
  contExtraBT = mins;
  [0,3,5,10].forEach(v => {
    const btn = document.getElementById('contBT' + v);
    if (!btn) return;
    const isActive = v === mins;
    btn.style.background  = isActive ? (v > 0 ? 'rgba(255,183,3,0.18)' : 'rgba(0,200,255,0.1)') : 'var(--surface)';
    btn.style.color       = isActive ? (v > 0 ? 'var(--yellow)' : 'var(--accent)') : 'var(--text)';
    btn.style.borderColor = isActive ? (v > 0 ? 'var(--yellow)' : 'var(--accent)') : 'var(--border-hi)';
    btn.style.opacity     = '1';
  });
}

function syncContDepthLabels() {
  [0, 3, 5].forEach(v => {
    const btn = document.getElementById('contDepth' + v);
    if (!btn) return;
    const disp = units === 'metric' ? v : Math.round(v * 3.28084);
    const du = units === 'metric' ? 'm' : 'ft';
    btn.textContent = '+' + disp + ' ' + du;
  });
}

/** @param {number} metres — extra depth in metres (3/5); imperial display is derived in syncContDepthLabels */
function selectContDepth(metres) {
  contExtraDepth = metres;
  syncContDepthLabels();
  [0,3,5].forEach(v => {
    const btn = document.getElementById('contDepth' + v);
    if (!btn) return;
    const isActive = v === metres;
    btn.style.background  = isActive ? (v > 0 ? 'rgba(255,71,87,0.18)' : 'rgba(0,200,255,0.1)') : 'var(--surface)';
    btn.style.color       = isActive ? (v > 0 ? 'var(--red)' : 'var(--accent)') : 'var(--text)';
    btn.style.borderColor = isActive ? (v > 0 ? 'var(--red)' : 'var(--accent)') : 'var(--border-hi)';
    btn.style.opacity     = '1';
  });
}

function calcContingency() {
  const resultEl = document.getElementById('contingencyResult');
  if (!resultEl) return;

  try {
  const gases = [];
  for (const idx of getAllDecoGasIds()) {
    const el = document.getElementById('dg' + idx + 'Mix');
    const label = el?.selectedOptions[0]?.text?.replace(/\(.*?\)/g,'').trim() || ('Gas ' + idx);
    if (el && el.value !== 'none') gases.push({ id: idx, name: label });
  }

  // Build scenario label
  const parts = [];
  if (contGasLose === 'both') parts.push('Lost ' + gases.map(g=>g.name).join(' & '));
  else if (contGasLose !== 'none') {
    const g = gases.find(g => String(g.id) === contGasLose);
    if (g) parts.push('Lost ' + g.name);
  }
  if (contExtraBT > 0) parts.push('+' + contExtraBT + ' min BT');
  if (contExtraDepth > 0) {
    const du2 = units === 'metric' ? 'm' : 'ft';
    const depthDisp = units === 'metric' ? contExtraDepth : Math.round(contExtraDepth * 3.28084);
    parts.push('+' + depthDisp + ' ' + du2 + ' depth');
  }
  const label = parts.length ? parts.join(' and ') : 'Standard plan (no changes)';

  const severity = (contGasLose !== 'none') ? 'dang' : (contExtraBT > 0 || contExtraDepth > 0) ? 'warn' : 'info';
  const icon     = (contGasLose !== 'none') ? '🚨' : (contExtraBT > 0 || contExtraDepth > 0) ? '⏱️' : 'ℹ️';
  const msg      = (contGasLose === 'both') ? 'Emergency ascent on bottom gas only. Abort dive immediately.' :
                   (contGasLose !== 'none') ? 'Ascend on remaining gas. Monitor ppO2 closely.' :
                   (contExtraBT > 0)        ? 'Carry extra gas reserve for this scenario.' :
                   (contExtraDepth > 0)     ? 'You went deeper — deco obligation increased.' :
                   'Showing standard plan.';

  const { ok, newRows, lastRun, decoTime, lastRunFmt, decoTimeFmt, totalCNS, totalOTUc, decoZoneStart, decozoneDisp, decoStop, tts, planSum, contSurfaceGF, scenarioDepth, scenarioBT, scenarioBotFracs, contLastPlan, contLastTissues, contLastGasConsumed, primaryFirstStopDepth } = runContingencyScenario(() => {
    if (contExtraBT > 0) {
      const btEl = document.getElementById('decoBT');
      if (btEl) btEl.value = parseFloat(btEl.value) + contExtraBT;
    }
    if (contExtraDepth > 0) {
      const depthEl = document.getElementById('decoDepth');
      const factor = units === 'metric' ? 1 : 3.28084;
      if (depthEl) depthEl.value = parseFloat(depthEl.value) + Math.round(contExtraDepth * factor);
    }
    for (const idx of getAllDecoGasIds()) {
      if (contGasLose === String(idx) || contGasLose === 'both') {
        const el = document.getElementById(`dg${idx}Mix`);
        if (el) el.value = 'none';
      }
    }
    if (contGasLose !== 'none' && isRebreatherCircuit(getCCRSettingsFromDOM().circuit)) {
      const boEl = document.getElementById('ccrBailoutToggle');
      if (boEl) boEl.value = 'on';
    }
  });

  if (!ok || !newRows) {
    resultEl.style.display = 'block';
    const exportActions = document.getElementById('contingencyExportActions');
    if (exportActions) exportActions.style.display = 'none';
    resultEl.innerHTML = `<div class="alert dang" style="margin:0;"><span>⚠️</span><div><strong>Contingency plan unavailable.</strong> Run Calculate on the main deco plan first, or adjust scenario inputs.</div></div>`;
    return;
  }

  resultEl.style.display = 'block';
  const exportActions = document.getElementById('contingencyExportActions');
  if (exportActions) exportActions.style.display = 'flex';
  const _emRunFmt  = lastRunFmt  || `${lastRun}'00"`;
  const _emDecoFmt = decoTimeFmt || `${decoTime}'00"`;
  const _emDepthM  = domDepthToM('decoDepth') + (contExtraDepth || 0);
  const _emBT      = parseFloat(document.getElementById('decoBT')?.value || '0') + (contExtraBT || 0);
  const _emPrT     = calcPrTBarMin(_emDepthM, _emBT).toFixed(1);
  const _emOTU     = totalOTUc || '—';
  const cnsColor   = totalCNS && parseFloat(totalCNS) >= 100 ? 'var(--red)' : totalCNS && parseFloat(totalCNS) >= 80 ? 'var(--orange)' : 'var(--text)';
  const prtColorEm = parseFloat(_emPrT) < 15 ? 'var(--green)' : parseFloat(_emPrT) < 25 ? 'var(--yellow)' : parseFloat(_emPrT) < 40 ? 'var(--orange)' : 'var(--red)';
  const _emHasDeco = (decoTimeFmt && decoTimeFmt !== '0\'00"') || decoTime > 0;
  const _emTts = tts || planSum?.tts || '—';
  const _emDecozone = decozoneDisp || planSum?.decozone || formatDecoZoneStart(decoZoneStart);
  const _emDecoStop = decoStop || planSum?.decoStop || '—';
  const emInfoRow = buildPlanInfoRowHtml({
    runTime: _emRunFmt,
    tts: _emTts,
    decoTime: _emDecoFmt,
    cns: totalCNS || '—',
    cnsColor,
    otu: _emOTU,
    prt: _emPrT,
    prtColor: prtColorEm,
    hasDeco: _emHasDeco,
    decozone: _emDecozone,
    decoStop: _emDecoStop,
    surfaceGF: contSurfaceGF,
  }, 'info');
  resultEl.innerHTML = `
    <div class="deco-plan-caption">
      <div class="alert ${severity}" style="margin:0;${contGasLose==='both'?'border-width:2px;':''}">
        <span>${icon}</span>
        <div><strong>${label}</strong> — Run ≈ <strong>${_emRunFmt}</strong> · Deco ≈ <strong>${_emDecoFmt}</strong>
        <div style="font-size:11px;margin-top:3px;opacity:0.85;">${msg}</div></div>
      </div>
    </div>
    <div class="schedule-wrap">
      <div class="deco-table-wrap">
        <table class="deco-table schedule-table table-view">
          <thead><tr><th class="phase-cell" aria-label="Phase"></th><th>Depth</th><th>Stop</th><th>Mix</th><th class="align-r">Run</th><th class="align-r">TTS</th><th class="align-r">PPO₂</th><th class="align-r">EAD</th></tr></thead>
          <tbody id="contingencyTableBody">${(newRows || '').replace(/data-phase="/g, 'data-phase="contingency-').replace(/<tr[^>]*data-phase="contingency-totals"[^>]*>[\s\S]*?<\/tr>/gi, '')}${emInfoRow}</tbody>
        </table>
      </div>
      ${typeof buildScheduleLegendHtml === 'function' ? buildScheduleLegendHtml() : ''}
    </div>
    <div id="decoAlertsEmergency" style="margin-top:8px;"></div>`;

  // Store for export
  window._lastContingency = { label, lastRun, decoTime, lastRunFmt, decoTimeFmt, totalCNS, totalOTU: _emOTU, totalPrT: _emPrT, decoZoneStart, decozoneDisp: _emDecozone, decoStop: _emDecoStop, tts: _emTts, newRows, severity, icon, msg, surfGF: contSurfaceGF != null ? Math.round(contSurfaceGF) + '%' : '-', scenarioDepth, scenarioBT, scenarioBotFracs, emAlertsHtml: '', contLastPlan, contLastTissues };

  // CNS / bailout / gas-switch alerts — emergency card only, NOT main decoAlerts
  const emAlerts = document.getElementById('decoAlertsEmergency');
  if (emAlerts) {
    const modAlert = buildContingencyModViolationAlert(contExtraDepth);
    const gasSwitchAlert = revalidateContingencyGasSwitchDepth(
      primaryFirstStopDepth != null ? { firstStopDepth: primaryFirstStopDepth } : window._lastPlan,
      contLastPlan,
    );
    const bailoutAlert = buildContingencyBailoutGasAlert(contLastGasConsumed);
    const cnsPctEm = totalCNS ? parseFloat(totalCNS) : 0;
    let cnsAlert = '';
    if (cnsPctEm >= 80) {
      cnsAlert = `<div class="alert" style="margin-top:8px;background:#ffff00;border-color:#cccc00;color:#111;font-weight:700;"><span>☢</span><div><strong>HIGH CNS%.</strong> Emergency CNS oxygen load ${cnsPctEm.toFixed(0)}% exceeds 80%. Extreme caution.</div></div>`;
    }
    emAlerts.innerHTML = modAlert + gasSwitchAlert + bailoutAlert.html + cnsAlert;
    window._lastContingency.emAlertsHtml = emAlerts.innerHTML;
    window._lastContingency.warningBailoutContingency = bailoutAlert.warningBailoutContingency;
  }
  if (typeof injectTtsCells === 'function') injectTtsCells('contingencyTableBody');
  if (typeof decorateContingencyTableForV3 === 'function') decorateContingencyTableForV3();
  scheduleDecoScheduleStackSync();
  } catch (e) {
    console.error('[Contingency]', e);
    resultEl.style.display = 'block';
    resultEl.innerHTML = `<div class="alert dang" style="margin:0;"><span>⚠</span><div><strong>Contingency calculation failed.</strong> ${escapeHtmlText(e.message || String(e))}</div></div>`;
  } finally {
    _contingencyRunning = false;
    window._scheduleWorkerBusy = false;
    delete window._contingencyScratchGasConsumed;
  }
}
// Redirected to unified exportTXT — kept for backward compat





