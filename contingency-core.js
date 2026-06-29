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
  const dateStr = _ecNow.toISOString().slice(0,10);
  const ecStamp = `${_ecNow.getFullYear()}/${_ecMo}/${_ecD} ${_ecH}:${_ecMi}`;
  const algoSel = document.getElementById('algorithmSelect')?.value || 'ZHLC_GF';
  const algoNames = { ZHLC_GF: 'Buhlmann GF', VPMB: 'VPM-B', VPMB_GFS: 'VPM-B/GFS' };
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
  rows.forEach(tr => {
    const ph = tr.dataset.phase;
    if (ph !== 'deco' && ph !== 'safety') return;
    const tds = tr.querySelectorAll('td');
    const depRaw = clean(tds[1]?.textContent).replace(/(m|ft)$/i,'');
    const dep = (depRaw + du).padStart(5);
    const run = clean(tds[4]?.textContent).padStart(5);
    const gas = shortMix(tds[3]?.textContent).padEnd(6);
    const ppo2 = clean(tds[6]?.textContent).padStart(4);
    out.push(`${dep}  ${run}  ${gas} ${ppo2}`);
  });
  const _ecToMMSS = s => {
    if (!s && s !== 0) return '-';
    if (typeof s === 'number') return `${s}'00"`;
    s = String(s).trim();
    const mm = s.match(/(\d+)'(\d+)"/); if (mm) return `${mm[1]}'${mm[2]}"`;
    const colon = s.match(/(\d+):(\d+)/); if (colon) return `${colon[1]}'${colon[2]}"`;
    const plain = s.replace(/[^\d]/g,''); return plain ? `${plain}'00"` : '-';
  };
  const tbt = _ecToMMSS(cc.lastRunFmt || cc.lastRun);
  const decoDisp = _ecToMMSS(cc.decoTimeFmt || cc.decoTime);
  const _ecSum = getContingencySummaryExport();
  const bar = '========================';
  const lines = ['EMERGENCY SLATE', ecStamp, bar,
    `Algo: ${algoLine}`, `Mix: ${mixLine}`, '',
    'DEPTH  TIME   GAS    PPO2'];
  if (out.length) out.forEach(l => lines.push(l));
  else lines.push('  (no decompression stops)');
  lines.push(bar);
  lines.push(`TRT: ${tbt} | TTS: ${_ecSum.tts} | DECO: ${decoDisp}`);
  lines.push(`CNS: ${_ecSum.cns} OTU: ${_ecSum.otu} PrT: ${_ecSum.prt} Decozone: ${_ecSum.decozone} First deco: ${_ecSum.decoStop}`);
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
function runContingencyScenario(modifyFn) {
  const savedBody    = document.getElementById('decoTableBody').innerHTML;
  const savedSummary = document.getElementById('decoSummary').innerHTML;
  const savedLastPlan = window._lastPlan;
  const origBailout = document.getElementById('ccrBailoutToggle')?.value;

  _contingencyRunning = true;
  let ok = false;
  let scenarioDepth, scenarioBT, scenarioBotFracs, newRows = '', lastRun, decoTime;
  let lastRunFmt, decoTimeFmt, totalCNS, totalOTUc, tts, decoStop, decozoneDisp;
  let decoZoneStart, contSurfaceGF, planSum, contLastPlan, contLastTissues;
  try {
    modifyFn();
    runDecoSchedule();

    const rows = document.querySelectorAll('#decoTableBody tr[data-phase]');
    if (!rows.length) {
      return {
        ok: false, newRows: '', lastRun: 0, decoTime: 0, lastRunFmt: null, decoTimeFmt: null,
        totalCNS: null, totalOTUc: null, decoZoneStart: 0, decozoneDisp: null, decoStop: null,
        tts: null, planSum: null, contSurfaceGF: null, scenarioDepth: null, scenarioBT: null,
        scenarioBotFracs: null,
      };
    }
    ok = true;
    scenarioDepth = document.getElementById('decoDepth')?.value;
    scenarioBT    = document.getElementById('decoBT')?.value;
    scenarioBotFracs = getBottomGasFractions();
    newRows = document.getElementById('decoTableBody').innerHTML;
    lastRun = 0; decoTime = 0;
    rows.forEach(tr => {
      const run = parseRunMinutes(tr.querySelector('td[data-label="Run"]')?.textContent) || 0;
      if (run > lastRun) lastRun = run;
      if (tr.dataset.phase === 'deco' || tr.dataset.phase === 'safety') {
        const stopTxt = tr.querySelector('td[data-label="Stop"]')?.textContent || '';
        decoTime += parseRunMinutes(stopTxt) || 0;
      }
    });

    const totalsRow = document.querySelector('#decoTableBody tr[data-phase="totals"] td');
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
    contLastTissues = (typeof lastTissues !== 'undefined' && lastTissues && lastTissues.length)
      ? lastTissues.map(t => ({ pN2: t.pN2, pHe: t.pHe || 0, mv: t.mv }))
      : null;
  } finally {
    _contingencyRunning = false;
    document.getElementById('decoTableBody').innerHTML = savedBody;
    document.getElementById('decoSummary').innerHTML   = savedSummary;
    window._lastPlan = savedLastPlan;
    if (origBailout != null) {
      const boEl = document.getElementById('ccrBailoutToggle');
      if (boEl) boEl.value = origBailout;
    }
  }

  return {
    ok, newRows, lastRun, decoTime: Math.round(decoTime), lastRunFmt, decoTimeFmt, totalCNS, totalOTUc,
    decoZoneStart, decozoneDisp, decoStop, tts, planSum, contSurfaceGF, scenarioDepth, scenarioBT, scenarioBotFracs,
    contLastPlan, contLastTissues,
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

  const gases = [];
  for (const idx of getAllDecoGasIds()) {
    const el = document.getElementById('dg' + idx + 'Mix');
    const label = el?.selectedOptions[0]?.text?.replace(/\(.*?\)/g,'').trim() || ('Gas ' + idx);
    if (el && el.value !== 'none') gases.push({ id: idx, name: label });
  }

  const origBT = document.getElementById('decoBT')?.value;
  const _origDgVals = {};
  for (const idx of getAllDecoGasIds()) {
    const el = document.getElementById(`dg${idx}Mix`);
    if (el) _origDgVals[idx] = el.value;
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

  const origDepth = document.getElementById('decoDepth')?.value;
  const origBailout = document.getElementById('ccrBailoutToggle')?.value;
  let ok, newRows, lastRun, decoTime, lastRunFmt, decoTimeFmt, totalCNS, totalOTUc, decoZoneStart, decozoneDisp, decoStop, tts, planSum, contSurfaceGF, scenarioDepth, scenarioBT, scenarioBotFracs, contLastPlan, contLastTissues;
  try {
    ({ ok, newRows, lastRun, decoTime, lastRunFmt, decoTimeFmt, totalCNS, totalOTUc, decoZoneStart, decozoneDisp, decoStop, tts, planSum, contSurfaceGF, scenarioDepth, scenarioBT, scenarioBotFracs, contLastPlan, contLastTissues } = runContingencyScenario(() => {
    if (contExtraBT > 0 && origBT)
      document.getElementById('decoBT').value = parseFloat(origBT) + contExtraBT;
    if (contExtraDepth > 0 && origDepth) {
      const factor = units === 'metric' ? 1 : 3.28084;
      document.getElementById('decoDepth').value = parseFloat(origDepth) + Math.round(contExtraDepth * factor);
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
  }));
  } finally {
    if (origBT) document.getElementById('decoBT').value = origBT;
    if (origDepth) document.getElementById('decoDepth').value = origDepth;
    for (const [idx, val] of Object.entries(_origDgVals)) {
      const el = document.getElementById(`dg${idx}Mix`);
      if (el) el.value = val;
    }
    if (origBailout != null) {
      const boEl = document.getElementById('ccrBailoutToggle');
      if (boEl) boEl.value = origBailout;
    }
  }

  if (!ok || !newRows) {
    resultEl.style.display = 'block';
    resultEl.innerHTML = `<div class="alert dang" style="margin:0;"><span>⚠️</span><div><strong>Contingency plan unavailable.</strong> Run Calculate on the main deco plan first, or adjust scenario inputs.</div></div>`;
    return;
  }

  resultEl.style.display = 'block';
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
    <div class="deco-table-wrap">
      <div class="deco-plan-caption">
        <div class="alert ${severity}" style="margin:0;${contGasLose==='both'?'border-width:2px;':''}">
          <span>${icon}</span>
          <div><strong>${label}</strong> — Run ≈ <strong>${_emRunFmt}</strong> · Deco ≈ <strong>${_emDecoFmt}</strong>
          <div style="font-size:11px;margin-top:3px;opacity:0.85;">${msg}</div></div>
        </div>
      </div>
      <table class="deco-table table-view" style="font-size:10px;">
        <thead><tr><th>Phase</th><th>Depth</th><th>Stop</th><th>Mix</th><th>Run</th><th>TTS</th><th>PPO2</th><th>EAD</th></tr></thead>
        <tbody id="contingencyTableBody">${(newRows || '').replace(/data-phase="/g, 'data-phase="contingency-').replace(/<tr[^>]*data-phase="contingency-totals"[^>]*>[\s\S]*?<\/tr>/gi, '')}${emInfoRow}</tbody>
      </table>
      <div class="deco-schedule-stack__actions">
        <div class="export-row">
          <button class="btn-export" onclick="copyDiveProfile('contingency')" title="Copy to clipboard"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg></button>
          <button class="btn-export" onclick="showContingencySlate()" title="Emergency slate (waterproof format)"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="7" y1="8" x2="17" y2="8"/><line x1="7" y1="12" x2="17" y2="12"/><line x1="7" y1="16" x2="13" y2="16"/></svg></button>
          <button class="btn-export" onclick="exportTXT('contingency')" title="Download .txt"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/></svg></button>
          <button class="btn-export" onclick="showContingencyPDFDialog()" title="Export PDF"><span style="display:inline-block;width:16px;height:16px;font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;letter-spacing:0px;line-height:16px;text-align:center;overflow:visible;white-space:nowrap;">PDF</span></button>
        </div>
      </div>
    </div>
    <div id="decoAlertsEmergency" style="margin-top:8px;"></div>`;

  // Store for export
  window._lastContingency = { label, lastRun, decoTime, lastRunFmt, decoTimeFmt, totalCNS, totalOTU: _emOTU, totalPrT: _emPrT, decoZoneStart, decozoneDisp: _emDecozone, decoStop: _emDecoStop, tts: _emTts, newRows, severity, icon, msg, surfGF: contSurfaceGF != null ? Math.round(contSurfaceGF) + '%' : '-', scenarioDepth, scenarioBT, scenarioBotFracs, emAlertsHtml: '', contLastPlan, contLastTissues };

  // CNS alert — goes into emergency card, NOT main decoAlerts
  const emAlerts = document.getElementById('decoAlertsEmergency');
  if (emAlerts) {
    const cnsPctEm = totalCNS ? parseFloat(totalCNS) : 0;
    if (cnsPctEm >= 80) {
      emAlerts.innerHTML = `<div class="alert" style="margin-top:8px;background:#ffff00;border-color:#cccc00;color:#111;font-weight:700;"><span>☢</span><div><strong>HIGH CNS%.</strong> Emergency CNS oxygen load ${cnsPctEm.toFixed(0)}% exceeds 80%. Extreme caution.</div></div>`;
    } else {
      emAlerts.innerHTML = '';
    }
    window._lastContingency.emAlertsHtml = emAlerts.innerHTML;
  }
  scheduleDecoScheduleStackSync();
}
// Redirected to unified exportTXT — kept for backward compat





  function drawGraphLegend(doc, y, ML, CW, checkY) {
    const legEl = document.getElementById('decoProfileLegend');
    const rows = legEl ? Array.from(legEl.querySelectorAll('tbody tr')) : [];
    if (!rows.length) return y;
    checkY(rows.length * 5 + 10);
    // Header
    doc.setFillColor(240,244,255); doc.rect(ML,y,CW,5.5,'F');
    doc.setFontSize(6.5); doc.setFont('DejaVuSans','bold'); doc.setTextColor(80,80,120);
    const cw=[8,80,30,24]; const cx=[ML,ML+8,ML+88,ML+118];
    ['#','Stop','Run','ppO2'].forEach((h,i)=>doc.text(h,cx[i]+(i>0?cw[i]/2:cw[0]/2),y+3.8,{align:i===0?'center':'center'}));
    doc.setTextColor(0,0,0); y+=5.5;
    rows.forEach((tr,ri)=>{
      const cells=Array.from(tr.querySelectorAll('td'));
      const num=cells[0]?.textContent.trim()||'';
      const stop=cells[1]?.textContent.trim().replace(/[^\x20-\x7E]/g,'').trim()||'';
      const run=cells[2]?.textContent.trim()||'';
      const ppo=cells[3]?.textContent.trim()||'';
      const ppoV=parseFloat(ppo)||0;
      const tc=ppoV>=1.6?[200,0,0]:ppoV>=1.4?[180,100,0]:[60,120,60];
      ri%2===0?doc.setFillColor(248,249,255):doc.setFillColor(255,255,255);
      doc.rect(ML,y,CW,5,'F');
      doc.setFontSize(6.5); doc.setFont('DejaVuSans','normal');
      doc.setTextColor(180,0,0); doc.text(num,cx[0]+cw[0]/2,y+3.5,{align:'center'});
      doc.setTextColor(60,60,60); doc.text(stop,cx[1]+2,y+3.5);
      doc.setTextColor(80,80,80); doc.text(run,cx[2]+cw[2],y+3.5,{align:'right'});
      doc.setTextColor(...tc); doc.text(ppo,cx[3]+cw[3],y+3.5,{align:'right'});
      doc.setTextColor(0,0,0); y+=5;
    });
    return y+4;
  }

// ── PDF canvas capture — scale to print resolution to prevent 100 MB output ──
// jsPDF addImage stores raw pixel data. A 3× DPR canvas on mobile produces
// 2100×900 px raw (7.5 MB/image). Two images = 50–100 MB PDFs.
// Fix: re-draw the source canvas onto a 150 DPI print-resolution canvas
// (max ~1240 px wide for A4) before calling toDataURL.
function _canvasToDataURLForPDF(srcCanvas, targetMM) {
  const PDF_DPI = 150; // sufficient for print; 72 DPI is screen
  const PDF_MM_PER_INCH = 25.4;
  const targetPx = Math.round(targetMM * PDF_DPI / PDF_MM_PER_INCH);
  const srcW = srcCanvas.width;
  const srcH = srcCanvas.height;
  const scale = Math.min(1, targetPx / srcW); // never upscale
  const outW = Math.round(srcW * scale);
  const outH = Math.round(srcH * scale);
  const tmp = document.createElement('canvas');
  tmp.width  = outW;
  tmp.height = outH;
  const ctx = tmp.getContext('2d');
  ctx.drawImage(srcCanvas, 0, 0, outW, outH);
  return { dataURL: tmp.toDataURL('image/png'), w: outW, h: outH };
}
let _pdfFontCache = null;
async function loadPDFFonts(doc) {
  if (_pdfFontCache) {
    doc.addFileToVFS('DejaVuSans.ttf',      _pdfFontCache.regular);
    doc.addFileToVFS('DejaVuSans-Bold.ttf', _pdfFontCache.bold);
    doc.addFont('DejaVuSans.ttf',      'DejaVuSans', 'normal');
    doc.addFont('DejaVuSans-Bold.ttf', 'DejaVuSans', 'bold');
    doc.setFont('DejaVuSans', 'normal');
    return true;
  }
  try {
    const [rResp, bResp] = await Promise.all([
      fetch('vendor/fonts/DejaVuSans.ttf'),
      fetch('vendor/fonts/DejaVuSans-Bold.ttf'),
    ]);
    if (!rResp.ok || !bResp.ok) throw new Error('Font fetch failed');
    const [rBuf, bBuf] = await Promise.all([rResp.arrayBuffer(), bResp.arrayBuffer()]);
    function toBase64(buf) {
      const bytes = new Uint8Array(buf);
      // Process in 8192-byte chunks to avoid btoa/stack limits on large TTFs
      const CHUNK = 8192;
      let bin = '';
      for (let i = 0; i < bytes.length; i += CHUNK) {
        bin += String.fromCharCode.apply(null, bytes.subarray(i, i + CHUNK));
      }
      return btoa(bin);
    }
    _pdfFontCache = { regular: toBase64(rBuf), bold: toBase64(bBuf) };
    doc.addFileToVFS('DejaVuSans.ttf',      _pdfFontCache.regular);
    doc.addFileToVFS('DejaVuSans-Bold.ttf', _pdfFontCache.bold);
    doc.addFont('DejaVuSans.ttf',      'DejaVuSans', 'normal');
    doc.addFont('DejaVuSans-Bold.ttf', 'DejaVuSans', 'bold');
    doc.setFont('DejaVuSans', 'normal');
    return true;
  } catch(e) {
    console.error('[LSP] DejaVu font load failed — Unicode symbols will not render in PDF. Check vendor/fonts/ assets.', e);
    return false;
  }
}
async function ensurePDFFontsForPDF(doc) {
  try {
    const ok = await loadPDFFonts(doc);
    if (!ok) {
      alert('PDF fonts could not be loaded. Check your network connection and try again.');
      return false;
    }
    return true;
  } catch (e) {
    console.error('[LSP] PDF font load failed:', e);
    alert('PDF fonts could not be loaded. Check your network connection and try again.');
    return false;
  }
}
function showContingencyPDFDialog() {
  const old = document.getElementById('contingencyPDFDialog');
  if (old) old.remove();

  const overlay = document.createElement('div');
  overlay.id = 'contingencyPDFDialog';
  overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:9999;display:flex;align-items:center;justify-content:center;';

  const box = document.createElement('div');
  box.style.cssText = "background:var(--surface,#1a1e2e);border:1px solid var(--border,#2a3050);border-radius:12px;padding:24px 28px;width:340px;max-width:92vw;font-family:'Outfit',sans-serif;box-shadow:0 8px 40px rgba(0,0,0,0.5);";

  const sections = [
    { key:'gas',     label:'Emergency Gas Consumption', checked:true  },
    { key:'slate',   label:'Emergency Ascent Schedule',  checked:true  },
    { key:'profile', label:'Dive Profile Graph',         checked:true  },
    { key:'gfCurve', label:'GF Gradient Factor Curve',   checked:false },
    { key:'tissue',  label:'Tissue Saturation',          checked:false },
    { key:'emSlate', label:'Emergency Slate',            checked:true  },
  ];

  const rows = sections.map(s => `
    <label style="display:flex;align-items:center;gap:10px;padding:7px 0;cursor:pointer;border-bottom:1px solid var(--border,#2a3050);">
      <input type="checkbox" id="emPdfOpt_${s.key}" ${s.checked?'checked':''} style="width:15px;height:15px;accent-color:#ff4040;cursor:pointer;">
      <span style="font-size:13px;color:var(--text,#e8eaf6);">${s.label}</span>
    </label>`).join('');

  box.innerHTML = `
    <div style="font-family:'Bebas Neue',sans-serif;font-size:18px;letter-spacing:2px;color:#ff4040;margin-bottom:16px;">[!] EMERGENCY PDF EXPORT</div>
    <div style="font-size:11px;color:var(--muted,#8890b0);margin-bottom:14px;letter-spacing:0.5px;">SELECT SECTIONS TO INCLUDE</div>
    <div style="margin-bottom:18px;">${rows}</div>
    <div style="display:flex;gap:10px;justify-content:flex-end;">
      <button onclick="document.getElementById('contingencyPDFDialog').remove()"
        style="padding:9px 18px;background:transparent;color:var(--muted,#8890b0);border:1px solid var(--border,#2a3050);border-radius:6px;cursor:pointer;font-family:'Outfit',sans-serif;font-size:13px;font-weight:600;">
        Cancel
      </button>
      <button onclick="runContingencyPdfExportFromDialog()"
        style="padding:9px 18px;background:#cc0000;color:#fff;border:none;border-radius:6px;cursor:pointer;font-family:'Outfit',sans-serif;font-size:13px;font-weight:700;letter-spacing:1px;">
        EXPORT PDF
      </button>
    </div>`;

  overlay.appendChild(box);
  overlay.addEventListener('click', e => { if(e.target===overlay) overlay.remove(); });
  document.body.appendChild(overlay);
}

function runContingencyPdfExportFromDialog() {
  const opts = {};
  ['gas', 'slate', 'profile', 'gfCurve', 'tissue', 'emSlate'].forEach(k => {
    opts[k] = !!document.getElementById('emPdfOpt_' + k)?.checked;
  });
  document.getElementById('contingencyPDFDialog')?.remove();
  exportContingencyPDF(opts).catch(function(e) {
    console.error('[Contingency PDF export]', e);
    alert('PDF export failed: ' + (e && e.message ? e.message : e));
  });
}

async function exportContingencyPDF(opts) {
  opts = opts || {};
  const _incGas     = opts.gas     !== false;
  const _incSlate   = opts.slate   !== false;
  const _incProfile = opts.profile !== false;
  const _incGFCurve = opts.gfCurve !== false;
  const _incTissue  = opts.tissue  !== false;
  const _incEmSlate = opts.emSlate !== false;

  if (!window.jspdf || !window.jspdf.jsPDF) { alert('PDF library not loaded.'); return; }
  const { jsPDF } = window.jspdf;
  const c = window._lastContingency;
  if (!c) return;

  const doc = new jsPDF({ unit:'mm', format:'a4', orientation:'portrait' });
  if (!(await ensurePDFFontsForPDF(doc))) return;
  const now = new Date();
  const dateStr = now.toLocaleDateString('en-GB',{day:'2-digit',month:'short',year:'numeric'});
  const timeStr = now.toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit'});
  const isoDate = now.toISOString().split('T')[0];
  const du    = units === 'imperial' ? 'ft' : 'm';
  const depth = document.getElementById('decoDepth')?.value || '\u2014';
  const bt    = document.getElementById('decoBT')?.value    || '\u2014';
  const scenarioName = (c.label||'Emergency').replace(/[^a-zA-Z0-9_\- ]/g,'').replace(/\s+/g,'_').substring(0,30);
  const fileName = `LSP_${getExportCircuitTag()}_${isoDate}_Emergency_${depth}${du}_${bt}min_${scenarioName}.pdf`;

  const PW=210, PH=297, ML=14, MR=14, MT=10, MB=10, CW=182;
  let y=MT;

  function cleanPDF(s){
    if(!s) return '';
    s = s.replace(/[\u2080-\u2089]/g, c => String.fromCharCode(c.charCodeAt(0)-0x2050));
    s = s.replace(/[\u00B2\u00B3\u00B9]/g, c => ({'\u00B2':'2','\u00B3':'3','\u00B9':'1'}[c]||c));
    s = s.replace(/\u00B7|\u2022|\u2027/g,'*').replace(/\u2014/g,'--').replace(/\u2013/g,'-').replace(/\u2018|\u2019/g,"'").replace(/\u201C|\u201D/g,'"');
    // Strip decorative emoji/icon blocks but preserve \u2713\u2717\u26a0 and arrows \u2191\u2193\u2190\u2192
    s = s.replace(/[\u2600-\u269F\u26A1-\u26FF\u2700-\u2712\u2714-\u2716\u2718-\u27FF\u2B00-\u2BFF\u2300-\u23FF\uFE0F]/g,'');
    s = s.replace(/[^\x20-\x7E\xA0-\u024F\u2190-\u2193\u2713\u2717\u26A0]/g,'');
    return s.replace(/^\s*[!&*#^~]+\s*/,'').trim();
  }
  function checkY(n) { if(y+n>PH-MB){ drawFooter(); doc.addPage(); y=MT; drawHeader(); } }
  function drawHeader() {
    doc.setFillColor(180,30,30); doc.rect(0,0,PW,8,'F');
    doc.setFontSize(8); doc.setFont('DejaVuSans','bold'); doc.setTextColor(255,255,255);
    doc.text('⚠ EMERGENCY PLAN', ML, 5.5);
    doc.setFont('DejaVuSans','normal'); doc.setFontSize(8);
    // Truncate label so it fits the center zone (max ~70mm)
    const _hdrLabel = `${bt}min @ ${depth}${du} | ${c.label}`;
    const _hdrMax = 70;
    const _hdrTxt = doc.getTextWidth(_hdrLabel) > _hdrMax
      ? doc.splitTextToSize(_hdrLabel, _hdrMax)[0] + '…'
      : _hdrLabel;
    doc.text(_hdrTxt, PW/2, 5.5, {align:'center'});
    doc.setFontSize(8);
    doc.text(`${dateStr} ${timeStr}`, PW-MR, 5.5, {align:'right'});
    doc.setTextColor(0,0,0); y=MT;
  }
  function drawFooter() {
    doc.setFillColor(255,248,248); doc.rect(0,PH-6,PW,6,'F');
    doc.setFontSize(7); doc.setTextColor(100,100,120); doc.setFont('DejaVuSans','normal');
    doc.text('Planning Aid Only — Not a substitute for training, certification, or a dive computer · @threecats_lsp', ML, PH-2);
    doc.text(`${dateStr} ${timeStr}`, PW-MR, PH-2, {align:'right'});
    doc.setTextColor(0,0,0);
  }
  function sectionTitle(title, sub) {
    checkY(sub ? 14 : 12);
    doc.setFillColor(255,240,240); doc.rect(ML-2,y,CW+4,sub?9:7,'F');
    doc.setDrawColor(180,30,30); doc.setLineWidth(0.8); doc.line(ML-2,y,ML-2,y+(sub?9:7));
    doc.setFontSize(8); doc.setFont('DejaVuSans','bold'); doc.setTextColor(180,30,30);
    doc.text(cleanPDF(title), ML+1, y+4.8);
    if(sub){
      const subClean = cleanPDF(sub);
      doc.setFont('DejaVuSans','normal'); doc.setFontSize(7); doc.setTextColor(120,60,60);
      doc.text(subClean, ML+1, y+8.2);
    }
    doc.setTextColor(0,0,0); doc.setDrawColor(0,0,0); doc.setLineWidth(0.2); y+=(sub?11:9);
  }

  drawHeader();

  // ── Scenario info box ───────────────────────────────────────────────────
  doc.setFillColor(255,240,240); doc.setDrawColor(220,150,150);
  doc.roundedRect(ML,y,CW,16,2,2,'FD');
  doc.setFontSize(10); doc.setFont('DejaVuSans','bold'); doc.setTextColor(180,30,30);
  doc.text('⚠ ' + cleanPDF(c.label), ML+3, y+6);
  doc.setFontSize(8); doc.setFont('DejaVuSans','normal'); doc.setTextColor(100,0,0);
  doc.text(`Run: ${c.lastRunFmt||c.lastRun+"'00\""} | TTS: ${c.tts||'--'} | Deco: ${c.decoTimeFmt||c.decoTime+"'00\""} | CNS: ${c.totalCNS||'--'} | OTU: ${c.totalOTU||'--'} | PrT: ${c.totalPrT||'--'} | Decozone: ${c.decozoneDisp||formatDecoZoneStart(c.decoZoneStart)} | First deco: ${c.decoStop||'--'}`, ML+3, y+10.5);
  doc.setTextColor(150,0,0); doc.text(cleanPDF(c.msg||''), ML+3, y+14.5);
  doc.setTextColor(0,0,0); y+=19;

  // ── SECTION: Emergency Gas Consumption ──────────────────────────────────
  if (_incGas) {
    const emGasEl = document.getElementById('emergencyGasConsumption');
    const emGasRows = emGasEl ? Array.from(emGasEl.querySelectorAll('tbody tr')) : [];
    if (emGasRows.length) {
      checkY(10);
      sectionTitle('EMERGENCY GAS CONSUMPTION','Gas required vs available per cylinder');
      // Columns: GAS | REQUIRED | AVAILABLE | STATUS
      const egcW=[30,38,38,76]; const egcX=[ML,ML+30,ML+68,ML+106];
      doc.setFillColor(180,30,30); doc.rect(ML,y,CW,6,'F');
      doc.setFontSize(7); doc.setFont('DejaVuSans','bold'); doc.setTextColor(255,255,255);
      ['GAS','REQUIRED','AVAILABLE','STATUS'].forEach((h,i)=>doc.text(h,egcX[i]+egcW[i]/2,y+4,{align:'center'}));
      doc.setTextColor(0,0,0); y+=6;
      emGasRows.forEach((tr,ri)=>{
        const cells=Array.from(tr.querySelectorAll('td'));
        const cv=cells.map(td=>cleanPDF(td.textContent.trim()));
        // Detect insufficient from cell color or text
        const statusTxt=cv[3]||'';
        const isShort=statusTxt.includes('short')||statusTxt.includes('\u2717');
        ri%2===0?doc.setFillColor(255,250,250):doc.setFillColor(255,255,255);
        doc.rect(ML,y,CW,5.5,'F');
        doc.setFontSize(7); doc.setFont('DejaVuSans','bold');
        doc.setTextColor(isShort?180:40,isShort?0:40,isShort?0:40);
        doc.text(cv[0]||'',egcX[0]+2,y+3.8);
        doc.setFont('DejaVuSans','normal');
        doc.setTextColor(80,80,80); doc.text(cv[1]||'',egcX[1]+egcW[1]/2,y+3.8,{align:'center'});
        doc.setTextColor(80,80,80); doc.text(cv[2]||'',egcX[2]+egcW[2]/2,y+3.8,{align:'center'});
        // Status — colour-code
        const stc=isShort?[180,0,0]:[0,130,60];
        doc.setFont('DejaVuSans','bold'); doc.setTextColor(...stc);
        doc.text(statusTxt,egcX[3]+egcW[3]/2,y+3.8,{align:'center'});
        doc.setTextColor(0,0,0); y+=5.5;
      });
      y+=4;
    }
  }

  // ── SECTION: Emergency Ascent Schedule ──────────────────────────────────
  if (_incSlate) {
    sectionTitle('EMERGENCY ASCENT SCHEDULE', cleanPDF(c.label));
    const _emTbl = _pdfDecoTableLayout(ML, CW);
    const { tblMl, tblCw } = _emTbl;
    _pdfDrawDecoTableHeader(doc, y, _emTbl, [180, 30, 30]);
    y += 6;

    const emSumPdf = getContingencySummaryExport();
    document.querySelectorAll('#contingencyResult .deco-table tbody tr').forEach((tr,rowI)=>{
      const phase=tr.dataset.phase;
      const tds=Array.from(tr.querySelectorAll('td'));
      const cv=tds.map(td=>cleanPDF(td.textContent.trim()));
      checkY(5.5);
      if(phase==='switch'){
        _pdfDrawSwitchRow(doc, y, _emTbl, tr, cleanPDF);
        y+=5; return;
      }
      if(phase==='totals'){
        const t = `Run: ${emSumPdf.runTime}  TTS: ${emSumPdf.tts}  Deco: ${emSumPdf.decoTime}  CNS: ${emSumPdf.cns}  OTU: ${emSumPdf.otu}  PrT: ${emSumPdf.prt}  Surf GF: ${emSumPdf.surfGF||'-'}  Decozone: ${emSumPdf.decozone}  First deco: ${emSumPdf.decoStop}`;
        const tLines = doc.splitTextToSize(cleanPDF(t), tblCw - 4);
        const tH = 4.2 * tLines.length + 1.5;
        checkY(tH);
        doc.setFillColor(255,240,240); doc.rect(tblMl,y,tblCw,tH,'F');
        doc.setFontSize(7); doc.setFont('DejaVuSans','bold'); doc.setTextColor(150,0,0);
        tLines.forEach((line, li) => doc.text(line, tblMl+2, y + 3.8 + li * 4.2));
        doc.setTextColor(0,0,0); y+=tH; return;
      }
      const isDeco=phase==='deco', isAsc=phase==='ascent', isBtm=phase==='bottom', isSafe=phase==='safety', isDes=phase==='descent';
      const saE=tr.getAttribute('style')||'';
      const hiE100=tr.hasAttribute('data-cnshi')&&(saE.includes('#ffff00')||(saE.includes('255,255,0')&&!saE.includes('0.25')));
      const hiE80=tr.hasAttribute('data-cnshi')&&(saE.includes('rgba(255,255,0')||saE.includes('255,255,0,0.25'));
      if(hiE100) doc.setFillColor(255,255,0);
      else if(hiE80) doc.setFillColor(255,252,180);
      else if(rowI%2===0) doc.setFillColor(255,250,250);
      else doc.setFillColor(255,255,255);
      doc.rect(tblMl,y,tblCw,5,'F');
      const txC=(hiE100||hiE80)?[150,0,0]:isDeco?[180,0,0]:isAsc?[30,130,60]:isBtm?[0,60,160]:isSafe?[20,140,50]:[160,50,50];
      const icon=isDeco?'Stp':isAsc?'Asc':isBtm?'Lvl':isSafe?'Stp':isDes?'Des':'---';
      doc.setFontSize(7); doc.setFont('DejaVuSans','normal');
      doc.setTextColor(...txC); _pdfDrawDecoPhaseLabel(doc, y, _emTbl, icon);
      _pdfDrawDecoTableCells(doc, y, _emTbl, cv.slice(1, 8), txC);
      doc.setTextColor(0,0,0); y+=5;
    });
    y+=3;

    // Legend
    checkY(7); doc.setFontSize(7); doc.setFont('DejaVuSans','normal');
    const leg=['Des = Descent','Lvl = Bottom','Asc = Ascent','Stp = Deco/Safety Stop','>> = Gas Switch'];
    const lc=[[160,50,50],[0,100,200],[30,130,60],[180,0,0],[100,0,150]];
    let lx=tblMl; leg.forEach((l,i)=>{doc.setTextColor(...lc[i]);doc.text(l,lx,y+3.5);lx+=doc.getTextWidth(l)+5;});
    doc.setTextColor(0,0,0); y+=8;

    // HIGH CNS% alert
    const _emCNSpct = c.totalCNS ? parseFloat(c.totalCNS) : 0;
    if (_emCNSpct >= 80) {
      checkY(10);
      doc.setFillColor(255,255,0); doc.setDrawColor(180,180,0);
      const _cnsMsg = `HIGH CNS%. Emergency CNS oxygen load ${_emCNSpct.toFixed(0)}% exceeds 80%. Extreme caution.`;
      const _cnsLines = doc.splitTextToSize(_cnsMsg, CW-4);
      const _cnsH = 5.5*_cnsLines.length+2;
      doc.roundedRect(ML,y,CW,_cnsH,1.5,1.5,'FD');
      doc.setFontSize(7.5); doc.setFont('DejaVuSans','bold'); doc.setTextColor(17,17,17);
      doc.text(_cnsLines,ML+2,y+4);
      doc.setTextColor(0,0,0); y+=_cnsH+4;
    }
  }

  // ── SECTION: Dive Profile Graph ─────────────────────────────────────────
  if (_incProfile) {
    const saved = document.getElementById('decoTableBody').innerHTML;
    try {
      document.getElementById('decoTableBody').innerHTML = c.newRows;
      _drawForPDF(() => drawDecoProfile());
      const pc = document.getElementById('decoProfileCanvas');
      if (pc) {
        doc.addPage(); drawHeader();
        sectionTitle('EMERGENCY DIVE PROFILE GRAPH', `${depth}${du} / ${bt}min / ${cleanPDF(c.label)}`);
        const _pcCapture = _canvasToDataURLForPDF(pc, CW);
        const imgH = CW * pc.height / pc.width;
        doc.addImage(_pcCapture.dataURL,'PNG',ML,y,CW,imgH);
        y += imgH+4;
        y = drawGraphLegend(doc, y, ML, CW, checkY);
      }
    } catch(e) { console.warn('Emergency graph failed',e); }
    finally {
      document.getElementById('decoTableBody').innerHTML = saved;
      drawDecoProfile();
    }
  }

  // ── SECTION: GF Gradient Factor Curve ───────────────────────────────────
  const isVPMem = (document.getElementById('algorithmSelect')?.value||'ZHLC_GF') !== 'ZHLC_GF';
  if (_incGFCurve && !isVPMem) {
    _drawForPDF(() => drawGFCurve());
    const gc2=document.getElementById('gfCurveCanvas');
    if(gc2){
      doc.addPage(); drawHeader();
      sectionTitle('GRADIENT FACTOR CURVE',`GF Low ${mGF.low}%  GF High ${mGF.high}%`);
      const _gc2Capture=_canvasToDataURLForPDF(gc2,CW); const gd2=_gc2Capture.dataURL; const gh2=CW*gc2.height/gc2.width;
      doc.addImage(gd2,'PNG',ML,y,CW,gh2); y+=gh2+4;
      const gfLegEl2=document.getElementById('gfCurveLegend');
      const gfRows2=gfLegEl2?Array.from(gfLegEl2.querySelectorAll('tbody tr')):[];
      if(gfRows2.length){
        checkY(gfRows2.length*5+10);
        doc.setFillColor(240,244,255); doc.rect(ML,y,CW,5.5,'F');
        doc.setFontSize(6.5); doc.setFont('DejaVuSans','bold'); doc.setTextColor(80,80,120);
        const gcw2=[8,80,30,24]; const gcx2=[ML,ML+8,ML+88,ML+118];
        ['#','Stop','Run','ppO2'].forEach((h,i)=>doc.text(h,gcx2[i]+gcw2[i]/2,y+3.8,{align:'center'}));
        doc.setTextColor(0,0,0); y+=5.5;
        gfRows2.forEach((tr,ri)=>{
          const cells=Array.from(tr.querySelectorAll('td'));
          const num=cells[0]?.textContent.trim()||'';
          const stop=cells[1]?.textContent.trim().replace(/[^ -~]/g,'').trim()||'';
          const run=cells[2]?.textContent.trim()||'';
          const ppo=cells[3]?.textContent.trim()||'';
          const ppoV=parseFloat(ppo)||0;
          const tc=ppoV>=1.6?[200,0,0]:ppoV>=1.4?[180,100,0]:[60,120,60];
          ri%2===0?doc.setFillColor(248,249,255):doc.setFillColor(255,255,255);
          doc.rect(ML,y,CW,5,'F');
          doc.setFontSize(6.5); doc.setFont('DejaVuSans','normal');
          doc.setTextColor(180,0,0); doc.text(num,gcx2[0]+gcw2[0]/2,y+3.5,{align:'center'});
          doc.setTextColor(60,60,60); doc.text(stop,gcx2[1]+2,y+3.5);
          doc.setTextColor(80,80,80); doc.text(run,gcx2[2]+gcw2[2],y+3.5,{align:'right'});
          doc.setTextColor(...tc); doc.text(ppo,gcx2[3]+gcw2[3],y+3.5,{align:'right'});
          doc.setTextColor(0,0,0); y+=5;
        });
        y+=4;
      }
    }
  }

  const emTissues = c.contLastTissues || (typeof lastTissues !== 'undefined' ? lastTissues : null);
  const emPlan = c.contLastPlan || (typeof _lastPlan !== 'undefined' ? _lastPlan : null);

  // ── SECTION: Tissue Saturation ───────────────────────────────────────────
  if (_incTissue && !isVPMem && emTissues && emTissues.length) {
    doc.addPage(); drawHeader();
    sectionTitle('TISSUE SATURATION','Buhlmann ZH-L16C \u2014 loading at end of dive');
    const gfFem=mGF.high/100;

    // Surface Snapshot: 16 compartment bars
    checkY(8);
    doc.setFontSize(7); doc.setFont('DejaVuSans','bold'); doc.setTextColor(180,30,30);
    doc.text('SURFACE SNAPSHOT', ML, y+4.8); y+=7;
    emTissues.forEach((t0lp,i)=>{
      const pN2lp=t0lp.pN2; const pHelp=t0lp.pHe||0; const pTotlp=pN2lp+pHelp;
      checkY(7);
      const [ht,a_n,b_n]=ZHL16C[i];
      let a=a_n,b=b_n;
      if(pHelp>0&&pTotlp>0){a=(pN2lp*a_n+pHelp*ZHL16C_HE_AB[i][0])/pTotlp;b=(pN2lp*b_n+pHelp*ZHL16C_HE_AB[i][1])/pTotlp;}
      const mv = gfAdjustedMValue(a, b, altSurfaceP, gfFem);
      const pct=Math.min(100,Math.round((pTotlp/mv)*100));
      const cr=pct>=100?[220,0,0]:pct>=85?[200,80,0]:pct>=70?[180,150,0]:[20,160,60];
      doc.setFontSize(6.5); doc.setFont('DejaVuSans','normal'); doc.setTextColor(100,100,120);
      doc.text(`${i+1}`,ML+3,y+4,{align:'center'});
      doc.text(`${ht}min`,ML+14,y+4);
      const barX=ML+30,barW=CW-55,barH=5;
      doc.setFillColor(230,232,240); doc.roundedRect(barX,y+0.5,barW,barH,1,1,'F');
      doc.setFillColor(...cr); doc.roundedRect(barX,y+0.5,barW*pct/100,barH,1,1,'F');
      doc.setFontSize(6.5); doc.setTextColor(...cr); doc.setFont('DejaVuSans','bold');
      doc.text(`${pct}%`,ML+CW-3,y+4,{align:'right'});
      doc.setTextColor(0,0,0); y+=6.5;
    });
    y+=4;

    // Compartment Detail table
    const ttbEm=document.getElementById('tissueTableBody');
    if(ttbEm&&ttbEm.rows.length===0&&emTissues) updateTissueViz(emTissues,mGF.high);
    if(ttbEm&&ttbEm.rows.length){
      doc.addPage(); drawHeader();
      sectionTitle('COMPARTMENT DETAIL','Buhlmann ZH-L16C - End of dive N2 loading');
      const th3=['#','Half-time (min)','N2 Load (bar)','M-value (bar)','Saturation %','Status'];
      const tw3=[8,30,28,28,28,30]; const tx3=[ML]; tw3.forEach((w,i)=>{if(i<tw3.length-1)tx3.push(tx3[i]+tw3[i]);});
      doc.setFillColor(180,30,30);doc.rect(ML,y,CW,6,'F');
      doc.setFontSize(7);doc.setFont('DejaVuSans','bold');doc.setTextColor(255,255,255);
      th3.forEach((h,i)=>doc.text(h,tx3[i]+tw3[i]/2,y+4,{align:'center'}));
      doc.setTextColor(0,0,0);y+=6;
      Array.from(ttbEm.rows).forEach((tr,ri)=>{
        checkY(5);const cells=Array.from(tr.cells).map(td=>td.textContent.trim());
        const pct=parseFloat(cells[4])||0;
        const cr=pct>=100?[200,0,0]:pct>=85?[180,80,0]:pct>=70?[150,120,0]:[20,140,50];
        ri%2===0?doc.setFillColor(255,250,250):doc.setFillColor(255,255,255);
        doc.rect(ML,y,CW,5,'F');
        doc.setFontSize(7);doc.setFont('DejaVuSans','normal');doc.setTextColor(...cr);
        cells.forEach((v,i)=>doc.text(cleanPDF(v),tx3[i]+tw3[i]/2,y+3.5,{align:'center'}));
        doc.setTextColor(0,0,0);y+=5;
      });
      y+=4;
    }

    // Per-Stop Ascent Profile (grid)
    if(emPlan && emPlan.steps && emPlan.steps.some(s=>s._tissues)){
      doc.addPage(); drawHeader();
      sectionTitle('PER-STOP ASCENT PROFILE','Compartment loading at each deco stop');
      const stopSteps=emPlan.steps.filter(s=>s._tissues&&(s.phase==='deco'||s.phase==='safety'||s.phase==='ascent'));
      const COLS=4; const cellW=CW/COLS; const cellH=20;
      stopSteps.forEach((step,si)=>{
        if(si%COLS===0){ checkY(cellH+6); }
        const cx2=ML+(si%COLS)*cellW;
        const cy2=y;
        const depLbl=units==='imperial'?`${Math.round(step.depth*3.28084)}ft`:`${Math.round(step.depth)}m`;
        doc.setFontSize(6); doc.setFont('DejaVuSans','bold'); doc.setTextColor(180,30,30);
        doc.text(`${depLbl} ${step.phase==='safety'?'Safety':''} ${step.run?step.run+"'":""}`.trim(),cx2+1,cy2+4);
        const tissues=step._tissues;
        const bW=(cellW-4)/16; const bMaxH=cellH-8;
        tissues.forEach((t,ti)=>{
          const pT=Math.min(1,(t.pN2+(t.pHe||0))/(t.mv||1));
          const bH=Math.max(0.5,bMaxH*pT);
          const tc2=pT>=1?[220,0,0]:pT>=0.85?[200,80,0]:pT>=0.7?[180,150,0]:[20,160,60];
          doc.setFillColor(...tc2);
          doc.rect(cx2+2+ti*bW, cy2+cellH-bH-2, bW*0.75, bH, 'F');
        });
        if(si%COLS===COLS-1||si===stopSteps.length-1){ y+=cellH+2; }
      });
      y+=4;
    }
  }

  // ── SECTION: Emergency Slate ─────────────────────────────────────────────
  if (_incEmSlate) {
    const emAlertHtml = c.emAlertsHtml || document.getElementById('decoAlertsEmergency')?.innerHTML || '';
    const emAlertText = emAlertHtml.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
    if (emAlertText) {
      checkY(10);
      doc.setFillColor(255, 255, 0); doc.setDrawColor(180, 180, 0);
      const _alertLines = doc.splitTextToSize(cleanPDF(emAlertText), CW - 4);
      const _alertH = 5.5 * _alertLines.length + 2;
      doc.roundedRect(ML, y, CW, _alertH, 1.5, 1.5, 'FD');
      doc.setFontSize(7.5); doc.setFont('DejaVuSans', 'bold'); doc.setTextColor(17, 17, 17);
      doc.text(_alertLines, ML + 2, y + 4);
      doc.setTextColor(0, 0, 0); y += _alertH + 4;
    }
    const slateText = buildContingencySlateText();
    if (slateText) {
      checkY(10);
      doc.setFillColor(30,30,60); doc.rect(ML,y,CW,6,'F');
      doc.setFontSize(7); doc.setFont('DejaVuSans','bold'); doc.setTextColor(255,255,255);
      doc.text('EMERGENCY SLATE', ML+2, y+4);
      doc.setTextColor(0,0,0); y+=8;
      doc.setFont('DejaVuSans','normal'); doc.setFontSize(7);
      // Skip first 2 lines (title + timestamp) — already shown in the section banner above
      const slateLines = slateText.split('\n').slice(2);
      slateLines.forEach(line => {
        checkY(5);
        // Render separator bars as thin lines, stop rows in monospace style
        if (/^=+$/.test(line.trim())) {
          doc.setDrawColor(180,180,200); doc.setLineWidth(0.3);
          doc.line(ML, y+1, ML+CW, y+1);
          doc.setLineWidth(0.2); y+=3.5;
        } else if (!line.trim()) {
          y+=2.5;
        } else {
          doc.text(cleanPDF(line), ML, y); y+=4.5;
        }
      });
      y+=4;
    }
  }

  const totalPages=doc.getNumberOfPages();
  for(let p=1;p<=totalPages;p++){ doc.setPage(p); drawFooter(); }
  doc.save(fileName);
  showExportToast();
}
