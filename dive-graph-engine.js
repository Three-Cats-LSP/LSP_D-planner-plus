/**
 * Shared graph rendering primitives for dive-profile and GF graphs.
 * The engine owns canvas setup, theme colors, plot geometry, and PDF capture
 * so web/mobile/PDF graphs use the same rendering contract.
 */
(function () {
  'use strict';

  function cssVar(name, fallback) {
    if (typeof window._lspCssVar === 'function') return window._lspCssVar(name, fallback);
    try {
      const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
      return value || fallback;
    } catch (_) {
      return fallback;
    }
  }

  function isLightTheme(explicit) {
    if (typeof explicit === 'boolean') return explicit;
    return !!document.body?.classList?.contains('light-theme');
  }

  function theme(explicitLight) {
    const isLight = isLightTheme(explicitLight);
    return {
      isLight,
      bg: cssVar('--surface-2', isLight ? '#f4f6fa' : '#0e0f11'),
      grid: isLight ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.08)',
      axis: isLight ? 'rgba(0,0,0,0.2)' : 'rgba(255,255,255,0.15)',
      text: cssVar('--text', isLight ? '#1a202c' : '#e2e8f0'),
      muted: cssVar('--text-muted', isLight ? '#4a5568' : '#8892a4'),
      accent: cssVar('--accent', isLight ? '#0891b2' : '#22d3ee'),
      red: cssVar('--red', isLight ? '#dc2626' : '#f87171'),
      green: cssVar('--green', isLight ? '#16a34a' : '#4ade80'),
      orange: cssVar('--orange', isLight ? '#b45309' : '#fbbf24'),
      gasSwitchLine: cssVar('--gas-switch-guide', '#16a34a'),
      gasSwitchBg: cssVar('--gas-switch-label-bg', '#d6ff00'),
      gasSwitchText: cssVar('--gas-switch-guide', '#16a34a'),
    };
  }

  function setupHiDPI(canvas, opts) {
    opts = opts || {};
    const requested = Number(opts.dpr || window._lspGraphExportDpr || window.devicePixelRatio || 1);
    const dpr = Math.max(1, Math.min(requested || 1, opts.maxDpr || (window._lspGraphExportDpr ? 3 : 2)));
    const rect = canvas.getBoundingClientRect();
    const w = Number(rect.width || canvas.getAttribute('width') || 700);
    const h = Number(rect.height || canvas.getAttribute('height') || 240);
    canvas.width = Math.max(1, Math.round(w * dpr));
    canvas.height = Math.max(1, Math.round(h * dpr));
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    return { ctx, W: w, H: h, dpr };
  }

  function plotPadding(kind, W, H) {
    const mobile = W < 520;
    if (kind === 'gf') {
      return mobile
        ? { top: 6, right: 2, bottom: 20, left: 30 }
        : { top: 10, right: 6, bottom: 28, left: 40 };
    }
    return mobile
      ? { top: 6, right: 2, bottom: 14, left: 22 }
      : { top: 10, right: 6, bottom: 28, left: 40 };
  }

  function projectors(pad, W, H, domains) {
    const PW = Math.max(1, W - pad.left - pad.right);
    const PH = Math.max(1, H - pad.top - pad.bottom);
    const tMin = Number(domains.tMin || 0);
    const tMax = Number(domains.tMax || 1);
    const dMin = Number(domains.dMin || 0);
    const dMax = Number(domains.dMax || 1);
    const tSpan = Math.max(0.0001, tMax - tMin);
    const dSpan = Math.max(0.0001, dMax - dMin);
    return {
      PW,
      PH,
      toX(value) { return pad.left + ((value - tMin) / tSpan) * PW; },
      toY(value) { return pad.top + ((value - dMin) / dSpan) * PH; },
      inPlot(x, y) {
        return x >= pad.left && x <= pad.left + PW && y >= pad.top && y <= pad.top + PH;
      },
    };
  }

  function clipPlot(ctx, pad, PW, PH) {
    ctx.beginPath();
    ctx.rect(pad.left, pad.top, PW, PH);
    ctx.clip();
  }

  function drawRoundedRect(ctx, x, y, w, h, r) {
    const rr = Math.min(r || 4, w / 2, h / 2);
    ctx.beginPath();
    ctx.moveTo(x + rr, y);
    ctx.arcTo(x + w, y, x + w, y + h, rr);
    ctx.arcTo(x + w, y + h, x, y + h, rr);
    ctx.arcTo(x, y + h, x, y, rr);
    ctx.arcTo(x, y, x + w, y, rr);
    ctx.closePath();
  }

  function captureCanvasForPDF(srcCanvas, targetMM, opts) {
    opts = opts || {};
    const dpi = Number(opts.dpi || 170);
    const quality = Math.max(0.5, Math.min(0.95, Number(opts.quality || 0.82)));
    const mmPerInch = 25.4;
    const targetPx = Math.max(1, Math.round(targetMM * dpi / mmPerInch));
    const aspect = srcCanvas.height / Math.max(1, srcCanvas.width);
    const outW = targetPx;
    const outH = Math.max(1, Math.round(outW * aspect));
    const tmp = document.createElement('canvas');
    tmp.width = outW;
    tmp.height = outH;
    const ctx = tmp.getContext('2d');
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, outW, outH);
    ctx.drawImage(srcCanvas, 0, 0, outW, outH);
    return { dataURL: tmp.toDataURL('image/jpeg', quality), format: 'JPEG', w: outW, h: outH };
  }

  window.LSPGraphEngine = {
    setupHiDPI,
    theme,
    plotPadding,
    projectors,
    clipPlot,
    drawRoundedRect,
    captureCanvasForPDF,
  };

  // Preserve the long-standing public helper used by graph modules/tests.
  window.setupHiDPI = setupHiDPI;
})();
