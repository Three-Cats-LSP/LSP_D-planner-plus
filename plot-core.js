/**
 * Dive profile graph â€” canvas render, waypoints, zoom/pan interaction.
 * Loaded by index.html before main inline script.
 * Globals read: units, document, window._decoGasSegments, window._decoCeilingWps,
 *   _lspCssVar, _syncGraphsSectionHeads, scheduleDecoScheduleStackSync (indirect)
 * Globals written: window._decoWaypoints, window._plannerWaypoints, window._plannerGasSegments,
 *   window._plannerGasColorMap, window._plannerCeilingWps, _graphZoom, _graphOpts
 */

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// DIVE PROFILE GRAPH
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

// â”€â”€â”€ HiDPI canvas setup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function setupHiDPI(canvas) {
  return window.LSPGraphEngine?.setupHiDPI
    ? window.LSPGraphEngine.setupHiDPI(canvas)
    : { ctx: canvas.getContext('2d'), W: +canvas.width, H: +canvas.height };
}

// â”€â”€ Graph zoom/pan state â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const _graphZoom = {}; // canvasId â†’ { tMin, tMax, dMin, dMax }

const _profileDrawQueue = {};

function scheduleProfileDraw(key, drawFn, isStale) {
  if (typeof drawFn !== 'function') return;
  if (_profileDrawQueue[key]) cancelAnimationFrame(_profileDrawQueue[key]);
  _profileDrawQueue[key] = requestAnimationFrame(() => {
    _profileDrawQueue[key] = requestAnimationFrame(() => {
      delete _profileDrawQueue[key];
      if (typeof isStale === 'function' && isStale()) return;
      drawFn();
    });
  });
}

function schedulePlannerProfileDraw() {
  scheduleProfileDraw('planner-profile', () => drawPlannerProfile());
}

function scheduleDecoProfileFullDraw(isStale) {
  scheduleProfileDraw('deco-profile-full', () => drawDecoProfileFull(), isStale);
}

function scheduleGfCurveDraw(isStale) {
  scheduleProfileDraw('gf-curve', () => {
    if (typeof isStale === 'function' && isStale()) return;
    drawGFCurve?.();
    attachGFCurveInteraction?.();
  });
}

function _graphZoomReset(canvasId) {
  delete _graphZoom[canvasId];
}

function _graphZoomApply(canvasId, data) {
  _graphZoom[canvasId] = data;
  // Brighten the hint when zoomed
  if (canvasId === 'decoProfileCanvas') {
    const hint = document.getElementById('decoProfileCanvas-hint');
    if (hint) hint.style.opacity = data ? '0.85' : '0.55';
  }
  if (canvasId === 'plannerProfileCanvas') {
    const hint = document.getElementById('plannerProfileCanvas-hint');
    if (hint) hint.style.opacity = data ? '0.85' : '0.55';
  }
}

function _profileLegendDepthLabel(depthM) {
  if (units === 'imperial') return Math.round(depthM * 3.28084) + 'ft';
  const d = Math.round(depthM * 10) / 10;
  return (d % 1 === 0 ? d.toFixed(0) : d.toFixed(1)) + 'm';
}

function _buildProfileLegendTableRows(waypoints, colors) {
  const { red, green, accent } = colors;
  const rows = [];
  let stopNum = 0;
  [...waypoints].sort((a, b) => a.t - b.t).forEach(wp => {
    if (wp.type === 'gasswitch') {
      const gas = String(wp.gasLabel || '').replace(/\s+/g, ' ').trim();
      const depthTxt = wp.depthLabel || _profileLegendDepthLabel(wp.depth || 0);
      rows.push({
        kind: 'gasswitch',
        num: 'â‡„',
        stop: `${depthTxt}${gas ? ' Â· ' + gas : ''}`,
        run: Math.round(wp.t * 10) / 10,
        ppo2: wp.ppo2,
        color: 'var(--gas-switch)',
      });
      return;
    }
    if (!wp.dot || !wp.label) return;
    stopNum += 1;
    const dotColor = wp.type === 'deco' ? red : wp.type === 'safety' ? green : accent;
    rows.push({
      kind: wp.type,
      num: stopNum,
      stop: wp.label.replace(/(\d+m)\s+(\d+)/, '$1 - $2'),
      run: Math.round(wp.t * 10) / 10,
      ppo2: wp.ppo2,
      color: dotColor,
    });
  });
  return rows;
}

function _renderProfileLegendTableHtml(rows, colors) {
  const { red, orange, muted } = colors;
  return `<table class="profile-legend-table" style="width:100%;border-collapse:collapse;font-family:var(--font-mono);font-size:11px;margin-top:8px;">
    <thead><tr style="border-bottom:1px solid var(--border);">
      <th style="padding:5px 6px;text-align:left;color:var(--muted);font-size:9px;letter-spacing:1px;text-transform:uppercase;">#</th>
      <th style="padding:5px 6px;text-align:left;color:var(--muted);font-size:9px;letter-spacing:1px;text-transform:uppercase;">Stop</th>
      <th style="padding:5px 6px;text-align:right;color:var(--muted);font-size:9px;letter-spacing:1px;text-transform:uppercase;">Run</th>
      <th style="padding:5px 6px;text-align:right;color:var(--muted);font-size:9px;letter-spacing:1px;text-transform:uppercase;">ppOâ‚‚</th>
    </tr></thead>
    <tbody>${rows.map(row => {
      const pColor = row.ppo2 >= 1.6 ? red : row.ppo2 >= 1.4 ? orange : muted;
      const rowCls = row.kind === 'gasswitch' ? ' class="profile-legend-gasswitch"' : '';
      const rowBg = ' style="border-bottom:1px solid var(--border);"';
      return `<tr${rowCls}${rowBg}>
        <td style="padding:5px 6px;color:${row.color};font-weight:600;">${row.num}</td>
        <td style="padding:5px 6px;color:${row.color};">${row.stop}</td>
        <td style="padding:5px 6px;text-align:right;color:var(--muted);">${row.run} min</td>
        <td style="padding:5px 6px;text-align:right;color:${row.ppo2 != null ? pColor : 'var(--muted)'};">${row.ppo2 != null ? row.ppo2.toFixed(2) : '—'}</td>
      </tr>`;
    }).join('')}</tbody>
  </table>`;
}

// AUDIT-UNIT:UI-PLOT-RENDER
function _drawDiveProfileCore(canvasId, waypoints, opts) {
  // waypoints: [{t, depth, type, label, ppo2, cns}]
  // opts: { maxDepth, totalTime, isLight, simple }
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const simple = opts?.simple === true && canvasId === 'decoProfileCanvas';
  const engine = window.LSPGraphEngine;
  const { ctx, W, H } = engine?.setupHiDPI ? engine.setupHiDPI(canvas) : setupHiDPI(canvas);
  const isMobile  = W < 520;
  const PAD = engine?.plotPadding ? engine.plotPadding('profile', W, H) : { top: 10, right: 6, bottom: 28, left: 40 };
  const PW = W - PAD.left - PAD.right;
  const PH = H - PAD.top - PAD.bottom;

  ctx.clearRect(0, 0, W, H);

  const isLight   = opts?.isLight ?? document.body.classList.contains('light-theme');
  const _isMob    = W < 520;
  const rawMaxDepth  = (opts?.maxDepth || 10) * (_isMob ? 1.02 : 1.04);
  const rawTotalTime = opts?.totalTime || 60;
  // â”€â”€ Zoom state â”€â”€
  const zoom = _graphZoom[canvasId];
  const tMin = zoom ? zoom.tMin : 0;
  const tMax = zoom ? zoom.tMax : rawTotalTime;
  const dMin = zoom ? zoom.dMin : 0;
  const dMax = zoom ? zoom.dMax : rawMaxDepth;
  const totalTime = tMax - tMin;
  const maxDepth  = dMax - dMin;

  const monoFont  = isMobile ? '300 7px "JetBrains Mono",monospace'  : '300 9px "JetBrains Mono",monospace';
  const labelFont = isMobile ? '300 7px "JetBrains Mono",monospace'  : '500 10px "JetBrains Mono",monospace';
  const axisFont  = isMobile ? '300 6.5px "Outfit",sans-serif'        : '300 9px "Outfit",sans-serif';
  const dotRadius  = isMobile ? 3 : 5;
  const haloRadius = isMobile ? 5 : 8;
  // (PAD already set above before PW/PH computation)

  const palette = engine?.theme ? engine.theme(isLight) : null;
  const bg      = palette?.bg ?? _lspCssVar('--surface-2', isLight ? '#f4f6fa' : '#0e0f11');
  const grid    = palette?.grid ?? (isLight ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.08)');
  const text    = palette?.text ?? _lspCssVar('--text', isLight ? '#1a202c' : '#e2e8f0');
  const muted   = palette?.muted ?? _lspCssVar('--text-muted', isLight ? '#4a5568' : '#8892a4');
  const accent  = palette?.accent ?? _lspCssVar('--accent', isLight ? '#0891b2' : '#22d3ee');
  const red     = palette?.red ?? _lspCssVar('--red', isLight ? '#dc2626' : '#f87171');
  const green   = palette?.green ?? _lspCssVar('--green', isLight ? '#16a34a' : '#4ade80');
  const orange  = palette?.orange ?? _lspCssVar('--orange', isLight ? '#b45309' : '#fbbf24');
  const gasSwitchLine = palette?.gasSwitchLine ?? _lspCssVar('--gas-switch-guide', '#16a34a');
  const gasSwitchBg = palette?.gasSwitchBg ?? '#d6ff00';
  const gasSwitchText = palette?.gasSwitchText ?? gasSwitchLine;
  const profileLine = accent;

  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, W, H);

  function toX(t)     { return PAD.left + ((t - tMin) / totalTime) * PW; }
  function toY(depth) { return PAD.top  + ((depth - dMin) / maxDepth) * PH; }

  // Helper: set a clip to the plot area (call ctx.save() before, ctx.restore() after)
  function clipToPlot() {
    ctx.beginPath();
    ctx.rect(PAD.left, PAD.top, PW, PH);
    ctx.clip();
  }

  // â”€â”€ Grid â”€â”€
  const depStep = isMobile
    ? (maxDepth > 40 ? 10 : 5)
    : (maxDepth > 80 ? 20 : 10);
  const _du = (typeof units !== 'undefined' && units === 'imperial') ? 'ft' : 'm';
  for (let d = Math.ceil(dMin / depStep) * depStep; d <= dMax; d += depStep) {
    const y = toY(d);
    ctx.strokeStyle = grid; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(PAD.left, y); ctx.lineTo(PAD.left + PW, y); ctx.stroke();
    ctx.fillStyle = muted; ctx.font = monoFont; ctx.textAlign = 'right';
    if (d > 0) ctx.fillText(d + _du, PAD.left - 2, y + 3);
  }
  const rawTimeStep = isMobile
    ? (totalTime > 60 ? 15 : totalTime > 30 ? 10 : 5)
    : (totalTime > 120 ? 20 : totalTime > 60 ? 10 : 5);
  const minPxBetween = isMobile ? 40 : 50;
  const pxPerStep = (PW / totalTime) * rawTimeStep;
  const timeStep = pxPerStep < minPxBetween ? rawTimeStep * Math.ceil(minPxBetween / pxPerStep) : rawTimeStep;
  for (let t = Math.ceil(tMin / timeStep) * timeStep; t <= tMax; t += timeStep) {
    const x = toX(t);
    ctx.strokeStyle = grid; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(x, PAD.top); ctx.lineTo(x, PAD.top + PH); ctx.stroke();
    ctx.fillStyle = muted; ctx.font = monoFont; ctx.textAlign = 'center';
    ctx.fillText(t + 'min', x, PAD.top + PH + (isMobile ? 11 : 18));
  }

  // â”€â”€ Axes â”€â”€
  ctx.strokeStyle = isLight ? 'rgba(0,0,0,0.2)' : 'rgba(255,255,255,0.15)';
  ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(PAD.left, PAD.top); ctx.lineTo(PAD.left, PAD.top + PH); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(PAD.left, PAD.top + PH); ctx.lineTo(PAD.left + PW, PAD.top + PH); ctx.stroke();

  // â”€â”€ Deco zone shading removed â€” gas fills + deco staircase are sufficient â”€â”€
  // (decoStops[0] reference kept for audit)
  if (!simple) {
  ctx.save(); clipToPlot();
  const decoStops = waypoints.filter(wp => wp.type === 'deco' || wp.type === 'safety');
  void decoStops[0]; // audit anchor
  // Individual stop horizontal dashed lines (depth indicators)
  waypoints.forEach((wp, i) => {
    if (wp.type !== 'deco' && wp.type !== 'safety') return;
    const next = waypoints[i + 1];
    if (!next) return;
    const x1 = toX(wp.t), x2 = toX(next.t);
    const y  = toY(wp.depth);
    ctx.strokeStyle = wp.type === 'deco' ? red : green;
    ctx.lineWidth = 1;
    ctx.setLineDash([3, 3]);
    ctx.globalAlpha = 0.4;
    ctx.beginPath(); ctx.moveTo(x1, y); ctx.lineTo(x2, y); ctx.stroke();
    ctx.setLineDash([]);
    ctx.globalAlpha = 1;
  });
  ctx.restore(); // end deco shading clip
  }

  // Gas switch guides: full-height dashed lines make switch timing readable.
  function drawGasSwitchFlags() {
    const switchWpsVis = waypoints.filter(wp => wp.type === 'gasswitch' && wp.t >= tMin && wp.t <= tMax);
    switchWpsVis.forEach((wp, si) => {
      const x = toX(wp.t);
      const yDepth = toY(wp.depth || 0);
      const rawLabel = wp.gasLabel || 'Gas';
      const maxLen = isMobile ? 9 : 14;
      const displayLabel = rawLabel.length > maxLen ? rawLabel.slice(0, maxLen) : rawLabel;
      const labelY = PAD.top + PH - 5 - (si % 2) * (isMobile ? 9 : 11);

      ctx.save();
      ctx.strokeStyle = gasSwitchLine;
      ctx.lineWidth = isMobile ? 1 : 1.2;
      ctx.setLineDash([4, 4]);
      ctx.globalAlpha = isLight ? 0.82 : 0.9;
      ctx.beginPath();
      ctx.moveTo(x, PAD.top);
      ctx.lineTo(x, PAD.top + PH);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.beginPath();
      ctx.arc(x, yDepth, isMobile ? 2.5 : 3.2, 0, Math.PI * 2);
      ctx.fillStyle = gasSwitchLine;
      ctx.fill();
      ctx.globalAlpha = 1;
      ctx.font = `800 ${isMobile ? 7 : 9}px "JetBrains Mono",monospace`;
      const labelWidth = ctx.measureText(displayLabel).width;
      const labelX = Math.max(PAD.left + labelWidth / 2 + 2, Math.min(PAD.left + PW - labelWidth / 2 - 2, x));
      ctx.textAlign = 'center';
      ctx.textBaseline = 'bottom';
      ctx.fillStyle = gasSwitchText;
      ctx.fillText(displayLabel, labelX, labelY);
      ctx.restore();
    });
  }

  // â”€â”€ Profile line with per-gas color zones â”€â”€
  const pathWps = waypoints.filter(wp => wp.type !== 'gasswitch');
  const gasSegs    = (!simple && canvasId === 'decoProfileCanvas') ? window._decoGasSegments
                   : (!simple && canvasId === 'plannerProfileCanvas') ? window._plannerGasSegments : null;
  const gasColorMap = (!simple && canvasId === 'decoProfileCanvas') ? window._decoGasColorMap
                   : (!simple && canvasId === 'plannerProfileCanvas') ? window._plannerGasColorMap : null;

  if (pathWps.length > 1) {
    if (!simple && gasSegs && gasSegs.length >= 1) {
      // Draw per-gas colored segments
      // Build a map of t â†’ depth from pathWps for interpolation
      function depthAtT(t) {
        for (let i = 1; i < pathWps.length; i++) {
          if (pathWps[i].t >= t) {
            const prev = pathWps[i-1], next = pathWps[i];
            const frac = (t - prev.t) / (next.t - prev.t || 1);
            return prev.depth + (next.depth - prev.depth) * frac;
          }
        }
        return pathWps[pathWps.length-1].depth;
      }

      // â”€â”€ Draw fills first (all segments), then lines on top â”€â”€
      // Pass 1: fills only â€” each clipped exactly to its time column, no overlap
      gasSegs.forEach((seg, si) => {
        const pts = [];
        pts.push({ t: seg.fromT, depth: depthAtT(seg.fromT) });
        pathWps.forEach(wp => { if (wp.t > seg.fromT && wp.t < seg.toT) pts.push(wp); });
        pts.push({ t: seg.toT, depth: depthAtT(seg.toT) });
        const vis = pts.filter(p => p.t >= tMin - 0.01 && p.t <= tMax + 0.01);
        if (vis.length < 2) return;

        ctx.save();
        const clipX1 = toX(Math.max(seg.fromT, tMin));
        const clipX2 = toX(Math.min(seg.toT,   tMax));
        const r2 = parseInt(seg.color.slice(1,3),16), g2 = parseInt(seg.color.slice(3,5),16), b2 = parseInt(seg.color.slice(5,7),16);
        const segTopY    = Math.min(...vis.map(wp => toY(wp.depth)));
        const segBottomY = Math.max(...vis.map(wp => toY(wp.depth)));
        const segSpanPx  = segBottomY - segTopY;
        // Bottom gas (si=0, deepest segment) gets proportional fill; deco segments get tight fade
        const isBottomSeg = si === 0;
        const fadeH  = isBottomSeg
          ? Math.min(PH, segSpanPx * 0.75)
          : Math.max(40, Math.min(80, segSpanPx * 0.6 + 30)); // tighter cap for shallow deco stops
        const fadeAlpha = isBottomSeg
          ? (isLight ? 0.22 : 0.24)
          : (isLight ? 0.13 : 0.15);
        const fadeY  = Math.min(segTopY + fadeH, PAD.top + PH);
        // Clip: x-column, from shallowest point down to fadeY
        ctx.beginPath();
        ctx.rect(clipX1, segTopY, clipX2 - clipX1, fadeY - segTopY);
        ctx.clip();

        const maxY = PAD.top + PH;
        ctx.beginPath();
        vis.forEach((wp, i) => i === 0 ? ctx.moveTo(toX(wp.t), toY(wp.depth)) : ctx.lineTo(toX(wp.t), toY(wp.depth)));
        ctx.lineTo(toX(vis[vis.length - 1].t), maxY);
        ctx.lineTo(toX(vis[0].t), maxY);
        ctx.closePath();
        const grad = ctx.createLinearGradient(0, segTopY, 0, fadeY);
        grad.addColorStop(0,   `rgba(${r2},${g2},${b2},${fadeAlpha})`);
        grad.addColorStop(1.0, `rgba(${r2},${g2},${b2},0.00)`);
        ctx.fillStyle = grad;
        ctx.fill();
        ctx.restore();
      });

      // Pass 2: profile lines â€” drawn without clip so segment joins are seamless
      // Draw one continuous path per gas (no gap at segment boundaries)
      gasSegs.forEach((seg) => {
        const pts = [];
        pts.push({ t: seg.fromT, depth: depthAtT(seg.fromT) });
        pathWps.forEach(wp => { if (wp.t > seg.fromT && wp.t < seg.toT) pts.push(wp); });
        pts.push({ t: seg.toT, depth: depthAtT(seg.toT) });
        const vis = pts.filter(p => p.t >= tMin - 0.01 && p.t <= tMax + 0.01);
        if (vis.length < 2) return;

        ctx.save(); clipToPlot();
        ctx.beginPath();
        ctx.strokeStyle = seg.color;
        ctx.lineWidth = isMobile ? 1.5 : 2.5;
        ctx.lineJoin = 'round'; ctx.lineCap = 'round';
        vis.forEach((wp, i) => i === 0 ? ctx.moveTo(toX(wp.t), toY(wp.depth)) : ctx.lineTo(toX(wp.t), toY(wp.depth)));
        ctx.stroke();
        ctx.restore();
      });
    } else {
      // Single color fallback (also used for simple results graph)
      ctx.save(); clipToPlot();
      ctx.beginPath();
      ctx.strokeStyle = profileLine;
      ctx.lineWidth = simple ? (isMobile ? 2 : 2.5) : (isMobile ? 1.5 : 2);
      ctx.lineJoin = 'round';
      pathWps.forEach((wp, i) => i === 0 ? ctx.moveTo(toX(wp.t), toY(wp.depth)) : ctx.lineTo(toX(wp.t), toY(wp.depth)));
      ctx.stroke();
      ctx.beginPath();
      pathWps.forEach((wp, i) => i === 0 ? ctx.moveTo(toX(wp.t), toY(wp.depth)) : ctx.lineTo(toX(wp.t), toY(wp.depth)));
      ctx.lineTo(toX(pathWps[pathWps.length-1].t), PAD.top + PH);
      ctx.lineTo(toX(pathWps[0].t), PAD.top + PH);
      ctx.closePath();
      const grad = ctx.createLinearGradient(0, PAD.top, 0, PAD.top + PH);
      grad.addColorStop(0, isLight ? 'rgba(8,145,178,0.16)' : 'rgba(34,211,238,0.15)');
      grad.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = grad;
      ctx.fill();
      ctx.restore();
    }
  }

  // â”€â”€ Deco ceiling line overlay â”€â”€
  if (!simple) {
  const ceilWps = canvasId === 'decoProfileCanvas' ? window._decoCeilingWps
               : canvasId === 'plannerProfileCanvas' ? window._plannerCeilingWps : null;
  if (ceilWps && ceilWps.length > 1) {
    // Draw only points where ceiling > 0 â€” no artificial lead point that causes vertical artefacts
    const activeCeil = ceilWps.filter(wp => wp.ceil > 0.5); // 0.5m threshold to avoid noise
    if (activeCeil.length > 1) {
      const visCeil = activeCeil.filter(wp => wp.t >= tMin - 0.1 && wp.t <= tMax + 0.1);
      if (visCeil.length > 1) {
        ctx.save();
        clipToPlot();
        ctx.beginPath();
        ctx.strokeStyle = red;
        ctx.lineWidth = 1.5;
        ctx.setLineDash([5, 4]);
        ctx.globalAlpha = 0.85;
        visCeil.forEach((wp, i) => {
          const x = toX(wp.t), y = toY(wp.ceil);
          i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        });
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.restore();
      }
    }
  }
  }

  // â”€â”€ Stop dots with labels â”€â”€
  const usedY = new Map(); // track used y positions per x-column to stagger labels

  waypoints.forEach(wp => {
    if (simple) {
      if (wp.type !== 'deco' && wp.type !== 'safety') return;
    } else if (!wp.dot) return;
    const x = toX(wp.t), y = toY(wp.depth);
    const dotColor = wp.type === 'deco'   ? red
                   : wp.type === 'safety' ? green
                   : wp.type === 'bottom' ? accent
                   : muted;

    if (!simple && wp.ppo2 >= 1.4) {
      ctx.beginPath(); ctx.arc(x, y, haloRadius, 0, Math.PI*2);
      ctx.fillStyle = wp.ppo2 >= 1.6 ? 'rgba(255,71,87,0.2)' : 'rgba(255,183,3,0.2)';
      ctx.fill();
    }

    ctx.beginPath(); ctx.arc(x, y, simple ? (isMobile ? 2.5 : 3.5) : dotRadius, 0, Math.PI*2);
    ctx.fillStyle = dotColor; ctx.fill();
    ctx.strokeStyle = bg; ctx.lineWidth = isMobile ? 1 : 1.5; ctx.stroke();

    if (simple) return;

    // Draw dot number
    if (wp.dot && wp.num) {
      ctx.fillStyle = bg;
      ctx.font = `600 ${isMobile ? 7 : 8}px "JetBrains Mono",monospace`;
      ctx.textAlign = 'center';
      ctx.fillText(wp.num, x, y + 3);
    }

    if (!wp.label) return;

    // On mobile: dots only â€” legend table below has all info, labels are too crowded
    if (isMobile) return;
    // On very tiny screens also skip
    if (W < 280) return;

    const labelFmt = wp.label.replace(/(\d+m)\s+(\d+)/, '$1 - $2');
    const fullLabel = (wp.num ? wp.num + '  ' : '') + labelFmt;

    ctx.font = labelFont;
    const labelW = ctx.measureText(fullLabel).width;
    const ppTxt   = wp.ppo2 ? 'ppOâ‚‚ ' + wp.ppo2.toFixed(1) : '';
    ctx.font = monoFont;
    const ppW     = ppTxt ? ctx.measureText(ppTxt).width : 0;
    ctx.font = labelFont;

    const rightEdge = PAD.left + PW;
    const spaceLeft  = x - PAD.left;
    const spaceRight = rightEdge - x;

    // Label: prefer left of dot; force right only if not enough space on left
    const preferLeft = spaceLeft >= labelW + 10;
    const lAlign = preferLeft ? 'right' : 'left';
    const lx     = preferLeft ? x - 7 : x + 7;

    // ppOâ‚‚: opposite side from label; clamp so it never overflows canvas
    // If label is left â†’ ppOâ‚‚ wants right side, but guard against right-edge clip
    let ppAlign, ppx;
    if (preferLeft) {
      // label on left â†’ try ppOâ‚‚ on right
      if (x + 7 + ppW <= rightEdge) {
        ppAlign = 'left'; ppx = x + 7;
      } else {
        ppAlign = 'right'; ppx = rightEdge - 2; // pin to right edge
      }
    } else {
      // label on right â†’ try ppOâ‚‚ on left
      if (x - 7 - ppW >= PAD.left) {
        ppAlign = 'right'; ppx = x - 7;
      } else {
        ppAlign = 'left'; ppx = PAD.left + 2;
      }
    }

    // Vertical collision avoidance â€” bucket by label width for better grouping
    const labelH = isMobile ? 10 : 12;
    const lKey = Math.round(x / Math.max(labelW + 4, 20));
    if (!usedY.has(lKey)) usedY.set(lKey, []);
    const usedSlots = usedY.get(lKey);

    // Bottom-dot (type=bottom) label goes below dot, others go above
    const defaultLy = wp.type === 'bottom' ? y + 16 : y - 7;
    let ly = defaultLy;
    for (let attempt = 0; attempt < 10; attempt++) {
      const dir = wp.type === 'bottom' ? 1 : -1;
      const candidate = defaultLy + dir * attempt * labelH;
      const clash = usedSlots.some(sy => Math.abs(sy - candidate) < labelH - 1);
      if (!clash || attempt === 9) { ly = candidate; break; }
    }
    usedSlots.push(ly);

    ctx.textAlign = lAlign;
    ctx.fillStyle = text; ctx.font = labelFont;
    ctx.fillText(fullLabel, lx, ly);

    if (wp.ppo2 && ppTxt) {
      const pColor = wp.ppo2 >= 1.6 ? red : wp.ppo2 >= 1.4 ? orange : muted;
      ctx.fillStyle = pColor; ctx.font = monoFont;
      ctx.textAlign = ppAlign;
      ctx.fillText(ppTxt, ppx, y + 14);
    }
  });

  drawGasSwitchFlags();

  // â”€â”€ Axis label â”€â”€
  ctx.fillStyle = muted; ctx.font = monoFont; ctx.textAlign = 'right';
  ctx.fillText('0' + _du, PAD.left - 5, PAD.top + 4);

  // â”€â”€ Mobile legend below graph â”€â”€
  const legendId = canvasId === 'decoProfileCanvas'
    ? 'decoProfileLegend'
    : canvasId === 'contingencyProfileCanvas'
      ? 'contingencyProfileLegend'
      : 'plannerProfileLegend';
  const legendEl = document.getElementById(legendId);
  if (legendEl) {
    legendEl.style.display = 'none';
    legendEl.innerHTML = '';
  }
}

// â”€â”€â”€ Build waypoints from Dive Planner (Rec mode) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// AUDIT-UNIT:UI-PLOT-WAYPOINTS
function drawPlannerProfile() {
  const canvas = document.getElementById('plannerProfileCanvas');
  if (!canvas) return;

  const depthVal = parseFloat(document.getElementById('recDepth')?.value) || 0;
  const btVal    = parseFloat(document.getElementById('recBT')?.value)    || 0;
  const wrap = document.getElementById('plannerProfileCanvas-wrap');
  if (!depthVal || !btVal) { if(wrap) wrap.style.display='none'; return; }
  if (wrap) wrap.style.display = 'block';

  const dRate = 18, aRate = 9; // default rates m/min
  const duLbl = units === 'metric' ? 'm' : 'ft';
  const fmtDep = (d) => units === 'metric' ? d + 'm' : Math.round(d * 3.28084) + 'ft';
  const descentT = depthVal / dRate;
  const ascentT  = depthVal / aRate;
  const safetyT  = 3;
  const totalT   = descentT + btVal + ascentT + safetyT;

  let t = 0;
  const wps = [
    { t: t, depth: 0, type: 'surface' },
  ];
  t += descentT;
  wps.push({ t, depth: depthVal, type: 'bottom', dot: true, label: fmtDep(depthVal) });
  t += btVal;
  wps.push({ t, depth: depthVal, type: 'bottom' });
  t += ascentT * (depthVal - 5) / depthVal;
  wps.push({ t, depth: 5, type: 'safety' });
  t += safetyT;
  wps.push({ t, depth: 5, type: 'safety', dot: true, label: fmtDep(5) });
  t += ascentT * 5 / depthVal;
  wps.push({ t, depth: 0, type: 'surface' });

  canvas.style.display = 'block';
  window._plannerWaypoints = wps;

  // Simple single-gas segment for planner (no deco gas â€” NDL only)
  const pGasColor = _lspCssVar('--accent', '#22d3ee');
  window._plannerGasSegments = [{ fromT: 0, toT: Math.ceil(totalT), gas: 'AIR', color: pGasColor }];
  window._plannerGasColorMap = { 'AIR': pGasColor };
  // No ceiling for NDL planner (by definition no deco obligation)
  window._plannerCeilingWps = [];

  drawDiveProfile('plannerProfileCanvas', wps, {
    maxDepth: depthVal,
    totalTime: Math.ceil(totalT),
  });
}

// â”€â”€â”€ Build waypoints from Deco Schedule â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function _buildDecoProfileWaypoints(tbodyId = 'decoTableBody') {
  const depthVal  = parseFloat(getPlannerInputEl('decoDepth')?.value) || 0;
  const btVal     = parseFloat(getPlannerInputEl('decoBT')?.value)    || 0;
  if (!depthVal || !btVal) return null;

  function parseRunMin(txt) {
    if (!txt) return 0;
    const s = txt.trim();
    const colon = s.indexOf(':');
    if (colon !== -1) {
      const m = parseFloat(s.slice(0, colon)) || 0;
      const sec = parseFloat(s.slice(colon + 1)) || 0;
      return m + sec / 60;
    }
    return parseFloat(s) || 0;
  }

  const dRate = parseFloat(document.getElementById('descentRate')?.value) || 22;
  const descentT = depthVal / dRate;

  const fmtDepLbl = (d) => units === 'metric' ? d + 'm' : Math.round(d * 3.28084) + 'ft';
  const cellText = (tr, label) => tr.querySelector(`td[data-label="${label}"]`)?.textContent?.trim() || '';
  const tbody = document.getElementById(tbodyId);
  if (!tbody) return null;
  const phaseOf = tr => String(tr.dataset.phase || '').replace(/^contingency-/, '');

  const wps = [{ t: 0, depth: 0, type: 'surface' }];
  let t = descentT;
  const bottomRunRow = Array.from(tbody.querySelectorAll('tr[data-phase]'))
    .find(tr => ['bottom', 'level', 'lvl'].includes(phaseOf(tr)));
  const bottomGas = bottomRunRow ? cellText(bottomRunRow, 'Mix') : null;
  const bottomPpo2 = bottomRunRow ? parseFloat(cellText(bottomRunRow, 'PPO2')) || null : null;
  wps.push({ t, depth: depthVal, type: 'bottom', dot: true, label: fmtDepLbl(depthVal), gas: bottomGas, ppo2: bottomPpo2 });
  const renderedBottomRun = bottomRunRow ? parseRunMin(cellText(bottomRunRow, 'Run')) : 0;
  t = renderedBottomRun > 0 ? renderedBottomRun : btVal;
  wps.push({ t, depth: depthVal, type: 'bottom', gas: bottomGas, ppo2: bottomPpo2 });

  const labelledDepths = new Set();
  tbody.querySelectorAll('tr[data-phase]').forEach(tr => {
    const phase = phaseOf(tr);
    if (phase === 'switch') return;
    if (phase !== 'deco' && phase !== 'safety' && phase !== 'ascent') return;
    const run    = parseRunMin(cellText(tr, 'Run'));
    const depthTxt = cellText(tr, 'Depth');
    const ppo2   = parseFloat(cellText(tr, 'PPO2')) || 0;
    const gas    = cellText(tr, 'Mix') || null;

    if (phase === 'ascent') {
      const toDepth = parseFloat(depthTxt) || 0;
      wps.push({ t: run, depth: toDepth, type: 'ascent', gas });
    } else {
      const depth = parseFloat(depthTxt) || 0;
      const showLabel = !labelledDepths.has(depth);
      if (showLabel) labelledDepths.add(depth);
      const stopTime = cellText(tr, 'Stop');
      const stopNum = wps.filter(w => w.dot).length + 1;
      wps.push({ t: run, depth, type: phase, gas,
        dot: true,
        num: stopNum,
        label: showLabel ? fmtDepLbl(depth) + ' ' + stopTime : null,
        ppo2: ppo2 > 0 ? ppo2 : null,
      });
    }
  });

  const switchWps = [];
  tbody.querySelectorAll('tr[data-phase$="switch"], tr.row-switch').forEach(tr => {
    const switchDepthTxt = cellText(tr, 'Depth');
    const switchGas = cellText(tr, 'Mix');
    const depM = switchDepthTxt.match(/([\d.]+)\s*(m|ft)\b/i) || switchDepthTxt.match(/([\d.]+)/);
    if (!depM) return;
    const switchDepth = parseFloat(depM[1]);
    const switchPpo2 = parseFloat(cellText(tr, 'PPO2').replace(/[^\d.]/g, ''));
    const switchRun = parseRunMin(cellText(tr, 'Run'))
      || parseRunMin(tr.nextElementSibling ? cellText(tr.nextElementSibling, 'Run') : '')
      || parseRunMin(tr.previousElementSibling ? cellText(tr.previousElementSibling, 'Run') : '');
    const nextWp = wps.find(w => w.depth <= switchDepth + 1 && w.depth >= switchDepth - 1 && w.type !== 'bottom');
    const switchT = switchRun > 0 ? switchRun : (nextWp?.t ?? 0);
    switchWps.push({
      t: switchT,
      depth: switchDepth,
      depthLabel: switchDepthTxt,
      type: 'gasswitch',
      gasLabel: switchGas,
      ppo2: Number.isFinite(switchPpo2) ? switchPpo2 : null,
    });
  });
  wps.push(...switchWps);
  wps.sort((a, b) => a.t - b.t);

  const allPhaseRows = Array.from(tbody.querySelectorAll('tr[data-phase]'))
    .filter(tr => phaseOf(tr) !== 'totals' && phaseOf(tr) !== 'info');
  const lastT = parseRunMin(allPhaseRows.length ? cellText(allPhaseRows[allPhaseRows.length - 1], 'Run') : '') || btVal + descentT;
  wps.push({ t: lastT, depth: 0, type: 'surface' });

  return { wps, depthVal, lastT };
}

function drawContingencyProfile() {
  const canvas = document.getElementById('contingencyProfileCanvas');
  if (!canvas) return;
  const built = _buildDecoProfileWaypoints('contingencyTableBody');
  if (!built) return;
  const { wps, depthVal, lastT } = built;
  window._contingencyWaypoints = wps;
  drawDiveProfile('contingencyProfileCanvas', wps, {
    maxDepth: depthVal,
    totalTime: lastT,
    simple: true,
  });
}

function drawDecoProfile() {
  const canvas = document.getElementById('decoProfileCanvas');
  if (!canvas) return;
  const built = _buildDecoProfileWaypoints();
  if (!built) return;
  const { wps, depthVal, lastT } = built;
  window._decoWaypoints = wps;
  drawDiveProfile('decoProfileCanvas', wps, {
    maxDepth: depthVal,
    totalTime: lastT,
    simple: true,
  });
}

function drawDecoProfileFull() {
  const canvas = document.getElementById('plannerProfileCanvas');
  if (!canvas) return;
  const built = _buildDecoProfileWaypoints();
  if (!built) return;
  const { wps, depthVal, lastT } = built;
  const wrap = document.getElementById('plannerProfileCanvas-wrap');
  const card = document.getElementById('fullDiveGraphCard');
  const hint = document.getElementById('plannerProfileCanvas-hint');
  if (wrap) wrap.style.display = 'block';
  if (card) card.style.display = 'block';
  _syncGraphsSectionHeads();
  if (hint) hint.style.display = 'block';
  window._plannerWaypoints = wps;
  window._plannerGasSegments = window._decoGasSegments;
  window._plannerGasColorMap = window._decoGasColorMap;
  window._plannerCeilingWps = window._decoCeilingWps;
  drawDiveProfile('plannerProfileCanvas', wps, {
    maxDepth: depthVal,
    totalTime: lastT,
  });
}
// Store last opts for interpolation
const _graphOpts = {};

// Wrapper stores opts for hover interaction then calls core renderer
// AUDIT-UNIT:UI-TOOLS-PROFILE
function drawDiveProfile(canvasId, waypoints, opts) {
  _drawDiveProfileCore(canvasId, waypoints, opts);
  _graphOpts[canvasId] = { waypoints, opts };
  attachDiveProfileInteraction(canvasId);
}

function attachDiveProfileInteraction(canvasId) {
  const overlay  = document.getElementById(canvasId + '-overlay');
  const tooltip  = document.getElementById(canvasId + '-tooltip');
  const crossV   = document.getElementById(canvasId + '-crosshair-v');
  const crossH   = document.getElementById(canvasId + '-crosshair-h');
  const canvas   = document.getElementById(canvasId);
  if (!overlay || !tooltip || !canvas) return;
  const data = _graphOpts[canvasId];
  if (data?.opts?.simple) {
    overlay.style.cursor = 'default';
    return;
  }

  function getInfo(clientX, clientY) {
    const rect = canvas.getBoundingClientRect();
    const xPct = (clientX - rect.left) / rect.width;
    const yPct = (clientY - rect.top)  / rect.height;

    const data = _graphOpts[canvasId];
    if (!data) return null;
    const { waypoints, opts } = data;
    if (!waypoints || waypoints.length < 2) return null;

    const isMob = rect.width < 480;
    const PAD = isMob
      ? { top: 16, right: 10, bottom: 32, left: 36 }
      : { top: 20, right: 20, bottom: 40, left: 52 };
    const W = rect.width, H = rect.height;
    const PW = W - PAD.left - PAD.right;
    const PH = H - PAD.top  - PAD.bottom;
    const maxDepth  = (opts?.maxDepth || 10) * 1.15;
    const totalTime = opts?.totalTime || 60;

    // Convert pixel to time
    const xPx = clientX - rect.left;
    const yPx = clientY - rect.top;
    const t = ((xPx - PAD.left) / PW) * totalTime;
    if (t < 0 || t > totalTime) return null;

    // Use only path waypoints (exclude gasswitch markers) for interpolation
    const pathWps = waypoints.filter(wp => wp.type !== 'gasswitch');

    // Interpolate depth at time t
    let depth = null, gas = null, ppo2 = null, cns = null, phase = null;
    for (let i = 0; i < pathWps.length - 1; i++) {
      const a = pathWps[i], b = pathWps[i + 1];
      if (t >= a.t && t <= b.t) {
        const frac = (t - a.t) / (b.t - a.t);
        depth = a.depth + (b.depth - a.depth) * frac;
        phase = a.type;
        gas   = a.gas || b.gas || null;
        if (a.ppo2 != null && b.ppo2 != null) ppo2 = a.ppo2 + (b.ppo2 - a.ppo2) * frac;
        else if (a.ppo2 != null) ppo2 = a.ppo2;
        cns = a.cns || b.cns || null;
        break;
      }
    }
    if (depth === null) return null;

    // Pixel position for crosshair
    const cx = PAD.left + (t / totalTime) * PW;
    const cy = PAD.top  + (depth / maxDepth) * PH;

    // Interpolate ceiling at this time
    let ceiling = null;
    const ceilWps = canvasId === 'decoProfileCanvas' ? window._decoCeilingWps
               : canvasId === 'plannerProfileCanvas' ? window._plannerCeilingWps : null;
    if (ceilWps && ceilWps.length > 1) {
      for (let i = 0; i < ceilWps.length - 1; i++) {
        const a = ceilWps[i], b = ceilWps[i+1];
        if (t >= a.t && t <= b.t) {
          const frac = (t - a.t) / (b.t - a.t || 1);
          ceiling = a.ceil + (b.ceil - a.ceil) * frac;
          break;
        }
      }
    }

    return { t, depth, gas, ppo2, cns, phase, cx, cy, rect, ceiling, totalTime };
  }

  let tooltipPinned = false;

  function _profileTooltipEsc(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function _profileTooltipRow(label, value) {
    return `<div class="profile-tip-row"><span>${_profileTooltipEsc(label)}</span><strong>${_profileTooltipEsc(value)}</strong></div>`;
  }

  function _profileGasAtTime(t) {
    const segments = canvasId === 'plannerProfileCanvas' ? window._plannerGasSegments
      : canvasId === 'decoProfileCanvas' ? window._decoGasSegments
      : canvasId === 'contingencyProfileCanvas' ? window._contingencyGasSegments
      : null;
    if (!Array.isArray(segments)) return null;
    const seg = segments.find(s => t >= Number(s.fromT || 0) - 0.001 && t <= Number(s.toT || 0) + 0.001);
    return seg?.gas || null;
  }

  function _profileRoundMin(value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return '—';
    const rounded = Math.round(n * 10) / 10;
    return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
  }

  function _profileTotalsForCanvas() {
    const totals = document.querySelector('#decoTableBody tr.deco-totals-row td[data-run]')
      || document.querySelector('#decoTableBody tr.row-summary td[data-run]');
    return {
      tts: totals?.dataset?.tts || '—',
      surfGF: totals?.dataset?.surfgf || '—',
    };
  }

  function _profileNormalizeGasLabel(label) {
    return String(label || '')
      .replace(/\s+/g, '')
      .replace(/^EAN(\d+)$/i, '$1/00')
      .toUpperCase();
  }

  function _profileConsumedLitresForGas(gasLabel) {
    const gasConsumed = window._lastGasConsumed || {};
    const target = _profileNormalizeGasLabel(gasLabel);
    const key = Object.keys(gasConsumed).find(k => _profileNormalizeGasLabel(k) === target);
    const litres = key ? Number(gasConsumed[key]) : 0;
    return Number.isFinite(litres) && litres > 0 ? litres : 0;
  }

  function _profileSizeLForId(id) {
    if (!id || !document.getElementById(id)) return 0;
    if (typeof gpSizeL === 'function') {
      const size = Number(gpSizeL(id));
      if (Number.isFinite(size) && size > 0) return size;
    }
    const raw = Number.parseFloat(document.getElementById(id)?.value);
    return Number.isFinite(raw) && raw > 0 ? raw : 0;
  }

  function _profileCylinderSizeLForGas(gasLabel) {
    const target = _profileNormalizeGasLabel(gasLabel);
    const candidates = [];
    try {
      const bottom = typeof getBottomGasFractions === 'function' ? getBottomGasFractions() : null;
      if (bottom && typeof getGasLabel === 'function') {
        candidates.push({ label: getGasLabel(bottom.fO2, bottom.fHe), sizeId: 'cylBot_size' });
      }
      if (typeof isTravelGasConfigured === 'function' && isTravelGasConfigured() && typeof getTravelGasInfo === 'function') {
        const travel = getTravelGasInfo();
        candidates.push({ label: travel?.label, sizeId: 'cylTravelGas_size' });
      }
      if (typeof getAllDecoGasIds === 'function' && typeof getDecoCardFractions === 'function' && typeof getGasLabel === 'function') {
        getAllDecoGasIds().forEach(idx => {
          const fracs = getDecoCardFractions(idx);
          if (fracs && fracs.fO2 > 0) candidates.push({ label: getGasLabel(fracs.fO2, fracs.fHe), sizeId: `cylDg${idx}_size` });
        });
      }
    } catch (_) {}
    const match = candidates.find(row => row.label && _profileNormalizeGasLabel(row.label) === target);
    return _profileSizeLForId(match?.sizeId);
  }

  function _profileConsumedText(gasLabel) {
    const litres = _profileConsumedLitresForGas(gasLabel);
    if (!(litres > 0)) return '';
    const sizeL = _profileCylinderSizeLForGas(gasLabel);
    const bar = sizeL > 0 ? litres / sizeL : 0;
    if (units === 'imperial') {
      const vol = typeof gpVolDisp === 'function' ? gpVolDisp(litres) : Math.round(litres / 28.3168);
      const pres = typeof gpPresDisp === 'function' ? gpPresDisp(bar) : Math.round(bar * 14.5038);
      return `${vol} ${typeof lspVolUnit === 'function' ? lspVolUnit() : 'ft³'} / ${pres} psi`;
    }
    return `${Math.round(litres)} L / ${Math.round(bar)} bar`;
  }

  function showTooltip(clientX, clientY, persist = false) {
    const info = getInfo(clientX, clientY);
    if (!info) { hideTooltip(); return; }
    if (persist) tooltipPinned = true;

    const { t, depth, gas, ppo2, phase, cx, cy, rect, ceiling, totalTime } = info;
    const du    = units === 'imperial' ? 'ft' : 'm';
    const dDisp = units === 'imperial' ? Math.round(depth * 3.28084) : Math.round(depth * 10) / 10;
    const ttsRemaining = Math.max(0, (Number(totalTime) || 0) - t);
    const ceilDisp = ceiling != null && ceiling > 0.5
      ? (units === 'imperial' ? Math.round(ceiling * 3.28084) : Math.round(ceiling * 10) / 10)
      : 0;
    const totals = _profileTotalsForCanvas();
    const activeGas = gas || _profileGasAtTime(t);
    let html = '';
    html += _profileTooltipRow('RT', `${_profileRoundMin(t)} min`);
    html += _profileTooltipRow('Depth', `${dDisp} ${du}`);
    html += _profileTooltipRow('TTS', `${_profileRoundMin(ttsRemaining)} min`);
    html += _profileTooltipRow('Ceiling', `${ceilDisp} ${du}`);
    html += _profileTooltipRow('Surf GF', totals.surfGF || '—');
    html += _profileTooltipRow('Gas', activeGas ? activeGas.toUpperCase() : '—');
    html += _profileTooltipRow('PPO2', ppo2 != null ? ppo2.toFixed(2) : '—');
    tooltip.innerHTML = html;
    tooltip.style.display = 'block';
    tooltip.style.borderColor = 'var(--accent)';

    // Position tooltip - keep inside canvas
    const W = rect.width, H = rect.height;
    let tx = cx + 12, ty = cy - 10;
    if (tx + 160 > W) tx = cx - 160;
    if (ty < 0) ty = cy + 12;
    if (ty + 170 > H) ty = H - 175;
    tooltip.style.left = tx + 'px';
    tooltip.style.top  = ty + 'px';

    // Crosshair
    crossV.style.display = 'block';
    crossV.style.left    = cx + 'px';
    crossH.style.display = 'block';
    crossH.style.top     = cy + 'px';
  }

  function hideTooltip(force = false) {
    if (tooltipPinned && !force) return;
    if (force) tooltipPinned = false;
    tooltip.style.display  = 'none';
    crossV.style.display   = 'none';
    crossH.style.display   = 'none';
  }

  if (overlay.dataset.lspProfileBound === '1') return;
  overlay.dataset.lspProfileBound = '1';

  overlay.addEventListener('mousemove', e => {
    if (!tooltipPinned) showTooltip(e.clientX, e.clientY);
  });
  overlay.addEventListener('mouseleave', hideTooltip);
  overlay.addEventListener('touchmove',  e => {
    e.preventDefault();
    if (e.touches.length === 1) showTooltip(e.touches[0].clientX, e.touches[0].clientY, true);
  }, { passive: false });

  // Scroll/wheel zoom
  overlay.addEventListener('wheel', e => {
    e.preventDefault();
    const data = _graphOpts[canvasId];
    if (!data) return;
    const { opts } = data;
    const PAD = { top: 20, right: 20, bottom: 40, left: 52 };
    const rect = canvas.getBoundingClientRect();
    const PW = rect.width - PAD.left - PAD.right;
    const rawTotalTime = opts?.totalTime || 60;
    const rawMaxDepth  = (opts?.maxDepth || 10) * 1.15;
    const zoom = _graphZoom[canvasId] || { tMin: 0, tMax: rawTotalTime, dMin: 0, dMax: rawMaxDepth };

    const factor = e.deltaY < 0 ? 0.8 : 1.25;
    const xPx = e.clientX - rect.left;
    const tFrac = Math.max(0, Math.min(1, (xPx - PAD.left) / PW));
    const tCursor = zoom.tMin + tFrac * (zoom.tMax - zoom.tMin);

    let newTMin = tCursor - (tCursor - zoom.tMin) * factor;
    let newTMax = tCursor + (zoom.tMax - tCursor) * factor;
    // Clamp
    const span = Math.max(5, newTMax - newTMin);
    newTMin = Math.max(0, newTMin);
    newTMax = Math.min(rawTotalTime, newTMin + span);
    newTMin = Math.max(0, newTMax - span);

    if (newTMax - newTMin >= rawTotalTime * 0.98) {
      _graphZoomReset(canvasId);
    } else {
      _graphZoomApply(canvasId, { tMin: newTMin, tMax: newTMax, dMin: zoom.dMin, dMax: zoom.dMax });
    }
    drawDiveProfile(canvasId, data.waypoints, data.opts);
  }, { passive: false });

  // â”€â”€ Double-click: reset zoom â”€â”€
  overlay.addEventListener('dblclick', e => {
    e.preventDefault();
    hideTooltip(true);
    _graphZoomReset(canvasId);
    const data = _graphOpts[canvasId];
    if (data) drawDiveProfile(canvasId, data.waypoints, data.opts);
  });

  // â”€â”€ Drag to pan â”€â”€
  let _dragStart = null;
  let _dragMoved = false;
  overlay.addEventListener('mousedown', e => {
    if (e.button !== 0) return;
    _dragStart = { x: e.clientX, tMin: (_graphZoom[canvasId]?.tMin ?? 0), tMax: (_graphZoom[canvasId]?.tMax ?? (_graphOpts[canvasId]?.opts?.totalTime || 60)) };
    _dragMoved = false;
    overlay.style.cursor = 'grabbing';
  });
  overlay.addEventListener('mousemove', e => {
    if (!_dragStart) return;
    const data = _graphOpts[canvasId];
    if (!data) return;
    const _isMob2 = canvas.getBoundingClientRect().width < 480;
    const PAD = _isMob2 ? { left: 36, right: 10 } : { left: 52, right: 20 };
    const rect = canvas.getBoundingClientRect();
    const PW = rect.width - PAD.left - PAD.right;
    const span = _dragStart.tMax - _dragStart.tMin;
    const rawTotalTime = data.opts?.totalTime || 60;
    const rawMaxDepth  = (data.opts?.maxDepth || 10) * 1.15;
    const zoom = _graphZoom[canvasId] || { dMin: 0, dMax: rawMaxDepth };
    const dx = e.clientX - _dragStart.x;
    if (Math.abs(dx) > 3) _dragMoved = true;
    const dtPerPx = span / PW;
    let newTMin = _dragStart.tMin - dx * dtPerPx;
    let newTMax = newTMin + span;
    if (newTMin < 0) { newTMin = 0; newTMax = span; }
    if (newTMax > rawTotalTime) { newTMax = rawTotalTime; newTMin = rawTotalTime - span; }
    _graphZoomApply(canvasId, { tMin: newTMin, tMax: newTMax, dMin: zoom.dMin, dMax: zoom.dMax });
    drawDiveProfile(canvasId, data.waypoints, data.opts);
  });
  overlay.addEventListener('mouseup', () => { _dragStart = null; overlay.style.cursor = 'crosshair'; });
  overlay.addEventListener('mouseleave', () => { _dragStart = null; overlay.style.cursor = 'crosshair'; });
  overlay.addEventListener('click', e => {
    if (_dragMoved) {
      _dragMoved = false;
      return;
    }
    showTooltip(e.clientX, e.clientY, true);
  });

  // â”€â”€ Pinch to zoom (touch) â”€â”€
  let _pinchDist = null;
  let _pinchZoomStart = null;
  overlay.addEventListener('touchstart', e => {
    if (e.touches.length === 2) {
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      _pinchDist = Math.sqrt(dx*dx + dy*dy);
      _pinchZoomStart = { ...(_graphZoom[canvasId] || { tMin: 0, tMax: (_graphOpts[canvasId]?.opts?.totalTime || 60), dMin: 0, dMax: ((_graphOpts[canvasId]?.opts?.maxDepth || 10) * 1.15) }) };
    }
  }, { passive: true });
  overlay.addEventListener('touchmove', e => {
    if (e.touches.length === 2 && _pinchDist && _pinchZoomStart) {
      e.preventDefault();
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      const newDist = Math.sqrt(dx*dx + dy*dy);
      const factor = _pinchDist / newDist;
      const data = _graphOpts[canvasId];
      if (!data) return;
      const rawTotalTime = data.opts?.totalTime || 60;
      const span = _pinchZoomStart.tMax - _pinchZoomStart.tMin;
      const center = (_pinchZoomStart.tMin + _pinchZoomStart.tMax) / 2;
      const newSpan = Math.min(rawTotalTime, Math.max(5, span * factor));
      let newTMin = Math.max(0, center - newSpan / 2);
      let newTMax = Math.min(rawTotalTime, newTMin + newSpan);
      if (newTMax - newTMin >= rawTotalTime * 0.98) {
        _graphZoomReset(canvasId);
      } else {
        _graphZoomApply(canvasId, { tMin: newTMin, tMax: newTMax, dMin: _pinchZoomStart.dMin, dMax: _pinchZoomStart.dMax });
      }
      drawDiveProfile(canvasId, data.waypoints, data.opts);
    }
  }, { passive: false });
  overlay.addEventListener('touchend', e => {
    if (e.touches.length < 2) { _pinchDist = null; _pinchZoomStart = null; }
  });
}
