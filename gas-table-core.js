/**
 * Gas table / END / EAD reference — RUNTIME UI CORE.
 * Loaded by index.html before main inline script.
 * Globals read: units, altSurfaceP, BAR_PER_METRE, narcoticN2, narcoticO2, calcEND,
 *   calcGasMODm
 * Globals written: window._endTipTitle, window._endTipText, window._eadTipTitle,
 *   window._eadTipText, window._avgDepthTipTitle, window._avgDepthTipText
 */

// ═══════════════════════════════════════════════
// GAS TABLE — MOD / MND reference for common mixes
// ═══════════════════════════════════════════════
const _endTipTitle = 'Equivalent Narcotic Depth (END)';
window._endTipTitle = _endTipTitle;
const _endTipText  =
`What is END?
END (Equivalent Narcotic Depth) expresses the narcotic effect of a breathing gas as the depth at which breathing air would feel equally narcotic. A lower END means less impairment at the same actual depth.

What causes narcosis?
Nitrogen is narcotic at partial pressures above ~3 bar (roughly 20 m on air). Oxygen is also considered narcotic by most models. Helium is NOT narcotic — adding He to a mix reduces narcosis proportionally.

Formula (N₂ + O₂ narcotic model)
pNarc = ppN₂ + ppO₂ at depth
END = (pNarc / pNarc_air_surface) × 10 − 10

Narcosis risk levels
≤ 30 m END → Low  — mild, manageable for most divers
31–40 m END → Moderate — noticeable impairment, increased caution
41–50 m END → High — significant impairment, trimix recommended
> 50 m END → Severe — professional tec divers with helium only

Practical guidance
Most recreational agencies recommend keeping END ≤ 30 m. Technical divers typically plan for END ≤ 30–35 m even on deep trimix dives. Exertion, cold, stress, and CO₂ build-up can all worsen narcosis beyond what END predicts.`;
window._endTipText = _endTipText;

function calcEND_tool() {
  const du     = units === 'metric';
  const dUnit  = du ? 'm' : 'ft';
  const dRaw   = parseFloat(document.getElementById('endDepth')?.value) || 30;
  const dM     = du ? dRaw : dRaw / 3.28084;
  const o2Pct  = parseFloat(document.getElementById('endO2')?.value) || 21;
  const hePct  = parseFloat(document.getElementById('endHe')?.value) || 0;
  const n2Pct  = 100 - o2Pct - hePct;

  // Mix validity
  const warnEl = document.getElementById('endMixWarn');
  if (n2Pct < 0) {
    warnEl.style.display = 'block';
    warnEl.innerHTML = '<div class="alert dang"><span>\u26a0</span><div>O\u2082% + He% exceeds 100%. Adjust mix.</div></div>';
    document.getElementById('endResults').style.opacity = '0.3';
    return;
  }
  warnEl.style.display = 'none';
  document.getElementById('endResults').style.opacity = '1';

  const fO2  = o2Pct / 100;
  const fHe  = hePct / 100;
  const fN2  = n2Pct / 100;

  const surfP = altSurfaceP || 1.01325;
  const ppO2Surf = fO2 * surfP;
  if (ppO2Surf < 0.16) {
    warnEl.style.display = 'block';
    warnEl.innerHTML = '<div class="alert dang"><span>\u26a0</span><div><strong>Hypoxic mix.</strong> ppO\u2082 at surface is ' +
      ppO2Surf.toFixed(2) + ' bar (&lt; 0.16 bar). Do not breathe this gas.</div></div>';
    document.getElementById('endResults').style.opacity = '0.3';
    return;
  }

  const pAmb = surfP + dM * (BAR_PER_METRE || 0.1);
  const ppN2 = fN2 * pAmb;
  const ppO2 = fO2 * pAmb;
  const ppHe = fHe * pAmb;

  // Narcotic partial pressure — respect narcoticN2/narcoticO2 settings (He non-narcotic)
  const pNarc = (narcoticN2 ? ppN2 : 0) + (narcoticO2 ? ppO2 : 0);

  // Use shared calcEND() — handles altitude, narcotic toggles, and He correctly
  const endM    = calcEND(dM, fN2, fHe);
  const endDisp = du ? Math.round(endM) + ' m' : Math.round(endM * 3.28084) + ' ft';

  // Risk level
  let riskLabel, riskCol;
  if (endM <= 30)      { riskLabel = 'Low';      riskCol = 'var(--green)'; }
  else if (endM <= 40) { riskLabel = 'Moderate'; riskCol = 'var(--yellow)'; }
  else if (endM <= 50) { riskLabel = 'High';     riskCol = 'var(--orange)'; }
  else                 { riskLabel = 'Severe';   riskCol = 'var(--red)'; }

  // MOD
  const ppO2Limit = parseFloat(document.getElementById('ppo2Bottom')?.value) || 1.4;
  const mod14M = fO2 > 0 ? calcGasMODm(fO2, ppO2Limit) : null;
  const mod16M = fO2 > 0 ? calcGasMODm(fO2, 1.6) : null;
  const mod14d = mod14M != null ? (du ? mod14M + ' m' : Math.round(mod14M * 3.28084) + ' ft') : '\u2014';
  const mod16d = mod16M != null ? (du ? mod16M + ' m' : Math.round(mod16M * 3.28084) + ' ft') : '\u2014';

  // Mix name
  const mixName = hePct > 0
    ? o2Pct + '/' + hePct
    : (o2Pct === 21 ? 'Air' : 'EAN' + o2Pct);

  // Depth display label sync
  document.getElementById('endDepthDisplay').textContent = (du ? dRaw : dRaw) + (du ? ' m' : ' ft');

  // Update UI
  document.getElementById('endResult').textContent    = endDisp;
  document.getElementById('endResult').style.color    = riskCol;
  document.getElementById('endRisk').textContent      = riskLabel;
  document.getElementById('endRisk').style.color      = riskCol;
  document.getElementById('endNarcLoad').textContent  = pNarc.toFixed(2) + ' bar';
  document.getElementById('endAbsP').textContent      = pAmb.toFixed(2) + ' bar';
  document.getElementById('endPPN2').textContent      = ppN2.toFixed(2) + ' bar';
  document.getElementById('endPPO2').textContent      = ppO2.toFixed(2) + ' bar';
  document.getElementById('endPPHe').textContent      = ppHe.toFixed(2) + ' bar';
  document.getElementById('endMixName').textContent   = mixName;
  document.getElementById('endMOD14').textContent     = mod14d;
  document.getElementById('endMOD16').textContent     = mod16d;
  const mod14Lbl = document.getElementById('endMOD14')?.closest('.stat')?.querySelector('.stat-lbl');
  if (mod14Lbl) mod14Lbl.textContent = 'MOD @ ' + ppO2Limit.toFixed(1);

  // Alert banner
  const alertEl = document.getElementById('endAlert');
  let alertHtml = '';
  if (endM > 50) {
    alertHtml = `<div class="alert" style="background:#FF4433;border-color:#111;border-width:1px;color:#fff;font-weight:700;"><span>\u26a0</span><div><strong>SEVERE NARCOSIS.</strong> END ${endDisp} \u2014 consider adding helium.</div></div>`;
  } else if (endM > 40) {
    alertHtml = `<div class="alert" style="background:#FF4433;border-color:#111;border-width:1px;color:#fff;font-weight:700;"><span>\u26a0</span><div><strong>HIGH NARCOTIC DEPTH.</strong> END ${endDisp} exceeds 40 m equivalent.</div></div>`;
  } else if (endM > 30) {
    alertHtml = `<div class="alert" style="background:#FF4433;border-color:#111;border-width:1px;color:#fff;font-weight:700;"><span>\u26a0</span><div><strong>NARCOTIC DEPTH WARNING.</strong> END ${endDisp} exceeds 30 m equivalent.</div></div>`;
  }
  if (mod14M != null && dM > mod14M) {
    alertHtml += `<div class="alert dang" style="margin-top:6px;"><span>\u26a0</span><div><strong>EXCEEDS MOD.</strong> Depth ${du ? Math.round(dM)+' m' : Math.round(dM*3.28084)+' ft'} is deeper than MOD ${mod14d} at ppO\u2082 ${ppO2Limit.toFixed(1)}.</div></div>`;
  }
  alertEl.innerHTML = alertHtml;
}

const _eadTipTitle = 'Equivalent Air Depth (EAD)';
window._eadTipTitle = _eadTipTitle;
const _eadTipText  =
`What is EAD?
EAD (Equivalent Air Depth) is the depth at which air would have the same partial pressure of nitrogen as your nitrox mix at the actual depth. Because nitrox has less N₂ than air, EAD is always shallower — meaning you absorb nitrogen as if you were at a shallower depth.

Why does EAD matter?
Standard air NDL tables and dive computers set to "air" mode were designed for 79% N₂. When diving nitrox, you can look up your EAD in standard tables to get longer no-deco limits safely.

Formula
EAD = ((1 − fO₂) × (depth + 10) / 0.79) − 10
where fO₂ is the oxygen fraction and depth is in metres.

Example
Diving EAN32 to 30 m:
fN₂ = 0.68, pAmb = 4 bar
EAD = (0.68 × 40 / 0.79) − 10 = 24.4 m
→ Use the 24 m air NDL instead of 30 m.

Limits
EAD only addresses nitrogen narcosis and NDL. You must still respect the ppO₂ MOD for your mix — nitrox does not reduce oxygen toxicity risk.`;
window._eadTipText = _eadTipText;

const _avgDepthTipTitle = 'Why Not Just Use Max Depth?';
window._avgDepthTipTitle = _avgDepthTipTitle;
const _avgDepthTipText =
`Using max depth is conservative but over-penalises multi-level dives.

Example: a 40 m dive where you spent only 3 min at depth and the rest at 15 m. RDP tables penalise you as if you stayed at 40 m the entire dive — making surface intervals unnecessarily long.

Planning Depth Formula
avg + 75% × (max − avg)

This widely used approximation acknowledges the brief time at max depth without ignoring it. It gives a planning depth between your average and max, weighted toward the max.

Always validate against your dive computer's actual tissue loading — especially for repetitive dives, where fast compartments are driven by your actual maximum depth, not the average.`;
window._avgDepthTipText = _avgDepthTipText;

function renderEADTable() {
  const table = document.getElementById('eadRefTable');
  if (!table) return;
  const du = units === 'metric';
  const toDisp = m => du ? m.toFixed(1) + ' m' : (m * 3.28084).toFixed(1) + ' ft';
  const depthLabel = m => du ? m + ' m' : Math.round(m * 3.28084) + ' ft';

  const depths = [12,14,16,18,20,22,24,26,28,30,32,34,36,38];
  const mixes  = Array.from({length:19}, (_, i) => 22 + i); // 22..40

  // Header row
  let html = '<thead><tr style="border-bottom:1px solid var(--border);">' +
    '<th style="text-align:left;padding:5px 6px;font-size:9px;letter-spacing:2px;text-transform:uppercase;color:var(--muted);font-weight:400;white-space:nowrap;">Mix</th>';
  depths.forEach(d => {
    html += `<th style="text-align:right;padding:5px 4px;font-size:9px;letter-spacing:1px;text-transform:uppercase;color:var(--muted);font-weight:400;white-space:nowrap;">${depthLabel(d)}</th>`;
  });
  html += '</tr></thead><tbody>';

  // Data rows
  mixes.forEach(o2pct => {
    const fO2 = o2pct / 100;
    const fN2 = 1 - fO2;
    const o2Col = o2pct >= 32 ? 'var(--green)' : o2pct >= 22 ? 'var(--accent)' : 'var(--muted)';
    html += `<tr class="bmt-ref-row"><td style="color:${o2Col};font-weight:600;white-space:nowrap;">EAN${o2pct}</td>`;
    depths.forEach(dM => {
      const ead = calcEND(dM, fN2, 0);
      const eadDisp = ead == null ? '—' : Math.max(0, ead);
      html += `<td style="text-align:right;padding:5px 4px;color:var(--muted);white-space:nowrap;">${toDisp(eadDisp)}</td>`;
    });
    html += '</tr>';
  });

  html += '</tbody>';
  table.innerHTML = html;
}

function renderGasTable() {
  const body = document.getElementById('gasTableBody');
  if (!body) return;
  const dU   = units === 'metric';
  const conv = dU ? 1 : 3.28084;
  const uLbl = dU ? 'm' : 'ft';
  const selPpo2 = (parseFloat(document.getElementById('gasTablePPO2')?.value) || 14) / 10;
  const hdr = document.getElementById('gasTableModSelHdr');
  if (hdr) hdr.textContent = 'MOD @ ' + selPpo2.toFixed(1);

  // [label, fO2, fHe]
  const gases = [
    ['Air',    0.21, 0],
    ['EAN32',  0.32, 0],
    ['EAN36',  0.36, 0],
    ['EAN40',  0.40, 0],
    ['EAN50',  0.50, 0],
    ['100% O₂',1.00, 0],
    ['21/35',  0.21, 0.35],
    ['18/45',  0.18, 0.45],
    ['15/55',  0.15, 0.55],
  ];

  const fmtDepth = (mVal) => {
    if (mVal < 0) return '—';
    const v = dU ? Math.floor(mVal) : Math.floor(mVal * conv);
    return v + ' ' + uLbl;
  };

  // MOD (m) = (ppO2 / fO2 - altSurfaceP) / BAR_PER_METRE
  const modM = (fO2, ppo2) => calcGasMODm(fO2, ppo2);
  // MND: END = 3.5 bar. fNarc = fO2 + fN2 (He non-narcotic). MND = (3.5/fNarc - altP)/BAR_PER_METRE
  const mndM = (fO2, fHe) => {
    const fN2 = Math.max(0, 1 - fO2 - (fHe || 0));
    const fH = fHe || 0;
    const fO2n = Math.max(0, 1 - fN2 - fH);
    const narcFrac = (narcoticN2 ? fN2 : 0) + (narcoticO2 ? fO2n : 0);
    if (narcFrac <= 0) return -1;
    const pAmbTarget = 3.5 / narcFrac;
    if (pAmbTarget <= altSurfaceP) return -1;
    return (pAmbTarget - altSurfaceP) / BAR_PER_METRE;
  };

  body.innerHTML = '';
  gases.forEach(([label, fO2, fHe]) => {
    const m1   = modM(fO2, selPpo2);
    const m16  = modM(fO2, 1.6);
    const mnd  = mndM(fO2, fHe);
    const col1  = m1  < 20 ? 'var(--red)' : m1  < 30 ? 'var(--yellow)' : 'var(--accent)';
    const col16 = m16 < 20 ? 'var(--red)' : m16 < 30 ? 'var(--yellow)' : 'var(--accent)';
    const mndCol = (mnd >= 0 && mnd < 30) ? 'var(--yellow)' : 'var(--muted)';
    body.innerHTML += `<tr data-phase="gas">
      <td style="text-align:left;font-weight:700;">${label}</td>
      <td data-label="MOD @ ${selPpo2.toFixed(1)}" style="color:${col1};">${fmtDepth(m1)}</td>
      <td data-label="MOD @ 1.6" style="color:${col16};">${fmtDepth(m16)}</td>
      <td data-label="MND" style="color:${mndCol};">${fmtDepth(mnd)}</td>
    </tr>`;
  });
}
