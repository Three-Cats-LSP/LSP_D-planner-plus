/**
 * Schedule runner core — VPM/ZHL UI orchestration, visible schedule table contract,
 * and plan exposure totals. Loaded after results-render-core and before planner-shell.
 */
'use strict';
const SCHEDULE_TABLE_COLUMNS = Object.freeze(['Phase', 'Depth', 'Stop', 'Run', 'Mix', 'PPO2', 'CNS', 'EAD']);

function scheduleColumnCount() {
  return SCHEDULE_TABLE_COLUMNS.length;
}

function scheduleCell(label, value, attrs) {
  const attrText = attrs ? ' ' + String(attrs).trim() : '';
  const dataLabel = label && label !== 'Phase' ? ` data-label="${escHtmlAttr(label)}"` : '';
  const safeValue = typeof escapeHtmlText === 'function'
    ? escapeHtmlText(value ?? '')
    : String(value ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  return `<td${dataLabel}${attrText}>${safeValue}</td>`;
}

function scheduleErrorRowHtml(message) {
  return `<tr data-phase="error">${scheduleCell('', message, `colspan="${scheduleColumnCount()}" class="schedule-error-cell" style="color:var(--red);padding:12px;"`)}</tr>`;
}

function renderScheduleErrorRow(message, tbodyId) {
  const tbody = document.getElementById(tbodyId || 'decoTableBody');
  if (tbody) tbody.innerHTML = scheduleErrorRowHtml(message);
  return !!tbody;
}

function fmtRowTTS(rowRunMin, rtAtBottomEnd, finalRunMin) {
  if (rowRunMin == null || isNaN(rowRunMin) || rowRunMin < rtAtBottomEnd - 0.001) return '—';
  return toMMSS(Math.max(0, finalRunMin - rowRunMin));
}

function parsePlanSummaryText(t) {
  const s = (t || '').replace(/\s+/g, ' ');
  return {
    runTime:  (s.match(/Run time:\s*([\d'":]+)/i) || [])[1] || '-',
    tts:      (s.match(/TTS:\s*([\d'":]+)/i) || [])[1] || '-',
    decoTime: (s.match(/Deco time:\s*([\d'":]+)/i) || [])[1] || '-',
    cns:      (s.match(/CNS:\s*([\d.]+%|-)/i) || [])[1] || '-',
    otu:      (s.match(/OTU:\s*(\d+|-)/i) || [])[1] || '-',
    prt:      (s.match(/PrT:\s*([\d.]+|-)/i) || [])[1] || '-',
    decozone: ((s.match(/Decozone:\s*([\d.]+ (?:m|ft)|—|-)/i) || s.match(/Deco zone:\s*([\d.]+ (?:m|ft)|—|-)/i) || [])[1] || '').trim() || '-',
    decoStop: (s.match(/First deco:\s*([\d.]+ (?:m|ft)|—|-)/i) || [])[1]?.trim() || '-',
  };
}

function getContingencySummaryExport() {
  const c = window._lastContingency;
  const totRow = document.querySelector('#contingencyResult .deco-table tbody tr[data-phase="totals"] td');
  if (totRow) {
    const p = totRow.dataset.run ? {
      runTime: normalizeMMSSDisplay(totRow.dataset.run) || '-',
      tts: normalizeMMSSDisplay(totRow.dataset.tts) || '-',
      decoTime: normalizeMMSSDisplay(totRow.dataset.deco) || '-',
      cns: totRow.dataset.cns||'-', otu: totRow.dataset.otu||'-', prt: totRow.dataset.prt||'-',
      decozone: totRow.dataset.decozone||'-', decoStop: totRow.dataset.decostop||'-',
      surfGF: totRow.dataset.surfgf||'-',
    } : parsePlanSummaryText(totRow.textContent);
    if (c) {
      if (p.runTime === '-') p.runTime = c.lastRunFmt || `${c.lastRun}'00"`;
      if (p.decoTime === '-') p.decoTime = c.decoTimeFmt || `${c.decoTime}'00"`;
      if (p.cns === '-') p.cns = c.totalCNS || '-';
      if (p.otu === '-') p.otu = c.totalOTU || '-';
      if (p.prt === '-') p.prt = c.totalPrT || '-';
      if (p.tts === '-') p.tts = c.tts || '-';
      if (p.decozone === '-') p.decozone = c.decozoneDisp || formatDecoZoneStart(c.decoZoneStart);
      if (p.decoStop === '-') p.decoStop = c.decoStop || '-';
      if (!p.surfGF || p.surfGF === '-') p.surfGF = c.surfGF || '-';
    }
    p.runTime = normalizeMMSSDisplay(p.runTime);
    p.tts = normalizeMMSSDisplay(p.tts);
    p.decoTime = normalizeMMSSDisplay(p.decoTime);
    return p;
  }
  if (!c) return getPlanSummaryExport();
  return {
    runTime: normalizeMMSSDisplay(c.lastRunFmt || `${c.lastRun}'00"`),
    tts: normalizeMMSSDisplay(c.tts || '-'),
    decoTime: normalizeMMSSDisplay(c.decoTimeFmt || `${c.decoTime}'00"`),
    cns: c.totalCNS || '-',
    otu: c.totalOTU || '-',
    prt: c.totalPrT || '-',
    decozone: c.decozoneDisp || formatDecoZoneStart(c.decoZoneStart),
    decoStop: c.decoStop || '-',
    surfGF: c.surfGF || '-',
  };
}

function getPlanSummaryExport(fromTotalsEl) {
  const el = fromTotalsEl || document.querySelector('#decoTableBody tr[data-phase="totals"] td');
  const lp = window._lastPlan || {};
  if (el) {
    // Read from data-* attributes (text content is empty to avoid inflating table width)
    const p = el.dataset.run ? {
      runTime:  normalizeMMSSDisplay(el.dataset.run)  || '-',
      tts:      normalizeMMSSDisplay(el.dataset.tts)  || '-',
      decoTime: normalizeMMSSDisplay(el.dataset.deco) || '-',
      cns:      el.dataset.cns  || '-',
      otu:      el.dataset.otu  || '-',
      prt:      el.dataset.prt  || '-',
      decozone: el.dataset.decozone || '-',
      decoStop: el.dataset.decostop || '-',
      surfGF:   el.dataset.surfgf || '-',
    } : parsePlanSummaryText(el.textContent);
    p.runTime = normalizeMMSSDisplay(p.runTime);
    p.tts = normalizeMMSSDisplay(p.tts);
    p.decoTime = normalizeMMSSDisplay(p.decoTime);
    if (p.decozone === '-') p.decozone = formatDecoZoneStart(lp.decoZoneStart);
    if (p.decoStop === '-') p.decoStop = formatDecoStopDepth(lp.firstStopDepth);
    if (p.tts === '-' && lp.tts != null) p.tts = toMMSS(lp.tts);
    if (!p.surfGF || p.surfGF === '-') p.surfGF = lp.surfaceGF != null ? Math.round(lp.surfaceGF) + '%' : '-';
    return p;
  }
  return {
    runTime: '-', decoTime: '-',
    tts: lp.tts != null ? toMMSS(lp.tts) : '-',
    cns: '-', otu: '-', prt: '-',
    decozone: formatDecoZoneStart(lp.decoZoneStart),
    decoStop: formatDecoStopDepth(lp.firstStopDepth),
  };
}

function getDecoZoneExportVal(fromTotalsEl) {
  return getPlanSummaryExport(fromTotalsEl).decozone;
}

function _escHtmlPre(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

/** VPM deco gas switch depth (metric m or imperial ft per unit mode). */
function vpmDecoSwitchDepthVal(dgO2pct, ppO2Limit) {
  const dU = units === 'metric';
  const fO2 = dgO2pct / 100;
  if (fO2 >= 0.995) {
    const modM = calcGasMODm(fO2, ppO2Limit || 1.6);
    return dU ? modM : Math.round(modM * 3.28084);
  }
  const modM = Math.max(0, Math.floor(((ppO2Limit || 1.6) / fO2 - altSurfaceP) / BAR_PER_METRE));
  return dU ? modM : Math.floor(modM * 3.28084);
}

/** Parse gas mix label for export/banner (50/00, 100%, Air, …). */
function shortMixLabel(m) {
  const s = (m || '').trim();
  if (!s) return '-';
  if (/^\d+\/\d+$/.test(s)) return s;
  if (s === '100%') return '100%';
  if (/^air$/i.test(s)) return 'Air';
  if (/^100/i.test(s)) return '100%';
  const ean = s.match(/[Ee][Aa][Nn]\s*(\d+)/); if (ean) return ean[1] + '/00';
  const pct = s.match(/(\d+)%/); if (pct) return pct[1] + '/00';
  return s;
}

/** Deco gas switches — reads computed table rows or falls back to gas cards. */
function getDecoGasSwitches() {
  const gswRows = Array.from(document.querySelectorAll('#decoTableBody tr[data-phase="switch"]'));
  if (gswRows.length) {
    return gswRows.map(tr => {
      const depthTxt = (tr.querySelector('td[data-label="Depth"]') || tr.querySelectorAll('td')[1])?.textContent?.trim() || '';
      const mixTxt = (tr.querySelector('td[data-label="Mix"]') || tr.querySelectorAll('td')[3])?.textContent?.trim() || '';
      const legacy = depthTxt.match(/^(.+?)\s*@\s*(.+)$/i);
      if (legacy) {
        return {
          gas: shortMixLabel(legacy[1]),
          depth: legacy[2].replace(/\s+/g, ''),
        };
      }
      return {
        gas: shortMixLabel(mixTxt || depthTxt.split('@')[0] || depthTxt),
        depth: depthTxt.replace(/\s+/g, '') || '-',
      };
    });
  }
  const switches = [];
  const decoModelSel = document.getElementById('algorithmSelect')?.value || 'ZHLC_GF';
  const isVPM = decoModelSel === 'VPMB' || decoModelSel === 'VPMB_GFS';
  const ppO2Deco  = parseFloat(document.getElementById('ppo2Deco')?.value)  || 1.6;
  const ppO2Bot   = parseFloat(document.getElementById('ppo2Bottom')?.value) || 1.4;
  const _lastStopM = parseFloat(document.getElementById('lastDecoStop')?.value) || 3;
  const _decoStepM = parseFloat(document.getElementById('decoStep')?.value)    || 3;
  const dU = units === 'metric';
  for (const idx of getAllDecoGasIds()) {
    const dgf = getDecoCardFractions(idx);
    if (!dgf || dgf.fN2 === null) continue;
    const gas = shortMixLabel(getGasLabel(dgf.fO2, dgf.fHe));
    let sw;
    if (isVPM) {
      const fO2 = dgf.fO2 != null ? dgf.fO2 : Math.max(0, 1 - dgf.fN2 - (dgf.fHe || 0));
      const ppLimit = fO2 > 0.60 ? ppO2Deco : ppO2Bot;
      const switchD = vpmDecoSwitchDepthVal(Math.round(fO2 * 100), ppLimit);
      sw = dU ? Math.max(3, Math.floor(switchD / 3) * 3) : Math.max(10, Math.floor(switchD / 10) * 10);
    } else {
      // Global switch-depth fallback (closure-scoped version not available here):
      const fO2 = dgf.fO2 != null ? dgf.fO2 : Math.max(0, 1 - dgf.fN2 - (dgf.fHe || 0));
      if (fO2 <= 0) continue;
      else {
        const limit = fO2 > 0.60 ? ppO2Deco : ppO2Bot;
        const modM = calcGasMODm(fO2, limit);
        sw = Math.max(_lastStopM, Math.max(0, Math.floor(modM / _decoStepM) * _decoStepM));
      }
    }
    if (!sw || sw <= 0) continue;
    const depth = dU ? sw + 'm' : Math.round(sw * 3.28084) + 'ft';
    switches.push({ gas, depth });
  }
  return switches;
}

function getDecoGasSwitchLines() {
  const ccrUi = isCcrGasUiMode();
  const prefix = ccrUi ? 'Bailout mix' : 'Deco Gas';
  return getDecoGasSwitches().map((g, i) => `${prefix} ${i + 1}  : ${g.gas} (switch @ ${g.depth})`);
}


function measureDecoScheduleColumnWidth(table) {
  let left = Infinity;
  let right = -Infinity;
  table.querySelectorAll('tr:not(.deco-totals-row)').forEach(row => {
    Array.from(row.cells || []).forEach(cell => {
      const rect = cell.getBoundingClientRect();
      if (rect.width <= 0) return;
      left = Math.min(left, rect.left);
      right = Math.max(right, rect.right);
    });
  });
  return right > left ? right - left : (table.getBoundingClientRect().width || table.offsetWidth);
}

function syncDecoScheduleStackWidths() {
  document.querySelectorAll('.deco-table-wrap').forEach(wrap => {
    if (wrap.closest('#contingencyResult') && wrap.closest('#resultsPanel')) {
      wrap.style.width = '';
      wrap.style.removeProperty('--deco-table-width');
      return;
    }
    const table = wrap.querySelector('.deco-table');
    if (!table?.tBodies[0]?.rows.length) {
      wrap.style.width = '';
      wrap.style.removeProperty('--deco-table-width');
      return;
    }
    wrap.style.width = '';
    wrap.style.removeProperty('--deco-table-width');
    void wrap.offsetHeight;
    const w = measureDecoScheduleColumnWidth(table);
    if (w > 0) {
      const px = w + 'px';
      wrap.style.setProperty('--deco-table-width', px);
      wrap.style.width = px;
    }
  });
  const stack = document.getElementById('contingencyScheduleStack');
  const btn = stack?.querySelector('.deco-contingency-calc');
  const emergWrap = document.querySelector('#contingencyResult .deco-table-wrap');
  const emergAlerts = document.getElementById('decoAlertsEmergency');
  if (stack?.closest('#resultsPanel')) {
    stack.style.width = '100%';
    if (btn) btn.style.width = '100%';
    if (emergWrap) {
      emergWrap.style.width = '';
      emergWrap.style.removeProperty('--deco-table-width');
    }
    if (emergWrap && emergAlerts) {
      emergAlerts.style.width = '';
      emergAlerts.style.maxWidth = '';
      emergAlerts.style.boxSizing = '';
    }
  } else if (stack && btn) {
    const wrap = emergWrap;
    if (wrap?.style.width) {
      stack.style.width = wrap.style.width;
      btn.style.width = '100%';
    } else {
      stack.style.width = '';
    }
    if (emergWrap && emergAlerts) {
      if (emergWrap.style.width) {
        emergAlerts.style.width = emergWrap.style.width;
        emergAlerts.style.maxWidth = '100%';
        emergAlerts.style.boxSizing = 'border-box';
      } else {
        emergAlerts.style.width = '';
        emergAlerts.style.maxWidth = '';
        emergAlerts.style.boxSizing = '';
      }
    }
  }
  const mainWrap = document.querySelector('#decoResult .deco-table-wrap');
  const decoAlerts = document.getElementById('decoAlerts');
  const decoAlertsNarcotic = document.getElementById('decoAlertsNarcotic');
  [decoAlerts, decoAlertsNarcotic].forEach(alertsEl => {
    if (!alertsEl) return;
    if (mainWrap && mainWrap.style.width) {
      alertsEl.style.width = mainWrap.style.width;
      alertsEl.style.maxWidth = '100%';
      alertsEl.style.boxSizing = 'border-box';
    } else {
      alertsEl.style.width = '';
      alertsEl.style.maxWidth = '';
      alertsEl.style.boxSizing = '';
    }
  });
}

function scheduleDecoScheduleStackSync() {
  requestAnimationFrame(() => {
    syncDecoScheduleStackWidths();
    requestAnimationFrame(syncDecoScheduleStackWidths);
  });
}

function planInfoTipIconHtml() {
  return `<span class="tip-icon" onclick="event.stopPropagation();showTip('Plan summary',PLAN_INFO_TIP)" style="vertical-align:middle;margin-right:12px;cursor:pointer;"><svg fill="none" height="11" viewBox="0 0 11 11" width="11" xmlns="http://www.w3.org/2000/svg"><circle cx="5.5" cy="5.5" r="5" stroke="currentColor" stroke-width="1.1"></circle><path d="M4.1 3.8 Q4.1 2.4 5.5 2.4 Q6.9 2.4 6.9 3.7 Q6.9 4.6 5.5 5.3 L5.5 6.2" fill="none" stroke="currentColor" stroke-linecap="round" stroke-width="1.1"></path><circle cx="5.5" cy="7.4" fill="currentColor" r="0.55"></circle></svg></span>`;
}

function buildPlanInfoRowHtml(o, phase) {
  const decoColor = o.hasDeco ? 'var(--red)' : 'var(--green)';
  const surfGFVal = o.surfaceGF != null ? Math.round(o.surfaceGF) : null;
  const surfGFDisp = surfGFVal != null ? surfGFVal + '%' : '—';
  const surfGFColor = surfGFVal == null ? 'var(--muted)' :
    surfGFVal >= 100 ? 'var(--red)' : surfGFVal >= 85 ? 'var(--orange)' :
    surfGFVal >= 70 ? 'var(--yellow)' : 'var(--green)';
  const firstStopColor = (o.decoStop && o.decoStop !== '—' && o.decoStop !== '-') ? 'var(--red)' : 'var(--text)';
  const innerHtml = `<div class="deco-totals-inner">
      ${planInfoTipIconHtml()}
      <span class="summary-stat"><span>Run time:</span> <span style="color:#2563eb">${o.runTime}</span></span> &nbsp;
      <span class="summary-stat"><span>TTS:</span> <span>${o.tts}</span></span> &nbsp;
      <span class="summary-stat">Deco time: <span style="color:${decoColor}">${o.decoTime}</span></span> &nbsp;
      <span class="summary-stat">CNS: <span style="color:${o.cnsColor}">${o.cns}</span></span> &nbsp;
      <span class="summary-stat">OTU: <span style="color:${o.otuColor || 'var(--text)'}">${o.otu}</span></span> &nbsp;
      <span class="summary-stat">PrT: <span style="color:${o.prtColor}" title="${o.prtTitle || ''}">${o.prt}</span></span> &nbsp;
      <span class="summary-stat">Surf GF: <span style="color:${surfGFColor}" title="Surface gradient factor — tissue load ÷ M-value at surface">${surfGFDisp}</span></span> &nbsp;
      <span class="summary-stat">Decozone: <span>${o.decozone}</span></span> &nbsp;
      <span class="summary-stat">First deco: <span style="color:${firstStopColor}">${o.decoStop}</span></span>
    </div>`;
  const totalsEl = document.getElementById('decoTotals');
  if (totalsEl) {
    totalsEl.innerHTML = '';
    totalsEl.style.display = 'none';
  }
  const rowHtml = `<tr class="deco-totals-row" data-phase="${phase || 'totals'}"><td colspan="20" data-run="${escHtmlAttr(o.runTime)}" data-tts="${escHtmlAttr(o.tts)}" data-deco="${escHtmlAttr(o.decoTime)}" data-cns="${escHtmlAttr(o.cns)}" data-otu="${escHtmlAttr(o.otu)}" data-prt="${escHtmlAttr(o.prt)}" data-decozone="${escHtmlAttr(o.decozone)}" data-decostop="${escHtmlAttr(o.decoStop)}" data-surfgf="${escHtmlAttr(surfGFDisp)}">${innerHtml}</td></tr>`;
  scheduleDecoScheduleStackSync();
  return rowHtml;
}

function compactExportDepth(v) {
  if (!v || v === '-' || v === '—') return v;
  return String(v).replace(/(\d+(?:\.\d+)?)\s+(m|ft)\b/gi, '$1$2').trim();
}

function formatPlanSummaryBlock(p, compact) {
  const sg = p.surfGF || '-';
  if (compact) {
    const dz = compactExportDepth(p.decozone);
    const ds = compactExportDepth(p.decoStop);
    return [
      `RT: ${p.runTime} TTS: ${p.tts} Deco: ${p.decoTime}`,
      `CNS: ${p.cns} OTU: ${p.otu} PrT: ${p.prt}`,
      `Surf GF: ${sg} Decozone: ${dz}`,
      `First deco: ${ds}`,
    ];
  }
  return [
    `Deco Time: ${p.decoTime}  Run Time: ${p.runTime}  TTS: ${p.tts}`,
    `CNS: ${p.cns}  OTU: ${p.otu}  PrT: ${p.prt}`,
    `Surf GF: ${sg}  Decozone: ${p.decozone}  First deco: ${p.decoStop}`,
  ];
}

/** Compact 3-line totals footer for .txt export (no inch marks on times). */
function formatExportSummaryBlock(p) {
  const stripInch = s => (s && s !== '-') ? String(s).replace(/"/g, '') : s;
  const dz = compactExportDepth(p.decozone);
  const ds = compactExportDepth(p.decoStop);
  const sg = p.surfGF || '-';
  return [
    `RT: ${stripInch(p.runTime)} TTS: ${stripInch(p.tts)} Deco: ${stripInch(p.decoTime)}`,
    `CNS: ${p.cns} OTU: ${p.otu} PrT: ${p.prt}`,
    `Surf GF: ${sg} Decozone: ${dz} First deco: ${ds}`,
  ];
}

function injectTtsCells(tbodyId, rtAtBottomEnd) {
  const tbody = document.getElementById(tbodyId || 'decoTableBody');
  if (!tbody) return;
  let finalRun = 0;
  tbody.querySelectorAll('tr[data-phase]').forEach(tr => {
    const ph = tr.dataset.phase;
    if (ph === 'totals' || ph === 'switch') return;
    const runVal = parseRunMinutes(tr.querySelectorAll('td')[4]?.textContent);  // Run is col 4 (icon|Depth|Stop|Mix|Run)
    if (runVal > finalRun) finalRun = runVal;
  });
  tbody.querySelectorAll('tr[data-phase]').forEach(tr => {
    const ph = tr.dataset.phase;
    if (ph === 'switch' || ph === 'totals') return;
    const tds = tr.querySelectorAll('td');
    if (tds.length < 4) return;
    tr.querySelector('td[data-label="TTS"]')?.remove();
    const runVal = parseRunMinutes(tds[4]?.textContent);
    const cell = document.createElement('td');
    cell.setAttribute('data-label', 'TTS');
    cell.style.cssText = 'color:var(--muted);font-size:11px;text-align:right;';
    cell.textContent = fmtRowTTS(runVal, rtAtBottomEnd, finalRun);
    tds[4].insertAdjacentElement('afterend', cell);
  });
}

// AUDIT-UNIT:UI-UNIT-SWITCHING
function setUnits(u, opts) {
  opts = opts || {};
  const relabelOnly = !!opts.relabelOnly;
  const prev = units;
  units = u;
  updateMinDecoLabels(u !== 'imperial');

  const FT_PER_M = 3.28084;
  const PSI_PER_BAR = 14.5038;
  const CUFT_PER_L = 0.0353147;
  const isToImperial = !relabelOnly && u === 'imperial' && prev === 'metric';
  const isToMetric = !relabelOnly && u === 'metric' && prev === 'imperial';

  const setTxt = (id, txt) => {
    const el = document.getElementById(id);
    if (el) el.textContent = txt;
  };

  const convertNumericInput = (id, toImperial, toMetric, metricMax, imperialMax) => {
    const el = document.getElementById(id);
    if (!el) return;
    const v = parseFloat(el.value);
    if (Number.isNaN(v)) return;
    if (isToImperial) {
      if (imperialMax != null) el.max = imperialMax;
      el.value = toImperial(v);
    } else if (isToMetric) {
      if (metricMax != null) el.max = metricMax;
      el.value = toMetric(v);
    }
  };

  const relabelSelectOptions = (id, formatter) => {
    const sel = document.getElementById(id);
    if (!sel) return;
    Array.from(sel.options).forEach(opt => {
      const val = parseFloat(opt.value);
      if (!Number.isNaN(val)) opt.text = formatter(val);
    });
  };

  const relabelFieldLabelsByText = () => {
    document.querySelectorAll('label').forEach(label => {
      const raw = (label.textContent || '').trim();
      if (/\bBT SAC\b/i.test(raw)) label.textContent = u === 'imperial' ? 'BT SAC (ft³/min)' : 'BT SAC (L/min)';
      if (/\bDeco SAC\b/i.test(raw)) label.textContent = u === 'imperial' ? 'Deco SAC (ft³/min)' : 'Deco SAC (L/min)';
      if (/\bCyl\. Pressure\b/i.test(raw)) label.textContent = u === 'imperial' ? 'Cyl. Pressure (psi)' : 'Cyl. Pressure (bar)';
      if (/\bBottom Gas\b/i.test(raw) && /\(.*\)/.test(raw) && /bar|psi|L|cu ft|ft³/i.test(raw)) {
        if (/bar|psi/i.test(raw)) label.textContent = u === 'imperial' ? 'Bottom Gas (psi)' : 'Bottom Gas (bar)';
        if (/\bL\b|cu ft|ft³/i.test(raw)) label.textContent = u === 'imperial' ? 'Bottom Gas Size (ft³)' : 'Bottom Gas Size (L)';
      }
      if (/\bDeco Gas 1\b/i.test(raw) && /\(.*\)/.test(raw) && /bar|psi|L|cu ft|ft³/i.test(raw)) {
        if (/bar|psi/i.test(raw)) label.textContent = u === 'imperial' ? 'Deco Gas 1 (psi)' : 'Deco Gas 1 (bar)';
        if (/\bL\b|cu ft|ft³/i.test(raw)) label.textContent = u === 'imperial' ? 'Deco Gas 1 Size (ft³)' : 'Deco Gas 1 Size (L)';
      }
      if (/\bDeco Gas 2\b/i.test(raw) && /\(.*\)/.test(raw) && /bar|psi|L|cu ft|ft³/i.test(raw)) {
        if (/bar|psi/i.test(raw)) label.textContent = u === 'imperial' ? 'Deco Gas 2 (psi)' : 'Deco Gas 2 (bar)';
        if (/\bL\b|cu ft|ft³/i.test(raw)) label.textContent = u === 'imperial' ? 'Deco Gas 2 Size (ft³)' : 'Deco Gas 2 Size (L)';
      }
    });
  };

  const refreshMultiDiveDepthDisplays = () => {
    document.querySelectorAll('.mDLbl').forEach(el => {
      el.textContent = `Depth (${u === 'imperial' ? 'ft' : 'm'})`;
    });
    document.querySelectorAll('.mDepth').forEach(el => {
      const v = parseFloat(el.value);
      if (Number.isNaN(v)) return;
      if (isToImperial) {
        el.value = Math.round(v * FT_PER_M);
        el.max = 330;
      } else if (isToMetric) {
        el.value = (v / FT_PER_M).toFixed(1).replace(/\.0$/, '');
        el.max = 100;
      }
    });
  };

  const refreshInlineStaticText = () => {
    const versionRow = document.getElementById('mainVersionLabel');
    if (versionRow) versionRow.textContent = versionRow.textContent;
  };

  const syncSelect = id => {
    const el = document.getElementById(id);
    if (el) el.value = u;
  };
  syncSelect('unitsSelect');

  ['uImp','uMet'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.classList.toggle('active', id === (u === 'imperial' ? 'uImp' : 'uMet'));
  });
  ['ndlUImp','ndlUMet','mUImp','mUMet'].forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    const isImp = id.includes('Imp');
    el.classList.toggle('active', u === 'imperial' ? isImp : !isImp);
  });

  const applyDepthUnitSwitch = (id, metricMax, imperialMax) => {
    const el = document.getElementById(id);
    if (!el || (!isToImperial && !isToMetric)) return;
    let metres = parseFloat(el.dataset.depthM);
    if (!Number.isFinite(metres)) {
      const v = parseFloat(el.value);
      if (Number.isNaN(v)) return;
      metres = prev === 'imperial' ? v / FT_PER_M : v;
      el.dataset.depthM = String(metres);
    }
    if (isToImperial) {
      if (imperialMax != null) el.max = imperialMax;
      el.value = String(Math.round(metres * FT_PER_M));
    } else if (isToMetric) {
      if (metricMax != null) el.max = metricMax;
      el.value = Number.isInteger(metres) ? String(Math.round(metres))
        : metres.toFixed(1).replace(/\.0$/, '');
    }
    el.dataset.depthM = String(metres);
  };

  applyDepthUnitSwitch('recDepth', 100, 330);
  applyDepthUnitSwitch('tecDepth', 120, 394);
  applyDepthUnitSwitch('bestMixDepth', 100, 330);
  syncBestMixDepthConstraints?.();
  applyDepthUnitSwitch('cnsDepth', 60, 197);
  setTxt('cnsDepthLbl', `Depth (${u === 'imperial' ? 'ft' : 'm'})`);
  applyDepthUnitSwitch('endDepth', 100, 330);
  syncEndDepthConstraints?.();
  applyDepthUnitSwitch('siD1Depth', 60, 197);
  applyDepthUnitSwitch('siD2Depth', 60, 197);
  syncSurfIntDepthConstraints?.();

  const CYL_SIZE_MAX_L = 50;
  const CYL_SIZE_MIN_L = 0.5;
  const cylMaxCuFt = () => +(CYL_SIZE_MAX_L * CUFT_PER_L).toFixed(2);
  const cylMinCuFt = () => +(CYL_SIZE_MIN_L * CUFT_PER_L).toFixed(2);

  const applyCylinderSizeUnitSwitch = (id) => {
    const el = document.getElementById(id);
    if (!el || (!isToImperial && !isToMetric)) return;
    let litres = parseFloat(el.dataset.volumeL);
    if (!Number.isFinite(litres)) {
      const v = parseFloat(el.value);
      if (Number.isNaN(v)) return;
      litres = prev === 'imperial' ? v / CUFT_PER_L : v;
      el.dataset.volumeL = String(litres);
    }
    if (isToImperial) {
      el.min = String(cylMinCuFt());
      el.max = String(cylMaxCuFt());
      el.step = String(cylMinCuFt());
      el.value = (litres * CUFT_PER_L).toFixed(1).replace(/\.0$/, '');
    } else if (isToMetric) {
      el.min = String(CYL_SIZE_MIN_L);
      el.max = String(CYL_SIZE_MAX_L);
      el.step = String(CYL_SIZE_MIN_L);
      el.value = Number.isInteger(litres) ? String(Math.round(litres))
        : litres.toFixed(1).replace(/\.0$/, '');
    }
    el.dataset.volumeL = String(litres);
  };

  // ── Cylinder pressure conversion (all gas cards including dynamic ones) ──
  const allCylPres = ['cylBot_pres','cylTravelGas_pres','cylDg1_pres','cylDg2_pres',
    ...Array.from(document.querySelectorAll('[id^="cylDg"][id$="_pres"]')).map(el=>el.id)].filter((v,i,a)=>a.indexOf(v)===i);
  const allCylSize = ['cylBot_size','cylTravelGas_size','cylDg1_size','cylDg2_size',
    ...Array.from(document.querySelectorAll('[id^="cylDg"][id$="_size"]')).map(el=>el.id)].filter((v,i,a)=>a.indexOf(v)===i);
  const allCylReserve = ['cylBot_reserve','cylTravelGas_reserve','cylDg1_reserve','cylDg2_reserve',
    ...Array.from(document.querySelectorAll('[id^="cylDg"][id$="_reserve"]')).map(el=>el.id)].filter((v,i,a)=>a.indexOf(v)===i);
  allCylPres.forEach(id => {
    convertNumericInput(id, v => Math.round(v * PSI_PER_BAR), v => Math.round(v / PSI_PER_BAR), 300, 4351);
  });
  allCylSize.forEach(id => {
    applyCylinderSizeUnitSwitch(id);
  });
  syncCylinderSizeConstraints?.();
  allCylReserve.forEach(id => {
    convertNumericInput(id, v => Math.round(v * PSI_PER_BAR), v => Math.round(v / PSI_PER_BAR), 300, 4351);
  });

  // SAC conversion (L/min ↔ cu ft/min)
  convertNumericInput('sacBottom', v => (v * CUFT_PER_L).toFixed(2).replace(/\.0+$/, ''), v => Math.round(v / CUFT_PER_L), 60, 2.12);
  convertNumericInput('sacDeco',   v => (v * CUFT_PER_L).toFixed(2).replace(/\.0+$/, ''), v => Math.round(v / CUFT_PER_L), 40, 1.41);

  // ── Gas Plan tab conversions ──
  ['gpBot_size','gpTravel_size','gpDg1_size','gpDg2_size'].forEach(id => {
    convertNumericInput(id, v => (v * CUFT_PER_L).toFixed(1).replace(/\.0$/, ''), v => Math.round(v / CUFT_PER_L), 50, 1.77);
  });
  ['gpBot_fill','gpBot_reserve','gpTravel_fill','gpTravel_reserve','gpDg1_fill','gpDg1_reserve','gpDg2_fill','gpDg2_reserve'].forEach(id => {
    convertNumericInput(id, v => Math.round(v * PSI_PER_BAR), v => Math.round(v / PSI_PER_BAR), 300, 4351);
  });
  ['gpBot_size_lbl','gpTravel_size_lbl','gpDg1_size_lbl','gpDg2_size_lbl'].forEach(id =>
    setTxt(id, u === 'imperial' ? 'Size (ft³)' : 'Size (L)'));
  ['gpBot_fill_lbl','gpTravel_fill_lbl','gpDg1_fill_lbl','gpDg2_fill_lbl'].forEach(id =>
    setTxt(id, u === 'imperial' ? 'Fill psi' : 'Fill bar'));
  ['gpBot_reserve_lbl','gpTravel_reserve_lbl','gpDg1_reserve_lbl','gpDg2_reserve_lbl',
   'cylBot_reserve_lbl','cylTravelGas_reserve_lbl','cylDg1_reserve_lbl','cylDg2_reserve_lbl'].forEach(id =>
    setTxt(id, u === 'imperial' ? 'Reserve psi' : 'Reserve bar'));
  document.querySelectorAll('[id^="cylDg"][id$="_reserve_lbl"]').forEach(el => {
    el.textContent = u === 'imperial' ? 'Reserve psi' : 'Reserve bar';
  });
  if (document.getElementById('gasplan')?.classList.contains('active')) calcGasPlan();

  const du = u === 'metric' ? 'm' : 'ft';
  setTxt('depthLbl', `Depth (${du})`);
  setTxt('ndlDepthHdr', `Depth (${du})`);
  _syncDepthBtSteppers();
  // Altitude custom input unit label
  setTxt('altitudeCustomUnit', du);
  syncAltitudeCustomInputConstraints?.();
  if (document.getElementById('altitudeSelect')?.value === 'custom') {
    const altInp = document.getElementById('altitudeCustomInput');
    if (altInp) altInp.value = altitudeMToCustomDisplay(altitudeM);
  }
  const depthToggle = document.getElementById('stopDepthToggle');
  if (depthToggle) {
    const depthOpts = depthToggle.querySelectorAll('.option-pill-opt');
    if (depthOpts[0]) depthOpts[0].textContent = u === 'metric' ? '3 m' : '10 ft';
    if (depthOpts[1]) depthOpts[1].textContent = u === 'metric' ? '6 m' : '20 ft';
  }

  relabelSelectOptions('descentRate', v => u === 'imperial' ? Math.round(v * FT_PER_M) + ' ft/min' : v + ' m/min');
  relabelSelectOptions('ascentRate', v => u === 'imperial' ? Math.round(v * FT_PER_M) + ' ft/min' : v + ' m/min');
  relabelSelectOptions('decoAscentRate', v => u === 'imperial' ? Math.round(v * FT_PER_M) + ' ft/min' : v + ' m/min');
  relabelSelectOptions('surfaceAscentRate', v => u === 'imperial' ? Math.round(v * FT_PER_M) + ' ft/min' : v + ' m/min');
  relabelSelectOptions('decoStep', v => u === 'imperial' ? Math.round(v * FT_PER_M) + ' ft' : v + ' m');
  relabelSelectOptions('lastDecoStop', v => u === 'imperial' ? Math.round(v * FT_PER_M) + ' ft' : v + ' m');

  [['refDepthRec',40,130],['refDepthOW',18,60],['refDepthAdv',30,100]].forEach(([id,m,ft]) => {
    const el = document.getElementById(id);
    if (el) el.textContent = u === 'imperial' ? `${ft} ft` : `${m} m`;
  });

  const ndlRangeEl = document.getElementById('ndlRange');
  if (ndlRangeEl) {
    const metricLabels = ['10–12 m','15–18 m','21–27 m','30–40 m'];
    const imperialLabels = ['35–40 ft','50–60 ft','70–90 ft','100–130 ft'];
    Array.from(ndlRangeEl.options).forEach((opt, i) => {
      opt.text = u === 'imperial' ? imperialLabels[i] : metricLabels[i];
    });
  }

  // ── Cylinder label updates (fixed IDs with underscores) ──
  setTxt('cylBot_pres_lbl',       u === 'imperial' ? 'PSI' : 'Bar');
  setTxt('cylTravelGas_pres_lbl', u === 'imperial' ? 'PSI' : 'Bar');
  setTxt('cylDg1_pres_lbl',       u === 'imperial' ? 'PSI' : 'Bar');
  setTxt('cylDg2_pres_lbl',       u === 'imperial' ? 'PSI' : 'Bar');
  // Dynamic deco gas card labels
  document.querySelectorAll('[id^="cylDg"][id$="_pres_lbl"]').forEach(el => { el.textContent = u === 'imperial' ? 'PSI' : 'Bar'; });
  document.querySelectorAll('[id^="cylDg"][id$="_size"] ~ * label, label[id$="_size_lbl"]').forEach(el => { el.textContent = u === 'imperial' ? 'Size (ft³)' : 'Size (L)'; });
  // Cyl size labels (static)
  document.querySelectorAll('.field label').forEach(lbl => {
    const t = lbl.textContent.trim();
    if (/^Cyl\. Size/i.test(t) || t === 'Size' || t === 'Cyl. Size (L)' || t === 'Cyl. Size (ft³)' || t === 'Cyl. Size (cu ft)' || /^Size \(/.test(t)) {
      lbl.textContent = u === 'imperial' ? 'Size (ft³)' : 'Size (L)';
    }
    if (/^Cyl\. bar/i.test(t) || /^Cyl\. psi/i.test(t) || t === 'Bar' || t === 'PSI') {
      lbl.textContent = u === 'imperial' ? 'PSI' : 'Bar';
    }
  });
  ['cylSizeUnit','cylinderSizeUnit','tankSizeUnit'].forEach(id => setTxt(id, u === 'imperial' ? 'ft³' : 'L'));
  ['cylPressureUnit','tankPressureUnit'].forEach(id => setTxt(id, u === 'imperial' ? 'psi' : 'bar'));

  relabelFieldLabelsByText();
  refreshMultiDiveDepthDisplays();
  refreshInlineStaticText();
  syncContDepthLabels?.();

  ndlUnits = u;
  multiUnits = u;

  // Skip all recalculations in headless test mode
  if (window._zhlHeadless) return;

  renderNDLTable?.();
  buildUnifiedPlan?.();

  if (document.getElementById('plannerResult')?.innerHTML) runPlanner?.();
  if (document.getElementById('decoResult')?.innerHTML) {
    if (window._lastContingency) calcContingency();
  }

  // ── Refresh gas card MOD displays and travel gas switch depth ──
  updateGasMODDisplays?.();
  updateTravelGasMOD?.();

  // ── Refresh Tools panels that have depth/unit-sensitive displays ──
  // Update depth display labels on tools sliders when unit changes
  const bmDepthEl = document.getElementById('bestMixDepth');
  if (bmDepthEl) document.getElementById('bestMixDepthDisplay').textContent =
    bmDepthEl.value + (u === 'imperial' ? ' ft' : ' m');

  // Recalculate visible tools panels
  renderEADTable?.();
  renderGasTable?.();
  calcBestMix?.();
  calcEND_tool?.();
  calcSurfInt?.();
  calcAvgDepth?.();
  calcMODTool?.();
  renderModRefTable?.();
}

// ═══════════════════════════════════════════════
// SAFETY STOP CONTROLS
// ═══════════════════════════════════════════════
function _syncStopDepthPill() {
  const toggle = document.getElementById('stopDepthToggle');
  if (toggle) toggle.dataset.side = stopDepthM === 6 ? 'right' : 'left';
}
function _syncStopDurPill() {
  const toggle = document.getElementById('stopDurToggle');
  if (toggle) toggle.dataset.side = stopDurMin === 5 ? 'right' : 'left';
}
function toggleStopDepth() {
  setStopDepth(stopDepthM === 3 ? 6 : 3);
}
function toggleStopDur() {
  setStopDur(stopDurMin === 3 ? 5 : 3);
}
function setStopDepth(m) {
  stopDepthM = m;
  _syncStopDepthPill();
}
function setStopDur(min) {
  stopDurMin = min;
  _syncStopDurPill();
}

// ═══════════════════════════════════════════════
// GF CONTROLS
// ═══════════════════════════════════════════════
function autoSlashGF(input) {
  const oldVal = input.value;
  const oldPos = input.selectionStart;
  
  // If backspace was pressed at or near the slash, handle specially
  if (oldVal.length > 0 && oldVal[2] === '/' && oldPos === 3) {
    // Cursor is right after slash — delete the slash and one Low digit
    input.value = oldVal.slice(0, 1) + oldVal.slice(3);
    input.selectionStart = input.selectionEnd = 1;
    return;
  }
  
  // Normal digit-only filtering and slash insertion
  let v = input.value.replace(/[^\d/]/g, '');
  const digits = v.replace('/', '');
  
  if (digits.length >= 2) {
    v = digits.slice(0, 2) + '/' + digits.slice(2, 4);
  } else {
    v = digits;
  }
  
  input.value = v;
  
  // Smart cursor positioning: jump over the slash
  if (oldPos === 2 && v[2] === '/') {
    // User just typed the 2nd digit, move cursor past the slash
    input.selectionStart = input.selectionEnd = 3;
  } else if (oldPos === 3 && v[2] === '/') {
    // Cursor at slash position, move past it
    input.selectionStart = input.selectionEnd = 3;
  }
}

// ═══════════════════════════════════════════════
// BÜHLMANN PHYSICS — delegates to ZhlEngineBundle (zhl-physics-core.js)
// ═══════════════════════════════════════════════
// AUDIT-UNIT:UI-ZHL-DELEGATES
function _syncZhlBundleEnv(extra) {
  if (!window.ZhlEngineBundle) return;
  ZhlEngineBundle.applyEnvironment(Object.assign({
    altSurfaceP,
    barPerMetre: BAR_PER_METRE,
    waterVapor: WATER_VAPOR,
    altAcclimatized,
    allowO2AtMOD: typeof allowO2AtMOD !== 'undefined' ? allowO2AtMOD : true,
  }, extra || {}));
}
function initTissues() { _syncZhlBundleEnv(); return ZhlEngineBundle.initTissues(); }
function depthBar(m) { _syncZhlBundleEnv(); return ZhlEngineBundle.depthBar(m); }
function schreiner(p0, pGas, ht, t) { _syncZhlBundleEnv(); return ZhlEngineBundle.schreiner(p0, pGas, ht, t); }
function schreinerLinear(p0, fN2, ht, t, p0Amb, R) { _syncZhlBundleEnv(); return ZhlEngineBundle.schreinerLinear(p0, fN2, ht, t, p0Amb, R); }
function saturateLinear(tissues, fromDepth, toDepth, t, fN2, fHe) { _syncZhlBundleEnv(); return ZhlEngineBundle.saturateLinear(tissues, fromDepth, toDepth, t, fN2, fHe); }
function saturate(tissues, depthM, t, fN2, fHe) { _syncZhlBundleEnv(); return ZhlEngineBundle.saturate(tissues, depthM, t, fN2, fHe); }

function toggleCustomO2() {
  const gasMixEl = document.getElementById('gasMix');
  if (!gasMixEl) return;
  if (typeof algo !== 'undefined' && algo === 'padi') return;
  const mix = gasMixEl.value;
  const customField = document.getElementById('customO2Field');
  if (customField) customField.style.display = mix === 'custom' ? 'block' : 'none';
  const showTrimix = mix === 'trimix';
  const trimixO2Field = document.getElementById('plannerTrimixO2Field');
  const trimixHeField = document.getElementById('plannerTrimixHeField');
  if (trimixO2Field) trimixO2Field.style.display = showTrimix ? 'block' : 'none';
  if (trimixHeField) trimixHeField.style.display = showTrimix ? 'block' : 'none';
  syncTecGasMixMemory();
}

function getN2Frac(mix) {
  if (mix === 'ean32') return FN2_EAN32;
  if (mix === 'ean36') return FN2_EAN36;
  if (mix === 'custom') {
    return ZhlEngineBundle.n2FracFromCustomO2(parseFloat(document.getElementById('customO2')?.value) || 21);
  }
  if (mix === 'trimix') {
    const o2 = readDomO2Pct('plannerTrimixO2');
    const he = readDomHePct('plannerTrimixHe');
    const n2 = ZhlEngineBundle.n2FracFromPercentages(o2, he);
    if (n2 != null) return n2;
    console.warn('[LSP] Invalid trimix N₂ fraction — check O₂/He percentages.');
    return null;
  }
  return FN2_AIR;
}

function getHeFrac(mix) {
  if (mix === 'trimix') {
    const he = readDomHePct('plannerTrimixHe');
    return Number.isFinite(he) ? Math.min(1, Math.max(0, he / 100)) : 0;
  }
  return 0;
}

// ═══════════════════════════════════════════════════════════════════════════════
// CCR / Rebreather shared physics (v2.30) — used by Bühlmann + VPM paths
// ═══════════════════════════════════════════════════════════════════════════════
function getPscrMinPpo2() {
  return (typeof ZhlEngineBundle !== 'undefined' && ZhlEngineBundle.PSCR_MIN_PPO2 != null)
    ? ZhlEngineBundle.PSCR_MIN_PPO2 : 0.16;
}
const PSCR_DILUENT_EPSILON = 1e-6;
const PSCR_DEFAULT_BYPASS_RATIO = 10; // fallback when loop/diluent delta vanishes (typical sport pSCR ~1:7–1:10)
const PSCR_LOOP_VOLUME_MIN = ZhlEngineBundle.PSCR_LOOP_VOLUME_MIN;
const PSCR_LOOP_VOLUME_MAX = ZhlEngineBundle.PSCR_LOOP_VOLUME_MAX;
const PSCR_METABOLIC_O2_MIN = ZhlEngineBundle.PSCR_METABOLIC_O2_MIN;
const PSCR_METABOLIC_O2_MAX = ZhlEngineBundle.PSCR_METABOLIC_O2_MAX;

function parseCcrSetpoint(id, fallback) {
  const v = parseFloat(document.getElementById(id)?.value);
  return Number.isFinite(v) ? v : fallback;
}

function getCCRSettingsFromDOM() {
  const circuit = document.getElementById('circuitSelect')?.value || 'OC';
  const bailoutEl = document.getElementById('ccrBailoutToggle');
  const bailout = bailoutEl ? (bailoutEl.type === 'checkbox' ? bailoutEl.checked : bailoutEl.value === 'on') : false;
  const decoSP = parseCcrSetpoint('ccrDecoSetpoint', parseCcrSetpoint('ccrSetpoint', 1.3));
  const loopVol = parseCcrSetpoint('ccrLoopVolume', parseCcrSetpoint('scrLoopVolume', 10));
  const metO2 = parseCcrSetpoint('ccrMetabolicO2', parseCcrSetpoint('scrMetabolicO2', 1.5));
  // Keep hidden legacy fields in sync for saved presets / exports
  const legSp = document.getElementById('ccrSetpoint');
  const legVol = document.getElementById('scrLoopVolume');
  const legMet = document.getElementById('scrMetabolicO2');
  if (legSp) legSp.value = String(decoSP);
  if (legVol) legVol.value = String(loopVol);
  if (legMet) legMet.value = String(metO2);
  return {
    circuit,
    setpoint: decoSP,
    decoSetpoint: decoSP,
    bottomSetpoint: parseCcrSetpoint('ccrBottomSetpoint', 1.2),
    descentSetpoint: parseCcrSetpoint('ccrDescentSetpoint', 0.7),
    bailout,
    bailoutGfLow: parseInt(document.getElementById('ccrBailoutGfLow')?.value, 10) || 50,
    bailoutGfHigh: parseInt(document.getElementById('ccrBailoutGfHigh')?.value, 10) || 85,
    scrLoopVolume: loopVol,
    scrMetabolicO2: metO2,
    sacStress: parseFloat(document.getElementById('ccrSacStress')?.value) || 50,
    sacDecoCcr: parseFloat(document.getElementById('ccrSacDeco')?.value) || 25,
    stressTimeMin: parseFloat(document.getElementById('ccrStressTime')?.value) || 10,
    problemSolveMin: parseFloat(document.getElementById('ccrProblemSolve')?.value) || 3,
    diluentUseAsBailout: document.getElementById('diluentUseAsBailout')?.value === 'on',
  };
}

function mergeCCRSettings(settings) {
  const s = settings || {};
  const hasSnap = s.circuit != null && s.circuit !== '';
  const dom = hasSnap ? {} : (typeof document !== 'undefined' ? getCCRSettingsFromDOM() : {});
  const raw = {
    circuit: s.circuit || dom.circuit || 'OC',
    setpoint: s.setpoint != null ? s.setpoint : (s.decoSetpoint != null ? s.decoSetpoint : dom.setpoint),
    decoSetpoint: s.decoSetpoint != null ? s.decoSetpoint : (s.setpoint != null ? s.setpoint : dom.decoSetpoint),
    bottomSetpoint: s.bottomSetpoint != null ? s.bottomSetpoint : dom.bottomSetpoint,
    descentSetpoint: s.descentSetpoint != null ? s.descentSetpoint : dom.descentSetpoint,
    bailout: s.bailout != null ? s.bailout : dom.bailout,
    bailoutGfLow: s.bailoutGfLow != null ? s.bailoutGfLow : dom.bailoutGfLow,
    bailoutGfHigh: s.bailoutGfHigh != null ? s.bailoutGfHigh : dom.bailoutGfHigh,
    scrLoopVolume: s.scrLoopVolume != null ? s.scrLoopVolume : dom.scrLoopVolume,
    scrMetabolicO2: s.scrMetabolicO2 != null ? s.scrMetabolicO2 : dom.scrMetabolicO2,
    sacStress: s.sacStress != null ? s.sacStress : dom.sacStress,
    sacDecoCcr: s.sacDecoCcr != null ? s.sacDecoCcr : dom.sacDecoCcr,
    stressTimeMin: s.stressTimeMin != null ? s.stressTimeMin : dom.stressTimeMin,
    problemSolveMin: s.problemSolveMin != null ? s.problemSolveMin : dom.problemSolveMin,
    ccrPhase: s.ccrPhase || dom.ccrPhase || null,
    scrRuntimeMin: s.scrRuntimeMin || 0,
    diluentUseAsBailout: s.diluentUseAsBailout != null ? s.diluentUseAsBailout : dom.diluentUseAsBailout,
  };
  if (window.ZhlEngineBundle && ZhlEngineBundle.normalizeCCRSettings) {
    const norm = ZhlEngineBundle.normalizeCCRSettings(raw);
    if (raw.diluentUseAsBailout != null) norm.diluentUseAsBailout = raw.diluentUseAsBailout;
    return norm;
  }
  return raw;
}

// AUDIT-UNIT:UI-CCR-DELEGATES
function canonicalCircuit(circuit) { _syncZhlBundleEnv(); return ZhlEngineBundle.canonicalCircuit(circuit); }
function isRebreatherCircuit(circuit) { _syncZhlBundleEnv(); return ZhlEngineBundle.isRebreatherCircuit(circuit); }
function depthAtSetpointCrossing(setpoint, surfP) { _syncZhlBundleEnv(); return ZhlEngineBundle.depthAtSetpointCrossing(setpoint, surfP); }
function getEffectiveSetpointAtDepth(depthM, ccr, surfP, phase) { _syncZhlBundleEnv(); return ZhlEngineBundle.getEffectiveSetpointAtDepth(depthM, mergeCCRSettings(ccr), surfP, phase); }
function getCcrMetabolicO2Rate(ccr) { _syncZhlBundleEnv(); return ZhlEngineBundle.getCcrMetabolicO2Rate(mergeCCRSettings(ccr)); }
function computePSCRFractions(pAmb, fO2, fHe, ccr) { _syncZhlBundleEnv(); return ZhlEngineBundle.computePSCRFractions(pAmb, fO2, fHe, mergeCCRSettings(ccr)); }
function ccrLoopGasBelowSetpoint(pAmb, fO2, fHe, setpoint) { _syncZhlBundleEnv(); return ZhlEngineBundle.ccrLoopGasBelowSetpoint(pAmb, fO2, fHe, setpoint); }
function getInspiredInertPressures(pAmb, setpoint, fO2, fHe, ccr) { _syncZhlBundleEnv(); return ZhlEngineBundle.getInspiredInertPressures(pAmb, setpoint, fO2, fHe, mergeCCRSettings(ccr)); }
function getCCRInertSchreinerParams(pAmbStart, setpoint, fO2, fHe, pressureRate, ccr) { _syncZhlBundleEnv(); return ZhlEngineBundle.getCCRInertSchreinerParams(pAmbStart, setpoint, fO2, fHe, pressureRate, mergeCCRSettings(ccr)); }
function getSetpointBoundaryDepths(ccr, surfP) { _syncZhlBundleEnv(); return ZhlEngineBundle.getSetpointBoundaryDepths(mergeCCRSettings(ccr), surfP); }
function splitLinearDepthAtBoundaries(fromDepth, toDepth, boundaryDepths) { _syncZhlBundleEnv(); return ZhlEngineBundle.splitLinearDepthAtBoundaries(fromDepth, toDepth, boundaryDepths); }
function splitSegmentAtSetpoint(fromDepth, toDepth, setpoint, surfP) { _syncZhlBundleEnv(); return ZhlEngineBundle.splitSegmentAtSetpoint(fromDepth, toDepth, setpoint, surfP); }
function getEffectivePpo2(pAmb, setpoint, fO2, ccr, depthM, fHe) { _syncZhlBundleEnv(); return ZhlEngineBundle.getEffectivePpo2(pAmb, setpoint, fO2, mergeCCRSettings(ccr), depthM, fHe); }
function schreinerLinearCCR(p0, ht, t, p0Amb, R, setpoint, fO2, fHe, ccr, isHe) { _syncZhlBundleEnv(); return ZhlEngineBundle.schreinerLinearCCR(p0, ht, t, p0Amb, R, setpoint, fO2, fHe, mergeCCRSettings(ccr), isHe); }
function saturateLinearCCR(tissues, fromDepth, toDepth, t, fO2, fHe, ccr) { _syncZhlBundleEnv(); return ZhlEngineBundle.saturateLinearCCR(tissues, fromDepth, toDepth, t, fO2, fHe, mergeCCRSettings(ccr)); }
function saturateCCR(tissues, depthM, t, fO2, fHe, ccr) { _syncZhlBundleEnv(); return ZhlEngineBundle.saturateCCR(tissues, depthM, t, fO2, fHe, mergeCCRSettings(ccr)); }
function loadTissuesWithCCR(tissues, fromDepth, toDepth, time, fO2, fHe, ccr, constantDepth) { _syncZhlBundleEnv(); return ZhlEngineBundle.loadTissuesWithCCR(tissues, fromDepth, toDepth, time, fO2, fHe, mergeCCRSettings(ccr), constantDepth); }

function gfAdjustedMValue(a, b, pAmb, gf) {
  return a * gf + pAmb * (1 - gf + gf / b);
}

function isCcrOnLoopGasLabel(label) {
  if (typeof label !== 'string') return false;
  const u = label.toUpperCase();
  return u.startsWith('CCR ') || u.startsWith('PSCR ');
}
function ccrDiluentSurfaceLpm(depthM) {
  const ccr = getCCRSettingsFromDOM();
  const metRate = getCcrMetabolicO2Rate(ccr);
  const bot = getBottomGasFractions();
  if (!bot) return NaN;
  const fO2Dil = Math.max(0.01, bot.fO2 || 0.21);
  if (ccr.circuit === 'pSCR' && !ccr.bailout) {
    const pAmb = altSurfaceP + (depthM || 0) * BAR_PER_METRE;
    const pSurf = altSurfaceP || 1.01325;
    const fr = computePSCRFractions(pAmb, fO2Dil, bot.fHe || 0, ccr);
    const delta = Math.max(PSCR_DILUENT_EPSILON, fO2Dil - fr.fO2);
    const flowAtDepth = metRate / delta;
    return flowAtDepth * (pSurf / pAmb);
  }
  return metRate / fO2Dil;
}
function isCcrDiluentGasLabel(label) {
  if (!label) return false;
  if (isCcrOnLoopGasLabel(label)) return true;
  const ccr = getCCRSettingsFromDOM();
  if (!isRebreatherCircuit(ccr.circuit) || ccr.bailout) return false;
  const bot = getBottomGasFractions();
  if (!bot) return false;
  const norm = s => String(s).trim().replace(/^(CCR|PSCR)\s+/i, '').toUpperCase();
  const a = norm(label);
  const b = norm(getGasLabel(bot.fO2, bot.fHe));
  if (a === b) return true;
  if (a === 'AIR' && b === '21/00') return true;
  if ((a === '100%' || a === '100') && b.startsWith('100')) return true;
  return false;
}
function isCcrOnLoopProfile(ccr) {
  const cfg = ccr || getCCRSettingsFromDOM();
  return isRebreatherCircuit(cfg.circuit) && !cfg.bailout;
}
/** Display label for on-loop rebreather gas (CCR Air / pSCR Air). OC/bailout → diluent unchanged. */
function loopMixLabelFor(diluentLabel, ccr) {
  const cfg = ccr || getCCRSettingsFromDOM();
  if (!isRebreatherCircuit(cfg.circuit) || cfg.bailout) return diluentLabel;
  if (typeof diluentLabel === 'string' && /^(CCR|pSCR)\s/i.test(diluentLabel)) return diluentLabel;
  const prefix = cfg.circuit === 'pSCR' ? 'pSCR' : 'CCR';
  return `${prefix} ${diluentLabel}`;
}
/** Read SAC from DOM; always returns L/min (converts cu ft/min when units === 'imperial'). */
function sacDomToLpm(inputId, defaultLpm) {
  const raw = parseFloat(document.getElementById(inputId)?.value);
  if (!Number.isFinite(raw)) return defaultLpm;
  if (raw <= 0) return 0;
  return units === 'imperial' ? raw / CUFT_PER_LITRE : raw;
}
function ccrGasLitres(label, depthM, durMin, sac) {
  if (isCcrDiluentGasLabel(label)) {
    const pAmb = altSurfaceP + depthM * BAR_PER_METRE;
    const pSurf = altSurfaceP || 1.01325;
    const surfLpm = ccrDiluentSurfaceLpm(depthM);
    if (!Number.isFinite(surfLpm)) return NaN;
    return surfLpm * (pAmb / pSurf) * durMin;
  }
  const absP = altSurfaceP + depthM * BAR_PER_METRE;
  return sac * absP * durMin; // sac must be L/min → litres at ambient
}
function accumGasLitres(acc, label, litres) {
  if (!Number.isFinite(litres)) { acc[label] = NaN; return; }
  const prev = acc[label];
  if (prev === undefined || prev === null) { acc[label] = litres; return; }
  acc[label] = Number.isFinite(prev) ? prev + litres : NaN;
}

function setCircuitMode(mode, btn) {
  const sel = document.getElementById('circuitSelect');
  if (sel) sel.value = mode;
  document.querySelectorAll('#circuitBtnGroup .circ-btn').forEach(b => {
    b.classList.toggle('active', b === btn || b.getAttribute('data-circuit') === mode);
  });
  toggleCircuitFields();
  if (window._lastContingency) calcContingency();
  calcCNS();
  appSettings?.save?.(false);
}

function _syncCircuitBtns() {
  const mode = document.getElementById('circuitSelect')?.value || 'OC';
  document.querySelectorAll('#circuitBtnGroup .circ-btn').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-circuit') === mode);
  });
}

function toggleCircuitFields() {
  const circuit = document.getElementById('circuitSelect')?.value || 'OC';
  const isRB = circuit !== 'OC';
  const isCCR = circuit === 'CCR';
  const isPSCR = circuit === 'pSCR';
  const advSec = document.getElementById('ccrAdvSettingsSection');
  if (advSec) advSec.style.display = isRB ? '' : 'none';
  const ccrGrp = document.getElementById('ccrSettingsGroup');
  if (ccrGrp) ccrGrp.style.display = isRB ? '' : 'none';
  const boGrp = document.getElementById('ccrBailoutSettingsGroup');
  const bailoutOn = document.getElementById('ccrBailoutToggle')?.value === 'on';
  if (boGrp) boGrp.style.display = (isRB && bailoutOn) ? '' : 'none';
  ['ccrSpDescentRow', 'ccrSpBottomRow', 'ccrSpDecoRow'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = isCCR ? '' : 'none';
  });
  const bailoutEl = document.getElementById('ccrBailoutRow');
  if (bailoutEl) bailoutEl.style.display = isRB ? '' : 'none';
  if (isRB) _updateCcrAdvSummary();
  updateCcrGasCardLabels();
  updateCcrGasValidation();
}

function isCcrGasUiMode() {
  const c = document.getElementById('circuitSelect')?.value || 'OC';
  return c === 'CCR' || c === 'pSCR';
}

function updateCcrGasCardLabels() {
  const ccrUi = isCcrGasUiMode();
  const isCCR = (document.getElementById('circuitSelect')?.value || 'OC') === 'CCR';
  const titleEl = document.getElementById('diluentCardTitle');
  if (titleEl) {
    titleEl.textContent = ccrUi ? 'DILUENT' : 'GAS MIX 1 — BOTTOM GAS';
  }
  const dilBailoutRow = document.getElementById('diluentUseAsBailoutRow');
  if (dilBailoutRow) dilBailoutRow.style.display = isCCR ? '' : 'none';
  const mixLbl = document.getElementById('diluentMixLabel');
  if (mixLbl) mixLbl.textContent = ccrUi ? 'Diluent mix' : 'Gas Mix';
  const travelBtn = document.getElementById('addTravelGasBtn');
  const travelCard = document.getElementById('travelGasCard');
  if (ccrUi) {
    if (travelBtn) travelBtn.style.display = 'none';
    if (travelCard) travelCard.style.display = 'none';
  } else if (travelBtn && (!travelCard || travelCard.style.display === 'none')) {
    travelBtn.style.display = '';
  }
  const addBtn = document.getElementById('addDecoGasBtn');
  if (addBtn) addBtn.textContent = ccrUi ? '+ ADD BAILOUT MIX' : '+ ADD GAS MIX';
  const gpBotTitle = document.getElementById('gpBotRowTitle');
  if (gpBotTitle) {
    gpBotTitle.textContent = ccrUi ? '🔵 DILUENT CYLINDER' : '🔵 BOTTOM GAS CYLINDER';
  }
  renumberDecoGasCards();
}

function calcGasMODm(fO2, ppO2Limit) {
  const o2AtMOD = typeof allowO2AtMOD !== 'undefined' ? allowO2AtMOD : true;
  const lastStop = parseInt(document.getElementById('lastDecoStop')?.value, 10) || 3;
  const o2MODm = Math.max(lastStop, 6);
  if (fO2 <= 0) return 0;
  if (fO2 >= 0.995) {
    if (o2AtMOD) return o2MODm;
    const strictM = Math.max(0, Math.floor((ppO2Limit / fO2 - altSurfaceP) / BAR_PER_METRE));
    return Math.max(o2MODm, strictM);
  }
  return Math.max(0, Math.floor((ppO2Limit / fO2 - altSurfaceP) / BAR_PER_METRE));
}

function getBailoutPpo2Limit() {
  return parseFloat(document.getElementById('ppo2Bottom')?.value) || 1.4;
}

function getConfiguredBailoutMixes() {
  const ocPpo2 = getBailoutPpo2Limit();
  const mixes = [];
  const ids = getAllDecoGasIds();
  ids.forEach(cidx => {
    const sel = document.getElementById(`dg${cidx}Mix`);
    if (!sel || sel.value === 'none' || !sel.value) return;
    const fracs = getDecoCardFractions(cidx);
    if (!fracs) return;
    mixes.push({
      cidx,
      label: getGasLabel(fracs.fO2, fracs.fHe),
      fO2: fracs.fO2,
      modM: calcGasMODm(fracs.fO2, ocPpo2),
    });
  });
  return mixes;
}

/** Richest breathable bailout mix for stress/problem-solve reserve at depth. */
function getBailoutReserveMixLabel(depthM, fO2Bot, fHeBot) {
  const mixes = getConfiguredBailoutMixes();
  const atDepth = mixes.filter(m => m.modM >= depthM - 0.01);
  if (atDepth.length) {
    return atDepth.reduce((best, m) => (!best || m.modM < best.modM) ? m : best).label;
  }
  const useDil = document.getElementById('diluentUseAsBailout')?.value === 'on';
  if (useDil) {
    const bailoutPpo2 = getBailoutPpo2Limit();
    if (calcGasMODm(fO2Bot, bailoutPpo2) >= depthM - 0.01) {
      return getGasLabel(fO2Bot, fHeBot);
    }
  }
  return null;
}

/** Split stress/problem-solve reserve across bottom + deco stop depths with phase-appropriate bailout mix (BUG-70). */
function addBailoutStressReserve(addGasFn, reserveMin, bottomDepthM, stopDepthsM, fO2Bot, fHeBot, sacStress) {
  if (!reserveMin || reserveMin <= 0) return;
  const seen = new Set();
  const depths = [];
  [bottomDepthM, ...(stopDepthsM || [])].forEach(d => {
    if (d == null || d < 0) return;
    const key = Math.round(d * 100);
    if (seen.has(key)) return;
    seen.add(key);
    depths.push(d);
  });
  if (!depths.length) return;
  const shareMin = reserveMin / depths.length;
  depths.forEach(d => {
    const label = getBailoutReserveMixLabel(d, fO2Bot, fHeBot);
    if (label) addGasFn(label, d, shareMin, sacStress);
  });
}

function validateCcrGasConfiguration() {
  if (!isCcrGasUiMode()) return { ok: true, errors: [], warnings: [] };
  const rawD = parseFloat(getPlannerInputEl('decoDepth')?.value) || 0;
  const depthM = units === 'metric' ? rawD : rawD / 3.28084;
  if (depthM <= 0) return { ok: true, errors: [], warnings: [] };
  const circuit = document.getElementById('circuitSelect')?.value || 'OC';
  const activePpo2 = circuit === 'pSCR'
    ? getBailoutPpo2Limit()
    : (parseFloat(document.getElementById('ccrBottomSetpoint')?.value)
       || parseFloat(document.getElementById('ppo2Bottom')?.value) || 1.4);
  const bot = getBottomGasFractions();
  const du = units === 'imperial' ? 'ft' : 'm';
  const depthDisp = units === 'imperial' ? Math.round(depthM * 3.28084) : Math.round(depthM);
  const errors = [];
  const warnings = [];
  const gasFrac = validateDomDecoGases();
  if (!gasFrac.ok) {
    gasFrac.errors.forEach(e => errors.push(e.message || String(e)));
  }
  if (!bot) {
    errors.push('Invalid bottom gas configuration.');
  } else {
    const diluentMod = calcGasMODm(bot.fO2, activePpo2);
    const modDisp = units === 'imperial' ? Math.round(diluentMod * 3.28084) : diluentMod;
    if (depthM > diluentMod + 0.01) {
      errors.push(`Diluent MOD (${modDisp}${du}) is shallower than dive depth (${depthDisp}${du}). Use a leaner diluent or reduce depth.`);
    }
    const useDiluentBailout = document.getElementById('diluentUseAsBailout')?.value === 'on';
    const bailoutMixes = getConfiguredBailoutMixes();
    const bailoutAtDepth = bailoutMixes.filter(m => m.modM >= depthM - 0.01);
    if (useDiluentBailout && diluentMod >= depthM - 0.01) {
      // diluent cylinder counts as bailout at depth
    } else if (bailoutAtDepth.length === 0) {
      if (bailoutMixes.length === 0 && !useDiluentBailout) {
        errors.push('Add at least one bailout mix with sufficient MOD, or enable "Use diluent as bailout".');
      } else {
        errors.push(`No bailout mix with enough MOD for ${depthDisp}${du}. Add or correct bailout mixtures.`);
      }
    }
  }
  if (errors.length === 0) {
    const useDiluentBailout = document.getElementById('diluentUseAsBailout')?.value === 'on';
    const bailoutMixes = getConfiguredBailoutMixes();
    if (bailoutMixes.length === 0 && !useDiluentBailout) {
      warnings.push('No bailout mixes configured — add OC bailout cylinders for emergency open-circuit use.');
    }
  }
  return { ok: errors.length === 0, errors, warnings };
}

function updateCcrGasValidation() {
  const box = document.getElementById('ccrGasValidation');
  if (!box) return;
  if (!isCcrGasUiMode()) { box.style.display = 'none'; box.innerHTML = ''; return; }
  const v = validateCcrGasConfiguration();
  box.style.display = '';
  let html = '';
  v.errors.forEach(msg => {
    html += `<div class="alert dang" style="margin-top:0;"><span>⚠</span><div><strong>Validation error.</strong> ${msg}</div></div>`;
  });
  v.warnings.forEach(msg => {
    html += `<div class="alert" style="margin-top:6px;background:var(--card2);"><span>ℹ</span><div>${msg}</div></div>`;
  });
  if (v.ok && v.warnings.length === 0) {
    html = `<div class="alert" style="margin-top:0;background:rgba(38,208,124,0.08);border-color:var(--green);"><span>✓</span><div>Diluent and bailout MOD check passed for planned depth.</div></div>`;
  }
  box.innerHTML = html;
}

function toggleCcrAdvSettings(forceOpen) {
  const body = document.getElementById('ccrAdvSettingsBody');
  const chevron = document.getElementById('ccrAdvSettingsChevron');
  const btn = document.getElementById('ccrAdvSettingsToggle');
  if (!body) return;
  const isOpen = body.style.display !== 'none';
  const open = forceOpen !== undefined ? forceOpen : !isOpen;
  body.style.display = open ? '' : 'none';
  if (chevron) chevron.style.transform = open ? 'rotate(90deg)' : '';
  if (btn) {
    btn.style.borderColor = open ? 'var(--accent)' : 'var(--border)';
    btn.style.color = open ? 'var(--accent)' : 'var(--muted)';
  }
  _updateCcrAdvSummary();
  try { localStorage.setItem('lspCcrAdvOpen', open ? '1' : '0'); } catch(e) {}
}

function _updateCcrAdvSummary() {
  const el = document.getElementById('ccrAdvSettingsSummary');
  if (!el) return;
  const body = document.getElementById('ccrAdvSettingsBody');
  if (body && body.style.display !== 'none') { el.textContent = ''; return; }
  const circuit = document.getElementById('circuitSelect')?.value || 'OC';
  if (circuit === 'OC') { el.textContent = ''; return; }
  const parts = [];
  if (circuit === 'CCR') {
    const ds = document.getElementById('ccrDescentSetpoint')?.value;
    const bs = document.getElementById('ccrBottomSetpoint')?.value;
    const dec = document.getElementById('ccrDecoSetpoint')?.value;
    if (ds && bs && dec) parts.push(`SP ${ds}/${bs}/${dec}`);
  }
  const bo = document.getElementById('ccrBailoutToggle')?.value;
  if (bo === 'on') {
    const glo = document.getElementById('ccrBailoutGfLow')?.value || '50';
    const ghi = document.getElementById('ccrBailoutGfHigh')?.value || '85';
    parts.push(`BO GF ${glo}/${ghi}`);
  }
  el.textContent = parts.length ? parts.join(' · ') : 'defaults';
}

if (typeof window !== 'undefined') {
  window.getInspiredInertPressures = getInspiredInertPressures;
  window.getCCRSettingsFromDOM = getCCRSettingsFromDOM;
  window.mergeCCRSettings = mergeCCRSettings;
  window.getEffectiveSetpointAtDepth = getEffectiveSetpointAtDepth;
  window.getEffectivePpo2 = getEffectivePpo2;
  window.loadTissuesWithCCR = loadTissuesWithCCR;
  window.splitSegmentAtSetpoint = splitSegmentAtSetpoint;
  window.computePSCRFractions = computePSCRFractions;
  window.isCcrOnLoopProfile = isCcrOnLoopProfile;
  window.loopMixLabelFor = loopMixLabelFor;
  window.toggleCcrAdvSettings = toggleCcrAdvSettings;
  window.updateCcrGasCardLabels = updateCcrGasCardLabels;
  window.updateCcrGasValidation = updateCcrGasValidation;
  window.validateCcrGasConfiguration = validateCcrGasConfiguration;
}

// AUDIT-UNIT:UI-DECO-PHYSICS
function ceiling(tissues, gfHigh) { _syncZhlBundleEnv(); return ZhlEngineBundle.ceiling(tissues, gfHigh); }

// ── Decozone start (GF-INDEPENDENT) ──────────────────────────────────────────
// This is NOT a Bühlmann M-value/ceiling calculation. It's the purely physical
// depth where any tissue's total inert-gas tension (pN2+pHe) first exceeds the
// surrounding ambient pressure — the point where the diver becomes supersaturated
// in the loosest sense, before any conservatism (GF) is applied. Gradient factors
// move the M-value line, not the ambient line, so this value must not vary with
// GF Lo/Hi — same dive at GF30/70 and GF50/80 must report the same decozone start.
// Matches MultiDeco/DiveKit's published "decozone" definition exactly.
// Surface GF — maximum tissue loading ratio vs M-value at surface pressure.
// Formula (tl5915 / Baker): surfGF_i = (pN2+pHe - P_surf) / (a_i + P_surf/b_i)
// where P_surf = altSurfaceP (actual surface ambient — altitude-aware). Returns 0–100+ as a percentage.
// Negative values (all tissues undersaturated at surface) are clamped to 0.
function computeSurfaceGF(tissues) { _syncZhlBundleEnv(); return ZhlEngineBundle.computeSurfaceGF(tissues); }

function ambientCrossingDepth(tissues) { _syncZhlBundleEnv(); return ZhlEngineBundle.ambientCrossingDepth(tissues); }

function parseDomInt(id, fallback) {
  const raw = parseInt(document.getElementById(id)?.value, 10);
  return Number.isNaN(raw) ? fallback : raw;
}

function isShallowGradientOn() {
  return document.getElementById('shallowGradient')?.value === 'on';
}

function buhNDL(depthM, fN2, gfLow, gfHigh, fHe) {
  _syncZhlBundleEnv();
  const lastStop = parseDomInt('lastDecoStop', 3);
  const decoStep = parseDomInt('decoStep', 3);
  return ZhlEngineBundle.buhNDL(depthM, fN2, gfLow, gfHigh, fHe, lastStop, decoStep, isShallowGradientOn());
}

function maxSatPct(tissues, gfHigh) {
  let max = 0;
  tissues.forEach((t0, i) => {
    const pN2 = t0.pN2;
    const pHe = t0.pHe || 0;
    const pTotal = pN2 + pHe;
    let a, b;
    if (pHe > 0 && pTotal > 0) {
      a = (pN2 * ZHL16C[i][1] + pHe * ZHL16C_HE_AB[i][0]) / pTotal;
      b = (pN2 * ZHL16C[i][2] + pHe * ZHL16C_HE_AB[i][1]) / pTotal;
    } else {
      [, a, b] = ZHL16C[i];
    }
    const mv = gfAdjustedMValue(a, b, altSurfaceP, gfHigh / 100);
    const pct = Math.round((pTotal / mv) * 100);
    if (pct > max) max = pct;
  });
  return max;
}

// ═══════════════════════════════════════════════
// PLANNER
// ═══════════════════════════════════════════════
function runPlanner() {
  if (!guardEngineBootForCalculate()) return;
  if (!window._zhlHeadless) {
    const inputVal = validatePlannerInputs();
    if (!inputVal.ok) {
      alert('Cannot calculate dive:\n\n' + inputVal.msg);
      return;
    }
  }
  const isMetric = units === 'metric';
  const rawD = parseFloat(document.getElementById('recDepth')?.value)||30;
  const depthM = isMetric ? rawD : rawD/3.28084;
  const bt  = parseInt(document.getElementById('recBT')?.value)||25;
  const gfL = mGF.low;
  const gfH = mGF.high;
  const mix = getPersistedGasMix();
  const modPpo2 = parseFloat(document.getElementById('ppo2Bottom')?.value) || 1.4;
  const fN2 = getN2Frac(mix);
  if (fN2 == null) {
    if (!window._zhlHeadless) alert('Invalid gas mix — check O₂ and He percentages.');
    return;
  }
  const fHe = getHeFrac(mix);
  const dDisp = isMetric ? rawD+' m' : rawD+' ft';
  const stopFt = stopDepthM === 3 ? 10 : 20;

  let html = '';
  let summarySurfGF = '—';

  if (algo === 'padi') {
    const fO2 = PadiEngine.recMixFO2(mix);
    const isNitrox = mix !== 'air';
    const gasLabel = mix === 'ean32' ? '32/00' : mix === 'ean36' ? '36/00' : 'Air';
    const pO2  = parseFloat((depthBar(depthM) * fO2).toFixed(2));
    const ndl = padiNDL(depthM, mix);
    const rem = ndl > 0 ? Math.max(0, ndl - bt) : 0;
    const group = padiGroup(depthM, bt, mix);
    const pct = ndl > 0 ? Math.min(100, Math.round((bt / ndl) * 100)) : 100;
    summarySurfGF = `${pct}%`;
    const bc  = pct>=100?'var(--red)':pct>=80?'var(--orange)':pct>=65?'var(--yellow)':'var(--green)';
    const modM = nitroxMOD(fO2, modPpo2);
    const modFt = modM !== null ? Math.floor(modM * 3.28084) : null;
    const beyondMOD = depthM > modM;
    const ppO2Ok = pO2 <= modPpo2;
    const btOk = ndl > 0 && bt <= ndl && !beyondMOD;

    const gasStatHtml = `<div class="stat"><div class="stat-val ${ppO2Ok?'g':'r'}">${pO2.toFixed(2)}</div><div class="stat-lbl">ppO₂ (bar)</div></div>`;
    const modInfoHtml = `<div class="alert info" style="margin-top:12px;"><span>💡</span><div>MOD for ${gasLabel} @ ${modPpo2.toFixed(1)} bar ppO₂: <strong>${isMetric ? modM+' m' : modFt+' ft'}</strong></div></div>`;
    const tableRef = isNitrox ? `PADI Nitrox ${gasLabel}` : 'PADI Air';

    html = `<div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <div class="card-title" style="margin:0;">Rec Results · ${dDisp} / ${bt} min · ${gasLabel}</div>
        <div class="export-row">
          <button class="btn-export" onclick="copyDiveProfile('planner')" title="Copy to clipboard"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg></button>
          <button class="btn-export" onclick="exportTXT('planner')" title="Download .txt"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/></svg></button>
        </div>
      </div>
      <div class="stats" style="grid-template-columns:repeat(4,1fr);margin-top:4px;margin-bottom:4px;">
        <div class="stat"><div class="stat-val ${btOk?'g':'r'}">${bt}</div><div class="stat-lbl">Your BT</div></div>
        <div class="stat"><div class="stat-val ${rem===0?'r':rem<10?'o':'g'}">${rem}</div><div class="stat-lbl">Remaining</div></div>
        <div class="stat"><div class="stat-val" style="font-size:22px;"><span class="group-badge">${group}</span></div><div class="stat-lbl">Press. Group (est.)</div></div>
        ${gasStatHtml}
      </div>
      <div style="margin-top:14px;">
        <div style="display:flex;justify-content:space-between;font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--muted);margin-bottom:5px;letter-spacing:1px;"><span>NDL USAGE · ${tableRef}</span><span>${pct}%</span></div>
        <div class="bar-wrap"><div class="bar-fill" style="width:${pct}%;background:${bc};"></div></div>
      </div>
      ${beyondMOD ? `<div class="alert dang" style="margin-top:12px;"><span>⚠</span><div><strong>BEYOND MOD.</strong> ${dDisp} exceeds ${gasLabel} MOD of ${isMetric ? modM+' m' : modFt+' ft'} at ${modPpo2.toFixed(1)} bar ppO₂. CNS oxygen toxicity risk — use a lower O₂ mix or reduce depth.</div></div>` : ''}
      ${!beyondMOD && ndl === 0 ? `<div class="alert dang" style="margin-top:12px;"><span>⚠</span><div><strong>BEYOND TABLE.</strong> ${dDisp} exceeds the PADI recreational table maximum (${isMetric ? PADI_TABLE_MAX_M+' m' : PADI_TABLE_MAX_FT+' ft'}).</div></div>` : ''}
      ${!beyondMOD && ndl > 0 && !btOk ? '<div class="alert" style="margin-top:12px;background:#FF4433;border-color:#cc2200;color:#fff;font-weight:700;"><span>⚠</span><div><strong>NDL EXCEEDED.</strong> Not permitted for recreational diving. Reduce bottom time.</div></div>' : ''}
      ${!beyondMOD && btOk && pct>=80 ? '<div class="alert" style="margin-top:12px;background:#ffff00;border-color:#cccc00;color:#111;font-weight:700;"><span>⚡</span><div><strong>APPROACHING LIMIT.</strong> 80%+ NDL used. Monitor closely and ascend conservatively.</div></div>' : ''}
      ${!beyondMOD && btOk && pct<80 ? '<div class="alert ok" style="margin-top:12px;"><span>✓</span><div><strong>WITHIN LIMITS.</strong> '+rem+' minutes remaining. Good safety margin.</div></div>' : ''}
      ${modInfoHtml}
      ${safetyStopHTML(stopDepthM, stopFt, stopDurMin)}
    </div>`;

  } else {
    // Bühlmann — BT includes descent; saturate linearly on descent, then hold at depth
    let tissues = initTissues();
    const descentRate = Math.max(1, parseInt(document.getElementById('descentRate')?.value, 10) || 20);
    const descentTime = depthM / descentRate;
    const btAtDepth = Math.max(0, bt - descentTime);
    if (descentTime > 0 && depthM > 0) {
      tissues = saturateLinear(tissues, 0, depthM, descentTime, fN2, fHe);
    }
    tissues = saturate(tissues, depthM, btAtDepth, fN2, fHe);
    lastTissues = tissues;
    const gfHF = gfH/100;
    const ndl = buhNDL(depthM, fN2, gfL, gfH, fHe);
    const ceil = ceiling(tissues, gfHF);
    const sat  = maxSatPct(tissues, gfH);
    const rem  = Math.max(0, ndl-bt);
    const pct  = Math.min(100, Math.round((bt/ndl)*100));
    summarySurfGF = `${pct}%`;
    const bc   = pct>=100?'var(--red)':pct>=85?'var(--orange)':pct>=70?'var(--yellow)':'var(--green)';
    const btOk = bt <= ndl && ceil <= 0;
    const fO2  = Math.max(0, 1 - fN2 - fHe);
    const pO2  = parseFloat((depthBar(depthM) * fO2).toFixed(2));

    updateTissueViz(tissues, gfH);

    html = `<div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <div class="card-title" style="margin:0;">Bühlmann · ${dDisp} / ${bt} min · GF ${gfL}/${gfH}</div>
        <div class="export-row">
          <button class="btn-export" onclick="copyDiveProfile('planner')" title="Copy to clipboard"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg></button>
          <button class="btn-export" onclick="exportTXT('planner')" title="Download .txt"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/></svg></button>
        </div>
      </div>
      <div class="stats" style="grid-template-columns:repeat(5,1fr);margin-top:4px;margin-bottom:4px;">
        <div class="stat"><div class="stat-val ${btOk?'g':'r'}">${bt}</div><div class="stat-lbl">Your BT</div></div>
        <div class="stat"><div class="stat-val ${rem===0?'r':rem<10?'o':'g'}">${rem}</div><div class="stat-lbl">Remaining</div></div>
        <div class="stat"><div class="stat-val ${ceil>0?'r':'g'}">${ceil>0?Math.ceil(ceil)+' m':'0 m'}</div><div class="stat-lbl">Deco Ceil</div></div>
        <div class="stat"><div class="stat-val ${sat>=100?'r':sat>=85?'o':sat>=70?'y':'g'}">${sat}%</div><div class="stat-lbl">Max Sat</div></div>
        <div class="stat"><div class="stat-val ${pO2>modPpo2?'r':'g'}">${pO2.toFixed(1)}</div><div class="stat-lbl">ppO₂</div></div>
      </div>
      <div style="margin-top:14px;">
        <div style="display:flex;justify-content:space-between;font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--muted);margin-bottom:5px;letter-spacing:1px;"><span>NDL USAGE</span><span>${pct}%</span></div>
        <div class="bar-wrap"><div class="bar-fill" style="width:${pct}%;background:${bc};"></div></div>
      </div>
      ${ceil>0 ? '<div class="alert deco" style="margin-top:12px;"><span>⚠</span><div><strong>DECOMPRESSION REQUIRED.</strong> Deco ceiling at '+Math.ceil(ceil)+' m. See Deco Schedule tab for full profile.</div></div>' : ''}
      ${!btOk && ceil<=0 ? '<div class="alert" style="margin-top:12px;background:#FF4433;border-color:#cc2200;color:#fff;font-weight:700;"><span>⚠</span><div><strong>NDL EXCEEDED.</strong> Reduce bottom time by '+(bt-ndl)+' min.</div></div>' : ''}
      ${btOk ? '<div class="alert ok" style="margin-top:12px;"><span>✓</span><div><strong>WITHIN NDL.</strong> GF '+gfL+'/'+gfH+'. '+rem+' minutes remaining.</div></div>' : ''}
      ${pO2>modPpo2 ? `<div class="alert dang"><span>⚠</span><div><strong>ppO₂ EXCEEDS ${modPpo2.toFixed(1)} bar.</strong> CNS oxygen toxicity risk. Use lower O₂ mix or reduce depth.</div></div>` : ''}
      <div style="margin-top:8px;"><div class="alert info" style="margin-bottom:0;"><span>💡</span><div>Tissue saturation chart updated — see <strong>Tissue Sat.</strong> tab.</div></div></div>
      ${safetyStopHTML(stopDepthM, stopFt, stopDurMin)}
    </div>`;
  }

  document.getElementById('plannerResult').innerHTML = html;
  document.getElementById('plannerResult').style.display = 'block';
  setTimeout(drawPlannerProfile, 30);

  const stopDisp = isMetric ? `${stopDepthM}m` : `${stopFt}ft`;
  _renderResultSummaryStrip({
    runTime: String(bt),
    decoTime: '0',
    cns: '—',
    firstStop: stopDisp,
    surfaceGF: summarySurfGF,
    otu: '—',
    tts: '—',
    decozone: '—',
  });
  _onPlanResultsReady();

  // Surface Interval panel (collapsed) — pre-fill Dive 1 from this dive
  renderSurfIntPanel('recSurfIntContainer', 'recSi', depthM, bt);
}

function safetyStopHTML(depthM, depthFt, dur) {
  const isMetric = units === 'metric';
  const depthDisp = isMetric ? `${depthM} m` : `${depthFt} ft`;
  const rateDisp = isMetric ? '9 m/min' : '30 ft/min';
  const desc = depthM === 3
    ? `${depthDisp} standard safety stop. Ascend at max ${rateDisp} and hold for ${dur} min.`
    : depthM === 6
      ? `${depthDisp} deep stop: recommended for dives below 30 m. Follow with a standard 3 m stop before surfacing.`
      : `${depthDisp} safety stop. Ascend at max ${rateDisp} and hold for ${dur} min.`;
  return `<div style="background:rgba(38,208,124,0.06);border:1px solid rgba(38,208,124,0.2);border-radius:10px;padding:14px;margin-top:14px;">
    <div style="font-family:'Bebas Neue',sans-serif;font-size:13px;letter-spacing:3px;color:var(--green);margin-bottom:10px;">SAFETY STOP</div>
    <div class="stats" style="margin-top:0;">
      <div class="stat" style="padding:10px;"><div class="stat-val g" style="font-size:22px;">${depthDisp}</div><div class="stat-lbl">Safety Stop Depth</div></div>
      <div class="stat" style="padding:10px;"><div class="stat-val g" style="font-size:22px;">${dur}</div><div class="stat-lbl">Duration (min)</div></div>
      <div class="stat" style="padding:10px;"><div class="stat-val g" style="font-size:22px;">${rateDisp}</div><div class="stat-lbl">Max Ascent</div></div>
    </div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--muted);margin-top:10px;line-height:1.5;">${desc}</div>
  </div>`;
}

// ═══════════════════════════════════════════════
// NDL TABLE
// ═══════════════════════════════════════════════
// AUDIT-UNIT:UI-SCHEDULE-INPUTS
function renderNDLTable() {
  if (window._zhlHeadless) return; // skip during headless test execution
  const isM  = ndlUnits === 'metric';
  const ranges = { shallow:[0,1], moderate:[2,3], deeper:[4,6], deep:[7,10] };
  const sel = document.getElementById('ndlRange').value;
  const [from, to] = ranges[sel];
  const depths = isM ? PADI_DEPTHS_M.slice(from, to+1) : PADI_DEPTHS_FT.slice(from, to+1);
  const ndls   = PADI_NDL_M.slice(from, to+1);
  const isBuh  = algo === 'buh';
  const tbody  = document.getElementById('ndlBody');
  tbody.innerHTML = '';

  const modPpo2Ndl = parseFloat(document.getElementById('ppo2Bottom')?.value) || 1.4;
  const mod32 = nitroxMOD(0.32, modPpo2Ndl);
  const mod36 = nitroxMOD(0.36, modPpo2Ndl);

  depths.forEach((d, i) => {
    const depthM = isM ? d : d/3.28084;
    let ndl = ndls[i];
    let buhNDLVal = '';
    if (isBuh) {
      const fN2 = FN2_AIR;
      buhNDLVal = buhNDL(depthM, fN2, mGF.low, mGF.high);
    }
    const dUnit = isM ? ' m' : ' ft';
    const isDeep = depthM > 30;
    const isCaution = depthM > 21 && depthM <= 30;
    let rowClass = isDeep ? 'danger-row' : isCaution ? 'warn-row' : '';
    let ndlClass = isDeep ? 'td-r' : isCaution ? 'td-o' : 'td-g';
    const groupIdx = Math.min(PADI_GROUPS.length-1, Math.floor(i * PADI_GROUPS.length / depths.length));
    const group = PADI_GROUPS[groupIdx];

    const beyondMOD32 = depthM > mod32;
    const beyondMOD36 = depthM > mod36;

    // EAN32 NDL cell
    const idx2 = PADI_DEPTHS_M.indexOf(PADI_DEPTHS_M.reduce((a,v)=>Math.abs(v-depthM)<Math.abs(a-depthM)?v:a));
    const ndl32 = beyondMOD32 ? `<span style="color:var(--red);font-weight:700;" title="Beyond MOD (${isM?mod32+' m':Math.floor(mod32*3.28084)+' ft'})">—</span>` : `<span style="color:var(--green);">${NITROX_NDL_EAN32[idx2]} min</span>`;
    const ndl36 = beyondMOD36 ? `<span style="color:var(--red);font-weight:700;" title="Beyond MOD (${isM?mod36+' m':Math.floor(mod36*3.28084)+' ft'})">—</span>` : `<span style="color:var(--accent);">${NITROX_NDL_EAN36[idx2]} min</span>`;

    const ndlDisplay = isBuh
      ? `${buhNDLVal>=500?'500+':buhNDLVal} min <span style="color:var(--muted);font-size:10px;">(Air: ${ndl}) GF ${mGF.low}/${mGF.high}</span>`
      : `${ndl} min`;

    tbody.innerHTML += `<tr class="${rowClass}">
      <td><strong>${d}${dUnit}</strong></td>
      <td class="${ndlClass}">${ndlDisplay}</td>
      <td>${isBuh ? '—' : ndl32}</td>
      <td>${isBuh ? '—' : ndl36}</td>
      <td>${isBuh ? '—' : `<span class="group-badge">${group}</span>`}</td>
      <td style="color:var(--muted);">60+ min recommended</td>
    </tr>`;
  });
}

// ═══════════════════════════════════════════════
// TISSUE VIZ (Bühlmann)
// ═══════════════════════════════════════════════
function lspSatColors(pct) {
  const p = Math.round(pct);
  if (p >= 80) return { bar: 'var(--status-red)', text: 'var(--status-red)', status: p >= 100 ? 'LIMIT' : 'HIGH', level: 'warn' };
  if (p >= 50) return { bar: 'var(--status-orange)', text: 'var(--status-orange)', status: 'LOADED', level: 'caution' };
  return { bar: 'var(--status-green)', text: 'var(--status-green)', status: 'OK', level: 'safe' };
}
function updateTissueViz(tissues, gfH) {
  const gfF   = gfH / 100;
  const grid  = document.getElementById('tissueGrid');
  const tbody = document.getElementById('tissueTableBody');
  if (!grid) return;
  grid.innerHTML = '';
  if (tbody) tbody.innerHTML = '';

  tissues.forEach((t0, i) => {
    const pN2 = t0.pN2;
    const pHe = t0.pHe || 0;
    const pTotal = pN2 + pHe;
    const [ht, a_n2, b_n2] = ZHL16C[i];
    let a, b;
    if (pHe > 0 && pTotal > 0) {
      a = (pN2 * a_n2 + pHe * ZHL16C_HE_AB[i][0]) / pTotal;
      b = (pN2 * b_n2 + pHe * ZHL16C_HE_AB[i][1]) / pTotal;
    } else { a = a_n2; b = b_n2; }
    const mv  = gfAdjustedMValue(a, b, altSurfaceP, gfF);
    const pct = Math.min(100, Math.round((pTotal / mv) * 100));
    const sat = lspSatColors(pct);
    const col = sat.bar;
    const status = sat.status;

    // Horizontal bar row
    const row = document.createElement('div');
    row.style.cssText = 'display:flex;align-items:center;gap:8px;margin-bottom:5px;';
    row.innerHTML = `
      <span style="font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--muted);min-width:24px;text-align:right;">${i+1}</span>
      <div style="flex:1;background:var(--bg-alt);border-radius:3px;height:12px;overflow:hidden;">
        <div style="width:${pct}%;height:100%;background:${col};border-radius:3px;transition:width 0.3s;"></div>
      </div>
      <span style="font-family:'JetBrains Mono',monospace;font-size:10px;color:${col};min-width:36px;text-align:right;">${pct}%</span>`;
    grid.appendChild(row);

    if (tbody) tbody.innerHTML += `<tr class="tissue-sat-${sat.level}">
      <td>${i+1}</td><td>${ht}</td>
      <td>${pTotal.toFixed(3)}${pHe>0?' ('+pN2.toFixed(2)+'+'+pHe.toFixed(2)+')':''}</td><td>${mv.toFixed(3)}</td>
      <td class="tissue-sat-pct">${pct}%</td><td class="tissue-sat-status">${status}</td>
    </tr>`;
  });
  // Show unified tissue card
  const ttc = document.getElementById('tissueLoadCard');
  if (ttc) ttc.style.display = 'block';
  const tic = document.getElementById('tissueInlineCard');
  if (tic) tic.style.display = 'none'; // old card suppressed
}

// ═══════════════════════════════════════════════
// DECO SCHEDULE
// ═══════════════════════════════════════════════
function toggleDecoCustomO2(selectId, fieldId) {
  const selEl = document.getElementById(selectId);
  const fieldEl = document.getElementById(fieldId);
  if (!selEl || !fieldEl) return;
  const isCustom = selEl.value === 'custom';
  fieldEl.style.display = isCustom ? 'block' : 'none';
}

// Toggle trimix He/O2 fields for bottom gas card
function toggleBottomTrimix() {
  const isTrimix = document.getElementById('decoGas').value === 'trimix';
  document.getElementById('botTrimixO2Field').style.display = isTrimix ? 'block' : 'none';
  document.getElementById('botTrimixHeField').style.display = isTrimix ? 'block' : 'none';
}

// Toggle trimix fields for a deco gas card (idx = card index)
function toggleDecoTrimix(idx) {
  const val = document.getElementById(`dg${idx}Mix`)?.value;
  const isTrimix = val === 'trimix';
  const o2f = document.getElementById(`dg${idx}TrimixO2Field`);
  const hef = document.getElementById(`dg${idx}TrimixHeField`);
  if (o2f) o2f.style.display = isTrimix ? 'block' : 'none';
  if (hef) hef.style.display = isTrimix ? 'block' : 'none';
}

function toggleTravelTrimix() {
  const isTrimix = document.getElementById('travelGasMix')?.value === 'trimix';
  const o2f = document.getElementById('travelGasTrimixO2Field');
  const hef = document.getElementById('travelGasTrimixHeField');
  if (o2f) o2f.style.display = isTrimix ? 'block' : 'none';
  if (hef) hef.style.display = isTrimix ? 'block' : 'none';
}

// Read raw percent inputs from DOM without clamping (for validation only).
function readDomO2Pct(elementId) {
  const raw = document.getElementById(elementId)?.value;
  if (raw === '' || raw == null) return NaN;
  const o2 = parseFloat(raw);
  return Number.isFinite(o2) && o2 > 0 ? o2 : NaN;
}
function readDomHePct(elementId) {
  const raw = document.getElementById(elementId)?.value;
  if (raw === '' || raw == null) return NaN;
  const he = parseFloat(raw);
  return Number.isFinite(he) && he >= 0 ? he : NaN;
}

function getDomBottomGasPct() {
  const mix = document.getElementById('decoGas')?.value;
  if (mix === 'air') return { o2: 21, he: 0 };
  if (mix === 'ean32') return { o2: 32, he: 0 };
  if (mix === 'ean36') return { o2: 36, he: 0 };
  if (mix === 'custom') {
    return { o2: readDomO2Pct('decoCustomO2'), he: 0 };
  }
  if (mix === 'trimix') {
    return { o2: readDomO2Pct('botTrimixO2'), he: readDomHePct('botTrimixHe') };
  }
  return { o2: 21, he: 0 };
}

function getDomDecoGasPct(idx) {
  const mix = document.getElementById(`dg${idx}Mix`)?.value;
  if (!mix || mix === 'none') return null;
  if (mix === 'ean50') return { o2: 50, he: 0 };
  if (mix === 'ean80') return { o2: 80, he: 0 };
  if (mix === 'o2') return { o2: 100, he: 0 };
  if (mix === 'custom') {
    return { o2: readDomO2Pct(`dg${idx}CustomO2`), he: 0 };
  }
  if (mix === 'trimix') {
    return { o2: readDomO2Pct(`dg${idx}TrimixO2`), he: readDomHePct(`dg${idx}TrimixHe`) };
  }
  return null;
}

function validateDomDecoGases() {
  const errors = [];
  const circuit = document.getElementById('circuitSelect')?.value || 'OC';
  const bot = getDomBottomGasPct();
  const botCheck = validateGasFractionsPct(bot.o2, bot.he, 'bottomGas');
  if (!botCheck.ok) errors.push(botCheck);
  else {
    const botHypo = ZhlEngineBundle.validateHypoxicDecoGas(bot.o2, bot.he, 'bottomGas', circuit);
    if (botHypo) errors.push(botHypo);
    if (document.getElementById('decoGas')?.value === 'trimix' && bot.o2 > 40) {
      errors.push({ message: 'Bottom trimix O₂ must not exceed 40%.' });
    }
  }
  const seenMixes = new Map();
  for (const idx of getAllDecoGasIds()) {
    const g = getDomDecoGasPct(idx);
    if (!g) continue;
    const chk = validateGasFractionsPct(g.o2, g.he, `dg${idx}`);
    if (!chk.ok) errors.push(chk);
    else {
      const hypo = ZhlEngineBundle.validateHypoxicDecoGas(g.o2, g.he, `dg${idx}`, circuit);
      if (hypo) errors.push(hypo);
      const dgf = getDecoCardFractions(idx);
      const mixKey = dgf
        ? `${Math.round(dgf.fO2 * 1000)}|${Math.round(dgf.fHe * 1000)}`
        : `${g.o2}|${g.he}`;
      if (seenMixes.has(mixKey)) {
        errors.push({ message: `Duplicate deco gas mix: dg${idx} matches dg${seenMixes.get(mixKey)}` });
      } else {
        seenMixes.set(mixKey, idx);
      }
    }
  }
  return { ok: errors.length === 0, errors };
}
if (typeof window !== 'undefined') window.validateDomDecoGases = validateDomDecoGases;

// Get {fO2, fHe, fN2} from a gas card select+custom fields
function getDecoGasFractions(selectId, customId, trimixO2Id, trimixHeId) {
  const mix = document.getElementById(selectId)?.value;
  if (!mix || mix === 'none') return null;
  if (mix === 'ean50')  return { fO2: 0.50, fHe: 0,    fN2: 0.50 };
  if (mix === 'ean80')  return { fO2: 0.80, fHe: 0,    fN2: 0.20 };
  if (mix === 'o2')     return { fO2: 1.00, fHe: 0,    fN2: 0.00 };
  if (mix === 'custom') {
    const o2 = readDomO2Pct(customId);
    if (!Number.isFinite(o2)) return null;
    const fO2 = Math.min(1, Math.max(0.05, o2 / 100));
    return { fO2, fHe: 0, fN2: Math.max(0, 1 - fO2) };
  }
  if (mix === 'trimix') {
    const o2 = readDomO2Pct(trimixO2Id);
    const he = readDomHePct(trimixHeId);
    if (!Number.isFinite(o2) || !Number.isFinite(he)) return null;
    const fO2 = Math.min(0.99, Math.max(0.05, o2 / 100));
    const fHe = Math.min(0.95, Math.max(0, he / 100));
    if (fO2 + fHe > 1.0) return null;
    const fN2 = Math.max(0, 1 - fO2 - fHe);
    return { fO2, fHe, fN2 };
  }
  return null;
}

// Gas label format: delegate to canonical schedule-core implementation in ZhlEngineBundle
function getGasLabel(fO2, fHe) {
  _syncZhlBundleEnv();
  return ZhlEngineBundle.getGasLabel(fO2, fHe);
}

function getDecoGasFrac(selectId, customId) {
  const fracs = getDecoGasFractions(selectId, customId,
    selectId.replace('Mix', 'TrimixO2'), selectId.replace('Mix', 'TrimixHe'));
  return fracs ? fracs.fN2 : null;
}

function getDecoGasLabel(selectId, customId) {
  const fracs = getDecoGasFractions(selectId, customId,
    selectId.replace('Mix', 'TrimixO2'), selectId.replace('Mix', 'TrimixHe'));
  return fracs ? getGasLabel(fracs.fO2, fracs.fHe) : null;
}

// Full fractions for a deco gas card by card-index n
function getDecoCardFractions(n) {
  return getDecoGasFractions(
    `dg${n}Mix`, `dg${n}CustomO2`, `dg${n}TrimixO2`, `dg${n}TrimixHe`
  );
}

// Get bottom gas {fO2, fHe, fN2} from the bottom gas card UI
function getBottomGasFractions() {
  const mix = document.getElementById('decoGas')?.value;
  if (mix === 'air')    return { fO2: 0.21, fHe: 0, fN2: 0.79 };
  if (mix === 'ean32')  return { fO2: 0.32, fHe: 0, fN2: 0.68 };
  if (mix === 'ean36')  return { fO2: 0.36, fHe: 0, fN2: 0.64 };
  if (mix === 'custom') {
    const o2 = readDomO2Pct('decoCustomO2');
    if (!Number.isFinite(o2)) return null;
    const fO2 = Math.min(1.00, Math.max(0.05, o2 / 100));
    return { fO2, fHe: 0, fN2: 1 - fO2 };
  }
  if (mix === 'trimix') {
    const o2 = readDomO2Pct('botTrimixO2');
    const he = readDomHePct('botTrimixHe');
    if (!Number.isFinite(o2) || !Number.isFinite(he)) return null;
    const fO2 = Math.min(0.99, Math.max(0.05, o2 / 100));
    const fHe = Math.min(0.95, Math.max(0, he / 100));
    if (fO2 + fHe > 1.0) return null;
    return { fO2, fHe, fN2: Math.max(0, 1 - fO2 - fHe) };
  }
  return { fO2: 0.21, fHe: 0, fN2: 0.79 };
}

// Returns the best available gas at a given depth.
// "Best" = lowest fN2 (highest O₂) whose floored ppO₂ at curDepthM is within
// that gas's own ppO2 limit (determined by O2 fraction band via getPPO2Limit).
// Switch depths are exact meters so gas switches happen precisely at the right ppO₂.

// ── Min Deco Profile helpers ──────────────────────────
function toggleMinDecoProfile() {
  const en = document.getElementById('minDecoProfileEnable').value === 'yes';
  const fields = document.getElementById('minDecoProfileFields');
  if (fields) fields.style.display = en ? 'contents' : 'none';
}

function syncMinStopTimeRounding() {
  const rounding = document.getElementById('stopRounding')?.value || 'wholeminute';
  const subMin = document.getElementById('minStopTimeSubMin');
  const sel = document.getElementById('minStopTime');
  if (!subMin || !sel) return;
  const whole = rounding === 'wholeminute';
  subMin.disabled = whole;
  if (whole && sel.value === '0.0167') sel.value = '0.1667';
}

function updateMinDecoLabels(isMetric) {
  const l9 = document.getElementById('minDeco9mLabel');
  const l6 = document.getElementById('minDeco6mLabel');
  if (l9) l9.textContent = isMetric ? '9m (min)' : '30ft (min)';
  if (l6) l6.textContent = isMetric ? '6m (min)' : '20ft (min)';
}

/**
 * Enforce minimum stop times at 9 m (30 ft) and 6 m (20 ft).
 * Works on the collapsed steps array used by both Bühlmann and VPM-B engines.
 * @param {Array} steps  - array of step objects with {type, depth, to, dur, gas, ...}
 * @param {boolean} enabled
 * @param {number} min9m  - minimum minutes at 9 m stop
 * @param {number} min6m  - minimum minutes at 6 m stop
 * @param {boolean} isMetric
 * @returns {Array} steps with minimum enforced
 */
function enforceMinDecoProfile(steps, enabled, min9m, min6m, isMetric, fallbackGas, fallbackFN2, fallbackFHe) {
  _syncZhlBundleEnv();
  return ZhlEngineBundle.enforceMinDecoProfile(steps, enabled, min9m, min6m, isMetric, fallbackGas, fallbackFN2, fallbackFHe);
}

function getVpmMinDecoSettingsFromDom() {
  return {
    enabled: document.getElementById('minDecoProfileEnable')?.value === 'yes',
    min9m: parseFloat(document.getElementById('minDeco9m')?.value) || 1,
    min6m: parseFloat(document.getElementById('minDeco6m')?.value) || 3,
    isMetric: units !== 'imperial',
  };
}

let _confirmCallback = null;
function showConfirm(message, callback) {
  _confirmCallback = callback || null;
  document.getElementById('confirmModalMsg').textContent = message;
  const modal = document.getElementById('confirmModal');
  modal.style.display = 'flex';
}
function closeConfirmModal(ok) {
  document.getElementById('confirmModal').style.display = 'none';
  if (ok && typeof _confirmCallback === 'function') {
    _confirmCallback();
  }
  _confirmCallback = null;
}

// ── Env Settings collapse (Water / Units / Altitude / Acclimatized) ─────────
// AUDIT-UNIT:UI-SETTINGS-CONTROLS
function toggleEnvSettings(forceOpen) {
  if (forceOpen === false) return;
  setMainNav('settings', document.getElementById('navBtnSettings'));
  try { localStorage.setItem('lspEnvOpen', '1'); } catch (e) {}
}

// ── Advanced Settings collapse ───────────────────────────────────────────────
function toggleAdvancedSettings(forceOpen) {
  const body = document.getElementById('advancedSettingsBody');
  const chevron = document.getElementById('advancedSettingsChevron');
  const btn = document.getElementById('advancedSettingsToggle');
  if (!body) return;
  const isOpen = body.style.display !== 'none';
  const open = forceOpen !== undefined ? forceOpen : !isOpen;
  body.style.display = open ? '' : 'none';
  if (chevron) chevron.style.transform = open ? 'rotate(90deg)' : '';
  if (btn) {
    btn.style.borderColor = open ? 'var(--accent)' : 'var(--border)';
    btn.style.color = open ? 'var(--accent)' : 'var(--muted)';
  }
  _updateAdvancedSummary();
  try { localStorage.setItem('lspAdvancedOpen', open ? '1' : '0'); } catch(e) {}
}
function _updateAdvancedSummary() {
  // Show key non-default values in the collapsed summary line
  const el = document.getElementById('advancedSettingsSummary');
  if (!el) return;
  const body = document.getElementById('advancedSettingsBody');
  if (body && body.style.display !== 'none') { el.textContent = ''; return; }
  const rateU = units === 'imperial' ? 'ft/min' : 'm/min';
  const depthU = units === 'imperial' ? 'ft' : 'm';
  const parts = [];
  const dr = document.getElementById('descentRate')?.value; if (dr && dr !== '20') parts.push(dr+'↓'+rateU);
  const ar = document.getElementById('ascentRate')?.value; if (ar && ar !== '10') parts.push(ar+'↑'+rateU);
  const dar = document.getElementById('decoAscentRate')?.value; if (dar && dar !== '3') parts.push(dar+'↑deco');
  const ls = document.getElementById('lastDecoStop')?.value; if (ls && ls !== '3') parts.push('last '+ls+depthU);
  const ms = document.getElementById('minStopTime')?.value; if (ms && ms !== '2') parts.push('min '+ms+'min');
  const wv = document.getElementById('waterVapor')?.value; if (wv === '0.0627') parts.push('WV Bühl');
  const tr = document.getElementById('decoTransitMode')?.value; if (tr === 'schreiner') parts.push('Schreiner');
  const md = document.getElementById('minDecoProfileEnable')?.value; if (md === 'yes') parts.push('MinDeco on');
  el.textContent = parts.length ? parts.join(' · ') : 'defaults';
}

// ── User personal defaults ────────────────────────────────────────────────
// The ADVANCED settings that "Set as My Default" persists.
// Factory defaults are used as fallback when no user defaults are saved.
const _ADV_FIELDS = [
  'gfPresetSelect','gfLowInput','gfHighInput',
  'descentRate','ascentRate','decoAscentRate','surfaceAscentRate',
  'decoStep','lastDecoStop','minStopTime','stopRounding','decoTransitMode','shallowGradient',
  'waterVapor','heHalfTimeMode','sacBottom','sacDeco','contingencySacMultiplier',
  'n2NarcSel','o2NarcSel','ppo2Bottom','ppo2Deco','o2AtMODSelect',
  'ccrDescentSetpoint','ccrBottomSetpoint','ccrDecoSetpoint',
  'ccrLoopVolume','ccrMetabolicO2',
  'minDecoProfileEnable','minDeco9m','minDeco6m'
];

function saveAsMyDefault() {
  const snapshot = {};
  _ADV_FIELDS.forEach(id => {
    const el = document.getElementById(id);
    if (el) snapshot[id] = el.value;
  });
  try {
    localStorage.setItem('lspUserAdvDefaults', JSON.stringify(snapshot));
    showToast('✓ Advanced settings saved as your personal defaults', 'preset');
    // Update button to show it's been saved
    const btn = document.getElementById('saveMyDefaultBtn');
    if (btn) {
      const orig = btn.innerHTML;
      btn.style.color = 'var(--green)';
      btn.style.borderColor = 'var(--green)';
      setTimeout(() => { btn.style.color = ''; btn.style.borderColor = ''; }, 1800);
    }
  } catch(e) {
    showToast('Could not save defaults — storage unavailable', 'error', true);
  }
}

function resetToDefaults() {
  showConfirm('Reset settings to defaults?', () => {
    let ud = null;
    try { ud = JSON.parse(localStorage.getItem('lspUserAdvDefaults') || 'null'); } catch(e) {}
    _doResetToDefaults(ud);
  });
}

function _factoryMetricDefaults() {
  return {
    // Rates
    descentRate:      '20',
    ascentRate:       '10',
    decoAscentRate:   '3',
    surfaceAscentRate:'3',
    // Stop settings
    decoStep:         '3',
    lastDecoStop:     '3',
    minStopTime:      '2',
    stopRounding:     'wholeminute',
    waterVapor:       '0.0577',
    // ppO2 limits
    ppo2Bottom:       '1.4',
    ppo2Deco:         '1.6',
    // SAC rates
    sacBottom:        '22',
    sacDeco:          '20',
    contingencySacMultiplier: '1.5',
    // Narcosis
    n2NarcSel:        'yes',
    o2NarcSel:        'yes',
    // Deco plan inputs
    tecDepth:        '40',
    tecBT:           '25',
    recDepth:        '40',
    recBT:           '30',
    decoGas:          'air',
    circuitSelect:    'OC',
    ccrDecoSetpoint:  '1.3',
    ccrBottomSetpoint:'1.2',
    ccrDescentSetpoint: '0.7',
    ccrBailoutToggle: 'off',
    ccrBailoutGfLow:  '50',
    ccrBailoutGfHigh: '85',
    ccrLoopVolume:    '10',
    ccrMetabolicO2:   '1.5',
    ccrSacStress:     '50',
    ccrSacDeco:       '25',
    ccrStressTime:    '10',
    ccrProblemSolve:  '3',
    ccrSetpoint:      '1.3',
    scrLoopVolume:    '10',
    scrMetabolicO2:   '1.5',
    // Deco gases
    dg1Mix:           'ean50',
    dg2Mix:           'o2',
    // Cylinder defaults
    cylBot_size:      '12',
    cylBot_pres:      '200',
    cylDg1_size:      '11',
    cylDg1_pres:      '200',
    cylDg2_size:      '11',
    cylDg2_pres:      '200',
    cylTravelGas_size:'11',
    cylTravelGas_pres:'200',
    // Cylinder reserve pressures (bar)
    cylBot_reserve:      '50',
    cylDg1_reserve:      '50',
    cylDg2_reserve:      '50',
    cylTravelGas_reserve:'50',
    // Gas Plan tab cylinders (metric defaults)
    gpBot_size:     '12',
    gpBot_fill:     '200',
    gpBot_reserve:  '50',
    gpTravel_size:  '11',
    gpTravel_fill:  '200',
    gpTravel_reserve:'50',
    gpDg1_size:     '11',
    gpDg1_fill:     '200',
    gpDg1_reserve:  '50',
    gpDg2_size:     '11',
    gpDg2_fill:     '200',
    gpDg2_reserve:  '50',
    // Min deco profile
    minDecoProfileEnable: 'no',
    minDeco9m:        '1',
    minDeco6m:        '3',
    // He half-time
    heHalfTimeMode:   'baker',
  };
}

function _factoryDefaultsForUnits() {
  const d = _factoryMetricDefaults();
  if (units !== 'imperial') return d;
  const FT_PER_M = 3.28084;
  const PSI_PER_BAR = 14.5038;
  const CUFT_PER_L = CUFT_PER_LITRE;
  const cuft = (litres) => (litres * CUFT_PER_L).toFixed(1).replace(/\.0$/, '');
  const psi = (bar) => String(Math.round(bar * PSI_PER_BAR));
  const sacCuft = (lMin) => (lMin * CUFT_PER_L).toFixed(2).replace(/\.0+$/, '');
  return Object.assign(d, {
    tecDepth: String(Math.round(40 * FT_PER_M)),
    recDepth: String(Math.round(40 * FT_PER_M)),
    sacBottom: sacCuft(22),
    sacDeco: sacCuft(20),
    cylBot_size: cuft(12),
    cylBot_pres: psi(200),
    cylBot_reserve: psi(50),
    cylDg1_size: cuft(11),
    cylDg1_pres: psi(200),
    cylDg1_reserve: psi(50),
    cylDg2_size: cuft(11),
    cylDg2_pres: psi(200),
    cylDg2_reserve: psi(50),
    cylTravelGas_size: cuft(11),
    cylTravelGas_pres: psi(200),
    cylTravelGas_reserve: psi(50),
    gpBot_size: cuft(12),
    gpBot_fill: psi(200),
    gpBot_reserve: psi(50),
    gpTravel_size: cuft(11),
    gpTravel_fill: psi(200),
    gpTravel_reserve: psi(50),
    gpDg1_size: cuft(11),
    gpDg1_fill: psi(200),
    gpDg1_reserve: psi(50),
    gpDg2_size: cuft(11),
    gpDg2_fill: psi(200),
    gpDg2_reserve: psi(50),
  });
}

function _doResetToDefaults(userDefaults) {
  const defaults = _factoryDefaultsForUnits();

  // Overlay user's personal advanced defaults on top of factory defaults (if any)
  if (userDefaults && typeof userDefaults === 'object') {
    _ADV_FIELDS.forEach(id => {
      if (userDefaults[id] != null) defaults[id] = userDefaults[id];
    });
  }

  // Apply to all DOM fields
  Object.entries(defaults).forEach(([id, val]) => {
    const el = document.getElementById(id);
    if (el) el.value = val;
  });

  // Reset Gas Plan rule to thirds
  setGasRule('thirds');

  // Reset GF — honour saved personal GF when present
  if (userDefaults?.gfLowInput != null && userDefaults?.gfHighInput != null) {
    setGF(parseInt(userDefaults.gfLowInput, 10) || 20, parseInt(userDefaults.gfHighInput, 10) || 85);
  } else if (userDefaults?.gfPresetSelect) {
    const gfEl = document.getElementById('gfPresetSelect');
    if (gfEl) gfEl.value = userDefaults.gfPresetSelect;
    if (typeof applyGFPreset === 'function') applyGFPreset();
    else setGF(20, 85);
  } else {
    setGF(20, 85);
  }

  // Reset water density to salt default
  setWaterDensity('salt');

  // Reset altitude to sea level
  const altSel = document.getElementById('altitudeSelect');
  if (altSel) altSel.value = '0';
  const altCustomRow = document.getElementById('altitudeCustomRow');
  if (altCustomRow) altCustomRow.style.display = 'none';
  const acclSel = document.getElementById('acclimatizedSelect');
  if (acclSel) acclSel.value = 'yes';
  altitudeM = 0; altSurfaceP = SEA_LEVEL_P; altAcclimatized = true;
  try { localStorage.removeItem('lspAltitude'); localStorage.removeItem('lspAcclimatized'); } catch(e) {}
  try { localStorage.removeItem('gfCustomLow'); localStorage.removeItem('gfCustomHigh'); } catch(e) {}
  const badge = document.getElementById('altitudePressureDisplay'); if(badge) badge.textContent='';

  // Apply water vapor constant
  updateWaterVapor();

  // Clear custom O2 fields visibility
  toggleDecoCustomO2?.('decoGas', 'decoCustomO2Field');
  toggleDecoCustomO2?.('dg1Mix', 'dg1CustomField');
  toggleDecoCustomO2?.('dg2Mix', 'dg2CustomField');
  toggleBottomTrimix?.();
  for (const idx of getAllDecoGasIds()) {
    toggleDecoTrimix?.(idx);
  }
  toggleCircuitFields?.();
  syncMinStopTimeRounding?.();
  updateGasMODDisplays?.();
  _updateAdvancedSummary();

  // Clear localStorage v4
  try { localStorage.removeItem('lspDiveSettings_v6'); } catch(e) {}

  // Save fresh defaults
  if (typeof appSettings !== 'undefined' && appSettings.save) {
    appSettings.save(false);
  }

  // Clear any existing results
  const dr = document.getElementById('decoResult');
  if (dr) dr.style.display = 'none';

  // Update switch depth displays without running full schedule
  document.querySelectorAll('.switch-depth-display').forEach(el => { el.value = 'Calculate to see'; });

  console.log('[LSP] ↺ Settings reset to defaults (ApexDeco-matched)');
}

function getActiveGas(curDepthM, bottomFN2, bottomFHe, decoGases, getPPO2LimitFn, bottomLabel) {
  _syncZhlBundleEnv();
  return ZhlEngineBundle.getActiveGas(curDepthM, bottomFN2, bottomFHe || 0, decoGases, getPPO2LimitFn, bottomLabel);
}

function ppO2DisplayStyle(ppO2Str, limit) {
  if (ppO2Str === 'ERR') return 'color:var(--red);font-weight:700;';
  const v = parseFloat(ppO2Str);
  const lim = limit != null ? limit : 1.6;
  if (!Number.isFinite(v)) return 'color:var(--red);font-weight:700;';
  if (v > lim) return 'color:var(--red);font-weight:700;';
  if (v > lim * 0.97) return 'color:var(--orange);';
  return 'color:var(--muted);';
}

function ppO2Check(depthM, fN2, fHe, opts) {
  _syncZhlBundleEnv();
  if (opts && opts.ccr) {
    opts = { ...opts, ccr: mergeCCRSettings(opts.ccr) };
  }
  return ZhlEngineBundle.ppO2Check(depthM, fN2, fHe, opts);
}

function fmtPpO2(v) {
  if (v === 'ERR' || v == null) return String(v);
  return Number.isFinite(v) ? v.toFixed(2) : String(v);
}

function renderBlockingScheduleError(message) {
  _clearPlannerResults?.();
  notifyScheduleError?.(message);
  scheduleDecoScheduleStackSync?.();
}

function validateOcBottomGasPpo2(depthM, bottomFracs, ppo2Limit, settings, algorithmLabel) {
  if (!bottomFracs || !Number.isFinite(depthM) || depthM <= 0) return { ok: true };
  if (isRebreatherCircuit(settings?.circuit || 'OC')) return { ok: true };
  const actual = ppO2Check(depthM, bottomFracs.fN2, bottomFracs.fHe);
  const limit = Number.isFinite(ppo2Limit) ? ppo2Limit : 1.4;
  if (!Number.isFinite(actual) || actual <= limit + 0.005) return { ok: true, actual };
  const modM = calcGasMODm(bottomFracs.fO2, limit);
  const depthDisp = units === 'imperial' ? Math.round(depthM * 3.28084) : Math.round(depthM);
  const modDisp = units === 'imperial' ? Math.round(modM * 3.28084) : modM;
  const du = units === 'imperial' ? 'ft' : 'm';
  const label = getGasLabel(bottomFracs.fO2, bottomFracs.fHe);
  const algoPrefix = algorithmLabel ? `${algorithmLabel}: ` : '';
  return {
    ok: false,
    actual,
    message: `${algoPrefix}BEYOND MOD. ${depthDisp}${du} exceeds ${label} MOD of ${modDisp}${du} at actual ${actual.toFixed(2)} bar ppO₂. Use a lower O₂ bottom gas, add a travel gas, or reduce depth.`,
  };
}

function validateVpmOcBottomGasPpo2(depthM, bottomFracs, ppo2Limit, settings) {
  return validateOcBottomGasPpo2(depthM, bottomFracs, ppo2Limit, settings, 'VPM');
}

// ── VPM SCHEDULE RUNNER ──────────────────────────────────────────────
// ── Feature B: VPM repetitive dive carry ───────────────────────────────────
let _lastVPMResult = null; // { finalTissues, finalBubbleState }

function updateVpmRepUI() {
  const cb  = document.getElementById('vpmRepMode');
  const siRow = document.getElementById('vpmRepSIRow');
  const lbl   = document.getElementById('vpmRepLabel');
  if (!cb) return;
  if (cb.checked) {
    if (siRow) siRow.style.display = 'flex';
    if (lbl && _lastVPMResult) lbl.textContent = '● bubble state loaded';
  } else {
    if (siRow) siRow.style.display = 'none';
    if (lbl) lbl.textContent = '';
  }
}

function clearVpmRepState() {
  _lastVPMResult = null;
  const cb = document.getElementById('vpmRepMode');
  if (cb) cb.checked = false;
  const siRow = document.getElementById('vpmRepSIRow');
  if (siRow) siRow.style.display = 'none';
  const lbl = document.getElementById('vpmRepLabel');
  if (lbl) lbl.textContent = '';
  const row = document.getElementById('vpmRepRow');
  if (row) row.style.display = 'none';
}

function updateZhlRepUI() {
  const cb = document.getElementById('zhlRepMode');
  const siRow = document.getElementById('zhlRepSIRow');
  const lbl = document.getElementById('zhlRepLabel');
  if (!cb) return;
  if (cb.checked) {
    if (siRow) siRow.style.display = 'flex';
    if (lbl && peekZhlRepState()) lbl.textContent = '● tissue state loaded';
  } else {
    if (siRow) siRow.style.display = 'none';
    if (lbl) lbl.textContent = '';
  }
}

function clearZhlRepState() {
  window._zhlRepState = null;
  const cb = document.getElementById('zhlRepMode');
  if (cb) cb.checked = false;
  const siRow = document.getElementById('zhlRepSIRow');
  if (siRow) siRow.style.display = 'none';
  const lbl = document.getElementById('zhlRepLabel');
  if (lbl) lbl.textContent = '';
  const row = document.getElementById('zhlRepRow');
  if (row) row.style.display = 'none';
}
// ───────────────────────────────────────────────────────────────────────────────

function onConservatismChange() {
  _syncConservatismBtns();
  if (window._zhlHeadless) return;
  const sel = document.getElementById('conservatismSelect');
  const nextVal = sel?.value || '2';
  if (sel && sel.dataset.lspLastValue === nextVal) {
    if (typeof appSettings !== 'undefined' && appSettings.save) {
      appSettings.save(false);
    }
    return;
  }
  if (sel) sel.dataset.lspLastValue = nextVal;
  const decoRes = document.getElementById('decoResult');
  if (decoRes && decoRes.style.display !== 'none' && decoRes.innerHTML.trim()) {
    runDecoSchedule();
  }
  if (typeof appSettings !== 'undefined' && appSettings.save) {
    appSettings.save(false);
  }
}

// AUDIT-UNIT:UI-VPM-RUNNER
function runVPMSchedule(depthM, bt, descentRate, ascentRate, decoAscentRate, surfaceAscentRate,
                        stepSize, lastStop, minStopTime, ppo2Bottom, ppo2Deco, model, wholeMinStops) {
  // Headless mode: skip all VPM computation and DOM rendering
  // (called from ZHLEngine or fastRDS headless path when algo is VPM-B)
  if (window._zhlHeadless) return;
  _syncZhlBundleEnv();
  const conservatism = parseInt(document.getElementById('conservatismSelect')?.value || '0');
  const gfHi = (mGF && Number.isFinite(mGF.high)) ? mGF.high : 85;

  // Gather deco gases from DOM (same as Bühlmann)
  const decoGases = [];
  for (const n of getAllDecoGasIds()) {
    const mixEl = document.getElementById(`dg${n}Mix`);
    if (!mixEl || mixEl.value === 'none' || !mixEl.value) continue;
    const dgvFracs = getDecoCardFractions(n);
    if (!dgvFracs || !Number.isFinite(dgvFracs.fO2) || !Number.isFinite(dgvFracs.fHe)) {
      const dgPct = getDomDecoGasPct(n);
      if (dgPct) {
        notifyScheduleError(`VPM: invalid deco gas ${n} (${dgPct.o2}%/${dgPct.he}%) — fix mix or set to None.`);
      } else {
        notifyScheduleError(`VPM: deco gas ${n} has no valid mix — enter O₂/He or set to None.`);
      }
      continue;
    }
    decoGases.push({
      o2: parseFloat((dgvFracs.fO2 * 100).toFixed(2)),
      he: parseFloat((dgvFracs.fHe * 100).toFixed(2)),
    });
  }

  // Build settings object for VPMEngine
  // IMPORTANT: waterType 0=salt, 1=fresh, 2=EN13319, 3=custom (uses barPerM)
  const waterTypeVal = getWaterTypeForVPM();

  const settings = {
    metric:            true,
    waterType:         waterTypeVal,
    barPerM:           BAR_PER_METRE,
    descentRate,
    ascentRate,
    decoAscentRate,
    surfaceAscentRate,
    stepSize,
    lastStop,
    minStopTime,
    ppO2Bottom:        ppo2Bottom,
    ppO2Deco:          ppo2Deco,
    // ppO2 thresholds for selectDecoGas — must match ApexDeco defaults:
    // ≤28% O2 → ppO2Low, 28-45% O2 → ppO2Mid, >45% O2 → ppO2High
    // EAN50 is >45% so uses ppO2High=1.6 — critical for correct switch depth
    ppO2Low:           ppo2Bottom,  // air/lean: 1.4
    ppO2Mid:           1.5,         // nitrox 28-45%: 1.5 (NOT 1.4 — ApexDeco default)
    ppO2High:          ppo2Deco,    // rich deco gas >45%: 1.6
    o2MaxDepth:        6,
    conservatism,
    gfHi,
    gfs:               gfHi,
    waterVapor:        WATER_VAPOR,
    firstStop30sec:    false,
    extendedStops:     false,
    wholeMinStops:     wholeMinStops === true,
    altitude:          Number.isFinite(altitudeM) ? altitudeM : 0,
    minDecoProfile:    (() => {
      const m = getVpmMinDecoSettingsFromDom();
      return { enabled: m.enabled, m9: m.min9m, m6: m.min6m, isMetric: m.isMetric };
    })(),
    ...getCCRSettingsFromDOM(),
  };

  // ── Feature B: inject repetitive dive state if active ─────────────────────────
  const vpmRepEl = document.getElementById('vpmRepMode');
  const vpmSIEl  = document.getElementById('vpmSurfaceInterval');
  if (vpmRepEl && vpmRepEl.checked && _lastVPMResult) {
    const siCheck = validateVpmSurfaceInterval();
    if (!siCheck.ok) {
      const msg = siCheck.msg || 'Invalid VPM surface interval.';
      if (!renderScheduleErrorRow(msg)) alert(msg);
      return;
    }
    const siMin = siCheck.value;
    settings._preTissues      = _lastVPMResult.finalTissues;
    settings._surfaceInterval = siMin;
    settings._prevBubbleState = _lastVPMResult.finalBubbleState;
    // Carry CNS (decays on 90-min half-life) and OTU (daily accumulator, no decay)
    // CNS half-life: 90 min (Baker 1998 / NOAA standard)
    if (_lastVPMResult.finalCNS != null) {
      settings._preCNS = _lastVPMResult.finalCNS * Math.pow(0.5, siMin / 90);
    }
    if (_lastVPMResult.finalOTU != null) {
      settings._preOTU = _lastVPMResult.finalOTU; // OTU is a daily dose — no decay within a day
    }
  }
  // ── Prior dive O₂ carry (v2.20.0): inject from CNS tab if set ────────────────
  // Applied additively on top of VPM repetitive carry (if both active).
  // Day-boundary: OTU resets if >24h (computed in updatePriorDiveCarry).
  if (window._priorDiveCarry) {
    settings._preOTU = (settings._preOTU || 0) + window._priorDiveCarry.otuCarry;
    settings._preCNS = (settings._preCNS || 0) + window._priorDiveCarry.cnsCarry;
  }
  // ───────────────────────────────────────────────────────────────────────────

  // Bottom gas from DOM
  const bottomGasEl = document.getElementById('decoGas');
  const _vpmBotFracs = getBottomGasFractions();
  if (!_vpmBotFracs) {
    const msg = 'Cannot run VPM schedule: invalid bottom gas configuration.';
    if (!renderScheduleErrorRow(msg)) alert(msg);
    return;
  }
  const bottomO2pct = Math.round(_vpmBotFracs.fO2 * 100);
  const bottomHePct = Math.round(_vpmBotFracs.fHe * 100);
  const vpmBottomPpo2 = validateVpmOcBottomGasPpo2(depthM, _vpmBotFracs, ppo2Bottom, settings);
  if (!vpmBottomPpo2.ok) {
    renderBlockingScheduleError(vpmBottomPpo2.message);
    return;
  }

  const btAtDepthMin = Math.max(0, bt - depthM / descentRate);

  const levels = [{
    depth: depthM, time: btAtDepthMin, o2: bottomO2pct, he: bottomHePct,
    setpoint: settings.bottomSetpoint ?? settings.setpoint ?? 1.2,
    oc: settings.bailout,
  }];

  let result;
  const vpmApi = (typeof window !== 'undefined' && window.VPMEngine) ? window.VPMEngine : null;
  if (!vpmApi || typeof vpmApi.calculate !== 'function') {
    const msg = 'VPM engine failed to load (vpm-engine-bundle.js). Check network or refresh.';
    console.error('[VPM]', msg);
    renderScheduleErrorRow(msg);
    return;
  }
  try {
    result = vpmApi.calculate(levels, decoGases, settings, model);
  } catch(e) {
    console.error('[VPM] Engine error:', e);
    renderScheduleErrorRow(`VPM Error: ${e.message}`);
    return;
  }

  if (result.code === 'VPM_STOP_CAP' && result.plan && result.plan.length) {
    renderVPMResults(result, settings, depthM, bt, bottomO2pct, bottomHePct, decoGases, model, _vpmBotFracs);
    return;
  }
  if (result.error) {
    renderScheduleErrorRow(`VPM Error: ${result.error}`);
    return;
  }

  // ── Feature B: save dive result for next repetitive dive ───────────────────────
  if (result.finalTissues && !_contingencyRunning) {
    _lastVPMResult = {
      finalTissues:    result.finalTissues,
      finalBubbleState: result.finalBubbleState,
      finalCNS:        result.totalCNS,   // carry CNS for repetitive dive (decays on 90-min half-life)
      finalOTU:        result.totalOTU,   // carry OTU for repetitive dive (daily accumulator)
    };
    // Show/enable the repetitive dive UI now that we have a result
    const vpmRepRow = document.getElementById('vpmRepRow');
    if (vpmRepRow) vpmRepRow.style.display = 'flex';
  }
  // ───────────────────────────────────────────────────────────────────────────

  // Render into the existing deco table using the same format as Bühlmann
  renderVPMResults(result, settings, depthM, bt, bottomO2pct, bottomHePct, decoGases, model, _vpmBotFracs);
}


// ── END VPM SCHEDULE RUNNER ──────────────────────────────────────────

// VPMEngine — Tier 3 bundle (vpm-engine-bundle.js)


function validateDiveInputs(depthId, btId, depthLimits) {
  if (window._zhlHeadless) return { ok: true };
  const lim = depthLimits || {};
  const maxDepth = units === 'imperial'
    ? (lim.imperial != null ? lim.imperial : 330)
    : (lim.metric != null ? lim.metric : 100);
  const maxBt = lim.maxBt != null ? lim.maxBt : 300;
  const rawD = parseFloat(document.getElementById(depthId)?.value);
  const bt = parseInt(document.getElementById(btId)?.value, 10);
  const du = units === 'imperial' ? 'ft' : 'm';
  if (!Number.isFinite(rawD) || rawD <= 0) {
    return { ok: false, msg: 'Depth must be a positive number.' };
  }
  if (rawD > maxDepth) {
    return { ok: false, msg: `Depth exceeds the ${maxDepth} ${du} limit.` };
  }
  if (!Number.isFinite(bt) || bt <= 0) {
    return { ok: false, msg: 'Bottom time must be a positive number of minutes.' };
  }
  if (bt > maxBt) {
    return { ok: false, msg: `Bottom time exceeds the ${maxBt} minute limit.` };
  }
  return { ok: true };
}

function validatePlannerInputs() {
  const isPadi = typeof algo !== 'undefined' && algo === 'padi';
  const depthLim = isPadi
    ? { metric: PADI_TABLE_MAX_M, imperial: PADI_TABLE_MAX_FT, maxBt: 300 }
    : { metric: 100, imperial: 330, maxBt: 300 };
  const base = validateDiveInputs('recDepth', 'recBT', depthLim);
  if (!base.ok) return base;
  const isMetric = units === 'metric';
  const rawD = parseFloat(document.getElementById('recDepth')?.value);
  const bt = parseInt(document.getElementById('recBT')?.value, 10);
  const depthM = isMetric ? rawD : rawD / 3.28084;
  if (isPadi && padiTableRowIndex(depthM) == null) {
    const du = isMetric ? `${PADI_TABLE_MAX_M} m` : `${PADI_TABLE_MAX_FT} ft`;
    return { ok: false, msg: `Depth exceeds the PADI table maximum (${du}).` };
  }
  const descentRate = Math.max(1, parseInt(document.getElementById('descentRate')?.value, 10) || 20);
  if (Number.isFinite(depthM) && Number.isFinite(bt) && depthM > 0 && bt <= depthM / descentRate + 1e-6) {
    const descentMin = (depthM / descentRate).toFixed(1);
    return {
      ok: false,
      msg: `Bottom time (${bt} min) is not longer than descent (${descentMin} min); time at depth will be 0.`,
    };
  }
  if (!isPadi) {
    const mix = document.getElementById('gasMix')?.value || 'air';
    if (mix === 'trimix') {
      const check = validateGasFractionsPct(
        readDomO2Pct('plannerTrimixO2'), readDomHePct('plannerTrimixHe'), 'plannerTrimix');
      if (!check.ok) return { ok: false, msg: check.message };
      if (check.o2 < 18) {
        return { ok: false, msg: 'Trimix O₂ below 18% is hypoxic — use a higher O₂ fraction.' };
      }
    } else if (mix === 'custom') {
      const check = validateGasFractionsPct(readDomO2Pct('customO2'), 0, 'customO2');
      if (!check.ok) return { ok: false, msg: check.message };
      const o2 = check.o2;
      if (o2 < 21 || o2 > 100) {
        return { ok: false, msg: 'Custom O₂ must be between 21% and 100%.' };
      }
    }
  }
  return { ok: true };
}

const REP_SURFACE_INTERVAL_DEFAULT_MIN = 60;
const REP_SURFACE_INTERVAL_MAX_MIN = 10080;

function sanitizeRepetitiveSurfaceInterval(raw, fallback = REP_SURFACE_INTERVAL_DEFAULT_MIN) {
  const value = Number(raw);
  if (!Number.isFinite(value) || value < 0 || value > REP_SURFACE_INTERVAL_MAX_MIN) {
    return fallback;
  }
  return Math.round(value);
}

function normalizeRepetitiveSurfaceIntervalInput(id, fallback = REP_SURFACE_INTERVAL_DEFAULT_MIN) {
  const el = document.getElementById(id);
  const value = sanitizeRepetitiveSurfaceInterval(el?.value, fallback);
  if (el && String(el.value) !== String(value)) {
    el.value = String(value);
  }
  return value;
}

function validateVpmSurfaceInterval() {
  const vpmRepEl = document.getElementById('vpmRepMode');
  if (!vpmRepEl?.checked) return { ok: true, value: 0 };
  const raw = document.getElementById('vpmSurfaceInterval')?.value;
  const si = parseFloat(raw);
  if (!Number.isFinite(si) || si < 0 || si > REP_SURFACE_INTERVAL_MAX_MIN) {
    return { ok: false, msg: 'Surface interval must be a number from 0 to 10080 minutes.' };
  }
  return { ok: true, value: si };
}

function validateDecoInputs() {
  const base = validateDiveInputs('tecDepth', 'tecBT', { metric: 120, imperial: 394, maxBt: 300 });
  if (!base.ok) return base;
  const decoCheck = validateDomDecoGases();
  if (!decoCheck.ok) {
    return { ok: false, msg: decoCheck.errors.map(e => e.message).join('\n') };
  }
  const vpmSi = validateVpmSurfaceInterval();
  if (!vpmSi.ok) return vpmSi;
  return { ok: true };
}

// ═══════════════════════════════════════════════
// ZHL SCHEDULE CORE — Tier 3 (bundle + DOM param builder)
// ═══════════════════════════════════════════════

function getZhlEnvironment(settings) {
  const s = settings || {};
  let surfP = typeof altSurfaceP !== 'undefined' ? altSurfaceP : 1.01325;
  let accl = typeof altAcclimatized !== 'undefined' ? altAcclimatized : true;
  if (s.altitude != null && Number(s.altitude) > 0) {
    surfP = altToPressure(Number(s.altitude));
    if (s.acclimatized != null) accl = s.acclimatized !== false;
  }
  return {
    altSurfaceP: surfP,
    barPerMetre: BAR_PER_METRE,
    waterVapor: WATER_VAPOR,
    altAcclimatized: accl,
    allowO2AtMOD: typeof allowO2AtMOD !== 'undefined' ? allowO2AtMOD : true,
  };
}

function zhlOptimalSwitchDepth(fO2, ctx) {
  ZhlEngineBundle.applyEnvironment(getZhlEnvironment());
  return ZhlEngineBundle.zhlOptimalSwitchDepth(fO2, ctx);
}

function peekZhlRepState() {
  return (window._zhlRepState && Array.isArray(window._zhlRepState.tissues))
    ? window._zhlRepState : null;
}

function saveZhlRepState(tissues, surfaceIntervalMin, exposure) {
  if (tissues && tissues.length) {
    const lp = window._lastPlan;
    window._zhlRepState = {
      tissues,
      surfaceIntervalMin: sanitizeRepetitiveSurfaceInterval(surfaceIntervalMin, REP_SURFACE_INTERVAL_DEFAULT_MIN),
      surfaceP: altSurfaceP || SEA_LEVEL_P,
      totalCNS: exposure?.totalCNS ?? lp?.totalCNS,
      totalOTU: exposure?.totalOTU ?? lp?.totalOTU,
    };
  }
}

function getZhlRepStateForSchedule() {
  const zhlRepEl = document.getElementById('zhlRepMode');
  const snap = peekZhlRepState();
  if (!zhlRepEl?.checked || !snap) return null;
  return {
    tissues: snap.tissues,
    surfaceIntervalMin: sanitizeRepetitiveSurfaceInterval(snap.surfaceIntervalMin, REP_SURFACE_INTERVAL_DEFAULT_MIN),
    surfaceP: snap.surfaceP ?? (altSurfaceP || SEA_LEVEL_P),
    totalCNS: snap.totalCNS,
    totalOTU: snap.totalOTU,
  };
}

function takeZhlRepStateSnapshot() {
  return getZhlRepStateForSchedule();
}

function getWaterTypeForVPM() {
  const sel = document.getElementById('waterDensitySelect')?.value;
  if (sel === 'fresh') return 1;
  if (sel === 'en13319') return 2;
  if (sel === 'salt') return 0;
  if (sel === 'custom') return 3;
  const bpm = BAR_PER_METRE || 0.1;
  if (Math.abs(bpm - WATER_DENSITY.fresh) < 0.0001) return 1;
  if (Math.abs(bpm - WATER_DENSITY.en13319) < 0.0001) return 2;
  if (Math.abs(bpm - WATER_DENSITY.salt) < 0.0001) return 0;
  return 3;
}

function buildZhlScheduleParamsFromEngine(levels, decoGases, settings, profileSplit) {
  return ZhlEngineBundle.buildZhlScheduleParamsFromEngine(
    levels, decoGases, settings, profileSplit, getZhlEnvironment()
  );
}

function buildZhlScheduleParamsFromDom(rawD, depthM, bt) {
  _travelGasFractionWarning = '';
  const rate = Math.max(1, parseInt(document.getElementById('ascentRate')?.value) || 9);
  const decoRate = Math.max(1, parseInt(document.getElementById('decoAscentRate')?.value) || 9);
  const surfaceRate = Math.max(1, parseInt(document.getElementById('surfaceAscentRate')?.value) || 9);
  const descentRate = Math.max(1, parseInt(document.getElementById('descentRate')?.value) || 22);
  const ppo2Bottom = parseFloat(document.getElementById('ppo2Bottom')?.value) || 1.4;
  const ppo2Deco = parseFloat(document.getElementById('ppo2Deco')?.value) || 1.6;
  const minStopTime = parseFloat(document.getElementById('minStopTime')?.value) || 1;
  const lastStop = parseInt(document.getElementById('lastDecoStop')?.value) || 3;
  const decoStep = parseInt(document.getElementById('decoStep')?.value) || 3;
  const metric = units === 'metric';
  const switchCtx = { ppo2Bottom, ppo2Deco, lastStop, decoStep, metric };
  const _botFracs = getBottomGasFractions();
  if (!_botFracs) {
    throw new Error('Invalid bottom gas: enter valid O₂ and He percentages.');
  }
  const bottomFN2 = _botFracs.fN2;
  const bottomFHe = _botFracs.fHe;
  const bottomFO2 = _botFracs.fO2;
  const bottomMixLabel = getGasLabel(bottomFO2, bottomFHe);
  const _ccrDom = getCCRSettingsFromDOM();
  const _ccrMerged = mergeCCRSettings(_ccrDom);
  const botHypo = ZhlEngineBundle.validateHypoxicDecoGas(
    bottomFO2 * 100, bottomFHe * 100, 'bottomGas', _ccrMerged.circuit
  );
  if (botHypo) throw new Error(botHypo.message);
  const dU = metric;
  const decoGases = [];
  const switchDisplays = [];
  for (const idx of getAllDecoGasIds()) {
    const mixEl = document.getElementById(`dg${idx}Mix`);
    if (!mixEl || mixEl.value === 'none' || !mixEl.value) continue;
    const dgf = getDecoCardFractions(idx);
    if (!dgf) {
      throw new Error(`Invalid deco gas ${idx}: enter valid O₂ and He percentages.`);
    }
    const hypo = ZhlEngineBundle.validateHypoxicDecoGas(dgf.fO2 * 100, dgf.fHe * 100, `dg${idx}`, _ccrMerged.circuit);
    if (hypo) throw new Error(hypo.message);
    const fN2 = dgf.fN2;
    const fHe = dgf.fHe || 0;
    const fO2 = dgf.fO2;
    const label = getDecoGasLabel(`dg${idx}Mix`, `dg${idx}CustomO2`);
    const depth = zhlOptimalSwitchDepth(fO2, switchCtx);
    if (depth !== null && fN2 !== null) {
      switchDisplays.push({
        idx,
        text: (dU ? depth + 'm' : mToFt(depth) + 'ft') + '  (ppO₂ ' +
          ((altSurfaceP + depth * BAR_PER_METRE) * fO2).toFixed(2) + ')',
      });
      decoGases.push({ depth, fN2, fHe, fO2, label });
    } else {
      switchDisplays.push({ idx, text: '—' });
    }
  }
  decoGases.sort((a, b) => b.depth - a.depth);
  const travelInfo = getTravelGasInfo();
  if (travelInfo) {
    const botMODm = bottomFO2 > 0 ? calcGasMODm(bottomFO2, ppo2Bottom) : depthM;
    const resolved = resolveTravelGasFractions(travelInfo);
    if (!resolved.valid) {
      warnTravelGasFractionIssue(resolved.reason);
    } else {
      const travelFO2 = resolved.fO2;
      const travelFHe = resolved.fHe;
      const ppO2AtBotMOD = (altSurfaceP + botMODm * BAR_PER_METRE) * travelFO2;
      if (ppO2AtBotMOD <= ppo2Bottom + 0.01) {
        decoGases.push({
          depth: botMODm,
          fN2: travelInfo.fN2,
          fHe: travelFHe,
          fO2: travelFO2,
          label: travelInfo.label,
          isTravelGas: true,
        });
        decoGases.sort((a, b) => b.depth - a.depth);
      }
    }
  }
  return {
    params: {
      depthM, bt, rawD, metric,
      ascentRate: rate,
      decoAscentRate: decoRate,
      surfaceAscentRate: surfaceRate,
      descentRate,
      gfL: mGF.low / 100,
      gfH: mGF.high / 100,
      ppo2Bottom, ppo2Deco,
      minStopTime,
      switchPauseT: 0,
      mdCompatMode: (document.getElementById('decoTransitMode')?.value || 'multideco') === 'multideco',
      wholeMinStops: (document.getElementById('stopRounding')?.value || 'fractional') === 'wholeminute',
      lastStop, decoStep,
      shallowGradient: isShallowGradientOn(),
      bottomFN2, bottomFHe, bottomFO2, bottomMixLabel,
      travelInfo,
      repState: takeZhlRepStateSnapshot(),
      continuationLevels: (window._zhlHeadless && Array.isArray(window._zhlContinuationLevels))
        ? window._zhlContinuationLevels : [],
      minDecoProfile: {
        enabled: document.getElementById('minDecoProfileEnable')?.value === 'yes',
        m9: parseFloat(document.getElementById('minDeco9m')?.value) || 1,
        m6: parseFloat(document.getElementById('minDeco6m')?.value) || 3,
        isMetric: units !== 'imperial',
      },
      decoGases,
      environment: getZhlEnvironment(),
      ccr: _ccrMerged,
      onLoop: isRebreatherCircuit(_ccrMerged.circuit) && !_ccrMerged.bailout,
      loopMixLabel: loopMixLabelFor(bottomMixLabel, _ccrMerged),
    },
    switchDisplays,
  };
}

function applyZhlSwitchDepthDisplays(switchDisplays) {
  if (!switchDisplays || window._zhlHeadless) return;
  switchDisplays.forEach(({ idx, text }) => {
    const swEl = document.getElementById(`dg${idx}SwitchDepthDisplay`);
    if (swEl) swEl.value = text;
  });
}

// AUDIT-UNIT:UI-ZHL-RUNNER-SETUP
function runZhlScheduleCore(params) {
  if (!params.environment) {
    params = Object.assign({}, params, { environment: getZhlEnvironment() });
  }
  return ZhlEngineBundle.runZhlScheduleCore(params);
}

function nextDecoScheduleGen() {
  window._decoScheduleSeq = (window._decoScheduleSeq || 0) + 1;
  return window._decoScheduleSeq;
}
function isStaleDecoScheduleGen(gen) {
  return gen !== window._decoScheduleSeq;
}

function runDecoSchedule() {
  let _zhlPrevGF = null;
  const scheduleGen = nextDecoScheduleGen();
  _syncZhlBundleEnv();
  window._scheduleWorkerBusy = true;
  try {
  if (!guardEngineBootForCalculate()) return;
  if (!window._zhlHeadless && !_contingencyRunning) {
    const inputVal = validateDecoInputs();
    if (!inputVal.ok) {
      _clearPlannerResults();
      notifyScheduleError(inputVal.msg);
      return;
    }
  }
  if (!window._zhlHeadless && !_contingencyRunning && isCcrGasUiMode()) {
    const gasVal = validateCcrGasConfiguration();
    if (!gasVal.ok) {
      updateCcrGasValidation();
      const err0 = gasVal.errors[0];
      _clearPlannerResults();
      notifyScheduleError(typeof err0 === 'string' ? err0 : (err0?.message || 'CCR gas configuration is invalid.'));
      return;
    }
  }
  if (!window._zhlHeadless && !_contingencyRunning) {
    const domGasVal = validateDomDecoGases();
    if (!domGasVal.ok) {
      updateCcrGasValidation();
      const domErr0 = domGasVal.errors[0];
      _clearPlannerResults();
      notifyScheduleError(domErr0?.message || 'Invalid gas configuration.');
      return;
    }
  }
  const rawD   = parseFloat(getPlannerInputEl('decoDepth')?.value) || 40;
  const depthM = units === 'metric' ? rawD : rawD / 3.28084;
  const bt     = parseInt(getPlannerInputEl('decoBT')?.value) || 30;
  const bottomFracsForPpo2 = getBottomGasFractions();
  const _uiCcr = getCCRSettingsFromDOM();
  const bottomPpo2Limit = parseFloat(document.getElementById('ppo2Bottom')?.value) || 1.4;
  const zhlBottomPpo2 = validateOcBottomGasPpo2(
    depthM,
    bottomFracsForPpo2,
    bottomPpo2Limit,
    mergeCCRSettings(_uiCcr),
    'Bühlmann'
  );
  if (!zhlBottomPpo2.ok && !window._zhlHeadless && !_contingencyRunning) {
    renderBlockingScheduleError(zhlBottomPpo2.message);
    return;
  }
  if (!window._zhlHeadless && isRebreatherCircuit(_uiCcr.circuit)) {
    const bot = getDomBottomGasPct();
    const ccrVal = validateCcrCalculationInputs(
      [{ depth: depthM, time: bt, o2: bot.o2, he: bot.he }],
      mergeCCRSettings(_uiCcr),
      collectDecoGasesPctFromDom()
    );
    if (!ccrVal.ok) {
      const msg = ccrVal.errors[0].message;
      _clearPlannerResults();
      notifyScheduleError(msg);
      return;
    }
  }
  const rate            = Math.max(1, parseInt(document.getElementById('ascentRate')?.value)        || 9);
  const decoRate        = Math.max(1, parseInt(document.getElementById('decoAscentRate')?.value)    || 9);
  const surfaceRate     = Math.max(1, parseInt(document.getElementById('surfaceAscentRate')?.value) || 9);
  const descentRate = Math.max(1, parseInt(document.getElementById('descentRate')?.value) || 22);
  let gfL    = mGF.low  / 100;
  let gfH    = mGF.high / 100;
  const ppo2Bottom = parseFloat(document.getElementById('ppo2Bottom')?.value) || 1.4;
  const ppo2Deco   = parseFloat(document.getElementById('ppo2Deco')?.value)   || 1.6;
  const minStopT   = parseFloat(document.getElementById('minStopTime')?.value) || 1;
  const switchPauseT = 0;
  const wholeMinStops = (document.getElementById('stopRounding')?.value || 'fractional') === 'wholeminute';
  const mdCompatMode  = (document.getElementById('decoTransitMode')?.value || 'schreiner') === 'multideco';
  updateWaterVapor();
  const ppo2High = ppo2Deco;
  const ppo2Mid  = 1.5;         // mid-band: 28–44% O2 → 1.5 bar (not ppo2Bottom)
  const ppo2Low  = ppo2Bottom;
  // VPM-B: last stop must be 6m when using EAN50+O2 as deco gases
  // ApexDeco uses lastStop=6 for VPM — this determines where critical volume
  // time accumulates. lastStop=3 incorrectly splits time across 3m and 6m.
  const lastStop = parseInt(document.getElementById('lastDecoStop')?.value) || 3;
  const decoStep    = parseInt(document.getElementById('decoStep')?.value)     || 3;

  // ── VPM-B / VPM-B+GFS branch ──────────────────────────────────────
  const decoModelSel = document.getElementById('algorithmSelect')?.value || 'ZHLC_GF';
  if ((decoModelSel === 'VPMB' || decoModelSel === 'VPMB_GFS') && window.VPMEngine) {
    return runVPMSchedule(depthM, bt, descentRate, rate, decoRate, surfaceRate,
                          decoStep, lastStop, minStopT, ppo2Bottom, ppo2Deco,
                          decoModelSel, wholeMinStops);
  }
  // ── END VPM branch — Bühlmann continues below ─────────────────────

  const _ccrSettings = getCCRSettingsFromDOM();
  const _zhlOnLoop = isRebreatherCircuit(_ccrSettings.circuit) && !_ccrSettings.bailout;
  if (_ccrSettings.bailout) {
    _zhlPrevGF = { low: mGF.low, high: mGF.high };
    const boLo = _ccrSettings.bailoutGfLow ?? 50;
    const boHi = _ccrSettings.bailoutGfHigh ?? 85;
    mGF.low = boLo;
    mGF.high = boHi;
    gfL = boLo / 100;
    gfH = boHi / 100;
  }
  let bottomFN2, bottomFHe, bottomFO2, bottomMixLabel;
  let diveRuntimeMin = 0;
  function zhlLoadLinear(tissues, from, to, t, fO2, fHe, onLoop, phase) {
    if (onLoop) {
      const out = loadTissuesWithCCR(tissues, from, to, t, fO2, fHe, { ..._ccrSettings, scrRuntimeMin: diveRuntimeMin, ccrPhase: phase });
      diveRuntimeMin += t;
      return out;
    }
    return saturateLinear(tissues, from, to, t, Math.max(0, 1 - fO2 - fHe), fHe);
  }
  function zhlLoadConst(tissues, depth, t, fO2, fHe, onLoop, phase) {
    if (onLoop) {
      const out = loadTissuesWithCCR(tissues, depth, depth, t, fO2, fHe, { ..._ccrSettings, scrRuntimeMin: diveRuntimeMin, ccrPhase: phase });
      diveRuntimeMin += t;
      return out;
    }
    return saturate(tissues, depth, t, Math.max(0, 1 - fO2 - fHe), fHe);
  }

  // ── Bühlmann via Tier-3 unified core (OC + CCR) ───────────────────────
  // AUDIT-UNIT:UI-ZHL-RUNNER-ENGINE
  const { params: zhlParams, switchDisplays } = buildZhlScheduleParamsFromDom(rawD, depthM, bt);
  zhlParams.wholeMinStops = wholeMinStops;
  zhlParams.ccr = mergeCCRSettings(_ccrSettings);
  zhlParams.onLoop = _zhlOnLoop;
  if (_ccrSettings.bailout) {
    zhlParams.gfL = gfL;
    zhlParams.gfH = gfH;
  }
  applyZhlSwitchDepthDisplays(switchDisplays);
  const zhlCore = runZhlScheduleCore(zhlParams);
  const collapsed = zhlCore.collapsed;
  const collapsedMDP = zhlCore.collapsedMDP;
  const tissuesAtBottom = zhlCore.tissuesAtBottom;
  const tissues = zhlCore.lastPlan.finalTissues.map(t => ({ pN2: t.pN2, pHe: t.pHe || 0 }));
  const decoStops = zhlCore.decoStops;
  const decoTime = zhlCore.decoTime;
  const hasDeco = zhlCore.hasDeco;
  const gasUsed = zhlCore.gasUsed;
  const descentTime = zhlCore.descentTime;
  const trueDecoZoneStart = zhlCore.trueDecoZoneStart;
  let firstStopDepth = zhlCore.firstStopDepth;
  const gfAt = zhlCore.gfAt;
  bottomFN2 = zhlCore.bottomFN2;
  bottomFHe = zhlCore.bottomFHe;
  bottomFO2 = zhlCore.bottomFO2;
  bottomMixLabel = zhlCore.bottomMixLabel;
  const dU = zhlCore.dU;
  const loopMixLabel = loopMixLabelFor(bottomMixLabel, _ccrSettings);
  const runTimeMin = zhlCore.lastPlan.rt;
  const ttsMin = zhlCore.lastPlan.tts;
  const _headlessExposure = accumulateHeadlessPlanExposure(
    depthM, bt, descentRate, bottomFN2, bottomFHe, bottomFO2, _zhlOnLoop, collapsedMDP, _ccrSettings, zhlParams.repState
  );
  window._lastPlan = {
    ...zhlCore.lastPlan,
    totalOTU: _headlessExposure.totalOTU,
    totalCNS: _headlessExposure.totalCNS,
  };
  if (!_contingencyRunning && tissues && tissues.length) {
    saveZhlRepState(tissues, normalizeRepetitiveSurfaceIntervalInput('zhlSurfaceInterval', REP_SURFACE_INTERVAL_DEFAULT_MIN), { totalCNS: _headlessExposure.totalCNS, totalOTU: _headlessExposure.totalOTU });
    const zhlRepRow = document.getElementById('zhlRepRow');
    if (zhlRepRow) zhlRepRow.style.display = 'flex';
  }

  // ── Headless mode early return: skip ceiling/graph/DOM work ─────────────
  // Guard moved before ceiling waypoints — the intermediate saturate() calls
  // for graph smoothing are expensive and unnecessary in headless engine tests.
  if (window._zhlHeadless) return;

  // ── Store ceiling waypoints for graph overlay ──
  // Sample ceiling at finer resolution for smooth overlay line
  // Track ceiling from dive start (descent + bottom + deco ascent)
  {
    let ceilWps = [];

    // ── Phase 1: descent (0 → depthM over descentTime) ──
    {
      const descSteps = 8;
      let dTissues = initTissues();
      for (let di = 0; di <= descSteps; di++) {
        const frac = di / descSteps;
        const partDur = descentTime * frac;
        const partDepth = depthM * frac;
        const tis = di === 0 ? dTissues : (_zhlOnLoop
          ? zhlLoadLinear([...initTissues()], 0, partDepth, partDur, bottomFO2, bottomFHe, true)
          : saturateLinear([...initTissues()], 0, partDepth, partDur, bottomFN2, bottomFHe));
        const gf = gfAt ? gfAt(partDepth) : gfH;
        const ceilM = Math.max(0, ceiling(tis, gf));
        ceilWps.push({ t: partDur, ceil: ceilM });
      }
    }

    // ── Phase 2: bottom time (at depthM, descentTime → bt) ──
    {
      const btDuration = Math.max(0, bt - descentTime);
      const btSteps = Math.min(8, Math.max(2, Math.floor(btDuration)));
      let bTissues = [...tissuesAtBottom]; // end of bottom
      // Reconstruct intermediate bottom states (simplified: just record ceiling at start and end)
      const gfBottom = gfAt ? gfAt(depthM) : gfH;
      const btStartTis = _zhlOnLoop
        ? zhlLoadLinear([...initTissues()], 0, depthM, descentTime, bottomFO2, bottomFHe, true)
        : saturateLinear([...initTissues()], 0, depthM, descentTime, bottomFN2, bottomFHe);
      ceilWps.push({ t: descentTime, ceil: Math.max(0, ceiling(btStartTis, gfBottom)) });
      ceilWps.push({ t: bt, ceil: Math.max(0, ceiling(bTissues, gfBottom)) });
    }

    // ── Phase 3: deco ascent (from bt onward through collapsed steps) ──
    let cTissues2 = tissuesAtBottom ? [...tissuesAtBottom] : null;
    if (cTissues2) {
      let walkT = bt;
      for (const s of collapsed) {
        const gf = gfAt ? gfAt(s.type === 'ascent' ? s.to : (s.depth || 0)) : gfH;
        const ceilM = Math.max(0, ceiling(cTissues2, gf));
        ceilWps.push({ t: walkT, ceil: ceilM });
        // Intermediate samples for smoother line
        if (s.dur > 1.5) {
          const nSteps = Math.min(Math.floor(s.dur), 8);
          for (let si = 1; si < nSteps; si++) {
            const frac = si / nSteps;
            const partDur = s.dur * frac;
            const midTis = s.type === 'ascent'
              ? (_zhlOnLoop
                ? zhlLoadLinear([...cTissues2], s.from, s.to, partDur, bottomFO2, bottomFHe, true)
                : saturateLinear([...cTissues2], s.from, s.to, partDur, s.fN2 != null ? s.fN2 : bottomFN2, s.fHe !== undefined ? s.fHe : bottomFHe))
              : (_zhlOnLoop
                ? zhlLoadConst([...cTissues2], s.depth || 0, partDur, bottomFO2, bottomFHe, true)
                : saturate([...cTissues2], s.depth || 0, partDur, s.fN2 != null ? s.fN2 : bottomFN2, s.fHe !== undefined ? s.fHe : bottomFHe));
            const gfMid = gfAt ? gfAt(s.type === 'ascent' ? (s.from + (s.to - s.from) * frac) : (s.depth || 0)) : gfH;
            ceilWps.push({ t: walkT + partDur, ceil: Math.max(0, ceiling(midTis, gfMid)) });
          }
        }
        if (s.type === 'ascent') {
          cTissues2 = _zhlOnLoop
            ? zhlLoadLinear(cTissues2, s.from, s.to, s.dur, bottomFO2, bottomFHe, true)
            : saturateLinear(cTissues2, s.from, s.to, s.dur, s.fN2 != null ? s.fN2 : bottomFN2, s.fHe !== undefined ? s.fHe : bottomFHe);
        } else {
          cTissues2 = _zhlOnLoop
            ? zhlLoadConst(cTissues2, s.depth || 0, s.dur, bottomFO2, bottomFHe, true)
            : saturate(cTissues2, s.depth || 0, s.dur, s.fN2 != null ? s.fN2 : bottomFN2, s.fHe !== undefined ? s.fHe : bottomFHe);
        }
        walkT += s.dur;
      }
      ceilWps.push({ t: walkT, ceil: 0 }); // surface
    }

    // Sort by time (phases may have out-of-order due to descent reconstruction)
    ceilWps.sort((a, b) => a.t - b.t);
    window._decoCeilingWps = ceilWps;

    // Gas color segments: [{fromT, toT, gas, color}]
    // bt is run time including descent — deco phase starts at bt
    const gasColors = [_lspCssVar('--accent','#22d3ee'), _lspCssVar('--green','#4ade80'), _lspCssVar('--orange','#fbbf24'), _lspCssVar('--yellow','#fbbf24'), '#a78bfa', '#f472b6'];
    const gasColorMap = {};
    let gcIdx = 0;
    let gsT = bt;   // deco phase starts at bt (run time)
    const gasSegs = [];
    for (const s of collapsed) {
      if (!gasColorMap[s.gas]) { gasColorMap[s.gas] = gasColors[gcIdx++ % gasColors.length]; }
      gasSegs.push({ fromT: gsT, toT: gsT + s.dur, gas: s.gas, color: gasColorMap[s.gas] });
      gsT += s.dur;
    }
    // Prepend descent + bottom segment using bottom gas (covers 0 → bt)
    if (!gasColorMap[loopMixLabel]) { gasColorMap[loopMixLabel] = gasColors[gcIdx++ % gasColors.length]; }
    gasSegs.unshift({ fromT: 0, toT: bt, gas: loopMixLabel, color: gasColorMap[loopMixLabel] });
    window._decoGasSegments = gasSegs;
    window._decoGasColorMap = gasColorMap;
  }

  renderZhlScheduleResults({
    depthM, bt, rawD, descentRate,
    bottomFN2, bottomFHe, bottomFO2, bottomMixLabel,
    collapsedMDP, tissues, decoTime, hasDeco, firstStopDepth, trueDecoZoneStart,
    zhlCore, zhlOnLoop: _zhlOnLoop, ccrSettings: _ccrSettings, dU, loopMixLabel,
    ppo2Deco, ppo2Bottom,
  });

  // Tissue handled by updateTissueViz via tissueInlineCard

  if (!_contingencyRunning) {
    { const _tlc = document.getElementById('tissueLoadCard'); if (_tlc) _tlc.style.display = 'block'; }
    _syncGraphsSectionHeads();
    // Clear any VPM "N/A" notices from tissue/GF cards
    ['gfCurveInlineCard'].forEach(id => { // tissueInlineCard/tableCard merged into tissueLoadCard
      const el = document.getElementById(id);
      if (el) el.querySelectorAll('.info-box').forEach(n => { if (n.textContent.includes('N/A for VPM')) n.remove(); });
    });
    { const _cc = document.getElementById('contingencyCard'); if (_cc) _cc.style.display = 'block'; }
    const _fdgc = document.getElementById('fullDiveGraphCard'); if (_fdgc) _fdgc.style.display = 'block';
    buildContingencyButtons();
    { const _cr = document.getElementById('contingencyResult'); if (_cr) _cr.style.display = 'none'; }
    setTimeout(() => {
      if (isStaleDecoScheduleGen(scheduleGen)) return;
      setTimeout(() => { if (!isStaleDecoScheduleGen(scheduleGen)) { drawDecoProfileFull(); } }, 50);
    }, 100);
    setTimeout(() => {
      if (!isStaleDecoScheduleGen(scheduleGen)) {
        drawGFCurve();
        attachGFCurveInteraction();
      }
    }, 250);
    // Surface Interval panel (collapsed) — pre-fill Dive 1 from this dive
    renderSurfIntPanel('tecSurfIntContainer', 'tecSi', depthM, bt);
    if (!_contingencyRunning) renderTissueLoadChart();
    { const _tBtn=document.getElementById('tissueChartToggleBtn'); const _cBtn=document.getElementById('contingencyJumpBtn'); if(_tBtn)_tBtn.style.display='inline-block'; if(_cBtn)_cBtn.style.display='inline-block'; }
  }
  if (_zhlPrevGF) { mGF.low = _zhlPrevGF.low; mGF.high = _zhlPrevGF.high; }
  } catch(err) {
    if (_zhlPrevGF) { mGF.low = _zhlPrevGF.low; mGF.high = _zhlPrevGF.high; }
    if (_contingencyRunning) throw err;
    console.error('[Deco] Error:', err);
    const _ds = document.getElementById('decoSummary');
    if (_ds) _ds.innerHTML = `<div class="alert dang"><span>⚠</span><div><strong>Error:</strong> ${escapeHtmlText(err.message || String(err))}</div></div>`;
    const _dr2 = document.getElementById('decoResult');
    if (_dr2) _dr2.style.display = 'block';
  } finally {
    window._scheduleWorkerBusy = false;
  }
}

// Shared OTU/CNS integration from plan segments (headless harness + pSCR validation).
function planSegDepthM(seg) {
  if (seg.depth != null && isFinite(seg.depth)) return seg.depth;
  if (seg.endDepth != null && isFinite(seg.endDepth)) return seg.endDepth;
  if (seg.startDepth != null && seg.endDepth != null) return (seg.startDepth + seg.endDepth) / 2;
  if (seg.from != null && seg.to != null) return (seg.from + seg.to) / 2;
  if (seg.startDepth != null) return seg.startDepth;
  return 0;
}
function planSegDurationMin(seg) {
  return seg.time != null ? seg.time : (seg.dur || 0);
}
function planSegRunEndMin(seg) {
  return seg.run != null ? seg.run : (seg.runtime != null ? seg.runtime : 0);
}

function addExposureSample(otu, cnsFrac, ppO2, dur) {
  if (dur <= 0) return;
  if (ppO2 > 0.5) {
    otu.val += dur * Math.pow((ppO2 - 0.5) / 0.5, OTU_EXPONENT);
  }
  if (ppO2 < 0.6) return;
  const cnsLimits = { 6:720, 7:570, 8:450, 9:360, 10:300, 11:240, 12:210, 13:180, 14:150, 15:120, 16:45, 17:45 };
  const lo = Math.min(Math.floor(ppO2 * 10), 17);
  const hi = Math.min(lo + 1, 17);
  const lim = (cnsLimits[lo] || 0) + ((cnsLimits[hi] || 0) - (cnsLimits[lo] || 0)) * (ppO2 * 10 - lo);
  cnsFrac.val += dur / (lim > 0 ? lim : 45);
}

/** Headless Bühlmann OTU/CNS — build plan from collapsed steps and delegate to computePlanExposureTotals. */
function accumulateHeadlessPlanExposure(depthM, bt, descentRate, bottomFN2, bottomFHe, bottomFO2, onLoop, collapsedSteps, ccrSettings, repState) {
  const _pdCarry = window._priorDiveCarry;
  const _zhlRepSnap = repState || ((document.getElementById('zhlRepMode')?.checked && peekZhlRepState()) || null);
  let otuCarry = _pdCarry ? (_pdCarry.otuCarry || 0) : 0;
  let cnsCarry = _pdCarry ? (_pdCarry.cnsCarry || 0) : 0;
  if (_zhlRepSnap && !_pdCarry) {
    if (_zhlRepSnap.totalOTU != null) otuCarry = _zhlRepSnap.totalOTU;
    if (_zhlRepSnap.totalCNS != null) cnsCarry = _zhlRepSnap.totalCNS;
  }
  const descentTimeMin = depthM / descentRate;
  const btAtDepthMin = Math.max(0, bt - descentTimeMin);
  const o2pct = Math.round(bottomFO2 * 100);
  const hepct = Math.round((bottomFHe || 0) * 100);
  const gasLabel = (collapsedSteps && collapsedSteps[0] && collapsedSteps[0].gas) || 'bottom';
  const plan = [];
  let runAccum = 0;
  if (descentTimeMin > 0) {
    runAccum += descentTimeMin;
    plan.push({ type: 'descent', depth: depthM, time: descentTimeMin, run: runAccum, o2: o2pct, he: hepct, gas: gasLabel });
  }
  if (btAtDepthMin > 0) {
    runAccum += btAtDepthMin;
    plan.push({ type: 'bottom', depth: depthM, time: btAtDepthMin, run: runAccum, o2: o2pct, he: hepct, gas: gasLabel });
  }
  (collapsedSteps || []).forEach(s => {
    if (s.decoTransit) return; // mdCompatMode: transit folded into stop display
    const dur = typeof s.dur === 'number' ? s.dur : parseFloat(s.dur) || 0;
    if (dur <= 0) return;
    runAccum += dur;
    plan.push({
      type: s.type === 'deco' ? 'stop' : s.type,
      depth: s.type === 'ascent' ? s.to : s.depth,
      from: s.type === 'ascent' ? s.from : undefined,
      to: s.type === 'ascent' ? s.to : undefined,
      time: dur,
      run: Math.round(runAccum * 10) / 10,
      pO2: s.pO2,
      o2: Math.round((1 - (s.fN2 ?? bottomFN2) - (s.fHe ?? 0)) * 100),
      he: Math.round((s.fHe ?? 0) * 100),
      gas: s.gas,
    });
  });
  const exposure = computePlanExposureTotals(
    plan, ccrSettings || {}, bottomFO2, bottomFHe, altSurfaceP || 1.01325, BAR_PER_METRE || 0.1
  );
  return {
    totalOTU: Math.round(exposure.totalOTU + otuCarry),
    totalCNS: parseFloat((exposure.totalCNS + cnsCarry).toFixed(1)),
  };
}

function computePlanExposureTotals(plan, settings, defaultFO2, defaultFHe, surfP, barPerM) {
  const otu = { val: 0 }, cnsFrac = { val: 0 };
  const cfg = mergeCCRSettings(settings || {});
  function segFrac(val, fallback) {
    if (val == null) return fallback;
    return val > 1 ? val / 100 : val;
  }
  (plan || []).forEach(seg => {
    const dur = planSegDurationMin(seg);
    if (dur <= 0) return;
    const depth = planSegDepthM(seg);
    const fo2 = segFrac(seg.o2, defaultFO2);
    const fh = segFrac(seg.he, defaultFHe);
    const runEnd = planSegRunEndMin(seg);
    const runStart = Math.max(0, runEnd - dur);
    const pAmbBase = (surfP || altSurfaceP || 1.01325);
    const bar = barPerM || BAR_PER_METRE || 0.1;
    const onLoop = isRebreatherCircuit(cfg.circuit) && !cfg.bailout;
    const baked = seg.pO2 != null ? parseFloat(seg.pO2) : NaN;
    if (isFinite(baked) && baked > 0) {
      addExposureSample(otu, cnsFrac, baked, dur);
      return;
    }
    if (onLoop && cfg.circuit === 'pSCR') {
      const steps = Math.max(1, Math.min(Math.ceil(dur), 12));
      for (let i = 0; i < steps; i++) {
        const subDur = dur / steps;
        const frac = (i + 0.5) / steps;
        const rt = runStart + frac * dur;
        const d = seg.type === 'ascent' && seg.from != null && seg.to != null
          ? seg.from + (seg.to - seg.from) * frac : depth;
        const pAmb = pAmbBase + d * bar;
        const ppO2 = getEffectivePpo2(pAmb, 0, fo2, { ...cfg, scrRuntimeMin: rt, bailout: false }, d, fh);
        addExposureSample(otu, cnsFrac, ppO2, subDur);
      }
      return;
    }
    const pAmb = pAmbBase + depth * bar;
    let ppO2;
    if (onLoop && cfg.circuit === 'CCR') {
      const phase = seg.type === 'deco' || seg.type === 'stop' ? 'deco'
        : (seg.type === 'descent' ? 'descent' : (seg.type === 'bottom' ? 'bottom' : 'ascent'));
      const sp = getEffectiveSetpointAtDepth(depth, cfg, surfP || altSurfaceP, phase);
      ppO2 = getEffectivePpo2(pAmb, sp, fo2, cfg, depth, fh);
    } else {
      ppO2 = fo2 * pAmb;
    }
    addExposureSample(otu, cnsFrac, ppO2, dur);
  });
  return { totalOTU: Math.round(otu.val), totalCNS: parseFloat((cnsFrac.val * 100).toFixed(1)) };
}
if (typeof window !== 'undefined') window.computePlanExposureTotals = computePlanExposureTotals;

