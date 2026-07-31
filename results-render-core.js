/**
 * Schedule results rendering — VPM table/summary and Bühlmann deco table + gas consumption.
 * Loaded by index.html before main inline script.
 * Globals read: units, altSurfaceP, BAR_PER_METRE, OTU_EXPONENT, mGF, narcoticN2, narcoticO2,
 *   _contingencyRunning, _gasRule, fmtPpO2, ppO2Check, calcEND, getTravelGasInfo, toMMSS,
 *   formatDecoZoneStart, formatDecoStopDepth, updateDecoSummaryHtml, buildPlanInfoRowHtml,
 *   _renderResultSummaryStrip, _onPlanResultsReady, decorateDecoTableForV3,
 *   scheduleDecoScheduleStackSync, renderDecoAlerts, _syncCylToGasPlan, calcGasPlan,
 *   lspVolUnit, lspSacUnit, gpVolWithUnit, _applyGasWarningStyles, _updateGasWarningBannerFromCard,
 *   _setGasWarningBanner, ccrGasLitres, accumGasLitres, addBailoutStressReserve, sacDomToLpm,
 *   getContingencySacMultiplier, mToFt, loopMixLabelFor, getGasLabel, mergeCCRSettings,
 *   isRebreatherCircuit, getEffectivePpo2, getEffectiveSetpointAtDepth, updateTissueViz
 * Globals written: lastTissues, window._lastPlan, window._lastGasConsumed,
 *   window._lastBottomPhaseConsumedL, window._contingencyScratchGasConsumed
 */

const GAS_LOW_THRESHOLD_KEY = 'gasLowThresholdPct';

function _gasCardHtml(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function getGasLowThresholdPct() {
  const raw = Number.parseFloat(localStorage.getItem(GAS_LOW_THRESHOLD_KEY));
  const val = Number.isFinite(raw) ? raw : 20;
  return Math.min(50, Math.max(5, Math.round(val)));
}

function setGasLowThresholdPct(value) {
  const next = Math.min(50, Math.max(5, Math.round(Number.parseFloat(value) || 20)));
  localStorage.setItem(GAS_LOW_THRESHOLD_KEY, String(next));
  const mainGasEl = document.getElementById('gasConsumptionSummary');
  if (mainGasEl && mainGasEl.style.display !== 'none' && window._lastGasConsumed) {
    renderGasConsumptionBars(mainGasEl, window._lastGasConsumed, { title: 'Gas Consumption' });
  }
  const emergencyGasEl = document.getElementById('emergencyGasConsumption');
  if (emergencyGasEl && emergencyGasEl.style.display !== 'none' && window._contingencyScratchGasConsumed) {
    renderGasConsumptionBars(emergencyGasEl, window._contingencyScratchGasConsumed, { title: 'Emergency Gas Consumption' });
  }
}

if (typeof window !== 'undefined') {
  window.getGasLowThresholdPct = getGasLowThresholdPct;
  window.setGasLowThresholdPct = setGasLowThresholdPct;
}

function _gasPresText(bar) {
  const unit = units === 'imperial' ? 'psi' : 'bar';
  return `${gpPresDisp(Math.max(0, bar))}${unit}`;
}

function _gasVolText(litres) {
  return `${gpVolDisp(Math.max(0, litres))}${lspVolUnit()}`;
}

function _gasVolPresText(litres, bar) {
  return `${_gasVolText(litres)} (${_gasPresText(bar)})`;
}

function _gasMeasureHtml(text) {
  const raw = String(text == null ? '' : text);
  const match = raw.match(/^(.+?)(ft³|ft3|psi|bar|L)$/i);
  if (!match) return _gasCardHtml(raw);
  return `<strong class="gas-measure"><span class="gas-value">${_gasCardHtml(match[1])}</span><span class="gas-unit" style="font-size:0.82em;font-weight:800;margin-left:0;">${_gasCardHtml(match[2])}</span></strong>`;
}

function _gasPresHtml(bar) {
  return _gasMeasureHtml(_gasPresText(bar));
}

function _gasVolHtml(litres) {
  return _gasMeasureHtml(_gasVolText(litres));
}

function _gasVolPresHtml(litres, bar) {
  return `${_gasVolHtml(litres)} <span class="gas-pres-wrap">(${_gasPresHtml(bar)})</span>`;
}

function scheduleCnsDisplay(cnsPct) {
  const n = Number(cnsPct);
  return Number.isFinite(n) ? `${n.toFixed(1)}%` : '';
}

function scheduleCnsStyle(cnsPct) {
  const n = Number(cnsPct);
  if (!Number.isFinite(n)) return 'color:var(--muted);';
  if (n >= 100) return 'color:var(--red);font-weight:700;';
  if (n >= 80) return 'color:var(--orange);font-weight:700;';
  if (n >= 50) return 'color:var(--yellow);font-weight:700;';
  return 'color:var(--green);';
}

function _gasConsumedForLabel(gasConsumed, label) {
  if (!gasConsumed || !label) return 0;
  if (Number.isFinite(gasConsumed[label])) return gasConsumed[label];
  const key = Object.keys(gasConsumed).find(k => k.toLowerCase() === label.toLowerCase());
  if (key && Number.isFinite(gasConsumed[key])) return gasConsumed[key];
  if (typeof gpRequiredFor === 'function') {
    const matched = gpRequiredFor(label);
    if (Number.isFinite(matched)) return matched;
  }
  return 0;
}

function _configuredGasCylinders() {
  const rows = [];
  const bottom = getBottomGasFractions();
  if (bottom) {
    rows.push({
      key: 'bottom',
      role: 'Bottom',
      label: getGasLabel(bottom.fO2, bottom.fHe),
      sizeId: 'cylBot_size',
      fillId: 'cylBot_pres',
      reserveId: 'cylBot_reserve',
      turn: true,
    });
  }

  if (isTravelGasConfigured() && document.getElementById('cylTravelGas_size')) {
    const travel = getTravelGasInfo();
    rows.push({
      key: 'travel',
      role: 'Travel',
      label: travel?.label || getDecoGasLabel('travelGasMix', 'travelGasCustomO2') || 'Travel',
      sizeId: 'cylTravelGas_size',
      fillId: 'cylTravelGas_pres',
      reserveId: 'cylTravelGas_reserve',
      turn: false,
    });
  }

  let activeDecoOrdinal = 0;
  getAllDecoGasIds().forEach(idx => {
    const fracs = getDecoCardFractions(idx);
    if (!fracs || !(fracs.fO2 > 0)) return;
    activeDecoOrdinal += 1;
    rows.push({
      key: `deco${idx}`,
      role: `Deco ${activeDecoOrdinal}`,
      label: getGasLabel(fracs.fO2, fracs.fHe),
      sizeId: `cylDg${idx}_size`,
      fillId: `cylDg${idx}_pres`,
      reserveId: `cylDg${idx}_reserve`,
      turn: false,
    });
  });
  return rows.filter(row => row.label && document.getElementById(row.sizeId));
}

function _buildGasUsageModel(gasConsumed) {
  const cylinders = _configuredGasCylinders().map(row => {
    const sizeL = gpSizeL(row.sizeId);
    const fillBar = gpPresBar(row.fillId);
    const reserveBar = gpPresBar(row.reserveId);
    const totalL = Math.max(0, sizeL * fillBar);
    const usableL = Math.max(0, sizeL * Math.max(0, fillBar - reserveBar));
    return { ...row, sizeL, fillBar, reserveBar, totalL, usableL };
  });

  const usableByLabel = {};
  const countByLabel = {};
  cylinders.forEach(row => {
    const key = row.label.toLowerCase();
    usableByLabel[key] = (usableByLabel[key] || 0) + row.usableL;
    countByLabel[key] = (countByLabel[key] || 0) + 1;
  });

  return cylinders.map(row => {
    const key = row.label.toLowerCase();
    const requiredL = _gasConsumedForLabel(gasConsumed, row.label);
    let usedL = requiredL;
    if (countByLabel[key] > 1) {
      usedL = usableByLabel[key] > 0
        ? requiredL * (row.usableL / usableByLabel[key])
        : requiredL / countByLabel[key];
    }
    const usedBar = row.sizeL > 0 ? usedL / row.sizeL : 0;
    const remainingUsableL = row.usableL - usedL;
    const remainingTotalL = row.totalL - usedL;
    const remainingBar = row.sizeL > 0 ? remainingTotalL / row.sizeL : 0;
    const shortfallL = Math.max(0, -remainingUsableL);
    const remainingPercent = row.usableL > 0 ? Math.max(0, remainingUsableL / row.usableL * 100) : 0;
    const remainingPercentOfTotal = row.totalL > 0 ? Math.min(100, Math.max(0, remainingTotalL / row.totalL * 100)) : 0;
    const turnPressureBar = row.turn && typeof computePooledBottomTurnBars === 'function'
      ? computePooledBottomTurnBars(row.sizeL, row.fillBar, row.reserveBar, 0, _gasRule === 'half' ? 0.5 : 1 / 3)?.turnBar
      : null;
    return {
      ...row,
      displayName: `${row.label} ${row.role}`,
      usedL,
      usedBar,
      remainingTotalL: Math.max(0, remainingTotalL),
      remainingBar: Math.max(0, remainingBar),
      remainingPercent,
      remainingPercentOfTotal,
      shortfallL,
      turnPressureBar,
    };
  });
}

function _gasUsageStatus(row, threshold) {
  if (!(row.totalL > 0) || row.shortfallL > 0) return 'nogas';
  if (row.remainingPercent < threshold) return 'critical';
  if (row.remainingPercent <= 50) return 'low';
  return 'ok';
}

function _gasWarningMessages(rows, threshold) {
  const messages = [];
  const groupedShortfalls = new Map();
  rows.forEach(row => {
    const status = _gasUsageStatus(row, threshold);
    if (status !== 'critical' && status !== 'nogas') return;
    const labelKey = String(row.label || row.displayName || '').toLowerCase();
    if (!(row.totalL > 0)) {
      if (!groupedShortfalls.has(`nosupply:${labelKey}`)) {
        groupedShortfalls.set(`nosupply:${labelKey}`, {
          type: 'nosupply',
          label: row.label || row.displayName,
          displayNames: [],
        });
      }
      groupedShortfalls.get(`nosupply:${labelKey}`).displayNames.push(row.displayName);
    } else if (row.shortfallL > 0) {
      if (!groupedShortfalls.has(`short:${labelKey}`)) {
        groupedShortfalls.set(`short:${labelKey}`, {
          type: 'short',
          label: row.label,
          displayNames: [],
          usedL: 0,
          totalL: 0,
        });
      }
      const group = groupedShortfalls.get(`short:${labelKey}`);
      group.displayNames.push(row.displayName);
      group.usedL += row.usedL;
      group.totalL += row.totalL;
    } else {
      messages.push(`Critical: ${_gasCardHtml(row.displayName)} below <strong class="gas-measure">${threshold}<span class="gas-unit">%</span></strong> remaining`);
    }
  });
  groupedShortfalls.forEach(group => {
    const roleText = group.displayNames.length > 1
      ? ` (${group.displayNames.map(name => String(name).replace(String(group.label), '').trim()).filter(Boolean).join(' + ')})`
      : '';
    if (group.type === 'nosupply') {
      messages.push(`No gas supply: ${_gasCardHtml(group.label)}${_gasCardHtml(roleText)} has no configured cylinder supply`);
    } else {
      messages.push(`No gas supply: ${_gasCardHtml(group.label)}${_gasCardHtml(roleText)} needs ${_gasVolHtml(group.usedL)}, cylinders have ${_gasVolHtml(group.totalL)}`);
    }
  });
  return messages;
}

function _gasWarningMessageForRow(row, threshold) {
  const status = _gasUsageStatus(row, threshold);
  if (status !== 'critical' && status !== 'nogas') return '';
  if (!(row.totalL > 0)) {
    return `No gas supply: ${_gasCardHtml(row.displayName)} has no configured cylinder supply`;
  }
  if (row.shortfallL > 0) {
    return `No gas supply: ${_gasCardHtml(row.displayName)} needs ${_gasVolHtml(row.usedL)}, cylinder has ${_gasVolHtml(row.totalL)}`;
  }
  return `Critical: ${_gasCardHtml(row.displayName)} below <strong class="gas-measure">${threshold}<span class="gas-unit">%</span></strong> remaining`;
}

function renderGasConsumptionBars(container, gasConsumed, options) {
  if (!container) return;
  const title = options?.title || 'Gas Consumption';
  const threshold = getGasLowThresholdPct();
  const rows = _buildGasUsageModel(gasConsumed || {});
  if (!rows.length) {
    container.innerHTML = '';
    container.style.display = 'none';
    _setGasWarningBanner('');
    return;
  }

  const rowHtml = rows.map(row => {
    const status = _gasUsageStatus(row, threshold);
    const narcoticTarget = window._lastNarcoticGasTarget || null;
    const isNarcoticTarget = !!(narcoticTarget
      && String(narcoticTarget.label || '').toLowerCase() === String(row.label || '').toLowerCase()
      && String(narcoticTarget.role || '').toLowerCase() === String(row.role || '').toLowerCase());
    const turn = Number.isFinite(row.turnPressureBar)
      ? `<span>Turn Pressure: ${_gasPresHtml(row.turnPressureBar)}</span>`
      : '';
    const cardWarning = _gasWarningMessageForRow(row, threshold);
    const cardWarningHtml = cardWarning
      ? `<div class="gas-usage-inline-warning gas-usage-inline-warning--${status}"><span aria-hidden="true">&#9888;</span><div class="gas-warning-copy">${cardWarning}</div></div>`
      : '';
    const titleClass = isNarcoticTarget ? ' gas-usage-title--narcotic' : '';
    const roleClass = isNarcoticTarget ? ' gas-usage-role--narcotic' : '';
    const roleText = isNarcoticTarget ? String(row.role || '').toLowerCase() : row.role;
    return `<div class="gas-usage-card gas-usage-card--${status}${isNarcoticTarget ? ' gas-usage-card--narcotic' : ''}" data-gas-label="${_gasCardHtml(row.label)}" data-gas-role="${_gasCardHtml(row.role)}" style="--gas-remaining-pct:${row.remainingPercentOfTotal.toFixed(2)}%;">
      <div class="gas-usage-head">
        <div class="gas-usage-title${titleClass}"><span class="gas-usage-mix">${_gasCardHtml(row.label)}</span> <span class="gas-usage-role${roleClass}">${_gasCardHtml(roleText)}</span></div>
        <div class="gas-usage-remaining">${_gasVolHtml(row.remainingTotalL)} <span>(${_gasPresHtml(row.remainingBar)})</span></div>
      </div>
      ${cardWarningHtml}
      <div class="gas-usage-scale"><span>0</span><span>${_gasVolHtml(row.totalL)} <span class="gas-pres-wrap">(${_gasPresHtml(row.fillBar)})</span></span></div>
      <div class="gas-usage-track" aria-label="${_gasCardHtml(row.displayName)} remaining gas"><div class="gas-usage-remaining-bar"></div></div>
      <div class="gas-usage-foot"><span>Used: ${_gasVolHtml(row.usedL)} <span class="gas-pres-wrap">(${_gasPresHtml(row.usedBar)})</span></span>${turn}</div>
    </div>`;
  }).join('');

  const narcoticSource = !_contingencyRunning ? document.getElementById('decoAlertsNarcotic') : null;
  const narcoticHtml = narcoticSource ? String(narcoticSource.innerHTML || '').trim() : '';
  const gasCardNarcoticHtml = narcoticHtml
    ? `<div class="gas-consumption-narcotic">${narcoticHtml}</div>`
    : '';
  const sacUnit = lspSacUnit();
  const sacBottom = document.getElementById('sacBottom')?.value || '';
  const sacDeco = document.getElementById('sacDeco')?.value || '';
  container.innerHTML = `<div class="card collapsible card-open gas-consumption-card">
    <div class="card-title" onclick="toggleCard(this)">${_gasCardHtml(title)}<span class="card-caret">v</span></div>
    <div class="card-collapsible-body">
      <div class="gas-consumption-toolbar">
        <label class="gas-threshold-control">Low gas
          <input id="gasLowThresholdPct" type="number" min="5" max="50" step="1" value="${threshold}" onchange="setGasLowThresholdPct(this.value)" inputmode="numeric">
          <span>%</span>
        </label>
      </div>
      ${gasCardNarcoticHtml}
      <div class="gas-consumption-bars">${rowHtml}</div>
      <div class="gas-consumption-note">SAC bottom: ${_gasCardHtml(sacBottom)} ${_gasCardHtml(sacUnit)} &middot; deco: ${_gasCardHtml(sacDeco)} ${_gasCardHtml(sacUnit)}</div>
    </div>
  </div>`;
  container.style.display = 'block';
  _updateGasWarningBannerFromCard(container);
}

// AUDIT-UNIT:UI-VPM-RENDER
function renderVPMResults(result, settings, depthM, bt, bottomO2pct, bottomHePct, decoGases, model, _vpmBotFracs) {
  const dU = units === 'metric';
  const du = dU ? 'm' : 'ft';
  const surfP = altSurfaceP || 1.01325; // altitude-correct surface pressure for ppO₂ display
  const plan = result.plan || [];
  const tbody = document.getElementById('decoTableBody');
  if (!tbody) return;

  // Gas color helper
  function gasColor(o2pct) {
    if (o2pct >= 99) return 'var(--accent)';
    if (o2pct >= 45) return 'var(--green)';
    return 'var(--text)';
  }
  function fmtT(t) {
    const total = Math.round(t * 60), m = Math.floor(total / 60), s = total % 60;
    return `${m}:${String(s).padStart(2,'0')}`;
  }
  function fmtRT(t) {
    const total = Math.round(t * 60), m = Math.floor(total / 60), s = total % 60;
    return `${m}:${String(s).padStart(2,'0')}`;
  }

  const _vpmCcr = getCCRSettingsFromDOM();
  const _vpmOnLoop = isRebreatherCircuit(_vpmCcr.circuit) && !_vpmCcr.bailout;
  function vpmDisplayPpo2(depthM, o2pct, hepct, seg) {
    const fO2 = o2pct / 100;
    const fHe = hepct / 100;
    const fN2 = Math.max(0, 1 - fO2 - fHe);
    if (_vpmOnLoop) {
      const pAmb = surfP + depthM * BAR_PER_METRE;
      const sp = (seg && seg.setpoint > 0)
        ? seg.setpoint
        : getEffectiveSetpointAtDepth(depthM, _vpmCcr, surfP);
      const ccrDisp = {
        ..._vpmCcr,
        scrRuntimeMin: seg && seg.runtime != null ? seg.runtime : 0,
      };
      return getEffectivePpo2(pAmb, sp, fO2, ccrDisp, depthM, fHe).toFixed(2);
    }
    return fmtPpO2(ppO2Check(depthM, fN2, fHe));
  }

  let html = '';
  let prevGas = `${bottomO2pct}/${bottomHePct}`;
  let gasLabel = getGasLabel(bottomO2pct/100, bottomHePct/100);
  let vpmRtAtBottomEnd = 0;
  let vpmStopCapHit = false;

  plan.forEach(seg => {
    const segGas = seg.gas || prevGas;
    const gasParts = segGas.split('/');
    const o2pct = parseInt(gasParts[0]) || bottomO2pct;
    const hepct = parseInt(gasParts[1]) || 0;
    const gc = gasColor(o2pct);
    const gasDisp = _vpmOnLoop
      ? loopMixLabelFor(getGasLabel(o2pct/100, hepct/100), _vpmCcr)
      : getGasLabel(o2pct/100, hepct/100);

    // Gas switch row
    if (!_vpmOnLoop && segGas !== prevGas && seg.type !== 'descent') {
      const switchDepth = seg.type === 'stop' ? seg.depth : (seg.startDepth || seg.depth || 0);
      const switchDepthDisp = dU ? switchDepth + du : Math.round(switchDepth * 3.28084) + du;
      const switchPpO2 = vpmDisplayPpo2(switchDepth, o2pct, hepct, seg);
      const switchMixDisp = gasDisp.replace(/\s+/g, '').toUpperCase();
      html += `<tr data-phase="switch">
        <td style="text-align:center;">⇄</td>
        <td data-label="Depth">${switchDepthDisp}</td>
        <td data-label="Stop"></td>
        <td data-label="Run"></td>
        <td data-label="Mix">${switchMixDisp}</td>
        <td data-label="PPO2">${switchPpO2}</td>
        <td data-label="CNS"></td>
        <td data-label="EAD"></td>
      </tr>`;
      prevGas = segGas;
    }

    if (seg.type === 'descent') {
      if (seg.runtime) vpmRtAtBottomEnd = seg.runtime;
      const rtDisp = fmtRT(seg.runtime);
      html += `<tr class="asc-row" data-phase="descent">
        <td><span style="font-size:18px;color:var(--red);">↓</span></td>
        <td data-label="Depth">0 → ${dU ? seg.endDepth : Math.round(seg.endDepth * 3.28084)}${du}</td>
        <td data-label="Stop"></td>
        <td data-label="Run" style="color:var(--accent);">${rtDisp}</td>
        <td data-label="Mix" style="color:${gc};">${gasDisp}</td>
        <td data-label="PPO2" style="color:var(--muted);">${vpmDisplayPpo2(seg.endDepth, o2pct, hepct, seg)}</td>
        <td data-label="CNS" style="${scheduleCnsStyle(seg._cumCNS)}">${scheduleCnsDisplay(seg._cumCNS)}</td>
        <td data-label="EAD" style="color:var(--muted);">—</td>
      </tr>`;
      prevGas = segGas;
    } else if (seg.type === 'bottom') {
      vpmRtAtBottomEnd = seg.runtime;
      const rtDisp = fmtRT(seg.runtime);
      const ppO2b = vpmDisplayPpo2(seg.depth, o2pct, hepct, seg);
      html += `<tr class="btm-row" data-phase="bottom">
        <td><span style="color:var(--accent);font-size:13px;">🔵</span></td>
        <td data-label="Depth" style="color:var(--accent);">${dU ? seg.depth : Math.round(seg.depth * 3.28084)}${du}</td>
        <td data-label="Stop" style="color:var(--accent);">${fmtT(seg.time)}</td>
        <td data-label="Run" style="color:var(--accent);">${rtDisp}</td>
        <td data-label="Mix" style="color:${gc};">${gasDisp}</td>
        <td data-label="PPO2" style="color:var(--muted);">${ppO2b}</td>
        <td data-label="CNS" style="${scheduleCnsStyle(seg._cumCNS)}">${scheduleCnsDisplay(seg._cumCNS)}</td>
        <td data-label="EAD" style="color:var(--muted);">—</td>
      </tr>`;
    } else if (seg.type === 'ascent') {
      const rtDisp = fmtRT(seg.runtime);
      const ppO2a = vpmDisplayPpo2(seg.startDepth, o2pct, hepct, seg);
      const toD   = dU ? seg.endDepth   : Math.round(seg.endDepth   * 3.28084);
      html += `<tr class="asc-row" data-phase="ascent">
        <td><span class="asc-color" style="font-size:18px;">↑</span></td>
        <td data-label="Depth" class="asc-color">${toD}${du}</td>
        <td data-label="Stop" class="asc-color" style="font-size:11px;color:var(--muted);">${fmtT(seg.time)}</td>
        <td data-label="Run" class="asc-color">${rtDisp}</td>
        <td data-label="Mix" style="color:${gc};">${gasDisp}</td>
        <td data-label="PPO2" style="color:var(--muted);">${ppO2a}</td>
        <td data-label="CNS" style="${scheduleCnsStyle(seg._cumCNS)}">${scheduleCnsDisplay(seg._cumCNS)}</td>
        <td data-label="EAD" style="color:var(--muted);"></td>
      </tr>`;
    } else if (seg.type === 'stop') {
      if (seg.vpmStopCapHit) vpmStopCapHit = true;
      const rtDisp = fmtRT(seg.runtime);
      const ppO2s = vpmDisplayPpo2(seg.depth, o2pct, hepct, seg);
      const ppO2Color = ppO2DisplayStyle(ppO2s, 1.6);
      const capNote = seg.vpmStopCapHit ? ' title="Stop capped at safety limit — ceiling not cleared"' : '';
      // Cumulative CNS row highlight (same logic as Bühlmann, uses _cumCNS stored by VPM engine)
      const cumCnsPctVPM = seg._cumCNS != null ? seg._cumCNS : 0;
      const cnsTierVPM = seg.vpmStopCapHit ? '' : (cumCnsPctVPM >= 100 ? '100' : cumCnsPctVPM >= 80 ? '80' : '');
      const rowBgVPM = seg.vpmStopCapHit
        ? 'background:rgba(255,140,0,0.15);'
        : cnsTierVPM === '100'
        ? 'background:#ffff00;color:#111;'
        : cnsTierVPM === '80'
          ? 'background:rgba(255,255,0,0.25);'
          : '';
      html += `<tr class="deco-row" data-phase="deco" style="${rowBgVPM}"${capNote} ${cnsTierVPM ? `data-cnshi="1" data-cns-tier="${cnsTierVPM}"` : ''}>
        <td><span style="color:${seg.vpmStopCapHit ? 'var(--orange)' : rowBgVPM ? '#b30000' : 'var(--red)'};font-size:13px;">${seg.vpmStopCapHit ? '⚠' : '●'}</span></td>
        <td data-label="Depth" style="color:${seg.vpmStopCapHit ? 'var(--orange)' : rowBgVPM ? '#b30000' : 'var(--red)'};font-weight:600;">${dU ? seg.depth : Math.round(seg.depth * 3.28084)}${du}</td>
        <td data-label="Stop" style="color:${seg.vpmStopCapHit ? 'var(--orange)' : rowBgVPM ? '#b30000' : 'var(--red)'};font-weight:600;">${fmtT(seg.time)}${seg.vpmStopCapHit ? ' ⚠' : ''}</td>
        <td data-label="Run" style="color:var(--text);">${rtDisp}</td>
        <td data-label="Mix" style="color:${gc};">${gasDisp}</td>
        <td data-label="PPO2" style="${rowBgVPM?'color:#b30000;font-weight:700;':ppO2Color}">${ppO2s}</td>
        <td data-label="CNS" style="${rowBgVPM?'color:#b30000;font-weight:700;':scheduleCnsStyle(cumCnsPctVPM)}">${scheduleCnsDisplay(cumCnsPctVPM)}</td>
        <td data-label="EAD" style="color:var(--muted);">—</td>
      </tr>`;
    }

    if (seg.type !== 'descent') prevGas = segGas;
  });

  tbody.innerHTML = html;

  if (vpmStopCapHit) {
    const capNote = document.getElementById('vpmStopCapNote');
    if (capNote) {
      capNote.style.display = 'block';
      capNote.textContent = 'One or more stops were limited to the safety time limit — VPM ceiling could not be cleared at that depth.';
    }
  } else {
    const capNote = document.getElementById('vpmStopCapNote');
    if (capNote) capNote.style.display = 'none';
  }

  // ── TOTALS FOOTER ROW (same format as Bühlmann) ──────────────────────────
  const rt   = result.totalRuntime;
  const deco = result.stops?.reduce((a, s) => a + (s.time || 0), 0) || 0;
  const modelName = model === 'VPMB' ? 'VPM-B' : 'VPM-B/GFS';
  const cons = document.getElementById('conservatismSelect')?.value || '0';
  const gfHi = model === 'VPMB_GFS' ? ` · GF Hi ${mGF.high}` : '';
  const cnsDisp = result.totalCNS != null ? result.totalCNS.toFixed(1) : '—';
  const otuDisp = result.totalOTU != null ? Math.round(result.totalOTU) : '—';
  // PrT
  const prtValVPM = (depthM * BAR_PER_METRE) * Math.sqrt(bt);
  const prtDispVPM = prtValVPM.toFixed(1);
  const prtColorVPM = prtValVPM < 15 ? 'var(--green)' : prtValVPM < 25 ? 'var(--yellow)' : prtValVPM < 40 ? 'var(--orange)' : 'var(--red)';
  const cnsFootColor = result.totalCNS != null ? (result.totalCNS >= 100 ? 'var(--red)' : result.totalCNS >= 80 ? 'var(--orange)' : result.totalCNS >= 50 ? 'var(--yellow)' : 'var(--green)') : 'var(--muted)';
  const decoZoneDispVPM = formatDecoZoneStart(result.decoZoneStart);
  const vpmFirstStop = result.stops?.length ? Math.max(...result.stops.map(s => s.depth)) : 0;
  const decoStopDispVPM = formatDecoStopDepth(vpmFirstStop);
  const vpmTtsMin = Math.max(0, rt - (vpmRtAtBottomEnd || 0));
  const vpmTtsMMSS = toMMSS(vpmTtsMin);
  const otuFootColorVPM = (result.totalOTU ?? 0) >= 300 ? 'var(--red)' : (result.totalOTU ?? 0) >= 200 ? 'var(--orange)' : (result.totalOTU ?? 0) >= 100 ? 'var(--yellow)' : 'var(--green)';
  tbody.innerHTML += buildPlanInfoRowHtml({
    runTime: toMMSS(rt),
    tts: vpmTtsMMSS,
    decoTime: toMMSS(deco),
    cns: cnsDisp !== '—' ? cnsDisp + '%' : '—',
    otu: otuDisp,
    prt: prtDispVPM,
    prtColor: prtColorVPM,
    cnsColor: cnsFootColor,
    otuColor: otuFootColorVPM,
    hasDeco: deco > 0,
    decozone: decoZoneDispVPM,
    decoStop: decoStopDispVPM,
    surfaceGF: window._lastPlan ? window._lastPlan.surfaceGF : null,
  });
  _renderResultSummaryStrip({
    runTime: toMMSS(rt),
    decoTime: toMMSS(deco),
    cns: cnsDisp !== '—' ? cnsDisp + '%' : '—',
    firstStop: decoStopDispVPM,
    surfaceGF: window._lastPlan && Number.isFinite(window._lastPlan.surfaceGF) ? `${window._lastPlan.surfaceGF.toFixed(0)}%` : '—',
    otu: otuDisp,
    tts: vpmTtsMMSS,
    decozone: decoZoneDispVPM,
  });
  _onPlanResultsReady();

  decorateDecoTableForV3();
  scheduleDecoScheduleStackSync();

  // Surface Interval panel (collapsed) — pre-fill Dive 1 from this dive
  if (!_contingencyRunning) renderSurfIntPanel('tecSurfIntContainer', 'tecSi', depthM, bt);
  if (!_contingencyRunning) renderTissueLoadChart();

  // ── POST-RENDER: show/hide same cards as Bühlmann ────────────────────────
  // Dive graph — works for VPM (reads table rows)
  const _fdgcVPM = document.getElementById('fullDiveGraphCard');
  if (_fdgcVPM) _fdgcVPM.style.display = 'block';
  _syncGraphsSectionHeads?.();
  const vpmScheduleGen = window._decoScheduleSeq;
  scheduleDecoProfileFullDraw?.(() => isStaleDecoScheduleGen(vpmScheduleGen));

  // Gas Consumption — compute from rendered table rows
  const gasConsVPM = {};
  const sacBotVPM  = sacDomToLpm('sacBottom', 20);
  const sacDecoVPM = sacDomToLpm('sacDeco', 15);
  const sacBottomDisp = parseFloat(document.getElementById('sacBottom')?.value) || 20;
  const sacDecoDisp   = parseFloat(document.getElementById('sacDeco')?.value) || 15;
  document.querySelectorAll('#decoTableBody tr[data-phase]').forEach(tr => {
    const ph = tr.dataset.phase;
    if (ph === 'switch' || ph === 'totals') return;
    const mixRaw = tr.querySelector('td[data-label="Mix"]')?.textContent?.trim() || '';
    const stopRaw = tr.querySelector('td[data-label="Stop"]')?.textContent?.trim() || '';
    const depthRaw = tr.querySelector('td[data-label="Depth"]')?.textContent?.trim() || '';
    const depthM2 = endParseDepthM(depthRaw) ?? (parseFloat(depthRaw) || 0);
    const durMin = (() => { const p = stopRaw.split(':'); return p.length===2 ? parseInt(p[0]) + parseInt(p[1])/60 : parseFloat(stopRaw)||0; })();
    if (!durMin || !mixRaw || mixRaw === '-') return;
    const gasKey = (_vpmOnLoop && !isCcrOnLoopGasLabel(mixRaw))
      ? loopMixLabelFor(mixRaw.replace(/^(CCR|PSCR)\s+/i, ''), _vpmCcr)
      : mixRaw;
    const sac = (ph === 'bottom') ? sacBotVPM : sacDecoVPM;
    accumGasLitres(gasConsVPM, gasKey, ccrGasLitres(gasKey, depthM2, durMin, sac));
  });
  if (_vpmOnLoop) {
    const reserveMin = (_vpmCcr.stressTimeMin || 0) + (_vpmCcr.problemSolveMin || 0);
    if (reserveMin > 0) {
      const stopDepths = (result.stops || []).map(s => s.depth).filter(d => d != null && d >= 0);
      const stressSac = _vpmCcr.sacStress || sacBotVPM;
      addBailoutStressReserve(
        (label, d, min, sac) => { accumGasLitres(gasConsVPM, label, ccrGasLitres(label, d, min, sac)); },
        reserveMin, depthM, stopDepths, _vpmBotFracs.fO2, _vpmBotFracs.fHe, stressSac
      );
    }
  }
  const gasElVPM = _contingencyRunning
    ? document.getElementById('emergencyGasConsumption')
    : document.getElementById('gasConsumptionSummary');
  if (gasElVPM && Object.keys(gasConsVPM).length) {
    const cylIds = [['cylBot_size','cylBot_pres'],['cylDg1_size','cylDg1_pres'],['cylDg2_size','cylDg2_pres'],['cylTravelGas_size','cylTravelGas_pres']];
    const cylCapVPM = {};
    Object.keys(gasConsVPM).forEach((label, idx) => {
      const [sId,pId] = cylIds[idx] || [];
      if (!sId) return;
      const szRaw = parseFloat(document.getElementById(sId)?.value) || 0;
      const sz = units === 'imperial' ? szRaw * 28.3168 : szRaw;
      const prRaw = parseFloat(document.getElementById(pId)?.value) || 0;
      const pr = units === 'imperial' ? prRaw / 14.5038 : prRaw;
      if (sz > 0 && pr > 0) cylCapVPM[label] = sz * pr;
    });
    // ── Build rule-of-thirds table ──
    const volUnitV = lspVolUnit();
    const presUnitV = units === 'imperial' ? 'psi' : 'bar';
    const sacUnitVPM = lspSacUnit();
    const ruleName = (_gasRule === 'half') ? 'Half Tank (1/2)' : 'Rule of Thirds (1/3)';
    const fraction = (_gasRule === 'half') ? 0.5 : (1/3);

    // Helper: get cylinder info from Deco Schedule inputs
    const cylMap = {
      // gasLabel → [sizeId, fillId, reserveId]
    };
    const gasLabels = Object.keys(gasConsVPM);
    // Build label→cylinders map (same-mix cylinders pool their capacity)
    const _cylDefsVPM = [
      { ids:['cylBot_size','cylBot_pres','cylBot_reserve'],                   label: gasLabels[0] || null,                                              isBottom: true  },
      { ids:['cylTravelGas_size','cylTravelGas_pres','cylTravelGas_reserve'], label: (getTravelGasInfo()?.label || null),                                isBottom: false },
      ...getAllDecoGasIds().map(n => ({
        ids: [`cylDg${n}_size`, `cylDg${n}_pres`, `cylDg${n}_reserve`],
        label: getDecoGasLabel(`dg${n}Mix`, `dg${n}CustomO2`) || null,
        isBottom: false,
      })),
    ];
    const _cylByLabelVPM = {};
    _cylDefsVPM.forEach(cyl => {
      if (!cyl.label) return;
      if (!_cylByLabelVPM[cyl.label]) _cylByLabelVPM[cyl.label] = [];
      _cylByLabelVPM[cyl.label].push(cyl);
    });

    let tableRows = '';
    let warnings = '';
    let hasAnyTurn = false;

    for (const [gas, reqL] of Object.entries(gasConsVPM)) {
      const cylsVPM = _cylByLabelVPM[gas] || [];
      let sizeRaw = 0, fillRaw = 0, resRaw = 0;
      let usableLVPM = null;
      let hasCylVPM  = false;
      cylsVPM.forEach(cyl => {
        const ids = cyl.ids;
        const sr = parseFloat(document.getElementById(ids[0])?.value) || 0;
        const fr = parseFloat(document.getElementById(ids[1])?.value) || 0;
        const rr = parseFloat(document.getElementById(ids[2])?.value) || 0;
        const sL  = units === 'imperial' ? sr * 28.3168 : sr;
        const fB  = units === 'imperial' ? fr / 14.5038 : fr;
        const rB  = units === 'imperial' ? rr / 14.5038 : rr;
        if (sL > 0 && fB > rB) { usableLVPM = (usableLVPM || 0) + (fB - rB) * sL; hasCylVPM = true; }
        if (cyl.isBottom) { sizeRaw = sr; fillRaw = fr; resRaw = rr; }
      });
      const sizeL = units === 'imperial' ? sizeRaw * 28.3168 : sizeRaw;
      const fillBar = units === 'imperial' ? fillRaw / 14.5038 : fillRaw;
      const resBar  = units === 'imperial' ? resRaw  / 14.5038 : resRaw;
      const isBottom = gas === gasLabels[0]; // first gas = bottom gas
      const reqVolV = gpVolWithUnit(reqL);

      let travelPooledLVPM = 0;
      if (isBottom) {
        const tSr = parseFloat(document.getElementById('cylTravelGas_size')?.value) || 0;
        const tFr = parseFloat(document.getElementById('cylTravelGas_pres')?.value) || 0;
        const tRr = parseFloat(document.getElementById('cylTravelGas_reserve')?.value) || 0;
        const tSL = units === 'imperial' ? tSr * 28.3168 : tSr;
        const tFB = units === 'imperial' ? tFr / 14.5038 : tFr;
        const tRB = units === 'imperial' ? tRr / 14.5038 : tRr;
        if (tSL > 0 && tFB > tRB) travelPooledLVPM = (tFB - tRB) * tSL;
      }

      const hasCyl = hasCylVPM || (sizeL > 0 && fillBar > resBar);
      let usableL = usableLVPM !== null ? usableLVPM : (hasCyl ? (fillBar - resBar) * sizeL : null);
      if (isBottom && usableL != null && travelPooledLVPM > 0) usableL += travelPooledLVPM;
      const pooledTurn = (isBottom && sizeL > 0 && fillBar > resBar && typeof computePooledBottomTurnBars === 'function')
        ? computePooledBottomTurnBars(sizeL, fillBar, resBar, travelPooledLVPM, fraction)
        : null;
      const portionL = pooledTurn ? pooledTurn.portionL : (usableL != null ? usableL * fraction : null);
      const turnBar  = pooledTurn ? pooledTurn.turnBar : ((hasCyl && isBottom && sizeL > 0) ? fillBar - (portionL / sizeL) : null);

      const availVolV = usableL != null ? gpVolWithUnit(usableL) : null;
      const reqValid = Number.isFinite(reqL);
      const short = reqValid && usableL != null && reqL > usableL;
      const tight = reqValid && usableL != null && !short && reqL > usableL * 0.90;
      const sufficient = reqValid && usableL != null && !short;

      // Sufficiency colour
      const sufCol = !reqValid ? 'var(--orange)' : short ? 'var(--red)' : tight ? 'var(--yellow)' : hasCyl ? 'var(--green)' : 'var(--muted)';
      const sufIcon = !reqValid ? '—' : short ? '✗' : tight ? '⚠' : hasCyl ? '✓' : '—';
      const sufTxt  = !reqValid ? 'Invalid gas' : short ? `Short ${gpVolWithUnit(reqL - (usableL || 0))}` : tight ? 'Tight' : hasCyl ? 'OK' : 'No cyl data';

      // Thirds/Half portion in litres (bottom only)
      const portionDispV = (isBottom && portionL != null) ? gpVolWithUnit(portionL) : '—';
      const portionColorV = (isBottom && portionL != null) ? 'var(--accent)' : 'var(--muted)';
      // Turn pressure (bottom only)
      const turnDispV = (isBottom && turnBar != null) ? (units==='imperial'?Math.round(turnBar*14.5038):Math.round(turnBar)) : null;
      const turnCellV = (isBottom && turnDispV != null)
        ? `<td style="color:var(--accent);font-weight:700;">${turnDispV} ${presUnitV}</td>`
        : `<td style="color:var(--muted);font-size:10px;">one-way</td>`;
      if (isBottom && turnDispV != null) hasAnyTurn = true;
      // Reserve (bottom cyl)
      const resDispV = resBar > 0 ? `${units==='imperial'?Math.round(resBar*14.5038):Math.round(resBar)} ${presUnitV}` : '—';

      const rowBgV = short ? 'rgba(220,50,50,0.07)' : tight ? 'rgba(255,180,0,0.07)' : '';
      const reqColorV   = short ? 'var(--red)'  : 'var(--text)';
      const availColorV = short ? 'var(--red)'  : tight ? 'var(--yellow)' : hasCyl ? 'var(--green)' : 'var(--muted)';
      const statusCellV = short
        ? `<td style="color:var(--red);font-weight:700;">✗ short ${gpVolWithUnit(reqL - (usableL || 0))}</td>`
        : tight
          ? `<td style="color:var(--yellow);font-weight:700;">⚠ tight</td>`
          : (isBottom && turnDispV != null)
            ? `<td style="color:var(--accent);">⟳ turn${usableL!=null?` <span style="color:var(--green);font-size:10px;">✓ ${reqVolV} needed</span>`:''}</td>`
            : `<td style="color:${sufCol};font-weight:700;">${sufIcon} ${sufTxt}</td>`;
      tableRows += `<tr style="background:${rowBgV};">
        <td style="font-weight:700;">${gas}</td>
        <td style="color:${reqColorV};font-weight:${short?'700':'400'};">${reqVolV}</td>
        <td style="color:${availColorV};font-weight:${(!short&&hasCyl)?'700':'400'};">${availVolV != null ? availVolV : '—'}</td>
        <td style="color:${portionColorV};">${portionDispV}</td>
        ${turnCellV}
        <td style="color:var(--muted);">${resDispV}</td>
        ${statusCellV}
      </tr>`;

      if (short) {
        // Compute max BT suggestion
        const bt = parseFloat(getPlannerInputEl('decoBT')?.value) || 0;
        let btSuggest = '';
        if (usableL === 0) {
          btSuggest = 'No usable gas available — fill pressure equals or is below reserve. Use a larger cylinder or higher fill.';
        } else if (bt > 0 && reqL > 0) {
          const rate = reqL / bt;
          const maxBT = Math.max(1, Math.floor(usableL / rate));
          const maxPooled = (typeof computePooledBottomTurnBars === 'function')
            ? computePooledBottomTurnBars(sizeL, fillBar, resBar, travelPooledLVPM, fraction)
            : null;
          const maxTurnBar = maxPooled
            ? maxPooled.turnBar
            : (sizeL > 0 ? fillBar - (usableL * fraction) / sizeL : null);
          const maxTurnDisp = maxTurnBar != null
            ? (units === 'imperial' ? Math.round(maxTurnBar * 14.5038) : Math.round(maxTurnBar))
            : null;
          btSuggest = maxTurnDisp != null
            ? `Shorten BT to <strong>${maxBT} min</strong> and turn at <strong>${maxTurnDisp} ${presUnitV}</strong>, or use a larger cylinder / add a stage.`
            : `Shorten BT to <strong>${maxBT} min</strong>, or use a larger cylinder / add a stage.`;
        }
        warnings += `<div class="alert dang" style="margin-top:6px;"><span>⚠</span><div><strong>${gas} insufficient</strong> — need ${reqVolV}, have ${availVolV}. Short by <strong>${gpVolWithUnit(reqL - usableL)}</strong>.${btSuggest ? '<br>' + btSuggest : ''}</div></div>`;
      }
    }

    if (_contingencyRunning) {
      window._contingencyScratchGasConsumed = Object.assign({}, gasConsVPM);
      renderGasConsumptionBars(gasElVPM, gasConsVPM, { title: 'Emergency Gas Consumption' });
    } else {
      // Gas Consumption result card (VPM) uses the last plan consumption but
      // keeps calcGasPlan() available for the Gas Plan tab/export path.
      window._lastGasConsumed = Object.assign({}, gasConsVPM);
      window._lastBottomPhaseConsumedL = {};
      _syncCylToGasPlan();
      calcGasPlan();
      renderGasConsumptionBars(gasElVPM, gasConsVPM, { title: 'Gas Consumption' });
    }
  }

  // Contingency Plans — re-runs Bühlmann internally, works fine with VPM settings
  const contCard = document.getElementById('contingencyCard');
  if (contCard) contCard.style.display = 'block';
  { const _cBtn=document.getElementById('contingencyJumpBtn'); if(_cBtn)_cBtn.style.display='inline-block'; }
  if (!_contingencyRunning) buildContingencyButtons();
  const contRes = document.getElementById('contingencyResult');
  if (contRes) contRes.style.display = 'none';

  // Tissues, GF Curve — Bühlmann-only: hide GF card on VPM
  const gfcVpm = document.getElementById('gfCurveInlineCard');
  if (gfcVpm) gfcVpm.style.display = _plannerShowsGfCurve() ? 'block' : 'none';

  // ── Min Deco Profile enforcement (VPM) — applied in runVPMSchedule before render ──
  const _vpmRawStops = result.stops?.map(s => ({ depth: s.depth, dur: s.time, gas: s.gas })) || [];

  window._lastPlan = {
    rt,
    tts: Math.round(vpmTtsMin * 10) / 10,
    decoTime: Math.round(deco),
    stops: _vpmRawStops,
    steps: plan,
    totalOTU: result.totalOTU != null ? result.totalOTU : undefined,
    totalCNS: result.totalCNS != null ? result.totalCNS : undefined,
    decoZoneStart: result.decoZoneStart || 0,
    firstStopDepth: vpmFirstStop,
    surfaceGF: result.finalTissues ? computeSurfaceGF(result.finalTissues) : null,
  };

  // Store for TXT/copy export (stat card IDs may not exist in DOM)
  window._lastVPMExport = {
    rt, deco: Math.round(deco),
    tts: vpmTtsMMSS,
    cns: result.totalCNS != null ? result.totalCNS.toFixed(1) + '%' : '-',
    otu: result.totalOTU != null ? String(result.totalOTU) : '-',
    prt: ((depthM * BAR_PER_METRE) * Math.sqrt(bt)).toFixed(1),
    decozone: decoZoneDispVPM,
    decoStop: decoStopDispVPM,
  };

  // Show results card
  const resultEl = document.getElementById('decoResult');
  if (resultEl) resultEl.style.display = 'block';

  // Update stat cards
  const setStatVal = (id, v) => { const el=document.getElementById(id); if(el) el.textContent=v; };
  const dU2 = units === 'metric';
  setStatVal('decoDepthDisplay',  (dU2 ? depthM : Math.round(depthM*3.28084)) + ' ' + du);
  setStatVal('decoBTDisplay',     bt + ' min');
  setStatVal('decoRunTimeDisplay', rt + '\'');
  setStatVal('decoDecoTimeDisplay', Math.round(deco) + ' min');
  setStatVal('decoCNSDisplay',    (result.totalCNS != null ? result.totalCNS.toFixed(1) : '—') + '%');
  setStatVal('decoOTUDisplay',    (result.totalOTU != null ? result.totalOTU : '—') + '');
  setStatVal('decoAlgoDisplay',   modelName + ' C' + cons + gfHi);

  // ── DECO SUMMARY — text-export style header block ──
  const summEl = document.getElementById('decoSummary');
  if (summEl) {
    const bottomFN2vpm = _vpmBotFracs.fN2;
    const endMvpm = calcEND(depthM, bottomFN2vpm, _vpmBotFracs.fHe || 0);
    const hasDeco = (result.stops || []).some(s => s.time > 0);
    updateDecoSummaryHtml(hasDeco, endMvpm, '');
  }
  const alertsContainer = document.getElementById('decoAlerts');
  if (alertsContainer) {
    const cnsAlert = result.totalCNS != null && result.totalCNS >= 80
      ? `<div class="alert cns-warn"><span>☢</span><div><strong>HIGH CNS%.</strong> CNS oxygen load ${result.totalCNS.toFixed(0)}% exceeds 80%. Reduce deco gas ppO₂, switch depth, or bottom time.</div></div>`
      : '';
    renderDecoAlerts(alertsContainer, cnsAlert);
  }
  if (result.finalTissues && result.finalTissues.length && !_contingencyRunning) {
    updateTissueViz(result.finalTissues, mGF.high);
  }
}

// AUDIT-UNIT:UI-ZHL-RESULTS
function renderZhlScheduleResults(ctx) {
  const {
    depthM, bt, rawD, descentRate,
    bottomFN2, bottomFHe, bottomFO2, bottomMixLabel,
    collapsedMDP, tissues, decoTime, hasDeco, firstStopDepth, trueDecoZoneStart,
    zhlCore, zhlOnLoop: _zhlOnLoop, ccrSettings: _ccrSettings, dU, loopMixLabel,
    ppo2Deco, ppo2Bottom,
  } = ctx;
  function getPPO2Limit(fO2) {
    const fO2pct = fO2 * 100;
    if (fO2pct >= 45) return ppo2Deco;
    if (fO2pct >= 28) return 1.5;
    return ppo2Bottom;
  }

  // ── END (Equivalent Narcotic Depth) at bottom depth ──
  const endM     = calcEND(depthM, bottomFN2, bottomFHe);
  const endDisp  = Math.round(endM);
  const endColor = endM > 40 ? 'var(--red)' : endM > 30 ? 'var(--orange)' : endM > 20 ? 'var(--yellow)' : 'var(--green)';
  const narcoStr = `N₂:${narcoticN2?'✓':'✗'} O₂:${narcoticO2?'✓':'✗'}`;

  // Update live END display in the settings card
  const endLive = document.getElementById('endDisplayLive');
  if (endLive) {
    endLive.textContent = `${endDisp} m  (${narcoStr})`;
    endLive.style.color = endColor;
  }

  const tbody = document.getElementById('decoTableBody');
  if (!tbody) return;
  const descentTimeMin = Math.round((depthM / descentRate) * 10) / 10;

  tbody.innerHTML = '';
  const _decoTotalsEl = document.getElementById('decoTotals'); if (_decoTotalsEl) _decoTotalsEl.innerHTML = '';
  let prevGas = loopMixLabel;
  let rowRT = 0;
  // ── EAD (Equivalent Air Depth) ──
  // EAD = (fN2 × (depth + 10) / 0.79) − 10  [metres]
  function calcEAD(depthM, fN2) {
    if (fN2 >= 0.79) return null;
    const ead = calcEND(depthM, fN2, 0);
    if (ead == null || ead <= 0) return null;
    return ead;
  }
  function fmtEAD(depthM, fN2) {
    const ead = calcEAD(depthM, fN2);
    if (ead === null) return '-';
    const dispEAD = dU ? Math.round(ead) + ' m' : Math.round(ead * 3.28084) + ' ft';
    return dispEAD;
  }

  // ── SAC gas consumption ──
  let sacBottom = sacDomToLpm('sacBottom', 20);
  let sacDeco   = sacDomToLpm('sacDeco', 15);
  if (_contingencyRunning && typeof getContingencySacMultiplier === 'function') {
    const contSacMult = getContingencySacMultiplier();
    sacBottom *= contSacMult;
    sacDeco *= contSacMult;
  }
  const sacBottomDisp = parseFloat(document.getElementById('sacBottom')?.value) || 20;
  const sacDecoDisp   = parseFloat(document.getElementById('sacDeco')?.value) || 15;
  const BAR_PER_M = BAR_PER_METRE;
  const gasConsumed = {};
  const bottomPhaseConsumed = {};
  function addGas(label, depthM, dur, sac, bottomPhaseOnly) {
    const litres = ccrGasLitres(label, depthM, dur, sac);
    accumGasLitres(gasConsumed, label, litres);
    if (bottomPhaseOnly) accumGasLitres(bottomPhaseConsumed, label, litres);
  }

  // ── OTU per segment (NOAA formula) ──
  function segOTU(ppo2, dur) {
    if (ppo2 <= 0.5) return 0;
    return dur * Math.pow((ppo2 - 0.5) / 0.5, OTU_EXPONENT);
  }
  // ── CNS raw fraction per segment ──
  function segCNSfrac(ppo2, dur) {
    if (ppo2 < 0.6) return 0;
    const limits = {6:720,7:570,8:450,9:360,10:300,11:240,12:210,13:180,14:150,15:120,16:45,17:45};
    const lo = Math.min(Math.floor(ppo2 * 10), 17);
    const hi = Math.min(lo + 1, 17);
    const vLo = limits[lo]||0, vHi = limits[hi]||0;
    const lim = vLo + (vHi-vLo)*(ppo2*10-lo);
    return lim > 0 ? dur / lim : dur / 45; // ppO2>1.6: clamp to 45-min limit (1.6 bar row) — avoids 100%-per-segment blowup
  }
  // ── mm'ss" formatter — uses global toMMSS (L4714)
  // Accumulators for footer — seed with prior dive carry if set (v2.20.0)
  const _pdCarry = window._priorDiveCarry;
  const _zhlRepSnap = (document.getElementById('zhlRepMode')?.checked && peekZhlRepState()) || null;
  let totalCNSfrac = _pdCarry ? (_pdCarry.cnsCarry / 100) : 0;
  let totalOTU     = _pdCarry ? _pdCarry.otuCarry : 0;
  if (_zhlRepSnap && !_pdCarry) {
    if (_zhlRepSnap.totalCNS != null) totalCNSfrac = _zhlRepSnap.totalCNS / 100;
    if (_zhlRepSnap.totalOTU != null) totalOTU = _zhlRepSnap.totalOTU;
  }

  // ── mm:ss formatter for table cells ──
  function fmtMM(minutes) {
    const totalSec = Math.round(minutes * 60);
    const m = Math.floor(totalSec / 60);
    const s = totalSec % 60;
    return `${m}:${String(s).padStart(2,'0')}`;
  }
  function rowDisplayPpo2(depthM, fN2, fHe, fO2, phase) {
    const fo2 = fO2 != null ? fO2 : Math.max(0, 1 - fN2 - (fHe || 0));
    if (_zhlOnLoop) {
      const v = ppO2Check(depthM, fN2, fHe, {
        ccr: { ..._ccrSettings, scrRuntimeMin: rowRT },
        onLoop: true,
        fO2: fo2,
      });
      return typeof v === 'string' ? v : Number(v).toFixed(2);
    }
    return ((depthM * BAR_PER_METRE + altSurfaceP) * fo2).toFixed(2);
  }

  // ── DESCENT ROW(S) — split by travel gas if active ──
  let _decoRowBuf = '';
  const travelInfoRow = getTravelGasInfo(); // null if no travel gas
  const travelSwitchMrow = travelInfoRow ? Math.min(travelInfoRow.switchDepthM, depthM) : 0;

  if (travelInfoRow && travelSwitchMrow > 0 && travelSwitchMrow < depthM) {
    // --- Phase 1: travel gas, surface → switch depth ---
    const travelDescentTimeMin = travelSwitchMrow / descentRate;
    const travelMidM = travelSwitchMrow / 2;
    const travelPPO2 = rowDisplayPpo2(travelMidM, travelInfoRow.fN2, travelInfoRow.fHe, travelInfoRow.fO2, 'descent');
    rowRT += travelDescentTimeMin;
    totalCNSfrac += segCNSfrac(parseFloat(travelPPO2), travelDescentTimeMin);
    totalOTU     += segOTU(parseFloat(travelPPO2), travelDescentTimeMin);
    addGas(travelInfoRow.label, travelMidM, travelDescentTimeMin, sacBottom, false);
    const travelSwitchDisp = dU ? travelSwitchMrow+'m' : mToFt(travelSwitchMrow)+'ft';
    _decoRowBuf += `<tr class="asc-row" data-phase="descent">
      <td><span style="font-size:18px;color:#ff8080;">↓</span></td>
      <td data-label="Depth" style="color:#ff8080;">0→${travelSwitchDisp}</td>
      <td data-label="Stop" style="color:#ff8080;"></td>
      <td data-label="Run" style="color:#ff8080;">${fmtMM(rowRT)}</td>
      <td data-label="Mix"><span style="color:#ff9900;font-weight:700;">${travelInfoRow.label}</span></td>
      <td data-label="PPO2" style="color:var(--muted);">${travelPPO2}</td>
      <td data-label="CNS" style="${scheduleCnsStyle(totalCNSfrac * 100)}">${scheduleCnsDisplay(totalCNSfrac * 100)}</td>
      <td data-label="EAD" style="color:var(--muted);"></td>
    </tr>`;

    // --- Phase 2: bottom gas, switch depth → bottom ---
    const bottomDescentTimeMin = (depthM - travelSwitchMrow) / descentRate;
    const bottomMidM = (travelSwitchMrow + depthM) / 2;
    const descentPPO2 = rowDisplayPpo2(bottomMidM, bottomFN2, bottomFHe, bottomFO2, 'descent');
    rowRT += bottomDescentTimeMin;
    totalCNSfrac += segCNSfrac(parseFloat(descentPPO2), bottomDescentTimeMin);
    totalOTU     += segOTU(parseFloat(descentPPO2), bottomDescentTimeMin);
    addGas(loopMixLabel, bottomMidM, bottomDescentTimeMin, sacBottom, true);
    _decoRowBuf += `<tr class="asc-row" data-phase="descent">
      <td><span style="font-size:18px;color:#ff8080;">↓</span></td>
      <td data-label="Depth" style="color:#ff8080;">${travelSwitchDisp}→${dU?rawD+'m':mToFt(rawD)+'ft'}</td>
      <td data-label="Stop" style="color:#ff8080;"></td>
      <td data-label="Run" style="color:#ff8080;">${fmtMM(rowRT)}</td>
      <td data-label="Mix"><span style="color:var(--accent);">${loopMixLabel}</span></td>
      <td data-label="PPO2" style="color:var(--muted);">${descentPPO2}</td>
      <td data-label="CNS" style="${scheduleCnsStyle(totalCNSfrac * 100)}">${scheduleCnsDisplay(totalCNSfrac * 100)}</td>
      <td data-label="EAD" style="color:var(--muted);"></td>
    </tr>`;
  } else {
    // No travel gas — single descent row as before
    rowRT += descentTimeMin;
    const descentMidM = depthM / 2;
    const descentPPO2 = rowDisplayPpo2(descentMidM, bottomFN2, bottomFHe, bottomFO2, 'descent');
    totalCNSfrac += segCNSfrac(parseFloat(descentPPO2), descentTimeMin);
    totalOTU     += segOTU(parseFloat(descentPPO2), descentTimeMin);
    addGas(loopMixLabel, descentMidM, descentTimeMin, sacBottom, true);
    _decoRowBuf += `<tr class="asc-row" data-phase="descent">
      <td><span style="font-size:18px;color:#ff8080;">↓</span></td>
      <td data-label="Depth" style="color:#ff8080;">0→${dU?rawD+'m':mToFt(rawD)+'ft'}</td>
      <td data-label="Stop" style="color:#ff8080;"></td>
      <td data-label="Run" style="color:#ff8080;">${fmtMM(rowRT)}</td>
      <td data-label="Mix"><span style="color:var(--accent);">${loopMixLabel}</span></td>
      <td data-label="PPO2" style="color:var(--muted);">${descentPPO2}</td>
      <td data-label="CNS" style="${scheduleCnsStyle(totalCNSfrac * 100)}">${scheduleCnsDisplay(totalCNSfrac * 100)}</td>
      <td data-label="EAD" style="color:var(--muted);"></td>
    </tr>`;
  }

  // ── BOTTOM ROW ──
  const btAtDepthMin = Math.max(0, bt - descentTimeMin);
  rowRT += btAtDepthMin;
  const btPPO2 = rowDisplayPpo2(rawD, bottomFN2, bottomFHe, bottomFO2, 'bottom');
  totalCNSfrac += segCNSfrac(parseFloat(btPPO2), btAtDepthMin);
  totalOTU     += segOTU(parseFloat(btPPO2), btAtDepthMin);
  addGas(loopMixLabel, rawD, btAtDepthMin, sacBottom, true);
  if (_zhlOnLoop) {
    const reserveMin = (_ccrSettings.stressTimeMin || 0) + (_ccrSettings.problemSolveMin || 0);
    if (reserveMin > 0) {
      const stopDepths = collapsedMDP.filter(s => s.type === 'deco').map(s => s.depth);
      addBailoutStressReserve(
        addGas, reserveMin, rawD, stopDepths, bottomFO2, bottomFHe,
        _ccrSettings.sacStress || sacBottom
      );
    }
  }
  _decoRowBuf += `<tr class="asc-row" data-phase="bottom">
    <td>🔵</td>
    <td data-label="Depth" style="color:var(--accent);">${dU?rawD+'m':mToFt(rawD)+'ft'}</td>
    <td data-label="Stop" style="color:var(--accent);">${fmtMM(btAtDepthMin)}</td>
    <td data-label="Run" style="color:var(--accent);">${fmtMM(rowRT)}</td>
    <td data-label="Mix"><span style="color:var(--accent);">${loopMixLabel}</span></td>
    <td data-label="PPO2" style="color:var(--muted);">${btPPO2}</td>
    <td data-label="CNS" style="${scheduleCnsStyle(totalCNSfrac * 100)}">${scheduleCnsDisplay(totalCNSfrac * 100)}</td>
    <td data-label="EAD" style="color:var(--muted);"></td>
  </tr>`;

  // ── TTS baseline: snapshot rowRT here — this is exactly descent+bottom time.
  // TTS (time-to-surface) is everything from this point to the final rowRT,
  // i.e. ascent+deco only. Matches MultiDeco/DiveKit's published TTS definition.
  const rtAtBottomEnd = rowRT;

  collapsedMDP.forEach(s => {
    if (s.decoTransit) return; // mdCompatMode: transit folded into stop duration
    const _sFN2    = s.fN2 ?? bottomFN2;
    const _sFHe    = s.fHe ?? 0;
    const pO2Raw   = s.pO2 != null ? String(s.pO2) : ppO2Check(s.depth, _sFN2, _sFHe);
    const pO2Val   = parseFloat(pO2Raw);
    const _sFO2    = Math.max(0, 1 - _sFN2 - _sFHe);  // trimix-safe fO2
    const gasLimit = getPPO2Limit(_sFO2);
    const pO2Color = pO2Raw === 'ERR' || !Number.isFinite(pO2Val)
      ? 'color:var(--red);font-weight:700;'
      : pO2Val >= gasLimit ? 'color:var(--red);font-weight:700;' : pO2Val > gasLimit * 0.97 ? 'color:var(--orange);' : 'color:var(--muted);';
    const stepDur  = typeof s.dur === 'number' ? s.dur : parseFloat(s.dur) || 0;
    rowRT += stepDur;
    const rtDisp = fmtMM(rowRT);

    // ── GAS SWITCH ROW ──
    if (!_zhlOnLoop && s.gas && s.gas !== prevGas && s.gas !== bottomMixLabel && s.gas !== loopMixLabel) {
      const isO2        = s.fN2 === 0;
      const switchDepth = s.type === 'deco' ? s.depth : (s.from ?? s.depth);
      const switchDepthDisp = dU ? switchDepth+'m' : mToFt(switchDepth)+'ft';
      const switchPpO2  = ppO2Check(switchDepth, s.fN2, s.fHe || 0);
      const sppVal      = typeof switchPpO2 === 'number' ? switchPpO2 : parseFloat(switchPpO2);
      const _swFHe  = s.fHe ?? 0;
      const _swFO2  = Math.max(0, 1 - (s.fN2 ?? bottomFN2) - _swFHe);  // trimix-safe
      const switchLimit = getPPO2Limit(_swFO2);
      const sppColor    = switchPpO2 === 'ERR' || !Number.isFinite(sppVal)
        ? 'color:var(--red);font-weight:700;'
        : sppVal >= switchLimit ? 'color:var(--red);font-weight:700;' : sppVal > switchLimit * 0.97 ? 'color:var(--orange);font-weight:700;' : '';
      const switchMixDisp = s.gas.replace(/\s+/g, '').toUpperCase();
      _decoRowBuf += `<tr data-phase="switch">
        <td style="text-align:center;">⇄</td>
        <td data-label="Depth">${switchDepthDisp}</td>
        <td data-label="Stop"></td>
        <td data-label="Run"></td>
        <td data-label="Mix">${switchMixDisp}</td>
        <td data-label="PPO2" style="${sppColor}">${fmtPpO2(switchPpO2)}</td>
        <td data-label="CNS"></td>
        <td data-label="EAD"></td>
      </tr>`;
    }
    prevGas = s.gas;

    const gasColor = s.type === 'deco'
      ? 'var(--red)'
      : (_sFN2 === 0) ? 'var(--accent)' : 'var(--green)';

    // ── DECO STOP ROW ──
    if (s.type === 'deco') {
      totalCNSfrac += segCNSfrac(pO2Val, stepDur);
      totalOTU     += segOTU(pO2Val, stepDur);
      addGas(s.gas, s.depth, stepDur, sacDeco);
      const eadDisp = fmtEAD(s.depth, _sFN2);
      const cumCnsPct = totalCNSfrac * 100;
      const cnsTier = cumCnsPct >= 100 ? '100' : cumCnsPct >= 80 ? '80' : '';
      const rowBg = cnsTier === '100'
        ? 'background:#ffff00;color:#111;'
        : cnsTier === '80'
          ? 'background:rgba(255,255,0,0.25);'
          : '';
      _decoRowBuf += `<tr class="deco-row" data-phase="deco" style="${rowBg}" ${cnsTier ? `data-cnshi="1" data-cns-tier="${cnsTier}"` : ''}>
        <td><span style="color:var(--red);">●</span></td>
        <td data-label="Depth">${dU?s.depth+'m':mToFt(s.depth)+'ft'}</td>
        <td data-label="Stop" style="color:${rowBg?'#b30000':'var(--red)'};">${fmtMM(stepDur)}</td>
        <td data-label="Run">${rtDisp}</td>
        <td data-label="Mix" style="color:${rowBg?'#b30000':'var(--red)'}">${(s.gas || '—').toUpperCase()}</td>
        <td data-label="PPO2" style="${rowBg?'color:#b30000;font-weight:700;':pO2Color}">${pO2Val.toFixed(2)}</td>
        <td data-label="CNS" style="${rowBg?'color:#b30000;font-weight:700;':scheduleCnsStyle(totalCNSfrac * 100)}">${scheduleCnsDisplay(totalCNSfrac * 100)}</td>
        <td data-label="EAD" style="color:${rowBg?'#555':'var(--muted)'};font-size:11px;">${eadDisp}</td>
      </tr>`;
    // ── SAFETY STOP ROW ──
    } else if (s.type === 'safety') {
      totalCNSfrac += segCNSfrac(pO2Val, stepDur);
      totalOTU     += segOTU(pO2Val, stepDur);
      addGas(s.gas, s.depth, stepDur, sacDeco);
      _decoRowBuf += `<tr class="safe-row" data-phase="safety">
        <td style="font-size:16px;">🟢</td>
        <td data-label="Depth">${dU?s.depth+'m':mToFt(s.depth)+'ft'}</td>
        <td data-label="Stop" style="color:var(--green);">${fmtMM(stepDur)}</td>
        <td data-label="Run">${rtDisp}</td>
        <td data-label="Mix" style="color:${gasColor};">${(s.gas || '—').toUpperCase()}</td>
        <td data-label="PPO2" style="color:var(--muted);">${Number.isFinite(pO2Val) ? pO2Val.toFixed(2) : '—'}</td>
        <td data-label="CNS" style="${scheduleCnsStyle(totalCNSfrac * 100)}">${scheduleCnsDisplay(totalCNSfrac * 100)}</td>
        <td data-label="EAD" style="color:var(--muted);font-size:11px;">${fmtEAD(s.depth, s.fN2)}</td>
      </tr>`;
    // ── ASCENT ROW ──
    } else {
      if (s.decoTransit) return; // mdCompatMode: transit folded into stop display
      totalCNSfrac += segCNSfrac(pO2Val, stepDur);
      totalOTU     += segOTU(pO2Val, stepDur);
      addGas(s.gas, (s.from + s.to) / 2, stepDur, sacDeco);
      _decoRowBuf += `<tr class="asc-row" data-phase="ascent">
        <td><span style="font-size:18px;" class="asc-color">↑</span></td>
        <td data-label="Depth" class="asc-color">${dU?s.to+'m':mToFt(s.to)+'ft'}</td>
        <td data-label="Stop" class="asc-color" style="font-size:11px;color:var(--muted);">${fmtMM(s.dur)}</td>
        <td data-label="Run" class="asc-color">${rtDisp}</td>
        <td data-label="Mix" style="color:${gasColor};">${(s.gas || '—').toUpperCase()}</td>
        <td data-label="PPO2" style="${pO2Color}">${Number.isFinite(pO2Val) ? pO2Val.toFixed(2) : '—'}</td>
        <td data-label="CNS" style="${scheduleCnsStyle(totalCNSfrac * 100)}">${scheduleCnsDisplay(totalCNSfrac * 100)}</td>
        <td data-label="EAD" style="color:var(--muted);"></td>
      </tr>`;
    }
  });
  tbody.innerHTML += _decoRowBuf;

  // ── Update Tissues tab with final deco tissues ──
  if (!_contingencyRunning) {
    lastTissues = tissues;
    updateTissueViz(tissues, mGF.high);
  }

  // ── TOTALS FOOTER ROW ──
  const totalCNSpct  = (totalCNSfrac * 100).toFixed(1);
  const totalOTUval  = Math.round(totalOTU);
  // ── Update headless hook with CNS/OTU totals (now known) ──
  if (window._lastPlan) {
    window._lastPlan.totalCNS = parseFloat(totalCNSpct);
    window._lastPlan.totalOTU = totalOTUval;
  }
  const totalRunMMSS = toMMSS(window._lastPlan ? window._lastPlan.rt : rowRT);
  const decoTimeMMSS = toMMSS(decoTime);
  // ── TTS (time-to-surface): ascent+deco only, excludes descent+bottom time.
  // Sourced from window._lastPlan.tts (computed once, headless-safe, from
  // `rt - bt` at the engine level) rather than re-derived from DOM row totals —
  // single source of truth, matches MultiDeco/DiveKit's published TTS definition.
  const ttsVal   = window._lastPlan ? window._lastPlan.tts : Math.max(0, rowRT - rtAtBottomEnd);
  const ttsMMSS  = toMMSS(ttsVal);
  const cnsFootColor = totalCNSfrac >= 1 ? 'var(--red)' : totalCNSfrac >= 0.8 ? 'var(--orange)' : totalCNSfrac >= 0.5 ? 'var(--yellow)' : 'var(--green)';
  const otuFootColor = totalOTUval >= 300 ? 'var(--red)' : totalOTUval >= 200 ? 'var(--orange)' : totalOTUval >= 100 ? 'var(--yellow)' : 'var(--green)';
  // PrT = P_rel (bar) × √T(min) — Fraedrich/Balestra severity index
  // P_rel = gauge pressure at deepest depth, T = bottom time
  const prtVal  = (depthM * BAR_PER_METRE) * Math.sqrt(bt);
  const prtDisp = prtVal.toFixed(1);
  // GF High guidance from evidence (Fraedrich 2019):
  // PrT <15 → GF Hi ≤80 ok; 15–25 → ≤75; 25–40 → ≤70; >40 → extreme caution
  const prtGfHint = prtVal < 15 ? 'GF Hi ≤80' : prtVal < 25 ? 'GF Hi ≤75' : prtVal < 40 ? 'GF Hi ≤70' : 'GF Hi ≤60';
  const prtColor  = prtVal < 15 ? 'var(--green)' : prtVal < 25 ? 'var(--yellow)' : prtVal < 40 ? 'var(--orange)' : 'var(--red)';
  const decoZoneDisp = formatDecoZoneStart(trueDecoZoneStart);
  const decoStopDisp = formatDecoStopDepth(firstStopDepth);
  updateDecoSummaryHtml(hasDeco, endM, '3 min safety stop at 3 m included.', zhlCore.hitSafetyGuard);
  tbody.innerHTML += buildPlanInfoRowHtml({
    runTime: totalRunMMSS,
    tts: ttsMMSS,
    decoTime: decoTimeMMSS,
    cns: totalCNSpct + '%',
    otu: totalOTUval,
    prt: prtDisp,
    prtColor,
    prtTitle: prtGfHint + ' recommended (Fraedrich 2019)',
    cnsColor: cnsFootColor,
    otuColor: otuFootColor,
    hasDeco,
    decozone: decoZoneDisp,
    decoStop: decoStopDisp,
    surfaceGF: window._lastPlan ? window._lastPlan.surfaceGF : null,
  });
  _renderResultSummaryStrip({
    runTime: totalRunMMSS,
    decoTime: decoTimeMMSS,
    cns: totalCNSpct + '%',
    firstStop: decoStopDisp,
    surfaceGF: window._lastPlan && Number.isFinite(window._lastPlan.surfaceGF) ? `${window._lastPlan.surfaceGF.toFixed(0)}%` : '—',
    otu: totalOTUval,
    tts: ttsMMSS,
    decozone: decoZoneDisp,
  });
  _onPlanResultsReady();

  { const _decoRes = document.getElementById('decoResult'); if (_decoRes) _decoRes.style.display = 'block'; }
  { const _tBtn=document.getElementById('tissueChartToggleBtn'); const _cBtn=document.getElementById('contingencyJumpBtn'); if(_tBtn)_tBtn.style.display='inline-block'; if(_cBtn)_cBtn.style.display='inline-block'; }

  decorateDecoTableForV3();
  scheduleDecoScheduleStackSync();

  // ── CNS% high warning (post-render, totalCNSfrac now known) ──
  const decoAlertsEl = document.getElementById('decoAlerts');
  if (decoAlertsEl && !_contingencyRunning) {
    const cnsPctNum = totalCNSfrac * 100;
    const cnsAlert = cnsPctNum >= 80
      ? `<div class="alert cns-warn"><span>☢</span><div><strong>HIGH CNS%.</strong> CNS oxygen load ${cnsPctNum.toFixed(0)}% exceeds 80%. Reduce deco gas ppO₂, switch depth, or bottom time.</div></div>`
      : '';
    renderDecoAlerts(decoAlertsEl, cnsAlert);
  }

  // Expose consumption for the Gas Plan tab (deco/travel one-way requirements).
  // Only store from the main plan run, not emergency contingency runs.
  if (!_contingencyRunning) {
    window._lastGasConsumed = Object.assign({}, gasConsumed);
    window._lastBottomPhaseConsumedL = Object.assign({}, bottomPhaseConsumed);
  } else {
    window._contingencyScratchGasConsumed = Object.assign({}, gasConsumed);
  }
  _syncCylToGasPlan();

  // ── GAS CONSUMPTION SUMMARY ──
  const gasEl = _contingencyRunning
    ? document.getElementById('emergencyGasConsumption')
    : document.getElementById('gasConsumptionSummary');
  if (!_contingencyRunning) {
    // Clear emergency gas section when running main plan
    const emEl = document.getElementById('emergencyGasConsumption');
    if (emEl) emEl.style.display = 'none';
  }
  if (gasEl && Object.keys(gasConsumed).length) {

    // Build cylinder capacity map: gas label → available litres
    // Match cylinders to gas labels by position (bottom, deco1, deco2)
    const gasLabels  = Object.keys(gasConsumed); // e.g. ['AIR','EAN 50','100% O2']
    const cylIds = [
      ['cylBot_size','cylBot_pres'],
      ['cylDg1_size','cylDg1_pres'],
      ['cylDg2_size','cylDg2_pres'],
      ['cylTravelGas_size','cylTravelGas_pres'],
    ];
    const cylCapacity = {}; // gas label → available litres
    gasLabels.forEach((label, idx) => {
      const [sId, pId] = cylIds[idx] || [];
      if (!sId) return;
      const szRaw = parseFloat(document.getElementById(sId)?.value) || 0;
      const sz  = units === 'imperial' ? szRaw * 28.3168 : szRaw;
      const prRaw = parseFloat(document.getElementById(pId)?.value) || 0;
      // Pressure input is in bar (metric) or psi (imperial) — always calc in bar
      const pr = units === 'imperial' ? prRaw / 14.5038 : prRaw;
      if (sz > 0 && pr > 0) cylCapacity[label] = sz * pr;
    });

    // ── Rule-of-thirds table ──
    const volUnitV  = lspVolUnit();
    const presUnitV = units === 'imperial' ? 'psi' : 'bar';
    const sacUnitBHL = lspSacUnit();
    const fracBHL   = (_gasRule === 'half') ? 0.5 : (1/3);
    const ruleLblBHL = (_gasRule === 'half') ? 'HALF' : 'THIRDS';
    // Gas Consumption result card renders per-cylinder bars. calcGasPlan()
    // remains available for the Gas Plan tab/export path.
    const cardTitle = _contingencyRunning ? 'Emergency Gas Consumption' : 'Gas Consumption';
    if (!_contingencyRunning) {
      window._lastGasConsumed = Object.assign({}, gasConsumed);
      window._lastBottomPhaseConsumedL = Object.assign({}, bottomPhaseConsumed);
      _syncCylToGasPlan();
      calcGasPlan();
      renderGasConsumptionBars(gasEl, gasConsumed, { title: cardTitle });
    } else {
      window._contingencyScratchGasConsumed = Object.assign({}, gasConsumed);
      renderGasConsumptionBars(gasEl, gasConsumed, { title: cardTitle });
    }

  } else if (!_contingencyRunning) {
    _setGasWarningBanner('');
  } // end if (gasEl && Object.keys(gasConsumed).length)

}
