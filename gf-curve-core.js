/**
 * GF curve visualizer and interaction.
 * Loaded by index.html after plot-core.
 * Globals read: setupHiDPI, _lspCssVar, getPlannerInputEl, units, mGF,
 *   ZHL16C, gfAdjustedMValue, altSurfaceP, BAR_PER_METRE, WATER_VAPOR, FN2_AIR.
 * Globals written: GF curve DOM only.
 */
// GF CURVE VISUALIZER
// ═══════════════════════════════════════════════

// AUDIT-UNIT:UI-TOOLS-GF
function drawGFCurve() {
  const canvas = document.getElementById('gfCurveCanvas');
  if (!canvas) return;
  const engine = window.LSPGraphEngine;
  const { ctx, W, H } = engine?.setupHiDPI ? engine.setupHiDPI(canvas) : setupHiDPI(canvas);
  const isMobile = W < 520;
  const PAD = engine?.plotPadding ? engine.plotPadding('gf', W, H) : { top: 10, right: 6, bottom: 28, left: 40 };
  const PW = W - PAD.left - PAD.right;
  const PH = H - PAD.top - PAD.bottom;

  ctx.clearRect(0, 0, W, H);

  const isLight  = document.body.classList.contains('light-theme');
  const monoFont  = isMobile ? '300 7.5px "JetBrains Mono",monospace'  : '300 10px "JetBrains Mono",monospace';
  const labelFont = isMobile ? '500 8px "JetBrains Mono",monospace'    : '600 11px "JetBrains Mono",monospace';
  const axisFont  = isMobile ? '300 7px "Outfit",sans-serif'           : '300 10.5px "Outfit",sans-serif';
  const dotRadius = isMobile ? 3.5 : 5.8;
  const palette = engine?.theme ? engine.theme(isLight) : null;
  const graphBg = palette?.bg ?? _lspCssVar('--surface-2', isLight ? '#f4f6fa' : '#0f1117');
  ctx.fillStyle  = graphBg;
  ctx.fillRect(0, 0, W, H);

  const textColor   = palette?.text ?? _lspCssVar('--text', isLight ? '#1a202c' : '#e2e8f0');
  const gridColor   = palette?.grid ?? (isLight ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.08)');
  const accentColor = palette?.accent ?? _lspCssVar('--accent', isLight ? '#0891b2' : '#22d3ee');
  const greenColor  = palette?.green ?? _lspCssVar('--green', isLight ? '#16a34a' : '#4ade80');
  const redColor    = palette?.red ?? _lspCssVar('--red', isLight ? '#dc2626' : '#f87171');
  const orangeColor = palette?.orange ?? _lspCssVar('--orange', isLight ? '#b45309' : '#fbbf24');

  // ── Read deco stops from table (depth in cells[1], stop time cells[2], data-phase) ──
  const stops = [];
  document.querySelectorAll('#decoTableBody tr[data-phase]').forEach(tr => {
    const phase = tr.dataset.phase;
    if (phase !== 'deco' && phase !== 'safety') return;
    const tds = tr.querySelectorAll('td');
    const depthTxt = tds[1]?.textContent?.trim() || '';
    const stopTxt  = tds[2]?.textContent?.trim() || '';
    const depth = parseFloat(depthTxt);
    const dur   = parseFloat(stopTxt);
    if (!isNaN(depth) && depth > 0) stops.push({ depth, dur, type: phase });
  });

  // Read bottom depth & GF settings
  const bottomDepth = parseFloat(getPlannerInputEl('decoDepth')?.value) || 40;
  const gfLow  = mGF.low  / 100;
  const gfHigh = mGF.high / 100;
  const firstStop = stops.filter(s => s.type === 'deco').reduce((max, s) => Math.max(max, s.depth), 0);

  // Update stats
  document.getElementById('gfCurveGFL').textContent = mGF.low;
  document.getElementById('gfCurveGFH').textContent = mGF.high;
  document.getElementById('gfCurveStops').textContent = stops.filter(s => s.type === 'deco').length || '—';

  const maxDepth = Math.max(bottomDepth, 10);
  const maxDepthY = maxDepth * (isMobile ? 1.01 : 1.03);

  function toX(gf)    { return PAD.left + (gf / 1.0) * PW; }
  function toY(depth) { return PAD.top  + (depth / maxDepthY) * PH; }

  // ── Grid lines ──
  ctx.lineWidth = 1;
  [0.2, 0.4, 0.6, 0.8, 1.0].forEach(gf => {
    ctx.strokeStyle = gridColor;
    ctx.beginPath(); ctx.moveTo(toX(gf), PAD.top); ctx.lineTo(toX(gf), PAD.top + PH); ctx.stroke();
    ctx.fillStyle = textColor; ctx.font = monoFont;
    // Right-align 100% so it doesn't clip at the canvas edge
    ctx.textAlign = gf === 1.0 ? 'right' : 'center';
    ctx.fillText(Math.round(gf * 100) + '%', toX(gf), PAD.top + PH + (isMobile ? 13 : 18));
  });
  const _gfDu = (typeof units !== 'undefined' && units === 'imperial') ? 'ft' : 'm';
  const depthTicks = [0, 5, 10, 15, 20, 25, 30, 35, 40, 50, 60].filter(d => d <= maxDepth);
  depthTicks.forEach(d => {
    ctx.strokeStyle = gridColor;
    ctx.beginPath(); ctx.moveTo(PAD.left, toY(d)); ctx.lineTo(PAD.left + PW, toY(d)); ctx.stroke();
    ctx.fillStyle = textColor; ctx.font = monoFont; ctx.textAlign = 'right';
    ctx.fillText(d + _gfDu, PAD.left - (isMobile ? 3 : 6), toY(d) + 3);
  });

  // ── Axis labels ──
  // Axis titles removed — card name and scale labels (m, %) are self-explanatory

  // ── GF Envelope line (dashed): GF Low at firstStop → GF High at surface ──
  ctx.beginPath();
  ctx.strokeStyle = accentColor;
  ctx.lineWidth = isMobile ? 1.7 : 2.4;
  ctx.setLineDash([6, 4]);
  if (firstStop > 0) {
    // From bottom to firstStop: vertical line at GF Low
    ctx.moveTo(toX(gfLow), toY(maxDepth));
    ctx.lineTo(toX(gfLow), toY(firstStop));
    // From firstStop to surface: diagonal GF Low → GF High
    ctx.lineTo(toX(gfHigh), toY(0));
  } else {
    // No deco — just show GF High line
    ctx.moveTo(toX(gfHigh), toY(maxDepth));
    ctx.lineTo(toX(gfHigh), toY(0));
  }
  ctx.stroke();
  ctx.setLineDash([]);

  // ── GF Low / High labels ──
  ctx.fillStyle = accentColor; ctx.font = labelFont;
  if (firstStop > 0) {
    ctx.textAlign = 'right';
    ctx.fillText('GFL ' + mGF.low + '%', toX(gfLow) - 4, toY(firstStop) + 14);
    ctx.textAlign = 'left';
    ctx.fillText('GFH ' + mGF.high + '%', toX(gfHigh) + 4, toY(0) + 14);
  } else {
    ctx.textAlign = 'left';
    ctx.fillText('GFH ' + mGF.high + '%', toX(gfHigh) + 4, toY(maxDepth / 2));
  }

  if (stops.length === 0) {
    // ── No deco data — placeholder ──
    ctx.fillStyle = textColor; ctx.font = axisFont; ctx.textAlign = 'center';
    ctx.globalAlpha = 0.45;
    ctx.fillText('Run a Bühlmann deco plan to see the GF curve', PAD.left + PW / 2, PAD.top + PH / 2 - 8);
    ctx.fillText('Switch to Deco Schedule tab and click CALCULATE', PAD.left + PW / 2, PAD.top + PH / 2 + 12);
    ctx.globalAlpha = 1;
    return;
  }

  // ── Dive profile line ──
  // Build waypoints: surface(0) → bottom → ascent through stops → surface
  const waypoints = [
    { depth: 0,           gf: gfHigh, label: null },
    { depth: bottomDepth, gf: gfLow,  label: '🔵 ' + bottomDepth + _gfDu },
  ];
  // Add deco stops (deepest first)
  const decoStops = stops.filter(s => s.type === 'deco').sort((a, b) => b.depth - a.depth);
  decoStops.forEach(s => {
    const gfAtStop = firstStop > 0
      ? gfLow + (gfHigh - gfLow) * (1 - s.depth / firstStop)
      : gfHigh;
    waypoints.push({ depth: s.depth, gf: gfAtStop, label: '🔴 ' + s.depth + _gfDu + ' / ' + s.dur + 'min', isDeco: true });
  });
  // Safety stop
  const safetySt = stops.find(s => s.type === 'safety');
  if (safetySt) waypoints.push({ depth: safetySt.depth, gf: gfHigh * 0.95, label: '🟢 ' + safetySt.depth + _gfDu, isSafety: true });
  waypoints.push({ depth: 0, gf: gfHigh, label: null });

  // Draw profile line
  ctx.beginPath();
  ctx.strokeStyle = greenColor;
    ctx.lineWidth = isMobile ? 1.7 : 2.4;
  waypoints.forEach((wp, i) => {
    i === 0 ? ctx.moveTo(toX(wp.gf), toY(wp.depth)) : ctx.lineTo(toX(wp.gf), toY(wp.depth));
  });
  ctx.stroke();

  // Draw dots and labels at stops
  const gfStops = waypoints.filter(wp => wp.label);
  gfStops.forEach((wp, i) => {
    const x = toX(wp.gf), y = toY(wp.depth);
    ctx.beginPath();
    ctx.arc(x, y, dotRadius, 0, Math.PI * 2);
    ctx.fillStyle = wp.isDeco ? redColor : wp.isSafety ? greenColor : accentColor;
    ctx.fill();
    ctx.strokeStyle = graphBg;
    ctx.lineWidth = 1.8; ctx.stroke();
    // Dot number
    ctx.fillStyle = graphBg;
    ctx.font = `600 ${isMobile ? 7 : 8}px "JetBrains Mono",monospace`;
    ctx.textAlign = 'center';
    ctx.fillText(i + 1, x, y + 3);
    // Label desktop only
    if (!isMobile) {
      ctx.fillStyle = textColor; ctx.font = labelFont;
      ctx.textAlign = 'right';
      const labelFmt = wp.label.replace(/(\d+m)\s+\/\s+(\d+)/, '$1 - $2');
      ctx.fillText((i+1) + '  ' + labelFmt, x - 7, y - 6);
    }
  });

  // Mobile legend
  const gfLegendEl = document.getElementById('gfCurveLegend');
  if (gfLegendEl) {
    if (isMobile && gfStops.length) {
      gfLegendEl.style.display = 'block';
      gfLegendEl.innerHTML = `<table style="width:100%;border-collapse:collapse;font-family:'JetBrains Mono',monospace;font-size:11px;margin:0;">
        <thead><tr style="border-bottom:1px solid var(--border);">
          <th style="padding:4px 6px;text-align:left;color:var(--muted);font-size:9px;letter-spacing:1px;text-transform:uppercase;">#</th>
          <th style="padding:4px 6px;text-align:left;color:var(--muted);font-size:9px;letter-spacing:1px;text-transform:uppercase;">Stop</th>
          <th style="padding:4px 6px;text-align:right;color:var(--muted);font-size:9px;letter-spacing:1px;text-transform:uppercase;">GF%</th>
        </tr></thead>
        <tbody>${gfStops.map((wp, i) => {
          const col = wp.isDeco ? redColor : wp.isSafety ? greenColor : accentColor;
          const labelFmt = wp.label.replace(/(\d+m)\s+\/\s+(\d+)/, '$1 - $2');
          const isLast = i === gfStops.length - 1;
          return `<tr${isLast ? '' : ' style="border-bottom:1px solid var(--border);"'}>
            <td style="padding:4px 6px;color:${col};font-weight:600;">${i+1}</td>
            <td style="padding:4px 6px;color:${col};">${labelFmt}</td>
            <td style="padding:4px 6px;text-align:right;color:var(--muted);">${Math.round(wp.gf*100)}%</td>
          </tr>`;
        }).join('')}</tbody>
      </table>`;
    } else {
      gfLegendEl.style.display = 'none';
    }
  }
}

// ═══════════════════════════════════════════════
// INTERACTIVE GRAPHS — hover/touch cursor
// ═══════════════════════════════════════════════


// ── GF Curve interactive ──
function attachGFCurveInteraction() {
  const canvasId = 'gfCurveCanvas';
  const overlay  = document.getElementById(canvasId + '-overlay');
  const tooltip  = document.getElementById(canvasId + '-tooltip');
  const crossV   = document.getElementById(canvasId + '-crosshair-v');
  const crossH   = document.getElementById(canvasId + '-crosshair-h');
  const canvas   = document.getElementById(canvasId);
  if (!overlay || !tooltip || !canvas) return;

  function getGFInfo(clientX, clientY) {
    const rect = canvas.getBoundingClientRect();
    const PAD  = { top: 24, right: 24, bottom: 48, left: 58 };
    const W = rect.width, H = rect.height;
    const PW = W - PAD.left - PAD.right;
    const PH = H - PAD.top  - PAD.bottom;

    const bottomDepth = parseFloat(getPlannerInputEl('decoDepth')?.value) || 40;
    const maxDepthY   = Math.max(bottomDepth, 10) * 1.08;

    const xPx = clientX - rect.left;
    const yPx = clientY - rect.top;

    const gf    = ((xPx - PAD.left) / PW);
    const depth = ((yPx - PAD.top)  / PH) * maxDepthY;

    if (gf < 0 || gf > 1 || depth < 0 || depth > maxDepthY) return null;

    // Find controlling tissue compartment at this depth with this GF
    const depthM  = units === 'imperial' ? depth / 3.28084 : depth;
    const pAmb    = altSurfaceP + depthM * BAR_PER_METRE;
    const pN2     = (pAmb - WATER_VAPOR) * FN2_AIR;
    let maxSat = 0, controlComp = 0;
    ZHL16C.forEach(([ht, a, b], i) => {
      const mv  = gfAdjustedMValue(a, b, pAmb, gf);
      const sat = pN2 / mv;
      if (sat > maxSat) { maxSat = sat; controlComp = i + 1; }
    });

    const du    = units === 'imperial' ? 'ft' : 'm';
    const dDisp = units === 'imperial' ? Math.round(depth) : Math.round(depth * 10) / 10;
    const gfLowLine  = mGF.low  / 100;
    const gfHighLine = mGF.high / 100;
    const inEnvelope = gf >= Math.min(gfLowLine, gfHighLine) && gf <= Math.max(gfLowLine, gfHighLine);

    return { gf, depth: dDisp, du, controlComp, maxSat, inEnvelope, cx: xPx, cy: yPx };
  }

  function showGFTooltip(clientX, clientY) {
    const info = getGFInfo(clientX, clientY);
    if (!info) { hideGFTooltip(); return; }
    const { gf, depth, du, controlComp, maxSat, inEnvelope, cx, cy } = info;
    const rect = canvas.getBoundingClientRect();
    const satPct = Math.round(maxSat * 100);
    const satCol = satPct >= 100 ? 'var(--red)' : satPct >= 85 ? 'var(--orange)' : satPct >= 70 ? 'var(--yellow)' : 'var(--green)';

    let html = `<div style="color:var(--accent);font-size:10px;letter-spacing:1px;margin-bottom:4px;">GF CURVE</div>`;
    html += `<div>GF: <strong>${Math.round(gf * 100)}%</strong></div>`;
    html += `<div>Depth: <strong>${depth} ${du}</strong></div>`;
    html += `<div>Ctrl. comp: <strong>C${controlComp}</strong></div>`;
    html += `<div>Sat: <strong style="color:${satCol}">${satPct}%</strong></div>`;
    if (inEnvelope) html += `<div style="color:var(--green);font-size:10px;">- in GF envelope</div>`;

    tooltip.innerHTML = html;
    tooltip.style.display = 'block';
    const W = rect.width, H = rect.height;
    let tx = cx + 14, ty = cy - 10;
    if (tx + 170 > W) tx = cx - 175;
    if (ty < 0) ty = cy + 12;
    if (ty + 130 > H) ty = H - 135;
    tooltip.style.left = tx + 'px';
    tooltip.style.top  = ty + 'px';
    crossV.style.display = 'block'; crossV.style.left = cx + 'px';
    crossH.style.display = 'block'; crossH.style.top  = cy + 'px';
  }

  function hideGFTooltip() {
    tooltip.style.display = 'none';
    crossV.style.display  = 'none';
    crossH.style.display  = 'none';
  }

  const newOverlay = overlay.cloneNode(true);
  overlay.parentNode.replaceChild(newOverlay, overlay);
  newOverlay.addEventListener('mousemove',  e => showGFTooltip(e.clientX, e.clientY));
  newOverlay.addEventListener('mouseleave', hideGFTooltip);
  newOverlay.addEventListener('touchmove',  e => {
    e.preventDefault();
    showGFTooltip(e.touches[0].clientX, e.touches[0].clientY);
  }, { passive: false });
  newOverlay.addEventListener('touchend', hideGFTooltip);
}

// ═══════════════════════════════════════════════
