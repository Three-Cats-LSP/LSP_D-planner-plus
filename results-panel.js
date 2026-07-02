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
  deco: '<span class="ph ph-deco" aria-hidden="true"><svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor"><circle cx="5" cy="5" r="4.5" stroke="currentColor" stroke-width="1" fill="none"/><circle cx="5" cy="5" r="2.5"/></svg></span>',
  safety: '<span class="ph ph-deco" aria-hidden="true"><svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor"><circle cx="5" cy="5" r="4.5" stroke="currentColor" stroke-width="1" fill="none"/><circle cx="5" cy="5" r="2.5"/></svg></span>',
  switch: '<span class="ph ph-switch" aria-hidden="true"><svg width="14" height="10" viewBox="0 0 14 10" fill="none"><path d="M1 3h12M10 1l3 2-3 2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/><path d="M13 7H1M4 5l-3 2 3 2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg></span>',
};
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
function renderMetricCards({ runTime, decoTime, cns, firstStop, unit }) {
  const strip = document.getElementById('resultMetricStrip');
  if (!strip) return;
  const rt = _splitMetricValUnit(runTime, 'min');
  const dt = _splitMetricValUnit(decoTime, 'min');
  const cnsParts = _splitMetricValUnit(String(cns || '').replace('%', ''), '%');
  const fs = _splitMetricValUnit(firstStop, unit || 'm');
  const cnsNum = _parseChipNum(cns);
  const cnsStyle = cnsNum == null ? '' : ` style="color:${cnsNum >= 80 ? 'var(--orange)' : 'var(--green)'}"`;
  strip.innerHTML = `
    <div class="metric-card">
      <span class="metric-val">${rt.val}<span class="unit">${rt.unit}</span></span>
      <span class="metric-lbl">Run Time</span>
    </div>
    <div class="metric-card">
      <span class="metric-val">${dt.val}<span class="unit">${dt.unit}</span></span>
      <span class="metric-lbl">Deco Time</span>
    </div>
    <div class="metric-card">
      <span class="metric-val"${cnsStyle}>${cnsParts.val}<span class="unit">${cnsParts.unit}</span></span>
      <span class="metric-lbl">CNS O₂</span>
    </div>
    <div class="metric-card">
      <span class="metric-val">${fs.val}<span class="unit">${fs.unit}</span></span>
      <span class="metric-lbl">First Stop</span>
    </div>`;
}
function renderChipRow({ surfGF, otu, tts, decozone, unit }) {
  const row = document.getElementById('resultChipRow');
  if (!row) return;
  const surfNum = _parseChipNum(surfGF);
  const gfColor = surfNum == null ? 'chip-yellow' : (surfNum > 85 ? 'chip-red' : surfNum > 75 ? 'chip-orange' : 'chip-green');
  const otuNum = _parseChipNum(otu);
  const otuColor = otuNum == null ? 'chip-yellow' : (otuNum > 300 ? 'chip-red' : otuNum > 200 ? 'chip-orange' : 'chip-yellow');
  const dzRaw = String(decozone || '').trim();
  const dzColor = dzRaw && dzRaw !== '—' && !/^0\s*m/i.test(dzRaw) ? 'chip-orange' : 'chip-green';
  const dzUnit = unit || 'm';
  row.innerHTML = `
    <span class="chip ${gfColor}"><span class="chip-dot"></span>Surf GF ${surfGF || '—'}</span>
    <span class="chip ${otuColor}"><span class="chip-dot"></span>OTU ${otu || '—'}</span>
    <span class="chip chip-yellow"><span class="chip-dot"></span>TTS ${tts || '—'}</span>
    ${dzRaw && dzRaw !== '—' ? `<span class="chip ${dzColor}"><span class="chip-dot"></span>Decozone ${dzRaw}${/m|ft/i.test(dzRaw) ? '' : dzUnit}</span>` : ''}`;
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
    const dgc = document.getElementById('diveGraphCard');
    if (dgc) { dgc.style.display = 'block'; dgc.classList.add('card-open'); }
    const decoRes = document.getElementById('decoResult');
    if (decoRes) decoRes.style.display = 'block';
  }
  setMobilePlanView('results');
}
function setMobilePlanView(view) {
  if (!window.matchMedia('(max-width: 640px)').matches) return;
  const plan = document.getElementById('planPanel');
  const results = document.getElementById('resultsPanel');
  if (!plan || !results) return;
  plan.classList.toggle('mobile-active', view === 'plan');
  results.classList.toggle('mobile-active', view === 'results');
}
function _initMobilePlanView() {
  if (window.matchMedia('(max-width: 640px)').matches) {
    setMobilePlanView('plan');
  } else {
    document.getElementById('planPanel')?.classList.remove('mobile-active');
    document.getElementById('resultsPanel')?.classList.remove('mobile-active');
  }
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
    if (cells[1]) cells[1].classList.add('col-depth');
    if (cells[2]) cells[2].classList.add('col-time', 'stop');
    if (cells[3]) {
      cells[3].classList.add('col-gas', _gasMixClassV3(cells[3].textContent));
    }
    if (cells[4]) cells[4].classList.add('col-time', 'run', 'align-r');
    if (cells[5]) cells[5].classList.add('col-tts', 'align-r');
    if (cells[6]) {
      cells[6].classList.add('col-ppo2', 'align-r', _ppo2ClassV3(cells[6].textContent));
    }
    if (cells[7]) cells[7].classList.add('col-ead', 'align-r');
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
function _updateGasWarningBannerFromCard(gasEl) {
  if (!gasEl || gasEl.style.display === 'none') {
    _setGasWarningBanner('');
    return;
  }
  const alert = gasEl.querySelector('.alert.dang');
  if (alert) {
    const msg = alert.textContent.replace(/\s+/g, ' ').trim();
    _setGasWarningBanner(msg || 'Gas shortfall detected in Gas Consumption.');
    return;
  }
  const shortRow = Array.from(gasEl.querySelectorAll('tr')).find(tr => /(^|\s)short(\s|$)/i.test((tr.textContent || '').replace(/\s+/g, ' ')));
  if (shortRow) {
    _setGasWarningBanner('Gas shortfall detected in Gas Consumption. Review required vs available volumes.');
    return;
  }
  _setGasWarningBanner('');
}
function switchResultTab(name, btn) {
  const isRec = plannerAlgo === 'rec';
  const prefix = isRec ? '' : '';
  const panes = isRec
    ? ['dive','surfint','avgdepth','multi','ndlref']
    : ['profile','contingency','tissue','gfcurve'];
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
}
