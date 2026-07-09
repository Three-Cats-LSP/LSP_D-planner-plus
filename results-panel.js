/**
 * Results panel shell — metrics, chips, tabs, schedule table decoration.
 * Globals read: units, plannerAlgo, renderSurfIntPanel, updateSliderFill, calcSurfInt,
 *   calcAvgDepth, renderNDLTable, buildDiveBlocks
 * Globals written: (DOM only)
 */
/** Optional V4 tab variant: split Profile vs Schedule (default combined profile tab). */
window.LSP_V4_SPLIT_PROFILE_SCHEDULE = false;

const _PHASE_ICON_SVG = {
  descent: '<span class="ph ph-descent" aria-hidden="true"><svg width="12" height="14" viewBox="0 0 12 14" fill="none"><path d="M6 1v10M2 9l4 4 4-4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></span>',
  bottom: '<span class="ph ph-bottom" aria-hidden="true"><svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor"><circle cx="6" cy="6" r="5"/></svg></span>',
  ascent: '<span class="ph ph-ascent" aria-hidden="true"><svg width="12" height="14" viewBox="0 0 12 14" fill="none"><path d="M6 13V3M2 5l4-4 4 4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></span>',
  surface: '<span class="ph ph-surface" aria-hidden="true"><svg width="12" height="14" viewBox="0 0 12 14" fill="none"><path d="M6 13V3M2 5l4-4 4 4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></span>',
  deco: '<span class="ph ph-deco" aria-hidden="true"><svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor"><circle cx="5" cy="5" r="4"/></svg></span>',
  safety: '<span class="ph ph-deco" aria-hidden="true"><svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor"><circle cx="5" cy="5" r="4"/></svg></span>',
  switch: '<span class="ph ph-switch" aria-hidden="true"><svg width="14" height="10" viewBox="0 0 14 10" fill="none"><path d="M1 3h12M10 1l3 2-3 2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/><path d="M13 7H1M4 5l-3 2 3 2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg></span>',
};
function buildScheduleLegendHtml() {
  return `<div class="deco-table-legend legend">
<span class="legend-item"><svg class="leg-icon" width="12" height="14" viewBox="0 0 12 14" fill="none"><path d="M6 1v10M2 9l4 4 4-4" stroke="var(--red)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg> Descent</span>
<span class="legend-item"><span class="leg-dot" style="background:var(--accent)"></span> Bottom</span>
<span class="legend-item"><svg class="leg-icon" width="12" height="14" viewBox="0 0 12 14" fill="none"><path d="M6 13V3M2 5l4-4 4 4" stroke="var(--green)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg> Ascent</span>
<span class="legend-item"><span class="leg-dot" style="background:var(--red)"></span> Deco Stop</span>
<span class="legend-item"><span class="leg-dot" style="background:var(--green)"></span> Safety Stop</span>
<span class="legend-item legend-switch"><svg class="leg-icon" width="14" height="10" viewBox="0 0 14 10" fill="none"><path d="M1 3h12M10 1l3 2-3 2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/><path d="M13 7H1M4 5l-3 2 3 2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg> Gas Switch</span>
</div>`;
}
function _clearResultSummaryStrip() {
  const strip = document.getElementById('resultMetricStrip');
  const chips = document.getElementById('resultChipRow');
  if (strip) strip.innerHTML = '';
  if (chips) chips.innerHTML = '';
  document.getElementById('resultsPanel')?.classList.remove('has-results');
}
function _splitMetricValUnit(raw, defaultUnit) {
  const s = String(raw ?? '—').trim();
  const m = s.match(/^([\d.:]+)\s*(.*)$/);
  if (m) return { val: m[1], unit: (m[2] || defaultUnit).trim() };
  return { val: s, unit: defaultUnit };
}
function _parseChipNum(val) {
  const n = parseFloat(String(val || '').replace(/[^\d.]/g, ''));
  return Number.isFinite(n) ? n : null;
}
function _cnsMetricColor(cnsNum) {
  if (cnsNum == null) return '';
  if (cnsNum >= 80) return 'metric-val--cns-warn';
  if (cnsNum >= 50) return 'metric-val--cns-caution';
  return 'metric-val--cns-safe';
}
function renderMetricCards({ runTime, decoTime, cns, firstStop, unit }) {
  const strip = document.getElementById('resultMetricStrip');
  if (!strip) return;
  const rt = _splitMetricValUnit(runTime, 'min');
  const dt = _splitMetricValUnit(decoTime, 'min');
  const cnsParts = _splitMetricValUnit(String(cns || '').replace('%', ''), '%');
  const fs = _splitMetricValUnit(firstStop, unit || 'm');
  const cnsNum = _parseChipNum(cns);
  const cnsClass = _cnsMetricColor(cnsNum);
  const firstStopClass = fs.val === '—' || fs.val === '-' ? '' : 'metric-val--deco';
  strip.innerHTML = `
    <div class="metric-card">
      <span class="metric-val metric-val--runtime">${rt.val}<span class="unit">${rt.unit}</span></span>
      <span class="metric-lbl">Run Time</span>
    </div>
    <div class="metric-card">
      <span class="metric-val metric-val--deco">${dt.val}<span class="unit">${dt.unit}</span></span>
      <span class="metric-lbl">Deco Time</span>
    </div>
    <div class="metric-card">
      <span class="metric-val${cnsClass ? ' ' + cnsClass : ''}">${cnsParts.val}<span class="unit">${cnsParts.unit}</span></span>
      <span class="metric-lbl">CNS O₂</span>
    </div>
    <div class="metric-card">
      <span class="metric-val${firstStopClass ? ' ' + firstStopClass : ''}">${fs.val}<span class="unit">${fs.unit}</span></span>
      <span class="metric-lbl">First Stop</span>
    </div>`;
}
function renderChipRow({ surfGF, otu, tts, decozone, unit }) {
  const row = document.getElementById('resultChipRow');
  if (!row) return;
  const surfNum = _parseChipNum(surfGF);
  const gfColor = surfNum == null ? 'chip-yellow' : (surfNum > 85 ? 'chip-red' : surfNum > 75 ? 'chip-orange' : 'chip-green');
  const otuNum = _parseChipNum(otu);
  const otuColor = otuNum == null ? 'chip-info' : (otuNum > 300 ? 'chip-red' : otuNum > 200 ? 'chip-orange' : 'chip-green');
  const dzRaw = String(decozone || '').trim();
  const dzUnit = unit || 'm';
  row.innerHTML = `
    <span class="chip ${gfColor}"><span class="chip-dot"></span>Surf GF ${surfGF || '—'}</span>
    <span class="chip ${otuColor}"><span class="chip-dot"></span>OTU ${otu || '—'}</span>
    <span class="chip chip-info"><span class="chip-dot"></span>TTS ${tts || '—'}</span>
    ${dzRaw && dzRaw !== '—' ? `<span class="chip chip-deco"><span class="chip-dot"></span>Decozone ${dzRaw}${/m|ft/i.test(dzRaw) ? '' : dzUnit}</span>` : ''}`;
}
function _renderResultSummaryStrip(data) {
  const panel = document.getElementById('resultsPanel');
  const unit = units === 'imperial' ? 'ft' : 'm';
  renderMetricCards({
    runTime: data.runTime,
    decoTime: data.decoTime,
    cns: data.cns,
    firstStop: data.firstStop,
    unit,
  });
  renderChipRow({
    surfGF: data.surfaceGF,
    otu: data.otu,
    tts: data.tts,
    decozone: data.decozone,
    unit,
  });
  _hideResultEmptyState();
  if (panel) panel.classList.add('has-results');
}
function _onPlanResultsReady() {
  if (plannerAlgo !== 'rec') {
    const graphCard = document.getElementById('fullDiveGraphCard');
    if (graphCard) { graphCard.style.display = 'block'; graphCard.classList.add('card-open'); }
    const decoRes = document.getElementById('decoResult');
    if (decoRes) decoRes.style.display = 'block';
  }
  setMobilePlanView('stack');
}
function setMobilePlanView(view) {
  if (!window.matchMedia('(max-width: 640px)').matches) return;
  const rec = document.getElementById('recPlannerView');
  const tec = document.getElementById('tecPlannerView');
  const results = document.getElementById('resultsPanel');
  if (!results) return;
  const activePlan = plannerAlgo === 'rec' ? rec : tec;
  if (!activePlan) return;
  const hasResults = results.classList.contains('has-results');
  rec?.classList.toggle('mobile-active', activePlan === rec);
  tec?.classList.toggle('mobile-active', activePlan === tec);
  results.classList.toggle('mobile-active', hasResults || view === 'results' || view === 'stack');
}
function _initMobilePlanView() {
  if (window.matchMedia('(max-width: 640px)').matches) {
    setMobilePlanView('plan');
  } else {
    document.getElementById('recPlannerView')?.classList.remove('mobile-active');
    document.getElementById('tecPlannerView')?.classList.remove('mobile-active');
    document.getElementById('resultsPanel')?.classList.remove('mobile-active');
  }
}
function _ensureMobilePlanViewBootstrap() {
  if (window._mobilePlanViewBootstrapDone) return;
  window._mobilePlanViewBootstrapDone = true;
  _initMobilePlanView();
  window.addEventListener('resize', _initMobilePlanView);
}
function _hideResultEmptyState() {
  const empty = document.getElementById('resultEmptyState');
  if (empty) empty.style.display = 'none';
}
function _ppo2ClassV3(val) {
  const n = parseFloat(String(val).replace(/[^\d.]/g, ''));
  if (!Number.isFinite(n)) return '';
  if (n >= 1.6) return 'ppo2-crit';
  if (n >= 1.4) return 'ppo2-hi';
  if (n >= 1.1) return 'ppo2-warn';
  return 'ppo2-ok';
}
function _gasMixClassV3(mix) {
  const m = String(mix || '').toUpperCase();
  if (/100|O₂|O2/.test(m) && !/EAN|NITROX/.test(m)) return 'gas-100';
  if (/EAN|50|NITROX|32|36/.test(m)) return 'gas-ean50';
  return 'gas-air';
}
function decorateDecoTableForV3() {
  const table = document.querySelector('#decoResult .deco-table');
  const tbody = document.getElementById('decoTableBody');
  if (!table || !tbody) return;
  table.classList.add('schedule-table');
  tbody.querySelectorAll('tr').forEach(tr => {
    const ph = tr.dataset.phase;
    if (ph === 'totals') {
      tr.classList.add('row-summary');
      tr.querySelectorAll('.deco-totals-inner span').forEach(span => {
        if (!span.classList.contains('summary-stat')) span.classList.add('summary-stat');
      });
      return;
    }
    if (ph === 'descent') tr.classList.add('row-descent');
    if (ph === 'switch') tr.classList.add('row-switch');
    const cells = tr.cells;
    if (!cells || !cells.length) return;
    cells[0].classList.add('phase-cell');
    const iconPh = ph === 'ascent' && cells[1]?.textContent?.includes('0') ? 'surface' : ph;
    if (_PHASE_ICON_SVG[iconPh]) cells[0].innerHTML = _PHASE_ICON_SVG[iconPh];
    _decorateScheduleCellsByLabel(tr);
  });
}
function _decorateScheduleCellsByLabel(tr) {
  const byLabel = label => tr.querySelector(`td[data-label="${label}"]`);
  const depth = byLabel('Depth');
  const stop = byLabel('Stop');
  const run = byLabel('Run');
  const mix = byLabel('Mix');
  const ppo2 = byLabel('PPO2');
  const cns = byLabel('CNS');
  const ead = byLabel('EAD');
  if (depth) depth.classList.add('col-depth');
  if (stop) stop.classList.add('col-time', 'stop');
  if (run) run.classList.add('col-time', 'run', 'align-r');
  if (mix) mix.classList.add('col-gas', _gasMixClassV3(mix.textContent));
  if (ppo2) ppo2.classList.add('col-ppo2', 'align-r', _ppo2ClassV3(ppo2.textContent));
  if (cns) cns.classList.add('col-cns', 'align-r');
  if (ead) ead.classList.add('col-ead', 'align-r');
}
function _normalizeContingencyPhase(ph) {
  return String(ph || '').replace(/^contingency-/, '');
}
function decorateContingencyTableForV3() {
  const table = document.querySelector('#contingencyResult .deco-table');
  const tbody = document.getElementById('contingencyTableBody');
  if (!table || !tbody) return;
  table.classList.add('schedule-table');
  tbody.querySelectorAll('tr').forEach(tr => {
    const ph = _normalizeContingencyPhase(tr.dataset.phase);
    if (ph === 'totals' || ph === 'info') {
      tr.classList.add('row-summary');
      tr.querySelectorAll('.deco-totals-inner span').forEach(span => {
        if (!span.classList.contains('summary-stat')) span.classList.add('summary-stat');
      });
      return;
    }
    if (ph === 'descent') tr.classList.add('row-descent');
    if (ph === 'switch') tr.classList.add('row-switch');
    const cells = tr.cells;
    if (!cells || !cells.length) return;
    cells[0].classList.add('phase-cell');
    const iconPh = ph === 'ascent' && cells[1]?.textContent?.includes('0') ? 'surface' : ph;
    if (_PHASE_ICON_SVG[iconPh]) cells[0].innerHTML = _PHASE_ICON_SVG[iconPh];
    _decorateScheduleCellsByLabel(tr);
  });
}
function _setGasWarningBanner(message) {
  const banner = document.getElementById('gasWarningBanner');
  if (!banner) return;
  const text = (message || '').trim();
  if (!text) {
    banner.textContent = '';
    banner.style.display = 'none';
    return;
  }
  banner.textContent = text;
  banner.style.display = 'flex';
}
function _setGasWarningBannerHtml(html) {
  const banner = document.getElementById('gasWarningBanner');
  if (!banner) return;
  const content = String(html || '').trim();
  if (!content) {
    banner.textContent = '';
    banner.style.display = 'none';
    return;
  }
  banner.innerHTML = `<span aria-hidden="true">⚠</span><div class="gas-warning-copy">${content}</div>`;
  banner.style.display = 'flex';
}
function _updateGasWarningBannerFromCard(gasEl) {
  // Gas warnings render inside the Gas Consumption card. Do not mirror them into
  // the global top banner; that creates duplicate warnings above the tabs.
  _setGasWarningBanner('');
}
function switchResultTab(name, btn) {
  const isRec = plannerAlgo === 'rec';
  const panes = isRec
    ? ['dive','surfint','avgdepth','multi','ndlref']
    : ['profile','contingency','tissue'];
  const nav = isRec ? document.getElementById('recResultTabs') : document.getElementById('tecResultTabs');
  const panel = document.getElementById('resultsPanel');
  nav?.querySelectorAll('.result-tab-btn').forEach(b => b.classList.toggle('active', b === btn));
  panes.forEach(p => {
    const el = panel?.querySelector('#resultTab-' + p);
    if (el) el.classList.toggle('active', p === name);
  });
  if (name === 'avgdepth') setTimeout(calcAvgDepth, 50);
  if (name === 'surfint') {
    const c = document.getElementById('mainSurfIntContainer');
    if (c && !c.querySelector('#mainSiBody')) {
      renderSurfIntPanel('mainSurfIntContainer', 'mainSi', null, null);
      const body = document.getElementById('mainSiBody');
      const caret = document.getElementById('mainSiCaret');
      if (body) body.style.display = 'block';
      if (caret) caret.textContent = '▴';
      setTimeout(() => {
        document.querySelectorAll('#mainSiBody .lsp-slider').forEach(s => updateSliderFill(s));
        calcSurfInt('mainSi');
      }, 50);
    }
  }
  if (name === 'ndlref') renderNDLTable?.();
  if (name === 'multi') buildDiveBlocks?.();
  if (name === 'profile') setTimeout(() => { drawDecoProfileFull?.(); }, 50);
  if (name === 'tissue') {
    const card = document.getElementById('tissueLoadCard');
    const inner = document.getElementById('tissueLoadInnerCard');
    const hasTissue = window._lastPlan?.finalTissues?.length
      || document.getElementById('tissueGrid')?.children.length;
    if (card && hasTissue) card.style.display = 'block';
    if (inner) inner.classList.add('card-open');
    if (hasTissue) {
      const tissues = window._lastPlan?.finalTissues;
      if (tissues?.length) updateTissueViz?.(tissues, mGF?.high ?? 85);
      renderTissueLoadChart?.();
    }
    setTimeout(() => { _syncGfCurveCardVisibility?.(); drawGFCurve?.(); attachGFCurveInteraction?.(); }, 50);
  }
}
