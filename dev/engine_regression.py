#!/usr/bin/env python3
"""
Full engine regression — all algorithms (ZHLC_GF, VPMB, VPMB_GFS), CCR/pSCR,
worker parity, repetitive-dive carry, VPM water types, and issue-fix paths.

Usage: python dev/engine_regression.py
Exit 0 = all pass, 1 = failures.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_DEV = Path(__file__).resolve().parent
if str(_DEV) not in sys.path:
    sys.path.insert(0, str(_DEV))

from playwright_boot import boot_app_page  # noqa: E402
from test_http import serve_root  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PASS: list[str] = []
FAIL: list[str] = []
WARN: list[str] = []


def ok(msg: str) -> None:
    PASS.append(msg)
    print(f"  ✓ {msg}")


def fail(msg: str) -> None:
    FAIL.append(msg)
    print(f"  ✗ {msg}")


def warn(msg: str) -> None:
    WARN.append(msg)
    print(f"  ⚠ {msg}")


def assert_true(cond: bool, label: str, detail: str = "") -> None:
    if cond:
        ok(label)
    else:
        fail(f"{label}" + (f" — {detail}" if detail else ""))


def assert_near(a: float | None, b: float | None, tol: float, label: str) -> None:
    if a is None or b is None:
        fail(f"{label}: missing value ({a!r}, {b!r})")
        return
    if abs(a - b) <= tol:
        ok(f"{label}: {a:.2f} ≈ {b:.2f}")
    else:
        fail(f"{label}: {a:.2f} vs {b:.2f} (tol ±{tol})")


ENGINE_SUITE_JS = """
() => {
  const lv = (d, t, o2, he = 0) => [{ depth: d, time: t, o2, he }];
  const base = {
    metric: true, gfLo: 30, gfHi: 85, stepSize: 3, lastStop: 3, minStopTime: 1,
    descentRate: 20, ascentRate: 10, decoAscentRate: 3, surfaceAscentRate: 3,
    ppO2Bottom: 1.4, ppO2Deco: 1.6, conservatism: 0,
  };
  const zhl = (levels, gases, s) => window.ZHLEngine.calculate(levels, gases || [], { ...base, ...s });
  const vpm = (levels, gases, s, model) => window.VPMEngine.calculate(levels, gases || [], { ...base, ...s }, model);
  const fin = r => !!(r && !r.error && !r.code && (r.totalRuntime || 0) > 0);
  const rt = r => (r && r.totalRuntime) || 0;
  const decoMin = r => (r.stops || []).reduce((a, s) => a + (s.time || s.dur || 0), 0);
  const out = { sections: {} };

  // ── A: OC algorithm matrix ─────────────────────────────────────────────
  const air40 = lv(40, 25, 21, 0);
  out.sections.algos = {
    zhl: zhl(air40, []),
    vpm: vpm(air40, [], {}, 'VPMB'),
    vpmGfs: vpm(air40, [], { gfs: 85, gfHi: 85 }, 'VPMB_GFS'),
    trimixZhl: zhl(lv(60, 20, 18, 45), []),
    trimixVpm: vpm(lv(60, 20, 18, 45), [], {}, 'VPMB'),
  };

  // ── B: VPM water density / pressure gradient ───────────────────────────
  const wLv = lv(40, 25, 21, 0);
  const wBase = { ...base, metric: true };
  out.sections.water = {
    salt: vpm(wLv, [], { ...wBase, waterType: 0 }, 'VPMB'),
    fresh: vpm(wLv, [], { ...wBase, waterType: 1 }, 'VPMB'),
    en13319: vpm(wLv, [], { ...wBase, waterType: 2 }, 'VPMB'),
    custom: vpm(wLv, [], {
      ...wBase, waterType: 3, barPerM: (1030 * 9.80665) / 100000,
    }, 'VPMB'),
    customBarOnly: vpm(wLv, [], {
      ...wBase, waterType: 3, barPerM: 0.10052,
    }, 'VPMB'),
  };

  // ── C: ZHL repetitive via window._zhlRepState (mergeRepSettings) ───────
  window._zhlRepState = null;
  const d1 = zhl(lv(40, 30, 21, 0), []);
  const freshD2 = zhl(lv(40, 20, 21, 0), []);
  if (d1.finalTissues && d1.finalTissues.length) {
    window._zhlRepState = { tissues: d1.finalTissues, surfaceIntervalMin: 60 };
  }
  const repD2 = zhl(lv(40, 20, 21, 0), []);
  const repExplicit = zhl(lv(40, 20, 21, 0), [], {
    _preTissues: d1.finalTissues,
    _surfaceInterval: 60,
  });
  const peekAfter = window._zhlRepState != null;
  out.sections.zhlRep = {
    d1Rt: rt(d1),
    freshRt: rt(freshD2),
    repRt: rt(repD2),
    repExplicitRt: rt(repExplicit),
    peekIntact: peekAfter,
    tissuesSaved: !!(d1.finalTissues && d1.finalTissues.length),
    repDiffersFromFresh: Math.abs(rt(repD2) - rt(freshD2)) > 0.01,
    repMatchesExplicit: Math.abs(rt(repD2) - rt(repExplicit)) <= 2.0,
  };
  window._zhlRepState = null;

  // ── D: VPM repetitive tissue + bubble carry ────────────────────────────
  const vpmD1 = vpm(lv(45, 25, 32, 0), [{ o2: 50, he: 0 }], {}, 'VPMB');
  const vpmFresh = vpm(lv(45, 20, 32, 0), [{ o2: 50, he: 0 }], {}, 'VPMB');
  let vpmRep = null;
  if (vpmD1.finalTissues) {
    vpmRep = vpm(lv(45, 20, 32, 0), [{ o2: 50, he: 0 }], {
      _preTissues: vpmD1.finalTissues,
      _surfaceInterval: 45,
      _prevBubbleState: vpmD1.finalBubbleState,
    }, 'VPMB');
  }
  out.sections.vpmRep = {
    d1Rt: rt(vpmD1),
    freshRt: rt(vpmFresh),
    repRt: rt(vpmRep),
    hasBubble: !!(vpmD1.finalBubbleState),
    repDiffers: vpmRep && Math.abs(rt(vpmRep) - rt(vpmFresh)) > 0.01,
  };

  // ── E: CCR + pSCR (ZHLEngine) ──────────────────────────────────────────
  const ccr = {
    ...base, circuit: 'CCR', setpoint: 1.3, descentSetpoint: 0.7,
    bottomSetpoint: 1.2, decoSetpoint: 1.3, bailout: false,
  };
  const pscr = {
    ...base, circuit: 'pSCR', setpoint: 0, descentSetpoint: 0,
    bottomSetpoint: 0, decoSetpoint: 0, scrLoopVolume: 7, scrMetabolicO2: 0.85,
    bailout: false,
  };
  out.sections.rebreather = {
    ccr: zhl(lv(40, 25, 21, 0), [], ccr),
    pscr: zhl(lv(30, 25, 32, 0), [], pscr),
    ccrTrimix: zhl(lv(55, 20, 18, 35), [], ccr),
    pscrEan36: zhl(lv(25, 40, 36, 0), [], pscr),
  };

  // ── F: VPM engine API + GFS conservatism ───────────────────────────────
  out.sections.vpmApi = {
    loadTypeOk: typeof window.VPMEngine.load === 'function',
    loadReturnOk: (() => {
      if (typeof window.VPMEngine.load !== 'function') return false;
      return window.VPMEngine.load() === true;
    })(),
    gfsStricter: (() => {
      const loose = vpm(air40, [], { ...base, gfs: 95, gfHi: 95, conservatism: 0 }, 'VPMB_GFS');
      const tight = vpm(air40, [], { ...base, gfs: 70, gfHi: 70, conservatism: 3 }, 'VPMB_GFS');
      return { looseRt: rt(loose), tightRt: rt(tight), ok: rt(tight) >= rt(loose) };
    })(),
  };

  // ── G: Worker parity (sync vs calculateInWorker) ───────────────────────
  out.sections.worker = { oc: null, ccr: null, rep: null };

  // ── H: Cross-engine OTU sanity (same OC profile) ───────────────────────
  const zhlOc = zhl(air40, []);
  const vpmOc = vpm(air40, [], {}, 'VPMB');
  out.sections.cross = {
    zhlOtu: zhlOc.totalOTU,
    vpmOtu: vpmOc.totalOTU,
    bothFinite: Number.isFinite(zhlOc.totalOTU) && Number.isFinite(vpmOc.totalOTU),
    otuInRange: zhlOc.totalOTU > 20 && vpmOc.totalOTU > 20 && zhlOc.totalOTU < 120 && vpmOc.totalOTU < 120,
  };

  // ── I: Gas MOD display (calcGasMOD via updateGasMODDisplays) ───────────
  out.sections.gasMod = (() => {
    try {
      const ppo2El = document.getElementById('ppo2Bottom');
      const gasEl = document.getElementById('decoGas');
      const prevPpo2 = ppo2El ? ppo2El.value : null;
      const prevGas = gasEl ? gasEl.value : null;
      if (gasEl) gasEl.value = 'air';
      if (ppo2El) ppo2El.value = '1.4';
      if (typeof setWaterDensity === 'function') setWaterDensity('salt');
      if (typeof updateGasMODDisplays === 'function') updateGasMODDisplays();
      const botTxt = document.getElementById('botMODDisplay')?.value || '';
      const fracs = typeof getBottomGasFractions === 'function' ? getBottomGasFractions() : { fO2: 0.21 };
      const fO2 = fracs.fO2;
      const ppLim = 1.4;
      const o2AtMOD = typeof allowO2AtMOD !== 'undefined' ? allowO2AtMOD : true;
      const lastStop = parseInt(document.getElementById('lastDecoStop')?.value || '3', 10);
      const o2MODm = Math.max(lastStop, 6);
      let expect;
      if (fO2 >= 0.995 && o2AtMOD) expect = o2MODm;
      else expect = Math.floor((ppLim / fO2 - 1) / (window.BAR_PER_METRE || 0.1));
      if (ppo2El && prevPpo2 != null) ppo2El.value = prevPpo2;
      if (gasEl && prevGas != null) gasEl.value = prevGas;
      const m = botTxt.match(/(\\d+)/);
      const modM = m ? parseInt(m[1], 10) : NaN;
      return { botTxt, modM, expect, fO2, ok: Number.isFinite(modM) && Math.abs(modM - expect) <= 2 };
    } catch (e) {
      return { ok: false, err: String(e) };
    }
  })();

  return out;
}
"""

WORKER_SUITE_JS = """
async () => {
  const lv = [{ depth: 40, time: 25, o2: 21, he: 0 }];
  const dive1Lv = [{ depth: 40, time: 20, o2: 21, he: 0 }];
  const base = {
    metric: true, gfLo: 30, gfHi: 85, stepSize: 3, lastStop: 3, minStopTime: 1,
  };
  const ccr = {
    ...base, circuit: 'CCR', setpoint: 1.3, descentSetpoint: 0.7,
    bottomSetpoint: 1.2, decoSetpoint: 1.3,
  };
  const dive1 = window.ZHLEngine.calculate(dive1Lv, [], base);
  const repTissues = (dive1.finalTissues || []).map(t => ({ pN2: t.pN2, pHe: t.pHe || 0 }));
  const dive1Ok = !dive1.error && repTissues.length === 16;
  const repSettings = {
    ...base,
    _preTissues: repTissues,
    _surfaceInterval: 30,
  };
  const parity = async (settings) => {
    const sync = window.ZHLEngine.calculate(lv, [], settings);
    const worker = await window.ZHLEngine.calculateInWorker(lv, [], settings);
    const stopsMatch = (sync.stops || []).length === (worker.stops || []).length;
    return {
      ok: !sync.error && !worker.error && sync.totalRuntime === worker.totalRuntime
        && sync.tts === worker.tts && stopsMatch,
      syncRt: sync.totalRuntime, workerRt: worker.totalRuntime,
      syncErr: sync.error, workerErr: worker.error,
    };
  };
  const rep = dive1Ok ? await parity(repSettings) : { ok: false, dive1Err: dive1.error, tissueCount: repTissues.length };
  return { dive1Ok, oc: await parity(base), ccr: await parity(ccr), rep };
}
"""


def fin(r: dict | None) -> bool:
    return bool(r and not r.get("error") and not r.get("code") and (r.get("totalRuntime") or 0) > 0)


def run_suite(page) -> dict:
    print("\n── A–I: Engine matrix (sync) ──")
    data = page.evaluate(ENGINE_SUITE_JS)
    s = data["sections"]

    for name, r in s["algos"].items():
        assert_true(
            r and not r.get("error") and not r.get("code") and (r.get("totalRuntime") or 0) > 0,
            f"Algorithm {name} produces finite schedule",
            str(r)[:120],
        )

    w = s["water"]
    assert_true(fin(w["salt"]) and fin(w["fresh"]) and fin(w["en13319"]) and fin(w["custom"]),
                "VPM waterType 0/1/2/3 all produce schedules")
    salt_rt = w["salt"].get("totalRuntime", 0)
    fresh_rt = w["fresh"].get("totalRuntime", 0)
    custom_rt = w["custom"].get("totalRuntime", 0)
    assert_true(
        abs(salt_rt - fresh_rt) > 0.01 or abs(salt_rt - custom_rt) > 0.01,
        "VPM fresh/custom water changes runtime vs salt",
        f"salt={salt_rt} fresh={fresh_rt} custom={custom_rt}",
    )
    assert_near(
        w["custom"].get("totalRuntime"),
        w["customBarOnly"].get("totalRuntime"),
        0.5,
        "VPM custom waterType 3 barPerM consistent",
    )

    zr = s["zhlRep"]
    assert_true(zr["tissuesSaved"], "ZHL dive1 exposes finalTissues")
    assert_true(zr["peekIntact"], "peekZhlRepState non-destructive after ZHLEngine.calculate")
    assert_true(zr["repDiffersFromFresh"], "ZHL rep via _zhlRepState changes runtime vs fresh tissues")
    assert_true(zr["repMatchesExplicit"], "ZHL rep via _zhlRepState matches explicit _preTissues")

    vr = s["vpmRep"]
    assert_true(vr["hasBubble"], "VPM dive1 exposes finalBubbleState")
    assert_true(vr["repDiffers"], "VPM repetitive carry changes runtime vs fresh")

    for name, r in s["rebreather"].items():
        assert_true(fin(r), f"Rebreather {name} produces schedule", str(r)[:120])

    va = s["vpmApi"]
    assert_true(va["loadTypeOk"], "VPMEngine.load is a function")
    assert_true(va["loadReturnOk"], "VPMEngine.load() returns true")
    assert_true(va["gfsStricter"]["ok"], "VPM-B/GFS tighter GFS does not shorten runtime vs loose GFS")

    cr = s["cross"]
    assert_true(cr["bothFinite"] and cr["otuInRange"], "ZHL/VPM OTU finite and in range on 40/25 air")

    gm = s["gasMod"]
    assert_true(gm.get("ok"), "updateGasMODDisplays bot MOD matches calcGasMOD formula", str(gm))

    print("\n── G: Worker parity ──")
    worker = page.evaluate(WORKER_SUITE_JS)
    assert_true(worker.get("dive1Ok"), "Worker rep dive-1 produces 16 finalTissues", str(worker.get("rep")))
    for label, key in [("OC", "oc"), ("CCR", "ccr"), ("ZHL rep state", "rep")]:
        p = worker.get(key) or {}
        assert_true(p.get("ok"), f"Worker parity {label}", str(p))

    return {"sync": data, "worker": worker}


def main() -> int:
    from playwright.sync_api import sync_playwright

    print("=" * 60)
    print("LSP D-Planner — Full engine regression (all algos)")
    print("=" * 60)

    report = {"pass": [], "fail": [], "warn": []}

    with serve_root(ROOT) as base_url:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(240000)
            boot_app_page(page, base_url)
            run_suite(page)
            browser.close()

    report["pass"] = PASS
    report["fail"] = FAIL
    report["warn"] = WARN
    out_path = ROOT / "dev" / "engine_regression_results.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")

    print(f"\n{'─' * 60}")
    print(f"  Results: {len(PASS)} passed, {len(FAIL)} failed, {len(WARN)} warnings")
    print(f"{'─' * 60}\n")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
