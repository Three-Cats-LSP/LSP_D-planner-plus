/**
 * Planner / tools navigation shell and V4 layout bootstrap.
 * Globals read: plannerAlgo, setPlannerAlgo, toggleReference, syncEnvRowDisplay,
 *   initTools, setBrandIcon, appSettings, moveChildren (local in init)
 * Globals written: navMode, vpmVariant, window._v3LayoutDone
 */
let vpmVariant = (() => {
  try {
    const s = localStorage.getItem('vpmVariant');
    return s === 'VPMB_GFS' ? 'VPMB_GFS' : 'VPMB';
  } catch (e) { return 'VPMB'; }
})();

function _syncVpmModeUI(model) {
  const m = model === 'VPMB_GFS' ? 'VPMB_GFS' : 'VPMB';
  document.getElementById('vpmModePure')?.classList.toggle('active', m === 'VPMB');
  document.getElementById('vpmModeGfs')?.classList.toggle('active', m === 'VPMB_GFS');
  const sub = document.getElementById('vpmNavSub');
  if (sub) sub.textContent = m === 'VPMB_GFS' ? 'Bubble + GF Surfacing' : 'Bubble Model';
}

function setVpmMode(model, btn) {
  if (model !== 'VPMB' && model !== 'VPMB_GFS') return;
  vpmVariant = model;
  try { localStorage.setItem('vpmVariant', model); } catch (e) {}
  if (btn) {
    document.querySelectorAll('#vpmModeRowV3 .seg-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
  } else {
    _syncVpmModeUI(model);
  }
  if (plannerAlgo === 'VPMB' || plannerAlgo === 'VPMB_GFS') {
    setPlannerAlgo(model, document.getElementById('navBtnVpm'));
  }
}

function _highlightMainNav(section) {
  const map = { rec: 'navBtnRec', buh: 'navBtnBuh', vpm: 'navBtnVpm', tools: 'navBtnTools', settings: 'navBtnSettings' };
  document.querySelectorAll('#mainNavBar .main-nav-btn').forEach(b => b.classList.remove('active'));
  const id = map[section];
  if (id) document.getElementById(id)?.classList.add('active');
}

function setMainNav(section, btn) {
  if (btn) {
    document.querySelectorAll('#mainNavBar .main-nav-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
  } else {
    _highlightMainNav(section);
  }
  if (section === 'tools') { setNavMode('tools'); return; }
  if (section === 'settings') { setNavMode('settings'); return; }
  setNavMode('planner');
  if (section === 'rec') setPlannerAlgo('rec', btn || document.getElementById('navBtnRec'));
  else if (section === 'buh') setPlannerAlgo('ZHLC_GF', btn || document.getElementById('navBtnBuh'));
  else if (section === 'vpm') setPlannerAlgo(vpmVariant, btn || document.getElementById('navBtnVpm'));
}

function setNavMode(mode) {
  document.querySelectorAll('.bnav-btn').forEach(b => b.classList.remove('active'));
  if (mode === 'ref') {
    document.getElementById('bnavRef')?.classList.add('active');
    toggleReference();
    return;
  }
  if (mode !== 'planner' && mode !== 'tools' && mode !== 'settings') return;
  navMode = mode;
  document.getElementById('settingsPageWrap')?.classList.toggle('visible', mode === 'settings');
  document.getElementById('plannerView')?.classList.toggle('visible', mode === 'planner');
  document.getElementById('toolsPageWrap')?.classList.toggle('visible', mode === 'tools');
  document.getElementById('toolsBar')?.classList.toggle('visible', mode === 'tools');
  document.body.classList.toggle('algo-tools', mode === 'tools');
  syncEnvRowDisplay?.();
  if (mode === 'settings') {
    document.getElementById('bnavSettings')?.classList.add('active');
    _highlightMainNav('settings');
    document.getElementById('algoLabel').textContent = 'SETTINGS';
    document.getElementById('algoSubtitle').textContent = 'Water · Units · Altitude';
    setBrandIcon('planner');
    return;
  }
  if (mode === 'planner') {
    document.getElementById('bnavPlanner')?.classList.add('active');
    setMobilePlanView('plan');
    setPlannerAlgo(plannerAlgo);
    return;
  }
  if (mode === 'tools') {
    document.getElementById('bnavTools')?.classList.add('active');
    _highlightMainNav('tools');
    algo = 'tools';
    document.getElementById('algoLabel').textContent = 'TOOLS';
    document.getElementById('algoSubtitle').textContent = 'Dive Planning Tools & Calculators';
    setBrandIcon('tools');
    initTools();
    if (typeof appSettings !== 'undefined' && appSettings.save) setTimeout(() => appSettings.save(false), 100);
  }
}

function initV3Layout() {
  if (window._v3LayoutDone) return;
  window._v3LayoutDone = true;

  const moveChildren = (from, to, skipIds) => {
    if (!from || !to) return;
    while (from.firstChild) {
      const ch = from.firstChild;
      if (ch.id && skipIds && skipIds.includes(ch.id)) { from.removeChild(ch); continue; }
      to.appendChild(ch);
    }
  };

  // GF presets row → mount
  const gfRow = document.getElementById('gfPresetsRow');
  const gfMount = document.getElementById('gfPresetsMount');
  if (gfRow && gfMount) {
    const sel = gfRow.querySelector('#gfPresetSelect');
    const custom = gfRow.querySelector('#gfCustomRow');
    if (sel) gfMount.appendChild(sel);
    if (custom) gfMount.appendChild(custom);
    gfRow.remove();
  }

  const consRow = document.getElementById('conservatismRow');
  const consMount = document.getElementById('conservatismSelectMount');
  if (consRow && consMount) {
    const sel = consRow.querySelector('#conservatismSelect');
    if (sel) { sel.classList.add('hidden-v3'); consMount.appendChild(sel); }
    consRow.remove();
  }

  // Tec inputs from deco card → planPanelTecMount
  const decoCard = document.querySelector('#deco > .card');
  const tecMount = document.getElementById('planPanelTecMount');
  if (decoCard && tecMount) {
    const skip = new Set(['algoRow', 'gfPresetsRow', 'conservatismRow', 'decoCardHeaderRow']);
    Array.from(decoCard.children).forEach(ch => {
      if (ch.id && skip.has(ch.id)) return;
      if (ch.querySelector?.('#presetsHeaderBtn') || ch.querySelector?.('#advConfigPresetsBtn')) return;
      if (ch.querySelector?.('#decoDepth') || ch.querySelector?.('#decoBT')) return;
      if (ch.classList?.contains('form-grid') && ch.querySelector('#decoDepth')) return;
      if (ch.tagName === 'BUTTON' && ch.classList.contains('btn-calc')) return;
      tecMount.appendChild(ch);
    });
  }

  // Remove legacy planner duplicate card (inputs moved to v3 panel)
  const plannerCard = document.querySelector('#planner > .card');
  if (plannerCard) plannerCard.remove();

  // Result tab mounts — rec
  const moveToTab = (id, tab) => {
    const el = document.getElementById(id);
    const pane = document.getElementById('resultTab-' + tab);
    if (el && pane) pane.appendChild(el);
  };
  moveToTab('plannerResult', 'dive');
  moveToTab('plannerProfileCanvas-wrap', 'dive');
  moveToTab('plannerProfileLegend', 'dive');
  const surfPanel = document.getElementById('surfint');
  if (surfPanel) moveChildren(surfPanel, document.getElementById('resultTab-surfint'), []);
  const avgPanel = document.getElementById('avgdepth');
  if (avgPanel) moveChildren(avgPanel, document.getElementById('resultTab-avgdepth'), []);
  const multiPanel = document.getElementById('multi');
  if (multiPanel) moveChildren(multiPanel, document.getElementById('resultTab-multi'), []);
  const ndlPanel = document.getElementById('ndlref');
  if (ndlPanel) moveChildren(ndlPanel, document.getElementById('resultTab-ndlref'), []);

  const cnsPanel = document.getElementById('cns');
  const cnsMount = document.getElementById('tool-panel-cns');
  if (cnsPanel && cnsMount) {
    moveChildren(cnsPanel, cnsMount, []);
    cnsPanel.remove();
  }

  // Modals inside .legacy-panels are suppressed by display:none — move to body
  const legacyRoot = document.querySelector('.legacy-panels');
  if (legacyRoot) {
    [...legacyRoot.querySelectorAll('.lsp-modal-overlay')].forEach(modal => document.body.appendChild(modal));
  }

  // Tools → toolsPanelMount
  const toolsPanel = document.getElementById('toolsPanel');
  const toolsMount = document.getElementById('toolsPanelMount');
  if (toolsPanel && toolsMount) {
    moveChildren(toolsPanel, toolsMount, []);
  }

  _syncVpmModeUI(vpmVariant);
  _buildGfPresetBtns();
  _syncConservatismBtns();
  _syncCircuitBtns();
  _syncDepthBtSteppers();
  _updatePlanPanelSections();
  _initMobilePlanView();
}
