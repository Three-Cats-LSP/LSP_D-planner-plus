/**
 * Deco / travel / bailout gas card UI — MOD displays, dynamic cards, travel gas.
 * Loaded by index.html before main inline script.
 * Globals read: units, altSurfaceP, BAR_PER_METRE, allowO2AtMOD, FN2_AIR, FN2_EAN32, FN2_EAN36,
 *   calcGasMODm, validateGasFractionsPct, getBottomGasFractions, getDecoCardFractions,
 *   getDomBottomGasPct, getDomDecoGasPct, getGasLabel, getBailoutPpo2Limit, isCcrGasUiMode,
 *   updateCcrGasValidation, toggleDecoCustomO2, toggleDecoTrimix, replanAfterEnvChange,
 *   shortMixLabel, CUFT_PER_LITRE
 * Globals written: _dgNextIdx, _travelGasFractionWarning
 */

let _travelGasFractionWarning = '';

// Collect all deco gas IDs from DOM (both pre-built and dynamic cards)
// AUDIT-UNIT:UI-GAS-INPUTS
function getAllDecoGasIds() {
  const ids = [];
  document.querySelectorAll('.deco-gas-card').forEach(card => {
    const sel = card.querySelector('select[id^="dg"]');
    if (sel) {
      const m = sel.id.match(/^dg(\d+)Mix$/);
      if (m) ids.push(parseInt(m[1]));
    }
  });
  return ids;
}

function decoCardPersistFieldIds(idx) {
  return [
    `dg${idx}Mix`,
    `dg${idx}CustomO2`,
    `dg${idx}TrimixO2`,
    `dg${idx}TrimixHe`,
    `cylDg${idx}_size`,
    `cylDg${idx}_pres`,
    `cylDg${idx}_reserve`,
    `gpDg${idx}_size`,
    `gpDg${idx}_fill`,
    `gpDg${idx}_reserve`,
  ];
}

function _setModDisplay(el, text, title) {
  if (!el) return;
  if (el.tagName === 'INPUT') el.value = text;
  else el.textContent = text;
  if (title != null) el.title = title;
}

function syncGasCardDots() {
  const dotForDecoIndex = (n) => (n <= 1 ? 'gas-dot--deco1' : 'gas-dot--deco2');
  const applyDot = (card, dotClass) => {
    if (!card) return;
    let dot = card.querySelector('.gas-dot');
    if (!dot) {
      const titleRow = card.querySelector('.gas-card-title-row');
      if (!titleRow) return;
      dot = document.createElement('span');
      dot.className = 'gas-dot';
      dot.setAttribute('aria-hidden', 'true');
      titleRow.insertBefore(dot, titleRow.firstChild);
    }
    dot.className = `gas-dot ${dotClass}`;
  };
  applyDot(document.getElementById('diluentGasCard'), 'gas-dot--bottom');
  applyDot(document.getElementById('travelGasCard'), 'gas-dot--travel');
  document.querySelectorAll('.deco-gas-card').forEach((card, i) => {
    const mix = card.querySelector('select[id$="Mix"]')?.value || '';
    const dotClass = /^o2$/i.test(mix) ? 'gas-dot--o2' : dotForDecoIndex(i);
    applyDot(card, dotClass);
  });
}

function updateGasMODDisplays() {
  const ppO2Limit = parseFloat(document.getElementById('ppo2Bottom')?.value) || 1.4;
  const ppO2Deco  = parseFloat(document.getElementById('ppo2Deco')?.value)   || 1.6;
  const isMetric  = units !== 'imperial';
  const ccrUi     = isCcrGasUiMode();
  const o2AtMOD   = typeof allowO2AtMOD !== 'undefined' ? allowO2AtMOD : true;
  const lastStop  = parseInt(document.getElementById('lastDecoStop')?.value) || 3;
  const o2MODm    = Math.max(lastStop, 6); // 6 m is the standard O2 operating depth

  function fmtDepth(m) {
    return isMetric ? m + ' m' : Math.floor(m * 3.28084) + ' ft';
  }

  function fmtModLabel(m) {
    return 'MOD ' + fmtDepth(m);
  }

  function tooltipText(fO2, ppO2limit, label) {
    if (fO2 >= 0.995 && o2AtMOD)
      return `MOD: ${o2MODm} m (pure O₂ minimum: ${o2MODm} m — O₂ @ MOD: Allow at MOD)\nFormula: ppO₂ ${ppO2limit} / ${fO2.toFixed(2)} − ${altSurfaceP.toFixed(3)} = ${((ppO2limit/fO2-altSurfaceP)/BAR_PER_METRE).toFixed(1)} m (strict) → overridden to ${o2MODm} m`;
    const modM = calcGasMODm(fO2, ppO2limit);
    const exact = (ppO2limit / fO2 - altSurfaceP) / BAR_PER_METRE;
    const exactDisp = Math.max(0, exact);
    return `MOD = floor((${ppO2limit} / ${fO2.toFixed(2)} − ${altSurfaceP.toFixed(3)}) / BAR_PER_METRE)\n= floor(${exactDisp.toFixed(2)}) = ${modM} m\nLimit: ${label} ppO₂ ${ppO2limit} bar | ${o2AtMOD ? 'Allow at MOD' : 'Strict ppO₂'}`;
  }

  // Bottom gas MOD — validate raw DOM % before clamped fractions
  const botMix = document.getElementById('decoGas')?.value;
  const botDom = (botMix === 'custom' || botMix === 'trimix') ? getDomBottomGasPct() : null;
  const botDomCheck = botDom ? validateGasFractionsPct(botDom.o2, botDom.he, 'bottomGas') : null;
  const botEl    = document.getElementById('botMODDisplay');
  if (botEl) {
    if (botDomCheck && !botDomCheck.ok) {
      _setModDisplay(botEl, '—', botDomCheck.message);
    } else {
      const botFracs = getBottomGasFractions();
      if (!botFracs) {
        _setModDisplay(botEl, '—', 'Enter valid bottom gas mix');
      } else {
      const botFO2   = botFracs.fO2;
      const botMOD   = calcGasMODm(botFO2, ppO2Limit);
      const botLabel = getGasLabel(botFO2, botFracs.fHe);
      const heNote   = botFracs.fHe > 0 ? '  (' + botLabel + ')' : '';
      let clampNote = '';
      if (botMix === 'custom' && Number.isFinite(botDom.o2) && botDom.o2 > 0 && botDom.o2 < 5) {
        clampNote = '  (5% used)';
      }
      let tip = tooltipText(botFO2, ppO2Limit, ccrUi ? 'Diluent' : 'Bottom') + heNote;
      if (clampNote) {
        tip += '\n⚠ O₂ ' + botDom.o2 + '% is below 5% minimum — calculations use 5%.';
      }
      _setModDisplay(botEl, fmtModLabel(botMOD), tip);
      }
    }
  }

  // Loop over all deco gas cards
  for (const cidx of getAllDecoGasIds()) {
    const sel  = document.getElementById(`dg${cidx}Mix`);
    const disp = document.getElementById(`dg${cidx}MODDisplay`);
    if (!sel || !disp) continue;
    if (sel.value === 'none' || !sel.value) { _setModDisplay(disp, '—', 'Select a gas mix to see MOD'); continue; }
    if (sel.value === 'custom' || sel.value === 'trimix') {
      const domG = getDomDecoGasPct(cidx);
      const domCheck = domG ? validateGasFractionsPct(domG.o2, domG.he, `dg${cidx}`) : null;
      if (!domCheck || !domCheck.ok) {
        const inputHint = sel.value === 'custom'
          ? 'Enter a valid O₂ % for custom deco gas.'
          : 'Enter valid O₂ and He % for trimix deco gas.';
        _setModDisplay(disp, '—', domCheck?.message ? `${inputHint} ${domCheck.message}` : inputHint);
        continue;
      }
    }
    const dgFracs = getDecoCardFractions(cidx);
    if (!dgFracs) { _setModDisplay(disp, '—'); continue; }
    const fO2 = dgFracs.fO2;
    const bailoutPpo2 = ccrUi ? getBailoutPpo2Limit() : ppO2Deco;
    const mod = calcGasMODm(fO2, bailoutPpo2);
    const heNote = dgFracs.fHe > 0 ? '  (' + getGasLabel(fO2, dgFracs.fHe) + ')' : '';
    _setModDisplay(disp, fmtModLabel(mod), tooltipText(fO2, bailoutPpo2, ccrUi ? 'Bailout' : 'Deco') + heNote);
  }
  updateCcrGasValidation();
  syncGasCardDots();
}

// ── Dynamic Deco Gas Cards ──────────────────────────────────────────────────
let _dgNextIdx = 3; // next deco gas index (1-based, cards 1 and 2 are pre-built)
const _DG_MAX = 8;

function _dgCardCount() {
  return document.querySelectorAll('.deco-gas-card').length;
}

function _nextFreeDecoCardIdx() {
  for (let i = 3; i <= _DG_MAX; i++) {
    if (!document.getElementById(`dgCard_${i}`)) return i;
  }
  return null;
}

function _syncDgNextIdx() {
  const free = _nextFreeDecoCardIdx();
  _dgNextIdx = free != null ? free : (_DG_MAX + 1);
}

function renumberDecoGasCards() {
  const ccrUi = isCcrGasUiMode();
  document.querySelectorAll('.deco-gas-card').forEach((card, i) => {
    const n = i + 1;
    const mixNum = n + 1;
    const titleEl = card.querySelector('.dg-card-title');
    if (titleEl) {
      titleEl.textContent = ccrUi
        ? `BAILOUT MIX ${n}`
        : `GAS MIX ${mixNum} — DECO GAS ${n} (optional)`;
    }
  });
  const btn = document.getElementById('addDecoGasBtn');
  if (btn) btn.style.display = _dgCardCount() >= _DG_MAX ? 'none' : 'block';
  syncGasCardDots();
}

function _insertDecoGasCardInIdOrder(card, idx) {
  const container = document.getElementById('decoGasCards');
  if (!container) return;
  const nextId = getAllDecoGasIds().filter(id => id > idx).sort((a, b) => a - b)[0];
  const ref = nextId ? document.getElementById(`dgCard_${nextId}`) : null;
  if (ref) container.insertBefore(card, ref);
  else container.appendChild(card);
}

function syncDecoGasCardUi(idx) {
  toggleDecoCustomO2(`dg${idx}Mix`, `dg${idx}CustomField`);
  toggleDecoTrimix(idx);
  updateGasMODDisplays();
}

function defaultDecoCylFieldValues() {
  const PSI_PER_BAR = 14.5038;
  const sizeL = 11, fillBar = 200, reserveBar = 50;
  if (units === 'imperial') {
    return {
      size: (sizeL * CUFT_PER_LITRE).toFixed(1).replace(/\.0$/, ''),
      fill: String(Math.round(fillBar * PSI_PER_BAR)),
      reserve: String(Math.round(reserveBar * PSI_PER_BAR)),
      sizeMax: 1766,
      presMax: 4351,
    };
  }
  return {
    size: String(sizeL),
    fill: String(fillBar),
    reserve: String(reserveBar),
    sizeMax: 30,
    presMax: 300,
  };
}

// AUDIT-UNIT:UI-GAS-CARDS
function appendDecoGasCardAtIdx(idx) {
  if (idx <= 2 || idx > _DG_MAX || document.getElementById(`dgCard_${idx}`)) return;
  if (_dgCardCount() >= _DG_MAX) return;
  const n = _dgCardCount() + 1;
  const mixNum = n + 1;
  const ccrUi = isCcrGasUiMode();
  const cardTitle = ccrUi ? `BAILOUT MIX ${n}` : `GAS MIX ${mixNum} — DECO GAS ${n} (optional)`;
  const dotClass = n <= 1 ? 'gas-dot--deco1' : 'gas-dot--deco2';
  const cylDefaults = defaultDecoCylFieldValues();

  const card = document.createElement('div');
  card.className = 'deco-gas-card';
  card.id = `dgCard_${idx}`;
  card.style.cssText = 'border:1px solid var(--border);border-radius:8px;padding:14px;margin-top:8px;';

  card.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;gap:8px;">
      <div class="gas-card-title-row"><span class="gas-dot ${dotClass}" aria-hidden="true"></span><div class="dg-card-title" style="font-family:'Bebas Neue',sans-serif;font-size:12px;letter-spacing:2px;color:var(--accent);">${cardTitle}</div></div>
      <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;">
        <span class="gas-mod" id="dg${idx}MODDisplay" title="Calculated MOD using selected gas and Max Deco ppO₂">—</span>
        <button onclick="removeDecoGasCard(${idx})" title="Remove this gas"
          style="background:none;border:none;color:var(--muted);cursor:pointer;font-size:16px;line-height:1;padding:0 4px;"
          onmouseover="this.style.color='var(--red)'" onmouseout="this.style.color='var(--muted)'">✕</button>
      </div>
    </div>
    <div class="gas-card-grid" style="margin-bottom:0;">
      <div class="field gas-f-mix">
        <label>Gas Mix</label>
        <select id="dg${idx}Mix" onchange="toggleDecoCustomO2('dg${idx}Mix','dg${idx}CustomField');toggleDecoTrimix(${idx});updateGasMODDisplays()">
          <option value="none" selected>— None —</option>
          <option value="ean50">EAN50 (50%)</option>
          <option value="o2">100% O₂</option>
          <option value="custom">Custom O₂ %</option>
          <option value="trimix">Trimix (O₂/He %)</option>
        </select>
      </div>
      <div class="field gas-f-num" id="dg${idx}CustomField" style="display:none;">
        <label>O₂ %</label>
        <input type="number" id="dg${idx}CustomO2" value="50" min="21" max="100" step="1" oninput="updateGasMODDisplays()">
      </div>
      <div class="field gas-f-num" id="dg${idx}TrimixO2Field" style="display:none;">
        <label>O₂ %</label>
        <input type="number" id="dg${idx}TrimixO2" value="21" min="5" max="60" step="1" oninput="updateGasMODDisplays()" placeholder="21">
      </div>
      <div class="field gas-f-num" id="dg${idx}TrimixHeField" style="display:none;">
        <label>He %</label>
        <input type="number" id="dg${idx}TrimixHe" value="35" min="0" max="90" step="1" oninput="updateGasMODDisplays()" placeholder="35">
      </div>
      <div class="field gas-f-switch">
        <label>Switch Depth <span class="tip-icon" onclick="showTip('Switch Depth','Depth at which this gas becomes optimal to breathe during ascent (or the recommended OC bailout depth). Calculated from O₂ fraction and ppO₂ limits when you generate a schedule; manual override available in Auto/Manual mode.')"><svg fill="none" height="11" viewbox="0 0 11 11" width="11" xmlns="http://www.w3.org/2000/svg"><circle cx="5.5" cy="5.5" r="5" stroke="currentColor" stroke-width="1.1"></circle><path d="M4.1 3.8 Q4.1 2.4 5.5 2.4 Q6.9 2.4 6.9 3.7 Q6.9 4.6 5.5 5.3 L5.5 6.2" fill="none" stroke="currentColor" stroke-linecap="round" stroke-width="1.1"></path><circle cx="5.5" cy="7.4" fill="currentColor" r="0.55"></circle></svg></span></label>
        <input type="text" id="dg${idx}SwitchDepthDisplay" class="switch-depth-display" readonly style="cursor:default;" placeholder="Calculate to see">
      </div>
      <div class="field gas-f-num"><label>${units === 'imperial' ? 'Size (ft³)' : 'Size (L)'}</label><input type="number" id="cylDg${idx}_size" value="${cylDefaults.size}" min="1" max="${cylDefaults.sizeMax}" step="0.5" placeholder="${cylDefaults.size}"></div>
      <div class="field gas-f-num"><label id="cylDg${idx}_pres_lbl">${units === 'imperial' ? 'PSI' : 'Bar'}</label><input type="number" id="cylDg${idx}_pres" value="${cylDefaults.fill}" min="0" max="${cylDefaults.presMax}" step="10" placeholder="${cylDefaults.fill}"></div>
      <input type="hidden" id="cylDg${idx}_reserve" value="${cylDefaults.reserve}">
    </div>`;

  _insertDecoGasCardInIdOrder(card, idx);
  renumberDecoGasCards();
  syncDecoGasCardUi(idx);
}

function addDecoGasCard() {
  if (_dgCardCount() >= _DG_MAX) return;
  const idx = _nextFreeDecoCardIdx();
  if (idx == null) return;
  appendDecoGasCardAtIdx(idx);
  _syncDgNextIdx();
}

function removeDecoGasCard(idx) {
  const card = document.getElementById(`dgCard_${idx}`);
  if (card) card.remove();
  renumberDecoGasCards();
  updateGasMODDisplays();
  updateCcrGasValidation();
  _syncDgNextIdx();
  replanAfterEnvChange();
}

function restoreDecoGasCardLayout(cardIds, nextIdx) {
  getAllDecoGasIds().filter(id => id > 2).forEach(id => removeDecoGasCard(id));
  _dgNextIdx = 3;
  const wanted = (Array.isArray(cardIds) ? cardIds : [1, 2])
    .filter(id => id > 2 && id <= _DG_MAX)
    .sort((a, b) => a - b);
  for (const id of wanted) {
    appendDecoGasCardAtIdx(id);
  }
  _syncDgNextIdx();
  wanted.forEach(id => syncDecoGasCardUi(id));
}

// ── End Dynamic Deco Gas Cards ──────────────────────────────────────────────

// ═══════════════════════════════════════════════
// TRAVEL GAS
// ═══════════════════════════════════════════════

function addTravelGas() {
  const card = document.getElementById('travelGasCard');
  if (card) { card.style.display = 'block'; card.dataset.active = 'true'; }
  document.getElementById('addTravelGasBtn').style.display = 'none';
  updateTravelGasMOD();
}

function removeTravelGas() {
  const card = document.getElementById('travelGasCard');
  if (card) { card.style.display = 'none'; delete card.dataset.active; }
  document.getElementById('addTravelGasBtn').style.display = 'block';
}

/** True when travel gas is configured — card visible, add-btn hidden, or table shows travel descent. */
function isTravelGasConfigured() {
  const card = document.getElementById('travelGasCard');
  if (!card) return false;
  if (card.dataset.active === 'true') return true;
  if (card.style.display && card.style.display !== 'none') return true;
  const btn = document.getElementById('addTravelGasBtn');
  if (btn && btn.style.display === 'none') return true;
  return !!getTravelGasFromTable();
}

/** Read travel gas from rendered descent row when settings card state is stale. */
function getTravelGasFromTable() {
  const rows = document.querySelectorAll('#decoTableBody tr[data-phase="descent"]');
  for (const tr of rows) {
    const mixEl = tr.querySelector('td[data-label="Mix"]');
    if (!mixEl) continue;
    const span = mixEl.querySelector('span');
    const style = span?.getAttribute('style') || mixEl.innerHTML || '';
    if (!/ff9900|ff9f43|#ff9/i.test(style)) continue;
    const depthTxt = tr.querySelector('td[data-label="Depth"]')?.textContent?.trim() || '';
    const m = depthTxt.match(/(?:0→|→)\s*(.+)$/i);
    const depth = m ? m[1].replace(/\s+/g, '') : '';
    const gas = shortMixLabel(mixEl.textContent);
    if (gas && depth) return { gas, depth };
  }
  return null;
}

function getTravelGasInfo() {
  if (!isTravelGasConfigured()) return null;
  const mix = document.getElementById('travelGasMix')?.value || 'air';
  let fN2;
  if (mix === 'air')   fN2 = FN2_AIR;
  else if (mix === 'ean32') fN2 = FN2_EAN32;
  else if (mix === 'ean36') fN2 = FN2_EAN36;
  else if (mix === 'custom') {
    const o2 = parseFloat(document.getElementById('travelGasCustomO2')?.value) || 21;
    fN2 = (100 - Math.min(40, Math.max(16, o2))) / 100;
  } else fN2 = FN2_AIR;

  // Uniform O2/He format for travel gas label
  const _trvO2 = mix === 'air' ? 21 : mix === 'ean32' ? 32 : mix === 'ean36' ? 36
    : mix === 'custom' ? Math.round((1-fN2)*100) : 21;
  const fO2 = 1 - fN2;
  const label = _trvO2 === 21 ? 'Air' : _trvO2 >= 99 ? '100%' : `${_trvO2}/00`;

  const mode = document.getElementById('travelGasSwitchMode')?.value || 'auto';
  const ppO2Bot = parseFloat(document.getElementById('ppo2Bottom')?.value) || 1.4;
  let switchDepthM;
  if (mode === 'manual') {
    const rawVal = parseFloat(document.getElementById('travelGasManualDepth')?.value) || 30;
    switchDepthM = units === 'imperial' ? rawVal / 3.28084 : rawVal;
  } else {
    // Auto: MOD based on bottom gas ppO2 limit
    if (fO2 <= 0) switchDepthM = 0;
    else switchDepthM = calcGasMODm(fO2, ppO2Bot);
  }

  return { fN2, fO2, fHe: 0, label, switchDepthM };
}

/** Resolve travel gas O₂/He for decoGases; null fO2 when fractions are invalid. */
function resolveTravelGasFractions(travelInfo) {
  const fN2 = travelInfo.fN2;
  const rawFHe = travelInfo.fHe;
  if (!isFinite(fN2)) {
    return { valid: false, fHe: 0, reason: 'fN₂ is not a valid number' };
  }
  if (rawFHe != null && !isFinite(rawFHe)) {
    return { valid: false, fHe: 0, reason: 'explicit fHe is not a valid number' };
  }
  if (rawFHe != null && rawFHe < -1e-9) {
    return { valid: false, fHe: 0, reason: 'explicit fHe is negative' };
  }
  const travelFHe = rawFHe != null ? rawFHe : 0;
  if (travelInfo.fO2 != null) {
    if (!isFinite(travelInfo.fO2)) {
      return { valid: false, fHe: travelFHe, reason: 'explicit fO₂ is not a valid number' };
    }
    if (travelInfo.fO2 < -1e-9) {
      return { valid: false, fHe: travelFHe, reason: 'explicit fO₂ is negative' };
    }
    return { valid: true, fO2: Math.max(0, travelInfo.fO2), fHe: travelFHe };
  }
  const inferred = 1 - fN2 - travelFHe;
  if (inferred < -1e-9) {
    return {
      valid: false,
      fHe: travelFHe,
      reason: 'fN₂ + fHe exceeds 1 (sum ' + (fN2 + travelFHe).toFixed(3) + ')',
    };
  }
  return { valid: true, fO2: Math.max(0, inferred), fHe: travelFHe };
}

function escapeHtmlText(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function setTravelGasFractionWarning(reason, log) {
  const safeReason = escapeHtmlText(reason);
  if (log) console.warn('[LSP]', 'Travel gas omitted from deco gases: ' + reason + '. Check travel gas mix.');
  _travelGasFractionWarning =
    '<div class="alert" style="margin-top:8px;background:rgba(255,165,0,0.15);border-color:orange;color:var(--text);">' +
    '<span>⚠</span><div><strong>Travel gas omitted.</strong> ' + safeReason +
    '. Travel gas was not added to the deco gas list — verify your travel gas mix.</div></div>';
}

function warnTravelGasFractionIssue(reason) {
  setTravelGasFractionWarning(reason, true);
}

/** Drop stale travel-gas warning when UI mix is corrected without recalculating. */
function refreshTravelGasFractionWarning() {
  const info = getTravelGasInfo();
  if (!info) {
    _travelGasFractionWarning = '';
    return;
  }
  const resolved = resolveTravelGasFractions(info);
  if (resolved.valid) _travelGasFractionWarning = '';
  else setTravelGasFractionWarning(resolved.reason, false);
}

/** Travel gas line for info banner / text export / PDF — null if not configured. */
function getTravelGasExport() {
  const fromTable = getTravelGasFromTable();
  const info = getTravelGasInfo();
  if (!info && fromTable) return fromTable;
  if (!info) return null;
  const rawD = parseFloat(document.getElementById('decoDepth')?.value) || 0;
  const depthM = units === 'metric' ? rawD : rawD / 3.28084;
  const switchM = Math.min(info.switchDepthM, depthM);
  const dU = units === 'metric';
  const depth = dU ? Math.round(switchM) + 'm' : Math.round(switchM * 3.28084) + 'ft';
  return { gas: shortMixLabel(info.label), depth };
}

function updateTravelGasMOD() {
  const info = getTravelGasInfo();
  const dispEl = document.getElementById('travelGasMODDisplay');
  const manualField = document.getElementById('travelGasManualDepthField');
  const manualLbl   = document.getElementById('travelGasManualDepthLbl');
  const mode = document.getElementById('travelGasSwitchMode')?.value || 'auto';

  // Show/hide manual depth field
  if (manualField) manualField.style.display = mode === 'manual' ? 'block' : 'none';
  if (manualLbl)   manualLbl.textContent = `Switch Depth (${units === 'imperial' ? 'ft' : 'm'})`;

  if (!info) { if (dispEl) dispEl.value = '—'; return; }

  const dU = units === 'metric';
  const modDisp = dU ? info.switchDepthM + ' m' : Math.round(info.switchDepthM * 3.28084) + ' ft';
  const ppO2AtSwitch = ((altSurfaceP + info.switchDepthM * BAR_PER_METRE) * (1 - info.fN2)).toFixed(2);

  if (dispEl) {
    dispEl.value = mode === 'auto'
      ? `${modDisp}  (ppO₂ ${ppO2AtSwitch})`
      : `Auto: ${modDisp}`;
  }
}
