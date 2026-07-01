/**
 * Gas plan tab (Rule of Thirds) — RUNTIME UI CORE.
 * Loaded by index.html before main inline script.
 * Globals read: units, document, runDecoSchedule, ensurePDFFontsForPDF, getExportCircuitTag,
 *   showCopyToast, copyFallback, window.jspdf, getBottomGasFractions, getDecoCardFractions,
 *   getAllDecoGasIds, isTravelGasConfigured, getDecoGasLabel, getGasLabel, validateDomDecoGases,
 *   getCCRSettingsFromDOM, loopMixLabelFor
 * Globals written: _gasRule, window._lastGasPlan
 */

// ═══════════════════════════════════════════════
// GAS PLAN TAB — Rule of Thirds / turning pressure
// ═══════════════════════════════════════════════
const GP_PSI_PER_BAR = 14.5038;
const GP_CUFT_PER_L  = 0.0353147;
const GP_ONEWAY_MARGIN = 1.10;
let _gasRule = 'thirds';

/** Turn pressure uses bottom-cylinder rule fraction only; pool portionL is for plan cross-check. */
function computePooledBottomTurnBars(botSize, botFill, botRes, travelPooledL, fraction) {
  if (!(botSize > 0 && botFill > botRes)) return null;
  const botCylUsableL = (botFill - botRes) * botSize;
  const usableL = botCylUsableL + (travelPooledL || 0);
  if (!(usableL > 0)) return null;
  const portionL = usableL * fraction;
  const botCylPortionL = botCylUsableL * fraction;
  const turnBar = botFill - botCylPortionL / botSize;
  return { usableL, portionL, botCylPortionL, turnBar, maxTurnBar: turnBar };
}

function setGasRule(rule) {
  _gasRule = rule === 'half' ? 'half' : 'thirds';
  // Sync Gas Plan tab toggles
  const t = document.getElementById('gpRuleThirds');
  const h = document.getElementById('gpRuleHalf');
  if (t) t.classList.toggle('active', _gasRule === 'thirds');
  if (h) h.classList.toggle('active', _gasRule === 'half');
  calcGasPlan();
  const gasEl = document.getElementById('gasConsumptionSummary');
  if (!window._zhlHeadless && gasEl && gasEl.style.display !== 'none' && !window._scheduleWorkerBusy) {
    runDecoSchedule();
  }
}

// Read a Gas Plan pressure input, returning bar regardless of unit system.
function gpPresBar(id) {
  const v = parseFloat(document.getElementById(id)?.value);
  if (Number.isNaN(v)) return 0;
  return units === 'imperial' ? v / GP_PSI_PER_BAR : v;
}
// Read a Gas Plan size input, returning litres regardless of unit system.
function gpSizeL(id) {
  const v = parseFloat(document.getElementById(id)?.value);
  if (Number.isNaN(v)) return 0;
  return units === 'imperial' ? v / GP_CUFT_PER_L : v;
}
// Display helpers
function gpVolDisp(litres) {
  if (!Number.isFinite(litres)) return '—';
  return units === 'imperial' ? (litres * GP_CUFT_PER_L).toFixed(1) : Math.round(litres).toString();
}
function gpPresDisp(bar) {
  return units === 'imperial' ? Math.round(bar * GP_PSI_PER_BAR).toString() : Math.round(bar).toString();
}

// Match the last-run deco plan consumption (window._lastGasConsumed, keyed by gas
// label) to a target gas by its label. Returns required litres, or null.
function gpRequiredFor(label) {
  const gc = window._lastGasConsumed;
  if (!gc || !label) return null;
  if (gc[label] != null) return gc[label];
  // Case-insensitive fallback
  const key = Object.keys(gc).find(k => k.toLowerCase() === label.toLowerCase());
  if (key) return gc[key];
  // CCR/pSCR: consumption keyed as "CCR Air" / "pSCR Air" while Gas Plan uses diluent label
  const loopKey = loopMixLabelFor(label, getCCRSettingsFromDOM());
  if (loopKey !== label) {
    if (gc[loopKey] != null) return gc[loopKey];
    const loopMatch = Object.keys(gc).find(k => k.toLowerCase() === loopKey.toLowerCase());
    if (loopMatch) return gc[loopMatch];
  }
  return null;
}

function getContingencySacMultiplier() {
  const v = parseFloat(document.getElementById('contingencySacMultiplier')?.value);
  return Number.isFinite(v) && v >= 1 && v <= 3 ? v : 1.5;
}

function scaleGasConsumedMap(gasMap, multiplier) {
  if (!gasMap) return {};
  if (!multiplier || multiplier === 1) return Object.assign({}, gasMap);
  const out = {};
  Object.entries(gasMap).forEach(([label, litres]) => {
    if (Number.isFinite(litres)) out[label] = litres * multiplier;
  });
  return out;
}

function gpAvailLForGasLabel(label, options) {
  if (!label) return 0;
  options = options || {};
  let availL = 0;
  const bot = getBottomGasFractions();
  const botLabel = bot ? getGasLabel(bot.fO2, bot.fHe) : null;
  const ccr = getCCRSettingsFromDOM();
  const onRebreather = isRebreatherCircuit(ccr.circuit);
  const diluentAllowed = document.getElementById('diluentUseAsBailout')?.value === 'on';
  const includeBottom = !options.bailoutFocus || !onRebreather || diluentAllowed;
  if (includeBottom && botLabel && label.toLowerCase() === botLabel.toLowerCase()) {
    const size = gpSizeL('gpBot_size');
    const fill = gpPresBar('gpBot_fill');
    const res = gpPresBar('gpBot_reserve');
    if (size > 0 && fill > res) availL += (fill - res) * size;
  }
  getAllDecoGasIds().forEach(idx => {
    const fracs = getDecoCardFractions(idx);
    if (!fracs || fracs.fO2 <= 0) return;
    const gLabel = getGasLabel(fracs.fO2, fracs.fHe);
    if (gLabel.toLowerCase() !== label.toLowerCase()) return;
    const useGp = idx <= 2 && document.getElementById(`gpDg${idx}_size`);
    const size = gpSizeL(useGp ? `gpDg${idx}_size` : `cylDg${idx}_size`);
    const fill = gpPresBar(useGp ? `gpDg${idx}_fill` : `cylDg${idx}_pres`);
    const res = gpPresBar(useGp ? `gpDg${idx}_reserve` : `cylDg${idx}_reserve`);
    if (size > 0 && fill > res) availL += (fill - res) * size;
  });
  return availL;
}

/** Contingency profile gas requirements vs configured cylinders (bailout-focused). */
function calculateGasRequirementsFromConsumed(gasConsumed, options) {
  options = options || {};
  const consumed = scaleGasConsumedMap(gasConsumed, options.sacMultiplier || 1);
  const rows = [];
  const shortfalls = [];
  const bailoutShortfalls = [];
  if (!consumed || !Object.keys(consumed).length) {
    return { ok: true, shortfalls, bailoutShortfalls, warningBailoutContingency: false, rows };
  }
  const ccr = getCCRSettingsFromDOM();
  const onCcr = typeof isRebreatherCircuit === 'function' && isRebreatherCircuit(ccr.circuit);
  const bailoutMixes = typeof getConfiguredBailoutMixes === 'function' ? getConfiguredBailoutMixes() : [];
  const bailoutLabels = new Set(bailoutMixes.map(m => m.label.toLowerCase()));

  Object.entries(consumed).forEach(([label, reqL]) => {
    if (!Number.isFinite(reqL) || reqL <= 0) return;
    const availL = gpAvailLForGasLabel(label, options);
    const isBailout = bailoutLabels.has(label.toLowerCase()) || (onCcr && !!ccr.bailout);
    const shortL = availL > 0 && reqL > availL ? reqL - availL : (availL <= 0 && reqL > 0 ? reqL : 0);
    rows.push({ label, reqL, availL, shortL, isBailout });
    if (shortL > 0) {
      shortfalls.push({ label, reqL, availL, shortL });
      if (isBailout || options.bailoutFocus) bailoutShortfalls.push({ label, reqL, availL, shortL });
    }
  });

  const warningBailoutContingency = bailoutShortfalls.length > 0;
  return {
    ok: shortfalls.length === 0,
    shortfalls,
    bailoutShortfalls,
    warningBailoutContingency,
    rows,
  };
}

// Sync main cylinder inputs → Gas Plan cylinder fields before calcGasPlan()
// Main: cylBot_size, cylBot_pres, cylBot_reserve  →  gp: gpBot_size, gpBot_fill, gpBot_reserve
function _syncCylToGasPlan() {
  const map = [
    ['cylBot_size',          'gpBot_size'],
    ['cylBot_pres',          'gpBot_fill'],
    ['cylBot_reserve',       'gpBot_reserve'],
    ['cylTravelGas_size',    'gpTravel_size'],
    ['cylTravelGas_pres',    'gpTravel_fill'],
    ['cylTravelGas_reserve', 'gpTravel_reserve'],
  ];
  getAllDecoGasIds().forEach(idx => {
    if (idx <= 2) {
      map.push(
        [`cylDg${idx}_size`, `gpDg${idx}_size`],
        [`cylDg${idx}_pres`, `gpDg${idx}_fill`],
        [`cylDg${idx}_reserve`, `gpDg${idx}_reserve`],
      );
    }
  });
  map.forEach(([src, dst]) => {
    const srcEl = document.getElementById(src);
    const dstEl = document.getElementById(dst);
    if (srcEl && dstEl && srcEl.value) dstEl.value = srcEl.value;
  });
}

// Force red banner styles on gas warning rows — bypasses all CSS specificity battles
function _applyGasWarningStyles(container) {
  if (!container) return;
  const isLight = document.body.classList.contains('light-theme');
  const textCol = isLight ? '#000' : '#fff';
  container.querySelectorAll('.gas-bt-cell').forEach(td => {
    td.style.setProperty('background', '#FF4433', 'important');
    td.style.setProperty('color', textCol, 'important');
    td.style.setProperty('font-weight', '700', 'important');
    td.style.setProperty('font-size', '11px', 'important');
    td.style.setProperty('padding', '6px 10px', 'important');
    td.style.setProperty('border-bottom', '1px solid rgba(0,0,0,0.15)', 'important');
    td.querySelectorAll('*').forEach(el => el.style.setProperty('color', textCol, 'important'));
  });
  container.querySelectorAll('tr.gas-tight-row td').forEach(td => {
    td.style.setProperty('background', '#FF4433', 'important');
    td.style.setProperty('color', textCol, 'important');
    td.style.setProperty('font-weight', '600', 'important');
    td.style.setProperty('border-bottom', '1px solid rgba(0,0,0,0.15)', 'important');
    td.querySelectorAll('*').forEach(el => el.style.setProperty('color', textCol, 'important'));
  });
}

function calcGasPlan() {
  if (!window._zhlHeadless) {
    const gasVal = validateDomDecoGases();
    if (!gasVal.ok) return;
  }
  const volU  = units === 'imperial' ? 'cu ft' : 'L';
  const presU = units === 'imperial' ? 'psi'   : 'bar';

  // ── Determine which optional gases are configured on the Deco tab ──
  const travelConfigured = isTravelGasConfigured()
                           && !!document.getElementById('cylTravelGas_size');

  const showRow = (id, show) => { const el = document.getElementById(id); if (el) el.style.display = show ? '' : 'none'; };
  showRow('gpTravelRow', travelConfigured);
  showRow('gpDg1Row', false);
  showRow('gpDg2Row', false);

  const rows = [];

  // ── Bottom gas: rule of thirds / half tank + turn pressure ──
  const botSize = gpSizeL('gpBot_size');
  const botFill = gpPresBar('gpBot_fill');
  const botRes  = gpPresBar('gpBot_reserve');
  const botFracs = getBottomGasFractions();
  if (!botFracs) return;
  const botLabel = getGasLabel(botFracs.fO2, botFracs.fHe) || 'Bottom';

  // Check if travel gas has same mix — if so, pool its usable litres into bottom total
  let travelPooledL = 0;
  if (travelConfigured) {
    const tLabel = getDecoGasLabel('travelGasMix', 'travelGasCustomO2')
                 || getGasLabel(0.21, 0);
    if (tLabel === botLabel) {
      const tSize = gpSizeL('gpTravel_size');
      const tFill = gpPresBar('gpTravel_fill');
      const tRes  = gpPresBar('gpTravel_reserve');
      if (tSize > 0 && tFill > tRes) travelPooledL = (tFill - tRes) * tSize;
    }
  }

  if (botSize > 0 && botFill > botRes) {
    const fraction = _gasRule === 'half' ? 0.5 : (1 / 3);
    const pooled = computePooledBottomTurnBars(botSize, botFill, botRes, travelPooledL, fraction);
    const usableL  = pooled.usableL;
    const portionL = pooled.portionL;
    const turnBar  = pooled.turnBar;

    // Cross-check against last deco plan consumption
    const reqL      = gpRequiredFor(botLabel);
    const lastPlan  = window._lastPlan;
    let   shortL    = null;   // > 0 means insufficient
    let   maxBTmin  = null;   // suggested max BT
    let   maxTurnBar = null;  // turn pressure at max BT
    let   maxBTEstimate = false;
    if (Number.isFinite(reqL) && reqL > usableL) {
      shortL = reqL - usableL;
      const plannedBT = parseFloat(document.getElementById('decoBT')?.value) || 0;
      if (plannedBT > 0 && reqL > 0) {
        const bottomPhaseL = window._lastBottomPhaseConsumedL?.[botLabel];
        const rateL = (Number.isFinite(bottomPhaseL) && bottomPhaseL > 0)
          ? bottomPhaseL / plannedBT
          : reqL / plannedBT;
        maxBTEstimate = !(Number.isFinite(bottomPhaseL) && bottomPhaseL > 0);
        maxBTmin = Math.max(1, Math.floor(usableL / rateL));
        maxTurnBar = pooled.turnBar;
      }
    }

    rows.push({
      kind:       'bottom',
      label:      travelPooledL > 0 ? `${botLabel} (+Travel)` : botLabel,
      totalL:     usableL,
      portionL,
      turnBar,
      reserveBar: botRes,
      reqL,
      shortL,
      maxBTmin,
      maxTurnBar,
      maxBTEstimate,
    });
  }

  // ── One-way gases (travel, deco) checked against last deco plan ──
  const oneWay = [];
  if (travelConfigured) {
    const tLabel = getDecoGasLabel('travelGasMix', 'travelGasCustomO2')
                 || (getGasLabel(0.21, 0)); // travel default air
    oneWay.push({ name: 'Travel', label: tLabel, sizeId: 'gpTravel_size', fillId: 'gpTravel_fill', resId: 'gpTravel_reserve' });
  }
  getAllDecoGasIds().forEach(idx => {
    const fracs = getDecoCardFractions(idx);
    if (!fracs || fracs.fO2 <= 0) return;
    if (idx === 1) showRow('gpDg1Row', true);
    if (idx === 2) showRow('gpDg2Row', true);
    const label = getGasLabel(fracs.fO2, fracs.fHe);
    const useGp = idx <= 2 && document.getElementById(`gpDg${idx}_size`);
    oneWay.push({
      name: `Deco ${idx}`,
      label,
      sizeId: useGp ? `gpDg${idx}_size` : `cylDg${idx}_size`,
      fillId: useGp ? `gpDg${idx}_fill` : `cylDg${idx}_pres`,
      resId: useGp ? `gpDg${idx}_reserve` : `cylDg${idx}_reserve`,
    });
  });

  // Remove pooled label from one-way list (any gas name sharing the bottom mix)
  const oneWayFiltered = travelPooledL > 0
    ? oneWay.filter(g => g.label !== botLabel)
    : oneWay;

  let needPlan = false;
  oneWayFiltered.forEach(g => {
    const size = gpSizeL(g.sizeId);
    const fill = gpPresBar(g.fillId);
    const res  = gpPresBar(g.resId);
    const availL = (size > 0 && fill > res) ? (fill - res) * size : 0;
    const reqL = gpRequiredFor(g.label);
    if (reqL == null) needPlan = true;
    rows.push({
      kind: 'oneway',
      label: `${g.label} (${g.name})`,
      totalL: availL,
      reqL,
      reserveBar: res,
    });
  });

  // ── Render results table ──
  const body = document.getElementById('gpResultBody');
  if (body) {
    let html = '';
    rows.forEach(r => {
      if (r.kind === 'bottom') {
        const ruleTxt = _gasRule === 'half' ? '1/2' : '1/3';
        if (r.shortL != null && r.shortL > 0) {
          // Insufficient for deco plan — warning + max BT suggestion
          const btSuggest = r.maxBTmin != null
            ? `Max BT with this cylinder: <strong>${r.maxBTmin} min</strong>, turn at <strong>${gpPresDisp(r.maxTurnBar)} ${presU}</strong>${r.maxBTEstimate ? ' <span style="color:var(--muted);">(conservative estimate)</span>' : ''}`
            : '';
          html += `<tr>
            <td style="white-space:nowrap;">${r.label}</td>
            <td style="color:var(--red) !important;font-weight:700;">${gpVolDisp(r.totalL)} ${volU}</td>
            <td style="color:var(--muted);font-size:10px;">${gpVolDisp(r.portionL||0)} ${volU} <span style="color:var(--muted);">(${ruleTxt})</span></td>
            <td style="color:var(--muted);">—</td>
            <td>${gpPresDisp(r.reserveBar)} ${presU}</td>
            <td><span style="color:var(--red) !important;font-weight:700;">✗ short</span><br><span style="color:var(--muted);font-size:10px;">need ${gpVolDisp(r.reqL)} ${volU}</span></td>
            <td style="color:var(--red) !important;font-weight:700;">−${gpVolDisp(r.shortL)} ${volU}</td>
          </tr>`;
          if (btSuggest) html += `<tr class="gas-bt-row"><td colspan="7" class="gas-bt-cell">⚠ ${btSuggest} — or use a larger cylinder.</td></tr>`;
        } else {
          // Sufficient — normal turn pressure row with plan check
          const botVolColor = Number.isFinite(r.reqL)
            ? (r.totalL >= r.reqL * GP_ONEWAY_MARGIN ? 'color:var(--green) !important;font-weight:700;'
              : r.totalL >= r.reqL ? 'color:var(--yellow) !important;font-weight:700;'
              : 'color:var(--red) !important;font-weight:700;')
            : '';
          const botMargin = Number.isFinite(r.reqL) ? gpVolDisp(r.totalL - r.reqL) + ' ' + volU : '—';
          const botMarginCol = !Number.isFinite(r.reqL) ? 'color:var(--muted);'
            : r.totalL < r.reqL ? 'color:var(--red) !important;font-weight:700;'
            : r.totalL < r.reqL * GP_ONEWAY_MARGIN ? 'color:var(--yellow) !important;font-weight:700;'
            : 'color:var(--green) !important;font-weight:700;';
          const botSuffNote = Number.isFinite(r.reqL)
            ? (r.totalL >= r.reqL * GP_ONEWAY_MARGIN
              ? `<br><span style="color:var(--green) !important;font-size:10px;">✓ ${gpVolDisp(r.reqL)} ${volU} needed</span>`
              : r.totalL >= r.reqL
                ? `<br><span style="color:var(--yellow) !important;font-size:10px;">⚠ tight — ${gpVolDisp(r.reqL)} ${volU} needed</span>`
                : '')
            : (r.reqL != null ? '<br><span style="color:var(--orange) !important;font-size:10px;">Invalid gas</span>' : '');
          html += `<tr class="${Number.isFinite(r.reqL) && r.totalL >= r.reqL && r.totalL < r.reqL * GP_ONEWAY_MARGIN ? 'gas-tight-row' : ''}">
            <td style="white-space:nowrap;">${r.label}</td>
            <td style="${botVolColor}">${gpVolDisp(r.totalL)} ${volU}</td>
            <td>${gpVolDisp(r.portionL)} ${volU} <span style="color:var(--muted);">(${ruleTxt})</span></td>
            <td style="color:var(--accent) !important;font-weight:700;">${gpPresDisp(r.turnBar)} ${presU}</td>
            <td>${gpPresDisp(r.reserveBar)} ${presU}</td>
            <td><span style="color:var(--accent) !important;font-weight:700;">⟳ turn</span>${botSuffNote}</td>
            <td style="${botMarginCol}">${botMargin}</td>
          </tr>`;
        }
      } else {
        let suffCell, statusCol;
        if (r.reqL == null) {
          suffCell = '<span style="color:var(--muted);">run plan</span>';
          statusCol = 'var(--muted)';
        } else if (!Number.isFinite(r.reqL)) {
          suffCell = '<span style="color:var(--orange) !important;font-weight:700;">invalid gas</span>';
          statusCol = 'var(--orange)';
        } else if (r.totalL >= r.reqL * GP_ONEWAY_MARGIN) {
          suffCell = '<span style="color:var(--green) !important;font-weight:700;">✓ ok</span><br><span style="color:var(--muted);font-size:10px;">req ' + gpVolDisp(r.reqL) + ' ' + volU + '</span>';
          statusCol = 'var(--green)';
        } else if (r.totalL >= r.reqL) {
          suffCell = '<span>⚠ tight</span><br><span style="color:var(--muted);font-size:10px;">req ' + gpVolDisp(r.reqL) + ' ' + volU + '</span>';
          statusCol = '#FF4433';
        } else {
          suffCell = '<span style="color:var(--red) !important;font-weight:700;">✗ short</span><br><span style="color:var(--muted);font-size:10px;">req ' + gpVolDisp(r.reqL) + ' ' + volU + '</span>';
          statusCol = 'var(--red)';
        }
        const isTight = r.reqL != null && r.totalL >= r.reqL && r.totalL < r.reqL * GP_ONEWAY_MARGIN;
        const marginL = r.reqL != null ? r.totalL - r.reqL : null;
        const marginDisp = marginL != null ? (marginL >= 0 ? '+' : '−') + gpVolDisp(Math.abs(marginL)) + ' ' + volU : '—';
        const marginCol = marginL == null ? 'var(--muted)' : marginL < 0 ? 'var(--red)' : isTight ? '#FF4433' : 'var(--green)';
        html += `<tr class="${isTight ? 'gas-tight-row' : ''}">
          <td style="white-space:nowrap;">${r.label}</td>
          <td style="${isTight ? '' : 'color:' + statusCol + ' !important;'}font-weight:700;">${gpVolDisp(r.totalL)} ${volU}</td>
          <td style="color:var(--muted);">—</td>
          <td style="color:var(--muted);">one-way</td>
          <td>${gpPresDisp(r.reserveBar)} ${presU}</td>
          <td>${suffCell}</td>
          <td style="color:${marginCol} !important;font-weight:700;">${marginDisp}</td>
        </tr>`;
      }
    });
    if (!html) html = `<tr><td colspan="7" style="color:var(--muted);text-align:center;">Configure a bottom gas cylinder.</td></tr>`;
    body.innerHTML = html;
  }

  const note = document.getElementById('gpResultNote');
  if (note) {
    const ruleName = _gasRule === 'half' ? 'Half Tank' : 'Rule of Thirds';
    note.innerHTML = needPlan
      ? `Rule: ${ruleName} · Deco/travel requirements need a deco plan — run one on the Deco Schedule tab first.`
      : `Rule: ${ruleName} · One-way requirements pulled from the last deco plan run.`;
  }

  window._lastGasPlan = { rows, rule: _gasRule };
}

function buildGasPlanText() {
  calcGasPlan();
  const gp = window._lastGasPlan;
  if (!gp || !gp.rows.length) return null;
  const volU  = units === 'imperial' ? 'cu ft' : 'L';
  const presU = units === 'imperial' ? 'psi'   : 'bar';
  const depthU = units === 'imperial' ? 'ft' : 'm';
  const dateStr = new Date().toLocaleDateString('en-GB', { day:'2-digit', month:'short', year:'numeric' });
  const ruleName = gp.rule === 'half' ? 'Half Tank' : 'Thirds';

  // Pull dive info from last plan
  const depth   = document.getElementById('decoDepth')?.value  || '—';
  const bt      = document.getElementById('decoBT')?.value     || '—';
  const lastPlan = window._lastPlan;
  const rtStr   = lastPlan ? `RT ${lastPlan.rt} min` : '';

  const L = [];
  L.push('LSP GAS PLAN');
  L.push(`${dateStr} | ${units === 'imperial' ? 'Imperial' : 'Metric'} | Rule: ${ruleName}`);
  L.push(`Dive: ${depth}${depthU} / BT ${bt} min${rtStr ? ' / ' + rtStr : ''}`);
  L.push('---');

  gp.rows.forEach(r => {
    if (r.kind === 'bottom') {
      const ruleTxt = gp.rule === 'half' ? '1/2' : '1/3';
      const botLblTxt = r.label.includes('(+Travel)') ? r.label.replace('(+Travel)', '+ Travel cyl') : r.label;
      L.push(`BOTTOM GAS: ${botLblTxt}`);
      L.push(`  Usable: ${gpVolDisp(r.totalL)}${volU}  Reserve: ${gpPresDisp(r.reserveBar)}${presU}`);
      if (r.shortL != null && r.shortL > 0) {
        L.push(`  ! INSUFFICIENT: need ${gpVolDisp(r.reqL)}${volU}, have ${gpVolDisp(r.totalL)}${volU} (short ${gpVolDisp(r.shortL)}${volU})`);
        if (r.maxBTmin != null) {
          L.push(`  > Shorten BT to ${r.maxBTmin} min, turn at ${gpPresDisp(r.maxTurnBar)}${presU}${r.maxBTEstimate ? ' (conservative estimate)' : ''}`);
          L.push(`  > Or use a larger cylinder / add a stage`);
        }
      } else {
        L.push(`  Turn: ${gpPresDisp(r.turnBar)}${presU}  (${ruleTxt} of ${gpVolDisp(r.portionL)}${volU})`);
        if (r.reqL != null) L.push(`  Plan needs: ${gpVolDisp(r.reqL)}${volU} — OK`);
      }
    } else {
      const name = r.label.toUpperCase();
      L.push(name);
      L.push(`  Avail: ${gpVolDisp(r.totalL)}${volU}  Reserve: ${gpPresDisp(r.reserveBar)}${presU}`);
      if (r.reqL == null) {
        L.push('  Required: run deco plan first');
      } else {
        const margin = r.totalL - r.reqL;
        const status = r.totalL >= r.reqL * GP_ONEWAY_MARGIN ? 'OK' : r.totalL >= r.reqL ? 'TIGHT' : 'INSUFFICIENT';
        L.push(`  Need: ${gpVolDisp(r.reqL)}${volU}  Margin: ${gpVolDisp(margin)}${volU}  [${status}]`);
        if (status === 'INSUFFICIENT') L.push('  > Add more gas or reduce deco obligation');
      }
    }
    L.push('');
  });

  L.push('LSP D-Planner+ — threecats-lsp.com/d-planner-plus');
  return L.join('\n');
}

function copyGasPlan() {
  const text = buildGasPlanText();
  if (!text) return;
  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(text).then(() => showCopyToast()).catch(() => copyFallback(text));
  } else {
    copyFallback(text);
  }
}

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
  const volU  = units === 'imperial' ? 'cu ft' : 'L';
  const presU = units === 'imperial' ? 'psi'   : 'bar';
  const ruleName = gp.rule === 'half' ? 'Half Tank' : 'Rule of Thirds';

  const PW=210, PH=297, ML=14, MR=14, MT=10, MB=10, CW=182;
  let y=MT;
  function cleanPDF(s){
    if(!s) return '';
    s = s.replace(/·|•/g,'*').replace(/—/g,'--').replace(/–/g,'-');
    // Strip decorative emoji/icon blocks but preserve ✓✗⚠ and arrows ↑↓←→
    s = s.replace(/[\u2600-\u269F\u26A1-\u26FF\u2700-\u2712\u2714-\u2716\u2718-\u27FF\u2B00-\u2BFF\u2300-\u23FF\uFE0F]/g,'');
    s = s.replace(/[^\x20-\x7E\xA0-\u024F\u2190-\u2193\u2713\u2717\u26A0]/g,'');
    return s.trim();
  }
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
  doc.text(`Units: ${units === 'imperial' ? 'Imperial (cu ft / psi)' : 'Metric (L / bar)'}`, ML+3, y+9.5);
  doc.setTextColor(0,0,0); y+=16;

  // Table header
  const headers=['GAS','TOTAL VOL','THIRDS','TURN PRESS','RESERVE','SUFFICIENT'];
  const colW=[40,30,34,28,24,26];
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
        `${gpVolDisp(r.totalL)} ${volU}`,
        isShort ? `need ${gpVolDisp(r.reqL)} ${volU}` : `${gpVolDisp(r.portionL)} ${volU} (${ruleTxt})`,
        isShort ? `(${ruleTxt} rule)` : `${gpPresDisp(r.turnBar)} ${presU}`,
        `${gpPresDisp(r.reserveBar)} ${presU}`,
        isShort ? `SHORT ${gpVolDisp(r.shortL)} ${volU}` : 'TURN',
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
        `${gpVolDisp(r.totalL)} ${volU}`,
        r.reqL==null?'req --':`req ${gpVolDisp(r.reqL)} ${volU}`,
        'one-way',
        `${gpPresDisp(r.reserveBar)} ${presU}`,
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
