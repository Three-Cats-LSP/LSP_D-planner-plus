#!/usr/bin/env python3
"""
Engine validation regression — malformed gas fractions and dive profiles (GitHub #7).
Runs headless via Playwright against local index.html.

Usage: python engine_validation_regression.py
Exit 0 = all pass, 1 = failures.
"""

import sys
import threading
import http.server
import socketserver
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent

PASS = []
FAIL = []


def ok(msg):
    PASS.append(msg)
    print(f"  ✓ {msg}")


def fail(msg):
    FAIL.append(msg)
    print(f"  ✗ {msg}")


def start_server():
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ROOT), **kwargs)

        def log_message(self, fmt, *args):
            pass

    httpd = socketserver.TCPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, port


def run_checks(page, port):
    page.goto(f"http://127.0.0.1:{port}/index.html?massiveSuite=1", wait_until="domcontentloaded")
    page.wait_for_function(
        "() => window.ZHLEngine && window.VPMEngine && window.validateEngineInputs && window.ZhlEngineBundle",
        timeout=60000,
    )
    page.wait_for_timeout(3000)

    settings = {
        "metric": True,
        "gfLo": 30,
        "gfHi": 85,
        "stepSize": 3,
        "lastStop": 3,
        "minStopTime": 1,
    }

    results = page.evaluate(
        """(settings) => {
      const lv = (d, t, o2, he) => [{ depth: d, time: t, o2, he }];
      const zhlLv = (levels, gases) => window.ZHLEngine.calculate(levels, gases || [], settings);
      const zhl = (d, t, o2, he, gases) => zhlLv(lv(d, t, o2, he), gases);
      const vpmLv = (levels, gases, s) => window.VPMEngine.calculate(levels, gases || [], s, 'VPMB');
      const vpm = (d, t, o2, he, gases) => vpmLv(lv(d, t, o2, he), gases, settings);
      const out = {};

      out.valid = zhl(40, 25, 21, 0);
      out.badMixZhl = zhl(40, 25, 50, 60);
      out.badO2Zhl = zhl(40, 25, 150, 0);
      out.negO2Zhl = zhl(40, 25, -10, 0);
      out.negDepthZhl = zhl(-10, 25, 21, 0);
      out.zeroTimeZhl = zhl(40, 0, 21, 0);
      out.boundaryZhl = zhl(40, 25, 50, 50);
      out.badDecoZhl = zhl(40, 25, 21, 0, [{ o2: 50, he: 60 }]);
      out.badMixVpm = vpm(40, 25, 50, 60);
      out.negHeVpm = vpm(40, 25, 21, -5);
      out.nanHeZhl = zhl(40, 25, 21, NaN);
      out.nanHeVpm = vpm(40, 25, 21, NaN);
      out.nanO2Vpm = vpm(40, 25, NaN, 0);
      out.vpmEmpty = vpmLv([], [], settings);
      out.zhlEmpty = zhlLv([], []);
      out.zhlMl = zhlLv(
        [{ depth: 60, time: 20, o2: 18, he: 45 }, { depth: 42, time: 8, o2: 18, he: 45 }],
        []
      );
      out.zhlSingle = zhlLv([{ depth: 60, time: 20, o2: 18, he: 45 }], []);
      out.zhlRedescend = zhlLv(
        [{ depth: 60, time: 20, o2: 18, he: 45 }, { depth: 42, time: 8, o2: 18, he: 45 }, { depth: 50, time: 5, o2: 18, he: 45 }],
        []
      );
      out.zhlDeepNotFirst = zhlLv(
        [{ depth: 30, time: 10, o2: 21, he: 0 }, { depth: 60, time: 20, o2: 18, he: 45 }],
        []
      );
      out.vpmNoSettings = vpmLv(lv(40, 25, 21, 0), null, null);
      out.vpmNoGases = vpmLv(lv(40, 25, 21, 0), undefined, {});
      out.vpmNullLevel = vpmLv([null], [], {});
      out.vpmNullGas = vpmLv(lv(40, 25, 21, 0), [null], {});
      out.vpmOmittedHe = vpmLv(lv(40, 25, 21, 0), [{ o2: 50 }], settings);
      out.vpmOmittedHeFinite = (() => {
        const r = out.vpmOmittedHe;
        if (r.error || !(r.totalRuntime > 0)) return false;
        return !(r.plan || []).some(s => {
          const t = s.time ?? s.runtime;
          const d = s.depth ?? s.endDepth ?? s.startDepth;
          return !Number.isFinite(t) || !Number.isFinite(d) || (s.he != null && !Number.isFinite(s.he));
        });
      })();

      out.zhlRestoresHeadlessFields = (() => {
        const saved = {
          ascentRate: '9',
          decoAscentRate: '6',
          surfaceAscentRate: '9',
          descentRate: '18',
          minStopTime: '2',
          decoStep: '5',
          lastDecoStop: '6',
          ppo2Bottom: '1.2',
          ppo2Deco: '1.5',
        };
        Object.entries(saved).forEach(([id, value]) => {
          const el = document.getElementById(id);
          if (el) el.value = value;
        });
        const r = window.ZHLEngine.calculate(lv(40, 25, 21, 0), [], {
          ...settings,
          ascentRate: 10,
          decoAscentRate: 3,
          surfaceAscentRate: 3,
          descentRate: 20,
          minStopTime: 1,
          stepSize: 3,
          lastStop: 3,
          ppO2Bottom: 1.4,
          ppO2Deco: 1.6,
        });
        const restored = Object.entries(saved).every(([id, value]) => {
          const el = document.getElementById(id);
          return !el || el.value === value;
        });
        return { ok: restored && !r.error && r.totalRuntime > 0, restored, result: r };
      })();

      const dom = document.getElementById('decoGas');
      const prevMix = dom ? dom.value : null;
      const prevO2 = document.getElementById('botTrimixO2')?.value;
      const prevHe = document.getElementById('botTrimixHe')?.value;
      if (dom) dom.value = 'trimix';
      const o2El = document.getElementById('botTrimixO2');
      const heEl = document.getElementById('botTrimixHe');
      if (o2El) o2El.value = '50';
      if (heEl) heEl.value = '60';
      out.domInvalid = window.validateDomDecoGases();
      if (dom && prevMix != null) dom.value = prevMix;
      if (o2El && prevO2 != null) o2El.value = prevO2;
      if (heEl && prevHe != null) heEl.value = prevHe;

      return out;
    }""",
        settings,
    )

    if results["valid"].get("totalRuntime", 0) > 0 and not results["valid"].get("code"):
        ok("valid 40m/25min air produces schedule")
    else:
        fail(f"valid dive failed: {results['valid']}")

    for label, key, code in [
        ("ZHL O2+He>100%", "badMixZhl", "INVALID_GAS_FRACTIONS"),
        ("ZHL O2>100%", "badO2Zhl", "INVALID_GAS_FRACTIONS"),
        ("ZHL negative O2", "negO2Zhl", "INVALID_GAS_FRACTIONS"),
        ("ZHL negative depth", "negDepthZhl", "INVALID_DEPTH"),
        ("ZHL zero bottom time", "zeroTimeZhl", "INVALID_TIME"),
        ("ZHL invalid deco gas", "badDecoZhl", "INVALID_GAS_FRACTIONS"),
        ("VPM O2+He>100%", "badMixVpm", "INVALID_GAS_FRACTIONS"),
        ("VPM negative He", "negHeVpm", "INVALID_GAS_FRACTIONS"),
        ("ZHL NaN He", "nanHeZhl", "INVALID_GAS_FRACTIONS"),
        ("VPM NaN He", "nanHeVpm", "INVALID_GAS_FRACTIONS"),
        ("VPM NaN O2", "nanO2Vpm", "INVALID_GAS_FRACTIONS"),
    ]:
        got = results[key].get("code")
        if got == code:
            ok(f"{label} → {code}")
        else:
            fail(f"{label}: expected {code}, got {got!r} ({results[key]})")

    if results.get("vpmOmittedHeFinite"):
        ok("VPM deco gas with omitted He produces finite schedule")
    else:
        fail(f"VPM omitted He deco gas failed: {results.get('vpmOmittedHe')}")

    for label, key, code in [
        ("VPM empty levels", "vpmEmpty", "INVALID_PROFILE"),
        ("ZHL empty levels", "zhlEmpty", "INVALID_PROFILE"),
    ]:
        got = results[key].get("code")
        if got == code:
            ok(f"{label} → {code}")
        else:
            fail(f"{label}: expected {code}, got {got!r} ({results[key]})")

    for label, key in [
        ("VPM empty levels totalRuntime", "vpmEmpty"),
        ("ZHL empty levels totalRuntime", "zhlEmpty"),
    ]:
        r = results[key]
        if r.get("totalRuntime") == 0 and r.get("error"):
            ok(f"{label} is 0")
        else:
            fail(f"{label}: expected totalRuntime 0, got {r!r}")

    zhl_ml = results["zhlMl"]
    zhl_single = results["zhlSingle"]
    if not zhl_ml.get("error") and not zhl_single.get("error"):
        if zhl_ml.get("totalRuntime", 0) > zhl_single.get("totalRuntime", 0):
            ok("ZHL multi-level longer than deepest-only profile")
        else:
            fail(
                f"ZHL multi-level not distinguished: ml={zhl_ml.get('totalRuntime')} "
                f"single={zhl_single.get('totalRuntime')}"
            )
    else:
        fail(f"ZHL multi-level calc failed: ml={zhl_ml!r} single={zhl_single!r}")

    for label, key in [
        ("ZHL re-descend profile", "zhlRedescend"),
        ("ZHL deepest not first", "zhlDeepNotFirst"),
    ]:
        r = results[key]
        if r.get("code") == "INVALID_PROFILE" and r.get("error"):
            ok(f"{label} → INVALID_PROFILE")
        else:
            fail(f"{label}: expected INVALID_PROFILE, got {r!r}")

    if results["vpmNoSettings"].get("totalRuntime", 0) > 0 and not results["vpmNoSettings"].get("error"):
        ok("VPM null settings uses defaults (no throw)")
    else:
        fail(f"VPM null settings failed: {results['vpmNoSettings']}")

    if results["vpmNoGases"].get("totalRuntime", 0) > 0 and not results["vpmNoGases"].get("error"):
        ok("VPM undefined decoGases uses empty list (no throw)")
    else:
        fail(f"VPM undefined decoGases failed: {results['vpmNoGases']}")

    for label, key, code in [
        ("VPM null level", "vpmNullLevel", "INVALID_PROFILE"),
        ("VPM null gas", "vpmNullGas", "INVALID_GAS_FRACTIONS"),
    ]:
        got = results[key].get("code")
        if got == code:
            ok(f"{label} → {code}")
        else:
            fail(f"{label}: expected {code}, got {got!r} ({results[key]})")

    if results.get("vpmOmittedHeFinite"):
        ok("VPM deco gas with omitted He produces finite schedule")
    else:
        fail(f"VPM omitted He deco gas failed: {results.get('vpmOmittedHe')}")

    zhl_restore = results.get("zhlRestoresHeadlessFields", {})
    if zhl_restore.get("ok"):
        ok("ZHL headless call restores rate/stop/ppO2 DOM fields")
    else:
        fail(f"ZHL headless DOM field restore failed: {zhl_restore}")

    boundary = results["boundaryZhl"]
    if not boundary.get("code") and boundary.get("totalRuntime", 0) > 0:
        ok("boundary 50/50 trimix (100% total) still calculates")
    else:
        fail(f"boundary 50/50 failed: {boundary}")

    dom = results["domInvalid"]
    if dom.get("ok") is False and any(e.get("code") == "INVALID_GAS_FRACTIONS" for e in dom.get("errors", [])):
        ok("validateDomDecoGases rejects invalid bottom trimix in DOM")
    else:
        fail(f"DOM gas validation failed: {dom}")

    worker_parity = page.evaluate(
        """async (settings) => {
      const levels = [{ depth: 40, time: 25, o2: 21, he: 0 }];
      const sync = window.ZHLEngine.calculate(levels, [], settings);
      const worker = await window.ZHLEngine.calculateInWorker(levels, [], settings);
      const stopsMatch = (sync.stops || []).length === (worker.stops || []).length;
      return {
        ok: !sync.error && !worker.error && sync.totalRuntime === worker.totalRuntime
            && sync.tts === worker.tts && stopsMatch,
        syncRt: sync.totalRuntime,
        workerRt: worker.totalRuntime,
        syncErr: sync.error,
        workerErr: worker.error,
      };
    }""",
        settings,
    )
    if worker_parity.get("ok"):
        ok("ZHL worker calculateInWorker matches sync calculate (Tier 3 parity)")
    else:
        fail(f"ZHL worker parity failed: {worker_parity}")


def main():
    from playwright.sync_api import sync_playwright

    print("Engine validation regression (GitHub #7)")
    print("=" * 50)

    httpd, port = start_server()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            run_checks(page, port)
            browser.close()
    finally:
        httpd.shutdown()

    print(f"\n{'─' * 50}")
    print(f"  Results: {len(PASS)} passed, {len(FAIL)} failed")
    print(f"{'─' * 50}\n")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
