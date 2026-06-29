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
from test_http import serve_www  # noqa: E402

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
      ...wBase, waterType: 3, barPerM: (1025 * 9.80665) / 100000,
    }, 'VPMB'),
    customBarOnly: vpm(wLv, [], {
      ...wBase, waterType: 3, barPerM: 0.10052,
    }, 'VPMB'),
    customDensity: vpm(wLv, [], {
      ...wBase, waterType: 3, customWaterDensity: 1025,
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
    ccrVpm: vpm(lv(40, 120, 21, 0), [], ccr, 'VPMB'),
  };

  // ── E2: VPM zero surface interval — bubble carry must not produce NaN ───
  const vpmSi0D1 = vpm(lv(45, 25, 32, 0), [{ o2: 50, he: 0 }], {}, 'VPMB');
  let vpmSi0Rep = null;
  let vpmSi0TissuesOnly = null;
  if (vpmSi0D1.finalBubbleState) {
    vpmSi0Rep = vpm(lv(45, 20, 32, 0), [{ o2: 50, he: 0 }], {
      _preTissues: vpmSi0D1.finalTissues,
      _surfaceInterval: 0,
      _prevBubbleState: vpmSi0D1.finalBubbleState,
      conservatism: 1,
    }, 'VPMB');
    vpmSi0TissuesOnly = vpm(lv(45, 20, 32, 0), [{ o2: 50, he: 0 }], {
      _preTissues: vpmSi0D1.finalTissues,
      _surfaceInterval: 0,
      conservatism: 1,
    }, 'VPMB');
  }
  out.sections.vpmZeroSi = {
    d1Rt: rt(vpmSi0D1),
    repRt: rt(vpmSi0Rep),
    tissueOnlyRt: rt(vpmSi0TissuesOnly),
    repFinite: fin(vpmSi0Rep),
    repNoNan: vpmSi0Rep && Number.isFinite(vpmSi0Rep.totalRuntime),
    repCarriesBubble: vpmSi0Rep && vpmSi0TissuesOnly
      && Math.abs(rt(vpmSi0Rep) - rt(vpmSi0TissuesOnly)) > 0.01,
  };

  // ── E3: Repetitive VPM conservatism sensitivity (issue #106 H-1) ─────
  const vpmRepConsD1 = vpm(lv(45, 25, 32, 0), [{ o2: 50, he: 0 }], {}, 'VPMB');
  const repConsRts = {};
  if (vpmRepConsD1.finalBubbleState) {
    for (const c of [0, 1, 3, 5]) {
      repConsRts['c' + c] = rt(vpm(lv(45, 20, 32, 0), [{ o2: 50, he: 0 }], {
        _preTissues: vpmRepConsD1.finalTissues,
        _surfaceInterval: 45,
        _prevBubbleState: vpmRepConsD1.finalBubbleState,
        conservatism: c,
      }, 'VPMB'));
    }
  }
  out.sections.vpmRepConservatism = {
    rts: repConsRts,
    varies: repConsRts.c0 != null && repConsRts.c5 != null
      && Math.abs(repConsRts.c0 - repConsRts.c5) > 0.01,
  };

  // ── E4: CCR VPM deco setpoints on stops (issue #106 H-2) ─────────────
  out.sections.ccrVpmSetpoints = (() => {
    const r = vpm(lv(40, 30, 21, 0), [], ccr, 'VPMB');
    const stops = (r.plan || []).filter(p => p.type === 'stop' && p.depth >= 6);
    const decoSp = ccr.decoSetpoint;
    const allDecoSp = stops.length > 0 && stops.every(p => (p.setpoint || 0) >= decoSp - 0.01);
    return { stopCount: stops.length, setpoints: stops.map(p => p.setpoint), allDecoSp };
  })();

  // ── E4b: CCR VPM bottom hold setpoint (issue #106 verification H-1) ──
  out.sections.ccrVpmBottomSp = (() => {
    const r = vpm(lv(40, 30, 21, 0), [], ccr, 'VPMB');
    const bottom = (r.plan || []).find(p => p.type === 'bottom');
    const descent = (r.plan || []).find(p => p.type === 'descent');
    return {
      bottomSp: bottom && bottom.setpoint,
      descentSp: descent && descent.setpoint,
      ok: bottom && descent
        && Math.abs(bottom.setpoint - ccr.bottomSetpoint) < 0.01
        && Math.abs(descent.setpoint - ccr.descentSetpoint) < 0.01,
    };
  })();

  // ── E3b: Bubble carry isolated from tissue carry (issue #106 verification H-2)
  out.sections.vpmBubbleCarryIsolated = (() => {
    const d1 = vpm(lv(45, 25, 32, 0), [{ o2: 50, he: 0 }], {}, 'VPMB');
    if (!d1.finalBubbleState || !d1.finalTissues) return { ok: false };
    const repBase = {
      _preTissues: d1.finalTissues,
      _surfaceInterval: 45,
      conservatism: 1,
    };
    const tissueOnly = vpm(lv(45, 20, 32, 0), [{ o2: 50, he: 0 }], repBase, 'VPMB');
    const withBubble = vpm(lv(45, 20, 32, 0), [{ o2: 50, he: 0 }], {
      ...repBase,
      _prevBubbleState: d1.finalBubbleState,
    }, 'VPMB');
    return {
      tissueOnlyRt: rt(tissueOnly),
      withBubbleRt: rt(withBubble),
      ok: Math.abs(rt(tissueOnly) - rt(withBubble)) > 0.01,
    };
  })();

  // ── E5: buhNDL GF High sensitivity (issue #106 M-1) ───────────────────
  out.sections.buhNdlGf = {
    ndl70: buhNDL(18, 0.79, 30, 70),
    ndl85: buhNDL(18, 0.79, 30, 85),
    ndl95: buhNDL(18, 0.79, 30, 95),
  };

  // ── E6: VPM surface interval validation (issue #106 M-2) ───────────────
  out.sections.vpmSiValidate = (() => {
    const repEl = document.getElementById('vpmRepMode');
    const siEl = document.getElementById('vpmSurfaceInterval');
    const prevRep = repEl ? repEl.checked : false;
    const prevSi = siEl ? siEl.value : '60';
    if (repEl) repEl.checked = true;
    if (siEl) siEl.value = '-60';
    const neg = validateVpmSurfaceInterval();
    if (siEl) siEl.value = prevSi;
    if (repEl) repEl.checked = prevRep;
    return { rejectsNegative: !neg.ok };
  })();

  // ── E7: Tec gas mix memory across Rec mode (issue #106 verification M-1) ─
  out.sections.tecGasMixMemory = (() => {
    const sel = document.getElementById('gasMix');
    if (!sel) return { ok: false };
    const savedAlgo = typeof algo !== 'undefined' ? algo : null;
    window._tecGasMix = null;
    algo = 'buh';
    sel.value = 'trimix';
    toggleCustomO2();
    algo = 'padi';
    syncRecGasMixDisplay();
    algo = 'buh';
    sel.value = window._tecGasMix || 'trimix';
    sel.value = 'ean32';
    toggleCustomO2();
    algo = 'padi';
    const persisted = getPersistedGasMix();
    const ok = persisted === 'ean32' && window._tecGasMix === 'ean32';
    if (savedAlgo != null) algo = savedAlgo;
    return { persisted, mem: window._tecGasMix, ok };
  })();

  // ── E8: CCR below-setpoint loop inert (issue #98 H-1 / #120 H-1) ───────
  out.sections.issue98CcrInert = (() => {
    const ppH2O = typeof WATER_VAPOR !== 'undefined' ? WATER_VAPOR : 0.0627;
    const sp = 1.3;
    const pAmb = sp + ppH2O;
    const insp = getInspiredInertPressures(pAmb, sp, 0.21, 0, { circuit: 'CCR', setpoint: sp });
    return {
      pN2: insp.pN2,
      pHe: insp.pHe,
      ok: Math.abs(insp.pN2) < 1e-9 && Math.abs(insp.pHe) < 1e-9,
    };
  })();

  // ── E9: planner trimix O2+He validation (issue #98 H-2) ────────────────
  out.sections.issue98TrimixValidate = (() => {
    const o2El = document.getElementById('plannerTrimixO2');
    const heEl = document.getElementById('plannerTrimixHe');
    const mixEl = document.getElementById('gasMix');
    if (!o2El || !heEl || !mixEl || typeof validatePlannerInputs !== 'function') return { ok: false };
    const prevMix = mixEl.value;
    const prevO2 = o2El.value;
    const prevHe = heEl.value;
    mixEl.value = 'trimix';
    o2El.value = '40';
    heEl.value = '90';
    const bad = validatePlannerInputs();
    o2El.value = prevO2;
    heEl.value = prevHe;
    mixEl.value = prevMix;
    return { ok: !!(bad && !bad.ok) };
  })();

  // ── E10: issue #113 setpoint shallow zone + N2 clamp + hypoxic deco ────
  out.sections.issue113Setpoint = (() => {
    if (typeof getEffectiveSetpointAtDepth !== 'function') return { ok: false };
    const ccr = { circuit: 'CCR', descentSetpoint: 0.7, bottomSetpoint: 1.2, decoSetpoint: 1.3 };
    const sp2 = getEffectiveSetpointAtDepth(2, ccr, 1.01325);
    const sp10 = getEffectiveSetpointAtDepth(10, ccr, 1.01325);
    return { sp2, sp10, ok: sp2 === 0.7 && sp10 === 1.3 };
  })();

  // ── E10a: issue #128 CCR setpoint + inert PP (C-01 / C-02) ─────────────
  out.sections.issue128 = (() => {
    if (typeof getEffectiveSetpointAtDepth !== 'function' || typeof getInspiredInertPressures !== 'function') return { ok: false };
    const surfP = typeof altSurfaceP !== 'undefined' ? altSurfaceP : 1.01325;
    const ppH2O = typeof WATER_VAPOR !== 'undefined' ? WATER_VAPOR : 0.0627;
    const barM = BAR_PER_METRE || 0.1;
    const ccr = { circuit: 'CCR', descentSetpoint: 0.7, bottomSetpoint: 1.2, decoSetpoint: 1.3 };
    const sp50 = getEffectiveSetpointAtDepth(50, ccr, surfP);
    const sp10 = getEffectiveSetpointAtDepth(10, ccr, surfP);
    const c01Ok = sp50 === 1.3 && sp10 === 1.3;
    const sp = 1.3;
    const fO2 = 0.18;
    const fHe = 0.45;
    const fN2d = Math.max(0, 1 - fO2 - fHe);
    const pAmb40 = surfP + 40 * barM;
    const insp = getInspiredInertPressures(pAmb40, sp, fO2, fHe, { circuit: 'CCR', setpoint: sp });
    const pInert = Math.max(0, pAmb40 - sp - ppH2O);
    const den = Math.max(0.001, fN2d + fHe);
    const c02Ok = Math.abs(insp.pN2 + insp.pHe - pInert) < 1e-6
      && Math.abs(insp.pN2 - pInert * fN2d / den) < 1e-6;
    const params = typeof getCCRInertSchreinerParams === 'function'
      ? getCCRInertSchreinerParams(pAmb40, sp, fO2, fHe, 0.01, { circuit: 'CCR', setpoint: sp }) : null;
    const c02bOk = params && Math.abs(params.inspN2Start - pInert * fN2d / den) < 1e-6
      && Math.abs(params.inspHeStart - pInert * fHe / den) < 1e-6;
    return { sp50, sp10, c01Ok, c02Ok, c02bOk, ok: c01Ok && c02Ok && c02bOk };
  })();

  out.sections.issue113N2Clamp = (() => {
    const el = document.getElementById('customO2');
    if (!el || typeof getN2Frac !== 'function') return { ok: false };
    const prev = el.value;
    el.value = '105';
    const fN2 = getN2Frac('custom');
    el.value = prev;
    return { fN2, ok: fN2 === 0 };
  })();

  out.sections.issue113HypoxicDeco = (() => {
    if (typeof validateDomDecoGases !== 'function') return { ok: false };
    const sel = document.getElementById('dg1Mix');
    const o2El = document.getElementById('dg1TrimixO2');
    const heEl = document.getElementById('dg1TrimixHe');
    if (!sel || !o2El || !heEl) return { ok: false };
    const prev = { mix: sel.value, o2: o2El.value, he: heEl.value };
    sel.value = 'trimix';
    o2El.value = '10';
    heEl.value = '0';
    const badTrimix = validateDomDecoGases();
    sel.value = prev.mix;
    o2El.value = prev.o2;
    heEl.value = prev.he;
    return { ok: !!(badTrimix && !badTrimix.ok && badTrimix.errors.some(e => e.code === 'HYPOXIC_DECO_GAS')) };
  })();

  out.sections.issue116HypoxicCustomDeco = (() => {
    if (typeof validateDomDecoGases !== 'function') return { ok: false };
    const sel = document.getElementById('dg1Mix');
    const o2El = document.getElementById('dg1CustomO2');
    if (!sel || !o2El) return { ok: false };
    const prev = { mix: sel.value, o2: o2El.value };
    sel.value = 'custom';
    o2El.value = '10';
    const bad = validateDomDecoGases();
    sel.value = prev.mix;
    o2El.value = prev.o2;
    return { ok: !!(bad && !bad.ok && bad.errors.some(e => e.code === 'HYPOXIC_DECO_GAS')) };
  })();

  out.sections.issue116VpmStopCap = (() => {
    const ml = [{ depth: 60, time: 40, o2: 18, he: 45 }, { depth: 30, time: 10, o2: 21, he: 35 }];
    const r = vpm(ml, [{ o2: 50, he: 0, mod: 0 }], { _vpmMaxStopMin: 0, _vpmTestForceStopCap: true }, 'VPMB');
    return {
      ok: !!(r && r.code === 'VPM_STOP_CAP' && r.error && r.finalTissues == null && (r.plan || []).length > 0),
      code: r && r.code,
      planLen: (r && r.plan || []).length,
    };
  })();

  out.sections.issue113NuclearRegen = (() => {
    const ml = [{ depth: 60, time: 40, o2: 18, he: 45 }, { depth: 30, time: 10, o2: 21, he: 35 }];
    const r = vpm(ml, [{ o2: 50, he: 0, mod: 0 }], {}, 'VPMB');
    if (!fin(r)) return { ok: false, reason: 'no schedule' };
    const plan = r.plan || [];
    const idxShallow = plan.findIndex(s => s.type === 'bottom' && Math.abs((s.depth || 0) - 30) < 0.5);
    const interDeco = idxShallow > 0 && plan.slice(0, idxShallow).some(s => s.type === 'stop');
    return { ok: interDeco && (r.totalRuntime || 0) >= 100, interDeco, rt: r.totalRuntime, idxShallow };
  })();

  // ── E10b: issue #117 mdCompat pSCR runtime + CCR crossover inert ───────
  out.sections.issue117 = (() => {
    const pscrMd = zhl(lv(55, 25, 32, 0), [], {
      circuit: 'pSCR', setpoint: 0, descentSetpoint: 0,
      bottomSetpoint: 0, decoSetpoint: 0, scrLoopVolume: 7, scrMetabolicO2: 0.85,
      bailout: false, mdCompatMode: true,
    });
    const surfP = typeof altSurfaceP !== 'undefined' ? altSurfaceP : 1.01325;
    const ppH2O = typeof WATER_VAPOR !== 'undefined' ? WATER_VAPOR : 0.0627;
    const sp = 1.3;
    const pCross = sp + ppH2O;
    const crossover = getInspiredInertPressures(pCross, sp, 0.21, 0, { circuit: 'CCR', setpoint: sp });
    const crossoverOk = Math.abs(crossover.pN2) < 1e-9 && Math.abs(crossover.pHe) < 1e-9;
    const pAmb40 = surfP + 40 * (BAR_PER_METRE || 0.1);
    const fHe = 0.45;
    const deep = getInspiredInertPressures(pAmb40, sp, 0.18, fHe, { circuit: 'CCR', setpoint: sp });
    const heAboveOk = deep.pHe > 0;
    return { pscrOk: fin(pscrMd), crossoverOk, heAboveOk, ok: fin(pscrMd) && crossoverOk && heAboveOk };
  })();

  // ── E10c: issue #118 altitude setpoint + circuit case + buhNDL zero stop ─
  out.sections.issue118 = (() => {
    const altSurf = 0.74;
    const ccr = { circuit: 'CCR', descentSetpoint: 0.6, bottomSetpoint: 0.65, decoSetpoint: 0.66 };
    const sp30 = getEffectiveSetpointAtDepth(30, ccr, altSurf);
    const spShallow = getEffectiveSetpointAtDepth(3, ccr, altSurf);
    const rbLower = isRebreatherCircuit('ccr') && isRebreatherCircuit('PSCR');
    const lsEl = document.getElementById('lastDecoStop');
    const dsEl = document.getElementById('decoStep');
    let buhZeroOk = false;
    if (lsEl && dsEl && typeof buhNDL === 'function') {
      const prevLs = lsEl.value;
      const prevDs = dsEl.value;
      lsEl.value = '0';
      dsEl.value = '0';
      const ndl0 = buhNDL(20, 0.79, 30, 85, 0);
      lsEl.value = prevLs;
      dsEl.value = prevDs;
      buhZeroOk = Number.isFinite(ndl0) && ndl0 >= 0;
    }
    return {
      sp30, spShallow, rbLower, buhZeroOk,
      ok: sp30 === 0.66 && spShallow === 0.66 && rbLower && buhZeroOk,
    };
  })();

  // ── E10d: issue #119 worker bundle self-contained ppO2 helper ─────────────
  out.sections.issue119 = (() => {
    const bundleOk = typeof getEffectivePpo2 === 'function';
    const ccr = { circuit: 'CCR', setpoint: 1.3, descentSetpoint: 0.7, bottomSetpoint: 1.2, decoSetpoint: 1.3, bailout: false };
    const pAmb = (typeof altSurfaceP !== 'undefined' ? altSurfaceP : 1.01325) + 40 * (typeof BAR_PER_METRE !== 'undefined' ? BAR_PER_METRE : 0.1);
    const ppo2 = bundleOk ? getEffectivePpo2(pAmb, 1.3, 0.21, ccr, 40, 0) : NaN;
    return { bundleOk, ppo2, ok: bundleOk && ppo2 >= 1.2 && ppo2 <= pAmb };
  })();

  // ── E10e: issue #120 circuit canonicalization + dry-gas crossover ─────────
  out.sections.issue120 = (() => {
    const merged = mergeCCRSettings({ circuit: 'PSCR', setpoint: 1.3 });
    const pscrSp = getEffectiveSetpointAtDepth(30, merged, altSurfaceP);
    const ppH2O = typeof WATER_VAPOR !== 'undefined' ? WATER_VAPOR : 0.0627;
    const sp = 1.3;
    const pAmb = sp + ppH2O;
    const insp = getInspiredInertPressures(pAmb, sp, 0.21, 0, { circuit: 'CCR', setpoint: sp });
    const crossoverOk = Math.abs(insp.pN2) < 1e-9 && Math.abs(insp.pHe) < 1e-9;
    return {
      circuit: merged.circuit,
      pscrSp,
      crossoverOk,
      ok: merged.circuit === 'pSCR' && pscrSp === 0 && crossoverOk,
    };
  })();

  // ── E10f: issue #121 trimix UI + dynamic deco card persistence ───────────
  out.sections.issue121 = (() => {
    const mixEl = document.getElementById('gasMix');
    const o2Field = document.getElementById('plannerTrimixO2Field');
    const heField = document.getElementById('plannerTrimixHeField');
    if (!mixEl || !o2Field || !heField || typeof appSettings === 'undefined') return { ok: false };
    const syncHasToggle = String(appSettings._syncUiAfterRestore).includes('toggleCustomO2');
    const prevMix = mixEl.value;
    mixEl.value = 'trimix';
    toggleCustomO2?.();
    const trimixVisible = o2Field.style.display !== 'none' && heField.style.display !== 'none';
    if (typeof restoreDecoGasCardLayout !== 'function') {
      mixEl.value = prevMix;
      toggleCustomO2?.();
      return { syncHasToggle, trimixVisible, ok: false };
    }
    const prevStore = localStorage.getItem('lspDiveSettings_v6');
    const prevHeadless = window._zhlHeadless;
    window._zhlHeadless = false;
    restoreDecoGasCardLayout([1, 2, 3, 5], 6);
    const dg3 = document.getElementById('dg3Mix');
    const dg5 = document.getElementById('dg5Mix');
    if (!dg3 || !dg5) {
      window._zhlHeadless = prevHeadless;
      mixEl.value = prevMix;
      toggleCustomO2?.();
      if (prevStore != null) localStorage.setItem('lspDiveSettings_v6', prevStore);
      else localStorage.removeItem('lspDiveSettings_v6');
      return { syncHasToggle, trimixVisible, ok: false };
    }
    dg3.value = 'ean50';
    dg5.value = 'trimix';
    const dg5O2 = document.getElementById('dg5TrimixO2');
    const dg5He = document.getElementById('dg5TrimixHe');
    if (dg5O2) dg5O2.value = '18';
    if (dg5He) dg5He.value = '45';
    appSettings.save(false);
    const saved = JSON.parse(localStorage.getItem('lspDiveSettings_v6') || '{}');
    const cardsOk = Array.isArray(saved.__decoCardIds) && saved.__decoCardIds.includes(3) && saved.__decoCardIds.includes(5);
    const valuesOk = saved.dg3Mix === 'ean50' && saved.dg5Mix === 'trimix' && saved.dg5TrimixO2 === '18';
    dg3.value = 'none';
    dg5.value = 'none';
    appSettings._restoreFields(saved);
    const restoredIds = getAllDecoGasIds();
    const layoutOk = JSON.stringify(restoredIds) === JSON.stringify(saved.__decoCardIds);
    const restoredOk = document.getElementById('dg3Mix')?.value === 'ean50'
      && document.getElementById('dg5Mix')?.value === 'trimix'
      && document.getElementById('dg5TrimixO2')?.value === '18';
    window._zhlHeadless = prevHeadless;
    mixEl.value = prevMix;
    toggleCustomO2?.();
    if (prevStore != null) localStorage.setItem('lspDiveSettings_v6', prevStore);
    else localStorage.removeItem('lspDiveSettings_v6');
    return {
      syncHasToggle,
      trimixVisible,
      cardsOk,
      valuesOk,
      layoutOk,
      restoredOk,
      ok: syncHasToggle && trimixVisible && cardsOk && valuesOk && layoutOk && restoredOk,
    };
  })();

  // ── E10g: issue #122 gapped dynamic deco card layout restore ─────────────
  out.sections.issue122 = (() => {
    if (typeof restoreDecoGasCardLayout !== 'function' || typeof getAllDecoGasIds !== 'function') return { ok: false };
    getAllDecoGasIds().filter(id => id > 2).forEach(id => removeDecoGasCard(id));
    restoreDecoGasCardLayout([1, 2, 3, 5], 6);
    const ids = getAllDecoGasIds();
    const exact = JSON.stringify(ids) === JSON.stringify([1, 2, 3, 5]);
    const noPhantom4 = !document.getElementById('dgCard_4');
    return { ids, exact, noPhantom4, ok: exact && noPhantom4 };
  })();

  // ── E10h: issue #122 ID reuse — no card IDs above 8 after add/remove ─────
  out.sections.issue122IdReuse = (() => {
    if (typeof addDecoGasCard !== 'function' || typeof removeDecoGasCard !== 'function') return { ok: false };
    getAllDecoGasIds().filter(id => id > 2).forEach(id => removeDecoGasCard(id));
    for (let i = 0; i < 6; i++) addDecoGasCard();
    const filled = getAllDecoGasIds();
    const allLe8 = filled.every(id => id <= 8);
    removeDecoGasCard(3);
    addDecoGasCard();
    const afterReuse = getAllDecoGasIds();
    const reused3 = afterReuse.includes(3) && !afterReuse.includes(9);
    const domOrderOk = JSON.stringify(afterReuse) === JSON.stringify([...afterReuse].sort((a, b) => a - b));
    const card3Pos = Array.from(document.querySelectorAll('.deco-gas-card')).findIndex(c => c.id === 'dgCard_3');
    const card3SlotOk = card3Pos === 2;
    const prevStore = localStorage.getItem('lspDiveSettings_v6');
    const prevHeadless = window._zhlHeadless;
    window._zhlHeadless = false;
    const dg8 = document.getElementById('dg8Mix');
    if (dg8) dg8.value = 'ean50';
    appSettings.save(false);
    const saved = JSON.parse(localStorage.getItem('lspDiveSettings_v6') || '{}');
    if (dg8) dg8.value = 'none';
    appSettings._restoreFields(saved);
    const dg8Restored = document.getElementById('dg8Mix')?.value === 'ean50';
    window._zhlHeadless = prevHeadless;
    if (prevStore != null) localStorage.setItem('lspDiveSettings_v6', prevStore);
    else localStorage.removeItem('lspDiveSettings_v6');
    getAllDecoGasIds().filter(id => id > 2).forEach(id => removeDecoGasCard(id));
    return {
      filled, allLe8, afterReuse, reused3, domOrderOk, card3SlotOk, dg8Saved: saved.dg8Mix === 'ean50', dg8Restored,
      ok: allLe8 && reused3 && domOrderOk && card3SlotOk && saved.dg8Mix === 'ean50' && dg8Restored,
    };
  })();

  // ── E10c: issue #123 engine core audit (CCR + VPM) ─────────────────────
  out.sections.issue123 = (() => {
    const surfP = typeof altSurfaceP !== 'undefined' ? altSurfaceP : 1.01325;
    const ppH2O = typeof WATER_VAPOR !== 'undefined' ? WATER_VAPOR : 0.0627;
    const barM = BAR_PER_METRE || 0.1;
    const sp = 1.3;
    const fO2 = 0.21;
    const fHe = 0.35;
    const pAmb6 = surfP + 6 * barM;
    const loop = typeof ccrLoopGasBelowSetpoint === 'function'
      ? ccrLoopGasBelowSetpoint(pAmb6, fO2, fHe, sp) : null;
    const pDry6 = pAmb6 - ppH2O;
    const fO2dry = Math.min(1, sp / pDry6);
    const loopInertDry = Math.max(0, 1 - fO2dry);
    const fN2d = Math.max(0, 1 - fO2 - fHe);
    const inertSrc = Math.max(0.001, fHe + fN2d);
    const fN2effDry = loopInertDry * (fN2d / inertSrc);
    const c01Ok = loop && Math.abs(loop.pN2 - pDry6 * fN2effDry) < 1e-6
      && Math.abs(loop.pHe - pDry6 * loopInertDry * (fHe / inertSrc)) < 1e-6;
    const pAmbShallow = surfP + 0.1 * barM;
    const pAmbDeep = surfP + 40 * barM;
    const ccr = { circuit: 'pSCR', scrLoopVolume: 7, scrMetabolicO2: 1.5 };
    const frSh = typeof computePSCRFractions === 'function'
      ? computePSCRFractions(pAmbShallow, 0.32, 0, ccr) : null;
    const frDp = typeof computePSCRFractions === 'function'
      ? computePSCRFractions(pAmbDeep, 0.32, 0, ccr) : null;
    const c02Ok = frSh && frDp && frDp.fO2 > frSh.fO2;
    const ccrSp = { circuit: 'CCR', descentSetpoint: 0.7, bottomSetpoint: 1.2, decoSetpoint: 1.3 };
    const m03Ok = typeof getEffectiveSetpointAtDepth === 'function'
      && getEffectiveSetpointAtDepth(2.6, ccrSp, surfP) === 1.2;
    const l03Ok = typeof canonicalCircuit === 'function' && canonicalCircuit('scr') === 'OC';
    const deepMl = [{ depth: 56, time: 20, o2: 18, he: 45 }];
    const vpmDeep = typeof VPMEngine !== 'undefined' && VPMEngine.calculate
      ? VPMEngine.calculate(deepMl, [{ o2: 50, he: 0 }], {}, 'VPMBE') : null;
    const h01Ok = !!(vpmDeep && fin(vpmDeep) && (vpmDeep.totalRuntime || 0) > 0);
    const ccrAsc = zhl(lv(40, 20, 21, 35), [], {
      circuit: 'CCR', descentSetpoint: 0.7, bottomSetpoint: 1.2, decoSetpoint: 1.3, bailout: false,
    });
    const h02Ok = fin(ccrAsc) && (ccrAsc.totalRuntime || 0) > 0;
    const tissues0 = Array.from({ length: 16 }, () => ({ pN2: 0.79, pHe: 0 }));
    const phased = typeof saturateLinearCCR === 'function'
      ? saturateLinearCCR(tissues0, 30, 6, 24, 0.21, 0.35, {
        circuit: 'CCR', descentSetpoint: 0.7, bottomSetpoint: 1.2, decoSetpoint: 1.3, ccrPhase: 'bottom',
      }) : null;
    const h03Ok = phased && phased.some((t, i) => i > 0 && Math.abs(t.pN2 - tissues0[i].pN2) > 1e-6);
    return {
      c01Ok, c02Ok, m03Ok, l03Ok, h01Ok, h02Ok, h03Ok,
      ok: c01Ok && c02Ok && m03Ok && l03Ok && h01Ok && h02Ok && h03Ok,
    };
  })();

  // ── E10d: issue #124 audit fixes ───────────────────────────────────────
  out.sections.issue124 = (() => {
    const tissues = Array.from({ length: 16 }, () => ({ pN2: 1.0, pHe: 0 }));
    const ceilZero = typeof ceiling === 'function' ? ceiling(tissues, 0) : null;
    const h1Ok = ceilZero === 0;
    const parseMin = typeof parseRunMinutes === 'function'
      ? parseRunMinutes('3:30') : NaN;
    const h3Ok = Math.abs(parseMin - 3.5) < 0.01;
    const pscr = typeof computePSCRFractions === 'function'
      ? computePSCRFractions(1.01325, 0.5, 0, { circuit: 'pSCR', scrLoopVolume: 7, scrMetabolicO2: 1.5 }) : null;
    const h5Ok = pscr && pscr.fO2 > 0 && pscr.fO2 <= 0.999;
    const vpmCapNote = !!document.getElementById('vpmStopCapNote');
    const l1Ok = vpmCapNote;
    const syncUi = typeof syncDecoGasCardUi === 'function';
    const m3Ok = syncUi;
    return {
      h1Ok, h3Ok, h5Ok, l1Ok, m3Ok,
      ok: h1Ok && h3Ok && h5Ok && l1Ok && m3Ok,
    };
  })();

  // ── E10e: engine dedup — index delegates match ZhlEngineBundle API ─────
  out.sections.engineDedup = (() => {
    const b = window.ZhlEngineBundle;
    if (!b || typeof b.getEffectivePpo2 !== 'function' || typeof b.normalizeCCRSettings !== 'function') {
      return { ok: false, reason: 'missing ZhlEngineBundle CCR API' };
    }
    const env = typeof getZhlEnvironment === 'function' ? getZhlEnvironment() : {
      altSurfaceP: typeof altSurfaceP !== 'undefined' ? altSurfaceP : 1.01325,
      barPerMetre: typeof BAR_PER_METRE !== 'undefined' ? BAR_PER_METRE : 0.1,
      waterVapor: typeof WATER_VAPOR !== 'undefined' ? WATER_VAPOR : 0.0627,
      altAcclimatized: true,
      allowO2AtMOD: true,
    };
    b.applyEnvironment(env);
    const ccr = { circuit: 'pSCR', scrLoopVolume: 7, scrMetabolicO2: 1.5, bailout: false };
    const pAmb = 3.0;
    const viaDelegate = typeof getEffectivePpo2 === 'function'
      ? getEffectivePpo2(pAmb, 0, 0.21, ccr, 20, 0.35) : null;
    const viaBundle = b.getEffectivePpo2(pAmb, 0, 0.21, b.normalizeCCRSettings(ccr), 20, 0.35);
    const ppo2Ok = viaDelegate != null && Math.abs(viaDelegate - viaBundle) < 1e-6;
    const lv = [{ depth: 40, time: 25, o2: 21, he: 0 }];
    const syncRt = (typeof ZHLEngine !== 'undefined' && ZHLEngine.calculate)
      ? (ZHLEngine.calculate(lv, [], { circuit: 'CCR', setpoint: 1.3, bailout: false }) || {}).totalRuntime : null;
    const bundleRt = b.calculate(lv, [], { circuit: 'CCR', setpoint: 1.3, bailout: false }, b.splitZhlProfileLevels(lv), env).totalRuntime;
    const scheduleOk = syncRt != null && bundleRt != null && Math.abs(syncRt - bundleRt) < 0.5;
    return { ok: ppo2Ok && scheduleOk, ppo2Ok, scheduleOk, viaDelegate, viaBundle, syncRt, bundleRt };
  })();

  // ── E10j: issue #133 audit fixes ───────────────────────────────────────
  out.sections.issue133 = (() => {
    const b = window.ZhlEngineBundle;
    const gfL = b && typeof b.gfAtDepth === 'function' ? b.gfAtDepth(30, 30, 85, 0, 3, false) : null;
    const h1Ok = gfL === 30;
    const hypo = b && typeof b.validateHypoxicDecoGas === 'function'
      ? b.validateHypoxicDecoGas(15, 45, 'dg1') : null;
    const c2Ok = hypo && hypo.ok === false;
    const n2bad = b && typeof b.n2FracFromPercentages === 'function'
      ? b.n2FracFromPercentages(60, 50) : 0;
    const l2Ok = n2bad === null;
    const sgEl = document.getElementById('shallowGradient');
    const prevSg = sgEl ? sgEl.value : null;
    let c4Ok = false;
    if (sgEl && typeof isShallowGradientOn === 'function') {
      sgEl.value = 'on';
      const on = isShallowGradientOn();
      sgEl.value = 'off';
      const off = isShallowGradientOn();
      if (prevSg != null) sgEl.value = prevSg;
      c4Ok = on === true && off === false;
    }
    const wrapGas = typeof getActiveGas === 'function' && b
      ? (() => {
          const lim = fo2 => (fo2 >= 1 ? 1.6 : 1.4);
          const g = getActiveGas(39, 0.21, 0.35, [], lim, 'Tx21/35');
          return g && Math.abs((g.fHe || 0) - 0.35) < 0.01;
        })()
      : false;
    const vpmSnap = false;
    return { h1Ok, c2Ok, l2Ok, c4Ok, wrapGas, ok: h1Ok && c2Ok && l2Ok && c4Ok && wrapGas };
  })();

  // ── E10i: getActiveGas passes fO2 to ppO2 limit bands (audit 2026-06-29 H-1) ─
  out.sections.getActiveGasF02Limit = (() => {
    if (typeof ZhlEngineBundle === 'undefined' || typeof ZhlEngineBundle.getActiveGas !== 'function') return { ok: false };
    const env = typeof getZhlEnvironment === 'function' ? getZhlEnvironment() : {
      altSurfaceP: typeof altSurfaceP !== 'undefined' ? altSurfaceP : 1.01325,
      barPerMetre: typeof BAR_PER_METRE !== 'undefined' ? BAR_PER_METRE : 0.1,
      waterVapor: typeof WATER_VAPOR !== 'undefined' ? WATER_VAPOR : 0.0627,
      altAcclimatized: true,
      allowO2AtMOD: true,
    };
    ZhlEngineBundle.applyEnvironment(env);
    const limitFn = (fO2) => {
      const pct = fO2 * 100;
      if (pct >= 45) return 1.6;
      if (pct >= 28) return 1.5;
      return 1.4;
    };
    const ean32 = [{ depth: 0, fO2: 0.32, fN2: 0.68, fHe: 0, label: 'EAN32' }];
    const pick = ZhlEngineBundle.getActiveGas(39, 0.79, 0, ean32, limitFn, 'Air');
    const ok = pick && pick.label === 'Air';
    return { label: pick && pick.label, ok };
  })();

  // ── E11: issue #112 planner BT vs descent validation ───────────────────
  out.sections.issue112PlannerBt = (() => {
    const depthEl = document.getElementById('depth');
    const btEl = document.getElementById('bt');
    const rateEl = document.getElementById('descentRate');
    if (!depthEl || !btEl || typeof validatePlannerInputs !== 'function') return { ok: false };
    const prevD = depthEl.value;
    const prevBt = btEl.value;
    const prevRate = rateEl ? rateEl.value : null;
    depthEl.value = '40';
    btEl.value = '1';
    if (rateEl) rateEl.value = '20';
    const bad = validatePlannerInputs();
    depthEl.value = prevD;
    btEl.value = prevBt;
    if (rateEl && prevRate != null) rateEl.value = prevRate;
    return { ok: !!(bad && !bad.ok) };
  })();

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
      else expect = Math.floor((ppLim / fO2 - (window.altSurfaceP || 1.01325)) / (window.BAR_PER_METRE || 0.1));
      if (ppo2El && prevPpo2 != null) ppo2El.value = prevPpo2;
      if (gasEl && prevGas != null) gasEl.value = prevGas;
      const m = botTxt.match(/(\\d+)/);
      const modM = m ? parseInt(m[1], 10) : NaN;
      return { botTxt, modM, expect, fO2, ok: Number.isFinite(modM) && Math.abs(modM - expect) <= 2 };
    } catch (e) {
      return { ok: false, err: String(e) };
    }
  })();

  // ── J: Issue #110 timeline / formatter contracts ───────────────────────
  const planParity = r => {
    const p = r.plan || [];
    const tr = r.totalRuntime || 0;
    let sum = 0;
    let lastRun = 0;
    for (const seg of p) {
      sum += seg.time || 0;
      if (seg.run != null) lastRun = seg.run;
    }
    const tol = Math.max(0.6, tr * 0.02);
    return { tr, sum, lastRun, ok: Math.abs(lastRun - tr) <= tol && Math.abs(sum - tr) <= tol };
  };
  out.sections.timeline110 = {
    zhl4025: planParity(zhl(air40, [])),
    zhl3025: planParity(zhl(lv(30, 25, 21, 0), [])),
    schreiner: planParity(zhl(air40, [], { mdCompatMode: false })),
    toMMSSvpm: (() => {
      const rt = 61;
      const s = typeof toMMSS === 'function' ? toMMSS(rt) : '';
      const mins = parseInt(String(s).split("'")[0], 10);
      return { s, mins, ok: mins >= 60 && mins <= 62 };
    })(),
    bottomNoDoubleDescent: (() => {
      const r = zhl(air40, []);
      const bot = (r.plan || []).find(s => s.type === 'bottom');
      const descentTime = 40 / 20;
      const expectBottom = Math.max(0, 25 - descentTime);
      return { bottomTime: bot?.time, expectBottom, ok: bot && Math.abs(bot.time - expectBottom) < 0.1 };
    })(),
    ccrMl: planParity(zhl([
      { depth: 60, time: 20, o2: 18, he: 45 },
      { depth: 42, time: 8, o2: 18, he: 45 },
    ], [], {
      circuit: 'CCR', setpoint: 1.3, descentSetpoint: 0.7, bottomSetpoint: 1.3, decoSetpoint: 1.3,
      gfLo: 35, gfHi: 75, mdCompatMode: true,
    })),
  };

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
    assert_near(
        w["customDensity"].get("totalRuntime"),
        w["customBarOnly"].get("totalRuntime"),
        0.5,
        "VPM customWaterDensity fallback matches barPerM",
    )

    zr = s["zhlRep"]
    assert_true(zr["tissuesSaved"], "ZHL dive1 exposes finalTissues")
    assert_true(zr["peekIntact"], "peekZhlRepState non-destructive after ZHLEngine.calculate")
    assert_true(zr["repDiffersFromFresh"], "ZHL rep via _zhlRepState changes runtime vs fresh tissues")
    assert_true(zr["repMatchesExplicit"], "ZHL rep via _zhlRepState matches explicit _preTissues")

    vr = s["vpmRep"]
    assert_true(vr["hasBubble"], "VPM dive1 exposes finalBubbleState")
    assert_true(vr["repDiffers"], "VPM repetitive carry changes runtime vs fresh")

    vz = s["vpmZeroSi"]
    assert_true(vz["repFinite"] and vz["repNoNan"], "VPM zero surface interval produces finite schedule (no NaN)")
    assert_true(vz.get("repCarriesBubble"), "VPM zero-SI repetitive dive carries bubble state (issue #104 H-1)")

    vrc = s.get("vpmRepConservatism", {})
    assert_true(vrc.get("varies"), "Repetitive VPM runtime responds to conservatism (issue #106 H-1)", str(vrc))

    cs = s.get("ccrVpmSetpoints", {})
    assert_true(cs.get("allDecoSp"), "CCR VPM stops use deco setpoint (issue #106 H-2)", str(cs))

    cb = s.get("ccrVpmBottomSp", {})
    assert_true(cb.get("ok"), "CCR VPM bottom hold uses bottom setpoint (issue #106 verify H-1)", str(cb))

    bi = s.get("vpmBubbleCarryIsolated", {})
    assert_true(bi.get("ok"), "VPM bubble carry differs from tissue-only carry (issue #106 verify H-2)", str(bi))

    ng = s.get("buhNdlGf", {})
    assert_true(
        ng.get("ndl85", 0) > ng.get("ndl70", 0) or ng.get("ndl95", 0) > ng.get("ndl70", 0),
        "buhNDL NDL increases with GF High (issue #106 M-1)",
        str(ng),
    )

    sv = s.get("vpmSiValidate", {})
    assert_true(sv.get("rejectsNegative"), "validateVpmSurfaceInterval rejects negative SI (issue #106 M-2)", str(sv))

    tg = s.get("tecGasMixMemory", {})
    assert_true(tg.get("ok"), "Tec gasMix memory tracks EAN32 after trimix (issue #106 verify M-1)", str(tg))

    i98i = s.get("issue98CcrInert", {})
    assert_true(i98i.get("ok"), "CCR below-setpoint zero inert at O2-max crossover (issue #98 H-1 / #120 H-1)", str(i98i))
    i98t = s.get("issue98TrimixValidate", {})
    assert_true(i98t.get("ok"), "validatePlannerInputs rejects O2+He>100% trimix (issue #98 H-2)", str(i98t))

    i112 = s.get("issue112PlannerBt", {})
    assert_true(i112.get("ok"), "validatePlannerInputs rejects BT shorter than descent (issue #112 L-3)", str(i112))

    i113s = s.get("issue113Setpoint", {})
    assert_true(i113s.get("ok"), "CCR setpoint zones: descSP shallow, decoSP at 10 m (issue #113 / #128 C-01)", str(i113s))
    i113n = s.get("issue113N2Clamp", {})
    assert_true(i113n.get("ok"), "getN2Frac custom clamps O2>100 to fN2=0 (issue #113 M-7)", str(i113n))
    i113h = s.get("issue113HypoxicDeco", {})
    assert_true(i113h.get("ok"), "validateDomDecoGases rejects hypoxic trimix deco (issue #113 H-3)", str(i113h))
    i116h = s.get("issue116HypoxicCustomDeco", {})
    assert_true(i116h.get("ok"), "validateDomDecoGases rejects custom 10% O2 deco (issue #116 H-1)", str(i116h))
    i116v = s.get("issue116VpmStopCap", {})
    assert_true(i116v.get("ok"), "VPM stop cap returns VPM_STOP_CAP with partial plan for UI warning (issue #116 / #127 M-6)", str(i116v))
    i113r = s.get("issue113NuclearRegen", {})
    assert_true(i113r.get("ok"), "VPM ML inter-level deco excludes deco from nuclear regen path (issue #113 M-2)", str(i113r))
    i117 = s.get("issue117", {})
    assert_true(i117.get("ok"), "mdCompat pSCR schedule + CCR crossover/deep inert (issue #117 / #120)", str(i117))
    i118 = s.get("issue118", {})
    assert_true(i118.get("ok"), "altitude setpoint zones + circuit case + buhNDL zero stop (issue #118)", str(i118))
    i119 = s.get("issue119", {})
    assert_true(i119.get("ok"), "getEffectivePpo2 available in main bundle (issue #119 BUG-02)", str(i119))
    i120 = s.get("issue120", {})
    assert_true(i120.get("ok"), "PSCR canonicalization + dry-gas crossover (issue #120)", str(i120))
    i121 = s.get("issue121", {})
    assert_true(i121.get("ok"), "trimix UI sync + dynamic deco card value persistence (issue #121)", str(i121))
    i122 = s.get("issue122", {})
    assert_true(i122.get("ok"), "gapped dynamic deco card layout restores exact ID set (issue #122)", str(i122))
    i122r = s.get("issue122IdReuse", {})
    assert_true(i122r.get("ok"), "deco card IDs reuse slots 3–8 and dg8 values persist (issue #122 ID reuse)", str(i122r))
    i128 = s.get("issue128", {})
    assert_true(i128.get("ok"), "CCR setpoint at depth + trimix inert PP paths (issue #128 C-01/C-02)", str(i128))
    i123 = s.get("issue123", {})
    assert_true(i123.get("ok"), "issue #123 engine audit fixes (CCR shallow/pSCR/VPM)", str(i123))
    i124 = s.get("issue124", {})
    assert_true(i124.get("ok"), "issue #124 audit fixes (ceiling/gfAt/contingency/pSCR/UI)", str(i124))
    i133 = s.get("issue133", {})
    assert_true(i133.get("ok"), "issue #133 audit fixes (gfAtDepth/hypoxic/getActiveGas/shallowGF)", str(i133))
    dedup = s.get("engineDedup", {})
    assert_true(dedup.get("ok"), "index CCR delegates match ZhlEngineBundle (engine dedup)", str(dedup))
    gag = s.get("getActiveGasF02Limit", {})
    assert_true(gag.get("ok"), "getActiveGas uses fO2 for ppO2 limit bands (audit H-1)", str(gag))

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

    t110 = s.get("timeline110", {})
    assert_true(t110.get("toMMSSvpm", {}).get("ok"), "toMMSS accepts minutes not seconds (issue #110 H-1)", str(t110.get("toMMSSvpm")))
    assert_true(t110.get("bottomNoDoubleDescent", {}).get("ok"), "ZHL headless bottom excludes descent time (issue #110 H-2)", str(t110.get("bottomNoDoubleDescent")))
    for key in ("zhl4025", "zhl3025", "schreiner", "ccrMl"):
        assert_true(t110.get(key, {}).get("ok"), f"ZHL plan timeline parity {key} (issue #110 H-3/L-1)", str(t110.get(key)))

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

    with serve_www(ROOT) as base_url:
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
