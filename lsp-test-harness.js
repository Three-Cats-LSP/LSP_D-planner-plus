/**
 * LSP D-Planner — shared browser test harness (dual-engine: VPMEngine + ZHLEngine)
 * Include inline in test HTML (site sync may not deploy standalone .js files).
 */
var LSPTestHarness = (function () {
  'use strict';

  function assertFiniteNumbers(v, path) {
    path = path || '';
    if (typeof v === 'number') {
      if (!isFinite(v)) {
        var label = Number.isNaN(v) ? 'NaN' : (v > 0 ? '+Infinity' : '-Infinity');
        throw new Error('Harness clone: non-finite number' + (path ? ' at ' + path : '') + ': ' + label);
      }
      return;
    }
    if (v == null || typeof v !== 'object') return;
    if (Array.isArray(v)) {
      v.forEach(function (item, i) {
        assertFiniteNumbers(item, path + '[' + i + ']');
      });
      return;
    }
    Object.keys(v).forEach(function (k) {
      assertFiniteNumbers(v[k], path ? path + '.' + k : k);
    });
  }

  function clone(v) {
    assertFiniteNumbers(v, '');
    return JSON.parse(JSON.stringify(v));
  }

  function hookIframe(iframe, onErr) {
    iframe.addEventListener('load', function () {
      try {
        var w = iframe.contentWindow;
        if (!w || w.__lspHarnessHooked) return;
        w.__lspHarnessHooked = true;
        w.addEventListener('error', function (e) {
          onErr((e && e.message) || 'Script error');
        });
        w.addEventListener('unhandledrejection', function (e) {
          var r = e.reason;
          onErr((r && r.message) || String(r) || 'Unhandled rejection');
        });
      } catch (_) {}
    });
  }

  function appReady(w) {
    return !!(w
      && w.VPMEngine && typeof w.VPMEngine.calculate === 'function'
      && w.ZHLEngine && typeof w.ZHLEngine.calculate === 'function');
  }

  function appFullyReady(w) {
    return appReady(w) && w.__lspAppFullyReady === true;
  }

  function readPhys(win) {
    var surf = isFinite(win.altSurfaceP) ? win.altSurfaceP : 1.01325;
    var bar = win.BAR_PER_METRE;
    if (bar == null || !isFinite(bar)) bar = 0.1;
    return { surf: surf, barPerM: bar };
  }

  /**
   * Wait for index.html iframe to expose both engines.
   * @param {HTMLIFrameElement} iframe
   * @param {number} timeoutMs
   * @param {function(Error|null, object)} cb ctx: { win, vpm, zhl, version, surf, barPerM }
   */
  function waitForApp(iframe, timeoutMs, cb) {
    var bootErr = null;
    var settled = false;
    var start = Date.now();
    hookIframe(iframe, function (msg) { bootErr = msg; });

    function finish(err, ctx) {
      if (settled) return;
      settled = true;
      cb(err, ctx);
    }

    function check() {
      try {
        var w = iframe.contentWindow;
        if (appFullyReady(w)) {
          w._zhlHeadless = true;
          var phys = readPhys(w);
          finish(null, {
            win: w,
            vpm: w.VPMEngine,
            zhl: w.ZHLEngine,
            version: w.APP_VERSION || null,
            surf: phys.surf,
            barPerM: phys.barPerM,
          });
          return;
        }
      } catch (_) {}
      if (bootErr) return finish(new Error('Boot: ' + bootErr));
      if (Date.now() - start > timeoutMs) {
        return finish(new Error('Timed out waiting for VPMEngine + ZHLEngine in index.html'));
      }
      setTimeout(check, 50);
    }

    if (!iframe.src || iframe.src === 'about:blank') {
      iframe.src = 'index.html?regression=1&massiveSuite=1&ts=' + Date.now();
    }
    setTimeout(check, 100);
  }

  /** Route ZHLC_GF → ZHLEngine; VPM models → VPMEngine. */
  function calc(ctx, levels, gases, settings, model) {
    if (!ctx || !ctx.vpm || !ctx.zhl) throw new Error('Harness not booted — call waitForApp first');
    var lv = clone(levels || []);
    var gs = clone(gases || []);
    var st = clone(settings || {});
    if (ctx.win) ctx.win._zhlHeadless = true;
    var r = (model === 'ZHLC_GF')
      ? ctx.zhl.calculate(lv, gs, st)
      : ctx.vpm.calculate(lv, gs, st, model);
    if (!r || typeof r !== 'object') throw new Error('Engine returned no result');
    if (r.error) throw new Error(r.error);
    return r;
  }

  function reloadApp(iframe, qs) {
    iframe.src = 'index.html?' + (qs || 'regression=1&massiveSuite=1') + '&ts=' + Date.now();
  }

  return {
    clone: clone,
    waitForApp: waitForApp,
    calc: calc,
    readPhys: readPhys,
    reloadApp: reloadApp,
    appReady: appReady,
  };
})();
