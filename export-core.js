/**
 * Unified export engine — copy, text export, clipboard, slate, and all PDF variants.
 * Loaded by index.html before main inline script.
 * Globals read: units, mGF, altitudeM, altAcclimatized, window._lastPlan, window._lastContingency,
 *   window._lastGasPlan, getContingencySummaryExport, validateDomDecoGases,
 *   waterDensityDisplayLabel, getBottomGasFractions, drawDecoProfile, drawGFCurve, and DOM ids
 * Globals written: (toast DOM only)
 */

// ═══════════════════════════════════════════════
// COPY DIVE PROFILE TO CLIPBOARD
// ═══════════════════════════════════════════════

// ═══════════════════════════════════════════════════════
//  UNIFIED EXPORT SYSTEM — v5.7.0
//  buildExportText(mode) → clean plain text, messenger-friendly
//  copyDiveProfile(mode) → clipboard
//  exportTXT(mode)       → .txt file download
// ═══════════════════════════════════════════════════════

const EXPORT_SECTION_RULE_WIDTH = 50;
const ASCENT_SCHEDULE_HEADER = 'Phase Depth  Stop  Mix   Run   TTS     PPO2  EAD    ';

function ascentScheduleRule() {
  return '-'.repeat(EXPORT_SECTION_RULE_WIDTH);
}

/** Strip contingency table prefix so export/PDF use standard phase names. */
function normalizeSchedulePhase(phase) {
  return String(phase || '').replace(/^contingency-/, '');
}

function collectAlertPlainLines(ids) {
  const out = [];
  (ids || ['decoAlerts', 'decoAlertsNarcotic']).forEach((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.querySelectorAll('.alert').forEach((a) => {
      const t = extractAlertPlainText(a);
      if (t) out.push(t);
    });
  });
  return out;
}

function _pdfAlertStyle(txt) {
  const t = String(txt || '').toUpperCase();
  if (t.includes('CNS')) return { bg: [255, 255, 0], tx: [17, 17, 17], border: [180, 180, 0] };
  if (t.includes('INSUFFICIENT') || t.includes('BEYOND MOD') || t.includes('LIMIT')) {
    return { bg: [255, 230, 230], tx: [120, 0, 0], border: [180, 30, 30] };
  }
  if (t.includes('GAS SWITCH') || t.includes('LOADED')) {
    return { bg: [255, 248, 220], tx: [100, 60, 0], border: [200, 150, 50] };
  }
  if (t.includes('NARCOTIC') || t.includes('NDL') || t.includes('DECOMPRESSION')) {
    return { bg: [255, 68, 51], tx: [255, 255, 255], border: [200, 50, 30] };
  }
  return { bg: [255, 68, 51], tx: [255, 255, 255], border: [200, 50, 30] };
}

function extractAlertPlainText(el) {
  if (!el) return '';
  if (typeof el === 'string') return el.replace(/\s+/g, ' ').trim();
  const inner = el.querySelector(':scope > div') || el;
  return (inner.textContent || '').replace(/\s+/g, ' ').trim();
}

function drawPdfAlertBanners(doc, y, opts, source) {
  const { ML, CW, checkY, cleanPDF } = opts;
  const clean = cleanPDF || ((s) => (s || '').trim());
  let alerts = [];
  if (typeof source === 'string') {
    const tmp = document.createElement('div');
    tmp.innerHTML = source;
    alerts = Array.from(tmp.querySelectorAll('.alert'));
  } else if (source && typeof source.length === 'number') {
    alerts = Array.from(source);
  } else {
    alerts = Array.from(document.querySelectorAll('#decoAlerts .alert, #decoAlertsNarcotic .alert, #decoSummary .alert'));
  }
  const padX = 4;
  const padTop = 3.5;
  const lineStep = 4.2;
  alerts.forEach((el) => {
    const txt = clean(extractAlertPlainText(el));
    if (!txt) return;
    const st = _pdfAlertStyle(txt);
    const ls = doc.splitTextToSize(txt, CW - padX * 2);
    const h = padTop + lineStep * ls.length + 1.5;
    checkY(h);
    doc.setFillColor(...st.bg);
    doc.setDrawColor(...st.border);
    doc.roundedRect(ML, y, CW, h, 1.5, 1.5, 'FD');
    doc.setFontSize(7.5);
    doc.setFont('DejaVuSans', 'bold');
    doc.setTextColor(...st.tx);
    ls.forEach((line, i) => doc.text(line, ML + padX, y + padTop + i * lineStep));
    doc.setTextColor(0, 0, 0);
    y += h + 3;
  });
  return y;
}

function exportBrandName() {
  return 'LSP D-Planner+';
}

function exportBrandWithCircuit() {
  const tag = typeof getExportCircuitTag === 'function' ? getExportCircuitTag() : 'OC';
  return `${exportBrandName()} (${tag})`;
}

function pushExportPlanningAidLines(lines) {
  lines.push('Planning Aid Only - Not a substitute for training, ');
  lines.push('certification, or a dive computer.');
}

function pushExportDisclaimerLines(lines) {
  [
    'This LSP Planner generated dive schedule ',
    'could indirectly kill you.The author does ',
    'not warrant that it accurately reflects the ',
    'selected decompression model algorithms, that ',
    'it won\'t get you bent or dead, or that it will',
    'produce safe, reliable results. This dive ',
    'schedule is experimental and you use it at ',
    'your own risk. Diving in general is fraught',
    'with risk, and decompression diving adds ',
    'significantly more risk. Deep diving utilizing',
    'multiple gasses, including Helium, is about as ',
    'risky as it gets. ',
    'This schedule is not intended for uneducated',
    'users. LSP Planner and the decompression schedules',
    'it produces are tools for experienced mixed-gas',
    'decompression divers ONLY. If you have not been',
    'properly trained in mixed-gas decompression diving',
    'by an internationally recognized technical ',
    'certification agency and/or don\'t have a firm',
    'handle on decompression planning and mixed-gas ',
    'diving, then',
    'DO NOT USE THIS DIVE SCHEDULE.',
  ].forEach((line) => lines.push(line));
}

// LSP-EXPORT-ENGINE:PLAN-HEADER
/** Structured dive plan header — shared by text export and on-screen banner. */
function buildDecoPlanHeaderData() {
  const now = new Date();
  const _dd = String(now.getDate()).padStart(2, '0');
  const _mm = String(now.getMonth() + 1).padStart(2, '0');
  const _yy = now.getFullYear();
  const _hh = String(now.getHours()).padStart(2, '0');
  const _min = String(now.getMinutes()).padStart(2, '0');
  const stamp = `${_yy}/${_mm}/${_dd} ${_hh}:${_min}`;
  const density = waterDensityDisplayLabel();
  const du = units === 'imperial' ? 'ft' : 'm';
  const altM = typeof altitudeM !== 'undefined' ? altitudeM : 0;
  const altLabel = altLabelDisp(altM);
  const acclLabel = (typeof altAcclimatized !== 'undefined' ? altAcclimatized : true) ? 'Yes' : 'No';

  const depth = document.getElementById('decoDepth')?.value || '-';
  const bt = document.getElementById('decoBT')?.value || '-';
  const gfLow = mGF?.low ?? '-';
  const gfHigh = mGF?.high ?? '-';
  const ascentRate = domMetricValToDisp(document.getElementById('ascentRate')?.value || '-');
  const decoAscentRate = domMetricValToDisp(document.getElementById('decoAscentRate')?.value || '-');
  const surfAscentRate = domMetricValToDisp(document.getElementById('surfaceAscentRate')?.value || '-');
  const descentRate = domMetricValToDisp(document.getElementById('descentRate')?.value || '-');
  const lastStop = domMetricValToDisp(document.getElementById('lastDecoStop')?.value || '-');
  const decoStep = domMetricValToDisp(document.getElementById('decoStep')?.value || '-');

  const decoModelSel = document.getElementById('algorithmSelect')?.value || 'ZHLC_GF';
  const isVPMExport = decoModelSel === 'VPMB' || decoModelSel === 'VPMB_GFS';
  const consVal = document.getElementById('conservatismSelect')?.value ?? '0';
  const algoNames = { ZHLC_GF: 'Buhlmann ZH-L16C + GF', VPMB: 'VPM-B', VPMB_GFS: 'VPM-B+GFS' };
  const algoNameExp = algoNames[decoModelSel] || decoModelSel;
  const algoSettings = decoModelSel === 'ZHLC_GF'
    ? `GF ${gfLow}/${gfHigh}`
    : decoModelSel === 'VPMB'
      ? `Conservatism +${consVal}`
      : `GF Hi ${gfHigh}  Conservatism +${consVal}`;

  const _expBotFracs = getBottomGasFractions();
  const _expBotLabel = _expBotFracs ? getGasLabel(_expBotFracs.fO2, _expBotFracs.fHe) : '—';
  const _expBotO2 = _expBotFracs ? Math.round(_expBotFracs.fO2 * 100) : 0;
  const _expBotHe = _expBotFracs ? Math.round((_expBotFracs.fHe || 0) * 100) : 0;
  const _expBotN2 = _expBotFracs ? Math.round(_expBotFracs.fN2 * 100) : 0;
  const _expIsTrimix = _expBotHe > 0;
  const _expBotDetail = !_expBotFracs ? '—' : (_expIsTrimix
    ? `${_expBotLabel}  (O2:${_expBotO2}% He:${_expBotHe}% N2:${_expBotN2}%)`
    : _expBotLabel);

  const _heHtMode = document.getElementById('heHalfTimeMode')?.value || 'baker';
  const _heHtLabel = _heHtMode === 'baker' ? 'Baker 1.88 min' : 'Buhlmann 2003 1.51 min';
  const _expSurfP = 1.01325 * Math.exp(-(altM) / 8434);
  const _expAltFactor = Math.pow(1.01325 / _expSurfP, 1 / 3);
  const _expAltRadii = isVPMExport && altM > 0
    ? `  Radii factor: x${_expAltFactor.toFixed(3)}`
    : '';

  const _vpmRepEl = document.getElementById('vpmRepMode');
  const _vpmRepActive = isVPMExport && _vpmRepEl && _vpmRepEl.checked && typeof _lastVPMResult !== 'undefined' && _lastVPMResult;
  const _vpmSI = _vpmRepActive ? (parseFloat(document.getElementById('vpmSurfaceInterval')?.value || '60')) : null;

  const rndTxt = (document.getElementById('stopRounding')?.value || 'fractional') === 'wholeminute' ? 'Yes' : 'No';
  const wvTxt = parseFloat(document.getElementById('waterVapor')?.value || '0.0627');
  const wvLblTxt = wvTxt <= 0.058 ? 'M' : 'B';

  const _expMdpEn = document.getElementById('minDecoProfileEnable')?.value === 'yes';
  const _expMdp9m = domMetricValToDisp(document.getElementById('minDeco9m')?.value || '1');
  const _expMdp6m = domMetricValToDisp(document.getElementById('minDeco6m')?.value || '3');
  const _depthUnit = units === 'imperial' ? 'ft' : 'm';
  const _ccrHdr = getCCRSettingsFromDOM();
  const _ccrLabel = _ccrHdr.bailout
    ? `BAILOUT OC GF ${_ccrHdr.bailoutGfLow}/${_ccrHdr.bailoutGfHigh}`
    : _ccrHdr.circuit === 'CCR'
      ? `CCR SP ${_ccrHdr.descentSetpoint}/${_ccrHdr.bottomSetpoint}/${_ccrHdr.decoSetpoint}`
    : _ccrHdr.circuit === 'pSCR' ? 'pSCR'
    : 'OC';

  return {
    stamp, du, density, altLabel, acclLabel, depth, bt,
    algoNameExp, algoSettings, isVPMExport, heHtLabel: _heHtLabel,
    bottomGas: _expBotDetail, bottomGasShort: shortMixLabel(_expBotLabel),
    travelGas: getTravelGasExport(),
    circuit: _ccrHdr.circuit, ccrLabel: _ccrLabel, ccrSetpoint: _ccrHdr.setpoint,
    ccrBailout: _ccrHdr.bailout,
    descentRate, ascentRate, decoAscentRate, surfAscentRate,
    lastStop, decoStep, stopRounding: rndTxt, wvTxt, wvLblTxt,
    altRadii: _expAltRadii, minDecoEn: _expMdpEn, minDeco9m: _expMdp9m, minDeco6m: _expMdp6m,
    depthUnit: _depthUnit, vpmRepActive: _vpmRepActive, vpmSI: _vpmSI,
    decoGases: isCcrOnLoopProfile(_ccrHdr) ? [] : getDecoGasSwitches(),
  };
}

/** True when exports should use OC labelling (open circuit or rebreather bailout). */
function isOcExportMode(ccr) {
  const cfg = ccr && ccr.circuit != null ? ccr : getCCRSettingsFromDOM();
  const circuit = cfg.circuit || document.getElementById('circuitSelect')?.value || 'OC';
  const bailout = cfg.bailout != null
    ? cfg.bailout
    : (document.getElementById('ccrBailoutToggle')?.value === 'on');
  return circuit === 'OC' || bailout;
}

/** Returns "DECO PLAN (OC)" or "DECO PLAN (CCR)" from circuit / bailout state. */
function getDecoPlanTitle(ccr) {
  return isOcExportMode(ccr) ? 'DECO PLAN (OC)' : 'DECO PLAN (CCR)';
}

/** Filename segment: OC or CCR (matches getDecoPlanTitle). */
function getExportCircuitTag(ccr) {
  return isOcExportMode(ccr) ? 'OC' : 'CCR';
}

/** Header lines for DECO PLAN — shared by on-screen summary and text export. */
function buildDecoPlanHeaderLines() {
  const d = buildDecoPlanHeaderData();
  const lines = [getDecoPlanTitle(d), d.stamp, '='.repeat(22)];
  lines.push(`Algorithm   : ${d.algoNameExp}  (${d.algoSettings})`);
  if (d.circuit && d.circuit !== 'OC') lines.push(`Circuit     : ${d.ccrLabel}${d.ccrBailout ? ' (bailout)' : ''}`);
  if (d.isVPMExport) lines.push(`He Half-Time: ${d.heHtLabel}`);
  lines.push(`Depth       : ${d.depth}${d.du}    BT: ${d.bt} min`);
  if (isCcrOnLoopProfile({ circuit: d.circuit, bailout: d.ccrBailout })) {
    lines.push(`Loop gas    : ${loopMixLabelFor(d.bottomGasShort, { circuit: d.circuit, bailout: d.ccrBailout })} (on-loop from surface)    Water: ${d.density}`);
  } else {
    const botPrefix = (d.circuit === 'CCR' || d.circuit === 'pSCR') ? 'Diluent     ' : 'Bottom Gas  ';
    lines.push(`${botPrefix}: ${d.bottomGas}    Water: ${d.density}`);
  }
  if (d.travelGas) lines.push(`Travel Gas  : ${d.travelGas.gas} (switch @ ${d.travelGas.depth})`);
  lines.push(`Descent     : ${d.descentRate}${d.du}/min  Ascent: ${d.ascentRate}${d.du}/min  Deco: ${d.decoAscentRate}${d.du}/min  Surface: ${d.surfAscentRate}${d.du}/min`);
  lines.push(`Last Stop   : ${d.lastStop}${d.du}  Step: ${d.decoStep}${d.du}`);
  lines.push(`Stop Rounding: ${d.stopRounding}  WV: ${d.wvTxt}(${d.wvLblTxt})`);
  lines.push(`Altitude     : ${d.altLabel}  Acclimatized: ${d.acclLabel}${d.altRadii}`);
  if (d.minDecoEn) lines.push(`Min Deco Profile: ON  (9${d.depthUnit}: ${d.minDeco9m} min  6${d.depthUnit}: ${d.minDeco6m} min)`);
  if (d.vpmRepActive) lines.push(`Repetitive   : Yes  Surface Interval: ${d.vpmSI} min  (bubble state + tissue loading carried)`);
  if (!isCcrOnLoopProfile({ circuit: d.circuit, bailout: d.ccrBailout })) {
    const gasPrefix = (d.circuit === 'CCR' || d.circuit === 'pSCR') ? 'Bailout mix' : 'Deco Gas';
    d.decoGases.forEach((g, i) => lines.push(`${gasPrefix} ${i + 1}  : ${g.gas} (switch @ ${g.depth})`));
  }
  return lines;
}

function _dpbGasChipClass(gas) {
  if (/^100/i.test(gas)) return 'dpb-chip--o2';
  return 'dpb-chip--deco';
}

// AUDIT-UNIT:UI-PLAN-HEADER
function renderDecoPlanHeaderHtml(data, opts) {
  opts = opts || {};
  data = data || buildDecoPlanHeaderData();
  const useV3 = !!document.getElementById('resultsPanel');
  const depthBt = `<strong>${_escHtmlPre(data.depth + data.du)}</strong> · <strong>${_escHtmlPre(data.bt)} min</strong> BT`;
  const algoLine = `<span>${_escHtmlPre(data.algoNameExp)} (${_escHtmlPre(data.algoSettings)})</span>`;

  const chips = [];
  if (data.travelGas) {
    chips.push(`<span class="gas-pill travel-gas"><span class="pill-dot"></span>Travel ${_escHtmlPre(data.travelGas.gas)} @ ${_escHtmlPre(data.travelGas.depth)}</span>`);
  }
  if (isCcrOnLoopProfile({ circuit: data.circuit, bailout: data.ccrBailout })) {
    chips.push(`<span class="gas-pill bottom-gas"><span class="pill-dot"></span>Loop ${_escHtmlPre(loopMixLabelFor(data.bottomGasShort, { circuit: data.circuit, bailout: data.ccrBailout }))}</span>`);
  } else {
    const botLbl = (data.circuit === 'CCR' || data.circuit === 'pSCR') ? 'Diluent' : 'Bottom';
    chips.push(`<span class="gas-pill bottom-gas"><span class="pill-dot"></span>${botLbl} ${_escHtmlPre(data.bottomGasShort)}</span>`);
  }
  if (!isCcrOnLoopProfile({ circuit: data.circuit, bailout: data.ccrBailout })) {
    const chipPrefix = (data.circuit === 'CCR' || data.circuit === 'pSCR') ? 'Bailout' : 'Deco';
    data.decoGases.forEach((g, i) => {
      const cls = i === 0 ? 'deco1' : 'deco2';
      chips.push(`<span class="gas-pill ${cls}"><span class="pill-dot"></span>${chipPrefix} ${i + 1} ${_escHtmlPre(g.gas)} @ ${_escHtmlPre(g.depth)}</span>`);
    });
  }

  const rates = `Descent <span>${_escHtmlPre(data.descentRate + data.du)}/min</span> · Ascent <span>${_escHtmlPre(data.ascentRate + data.du)}/min</span> · Deco <span>${_escHtmlPre(data.decoAscentRate + data.du)}/min</span> · Surface <span>${_escHtmlPre(data.surfAscentRate + data.du)}/min</span>`;
  const stops = `Last stop <span>${_escHtmlPre(data.lastStop + data.du)}</span> · Step <span>${_escHtmlPre(data.decoStep + data.du)}</span> · Rounding <span>${_escHtmlPre(data.stopRounding)}</span> · WV <span>${_escHtmlPre(String(data.wvTxt) + '(' + data.wvLblTxt + ')')}</span>`;
  const env = `${_escHtmlPre(data.density)} water · ${_escHtmlPre(data.altLabel)} · Accl <span>${_escHtmlPre(data.acclLabel)}</span>`;
  let extra = '';
  if (data.isVPMExport) extra += `<br>He half-time: <span>${_escHtmlPre(data.heHtLabel)}</span>`;
  if (data.minDecoEn) extra += `<br>Min deco profile: <span>ON</span> (9${_escHtmlPre(data.depthUnit)}: ${_escHtmlPre(data.minDeco9m)} min · 6${_escHtmlPre(data.depthUnit)}: ${_escHtmlPre(data.minDeco6m)} min)`;
  if (data.vpmRepActive) extra += `<br>Repetitive dive · SI <span>${_escHtmlPre(String(data.vpmSI))} min</span>`;

  const modeTag = getExportCircuitTag(data);
  const titleIcon = opts.hasDeco ? '⚠' : '✓';

  let html;
  if (useV3) {
    html = `<div class="deco-plan-card">
      <div class="deco-plan-top">
        <span class="deco-plan-icon">${titleIcon}</span>
        <span class="deco-plan-title">DECO PLAN <span class="mode-tag">(${_escHtmlPre(modeTag)})</span></span>
        <span class="deco-plan-timestamp">${_escHtmlPre(data.stamp)}</span>
      </div>
      <div class="deco-plan-summary">${depthBt} <span>· ${_escHtmlPre(data.algoNameExp)} (${_escHtmlPre(data.algoSettings)})</span></div>
      <div class="gas-pills">${chips.join('')}</div>
      <div class="deco-params">${rates}<br>${stops}<br>${env}${extra}</div>
    </div>`;
  } else {
    const bannerCls = opts.hasDeco ? 'dive-plan-banner dive-plan-banner--deco' : 'dive-plan-banner dive-plan-banner--ndl';
    const algoLineLegacy = `<span class="dpb-algo">${_escHtmlPre(data.algoNameExp)} (${_escHtmlPre(data.algoSettings)})</span>`;
    const legacyChips = [];
    if (data.travelGas) legacyChips.push(`<span class="dpb-chip dpb-chip--travel"><span class="dpb-chip-lbl">Travel</span>${_escHtmlPre(data.travelGas.gas)} @ ${_escHtmlPre(data.travelGas.depth)}</span>`);
    if (isCcrOnLoopProfile({ circuit: data.circuit, bailout: data.ccrBailout })) {
      legacyChips.push(`<span class="dpb-chip dpb-chip--bottom"><span class="dpb-chip-lbl">Loop</span>${_escHtmlPre(loopMixLabelFor(data.bottomGasShort, { circuit: data.circuit, bailout: data.ccrBailout }))} on-loop</span>`);
    } else {
      const botLbl = (data.circuit === 'CCR' || data.circuit === 'pSCR') ? 'Diluent' : 'Bottom';
      legacyChips.push(`<span class="dpb-chip dpb-chip--bottom"><span class="dpb-chip-lbl">${botLbl}</span>${_escHtmlPre(data.bottomGasShort)}</span>`);
    }
    if (!isCcrOnLoopProfile({ circuit: data.circuit, bailout: data.ccrBailout })) {
      const chipPrefix = (data.circuit === 'CCR' || data.circuit === 'pSCR') ? 'Bailout' : 'Deco';
      data.decoGases.forEach((g, i) => {
        legacyChips.push(`<span class="dpb-chip ${_dpbGasChipClass(g.gas)}"><span class="dpb-chip-lbl">${chipPrefix} ${i + 1}</span>${_escHtmlPre(g.gas)} @ ${_escHtmlPre(g.depth)}</span>`);
      });
    }
    const ratesLegacy = `Descent <b>${_escHtmlPre(data.descentRate + data.du)}/min</b> · Ascent <b>${_escHtmlPre(data.ascentRate + data.du)}/min</b> · Deco <b>${_escHtmlPre(data.decoAscentRate + data.du)}/min</b> · Surface <b>${_escHtmlPre(data.surfAscentRate + data.du)}/min</b>`;
    const stopsLegacy = `Last stop <b>${_escHtmlPre(data.lastStop + data.du)}</b> · Step <b>${_escHtmlPre(data.decoStep + data.du)}</b> · Rounding <b>${_escHtmlPre(data.stopRounding)}</b> · WV <b>${_escHtmlPre(String(data.wvTxt) + '(' + data.wvLblTxt + ')')}</b>`;
    const envLegacy = `${_escHtmlPre(data.density)} water · ${_escHtmlPre(data.altLabel)} · Accl <b>${_escHtmlPre(data.acclLabel)}</b>`;
    html = `<div class="${bannerCls}">
      <span>${titleIcon}</span>
      <div style="flex:1;min-width:0;">
        <div class="dpb-title">${_escHtmlPre(getDecoPlanTitle(data))} <span class="dpb-stamp">${_escHtmlPre(data.stamp)}</span></div>
        <div class="dpb-headline">${depthBt} · ${algoLineLegacy}</div>
        <div class="dpb-chips">${legacyChips.join('')}</div>
        <div class="dpb-meta">${ratesLegacy}<br>${stopsLegacy}<br>${envLegacy}${extra}</div>
      </div>
    </div>`;
  }
  if (opts.decoAlertHtml) html += opts.decoAlertHtml;
  if (opts.narcAlertHtml) html += opts.narcAlertHtml;
  return html;
}

function _pdfChipColors(kind) {
  switch (kind) {
    case 'travel': return { fill: [255, 248, 240], border: [255, 153, 0], lbl: [153, 85, 0], txt: [30, 30, 30] };
    case 'bottom': return { fill: [240, 244, 255], border: [65, 105, 225], lbl: [65, 105, 225], txt: [17, 17, 17] };
    case 'o2':     return { fill: [236, 254, 255], border: [0, 153, 204], lbl: [0, 120, 160], txt: [17, 17, 17] };
    default:       return { fill: [255, 251, 235], border: [212, 160, 23], lbl: [140, 100, 0], txt: [30, 30, 30] };
  }
}

/** Draw web-style DECO PLAN info banner in PDF — returns new Y position. */
function drawDecoPlanBannerPdf(doc, y, layout, data, planSum, hasDeco) {
  const { ML, CW, checkY, cleanPDF } = layout;
  const padX = 4;
  const padY = 3;
  const boxX = ML;
  const boxW = CW;
  const textX = boxX + padX + 6;
  const textW = boxW - padX * 2 - 6;
  const titleColor = hasDeco ? [255, 68, 51] : [38, 208, 124];
  const boxFill = hasDeco ? [255, 245, 244] : [240, 255, 244];
  const boxBorder = hasDeco ? [204, 68, 51] : [34, 136, 85];

  const chips = [];
  const isCcr = data.circuit === 'CCR' || data.circuit === 'pSCR';
  const onLoop = isCcrOnLoopProfile({ circuit: data.circuit, bailout: data.ccrBailout });
  if (data.travelGas) chips.push({ kind: 'travel', lbl: 'TRAVEL', val: `${data.travelGas.gas} @ ${data.travelGas.depth}` });
  if (onLoop) {
    chips.push({
      kind: 'bottom',
      lbl: 'LOOP',
      val: cleanPDF(loopMixLabelFor(data.bottomGasShort, { circuit: data.circuit, bailout: data.ccrBailout })),
    });
  } else {
    chips.push({ kind: 'bottom', lbl: isCcr ? 'DILUENT' : 'BOTTOM', val: cleanPDF(data.bottomGasShort) });
  }
  if (!onLoop) {
    const decoLbl = isCcr ? 'BAILOUT' : 'DECO';
    data.decoGases.forEach((g, i) => chips.push({
      kind: /^100/i.test(g.gas) ? 'o2' : 'deco',
      lbl: `${decoLbl} ${i + 1}`,
      val: `${g.gas} @ ${g.depth}`,
    }));
  }

  const metaLines = [
    cleanPDF(`Descent ${data.descentRate}${data.du}/min · Ascent ${data.ascentRate}${data.du}/min · Deco ${data.decoAscentRate}${data.du}/min · Surface ${data.surfAscentRate}${data.du}/min`),
    cleanPDF(`Last stop ${data.lastStop}${data.du} · Step ${data.decoStep}${data.du} · Rounding ${data.stopRounding} · WV ${data.wvTxt}(${data.wvLblTxt})`),
    cleanPDF(`${data.density} water · ${data.altLabel} · Accl ${data.acclLabel}${data.altRadii || ''}`),
  ];
  if (data.isVPMExport) metaLines.push(cleanPDF(`He half-time: ${data.heHtLabel}`));
  if (data.minDecoEn) metaLines.push(cleanPDF(`Min deco profile ON (9${data.depthUnit}: ${data.minDeco9m} min · 6${data.depthUnit}: ${data.minDeco6m} min)`));
  if (data.vpmRepActive) metaLines.push(cleanPDF(`Repetitive dive · SI ${data.vpmSI} min`));
  if ((data.bottomGas || '').includes('He:')) metaLines.push(cleanPDF(data.bottomGas));

  const sumLine = planSum ? cleanPDF(
    `Run ${planSum.runTime} · TTS ${planSum.tts} · Deco ${planSum.decoTime} · CNS ${planSum.cns} · OTU ${planSum.otu} · PrT ${planSum.prt} · Surf GF ${planSum.surfGF || '-'} · Decozone ${planSum.decozone} · First deco ${planSum.decoStop}`
  ) : '';

  const chipH = 5.5;
  const chipGap = 2;
  const chipPadX = 2;
  const chipRows = [[]];
  let chipX = padX + 6;
  const maxChipX = boxW - padX;
  chips.forEach(ch => {
    doc.setFontSize(6);
    doc.setFont('DejaVuSans', 'bold');
    const lblW = doc.getTextWidth(ch.lbl + ' ');
    doc.setFont('DejaVuSans', 'normal');
    doc.setFontSize(7);
    const valW = doc.getTextWidth(cleanPDF(ch.val));
    const chipW = lblW + valW + chipPadX * 2 + 2;
    if (chipX + chipW > maxChipX && chipRows[chipRows.length - 1].length) {
      chipRows.push([]);
      chipX = padX + 6;
    }
    chipRows[chipRows.length - 1].push({ ...ch, w: chipW, x: chipX });
    chipX += chipW + chipGap;
  });

  const lh = 4.2;
  const headline = cleanPDF(`${data.depth}${data.du} · ${data.bt} min BT · ${data.algoNameExp} (${data.algoSettings})`);
  doc.setFontSize(8.5);
  const headlineSplit = doc.splitTextToSize(headline, textW);
  doc.setFontSize(7);
  const metaSplit = metaLines.flatMap(l => doc.splitTextToSize(l, textW));
  const sumSplit = sumLine ? doc.splitTextToSize(sumLine, textW) : [];

  const bannerH = padY + 5 + headlineSplit.length * lh + 2
    + chipRows.length * (chipH + 2) + 2
    + metaSplit.length * lh + 2
    + sumSplit.length * lh + padY;

  checkY(bannerH + 3);
  doc.setFillColor(...boxFill);
  doc.setDrawColor(...boxBorder);
  doc.setLineWidth(0.6);
  doc.roundedRect(boxX, y, boxW, bannerH, 2, 2, 'FD');

  let cy = y + padY + 3.5;
  doc.setFontSize(9);
  doc.setFont('DejaVuSans', 'bold');
  doc.setTextColor(...titleColor);
  doc.text(hasDeco ? '\u26A0' : 'OK', boxX + padX, cy);
  doc.text(getDecoPlanTitle(data), boxX + padX + 5, cy);
  doc.setFontSize(7);
  doc.setFont('DejaVuSans', 'normal');
  doc.setTextColor(100, 100, 120);
  doc.text(cleanPDF(data.stamp), boxX + boxW - padX, cy, { align: 'right' });
  cy += 5;

  doc.setFontSize(8.5);
  doc.setFont('DejaVuSans', 'bold');
  doc.setTextColor(30, 30, 30);
  headlineSplit.forEach(line => { doc.text(line, textX, cy); cy += lh; });
  cy += 1;

  chipRows.forEach(row => {
    row.forEach(ch => {
      const c = _pdfChipColors(ch.kind);
      doc.setFillColor(...c.fill);
      doc.setDrawColor(...c.border);
      doc.setLineWidth(0.5);
      doc.roundedRect(boxX + ch.x, cy - 3.5, ch.w, chipH, 2, 2, 'FD');
      doc.setFontSize(6);
      doc.setFont('DejaVuSans', 'bold');
      doc.setTextColor(...c.lbl);
      doc.text(ch.lbl, boxX + ch.x + chipPadX, cy);
      doc.setFont('DejaVuSans', 'normal');
      doc.setTextColor(...c.txt);
      doc.setFontSize(7);
      const lblW = doc.getTextWidth(ch.lbl + ' ');
      doc.text(cleanPDF(ch.val), boxX + ch.x + chipPadX + lblW, cy);
    });
    cy += chipH + 2;
  });
  cy += 1;

  doc.setFontSize(7);
  doc.setFont('DejaVuSans', 'normal');
  doc.setTextColor(80, 80, 100);
  metaSplit.forEach(line => { doc.text(line, textX, cy); cy += lh; });
  cy += 1;

  if (sumSplit.length) {
    doc.setFont('DejaVuSans', 'bold');
    doc.setTextColor(0, 85, 170);
    sumSplit.forEach(line => { doc.text(line, textX, cy); cy += lh; });
  }

  doc.setTextColor(0, 0, 0);
  doc.setDrawColor(0, 0, 0);
  doc.setLineWidth(0.2);
  return y + bannerH + 3;
}

/** PDF dive profile table — column widths scaled to full content width. */
const _PDF_TBL_PAD = 2;
const _PDF_PHASE_PAD = 1.5;

function _pdfDecoTableLayout(ml, cw, pad = _PDF_TBL_PAD) {
  const tblMl = ml + pad;
  const tblCw = cw - pad * 2;
  const pct = [5, 14, 9, 12, 9, 9, 11, 11];
  const sum = pct.reduce((a, b) => a + b, 0);
  const colW = pct.map(p => tblCw * p / sum);
  const colX = [tblMl];
  for (let i = 0; i < colW.length - 1; i++) colX.push(colX[i] + colW[i]);
  return {
    colW, colX, tblMl, tblCw,
    headers: ['Phase', 'Depth', 'Stop', 'Mix', 'Run', 'TTS', 'PPO2', 'EAD'],
  };
}

function _pdfDrawDecoTableHeader(doc, y, layout, bgRgb) {
  const { colW, colX, headers, tblMl, tblCw } = layout;
  doc.setFillColor(...bgRgb);
  doc.rect(tblMl, y, tblCw, 6, 'F');
  doc.setFontSize(7);
  doc.setFont('DejaVuSans', 'bold');
  doc.setTextColor(255, 255, 255);
  headers.forEach((h, i) => {
    if (i === 0) doc.text(h, colX[0] + _PDF_PHASE_PAD, y + 4, { align: 'left' });
    else doc.text(h, colX[i] + colW[i] / 2, y + 4, { align: 'center' });
  });
  doc.setTextColor(0, 0, 0);
}

function _pdfDrawDecoPhaseLabel(doc, y, layout, label) {
  doc.text(label, layout.colX[0] + _PDF_PHASE_PAD, y + 3.5, { align: 'left' });
}

function _pdfDrawDecoTableCells(doc, y, layout, cells, txColor) {
  const { colW, colX } = layout;
  doc.setFontSize(7);
  doc.setFont('DejaVuSans', 'normal');
  doc.setTextColor(...txColor);
  cells.forEach((v, i) => {
    const cv = (v || '').trim();
    if (cv && cv !== '-') doc.text(cv, colX[i + 1] + colW[i + 1] / 2, y + 3.5, { align: 'center' });
  });
  doc.setTextColor(0, 0, 0);
}

/** Gas-switch row — gold fill only (no border), aligned to columns. */
function _pdfDrawSwitchRow(doc, y, layout, tr, cleanFn) {
  const clean = cleanFn || (s => (s || '').trim());
  const { colW, colX, tblMl, tblCw } = layout;
  const tds = Array.from(tr.querySelectorAll('td'));
  const depthTxt = clean(tds[1]?.textContent || '');
  const mixTxt = clean(tds[3]?.textContent || '');
  const ppo2Txt = clean(tr.querySelector('td[data-label="PPO2"]')?.textContent || '');
  doc.setFillColor(255, 248, 220);
  doc.rect(tblMl, y, tblCw, 5, 'F');
  doc.setFontSize(7);
  doc.setFont('DejaVuSans', 'bold');
  doc.setTextColor(140, 100, 0);
  _pdfDrawDecoPhaseLabel(doc, y, layout, '>>');
  if (depthTxt) doc.text(depthTxt, colX[1] + colW[1] / 2, y + 3.5, { align: 'center', maxWidth: colW[1] - 1 });
  if (mixTxt) doc.text(mixTxt, colX[3] + colW[3] / 2, y + 3.5, { align: 'center', maxWidth: colW[3] - 1 });
  if (ppo2Txt) doc.text(ppo2Txt, colX[6] + colW[6] / 2, y + 3.5, { align: 'center' });
  doc.setTextColor(0, 0, 0);
}

function buildDecoSummaryAlerts(hasDeco, endM, noDecoNote, hitSafetyGuard) {
  const decoAlertHtml = hasDeco
    ? '<div class="alert deco"><span>⚠</span><div><strong>DECOMPRESSION DIVE.</strong> Do not skip mandatory stops. Switch gas at optimal depth according to the deco schedule. Verify ppO₂ before each switch.</div></div>'
    : `<div class="alert ok"><span>✓</span><div><strong>NO-DECO DIVE.</strong>${noDecoNote ? ' ' + noDecoNote : ''}</div></div>`;
  const safetyGuardHtml = hitSafetyGuard
    ? '<div class="alert dang"><span>⚠</span><div><strong>DECO CALCULATION LIMIT.</strong> Decompression obligation exceeds the calculation limit — plan may be incomplete.</div></div>'
    : '';
  const narcTip = '<span class="tip-icon" onclick="showTip(_narcoticTipTitle,_narcoticTipText)"><svg width="11" height="11" viewBox="0 0 11 11" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="5.5" cy="5.5" r="5" stroke="currentColor" stroke-width="1.1"/><path d="M4.1 3.8 Q4.1 2.4 5.5 2.4 Q6.9 2.4 6.9 3.7 Q6.9 4.6 5.5 5.3 L5.5 6.2" stroke="currentColor" stroke-width="1.1" stroke-linecap="round" fill="none"/><circle cx="5.5" cy="7.4" r="0.55" fill="currentColor"/></svg></span>';
  const narcAlertHtml = endM > 40
    ? `<div class="alert narcotic-warn"><span>⚠</span><div><strong>HIGH NARCOTIC DEPTH.</strong> END exceeds 40 m equivalent. Consider a less narcotic gas mix.${narcTip}</div></div>`
    : endM > 30
      ? `<div class="alert narcotic-warn"><span>⚠</span><div><strong>NARCOTIC DEPTH WARNING.</strong> END exceeds 30 m equivalent. Consider a less narcotic gas mix.${narcTip}</div></div>`
      : '';
  return { decoAlertHtml, narcAlertHtml, safetyGuardHtml };
}

function updateDecoSummaryHtml(hasDeco, endM, noDecoNote, hitSafetyGuard) {
  const el = document.getElementById('decoSummary');
  if (!el) return;
  const { decoAlertHtml, narcAlertHtml, safetyGuardHtml } = buildDecoSummaryAlerts(hasDeco, endM, noDecoNote, hitSafetyGuard);
  _pendingDecoAlerts = (decoAlertHtml || '') + (safetyGuardHtml || '');
  _pendingDecoAlertsNarcotic = narcAlertHtml || '';
  el.innerHTML = renderDecoPlanHeaderHtml(buildDecoPlanHeaderData(), { hasDeco });
  scheduleDecoScheduleStackSync();
}

function exportScheduleCell(val, width, { right = false, blank = false } = {}) {
  const s = (val == null ? '' : String(val)).trim();
  if (!s || s === '-' || s === '—') {
    if (blank) return ' '.repeat(width);
    return '-'.padStart(width);
  }
  return right ? s.padStart(width) : s.padEnd(width);
}

function readExportScheduleCells(tr, clean) {
  const get = (label) => {
    const el = tr.querySelector(`td[data-label="${label}"]`);
    return el ? clean(el.textContent) : '';
  };
  return {
    depth: get('Depth'),
    stop: get('Stop'),
    mix: get('Mix'),
    run: get('Run'),
    tts: get('TTS'),
    ppo2: get('PPO2'),
    ead: get('EAD'),
  };
}

function formatExportSchedulePpo2(val) {
  const s = (val || '').trim();
  if (!s || s === '-' || s === '—') return '-';
  const n = parseFloat(s.replace(/[^\d.+-]/g, ''));
  return Number.isFinite(n) ? n.toFixed(2) : s;
}

function formatExportScheduleEad(val) {
  const s = (val || '').trim();
  if (!s || s === '-' || s === '—') return '-';
  const unitMatch = s.match(/^([\d.]+)\s*(m|ft)\b/i);
  if (unitMatch) {
    const n = Math.round(parseFloat(unitMatch[1]));
    return `${n}${unitMatch[2].toLowerCase()}`;
  }
  const n = parseFloat(s);
  return Number.isFinite(n) ? String(Math.round(n)) : s;
}

function formatExportGasVol(litres, volU) {
  if (typeof gpVolDisp === 'function') return `${gpVolDisp(litres)}${volU}`;
  if (!Number.isFinite(litres)) return `—${volU}`;
  return `${Math.round(litres)}${volU}`;
}

function formatExportGasLabel(r) {
  if (r.kind === 'bottom') {
    return (r.label || 'Air').replace(/\s*\(\+Travel\)/i, '+Travel').replace(/\s+/g, '').toUpperCase();
  }
  const mix = (r.mixLabel || (r.label || '').replace(/\s*\([^)]*\)\s*$/, '')).replace(/\s+/g, '');
  const roleMatch = (r.label || '').match(/\(([^)]+)\)/);
  const role = (roleMatch ? roleMatch[1] : 'Deco').toUpperCase();
  return `${mix.toUpperCase()}(${role})`;
}

function buildGasConsumptionLines(gp) {
  const volU = (typeof lspVolUnit === 'function') ? lspVolUnit(true) : (units === 'imperial' ? 'ft3' : 'L');
  const fmtV = (l) => formatExportGasVol(l, volU);
  const presU = units === 'imperial' ? 'psi' : 'bar';
  const sacBot = document.getElementById('sacBottom')?.value || '20';
  const sacDec = document.getElementById('sacDeco')?.value || '15';
  const ruleName = gp.rule === 'half' ? 'Half Tank' : 'Thirds';
  const lines = [
    'GAS CONSUMPTION',
    `Rule: ${ruleName}  SAC: bottom ${sacBot} L/min, deco ${sacDec} L/min`,
    ascentScheduleRule(),
  ];
  gp.rows.forEach(r => {
    const gasLbl = formatExportGasLabel(r);
    if (r.kind === 'bottom') {
      lines.push(`${gasLbl} ${fmtV(r.totalL)} avail, reserve: ${gpPresDisp(r.reserveBar)} ${presU}`);
      if (r.shortL != null && r.shortL > 0) {
        lines.push(`STATUS: INSUFFICIENT — need ${fmtV(r.reqL)}, have ${fmtV(r.totalL)}(short ${fmtV(r.shortL)})`);
        if (r.maxBTmin != null) {
          lines.push(`FIX: Shorten BT to ${r.maxBTmin} min, turn at ${gpPresDisp(r.maxTurnBar)} ${presU}`);
          lines.push('FIX: Or use a larger cylinder / add a stage');
        }
      } else {
        const ruleTxt = gp.rule === 'half' ? '1/2' : '1/3';
        lines.push(`TURN: ${gpPresDisp(r.turnBar)} ${presU} (${ruleTxt} of ${fmtV(r.portionL)})`);
        if (r.reqL != null) lines.push(`PLAN: needs ${fmtV(r.reqL)}, STATUS: OK`);
      }
      return;
    }
    lines.push(`${gasLbl}: ${fmtV(r.totalL)} avail, reserve: ${gpPresDisp(r.reserveBar)} ${presU}`);
    if (r.reqL == null) {
      lines.push('STATUS: run deco plan first');
    } else {
      const margin = r.totalL - r.reqL;
      const status = r.totalL >= r.reqL * 1.10 ? 'OK' : r.totalL >= r.reqL ? 'TIGHT' : 'INSUFFICIENT';
      lines.push(`NEED: ${fmtV(r.reqL)}, MARGIN: ${fmtV(margin)}, STATUS: ${status}`);
      if (status === 'INSUFFICIENT') lines.push('FIX: Add more gas or reduce deco obligation');
    }
  });
  lines.push(ascentScheduleRule());
  return lines;
}

function formatExportScheduleRun(run) {
  const s = (run || '').trim();
  if (!s || s === '-') return '-'.padEnd(6);
  if (s.length <= 4 && /^\d:/.test(s)) return (' ' + s).padEnd(7);
  return s.padEnd(6);
}

function formatExportScheduleMix(mix) {
  const s = (mix || '').trim();
  if (s === '100%') return ' 100%'.padEnd(6);
  return s.padEnd(6);
}

function formatExportScheduleStop(stop, phase) {
  const s = (stop || '').trim();
  if (!s) return ' '.repeat(7);
  if (s.length >= 5) return s.padEnd(7);
  if (phase === 'Asc' && s !== '1:00') return (' ' + s + ' ').padEnd(7);
  return (' ' + s).padEnd(6);
}

function formatExportScheduleTail(tts, ppo2, ead, phase, depth) {
  const ttsS = (tts || '').trim();
  const ppo2Col = formatExportSchedulePpo2(ppo2);
  const eadCol = formatExportScheduleEad(ead);
  if (!ttsS || ttsS === '-') {
    return '-'.padEnd(7) + ppo2Col + '   -';
  }
  const ttsPad = (phase === 'Stp' || (phase === 'Asc' && depth === '0m')) ? 9 : 8;
  let eadGap;
  if (eadCol === '-') {
    eadGap = (phase === 'Asc' && depth === '0m') ? '    -' : '   -';
  } else {
    eadGap = ' '.repeat(Math.max(2, 5 - eadCol.length)) + eadCol;
  }
  return ttsS.padEnd(ttsPad) + ppo2Col + eadGap;
}

function formatAscentScheduleHeaderRow() {
  return ASCENT_SCHEDULE_HEADER;
}

function formatAscentScheduleRow({ phase, depth, stop, mix, run, tts, ppo2, ead }) {
  const stp = (stop || '').trim();
  const line = phase.padEnd(6)
    + (depth || '').trim().padEnd(6)
    + formatExportScheduleStop(stp, phase)
    + formatExportScheduleMix(mix)
    + formatExportScheduleRun(run)
    + formatExportScheduleTail(tts, ppo2, ead, phase, (depth || '').trim());
  if (phase === 'Stp') {
    const depthLen = ((depth || '').trim()).length;
    return line.padEnd(depthLen <= 2 ? 53 : 52);
  }
  return line;
}

function buildExportText(mode) {
  const now     = new Date();
  const dateStr = now.toLocaleDateString('en-GB', { day:'2-digit', month:'short', year:'numeric' });
  const timeStr = now.toLocaleTimeString('en-GB', { hour:'2-digit', minute:'2-digit' });
  // Short timestamp for headers: YYYY/DD/MM HH:MM
  const _dd  = String(now.getDate()).padStart(2,'0');
  const _mm  = String(now.getMonth()+1).padStart(2,'0');
  const _yy  = now.getFullYear();
  const _hh  = String(now.getHours()).padStart(2,'0');
  const _min = String(now.getMinutes()).padStart(2,'0');
  const stamp = `${_yy}/${_mm}/${_dd} ${_hh}:${_min}`;
  const density = waterDensityDisplayLabel();
  const depthUnit = units === 'imperial' ? 'ft' : 'm';  // use live global
  const du = depthUnit; // shorthand - used without space: `${val}${du}`

  // ── altitude + acclimatize helper ──
  const altM      = (typeof altitudeM !== 'undefined') ? altitudeM : 0;
  const altAccl   = (typeof altAcclimatized !== 'undefined') ? altAcclimatized : true;
  const altLabel  = altM === 0 ? 'Sea level (0 m)' : `${altM} m`;
  const acclLabel = altAccl ? 'Yes' : 'No';

  // ── helper: clean DOM text (strip emoji, fix subscripts) ──
  const clean = t => t
    .replace(/[🔵🔴🟢🔴⇄↓↑⚠️🤿✓⚡🚨⏱ℹ]/g, '')
    .replace(/\s*·\s*/g, ' - ')
    .replace(/ppO₂/g, 'ppO2').replace(/O₂/g, 'O2')
    .replace(/[—–]/g, '-')
    .replace(/[≈~]/g, '~')
    .replace(/[≥]/g, '>=').replace(/[≤]/g, '<=')
    .replace(/Bühlmann/g, 'Buhlmann')
    .replace(/(\d)\s+(m|ft)\b/g, '$1$2')
    .replace(/\s*→\s*/g, '>')
    .replace(/\s+/g, ' ').trim();

  // ── helper: horizontal rules ──
  const hr    = '='.repeat(40);          // planner/generic section divider
  const decoHr = '='.repeat(22);         // matches "DECOMPRESSION SCHEDULE" width

  let lines = [];

  // ────────────────────────────────────────
  if (mode === 'planner') {
    const depth   = document.getElementById('depth')?.value  || '-';
    const bt      = document.getElementById('bt')?.value     || '-';
    const algo    = document.body.classList.contains('algo-buh') ? 'Bühlmann ZH-L16C' : 'PADI Rec Tables';
    const isRec   = !document.body.classList.contains('algo-buh');
    const gfStr   = !isRec ? `GF ${mGF?.low ?? '-'}/${mGF?.high ?? '-'}` : '';
    const gasEl   = document.getElementById('gasMix');
    const gasStr  = gasEl?.options[gasEl?.selectedIndex]?.text || '';
    const o2pct   = document.getElementById('customO2')?.value;

    lines.push('DECO PLAN (OC)');
    lines.push(stamp);
    lines.push(hr);
    lines.push(`Algorithm : ${algo}${gfStr ? '  ' + gfStr : ''}`);
    lines.push(`Depth     : ${depth}${du}`);
    lines.push(`Bottom T. : ${bt} min`);
    if (gasStr)  lines.push(`Gas       : ${gasStr}`);
    lines.push(`Water     : ${density}`);
    lines.push(`Altitude  : ${altLabel}  Acclimatized: ${acclLabel}`);
    lines.push('');

    // Pull results from rendered stats
    const statsEl = document.getElementById('plannerResult');
    if (statsEl) {
      const stats = statsEl.querySelectorAll('.stat');
      if (stats.length) {
        lines.push('RESULTS');
        lines.push(hr);
        stats.forEach(s => {
          const val = clean(s.querySelector('.stat-val')?.textContent || '');
          const lbl = clean(s.querySelector('.stat-lbl')?.textContent || '');
          if (val && lbl) lines.push(`${lbl.padEnd(20)}: ${val}`);
        });
        lines.push('');
      }
      // Alerts
      const alerts = statsEl.querySelectorAll('.alert');
      if (alerts.length) {
        lines.push('!! STATUS');
        lines.push(hr);
        alerts.forEach(a => lines.push('- ' + clean(a.textContent)));
        lines.push('');
      }
    }

  // ────────────────────────────────────────
  } else if (mode === 'deco') {
    const depth = document.getElementById('decoDepth')?.value || '-';
    const bt    = document.getElementById('decoBT')?.value    || '-';

    // ── helper: shorten mix names for table (trimix-aware) ──
    const shortMix = m => {
      const s = (m||'').trim();
      if (!s) return '-';
      if (/^\d+\/\d+$/.test(s)) return s; // O2/He format already
      if (s === '100%') return '100%';          // pure O2
      if (/^air$/i.test(s)) return 'Air';
      if (/^100/i.test(s)) return '100%';       // legacy '100% O2' fallback
      const ean = s.match(/[Ee][Aa][Nn]\s*(\d+)/); if (ean) return ean[1] + '/00';
      const pct = s.match(/(\d+)%/); if (pct) return pct[1] + '/00';
      return s;
    };

    // Read Deco Time and Run Time — always from table totals footer row (exists for both Bühlmann and VPM)
    const decoModelSel = document.getElementById('algorithmSelect')?.value || 'ZHLC_GF';
    const isVPMExport  = decoModelSel === 'VPMB' || decoModelSel === 'VPMB_GFS';

    const totalsRowEl = document.querySelector('#decoTableBody tr[data-phase="totals"] td');
    let planSum = getPlanSummaryExport(totalsRowEl);

    // Fallback for VPM if totals row not yet rendered: use _lastVPMExport
    if (isVPMExport && planSum.runTime === '-' && window._lastVPMExport) {
      const vx = window._lastVPMExport;
      const toMMSS = (n) => { const m = Math.floor(n), s = Math.round((n - m) * 60); return `${m}'${String(s).padStart(2,'0')}"`; };
      planSum.runTime  = toMMSS(vx.rt);
      planSum.decoTime = toMMSS(vx.deco);
      planSum.tts      = vx.tts || toMMSS(Math.max(0, vx.rt - parseFloat(bt)));
      planSum.cns      = vx.cns;
      planSum.otu      = vx.otu;
      planSum.prt      = vx.prt;
      planSum.decozone = vx.decozone || planSum.decozone;
      planSum.decoStop = vx.decoStop || planSum.decoStop;
    }

    // PrT fallback if not in totals row
    if (planSum.prt === '-') {
      const prtN = calcPrTBarMin(domDepthToM('decoDepth'), bt);
      if (!isNaN(prtN)) planSum.prt = prtN.toFixed(1);
    }

    lines.push(...buildDecoPlanHeaderLines());
    lines.push('');

    // Ascent schedule table
    const rows = document.querySelectorAll('#decoTableBody tr[data-phase]');
    if (rows.length) {
      lines.push('ASCENT SCHEDULE');
      lines.push(ascentScheduleRule());
      lines.push(formatAscentScheduleHeaderRow());
      lines.push(ascentScheduleRule());
      const phaseLabel = { descent:'Des', bottom:'Lvl', ascent:'Asc', deco:'Stp', safety:'Stp', totals:'TOT' };
      rows.forEach(tr => {
        const ph  = tr.dataset.phase;
        if (ph === 'totals') return; // handled below
        const tds = tr.querySelectorAll('td');
        if (ph === 'switch') {
          const cSw = Array.from(tds).map(td => clean(td.textContent));
          const mixSw = shortMix(cSw[3] || '');
          const depSw = (cSw[1] || '').trim();
          lines.push(`>> ${mixSw} @ ${depSw}`);
          return;
        }
        const cells = readExportScheduleCells(tr, clean);

        // Depth: descent may use 0→dest; ascent rows are destination-only
        let depRaw = cells.depth || '';
        if (ph === 'descent') {
          const arrowMatch = depRaw.match(/[→>](.+)$/);
          if (arrowMatch) depRaw = arrowMatch[1].trim();
        }
        const stp = typeof parseStopDisplayTime === 'function' ? parseStopDisplayTime(cells.stop) : (cells.stop || '');
        lines.push(formatAscentScheduleRow({
          phase: phaseLabel[ph] || ph,
          depth: depRaw.trim(),
          stop: stp,
          mix: shortMix(cells.mix || ''),
          run: cells.run || '',
          tts: cells.tts || '',
          ppo2: cells.ppo2 || '',
          ead: cells.ead || '',
        }));
      });

      lines.push(ascentScheduleRule());
      lines.push(...formatExportSummaryBlock(planSum));
      lines.push('');
    }

    // ── Gas Consumption ──
    const _gcEl = document.getElementById('gasConsumptionSummary');
    if (_gcEl && _gcEl.style.display !== 'none') {
      calcGasPlan();
      const _gp = window._lastGasPlan;
      if (_gp && _gp.rows && _gp.rows.length) {
        lines.push(...buildGasConsumptionLines(_gp));
        lines.push('');
      }
    }

    lines.push('!! SAFETY REMINDERS');
    lines.push('- Do NOT skip mandatory deco stops');
    lines.push('- Check ppO2 before each gas switch');
    lines.push('- Plan conservatively - never dive tables exactly');
    lines.push('- Carry 3+ min of reserve gas');
    lines.push('- Use your dive computer for backup');
    // CNS toxicity warning
    const cnsNumExport = parseFloat((planSum.cns || '0').replace('%', ''));
    if (!isNaN(cnsNumExport) && cnsNumExport >= 80) {
      lines.push('');
      lines.push('!! CNS OXYGEN TOXICITY WARNING');
      lines.push(`!! CNS% = ${planSum.cns} — exceeds 80% threshold.`);
      if (cnsNumExport >= 100) {
        lines.push('!! DANGER: CNS >= 100% — oxygen convulsion risk. Reduce O2 exposure.');
      } else {
        lines.push('!! Reduce deco gas ppO2, extend switch depths, or shorten bottom time.');
      }
    }
    lines.push('');

  // ────────────────────────────────────────
  } else if (mode === 'contingency') {
    const c = window._lastContingency;
    if (!c) return null;
    const shortMix = m => {
      const s = (m||'').trim();
      if (!s) return '-';
      if (/^\d+\/\d+$/.test(s)) return s; // O2/He format already
      if (s === '100%') return '100%';          // pure O2
      if (/^air$/i.test(s)) return 'Air';
      if (/^100/i.test(s)) return '100%';       // legacy '100% O2' fallback
      const ean = s.match(/[Ee][Aa][Nn]\s*(\d+)/); if (ean) return ean[1] + '/00';
      const pct = s.match(/(\d+)%/); if (pct) return pct[1] + '/00';
      return s;
    };

    lines.push('EMERGENCY PLAN');
    lines.push(stamp);
    lines.push(decoHr);
    lines.push(`Scenario    : ${c.label}`);
    if (c.msg) lines.push(`Note        : ${clean(c.msg)}`);
    lines.push(...buildDecoPlanHeaderLines().slice(3));
    lines.push('');

    const rows = document.querySelectorAll('#contingencyResult .deco-table tbody tr');
    if (rows.length) {
      lines.push('ASCENT SCHEDULE');
      lines.push(ascentScheduleRule());
      lines.push(formatAscentScheduleHeaderRow());
      lines.push(ascentScheduleRule());
      const phaseLabel = { descent:'Des', bottom:'Lvl', ascent:'Asc', deco:'Stp', safety:'Stp', switch:'>>' };
      rows.forEach(tr => {
        const ph  = normalizeSchedulePhase(tr.dataset.phase);
        if (ph === 'totals' || ph === 'info') return;
        const tds = tr.querySelectorAll('td');
        if (ph === 'switch') {
          const cSw = Array.from(tds).map(td => clean(td.textContent));
          const mixSw = shortMix(cSw[3] || '');
          const depSw = (cSw[1] || '').trim();
          lines.push(`>> ${mixSw} @ ${depSw}`);
          return;
        }
        const cells = readExportScheduleCells(tr, clean);

        // Ascent rows are destination-only; descent may use 0→dest
        let depRaw = cells.depth || '';
        if (ph === 'descent') {
          const arrowMatch = depRaw.match(/[→>](.+)$/);
          if (arrowMatch) depRaw = arrowMatch[1].trim();
        }
        const stp = typeof parseStopDisplayTime === 'function' ? parseStopDisplayTime(cells.stop) : (cells.stop || '');
        lines.push(formatAscentScheduleRow({
          phase: phaseLabel[ph] || ph,
          depth: depRaw.trim(),
          stop: stp,
          mix: shortMix(cells.mix || ''),
          run: cells.run || '',
          tts: cells.tts || '',
          ppo2: cells.ppo2 || '',
          ead: cells.ead || '',
        }));
      });

      const emSum = getContingencySummaryExport();
      lines.push(ascentScheduleRule());
      lines.push(...formatExportSummaryBlock(emSum));
      lines.push('');
    }
    const emAlertLines = collectAlertPlainLines(['decoAlertsEmergency']);
    if (emAlertLines.length) {
      emAlertLines.forEach((t) => lines.push('!! ' + clean(t)));
      lines.push('');
    }
    lines.push('!! SAFETY REMINDERS');
    lines.push('- Do NOT skip mandatory deco stops');
    lines.push('- Check ppO2 before each gas switch');
    lines.push('- Plan conservatively - never dive tables exactly');
    lines.push('- Carry 3+ min of reserve gas');
    lines.push('- Use your dive computer for backup');
    lines.push('');

  // ────────────────────────────────────────
  } else if (mode === 'multi') {
    lines.push(`${exportBrandName()} - MULTI DIVE DAY PLAN`);
    lines.push(hr);
    lines.push(`Water : ${density}`);
    lines.push('');

    // Pull each dive result card
    // Pull each dive card from unifiedDivePlan
    const diveCards = document.querySelectorAll('#unifiedDivePlan [id^="udp-dive-"]');
    let diveNum = 1;
    diveCards.forEach(card => {
      lines.push(`* DIVE ${diveNum}`);
      lines.push('-'.repeat(30));
      const dEl   = card.querySelector('[id^="udp-d"][id$="-disp"]');
      const btEl  = card.querySelector('[id^="udp-bt"][id$="-disp"]');
      const advEl = card.querySelector('[id^="udp-adv"]');
      if (dEl)  lines.push(`  ${'Depth'.padEnd(22)}: ${clean(dEl.textContent)}`);
      if (btEl) lines.push(`  ${'Bottom Time'.padEnd(22)}: ${clean(btEl.textContent)}`);
      if (advEl?.textContent?.trim()) lines.push(`  !! ${clean(advEl.textContent)}`);
      lines.push('');
      diveNum++;
    });

    // Warnings block
    const warns = document.getElementById('multiWarnings');
    if (warns?.textContent?.trim()) {
      lines.push('!! WARNINGS');
      lines.push(hr);
      lines.push(clean(warns.textContent));
      lines.push('');
    }

  // ────────────────────────────────────────
  } else if (mode === 'cns') {
    const depth    = document.getElementById('cnsDepth')?.value || '-';
    const bt       = document.getElementById('cnsBT')?.value    || '-';
    const o2       = document.getElementById('cnsO2')?.value    || '-';
    const dives    = document.getElementById('cnsDives')?.value || '-';
    const ppo2     = document.getElementById('cnsPPO2')?.textContent    || '-';
    const single   = document.getElementById('cnsSinglePct')?.textContent || '-';
    const daily    = document.getElementById('cnsDailyPct')?.textContent  || '-';
    const otu      = document.getElementById('cnsOTU')?.textContent      || '-';
    const statusEl = document.getElementById('cnsStatusText');
    const status   = statusEl ? clean(statusEl.textContent) : '';

    lines.push(`${exportBrandName()} - CNS O2 TRACKER`);
    lines.push(hr);
    lines.push(`Depth         : ${depth}${du}`);
    lines.push(`BT Time      : ${bt} min`);
    lines.push(`Gas O2%       : ${o2}%`);
    lines.push(`Dives today   : ${dives}`);
    lines.push('');
    lines.push('RESULTS');
    lines.push(hr);
    lines.push(`ppO2          : ${ppo2} bar`);
    lines.push(`CNS% single   : ${single}`);
    lines.push(`CNS% daily    : ${daily}`);
    lines.push(`OTU           : ${otu}`);
    if (status) {
      lines.push('');
      lines.push(`Status        : ${status}`);
    }
    lines.push('');
    lines.push('Limits (NOAA): CNS < 80% per dive, < 100% per day');
    lines.push('');
  }

  // ── Footer (all modes) ──
  lines.push(hr);
  pushExportPlanningAidLines(lines);
  lines.push(`Generated by ${exportBrandWithCircuit()}  ${dateStr} ${timeStr}`);
  lines.push('https://threecats-lsp.com/d-planner-plus/');
  lines.push('');
  lines.push('*'.repeat(43));
  lines.push('*       WARNING & DISCLAIMER              *');
  lines.push('*'.repeat(43));
  pushExportDisclaimerLines(lines);
  lines.push('*'.repeat(43));

  return lines.join('\n');
}

function decoPlanRowsExist() {
  return document.querySelectorAll('#decoTableBody tr[data-phase]').length > 0;
}
function notifyInvalidGasExport(toastId) {
  const gasVal = validateDomDecoGases();
  const msg = gasVal.errors[0]?.message || 'Invalid gas mixture — check bottom and deco gas fields.';
  showToast('Invalid gas: ' + msg, toastId || 'copy', true);
}
function notifyScheduleError(msg) {
  showToast('Cannot generate schedule: ' + msg, 'schedule', true);
}

function exportNeedsDecoBottomGas(mode) {
  return mode === 'deco' || mode === 'contingency'
    || (mode === 'planner' && decoPlanRowsExist());
}

// ── Copy to clipboard - shows preview modal ──
function copyDiveProfile(mode) {
  if (mode === 'deco' && !decoPlanRowsExist()) { showToast('Run a dive plan first', 'copy', true); return; }
  if (mode === 'contingency' && !window._lastContingency) { showToast('Run an emergency plan first', 'copy', true); return; }
  if (exportNeedsDecoBottomGas(mode) && !getBottomGasFractions()) { notifyInvalidGasExport('copy'); return; }
  const text = buildMessengerText(mode);
  if (!text) { showToast('Run a dive plan first', 'copy', true); return; }
  const titles = { deco: 'Deco Plan', contingency: 'Emergency Plan', planner: 'Dive Plan' };
  document.getElementById('copyModalTitle').textContent = titles[mode] || 'Copy Plan';
  document.getElementById('copyModalBody').textContent = text;
  document.getElementById('copyModal').style.display = 'flex';
}
function closeCopyModal() {
  document.getElementById('copyModal').style.display = 'none';
}
function copyCopyModal() {
  const text = document.getElementById('copyModalBody').textContent || '';
  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(text).then(() => showToast('Copied to clipboard', 'copy')).catch(() => copyFallback(text));
  } else {
    copyFallback(text);
  }
}

// ── Deco Slate: compact waterproof-slate format (deco stops only) ──
function buildSlateText() {
  const rows = document.querySelectorAll('#decoTableBody tr[data-phase]');
  if (!rows.length) return null;
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

  // Header bits
  const _sNow = new Date();
  const _sD = String(_sNow.getDate()).padStart(2,'0'), _sMo = String(_sNow.getMonth()+1).padStart(2,'0');
  const _sH = String(_sNow.getHours()).padStart(2,'0'), _sMi = String(_sNow.getMinutes()).padStart(2,'0');
  const dateStr = _sNow.toISOString().slice(0, 10);
  const stamp = `${_sNow.getFullYear()}/${_sMo}/${_sD} ${_sH}:${_sMi}`;
  const algoSel = document.getElementById('algorithmSelect')?.value || 'ZHLC_GF';
  const algoNames = { ZHLC_GF: 'Buhlmann GF', VPMB: 'VPM-B', VPMB_GFS: 'VPM-B+GFS' };
  const algoName = algoNames[algoSel] || algoSel;
  const algoLine = algoSel === 'ZHLC_GF'
    ? `${algoName} ${(mGF && mGF.low != null) ? mGF.low : '-'}/${(mGF && mGF.high != null) ? mGF.high : '-'}`
    : algoSel === 'VPMB'
      ? `${algoName} +${document.getElementById('conservatismSelect')?.value ?? '0'}`
      : `${algoName} GF Hi ${mGF.high}`;

  const botFracs = getBottomGasFractions();
  if (!botFracs) return null;
  const botLabel = shortMix(getGasLabel(botFracs.fO2, botFracs.fHe));

  // Switch gases with depths from rendered switch rows
  const gswRows = Array.from(document.querySelectorAll('#decoTableBody tr[data-phase="switch"]'));
  const switchParts = gswRows.map(tr => {
    const dep = clean(tr.querySelector('td[data-label="Depth"]')?.textContent || '');
    const gas = shortMix(tr.querySelector('td[data-label="Mix"]')?.textContent || '');
    return gas && dep ? `${gas} @ ${dep}` : '';
  }).filter(Boolean);
  const _slTravel = getTravelGasExport();
  const travelPart = _slTravel ? `${_slTravel.gas} (TRV @ ${_slTravel.depth})` : '';
  const mixLine = [botLabel + ' (BTM)', travelPart, ...switchParts].filter(Boolean).join(' | ');

  // Stop rows: only deco + safety stops (skip descent/bottom/ascent/switch/totals)
  const out = [];
  rows.forEach(tr => {
    const ph = tr.dataset.phase;
    if (ph !== 'deco' && ph !== 'safety') return;
    const tds = tr.querySelectorAll('td');
    const depRaw = clean(tds[1]?.textContent).replace(/(m|ft)$/i, '');
    const dep = (depRaw + du).padStart(5);
    const run = clean(tds[4]?.textContent).padStart(5);
    const gas = shortMix(tds[3]?.textContent).padEnd(6);
    const ppo2 = clean(tds[6]?.textContent).padStart(4);
    out.push(`${dep}  ${run}  ${gas} ${ppo2}`);
  });

  // Footer: TRT/TTS/DECO/CNS/OTU/PrT/Decozone/Deco stop — read from totals row
  const _stotRow = document.querySelector('#decoTableBody tr[data-phase="totals"] td');
  const _slSum = getPlanSummaryExport(_stotRow);
  const slateSum = {
    ..._slSum,
    runTime: _slSum.runTime === '-' ? `${document.getElementById('decoBT')?.value || '-'}'00"` : _slSum.runTime,
    decozone: typeof compactExportDepth === 'function' ? compactExportDepth(_slSum.decozone) : _slSum.decozone,
    decoStop: typeof compactExportDepth === 'function' ? compactExportDepth(_slSum.decoStop) : _slSum.decoStop,
  };
  const summaryLines = formatPlanSummaryBlock(slateSum, true);
  summaryLines[0] = summaryLines[0].replace(/^RT:/, 'TRT:');

  const bar = '========================';
  const lines = [];
  lines.push('DECO SLATE');
  lines.push(stamp);
  lines.push(bar);
  lines.push(`Algo: ${algoLine}`);
  lines.push(`Mix: ${mixLine}`);
  const slateAlerts = collectAlertPlainLines();
  if (slateAlerts.length) {
    lines.push('');
    slateAlerts.forEach((t) => lines.push('!! ' + clean(t)));
  }
  lines.push('');
  lines.push('DEPTH  TIME   GAS    PPO2');
  if (out.length) {
    out.forEach(l => lines.push(l));
  } else {
    lines.push('  (no decompression stops)');
  }
  lines.push(bar);
  lines.push(...summaryLines);
  return lines.join('\n');
}

function showSlate() {
  if (!decoPlanRowsExist()) { showToast('Run a dive plan first', 'slate', true); return; }
  if (!getBottomGasFractions()) { notifyInvalidGasExport('slate'); return; }
  const text = buildSlateText();
  if (!text) { showToast('Run a dive plan first', 'slate', true); return; }
  document.getElementById('slateModalBody').textContent = text;
  document.getElementById('slateModal').style.display = 'flex';
}
function closeSlate() {
  document.getElementById('slateModal').style.display = 'none';
}
function copySlate() {
  const text = document.getElementById('slateModalBody').textContent || '';
  if (!text) return;
  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(text).then(() => showToast('Slate copied', 'slate')).catch(() => copyFallback(text));
  } else {
    copyFallback(text);
  }
}

function buildMessengerText(mode) {
  if (mode === 'contingency') {
    const c = window._lastContingency;
    if (!c) return null;
    const depth = c.scenarioDepth ?? document.getElementById('decoDepth')?.value ?? '-';
    const bt    = c.scenarioBT    ?? document.getElementById('decoBT')?.value    ?? '-';
    const du    = units === 'metric' ? 'm' : 'ft';
    const shortMix = m => {
      const s = (m||'').trim().replace(/[📋⚠️🤿]/g,'').trim();
      if (!s) return '-';
      if (/^\d+\/\d+$/.test(s)) return s; // O2/He format already
      if (s === '100%') return '100%';          // pure O2
      if (/^air$/i.test(s)) return 'Air';
      if (/^100/i.test(s)) return '100%';       // legacy fallback
      const ean = s.match(/(\d+)%/); if (ean) return ean[1] + '/00';
      return s;
    };
    const clean = t => t.replace(/[📋⚠️🤿✓⚡🔵🔴🟢🚨⏱ℹ⇄↓↑]/g,'').replace(/\s*·\s*/g,' - ').replace(/ppO₂/g,'ppO2').replace(/O₂/g,'O2').replace(/[—–]/g,'-').replace(/Bühlmann/g,'Buhlmann').replace(/(\d)\s+(m|ft)\b/g,'$1$2').replace(/\s*→\s*/g,'>').replace(/\s+/g,' ').trim();
    const _cn = new Date(); const _cStamp = `${_cn.getFullYear()}/${String(_cn.getMonth()+1).padStart(2,'0')}/${String(_cn.getDate()).padStart(2,'0')} ${String(_cn.getHours()).padStart(2,'0')}:${String(_cn.getMinutes()).padStart(2,'0')}`;
    const result = [];
    result.push('EMERGENCY PLAN');
    result.push(_cStamp);
    result.push('-'.repeat(28));
    result.push(`${depth}${du} / ${bt}min / ${c.label}`);

    const cRnd = (document.getElementById('stopRounding')?.value||'fractional')==='wholeminute'?'Yes':'No';
    const cWV  = parseFloat(document.getElementById('waterVapor')?.value||'0.0627');
    const cWVL = cWV<=0.058?'M':'B';
    result.push(`Stp Rounding: ${cRnd}  WV: ${cWV}(${cWVL})`);
    const _cAltM   = (typeof altitudeM !== 'undefined') ? altitudeM : 0;
    const _cAltLbl = _cAltM === 0 ? 'Sea level' : `${_cAltM}m`;
    const _cAccl   = (typeof altAcclimatized !== 'undefined') ? altAcclimatized : false;
    result.push(`Altitude    : ${_cAltLbl}  Acclimatized: ${_cAccl ? 'Yes' : 'No'}`);
    const _cLastStop = document.getElementById('lastDecoStop')?.value || '-';
    const _cDecoStep = document.getElementById('decoStep')?.value    || '-';
    const _cAscRate  = document.getElementById('ascentRate')?.value      || '-';
    const _cDecRate  = document.getElementById('decoAscentRate')?.value  || '-';
    const _cSurfRate = document.getElementById('surfaceAscentRate')?.value || '-';
    const _cDesRate  = document.getElementById('descentRate')?.value || '-';
    result.push(`Last Stop   : ${_cLastStop}${du}  Step: ${_cDecoStep}${du}`);
    result.push(`Descent     : ${_cDesRate}${du}/min  Ascent: ${_cAscRate}${du}/min`);
    result.push(`Deco        : ${_cDecRate}${du}/min  Surface: ${_cSurfRate}${du}/min`);
    result.push('-'.repeat(28));
    const rows = document.querySelectorAll('#contingencyResult .deco-table tbody tr');
    rows.forEach(tr => {
      const ph = normalizeSchedulePhase(tr.dataset.phase);
      if (!ph || ph === 'totals' || ph === 'info') return;
      const tds = tr.querySelectorAll('td');
      const cv  = Array.from(tds).map(td => clean(td.textContent));
      if (ph === 'switch') { const switchTxt = Array.from(tds).slice(1).map(t=>clean(t.textContent)).filter(Boolean).join(' '); result.push('>> ' + switchTxt); return; }
      if (ph === 'descent' || ph === 'ascent') return;
      if (ph === 'bottom') { result.push(`Lvl  ${cv[1]}  ${cv[2]}  ${shortMix(cv[3])}`); return; }
      const stop = parseStopDisplayTime(cv[2]);
      result.push(`Stp  ${cv[1]}  ${stop}  ${cv[4]}  ${shortMix(cv[3])}`);
    });
    result.push('-'.repeat(28));
    result.push(...formatPlanSummaryBlock(getContingencySummaryExport(), true));
    return result.join('\n');
  }

  const rows = document.querySelectorAll('#decoTableBody tr[data-phase]');
  if (!rows.length) return buildExportText(mode);

  // One-line context header
  const depth = document.getElementById('decoDepth')?.value || '-';
  const bt    = document.getElementById('decoBT')?.value    || '-';
  const gfL   = mGF.low;
  const gfH   = mGF.high;
  const du    = units === 'metric' ? 'm' : 'ft';
  const unitsPref = units;

  const shortMix = m => {
    const s = (m||'').trim();
    if (!s) return '-';
    if (/^\d+\/\d+$/.test(s)) return s; // O2/He format already
    if (s === '100%') return '100%';          // pure O2
    if (/^air$/i.test(s)) return 'Air';
    if (/^100/i.test(s)) return '100%';       // legacy fallback
    const ean = s.match(/[Ee][Aa][Nn]\s*(\d+)/); if (ean) return ean[1] + '/00';
    const pct = s.match(/(\d+)%/); if (pct) return pct[1] + '/00';
    return s;
  };
  const clean = t => t
    .replace(/[🔵🔴🟢🔴⇄↓↑⚠️🤿✓⚡🚨⏱ℹ]/g, '')
    .replace(/\s*·\s*/g, ' - ')
    .replace(/ppO₂/g, 'ppO2').replace(/O₂/g, 'O2')
    .replace(/[—–]/g, '-')
    .replace(/[≈~]/g, '~')
    .replace(/[≥]/g, '>=').replace(/[≤]/g, '<=')
    .replace(/Bühlmann/g, 'Buhlmann')
    .replace(/(\d)\s+(m|ft)\b/g, '$1$2')
    .replace(/\s*→\s*/g, '>')
    .replace(/\s+/g, ' ').trim();

  // ── bottom gas header for messenger (trimix-aware) ──
  const _msgBotFracs = getBottomGasFractions();
  if (!_msgBotFracs) return null;
  const _msgBotLabel = getGasLabel(_msgBotFracs.fO2, _msgBotFracs.fHe);
  const _msgBotHe    = Math.round((_msgBotFracs.fHe || 0) * 100);
  const _msgBotDetail = _msgBotHe > 0
    ? `${_msgBotLabel} (O2:${Math.round(_msgBotFracs.fO2*100)}% He:${_msgBotHe}% N2:${Math.round(_msgBotFracs.fN2*100)}%)`
    : _msgBotLabel;

  const _msgNow = new Date();
  const _msgStamp = `${_msgNow.getFullYear()}/${String(_msgNow.getMonth()+1).padStart(2,'0')}/${String(_msgNow.getDate()).padStart(2,'0')} ${String(_msgNow.getHours()).padStart(2,'0')}:${String(_msgNow.getMinutes()).padStart(2,'0')}`;
  const _msgHr = '-'.repeat(28);
  const _msgGasHdr = buildDecoPlanHeaderData();

  const result = [];
  result.push(getDecoPlanTitle(_msgGasHdr));
  result.push(_msgStamp);
  result.push(_msgHr);
  // Algorithm + settings line
  const _algoSel = document.getElementById('algorithmSelect')?.value || 'ZHLC_GF';
  const _algoNames = { ZHLC_GF: 'ZHL16C+GF', VPMB: 'VPM-B', VPMB_GFS: 'VPM-B+GFS' };
  const _algoShort = _algoNames[_algoSel] || _algoSel;
  const _cons = document.getElementById('conservatismSelect')?.value ?? '0';
  const _algoStr = _algoSel === 'ZHLC_GF'
    ? `${_algoShort} GF${gfL}/${gfH}`
    : _algoSel === 'VPMB'
      ? `${_algoShort} C+${_cons}`
      : `${_algoShort} GFHi${gfH} C+${_cons}`;
  result.push(`${depth}${du} / ${bt}min / ${_algoStr}`);
  if (isCcrOnLoopProfile({ circuit: _msgGasHdr.circuit, bailout: _msgGasHdr.ccrBailout })) {
    result.push(`Loop gas    : ${loopMixLabelFor(_msgBotLabel, { circuit: _msgGasHdr.circuit, bailout: _msgGasHdr.ccrBailout })} (on-loop)`);
  } else {
    const botLine = (_msgGasHdr.circuit === 'CCR' || _msgGasHdr.circuit === 'pSCR') ? 'Diluent     ' : 'Bottom Gas  ';
    result.push(`${botLine}: ${_msgBotDetail}`);
  }
  if (_msgGasHdr.travelGas) result.push(`Travel Gas  : ${_msgGasHdr.travelGas.gas} (switch @ ${_msgGasHdr.travelGas.depth})`);
  if (!isCcrOnLoopProfile({ circuit: _msgGasHdr.circuit, bailout: _msgGasHdr.ccrBailout })) {
    const gasPrefix = (_msgGasHdr.circuit === 'CCR' || _msgGasHdr.circuit === 'pSCR') ? 'Bailout mix' : 'Deco Gas';
    _msgGasHdr.decoGases.forEach((g, i) => result.push(`${gasPrefix} ${i + 1}  : ${g.gas} (switch @ ${g.depth})`));
  }
  const rndVal = (document.getElementById('stopRounding')?.value||'fractional')==='wholeminute'?'Yes':'No';
  const wvVal  = parseFloat(document.getElementById('waterVapor')?.value||'0.0627');
  const wvLbl  = wvVal<=0.058?'M':'B';
  result.push(`Stp Rounding: ${rndVal}  WV: ${wvVal}(${wvLbl})`);
  const _cpMdpEn = document.getElementById('minDecoProfileEnable')?.value === 'yes';
  const _cpMdp9m = document.getElementById('minDeco9m')?.value || '1';
  const _cpMdp6m = document.getElementById('minDeco6m')?.value || '3';
  const _cpDu    = units === 'imperial' ? 'ft' : 'm';
  if (_cpMdpEn) result.push(`Min Deco Profile: ON  (9${_cpDu}: ${_cpMdp9m} min  6${_cpDu}: ${_cpMdp6m} min)`);
  const _mAltM   = (typeof altitudeM !== 'undefined') ? altitudeM : 0;
  const _mAltLbl = _mAltM === 0 ? 'Sea level' : `${_mAltM}m`;
  const _mAccl   = (typeof altAcclimatized !== 'undefined') ? altAcclimatized : true;
  const _mIsVPM  = _algoSel === 'VPMB' || _algoSel === 'VPMB_GFS';
  const _mAltSurfP = 1.01325 * Math.exp(-_mAltM / 8434);
  const _mAltRadii = _mIsVPM && _mAltM > 0
    ? `  Radii x${Math.pow(1.01325 / _mAltSurfP, 1/3).toFixed(3)}`
    : '';
  result.push(`Altitude    : ${_mAltLbl}  Acclimatized: ${_mAccl ? 'Yes' : 'No'}${_mAltRadii}`);
  // VPM repetitive dive
  const _mRepEl = document.getElementById('vpmRepMode');
  if (_mIsVPM && _mRepEl && _mRepEl.checked && typeof _lastVPMResult !== 'undefined' && _lastVPMResult) {
    const _mSI = parseFloat(document.getElementById('vpmSurfaceInterval')?.value || '60');
    result.push(`Repetitive  : SI ${_mSI} min (bubble state + tissue carried)`);
  }
  const _lastStop2    = document.getElementById('lastDecoStop')?.value || '-';
  const _decoStep2    = document.getElementById('decoStep')?.value    || '-';
  const _ascentRate2     = document.getElementById('ascentRate')?.value      || '-';
  const _decoAscentRate2 = document.getElementById('decoAscentRate')?.value  || '-';
  const _surfAscentRate2 = document.getElementById('surfaceAscentRate')?.value || '-';
  const _descentRate2 = document.getElementById('descentRate')?.value || '-';
  result.push(`Last Stop   : ${_lastStop2}${du}  Step: ${_decoStep2}${du}`);
  result.push(`Descent     : ${_descentRate2}${du}/min  Ascent: ${_ascentRate2}${du}/min`);
  result.push(`Deco        : ${_decoAscentRate2}${du}/min  Surface: ${_surfAscentRate2}${du}/min`);
  result.push('-'.repeat(28));

  rows.forEach(tr => {
    const ph  = tr.dataset.phase;
    if (ph === 'totals') return;
    const tds = tr.querySelectorAll('td');
    const c   = Array.from(tds).map(td => clean(td.textContent));

    if (ph === 'switch') {
      const mixSw = shortMix(c[3] || '');
      const depSw = (c[1] || '').trim();
      result.push(`>> ${mixSw} @ ${depSw}`);
      return;
    }
    if (ph === 'descent' || ph === 'ascent') return; // skip travel rows - clutter

    // bottom level
    if (ph === 'bottom') {
      result.push(`Lvl  ${c[1]}  ${c[2]}  ${shortMix(c[3])}`);
      return;
    }

    // deco / safety stop
    const dep  = c[1] || '';
    const stop = parseStopDisplayTime(c[2]);
    const run  = c[4] || '';
    const mix  = shortMix(c[3]);
    result.push(`Stp  ${dep}  ${stop}  ${run}  ${mix}`);
  });

  // Totals line — VPM has no table footer row, use stat cards
  const _algoForCopy = document.getElementById('algorithmSelect')?.value || 'ZHLC_GF';
  const _isVPMCopy   = _algoForCopy === 'VPMB' || _algoForCopy === 'VPMB_GFS';
  const totRow = document.querySelector('#decoTableBody tr[data-phase="totals"] td');
  let planSumCopy = getPlanSummaryExport(totRow);
  if (!totRow && _isVPMCopy && window._lastVPMExport) {
    const vx2 = window._lastVPMExport;
    const toMMSS = (n) => { const m = Math.floor(n), s = Math.round((n - m) * 60); return `${m}'${String(s).padStart(2,'0')}"`; };
    planSumCopy = {
      runTime: toMMSS(vx2.rt),
      tts: vx2.tts || toMMSS(Math.max(0, vx2.rt - parseFloat(document.getElementById('decoBT')?.value || '0'))),
      decoTime: toMMSS(vx2.deco),
      cns: vx2.cns,
      otu: vx2.otu,
      prt: vx2.prt,
      decozone: vx2.decozone || planSumCopy.decozone,
      decoStop: vx2.decoStop || planSumCopy.decoStop,
    };
  } else if (!totRow && _isVPMCopy) {
    const rtV  = document.getElementById('decoRunTimeDisplay')?.textContent?.trim().replace(/['\s]/g,'') || '-';
    const dtV  = document.getElementById('decoDecoTimeDisplay')?.textContent?.trim().replace(/\s*min\s*/,'') || '-';
    const cnsV = document.getElementById('decoCNSDisplay')?.textContent?.trim() || '-';
    const otuV = document.getElementById('decoOTUDisplay')?.textContent?.trim() || '-';
    const prtN = calcPrTBarMin(domDepthToM('decoDepth'), document.getElementById('decoBT')?.value || '0');
    planSumCopy.runTime = `${rtV}'00"`;
    planSumCopy.decoTime = `${dtV}'00"`;
    planSumCopy.cns = cnsV;
    planSumCopy.otu = otuV;
    planSumCopy.prt = isNaN(prtN) ? '-' : prtN.toFixed(1);
  }
  if (planSumCopy.prt === '-') {
    const prtN = calcPrTBarMin(domDepthToM('decoDepth'), document.getElementById('decoBT')?.value || '0');
    if (!isNaN(prtN)) planSumCopy.prt = prtN.toFixed(1);
  }
  result.push('-'.repeat(28));
  result.push(...formatPlanSummaryBlock(planSumCopy, true));

  return result.join('\n');
}

// ── Download .txt file ──
function exportTXT(mode) {
  if (mode === 'contingency' && !window._lastContingency) { showToast('Run an emergency plan first', 'export', true); return; }
  if (exportNeedsDecoBottomGas(mode) && !getBottomGasFractions()) { notifyInvalidGasExport('export'); return; }
  let text = mode === 'gasplan' ? buildGasPlanText() : buildExportText(mode);
  if (!text) return;
  if (mode === 'gasplan') {
    const dateStr = new Date().toISOString().split('T')[0];
    const blob = new Blob([text], { type: 'text/plain' });
    const a    = document.createElement('a');
    a.href     = URL.createObjectURL(blob);
    a.download = `LSP_${getExportCircuitTag()}_${dateStr}_GasPlan_${_gasRule}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(a.href);
    showExportToast();
    return;
  }
  if (mode === 'deco') {
    const slate = buildSlateText();
    if (slate) text += '\n\n' + slate;
  }
  const now     = new Date();
  const dateStr = now.toISOString().split('T')[0];
  const du      = units === 'metric' ? 'm' : 'ft';
  // altitude suffix for filename
  const _expAltM  = (typeof altitudeM !== 'undefined') ? altitudeM : 0;
  const _expAccl  = (typeof altAcclimatized !== 'undefined') ? altAcclimatized : true;
  const _altSuffix = _expAltM === 0 ? '' : `_Alt${_expAltM}m${_expAccl ? 'Accl' : 'NoAccl'}`;
  let tag = '';
  if (mode === 'deco') {
    const d    = document.getElementById('decoDepth')?.value || '0';
    const bt   = document.getElementById('decoBT')?.value    || '0';
    const algo = document.getElementById('algorithmSelect')?.value || 'ZHLC_GF';
    const cons = document.getElementById('conservatismSelect')?.value || '0';
    const gfHi = mGF?.high || 85;
    const gfLo = mGF?.low  || 30;
    let algoTag = '';
    if (algo === 'ZHLC_GF')  algoTag = `GF${gfLo}-${gfHi}_Buhlmann`;
    else if (algo === 'VPMB') algoTag = `C${cons}_VPM-B`;
    else                      algoTag = `GF${gfHi}_C${cons}_VPM-B_GFS`;
    tag = `Deco_${d}${du}_${bt}min_${algoTag}${_altSuffix}`;
  } else if (mode === 'planner') {
    const d  = document.getElementById('depth')?.value || '0';
    const bt = document.getElementById('bt')?.value    || '0';
    tag = `Plan_${d}${du}_${bt}min${_altSuffix}`;
  } else if (mode === 'contingency') {
    const d  = document.getElementById('decoDepth')?.value || '0';
    const bt = document.getElementById('decoBT')?.value    || '0';
    const sc = (window._lastContingency?.label || 'Contingency')
               .replace(/\s+/g, '_').replace(/[^a-zA-Z0-9_-]/g, '');
    tag = `Emergency_${d}${du}_${bt}min_${sc}${_altSuffix}`;
  } else if (mode === 'multi') {
    tag = 'Multi_Dive';
  } else if (mode === 'cns') {
    tag = 'CNS_O2_Tracker';
  } else {
    tag = mode;
  }
  const blob = new Blob([text], { type: 'text/plain' });
  const a    = document.createElement('a');
  a.href     = URL.createObjectURL(blob);
  a.download = `LSP_${getExportCircuitTag()}_${dateStr}_${tag}.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(a.href);
  showExportToast();
}

// ── Clipboard fallback (execCommand) ──
function copyFallback(text) {
  try {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.cssText = 'position:fixed;left:-9999px;top:-9999px;opacity:0;width:1px;height:1px;padding:0;border:none;';
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(ta);
    if (ok) showCopyToast();
    else showToast('Copy failed — select text manually', 'copy', true);
  } catch(e) {
    console.error('Copy fallback error:', e);
    showToast('Copy failed', 'copy', true);
  }
}





function showCopyToast()   { showToast('📋 Copied!', 'copy'); }
function showExportToast() { showToast('📥 Saved!',  'export'); }
function showToast(msg, id, isError) {
  let toast = document.getElementById('toast-' + id);
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'toast-' + id;
    toast.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);padding:10px 22px;border-radius:20px;font-family:"JetBrains Mono",monospace;font-size:13px;font-weight:700;letter-spacing:1px;z-index:9999;transition:opacity 0.4s;pointer-events:none;max-width:min(90vw,480px);text-align:center;';
    document.body.appendChild(toast);
  }
  toast.style.background = isError ? 'var(--red)' : 'var(--accent)';
  toast.style.color = isError ? '#fff' : 'var(--bg)';
  toast.textContent = msg;
  toast.style.opacity = '1';
  setTimeout(() => { toast.style.opacity = '0'; }, isError ? 4000 : 2200);
}


function runPdfExportFromDialog() {
  const opts = {};
  ['gas', 'profile', 'slate', 'gfCurve', 'tissue'].forEach(k => {
    opts[k] = document.getElementById('pdfOpt_' + k)?.checked !== false;
  });
  document.getElementById('pdfExportDialog')?.remove();
  exportPDF(opts).catch(function(e) {
    console.error('[PDF export]', e);
    alert('PDF export failed: ' + (e && e.message ? e.message : e));
  });
}

// LSP-EXPORT-ENGINE:PDF-INFRA
// ── Shared PDF text sanitization (single canonical copy) ──
function cleanPdfText(s) {
  if (!s) return '';
  s = String(s);
  s = s.replace(/[\u2080-\u2089]/g, c => String.fromCharCode(c.charCodeAt(0) - 0x2050));
  s = s.replace(/[\u00B2\u00B3\u00B9]/g, c => ({ '\u00B2': '2', '\u00B3': '3', '\u00B9': '1' }[c] || c));
  s = s.replace(/\u00B7|\u2022|\u2027/g, '*').replace(/\u2014/g, '--').replace(/\u2013/g, '-')
    .replace(/\u2018|\u2019/g, "'").replace(/\u201C|\u201D/g, '"');
  s = s.replace(/[\u2600-\u269F\u26A1-\u26FF\u2700-\u2712\u2714-\u2716\u2718-\u27FF\u2B00-\u2BFF\u2300-\u23FF\uFE0F]/g, '');
  s = s.replace(/[^\x20-\x7E\xA0-\u024F\u2190-\u2193\u2713\u2717\u26A0]/g, '');
  return s.replace(/^\s*[!&*#^~]+\s*/, '').trim();
}

/** PDF RGB + status — must match web lspSatColors() thresholds in index.html. */
function lspSatStatus(pct) {
  const p = Math.round(pct);
  if (p >= 80) return { status: p >= 100 ? 'LIMIT' : 'HIGH', level: 'warn' };
  if (p >= 50) return { status: 'LOADED', level: 'caution' };
  return { status: 'OK', level: 'safe' };
}
function lspSatRgb(pct) {
  const { level } = lspSatStatus(pct);
  if (level === 'warn') return [239, 68, 68];
  if (level === 'caution') return [245, 158, 11];
  return [22, 163, 74];
}
function drawTissueSatLegend(doc, y, ML) {
  const items = [
    [lspSatRgb(25), '<50% clear'],
    [lspSatRgb(65), '50-79% loaded'],
    [lspSatRgb(85), '>=80% near/at limit'],
  ];
  doc.setFontSize(6); doc.setFont('DejaVuSans', 'normal');
  let lx = ML;
  items.forEach(([rgb, lbl]) => {
    doc.setFillColor(...rgb); doc.roundedRect(lx, y + 1, 3, 3, 0.5, 0.5, 'F');
    doc.setTextColor(80, 80, 100); doc.text(lbl, lx + 5, y + 4);
    lx += doc.getTextWidth(lbl) + 11;
  });
  doc.setTextColor(0, 0, 0);
  return y + 7;
}

function legendRowFromTr(tr) {
    if (!(tr instanceof HTMLElement)) return tr;
    const cell = (label) => tr.querySelector(`td[data-label="${label}"]`)?.textContent.trim()
      || tr.querySelector(`th[data-label="${label}"]`)?.textContent.trim()
      || '';
    const num = cell('#') || tr.querySelector('td:nth-child(1)')?.textContent.trim() || '';
    const stop = (cell('Stop') || tr.querySelector('td:nth-child(2)')?.textContent.trim() || '')
      .replace(/[^\x20-\x7E]/g, '').trim();
    const run = cell('Run') || tr.querySelector('td:nth-child(3)')?.textContent.trim() || '';
    const ppo = cell('ppO2') || cell('PPO2') || tr.querySelector('td:nth-child(4)')?.textContent.trim() || '';
    return { num, stop, run, ppo2: ppo };
  }

function drawGraphLegend(doc, y, ML, CW, checkY, legendRows) {
    let rows = legendRows;
    if (!rows) {
      const legEl = document.getElementById('plannerProfileLegend')
        || document.getElementById('decoProfileLegend');
      rows = legEl ? Array.from(legEl.querySelectorAll('tbody tr')) : [];
    }
    if (!rows.length && typeof buildProfileLegendRowsFromWaypoints === 'function') {
      rows = buildProfileLegendRowsFromWaypoints();
    }
    if (!rows.length) return y;
    checkY(rows.length * 5 + 10);
    // Header
    doc.setFillColor(240,244,255); doc.rect(ML,y,CW,5.5,'F');
    doc.setFontSize(6.5); doc.setFont('DejaVuSans','bold'); doc.setTextColor(80,80,120);
    const cw=[8,80,30,24]; const cx=[ML,ML+8,ML+88,ML+118];
    ['#','Stop','Run','ppO2'].forEach((h,i)=>doc.text(h,cx[i]+(i>0?cw[i]/2:cw[0]/2),y+3.8,{align:i===0?'center':'center'}));
    doc.setTextColor(0,0,0); y+=5.5;
    rows.forEach((row, ri)=>{
      const norm = legendRowFromTr(row);
      const num = norm.num || '';
      const stop = norm.stop || '';
      const run = norm.run || '';
      const ppo = norm.ppo2 || norm.ppo || '';
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

function buildProfileLegendRowsFromWaypoints() {
  const wps = window._plannerWaypoints || window._decoWaypoints || [];
  const rows = [];
  let stopNum = 0;
  [...wps].sort((a, b) => a.t - b.t).forEach(wp => {
    if (wp.type === 'gasswitch') {
      const gas = String(wp.gasLabel || '').replace(/\s+/g, ' ').trim();
      const depthTxt = wp.depthLabel || (wp.depth != null ? `${wp.depth}m` : '');
      rows.push({
        num: '⇄',
        stop: `${depthTxt}${gas ? ' · ' + gas : ''}`,
        run: `${Math.round(wp.t * 10) / 10} min`,
        ppo2: wp.ppo2 != null ? Number(wp.ppo2).toFixed(2) : '—',
      });
      return;
    }
    if (!wp.dot || !wp.label) return;
    stopNum += 1;
    rows.push({
      num: String(stopNum),
      stop: wp.label.replace(/(\d+m)\s+(\d+)/, '$1 - $2'),
      run: `${Math.round(wp.t)} min`,
      ppo2: wp.ppo2 != null ? Number(wp.ppo2).toFixed(2) : '—',
    });
  });
  return rows;
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

function _ttfBufferToBase64(buf) {
  const bytes = new Uint8Array(buf);
  const CHUNK = 8192;
  let bin = '';
  for (let i = 0; i < bytes.length; i += CHUNK) {
    bin += String.fromCharCode.apply(null, bytes.subarray(i, i + CHUNK));
  }
  return btoa(bin);
}

function _installPdfFontsOnDoc(doc, cache) {
  doc.addFileToVFS('DejaVuSans.ttf', cache.regular);
  doc.addFileToVFS('DejaVuSans-Bold.ttf', cache.bold);
  doc.addFont('DejaVuSans.ttf', 'DejaVuSans', 'normal');
  doc.addFont('DejaVuSans-Bold.ttf', 'DejaVuSans', 'bold');
  doc.setFont('DejaVuSans', 'normal');
}

async function loadPDFFonts(doc) {
  if (_pdfFontCache) {
    _installPdfFontsOnDoc(doc, _pdfFontCache);
    return true;
  }

  const embedded = typeof window !== 'undefined' ? window._LSP_PDF_FONTS : null;
  if (embedded?.regular && embedded?.bold) {
    _pdfFontCache = { regular: embedded.regular, bold: embedded.bold };
    _installPdfFontsOnDoc(doc, _pdfFontCache);
    return true;
  }

  try {
    const fontBase = new URL('vendor/fonts/', window.location.href);
    const [rResp, bResp] = await Promise.all([
      fetch(new URL('DejaVuSans.ttf', fontBase)),
      fetch(new URL('DejaVuSans-Bold.ttf', fontBase)),
    ]);
    if (!rResp.ok || !bResp.ok) throw new Error('Font fetch failed');
    const [rBuf, bBuf] = await Promise.all([rResp.arrayBuffer(), bResp.arrayBuffer()]);
    _pdfFontCache = { regular: _ttfBufferToBase64(rBuf), bold: _ttfBufferToBase64(bBuf) };
    _installPdfFontsOnDoc(doc, _pdfFontCache);
    return true;
  } catch (e) {
    console.error('[LSP] DejaVu font load failed — Unicode symbols will not render in PDF. Check vendor/pdf-fonts.js and vendor/fonts/ assets.', e);
    return false;
  }
}
async function ensurePDFFontsForPDF(doc) {
  try {
    const ok = await loadPDFFonts(doc);
    if (!ok) {
      alert('PDF fonts could not be loaded. Ensure vendor/pdf-fonts.js is included, or open the app via a local web server.');
      return false;
    }
    return true;
  } catch (e) {
    console.error('[LSP] PDF font load failed:', e);
    alert('PDF fonts could not be loaded. Ensure vendor/pdf-fonts.js is included, or open the app via a local web server.');
    return false;
  }
}

function showPDFExportDialog() {
  // Remove any existing dialog
  const old = document.getElementById('pdfExportDialog');
  if (old) old.remove();

  const overlay = document.createElement('div');
  overlay.id = 'pdfExportDialog';
  overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:9999;display:flex;align-items:center;justify-content:center;';

  const box = document.createElement('div');
  box.style.cssText = 'background:var(--surface,#1a1e2e);border:1px solid var(--border,#2a3050);border-radius:12px;padding:24px 28px;width:340px;max-width:92vw;font-family:\'Outfit\',sans-serif;box-shadow:0 8px 40px rgba(0,0,0,0.5);';

  const sections = [
    { key:'gas',     label:'Gas Consumption',       checked:true  },
    { key:'profile', label:'Dive Profile Graph',     checked:true  },
    { key:'slate',   label:'Deco Slate',             checked:true  },
    { key:'gfCurve', label:'GF Gradient Factor Curve', checked:false },
    { key:'tissue',  label:'Tissue Saturation',      checked:false },
  ];

  let rows = sections.map(s => `
    <label style="display:flex;align-items:center;gap:10px;padding:7px 0;cursor:pointer;border-bottom:1px solid var(--border,#2a3050);">
      <input type="checkbox" id="pdfOpt_${s.key}" ${s.checked?'checked':''} style="width:15px;height:15px;accent-color:var(--accent,#00d9ff);cursor:pointer;">
      <span style="font-size:13px;color:var(--text,#e8eaf6);">${s.label}</span>
    </label>`).join('');

  box.innerHTML = `
    <div style="font-family:'Bebas Neue',sans-serif;font-size:18px;letter-spacing:2px;color:var(--accent,#00d9ff);margin-bottom:16px;">PDF EXPORT</div>
    <div style="font-size:11px;color:var(--muted,#8890b0);margin-bottom:14px;letter-spacing:0.5px;">SELECT SECTIONS TO INCLUDE</div>
    <div style="margin-bottom:18px;">${rows}</div>
    <div style="display:flex;gap:10px;justify-content:flex-end;">
      <button onclick="document.getElementById('pdfExportDialog').remove()"
        style="padding:9px 18px;background:transparent;color:var(--muted,#8890b0);border:1px solid var(--border,#2a3050);border-radius:6px;cursor:pointer;font-family:'Outfit',sans-serif;font-size:13px;font-weight:600;">
        Cancel
      </button>
      <button onclick="runPdfExportFromDialog()"
        style="padding:9px 18px;background:var(--accent,#00d9ff);color:#000;border:none;border-radius:6px;cursor:pointer;font-family:'Outfit',sans-serif;font-size:13px;font-weight:700;letter-spacing:1px;">
        EXPORT PDF
      </button>
    </div>`;

  overlay.appendChild(box);
  // Click outside to cancel
  overlay.addEventListener('click', e => { if(e.target===overlay) overlay.remove(); });
  document.body.appendChild(overlay);
}

// Force light theme for a canvas draw + capture, then restore original theme.
// PDF is always a light-background document — dark canvas graphs look bad in it.
function _drawForPDF(drawFn) {
  const body = document.body;
  const wasLight = body.classList.contains('light-theme');
  if (!wasLight) body.classList.add('light-theme');
  try { drawFn(); } finally {
    if (!wasLight) body.classList.remove('light-theme');
  }
}

async function exportPDF(opts) {
  opts = opts || {};
  if (!window._zhlHeadless) {
    const gasVal = validateDomDecoGases();
    if (!gasVal.ok) {
      throw new Error(gasVal.errors[0]?.message || 'Invalid gas mixture.');
    }
  }
  const _incGas      = opts.gas      !== false;
  const _incProfile  = opts.profile  !== false;
  const _incSlate    = opts.slate    !== false;
  const _incGFCurve  = opts.gfCurve  !== false;
  const _incTissue   = opts.tissue   !== false;

  if (!window.jspdf || !window.jspdf.jsPDF) { alert('PDF library not loaded. Please check your internet connection.'); return; }
  const { jsPDF } = window.jspdf;

  const doc = new jsPDF({ unit:'mm', format:'a4', orientation:'portrait' });
  if (!(await ensurePDFFontsForPDF(doc))) return;
  const now = new Date();
  const dateStr = now.toLocaleDateString('en-GB',{day:'2-digit',month:'short',year:'numeric'});
  const timeStr = now.toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit'});
  const isoDate = now.toISOString().split('T')[0];

  const decoModelSel = document.getElementById('algorithmSelect')?.value || 'ZHLC_GF';
  const isVPM = decoModelSel === 'VPMB' || decoModelSel === 'VPMB_GFS';
  const algoNames = { ZHLC_GF:'Bühlmann ZH-L16C+GF', VPMB:'VPM-B', VPMB_GFS:'VPM-B+GFS' };
  const algo = algoNames[decoModelSel] || 'Bühlmann ZH-L16C+GF';
  const cons = document.getElementById('conservatismSelect')?.value || '0';
  const gfStr = decoModelSel==='ZHLC_GF' ? `GF ${mGF.low}/${mGF.high}`
              : decoModelSel==='VPMB'     ? `C+${cons}`
              :                             `GFHi ${mGF.high} · C+${cons}`;
  // VPM extras
  const _pdfAltM      = (typeof altitudeM !== 'undefined') ? altitudeM : 0;
  const _pdfAccl      = (typeof altAcclimatized !== 'undefined') ? altAcclimatized : true;
  const _pdfAltLbl    = _pdfAltM === 0 ? 'Sea level' : `${_pdfAltM} m`;
  const _pdfAltSurfP  = 1.01325 * Math.exp(-_pdfAltM / 8434);
  const _pdfRadii     = isVPM && _pdfAltM > 0 ? Math.pow(1.01325 / _pdfAltSurfP, 1/3).toFixed(3) : null;
  const _pdfHeHt      = document.getElementById('heHalfTimeMode')?.value || 'baker';
  const _pdfHeHtLbl   = _pdfHeHt === 'baker' ? 'Baker 1.88 min' : 'Buhlmann 2003 1.51 min';
  const _pdfRepEl     = document.getElementById('vpmRepMode');
  const _pdfRepActive = isVPM && _pdfRepEl && _pdfRepEl.checked && typeof _lastVPMResult !== 'undefined' && _lastVPMResult;
  const _pdfSI        = _pdfRepActive ? (parseFloat(document.getElementById('vpmSurfaceInterval')?.value || '60')) : null;
  const _pdfSacUnit   = (typeof lspSacUnit === 'function') ? lspSacUnit(true) : (units === 'imperial' ? 'ft3/min' : 'L/min');
  const du       = units === 'imperial' ? 'ft' : 'm';
  const depthVal = document.getElementById('decoDepth')?.value || '—';
  const btVal    = document.getElementById('decoBT')?.value    || '—';
  const densityLabel = waterDensityDisplayLabel();
  const _pdfHdr = buildDecoPlanHeaderData();
  const _pdfTravelInfo = _pdfHdr.travelGas;
  // Bottom gas: use fractions directly for accurate trimix label
  const _pdfBotFracs  = getBottomGasFractions();
  if (!_pdfBotFracs) throw new Error('Invalid bottom gas configuration.');
  const _pdfBotLabel  = getGasLabel(_pdfBotFracs.fO2, _pdfBotFracs.fHe);
  const _pdfBotO2     = Math.round(_pdfBotFracs.fO2 * 100);
  const _pdfBotHe     = Math.round((_pdfBotFracs.fHe || 0) * 100);
  const _pdfBotN2     = Math.round(_pdfBotFracs.fN2 * 100);
  const _pdfIsTrimix  = _pdfBotHe > 0;
  const bottomGasVal  = _pdfIsTrimix
    ? `${_pdfBotLabel} (O2:${_pdfBotO2}% He:${_pdfBotHe}% N2:${_pdfBotN2}%)`
    : _pdfBotLabel;
  const totalsRowEl = document.querySelector('#decoTableBody tr[data-phase="totals"] td');
  const planSumPdf = getPlanSummaryExport(totalsRowEl);
  let decoTimeVal = planSumPdf.decoTime;
  let totalRTVal = planSumPdf.runTime;
  let ttsVal = planSumPdf.tts;
  let cnsVal = planSumPdf.cns;
  let otuVal = planSumPdf.otu;
  let prtVal = planSumPdf.prt;
  let decoZoneVal = planSumPdf.decozone;
  let decoStopVal = planSumPdf.decoStop;
  let surfGFVal = planSumPdf.surfGF || '-';
  const algoTag = decoModelSel==='ZHLC_GF'?`GF${mGF.low}-${mGF.high}_Buhlmann`:decoModelSel==='VPMB'?`C${cons}_VPM-B`:`GFHi${mGF.high}_C${cons}_VPM-B_GFS`;
  const fileName = `LSP_${getExportCircuitTag()}_${isoDate}_Deco_${depthVal}${du}_${btVal}min_${algoTag}.pdf`;
  const PW=210, PH=297, ML=14, MR=14, MT=10, MB=10, CW=182;
  let y=MT;

  const cleanPDF = cleanPdfText;
  function checkY(n) { if(y+n>PH-MB){ drawFooter(); doc.addPage(); y=MT; drawHeader(); } }
  function drawHeader() {
    doc.setFillColor(0,85,170); doc.rect(0,0,PW,8,'F');
    doc.setFontSize(8); doc.setFont('DejaVuSans','bold'); doc.setTextColor(255,255,255);
    doc.text(exportBrandWithCircuit(), ML, 5.5);
    doc.setFont('DejaVuSans','normal');
    doc.setFontSize(8);
    const hdrMid = `${btVal}min @ ${depthVal}${du} | ${bottomGasVal} | ${gfStr} | ${algo} | ${densityLabel}`;
    doc.text(hdrMid, PW/2, 5.5, {align:'center'});
    doc.setFontSize(8); doc.text(`${dateStr} ${timeStr}`, PW-MR, 5.5, {align:'right'});
    doc.setTextColor(0,0,0); y=MT;
  }
  function drawFooter() {
    doc.setFillColor(248,249,255); doc.rect(0,PH-6,PW,6,'F');
    doc.setFontSize(7); doc.setTextColor(100,100,120); doc.setFont('DejaVuSans','normal');
    doc.text('Planning Aid Only — Not a substitute for training, certification, or a dive computer · @threecats_lsp', ML, PH-2);
    doc.text(`${dateStr} ${timeStr}`, PW-MR, PH-2,{align:'right'});
    doc.setTextColor(0,0,0);
  }
  function sectionTitle(title, sub) {
    checkY(sub ? 14 : 12);
    let subLines = [];
    if (sub) {
      doc.setFont('DejaVuSans', 'normal');
      doc.setFontSize(7);
      subLines = doc.splitTextToSize(cleanPDF(sub), CW);
    }
    const subH = subLines.length ? 3.8 + subLines.length * 3.6 : 0;
    const boxH = (sub ? 5 + subH : 5);
    doc.setFillColor(232,240,255); doc.rect(ML-2,y,CW+4,boxH,'F');
    doc.setDrawColor(0,85,170); doc.setLineWidth(0.8); doc.line(ML-2,y,ML-2,y+boxH);
    doc.setFontSize(8); doc.setFont('DejaVuSans','bold'); doc.setTextColor(0,85,170);
    doc.text(cleanPDF(title), ML+1, y+4.8);
    if(subLines.length){
      doc.setFont('DejaVuSans','normal'); doc.setFontSize(7); doc.setTextColor(80,80,100);
      subLines.forEach((line, i) => doc.text(line, ML+1, y + 8.2 + i * 3.6));
    }
    doc.setTextColor(0,0,0); doc.setDrawColor(0,0,0); doc.setLineWidth(0.2); y += boxH + 4;
  }

  drawHeader();
  const _hasDecoPdf = (() => {
    const d = String(decoTimeVal || '');
    if (!d || d === '-') return false;
    if (/^0['"]|^0:00|^0 min/i.test(d)) return false;
    return true;
  })();
  y = drawDecoPlanBannerPdf(doc, y, { ML, CW, checkY, cleanPDF }, _pdfHdr, planSumPdf, _hasDecoPdf);
  y = drawPdfAlertBanners(doc, y, { ML, CW, checkY, cleanPDF });
  y += 3;

  const _dRate  = document.getElementById('descentRate')?.value || '22';
  const _aRate  = document.getElementById('ascentRate')?.value || '9';
  const _daRate = document.getElementById('decoAscentRate')?.value || '9';
  const _saRate = document.getElementById('surfaceAscentRate')?.value || '9';
  const _wv     = parseFloat(document.getElementById('waterVapor')?.value || '0.0627');
  const _wvL    = _wv <= 0.058 ? 'M' : 'B';
  const _rnd    = (document.getElementById('stopRounding')?.value || 'fractional') === 'wholeminute' ? 'Yes' : 'No';
  // Build trimix detail + travel gas + VPM extras for profile subtitle
  const _pdfBotDetail = _pdfIsTrimix ? `${_pdfBotLabel} (O2:${_pdfBotO2}% He:${_pdfBotHe}% N2:${_pdfBotN2}%)` : _pdfBotLabel;
  const _pdfTravelStr = _pdfTravelInfo ? `  Travel:${_pdfTravelInfo.gas} @ ${_pdfTravelInfo.depth}` : '';
  const _pdfRepStr    = _pdfRepActive ? `  Rep.dive SI:${_pdfSI}min` : '';
  const _pdfAltStr    = _pdfAltM > 0 ? `  Alt:${_pdfAltLbl}${_pdfRadii?` Radii x${_pdfRadii}`:''}` : '';
  const _pdfHeHtStr   = isVPM ? `  He t½:${_pdfHeHtLbl}` : '';
  const _pdfMdpEn  = document.getElementById('minDecoProfileEnable')?.value === 'yes';
  const _pdfMdp9m  = document.getElementById('minDeco9m')?.value || '1';
  const _pdfMdp6m  = document.getElementById('minDeco6m')?.value || '3';
  const _pdfMdpStr = _pdfMdpEn ? `  MinDeco:ON(9${du}:${_pdfMdp9m}' 6${du}:${_pdfMdp6m}')` : '';
  sectionTitle('DIVE PROFILE', `${depthVal}${du} / ${btVal}min / ${cleanPDF(_pdfBotDetail)} / ${gfStr}`);
  const _pdfTbl = _pdfDecoTableLayout(ML, CW);
  const { colW, colX, tblMl, tblCw } = _pdfTbl;
  checkY(7);
  _pdfDrawDecoTableHeader(doc, y, _pdfTbl, [0, 85, 170]);
  y += 6;
  document.querySelectorAll('#decoTableBody tr').forEach((tr,rowI)=>{
    const phase=tr.dataset.phase; if(!phase) return;
    const tds=Array.from(tr.querySelectorAll('td')); const c=tds.map(td=>cleanPDF(td.textContent.trim()));
    checkY(5.5);
    if(phase==='switch'){
      _pdfDrawSwitchRow(doc, y, _pdfTbl, tr, cleanPDF);
      y+=5; return;
    }
    if(phase==='totals'){
      const t = `Run: ${planSumPdf.runTime}  TTS: ${planSumPdf.tts}  Deco: ${planSumPdf.decoTime}  CNS: ${planSumPdf.cns}  OTU: ${planSumPdf.otu}  PrT: ${planSumPdf.prt}  Surf GF: ${planSumPdf.surfGF||'-'}  Decozone: ${planSumPdf.decozone}  First deco: ${planSumPdf.decoStop}`;
      const tLines = doc.splitTextToSize(cleanPDF(t), tblCw - 4);
      const tH = 4.2 * tLines.length + 1.5;
      checkY(tH);
      doc.setFillColor(240,244,255); doc.rect(tblMl,y,tblCw,tH,'F');
      doc.setFontSize(7); doc.setFont('DejaVuSans','bold'); doc.setTextColor(0,60,130);
      tLines.forEach((line, li) => doc.text(line, tblMl+2, y + 3.8 + li * 4.2));
      doc.setTextColor(0,0,0); y+=tH; return;
    }
    const sa=tr.getAttribute('style')||'';
    const hasCnsHi=tr.hasAttribute('data-cnshi');
    const hi100=hasCnsHi && (sa.includes('#ffff00')||(sa.includes('255,255,0')&&!sa.includes('0.25')));
    const hi80=hasCnsHi && (sa.includes('rgba(255,255,0')||sa.includes('255,255,0,0.25'));
    if(hi100) doc.setFillColor(255,255,0);
    else if(hi80) doc.setFillColor(255,252,180);
    else if(rowI%2===0) doc.setFillColor(248,249,255);
    else doc.setFillColor(255,255,255);
    doc.rect(tblMl,y,tblCw,5,'F');
    const isDeco=phase==='deco',isAsc=phase==='ascent',isBtm=phase==='bottom',isSafe=phase==='safety',isDes=phase==='descent';
    const txC=(hi100||hi80)?[150,0,0]:isDeco?[180,0,0]:isAsc?[30,130,60]:isBtm?[0,60,160]:isSafe?[20,140,50]:[160,50,50];
    const icon=isDeco?'Stp':isAsc?'Asc':isBtm?'Lvl':isSafe?'Stp':isDes?'Des':'---';
    doc.setFontSize(7); doc.setFont('DejaVuSans','normal');
    doc.setTextColor(...txC); _pdfDrawDecoPhaseLabel(doc, y, _pdfTbl, icon);
    _pdfDrawDecoTableCells(doc, y, _pdfTbl, c.slice(1, 9), txC);
    y+=5;
  });
  y+=3; checkY(7); doc.setFontSize(7); doc.setFont('DejaVuSans','normal');
  const leg=['Des = Descent','Lvl = Bottom','Asc = Ascent','Stp = Deco/Safety Stop','>> = Gas Switch'];
  const lc=[[80,80,80],[80,80,80],[80,80,80],[80,80,80],[80,80,80],[100,0,150]];
  let lx=tblMl; leg.forEach((l,i)=>{doc.setTextColor(...lc[i]);doc.text(l,lx,y+3.5);lx+=doc.getTextWidth(l)+5;});
  doc.setTextColor(0,0,0); y+=8;

  // DECO SLATE section — compact waterproof-slate format (same as SLATE modal)
  const _pdfSlate = buildSlateText();
  if (_incSlate && _pdfSlate) {
    checkY(14); sectionTitle('DECO SLATE','Compact waterproof-slate format');
    const _slLines = _pdfSlate.split('\n').slice(1); // drop title line (already in section header)
    doc.setFontSize(7.5); doc.setFont('DejaVuSans','normal'); doc.setTextColor(20,20,20);
    _slLines.forEach(l=>{ checkY(4.2); doc.text(cleanPDF(l)||' ', ML+2, y+3); y+=4.2; });
    doc.setTextColor(0,0,0); y+=4;
  }

  // HIGH CNS% alert if applicable
  const _cnsPctMain = cnsVal ? parseFloat(cnsVal) : 0;
  if (_cnsPctMain >= 80) {
    checkY(10);
    doc.setFillColor(255,255,0); doc.setDrawColor(180,180,0);
    const _cnsMsgM = `HIGH CNS%. CNS oxygen load ${_cnsPctMain.toFixed(0)}% exceeds 80%. Reduce deco gas ppO2, switch depth, or bottom time.`;
    const _cnsLinesM = doc.splitTextToSize(_cnsMsgM, CW-4);
    const _cnsHM = 5.5*_cnsLinesM.length+2;
    doc.roundedRect(ML,y,CW,_cnsHM,1.5,1.5,'FD');
    doc.setFontSize(7.5); doc.setFont('DejaVuSans','bold'); doc.setTextColor(17,17,17);
    doc.text(_cnsLinesM,ML+2,y+4);
    doc.setTextColor(0,0,0); y+=_cnsHM+4;
  }

  const gasConsEl=document.getElementById('gasConsumptionSummary');
  if(_incGas&&gasConsEl&&gasConsEl.style.display!=='none'){
    calcGasPlan();
    const _gpPDF=window._lastGasPlan;
    if(_gpPDF&&_gpPDF.rows&&_gpPDF.rows.length){
      doc.addPage(); drawHeader();
      const sacBot=document.getElementById('sacBottom')?.value||'20';
      const sacDec=document.getElementById('sacDeco')?.value||'15';
      const pdfPresU=units==='imperial'?'psi':'bar';
      const pdfRuleName=_gpPDF.rule==='half'?'Half Tank':'Thirds';
      sectionTitle('GAS CONSUMPTION',`${pdfRuleName} rule  •  SAC bottom: ${sacBot} ${_pdfSacUnit}  deco: ${sacDec} ${_pdfSacUnit}`);

      // ── Table header ──────────────────────────────────────────────────────
      // Column widths (sum = CW ~170mm)
      const gc={
        gas:   28, vol: 24, thirds: 20, turn: 24,
        suf:   46, margin: 28
      };
      const gx={
        gas: ML,
        vol: ML+gc.gas,
        thirds: ML+gc.gas+gc.vol,
        turn: ML+gc.gas+gc.vol+gc.thirds,
        suf:  ML+gc.gas+gc.vol+gc.thirds+gc.turn,
        margin: ML+gc.gas+gc.vol+gc.thirds+gc.turn+gc.suf
      };
      const hdrs=['GAS','TOTAL VOL','THIRDS','TURN PRESS','SUFFICIENT','MARGIN'];
      const hkeys=['gas','vol','thirds','turn','suf','margin'];
      const ROW_H=6.5, HDR_H=6;

      checkY(HDR_H + _gpPDF.rows.length*(ROW_H+1) + 20);

      // Header background
      doc.setFillColor(30,40,60);
      doc.rect(ML, y, Object.values(gc).reduce((a,b)=>a+b,0), HDR_H, 'F');
      doc.setFontSize(6); doc.setFont('DejaVuSans','bold'); doc.setTextColor(0,200,255);
      hdrs.forEach((h,i)=>{
        const k=hkeys[i];
        doc.text(h, gx[k]+gc[k]/2, y+4, {align:'center'});
      });
      y += HDR_H;

      // ── Data rows ──────────────────────────────────────────────────────────
      const ruleTxt = _gpPDF.rule==='half'?'1/2':'1/3';

      _gpPDF.rows.forEach((r, ri)=>{
        // Alternate row background
        ri%2===0 ? doc.setFillColor(245,247,252) : doc.setFillColor(255,255,255);
        doc.rect(ML, y, Object.values(gc).reduce((a,b)=>a+b,0), ROW_H, 'F');

        const lbl = cleanPDF(r.label);
        const isBottom = r.kind === 'bottom';
        const insufficient = isBottom ? (r.shortL!=null && r.shortL>0) : (r.reqL!=null && r.totalL < r.reqL);

        // ── GAS cell ──
        doc.setFontSize(7); doc.setFont('DejaVuSans','bold');
        doc.setTextColor(insufficient ? 180 : 40, insufficient ? 0 : 40, insufficient ? 0 : 40);
        doc.text(lbl, gx.gas+1, y+4.2);

        // ── TOTAL VOL ──
        const volCol = insufficient ? [180,0,0] : [0,120,60];
        doc.setFont('DejaVuSans','normal'); doc.setFontSize(6.5);
        doc.setTextColor(...volCol);
        doc.text(gpVolWithUnit(r.totalL), gx.vol+gc.vol/2, y+4.2, {align:'center'});

        // ── THIRDS (bottom only) ──
        if(isBottom && r.portionL!=null){
          doc.setTextColor(100,100,100);
          doc.text(gpVolWithUnit(r.portionL), gx.thirds+gc.thirds/2, y+4.2, {align:'center'});
        } else {
          doc.setTextColor(160,160,160);
          doc.text('—', gx.thirds+gc.thirds/2, y+4.2, {align:'center'});
        }

        // ── TURN PRESS (bottom only) ──
        if(isBottom && r.turnBar!=null && !insufficient){
          doc.setTextColor(0,150,200);
          doc.text(`${gpPresDisp(r.turnBar)} ${pdfPresU}`, gx.turn+gc.turn/2, y+4.2, {align:'center'});
        } else if(isBottom){
          doc.setTextColor(160,160,160);
          doc.text('—', gx.turn+gc.turn/2, y+4.2, {align:'center'});
        } else {
          doc.setTextColor(160,160,160);
          doc.text('one-way', gx.turn+gc.turn/2, y+4.2, {align:'center'});
        }

        // ── SUFFICIENT ──
        if(isBottom){
          if(insufficient){
            doc.setFont('DejaVuSans','bold'); doc.setTextColor(180,0,0);
            doc.text(`SHORT ${gpVolWithUnit(r.shortL)}`, gx.suf+1, y+2.8);
            if(r.maxBTmin!=null){
              doc.setFont('DejaVuSans','normal'); doc.setFontSize(5.5); doc.setTextColor(140,0,0);
              doc.text(`BT→${r.maxBTmin}min, turn ${gpPresDisp(r.maxTurnBar)}${pdfPresU}`, gx.suf+1, y+5.8);
            }
          } else {
            doc.setFont('DejaVuSans','normal'); doc.setTextColor(0,130,60);
            doc.text(`turn ${gpPresDisp(r.turnBar)}${pdfPresU}  OK ${gpVolWithUnit(r.reqL)}`, gx.suf+1, y+4.2);
          }
        } else {
          if(r.reqL==null){
            doc.setFont('DejaVuSans','normal'); doc.setTextColor(160,160,160);
            doc.text('run plan first', gx.suf+1, y+4.2);
          } else {
            const stat3sym = r.totalL>=r.reqL*1.10?'✓':r.totalL>=r.reqL?'⚠':'✗';
            const stat3txt = r.totalL>=r.reqL*1.10?' OK':r.totalL>=r.reqL?' TIGHT':' SHORT';
            const tc3 = r.totalL>=r.reqL*1.10?[0,130,60]:r.totalL>=r.reqL?[180,80,0]:[180,0,0];
            doc.setFont('DejaVuSans','bold'); doc.setTextColor(...tc3);
            doc.text(stat3sym+stat3txt, gx.suf+1, y+2.8);
            doc.setFont('DejaVuSans','normal'); doc.setFontSize(5.5); doc.setTextColor(100,100,100);
            doc.text(`need ${gpVolWithUnit(r.reqL)}`, gx.suf+1, y+5.8);
          }
        }

        // ── MARGIN ──
        doc.setFontSize(6.5);
        if(isBottom && r.reqL!=null){
          const mg = r.totalL - r.reqL;
          const mgCol = mg >= 0 ? [0,130,60] : [180,0,0];
          doc.setFont('DejaVuSans','bold'); doc.setTextColor(...mgCol);
          doc.text(`${mg>=0?'+':''}${gpVolWithUnit(mg)}`, gx.margin+gc.margin/2, y+4.2, {align:'center'});
        } else if(!isBottom && r.reqL!=null){
          const mg3 = r.totalL - r.reqL;
          const mgCol3 = mg3 >= 0 ? [0,130,60] : [180,0,0];
          doc.setFont('DejaVuSans','bold'); doc.setTextColor(...mgCol3);
          doc.text(`${mg3>=0?'+':''}${gpVolWithUnit(mg3)}`, gx.margin+gc.margin/2, y+4.2, {align:'center'});
        } else {
          doc.setTextColor(160,160,160);
          doc.text('—', gx.margin+gc.margin/2, y+4.2, {align:'center'});
        }

        // Row border
        doc.setDrawColor(210,215,225); doc.setFont('DejaVuSans','normal'); doc.setFontSize(7);
        doc.line(ML, y+ROW_H, ML+Object.values(gc).reduce((a,b)=>a+b,0), y+ROW_H);
        y += ROW_H;
      });
      const reserveNote = typeof gpSafetyReserveNoteText === 'function' ? gpSafetyReserveNoteText() : '';
      if (reserveNote) {
        checkY(5);
        doc.setFontSize(7); doc.setFont('DejaVuSans','normal'); doc.setTextColor(90, 90, 110);
        doc.text(cleanPDF(reserveNote), ML, y + 3.5);
        y += 5;
      }
      y += 4;
    }
  }

  if(_incProfile) _drawForPDF(() => drawDecoProfileFull());
  const pc=document.getElementById('plannerProfileCanvas');
  if(_incProfile&&pc){
    doc.addPage(); drawHeader();
    sectionTitle('DIVE PROFILE GRAPH',`${depthVal}${du} / ${btVal}min / ${algo} / ${gfStr}`);
    const _pcCap=_canvasToDataURLForPDF(pc,CW); const id=_pcCap.dataURL; const ih=CW*pc.height/pc.width;
    checkY(ih); doc.addImage(id,'PNG',ML,y,CW,ih); y+=ih+4;
    y = drawGraphLegend(doc, y, ML, CW, checkY);
  }

  if(!isVPM){
    if(_incGFCurve) _drawForPDF(() => drawGFCurve());
    if(_incGFCurve){
    doc.addPage(); drawHeader();
    const gc=document.getElementById('gfCurveCanvas');
    if(gc){
      checkY(60); sectionTitle('GRADIENT FACTOR CURVE',`GF Low ${mGF.low}%  GF High ${mGF.high}%`);
      const _gcCap=_canvasToDataURLForPDF(gc,CW); const gd=_gcCap.dataURL; const gh=CW*gc.height/gc.width;
      doc.addImage(gd,'PNG',ML,y,CW,gh); y+=gh+4;
      // GF curve legend — same numbered stops as web view
      const gfLegEl=document.getElementById('gfCurveLegend');
      const gfRows=gfLegEl?Array.from(gfLegEl.querySelectorAll('tbody tr')):[];
      if(gfRows.length){
        checkY(gfRows.length*5+10);
        doc.setFillColor(240,244,255); doc.rect(ML,y,CW,5.5,'F');
        doc.setFontSize(6.5); doc.setFont('DejaVuSans','bold'); doc.setTextColor(80,80,120);
        const gcw=[8,80,30,24]; const gcx=[ML,ML+8,ML+88,ML+118];
        ['#','Stop','Run','ppO2'].forEach((h,i)=>doc.text(h,gcx[i]+gcw[i]/2,y+3.8,{align:'center'}));
        doc.setTextColor(0,0,0); y+=5.5;
        gfRows.forEach((tr,ri)=>{
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
          doc.setTextColor(180,0,0); doc.text(num,gcx[0]+gcw[0]/2,y+3.5,{align:'center'});
          doc.setTextColor(60,60,60); doc.text(stop,gcx[1]+2,y+3.5);
          doc.setTextColor(80,80,80); doc.text(run,gcx[2]+gcw[2],y+3.5,{align:'right'});
          doc.setTextColor(...tc); doc.text(ppo,gcx[3]+gcw[3],y+3.5,{align:'right'});
          doc.setTextColor(0,0,0); y+=5;
        });
        y+=4;
      }
    }
    } // end if(_incGFCurve)
    if(_incTissue){
      // Ensure tissue data is populated
      const ttb=document.getElementById('tissueTableBody');
      if(ttb&&ttb.rows.length===0&&lastTissues) updateTissueViz(lastTissues, mGF.high);

      if(lastTissues&&lastTissues.length){
        doc.addPage(); drawHeader();
        sectionTitle('TISSUE SATURATION — SURFACE SNAPSHOT','Bühlmann ZH-L16C · GF High applied · end-of-dive compartment loading');

        // ── Section 1: Surface Saturation bars ──
        const gfF = mGF.high/100;
        const BAR_X=ML+28, BAR_W=CW-52, BAR_H=5, ROW=6.5;
        // Column headers
        checkY(7);
        doc.setFontSize(6); doc.setFont('DejaVuSans','bold'); doc.setTextColor(100,100,140);
        doc.text('#',   ML+2,  y+4);
        doc.text('t½',  ML+14, y+4);
        doc.text('Saturation vs GF-adjusted M-value at surface', BAR_X+2, y+4);
        doc.text('%',   ML+CW-3, y+4, {align:'right'});
        doc.setTextColor(0,0,0); y+=6;

        lastTissues.forEach((t0pdf,i)=>{
          const pN2pdf=t0pdf.pN2; const pHepdf=t0pdf.pHe||0; const pTotpdf=pN2pdf+pHepdf;
          checkY(ROW);
          const [ht,a_n2pdf,b_n2pdf]=ZHL16C[i];
          let a=a_n2pdf, b=b_n2pdf;
          if(pHepdf>0&&pTotpdf>0){
            a=(pN2pdf*a_n2pdf+pHepdf*ZHL16C_HE_AB[i][0])/pTotpdf;
            b=(pN2pdf*b_n2pdf+pHepdf*ZHL16C_HE_AB[i][1])/pTotpdf;
          }
          const mv = gfAdjustedMValue(a, b, altSurfaceP, gfF);
          const pct=Math.min(100,Math.round((pTotpdf/mv)*100));
          const cr=lspSatRgb(pct);
          // Labels
          doc.setFontSize(6.5); doc.setFont('DejaVuSans','normal'); doc.setTextColor(100,100,120);
          doc.text(`${i+1}`, ML+4, y+4, {align:'center'});
          doc.text(`${ht}`, ML+18, y+4, {align:'center'});
          // Bar bg
          doc.setFillColor(220,222,235); doc.roundedRect(BAR_X,y+0.5,BAR_W,BAR_H,1,1,'F');
          // Bar fill
          doc.setFillColor(...cr); doc.roundedRect(BAR_X,y+0.5,BAR_W*pct/100,BAR_H,1,1,'F');
          // Pct
          doc.setFontSize(6.5); doc.setTextColor(...cr); doc.setFont('DejaVuSans','bold');
          doc.text(`${pct}%`, ML+CW-2, y+4, {align:'right'});
          doc.setTextColor(0,0,0); y+=ROW;
        });

        // Color legend
        y+=2; checkY(5);
        y = drawTissueSatLegend(doc, y, ML);

        // ── Section 2: Compartment Detail table ──
        checkY(12);
        doc.setFillColor(220,228,248); doc.rect(ML,y,CW,5,'F');
        doc.setFontSize(7); doc.setFont('DejaVuSans','bold'); doc.setTextColor(30,50,120);
        doc.text('COMPARTMENT DETAIL', ML+2, y+3.5);
        doc.setFontSize(6); doc.setFont('DejaVuSans','normal'); doc.setTextColor(80,90,130);
        doc.text('exact N₂/He loads, M-values, and saturation status at surfacing', ML+CW-2, y+3.5, {align:'right'});
        doc.setTextColor(0,0,0); y+=6;

        const th2=['#','t½ (min)','N₂+He (bar)','M-val (bar)','Sat %','Status'];
        const tw=[8,22,30,28,22,28]; const tx2=[ML]; tw.forEach((w,i)=>{if(i<tw.length-1)tx2.push(tx2[i]+tw[i]);});
        checkY(6);
        doc.setFillColor(0,85,170); doc.rect(ML,y,CW,5.5,'F');
        doc.setFontSize(6.5); doc.setFont('DejaVuSans','bold'); doc.setTextColor(255,255,255);
        th2.forEach((h,i)=>doc.text(h, tx2[i]+tw[i]/2, y+3.8, {align:'center'}));
        doc.setTextColor(0,0,0); y+=5.5;

        lastTissues.forEach((t0pdf,i)=>{
          checkY(5);
          const pN2pdf=t0pdf.pN2; const pHepdf=t0pdf.pHe||0; const pTotpdf=pN2pdf+pHepdf;
          const [ht,a_n2pdf,b_n2pdf]=ZHL16C[i];
          let a=a_n2pdf, b=b_n2pdf;
          if(pHepdf>0&&pTotpdf>0){
            a=(pN2pdf*a_n2pdf+pHepdf*ZHL16C_HE_AB[i][0])/pTotpdf;
            b=(pN2pdf*b_n2pdf+pHepdf*ZHL16C_HE_AB[i][1])/pTotpdf;
          }
          const mv = gfAdjustedMValue(a, b, altSurfaceP, gfF);
          const pct=Math.min(100,Math.round((pTotpdf/mv)*100));
          const cr=lspSatRgb(pct);
          const status=lspSatStatus(pct).status;
          const loadStr=pHepdf>0?`${pTotpdf.toFixed(3)} (${pN2pdf.toFixed(2)}+${pHepdf.toFixed(2)})`:pTotpdf.toFixed(3);
          i%2===0?doc.setFillColor(248,249,255):doc.setFillColor(255,255,255);
          doc.rect(ML,y,CW,5,'F');
          doc.setFontSize(6.5); doc.setFont('DejaVuSans','normal');
          doc.setTextColor(80,80,100); doc.text(`${i+1}`,      tx2[0]+tw[0]/2, y+3.5, {align:'center'});
          doc.setTextColor(80,80,100); doc.text(`${ht}`,        tx2[1]+tw[1]/2, y+3.5, {align:'center'});
          doc.setTextColor(60,60,100); doc.text(loadStr,        tx2[2]+1,       y+3.5);
          doc.setTextColor(60,60,100); doc.text(mv.toFixed(3),  tx2[3]+tw[3]/2, y+3.5, {align:'center'});
          doc.setFont('DejaVuSans','bold'); doc.setTextColor(...cr);
          doc.text(`${pct}%`,  tx2[4]+tw[4]/2, y+3.5, {align:'center'});
          doc.text(status,     tx2[5]+tw[5]/2, y+3.5, {align:'center'});
          doc.setTextColor(0,0,0); y+=5;
        });
        y+=4;

        // ── Section 3: Per-Stop Saturation ──
        const lp=window._lastPlan;
        if(lp&&lp.steps){
          const decoSteps=lp.steps.filter(s=>(s.type==='deco'||s.type==='safety')&&s._tissues&&s._tissues.length===16);
          if(decoSteps.length>0){
            doc.addPage(); drawHeader();
            sectionTitle('TISSUE SATURATION — PER-STOP ASCENT PROFILE','Each column = one deco stop · each row = one compartment · bars = tension / GF-adjusted M-value at stop depth');

            const dU=units==='metric'; const conv=dU?1:3.28084; const uLbl=dU?'m':'ft';
            const gfApplied=mGF.high/100;
            const nStops=decoSteps.length;

            // Layout: comp col + t½ col + one col per stop
            const COMP_W=10, HT_W=14;
            const stopColW=Math.min(16, Math.floor((CW-COMP_W-HT_W)/nStops));
            const totalW=COMP_W+HT_W+stopColW*nStops;
            const startX=ML+(CW-totalW)/2; // center the table

            // Header row — stop depths
            checkY(12);
            doc.setFontSize(5.5); doc.setFont('DejaVuSans','bold');
            doc.setFillColor(20,30,60); doc.rect(startX,y,totalW,10,'F');
            doc.setTextColor(150,180,220);
            doc.text('C#',  startX+COMP_W/2, y+4, {align:'center'});
            doc.text('t½',  startX+COMP_W+HT_W/2, y+4, {align:'center'});
            decoSteps.forEach((s,si)=>{
              const cx=startX+COMP_W+HT_W+si*stopColW;
              const depthD=Math.round(s.depth*conv);
              const stopM=s.dur>=1?Math.round(s.dur)+"'":'<1\'';
              doc.setTextColor(0,200,255);
              doc.text(`${depthD}${uLbl}`, cx+stopColW/2, y+3.5, {align:'center'});
              doc.setTextColor(120,150,180);
              doc.text(stopM, cx+stopColW/2, y+8, {align:'center'});
            });
            doc.setTextColor(0,0,0); y+=11;

            // One row per compartment
            const CROW=7.5;
            for(let i=0;i<16;i++){
              checkY(CROW);
              const [htN2,a_n2r,b_n2r]=ZHL16C[i];
              i%2===0?doc.setFillColor(245,247,252):doc.setFillColor(252,252,255);
              doc.rect(startX,y,totalW,CROW,'F');
              // Comp # and half-time
              doc.setFontSize(6); doc.setFont('DejaVuSans','normal');
              doc.setTextColor(100,110,140);
              doc.text(`C${i+1}`, startX+COMP_W/2, y+4.5, {align:'center'});
              doc.text(`${htN2}`, startX+COMP_W+HT_W/2, y+4.5, {align:'center'});
              // Bar per stop
              decoSteps.forEach((s,si)=>{
                const t=s._tissues[i];
                const pN2r=t.pN2||0; const pHer=t.pHe||0; const pTr=pN2r+pHer;
                const pAmb=altSurfaceP+s.depth * BAR_PER_METRE;
                let ar=a_n2r, br=b_n2r;
                if(pTr>0&&pHer>0){
                  const wN2=pN2r/pTr, wHe=pHer/pTr;
                  ar=wN2*a_n2r+wHe*ZHL16C_HE_AB[i][0];
                  br=wN2*b_n2r+wHe*ZHL16C_HE_AB[i][1];
                }
                const mValR = gfAdjustedMValue(ar, br, pAmb, gfApplied);
                const pctR=mValR>0?Math.round((pTr/mValR)*100):0;
                const clampR=Math.max(0,Math.min(120,pctR));
                const barPctR=Math.min(100,clampR);
                const crR=lspSatRgb(clampR);
                const cx=startX+COMP_W+HT_W+si*stopColW;
                const bx=cx+1, bw=stopColW-2, bh=4;
                // Bar bg
                doc.setFillColor(210,215,230); doc.roundedRect(bx,y+0.8,bw,bh,0.8,0.8,'F');
                // Bar fill
                if(barPctR>0){ doc.setFillColor(...crR); doc.roundedRect(bx,y+0.8,bw*barPctR/100,bh,0.8,0.8,'F'); }
                // Pct label
                doc.setFontSize(5); doc.setTextColor(...crR); doc.setFont('DejaVuSans','bold');
                doc.text(`${clampR}%`, cx+stopColW/2, y+6.8, {align:'center'});
              });
              doc.setTextColor(0,0,0); y+=CROW;
            }
            // Legend
            y+=3; checkY(5);
            y = drawTissueSatLegend(doc, y, ML);
          }
        }
      }
    } // end if(_incTissue)
  } else {
    if(_incTissue||_incGFCurve){
    checkY(12);
    sectionTitle('TISSUE SATURATION & GF CURVE',`N/A for ${algo} - Buhlmann ZH-L16C only`);
    doc.setFontSize(8);doc.setTextColor(100,100,120);
    doc.text('Tissue saturation and gradient factor analysis require Bühlmann ZH-L16C algorithm.',ML,y+4);
    doc.setTextColor(0,0,0);y+=9;
    } // end if(_incTissue||_incGFCurve)
  }

  // Emergency plan intentionally excluded from main deco PDF.
  // Use the dedicated Emergency Plan PDF button for that.
  if(false){
    const colX = [ML, ML + 12, ML + 30, ML + 48, ML + 66, ML + 84, ML + 102, ML + 120, ML + 138, ML + 156];
    const colW = [12, 18, 18, 18, 18, 18, 18, 18, 18, 18];
    doc.addPage(); drawHeader();
    const cc=window._lastContingency;
    doc.setFillColor(255,240,240);doc.setDrawColor(200,100,100);
    doc.roundedRect(ML,y,CW,18,2,2,'FD');
    doc.setFontSize(11);doc.setFont('DejaVuSans','bold');doc.setTextColor(180,30,30);
    doc.text('EMERGENCY PLAN: '+cc.label,ML+3,y+6);
    doc.setFontSize(8);doc.setFont('DejaVuSans','normal');doc.setTextColor(100,0,0);
    doc.text(`Run: ${cc.lastRunFmt||cc.lastRun+"'00\""} | TTS: ${cc.tts||'—'} | Deco: ${cc.decoTimeFmt||cc.decoTime+"'00\""} | CNS: ${cc.totalCNS||'—'} | OTU: ${cc.totalOTU||'—'} | PrT: ${cc.totalPrT||'—'} | Decozone: ${cc.decozoneDisp||formatDecoZoneStart(cc.decoZoneStart)} | First deco: ${cc.decoStop||'—'}`,ML+3,y+11);
    doc.setTextColor(150,0,0);doc.text(cc.msg||'',ML+3,y+15.5);
    doc.setTextColor(0,0,0);y+=22;
    sectionTitle('EMERGENCY ASCENT SCHEDULE', cc.label);
    doc.setFillColor(180,30,30);doc.rect(ML,y,CW,6,'F');
    doc.setFontSize(7);doc.setFont('DejaVuSans','bold');doc.setTextColor(255,255,255);
    ['Phase','Depth','Stop','Run','TTS','Mix','EAD','END','PPO2','CNS%'].forEach((h,i)=>doc.text(h,colX[i]+colW[i]/2,y+4,{align:'center'}));
    doc.setTextColor(0,0,0);y+=6;
    document.querySelectorAll('#contingencyResult .deco-table tbody tr').forEach((tr,ri)=>{
      const ph=tr.dataset.phase; const tds2=Array.from(tr.querySelectorAll('td')); const cv=tds2.map(td=>td.textContent.trim());
      checkY(5.5);
      if(ph==='switch'){const t=tds2.slice(1).map(td=>td.textContent.trim()).filter(Boolean).join(' ');doc.setDrawColor(0,122,51);doc.setLineWidth(1);doc.line(ML,y,ML+CW,y);doc.setFillColor(255,215,0);doc.rect(ML,y,CW,5,'F');doc.line(ML,y+5,ML+CW,y+5);doc.setFontSize(7);doc.setFont('DejaVuSans','bold');doc.setTextColor(0,100,40);doc.text('>> '+cleanPDF(t),ML+2,y+3.5);doc.setTextColor(0,0,0);doc.setLineWidth(0.2);y+=5;return;}
      if(ph==='totals'){const sps=tds2[0]?.querySelectorAll('span')||[];let t='';sps.forEach(s=>{const v=s.textContent.trim();if(v)t+=(t?'  ':'')+v;});if(!t&&tds2[0])t=tds2[0].textContent.replace(/\s+/g,' ').trim();doc.setFillColor(255,240,240);doc.rect(ML,y,CW,5.5,'F');doc.setFontSize(7);doc.setFont('DejaVuSans','bold');doc.setTextColor(150,0,0);doc.text(t,ML+2,y+3.8);doc.setTextColor(0,0,0);y+=5.5;return;}
      const id2=ph==='deco',ia=ph==='ascent',ib=ph==='bottom',is2=ph==='safety',id3=ph==='descent';
      ri%2===0?doc.setFillColor(255,250,250):doc.setFillColor(255,255,255);doc.rect(ML,y,CW,5,'F');
      const tc=id2?[180,0,0]:ia?[30,130,60]:ib?[0,60,160]:is2?[20,140,50]:[160,50,50];
      const ic=id2?'●':ia?'↑':ib?'●':is2?'●':id3?'↓':'·';
      doc.setFontSize(7);doc.setFont('DejaVuSans','normal');doc.setTextColor(...tc);doc.text(ic,colX[0]+colW[0]/2,y+3.5,{align:'center'});
      [cv[1],cv[2],cv[3],cv[4],cv[5],cv[6],cv[7],cv[8],cv[9]].forEach((v,i)=>{if(v&&v!=='-'&&v!=='—')doc.text(v,colX[i+1]+colW[i+1]/2,y+3.5,{align:'center'});});
      doc.setTextColor(0,0,0);y+=5;
    });
  }

  const tp=doc.getNumberOfPages(); for(let p=1;p<=tp;p++){doc.setPage(p);drawFooter();}
  doc.save(fileName);
  showExportToast();
}

// LSP-EXPORT-ENGINE:CONTINGENCY-PDF
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

  const cleanPDF = cleanPdfText;
  function checkY(n) { if(y+n>PH-MB){ drawFooter(); doc.addPage(); y=MT; drawHeader(); } }
  function drawHeader() {
    doc.setFillColor(180,30,30); doc.rect(0,0,PW,8,'F');
    doc.setFontSize(8); doc.setFont('DejaVuSans','bold'); doc.setTextColor(255,255,255);
    doc.text('⚠ EMERGENCY PLAN', ML, 5.5);
    doc.setFont('DejaVuSans','normal'); doc.setFontSize(8);
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
      const phase=normalizeSchedulePhase(tr.dataset.phase);
      if (!phase || phase === 'info') return;
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
    try {
      withScratchDecoTableBody(() => {
        _drawForPDF(() => drawDecoProfileFull());
        const pc = document.getElementById('plannerProfileCanvas');
        if (pc) {
          doc.addPage(); drawHeader();
          sectionTitle('EMERGENCY DIVE PROFILE GRAPH', `${depth}${du} / ${bt}min / ${cleanPDF(c.label)}`);
          const _pcCapture = _canvasToDataURLForPDF(pc, CW);
          const imgH = CW * pc.height / pc.width;
          doc.addImage(_pcCapture.dataURL,'PNG',ML,y,CW,imgH);
          y += imgH+4;
          y = drawGraphLegend(doc, y, ML, CW, checkY, buildProfileLegendRowsFromWaypoints());
        }
      }, c.newRows);
    } catch(e) { console.warn('Emergency graph failed',e); }
    finally { drawDecoProfile(); drawDecoProfileFull(); }
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

  const emTissues = c.contLastTissues;
  const emPlan = c.contLastPlan;

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
      const cr=lspSatRgb(pct);
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
    const ttbEm = document.getElementById('tissueTableBody');
    const savedTissueHtml = ttbEm ? ttbEm.innerHTML : '';
    try {
      if (ttbEm && ttbEm.rows.length === 0 && emTissues) updateTissueViz(emTissues, mGF.high);
      if (ttbEm && ttbEm.rows.length) {
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
          const cr=lspSatRgb(pct);
          ri%2===0?doc.setFillColor(255,250,250):doc.setFillColor(255,255,255);
          doc.rect(ML,y,CW,5,'F');
          doc.setFontSize(7);doc.setFont('DejaVuSans','normal');doc.setTextColor(...cr);
          cells.forEach((v,i)=>doc.text(cleanPDF(v),tx3[i]+tw3[i]/2,y+3.5,{align:'center'}));
          doc.setTextColor(0,0,0);y+=5;
        });
        y+=4;
      }
    } finally {
      if (ttbEm) ttbEm.innerHTML = savedTissueHtml;
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
          const tc2=lspSatRgb(Math.round(pT*100));
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
    if (emAlertHtml) {
      y = drawPdfAlertBanners(doc, y, { ML, CW, checkY, cleanPDF }, emAlertHtml);
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

// LSP-EXPORT-ENGINE:GAS-PLAN-PDF
async function buildGasPlanPDF() {
  if (!window.jspdf || !window.jspdf.jsPDF) { alert('PDF library not loaded.'); return; }
  const { jsPDF } = window.jspdf;
  calcGasPlan();
  const gp = window._lastGasPlan;
  if (!gp || !gp.rows.length) { alert('Configure a bottom gas cylinder first.'); return; }

  const doc = new jsPDF({ unit:'mm', format:'a4', orientation:'portrait' });
  if (!(await ensurePDFFontsForPDF(doc))) return;
  const now = new Date();
  const dateStr = now.toLocaleDateString('en-GB', { day:'2-digit', month:'short', year:'numeric' });
  const timeStr = now.toLocaleTimeString('en-GB', { hour:'2-digit', minute:'2-digit' });
  const isoDate = now.toISOString().split('T')[0];
  const volU  = lspVolUnit();
  const presU = units === 'imperial' ? 'psi'   : 'bar';
  const ruleName = gp.rule === 'half' ? 'Half Tank' : 'Rule of Thirds';

  const PW=210, PH=297, ML=14, MR=14, MT=10, MB=10, CW=182;
  let y=MT;
  const cleanPDF = cleanPdfText;
  function drawHeader() {
    doc.setFillColor(0,90,140); doc.rect(0,0,PW,8,'F');
    doc.setFontSize(8); doc.setFont('DejaVuSans','bold'); doc.setTextColor(255,255,255);
    doc.text('LSP D-PLANNER + CCR - GAS PLAN', ML, 5.5);
    doc.setFont('DejaVuSans','normal');
    doc.text(ruleName, PW/2, 5.5, {align:'center'});
    doc.text(`${dateStr} ${timeStr}`, PW-MR, 5.5, {align:'right'});
    doc.setTextColor(0,0,0); y=MT;
  }
  function drawFooter() {
    doc.setFillColor(245,250,255); doc.rect(0,PH-6,PW,6,'F');
    doc.setFontSize(7); doc.setTextColor(100,100,120); doc.setFont('DejaVuSans','normal');
    doc.text('Planning Aid Only — Not a substitute for training, certification, or a dive computer · @threecats_lsp', ML, PH-2);
    doc.text(`${dateStr} ${timeStr}`, PW-MR, PH-2, {align:'right'});
    doc.setTextColor(0,0,0);
  }
  function checkY(n){ if(y+n>PH-MB){ drawFooter(); doc.addPage(); y=MT; drawHeader(); } }

  drawHeader();

  // Info box
  doc.setFillColor(240,248,255); doc.setDrawColor(150,200,230);
  doc.roundedRect(ML,y,CW,12,2,2,'FD');
  doc.setFontSize(10); doc.setFont('DejaVuSans','bold'); doc.setTextColor(0,90,140);
  doc.text(`Gas Rule: ${ruleName}`, ML+3, y+5);
  doc.setFontSize(8); doc.setFont('DejaVuSans','normal'); doc.setTextColor(80,80,100);
  doc.text(`Units: ${units === 'imperial' ? 'Imperial (ft3 / psi)' : 'Metric (L / bar)'}`, ML+3, y+9.5);
  doc.setTextColor(0,0,0); y+=16;

  // Table header
  const headers=['GAS','TOTAL VOL','THIRDS','TURN PRESS','SUFFICIENT'];
  const colW=[40,30,34,28,50];
  const colX=[ML]; colW.forEach((w,i)=>{ if(i<colW.length-1) colX.push(colX[i]+colW[i]); });
  doc.setFillColor(0,90,140); doc.rect(ML,y,CW,6,'F');
  doc.setFontSize(7); doc.setFont('DejaVuSans','bold'); doc.setTextColor(255,255,255);
  headers.forEach((h,i)=>doc.text(h,colX[i]+colW[i]/2,y+4,{align:'center'}));
  doc.setTextColor(0,0,0); y+=6;

  gp.rows.forEach((r,rowI)=>{
    checkY(6);
    if(rowI%2===0) doc.setFillColor(245,250,255); else doc.setFillColor(255,255,255);
    doc.rect(ML,y,CW,5.5,'F');
    doc.setFontSize(7); doc.setFont('DejaVuSans','normal'); doc.setTextColor(0,0,0);
    let cells;
    if(r.kind==='bottom'){
      const ruleTxt = gp.rule === 'half' ? '1/2' : '1/3';
      const isShort = r.shortL != null && r.shortL > 0;
      cells=[
        r.label,
        gpVolWithUnit(r.totalL),
        isShort ? `need ${gpVolWithUnit(r.reqL)}` : `${gpVolWithUnit(r.portionL)} (${ruleTxt})`,
        isShort ? `(${ruleTxt} rule)` : `${gpPresDisp(r.turnBar)} ${presU}`,
        isShort ? `SHORT ${gpVolWithUnit(r.shortL)}` : 'TURN',
      ];
      // Extra BT suggestion row if short
      if(isShort && r.maxBTmin != null){
        cells.forEach((c,i)=>{ doc.text(cleanPDF(c),colX[i]+colW[i]/2,y+3.6,{align:'center'}); });
        y+=5.5; checkY(5.5);
        doc.setFillColor(255,68,51); doc.rect(ML,y,CW,5.5,'F');
        doc.setTextColor(255,255,255); doc.setFont('DejaVuSans','bold');
        doc.text(cleanPDF(`BT suggestion: max ${r.maxBTmin} min, turn at ${gpPresDisp(r.maxTurnBar)} ${presU} -- or use a larger cylinder`), ML+2, y+3.6);
        doc.setFont('DejaVuSans','normal'); doc.setTextColor(0,0,0);
        y+=5.5;
        return; // already wrote the row manually
      }
    } else {
      let status;
      if(r.reqL==null) status='RUN PLAN';
      else if(r.totalL>=r.reqL*GP_ONEWAY_MARGIN) status='OK';
      else if(r.totalL>=r.reqL) status='TIGHT';
      else status='SHORT';
      cells=[
        r.label,
        gpVolWithUnit(r.totalL),
        r.reqL==null?'req --':`req ${gpVolWithUnit(r.reqL)}`,
        'one-way',
        status,
      ];
    }
    cells.forEach((c,i)=>{
      const cv=cleanPDF(c);
      doc.text(cv,colX[i]+colW[i]/2,y+3.6,{align:'center'});
    });
    y+=5.5;
  });
  y+=4;

  const reserveNote = gpSafetyReserveNoteText();
  if (reserveNote) {
    checkY(5);
    doc.setFontSize(7); doc.setFont('DejaVuSans','normal'); doc.setTextColor(90,90,110);
    doc.text(cleanPDF(reserveNote), ML, y+3.5);
    y += 5;
  }

  // Text summary block
  checkY(10);
  doc.setFontSize(7); doc.setFont('DejaVuSans','normal'); doc.setTextColor(90,90,110);
  const summary = (buildGasPlanText()||'').split('\n').filter(l=>l && !/^[═]+$/.test(l));
  summary.forEach(line=>{
    checkY(4.2);
    doc.text(cleanPDF(line), ML, y+3); y+=4.2;
  });

  drawFooter();
  const fileName = `LSP_${getExportCircuitTag()}_${isoDate}_GasPlan_${gp.rule}.pdf`;
  doc.save(fileName);
  showExportToast();
}

