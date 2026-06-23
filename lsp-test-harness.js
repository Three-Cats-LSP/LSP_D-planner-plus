/**
 * LSP D-Planner — shared browser test harness (dual-engine: VPMEngine + ZHLEngine)
 * Include inline in test HTML (site sync may not deploy standalone .js files).
 */
var LSPTestHarness = (function () {
  'use strict';

  function clone(v) {
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
    hookIframe(iframe, function (msg) { bootErr = msg; });

    function finish(err, ctx) {
      if (settled) return;
      settled = true;
      cb(err, ctx);
    }

    function check() {
      try {
        var w = iframe.contentWindow;
        if (appReady(w)) {
          w._zhlHeadless = true;
          var phys = readPhys(w);
          setTimeout(function () {
            finish(null, {
              win: w,
              vpm: w.VPMEngine,
              zhl: w.ZHLEngine,
              version: w.APP_VERSION || null,
              surf: phys.surf,
              barPerM: phys.barPerM,
            });
          }, 1500);
          return;
        }
      } catch (_) {}
      if (bootErr) return finish(new Error('Boot: ' + bootErr));
      if (Date.now() - start > timeoutMs) {
        return finish(new Error('Timed out waiting for VPMEngine + ZHLEngine in index.html'));
      }
      setTimeout(check, 250);
    }

    var start = Date.now();
    if (!iframe.src || iframe.src === 'about:blank') {
      iframe.src = 'index.html?ts=' + Date.now();
    }
    setTimeout(check, 300);
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
    if (ctx.win) ctx.win._zhlHeadless = true;
    if (!r || typeof r !== 'object') throw new Error('Engine returned no result');
    if (r.error) throw new Error(r.error);
    return r;
  }

  function reloadApp(iframe) {
    iframe.src = 'index.html?ts=' + Date.now();
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
