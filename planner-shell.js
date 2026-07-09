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

let mobileTab = 'plan';
let mobileResultTab = 'profile';

function isMobileShell() {
  return window.matchMedia('(max-width: 767px)').matches;
}

function getMobileTab() {
  return mobileTab;
}

function isMobileTab(tab) {
  return isMobileShell() && mobileTab === tab;
}

function syncMobileResultsNav() {
  const hasResults = document.getElementById('resultsPanel')?.classList.contains('has-results');
  document.querySelectorAll('#appBottomNav [data-result-tab]').forEach(btn => {
    btn.disabled = !hasResults;
    btn.setAttribute('aria-disabled', hasResults ? 'false' : 'true');
  });
  const planBtn = document.querySelector('#appBottomNav [data-tab="plan"]');
  if (planBtn) {
    planBtn.disabled = false;
    planBtn.setAttribute('aria-disabled', 'false');
  }
  _highlightMobileBottomNav(mobileTab);
}

function _syncMobileAlgoChips(section) {
  const map = { rec: 'mobChipRec', buh: 'mobChipBuh', vpm: 'mobChipVpm', tools: 'mobChipTools', settings: 'mobChipSettings' };
  document.querySelectorAll('#mobileAlgoChips .mobile-algo-chip').forEach(b => b.classList.remove('active'));
  const id = map[section];
  if (id) document.getElementById(id)?.classList.add('active');
}
window._syncMobileAlgoChips = _syncMobileAlgoChips;

function _highlightMobileBottomNav(tab) {
  const hasResults = document.getElementById('resultsPanel')?.classList.contains('has-results');
  document.querySelectorAll('#appBottomNav .nav-item').forEach(btn => {
    const isPlan = tab === 'plan' && btn.dataset.tab === 'plan';
    const isResult = !!hasResults && tab === 'results' && btn.dataset.resultTab === mobileResultTab;
    btn.classList.toggle('active', isPlan || isResult);
  });
}

function _applyMobileTabClass(tab) {
  document.body.classList.remove('mobile-tab-plan', 'mobile-tab-results', 'mobile-tab-tools', 'mobile-tab-settings');
  if (isMobileShell()) document.body.classList.add('mobile-tab-' + tab);
}

function setMobileTab(tab, opts) {
  opts = opts || {};
  if (!isMobileShell()) return;
  if (tab !== 'plan' && tab !== 'results' && tab !== 'tools' && tab !== 'settings') return;
  if (tab === 'results') {
    const hasResults = document.getElementById('resultsPanel')?.classList.contains('has-results');
    if (!hasResults) return;
  }
  if (tab === mobileTab && !opts.force) return;

  mobileTab = tab;
  _applyMobileTabClass(tab);
  _highlightMobileBottomNav(tab);

  if (!opts.skipNavMode) {
    if (tab === 'plan' || tab === 'results') {
      if (navMode !== 'planner') setNavMode('planner', { skipMobileTab: true });
    } else if (tab === 'tools') {
      if (navMode !== 'tools') setNavMode('tools', { skipMobileTab: true });
    } else if (tab === 'settings') {
      if (navMode !== 'settings') setNavMode('settings', { skipMobileTab: true });
    }
  }
  if (tab === 'plan' || tab === 'results') {
    document.body.classList.remove('mobile-view-stack');
    if (typeof window._syncMobileActivePanels === 'function') {
      window._syncMobileActivePanels(tab === 'results' ? 'results' : 'plan');
    }
  }
}

function setMobileResultTab(name) {
  if (!isMobileShell()) return;
  if (name !== 'profile' && name !== 'contingency' && name !== 'tissue') return;
  const hasResults = document.getElementById('resultsPanel')?.classList.contains('has-results');
  if (!hasResults) return;
  mobileResultTab = name;
  if (mobileTab !== 'results') setMobileTab('results', { skipNavMode: true, force: true });
  const btn = document.querySelector(`#tecResultTabs [data-tab="${name}"]`);
  if (typeof switchResultTab === 'function') switchResultTab(name, btn);
  _highlightMobileBottomNav('results');
}

function _setMobileResultTabActive(name) {
  if (name !== 'profile' && name !== 'contingency' && name !== 'tissue') return;
  mobileResultTab = name;
  _highlightMobileBottomNav(mobileTab);
}

function _clearMobileShellState() {
  mobileTab = 'plan';
  document.body.classList.remove('mobile-tab-plan', 'mobile-tab-results', 'mobile-tab-tools', 'mobile-tab-settings');
  document.querySelectorAll('#appBottomNav .nav-item').forEach(btn => btn.classList.remove('active'));
}

function _initMobileShell() {
  if (window._mobileShellBootstrapDone) return;
  window._mobileShellBootstrapDone = true;

  const onResize = () => {
    if (isMobileShell()) {
      _applyMobileTabClass(mobileTab);
      _highlightMobileBottomNav(mobileTab);
      syncMobileResultsNav();
    } else {
      _clearMobileShellState();
      if (typeof _initMobilePlanView === 'function') _initMobilePlanView();
    }
  };

  window.addEventListener('resize', onResize);
  if (isMobileShell()) {
    setMobileTab('plan', { force: true });
    syncMobileResultsNav();
  }
}

window.isMobileShell = isMobileShell;
window.isMobileTab = isMobileTab;
window.getMobileTab = getMobileTab;
window.setMobileTab = setMobileTab;
window.setMobileResultTab = setMobileResultTab;
window._setMobileResultTabActive = _setMobileResultTabActive;
window.syncMobileResultsNav = syncMobileResultsNav;

function _syncVpmModeUI(model) {
  const m = model === 'VPMB_GFS' ? 'VPMB_GFS' : 'VPMB';
  const toggle = document.getElementById('vpmModeToggle');
  if (toggle) {
    toggle.dataset.side = m === 'VPMB_GFS' ? 'right' : 'left';
    toggle.setAttribute('aria-pressed', m === 'VPMB_GFS' ? 'true' : 'false');
  }
  const sub = document.getElementById('vpmNavSub');
  if (sub) sub.textContent = m === 'VPMB_GFS' ? 'Bubble + GF Surfacing' : 'Bubble Model';
}

function toggleVpmMode() {
  setVpmMode(vpmVariant === 'VPMB' ? 'VPMB_GFS' : 'VPMB');
}

function setVpmMode(model, btn) {
  if (model !== 'VPMB' && model !== 'VPMB_GFS') return;
  vpmVariant = model;
  try { localStorage.setItem('vpmVariant', model); } catch (e) {}
  _syncVpmModeUI(model);
  if (plannerAlgo === 'VPMB' || plannerAlgo === 'VPMB_GFS') {
    setPlannerAlgo(model, document.getElementById('navBtnVpm'));
  }
}

function _highlightMainNav(section) {
  const map = { rec: 'navBtnRec', buh: 'navBtnBuh', vpm: 'navBtnVpm', tools: 'navBtnTools', settings: 'navBtnSettings' };
  document.querySelectorAll('#mainNavBar .main-nav-btn').forEach(b => b.classList.remove('active'));
  const id = map[section];
  if (id) document.getElementById(id)?.classList.add('active');
  _syncMobileAlgoChips(section);
}
window._highlightMainNav = _highlightMainNav;

function setMainNav(section, btn) {
  _highlightMainNav(section);
  if (section === 'tools') {
    if (isMobileShell()) setMobileTab('tools');
    else setNavMode('tools');
    return;
  }
  if (section === 'settings') {
    if (isMobileShell()) setMobileTab('settings');
    else setNavMode('settings');
    return;
  }
  if (isMobileShell() && mobileTab !== 'plan' && mobileTab !== 'results') setMobileTab('plan', { skipNavMode: true });
  const returningFromAux = navMode === 'tools' || navMode === 'settings';
  const targetModel = section === 'rec'
    ? 'rec'
    : section === 'buh'
      ? 'ZHLC_GF'
      : section === 'vpm'
        ? vpmVariant
        : plannerAlgo;
  setNavMode('planner');
  if (returningFromAux && targetModel === plannerAlgo) {
    algo = plannerAlgo === 'rec' ? 'padi' : 'buh';
    _highlightMainNav(section);
    return;
  }
  if (section === 'rec') setPlannerAlgo('rec');
  else if (section === 'buh') setPlannerAlgo('ZHLC_GF');
  else if (section === 'vpm') setPlannerAlgo(vpmVariant);
  _highlightMainNav(section);
}

function setNavMode(mode, opts) {
  opts = opts || {};
  if (mode === 'ref') {
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
  if (!opts.skipMobileTab && isMobileShell()) {
    if (mode === 'planner' && mobileTab !== 'results') setMobileTab('plan', { skipNavMode: true, force: true });
    else if (mode === 'tools') setMobileTab('tools', { skipNavMode: true, force: true });
    else if (mode === 'settings') setMobileTab('settings', { skipNavMode: true, force: true });
  }
  if (mode === 'settings') {
    _highlightMainNav('settings');
    document.getElementById('algoLabel').textContent = 'SETTINGS';
    document.getElementById('algoSubtitle').textContent = 'Water · Units · Altitude';
    setBrandIcon('planner');
    return;
  }
  if (mode === 'planner') {
    const section = plannerAlgo === 'rec'
      ? 'rec'
      : (plannerAlgo === 'ZHLC_GF' ? 'buh' : 'vpm');
    _highlightMainNav(section);
    setMobilePlanView('plan');
    _updatePlanPanelSections();
    _updatePlannerSubtitle();
    algo = plannerAlgo === 'rec' ? 'padi' : 'buh';
    if (typeof appSettings !== 'undefined' && appSettings.save) appSettings.save(false);
    return;
  }
  if (mode === 'tools') {
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

  // Result tab mounts — rec
  const moveToTab = (id, tab) => {
    const el = document.getElementById(id);
    const pane = document.getElementById('resultTab-' + tab);
    if (el && pane) pane.appendChild(el);
  };
  const fullGraphMount = document.getElementById('fullDiveGraphMount');
  const profileWrap = document.getElementById('plannerProfileCanvas-wrap');
  const profileHint = document.getElementById('plannerProfileCanvas-hint');
  if (fullGraphMount && profileWrap) {
    fullGraphMount.appendChild(profileWrap);
    if (profileHint) fullGraphMount.appendChild(profileHint);
  }
  moveToTab('plannerResult', 'dive');
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
  _ensureMobilePlanViewBootstrap();
  _initMobileShell();
}
