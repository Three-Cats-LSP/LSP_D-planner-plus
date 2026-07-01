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


ENGINE_SUITE_JS = r"""
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
  out.sections.buhNdlGf = (() => {
    if (typeof buhNDL !== 'function') return { ok: false, ndl70: null, ndl85: null, ndl95: null };
    const ndl70 = buhNDL(18, 0.79, 30, 70);
    const ndl85 = buhNDL(18, 0.79, 30, 85);
    const ndl95 = buhNDL(18, 0.79, 30, 95);
    return { ok: true, ndl70, ndl85, ndl95 };
  })();

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
    appSettings._restoreInProgress = false;
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
    const gfH = b && typeof b.gfAtDepth === 'function' ? b.gfAtDepth(30, 30, 85, 0, 3, false) : null;
    const h1Ok = gfH === 85;
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

  // ── E10k: issue #134 audit fixes ───────────────────────────────────────
  out.sections.issue134 = (() => {
    const b = window.ZhlEngineBundle;
    const domFn = typeof validateDomDecoGases === 'function' ? validateDomDecoGases.toString() : '';
    const c1Ok = domFn.length > 0 && !/validateHypoxicDecoGas\\s*\\(\\s*bot\\.o2\\)/.test(domFn);
    const gfH = b && typeof b.gfAtDepth === 'function' ? b.gfAtDepth(30, 30, 85, 0, 3, false) : null;
    const h1Ok = gfH === 85;
    const ppo2Val = b && typeof b.ppO2Check === 'function' ? b.ppO2Check(30, 0.79, 0) : null;
    const m7Ok = typeof ppo2Val === 'number' && Number.isFinite(ppo2Val);
    const sg = document.getElementById('shallowGradient');
    const prevSg = sg ? sg.value : null;
    let shallowNdlOk = false;
    if (b && typeof b.gfAtDepth === 'function') {
      const gfOff = b.gfAtDepth(3, 0.3, 0.85, 9, 3, false);
      const gfOn = b.gfAtDepth(3, 0.3, 0.85, 9, 3, true);
      shallowNdlOk = gfOff !== gfOn;
    }
    const saveGuard = typeof appSettings !== 'undefined' && String(appSettings.save).includes('_restoreInProgress');
    return {
      c1Ok, h1Ok, m7Ok, shallowNdlOk, saveGuard,
      ok: c1Ok && h1Ok && m7Ok && shallowNdlOk && saveGuard,
    };
  })();

  // ── E10j: issue #135 audit fixes (Audit #130) ────────────────────────────
  out.sections.issue135 = (() => {
    const b = window.ZhlEngineBundle;
    const ppFn = typeof ppO2Check === 'function' ? ppO2Check.toString() : '';
    const h6Ok = ppFn.length > 0 && !/\\.toFixed\\(2\\)/.test(ppFn.split('return')[1] || '');
    const ppo2Val = typeof ppO2Check === 'function' ? ppO2Check(30, 0.79, 0) : null;
    const h6NumOk = typeof ppo2Val === 'number' && Number.isFinite(ppo2Val);
    const rcsFn = typeof runContingencyScenario === 'function' ? runContingencyScenario.toString() : '';
    const h1Ok = (/let ok = false/.test(rcsFn) && /ok:\\s*false/.test(rcsFn)) || (() => {
      try {
        const r = typeof runContingencyScenario === 'function' ? runContingencyScenario(() => {}) : null;
        return !!(r && r.ok === false && r.newRows === '');
      } catch (e) { return false; }
    })();
    const h8Ok = /parseRunMinutes\\(stopTxt\\)/.test(rcsFn) || /data-label="Stop"/.test(rcsFn);
    const rdFn = typeof runDecoSchedule === 'function' ? runDecoSchedule.toString() : '';
    const m2Ok = /!_contingencyRunning/.test(rdFn.split('validateDecoInputs', 1)[0] || rdFn.slice(0, 800));
    const repFn = typeof saveZhlRepState === 'function' ? saveZhlRepState.toString() : '';
    const h4Ok = /totalCNS/.test(repFn) && /totalOTU/.test(repFn);
    const endSubAir = typeof calcEND === 'function' ? calcEND(30, 0.21, 0.35) : null;
    const l6Ok = endSubAir === 0;
    return { h1Ok, h6Ok: h6Ok && h6NumOk, h8Ok, m2Ok, h4Ok, l6Ok, ok: h1Ok && h6Ok && h6NumOk && h8Ok && m2Ok && h4Ok };
  })();

  // ── E10k: issue #137 audit fixes ───────────────────────────────────────
  out.sections.issue137 = (() => {
    const b = window.ZhlEngineBundle;
    const hypoCcr = b && typeof b.validateHypoxicDecoGas === 'function'
      ? b.validateHypoxicDecoGas(15, 55, 'dg1', 'CCR') : null;
    const hypoOc = b && typeof b.validateHypoxicDecoGas === 'function'
      ? b.validateHypoxicDecoGas(15, 55, 'dg1', 'OC') : null;
    const m17Ok = hypoCcr === null && !!(hypoOc && hypoOc.code === 'HYPOXIC_DECO_GAS');
    const schedSrc = b && typeof b.runZhlScheduleCore === 'function' ? b.runZhlScheduleCore.toString() : '';
    const h7Ok = schedSrc.includes('firstStopDepth <= 0) return gfL');
    const vpmD1 = vpm([{ depth: 45, time: 25, o2: 32, he: 0 }], [{ o2: 50, he: 0 }], {}, 'VPMB');
    let m19Ok = false;
    if (vpmD1 && vpmD1.finalBubbleState) {
      const cloned = JSON.parse(JSON.stringify(vpmD1.finalBubbleState));
      const rep = vpm([{ depth: 45, time: 20, o2: 32, he: 0 }], [{ o2: 50, he: 0 }], {
        _prevBubbleState: cloned, _surfaceInterval: 60,
      }, 'VPMB');
      m19Ok = !!(rep && !rep.error && rep.totalRuntime > 0);
    }
    const h6Ok = typeof window.VPMEngine.calculateInWorker !== 'function';
    const rcsFn = typeof runContingencyScenario === 'function' ? runContingencyScenario.toString() : '';
    const m11Ok = /origBailout/.test(rcsFn);
    let m20Ok = false;
    if (typeof runContingencyScenario === 'function' && typeof runDecoSchedule === 'function') {
      try {
        runDecoSchedule();
        const res = runContingencyScenario(() => {});
        m20Ok = !!(res && (res.ok === false || (res.ok && res.newRows && res.newRows.length > 0)));
      } catch (e) { m20Ok = false; }
    }
    return { m17Ok, h7Ok, m19Ok, h6Ok, m11Ok, m20Ok, ok: m17Ok && h7Ok && m19Ok && h6Ok && m11Ok && m20Ok };
  })();

  // ── E10l: issue #138 audit fixes (Audit #132) ────────────────────────────
  out.sections.issue138 = (() => {
    const rdFn = typeof runDecoSchedule === 'function' ? runDecoSchedule.toString() : '';
    const h2Ok = rdFn.includes('escapeHtmlText(err.message');
    const m1Ok = rdFn.includes('!_contingencyRunning && isCcrGasUiMode()');
    const vpmFn = typeof runVPMSchedule === 'function' ? runVPMSchedule.toString() : '';
    const h8Ok = vpmFn.includes('time: btAtDepthMin');
    const repFn = typeof getZhlRepStateForSchedule === 'function' ? getZhlRepStateForSchedule.toString() : '';
    const h7Ok = repFn.includes('totalCNS: snap.totalCNS') && repFn.includes('totalOTU: snap.totalOTU');
    const b = window.ZhlEngineBundle;
    const l9Ok = b && typeof b.n2FracFromPercentages === 'function'
      ? b.n2FracFromPercentages(60, 50) === null : false;
    return { h7Ok, h2Ok, m1Ok, h8Ok, l9Ok, ok: h7Ok && h2Ok && m1Ok && h8Ok && l9Ok };
  })();

  // ── E10m: issue #139 audit fixes (Audit #133) ────────────────────────────
  out.sections.issue139 = (() => {
    const bot = document.getElementById('ccrBottomSetpoint');
    const dec = document.getElementById('ccrDecoSetpoint');
    const l1Ok = !!(bot && bot.getAttribute('oninput') && bot.getAttribute('oninput').includes('appSettings.save(false)')
      && dec && dec.getAttribute('oninput') && dec.getAttribute('oninput').includes('appSettings.save(false)'));
    const rdFn = typeof runDecoSchedule === 'function' ? runDecoSchedule.toString() : '';
    const safetySlice = rdFn.split("s.type === 'safety'")[1] || '';
    const l2Ok = safetySlice.includes('pO2Val.toFixed(2)');
    const gfFn = typeof setCustomGF === 'function' ? setCustomGF.toString() : '';
    const l3Ok = gfFn.includes('lowInput.value = String(low)') && gfFn.includes('low > high');
    return { l1Ok, l2Ok, l3Ok, ok: l1Ok && l2Ok && l3Ok };
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
      const m = botTxt.match(/(\d+)/);
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

  // ── multi-level continuation gas + headless bottom labels ───────────────
  out.sections.mlContGas = (() => {
    const decoGases = [{ o2: 50, he: 0 }];
    const r = zhl([
      { depth: 20, time: 25, o2: 21, he: 0 },
      { depth: 10, time: 5, o2: 50, he: 0 },
    ], decoGases);
    const plan = r.plan || [];
    const hold10 = plan.find(s => s.type === 'bottom' && s.depth === 10);
    let seenHold = false;
    let ascAfterHold = null;
    for (const s of plan) {
      if (s === hold10) { seenHold = true; continue; }
      if (seenHold && s.type === 'ascent') { ascAfterHold = s; break; }
    }
    const gasOk = hold10?.gas === 'EAN50' && ascAfterHold?.gas === 'EAN50';
    const expectMainRate = (10 - base.lastStop) / base.ascentRate;
    const rateOk = ascAfterHold && Math.abs(ascAfterHold.time - expectMainRate) < 0.15;
    const notDecoRate = !ascAfterHold || Math.abs(ascAfterHold.time - (10 - base.lastStop) / base.decoAscentRate) > 0.3;
    return {
      holdGas: hold10?.gas, ascGas: ascAfterHold?.gas, ascTime: ascAfterHold?.time,
      gasOk, rateOk, notDecoRate, ok: gasOk && rateOk && notDecoRate,
    };
  })();
  out.sections.mlBottomLabel = (() => {
    const r = zhl([{ depth: 20, time: 25, o2: 21, he: 0 }], [{ o2: 50, he: 0 }]);
    const descent = (r.plan || []).find(s => s.type === 'descent');
    const bottom = (r.plan || []).find(s => s.type === 'bottom');
    const labelOk = descent?.gas === 'Air' && bottom?.gas === 'Air';
    const o2Ok = descent?.o2 === 21 && bottom?.o2 === 21;
    return { descentGas: descent?.gas, bottomGas: bottom?.gas, labelOk, o2Ok, ok: labelOk && o2Ok };
  })();

  // ── Cycle 7 audit fixes (contingency, SW, adv settings) ─────────────────
  out.sections.cycle7 = (() => {
    const rcsFn = typeof runContingencyScenario === 'function' ? runContingencyScenario.toString() : '';
    const h1SrcOk = !/savedBody/.test(rcsFn) && (/withScratchDecoTableBody/.test(rcsFn) || /scratchTbody/.test(rcsFn));
    let h1FuncOk = false;
    if (typeof runContingencyScenario === 'function' && typeof runDecoSchedule === 'function') {
      const wasHeadless = window._zhlHeadless;
      window._zhlHeadless = false;
      try {
        runDecoSchedule();
        const tbody = document.getElementById('decoTableBody');
        if (tbody) {
          const saved = tbody.innerHTML;
          tbody.innerHTML = saved + '<tr data-phase="marker"><td>KEEP</td></tr>';
          runContingencyScenario(() => {});
          h1FuncOk = tbody.innerHTML.includes('KEEP');
          tbody.innerHTML = saved;
        }
      } catch (_) { h1FuncOk = false; }
      finally { window._zhlHeadless = wasHeadless; }
    }
    const calcFn = typeof calcContingency === 'function' ? calcContingency.toString() : '';
    const h2SrcOk = /origCircuit/.test(rcsFn) && !/origBT\)/.test(calcFn.split('runContingencyScenario')[0] || '');
    let h2ThrowOk = false;
    if (typeof runContingencyScenario === 'function') {
      try {
        const depthEl = document.getElementById('decoDepth');
        const btEl = document.getElementById('decoBT');
        const prevD = depthEl ? depthEl.value : null;
        const prevB = btEl ? btEl.value : null;
        runContingencyScenario(() => { throw new Error('cycle7 probe'); });
        h2ThrowOk = depthEl && btEl && prevD != null && depthEl.value === prevD && btEl.value === prevB;
      } catch (_) { h2ThrowOk = false; }
    }
    const slateFn = typeof buildContingencySlateText === 'function' ? buildContingencySlateText.toString() : '';
    const m1Ok = /data-label=/.test(slateFn) && !/tds\[4\]/.test(slateFn);
    const m2Ok = /origCircuit/.test(rcsFn);
    const pdfFn = typeof exportContingencyPDF === 'function' ? exportContingencyPDF.toString() : '';
    const m3Ok = /const emTissues = c\.contLastTissues;/.test(pdfFn)
      && !/contLastTissues \|\|/.test(pdfFn)
      && !/typeof lastTissues/.test(pdfFn);
    const m4Ok = /buildProfileLegendRowsFromWaypoints/.test(pdfFn);
    let l4Ok = false;
    if (typeof syncMinStopTimeRounding === 'function') {
      const rnd = document.getElementById('stopRounding');
      const sub = document.getElementById('minStopTimeSubMin');
      const sel = document.getElementById('minStopTime');
      if (rnd && sub && sel) {
        const prevR = rnd.value;
        const prevS = sel.value;
        rnd.value = 'wholeminute';
        syncMinStopTimeRounding();
        l4Ok = sub.disabled === true;
        rnd.value = prevR;
        sel.value = prevS;
        syncMinStopTimeRounding();
      }
    }
    const h1Ok = h1SrcOk && h1FuncOk;
    const h2Ok = h2SrcOk && h2ThrowOk;
    return { h1Ok, h2Ok, m1Ok, m2Ok, m3Ok, m4Ok, l4Ok, ok: h1Ok && h2Ok && m1Ok && m2Ok && m3Ok && m4Ok && l4Ok };
  })();

  // ── Cycle 7b re-read fixes (PDF export DOM isolation) ───────────────────
  out.sections.cycle7b = (() => {
    const pdfFn = typeof exportContingencyPDF === 'function' ? exportContingencyPDF.toString() : '';
    const h1Ok = /withScratchDecoTableBody/.test(pdfFn)
      && !/decoTableBody'\)\.innerHTML = c\.newRows/.test(pdfFn)
      && !/getElementById\('decoTableBody'\)\.innerHTML = saved/.test(pdfFn);
    const m1Ok = /savedTissueHtml/.test(pdfFn) && /ttbEm\.innerHTML = savedTissueHtml/.test(pdfFn);
    const slateFn = typeof buildContingencySlateText === 'function' ? buildContingencySlateText.toString() : '';
    const l1Ok = !/dateStr/.test(slateFn);
    const legFn = typeof legendRowFromTr === 'function' ? legendRowFromTr.toString() : '';
    const l2Ok = /data-label=/.test(legFn) && /legendRowFromTr/.test(typeof drawGraphLegend === 'function' ? drawGraphLegend.toString() : '');
    const helperOk = typeof withScratchDecoTableBody === 'function';
    return { h1Ok, m1Ok, l1Ok, l2Ok, helperOk, ok: h1Ok && m1Ok && l1Ok && l2Ok && helperOk };
  })();

  // ── Cycle 7 official scope (settings controls + VPM runner + ENG-VPM) ─────
  out.sections.cycle7Official = (() => {
    const lv = [{ depth: 40, time: 20, o2: 21, he: 0 }];
    const deco = [{ o2: 50, he: 0 }];
    const baseVpm = { metric: true, minStopTime: 1, stepSize: 3, lastStop: 3, descentRate: 20, ascentRate: 10, decoAscentRate: 3 };

    let exposureCarryOk = false;
    if (window.VPMEngine && typeof VPMEngine.calculate === 'function') {
      const d1 = VPMEngine.calculate(lv, deco, baseVpm, 'VPMB');
      const preOTU = d1.totalOTU || 0;
      const preCNS = d1.totalCNS || 0;
      const d2 = VPMEngine.calculate(lv, deco, { ...baseVpm, _preOTU: preOTU, _preCNS: preCNS, _surfaceInterval: 0 }, 'VPMB');
      exposureCarryOk = !d2.error && d2.totalOTU > preOTU + 0.01 && d2.totalCNS >= preCNS;
    }

    let stateValidationOk = false;
    if (window.VPMEngine) {
      const fresh = VPMEngine.calculate(lv, deco, baseVpm, 'VPMB');
      const badTissue = VPMEngine.calculate(lv, deco, {
        ...baseVpm,
        _preTissues: Array.from({ length: 16 }, () => ({ pN2: NaN, pHe: 0 })),
      }, 'VPMB');
      const negTissue = VPMEngine.calculate(lv, deco, {
        ...baseVpm,
        _preTissues: Array.from({ length: 16 }, (_, i) => ({ pN2: i === 0 ? -1 : 0.79, pHe: 0 })),
      }, 'VPMB');
      const badBubble = VPMEngine.calculate(lv, deco, {
        ...baseVpm,
        _prevBubbleState: {
          adjustedCritRadiiN2: Array(16).fill(NaN),
          adjustedCritRadiiHe: Array(16).fill(0),
          regeneratedRadiiN2: Array(16).fill(0),
          regeneratedRadiiHe: Array(16).fill(0),
        },
      }, 'VPMB');
      const zeroBubble = VPMEngine.calculate(lv, deco, {
        ...baseVpm,
        _prevBubbleState: {
          adjustedCritRadiiN2: Array(16).fill(0.000001),
          adjustedCritRadiiHe: Array(16).fill(0.000001),
          regeneratedRadiiN2: Array(16).fill(0),
          regeneratedRadiiHe: Array(16).fill(0.000001),
        },
      }, 'VPMB');
      stateValidationOk = !fresh.error
        && badTissue.code === 'INVALID_REPETITIVE_STATE'
        && negTissue.code === 'INVALID_REPETITIVE_STATE'
        && badBubble.code === 'INVALID_REPETITIVE_STATE'
        && zeroBubble.code === 'INVALID_REPETITIVE_STATE';
    }

    let settingsValidationOk = false;
    if (window.VPMEngine) {
      const badRate = VPMEngine.calculate(lv, deco, { ...baseVpm, descentRate: -5 }, 'VPMB');
      const badStep = VPMEngine.calculate(lv, deco, { ...baseVpm, stepSize: 0 }, 'VPMB');
      settingsValidationOk = badRate.code === 'INVALID_VPM_SETTINGS' && badStep.code === 'INVALID_VPM_SETTINGS';
    }

    let altitudeExposureOk = false;
    if (window.VPMEngine) {
      const sea = VPMEngine.calculate(lv, deco, { ...baseVpm, altitude: 0, altSurfaceP: 1.01325 }, 'VPMB');
      const alt = VPMEngine.calculate(lv, deco, { ...baseVpm, altitude: 2000, altSurfaceP: 0.77 }, 'VPMB');
      altitudeExposureOk = !sea.error && !alt.error && Math.abs((sea.totalOTU || 0) - (alt.totalOTU || 0)) > 0.01;
    }

    let imperialResetOk = false;
    const prevUnits = typeof units !== 'undefined' ? units : 'metric';
    if (typeof _factoryDefaultsForUnits === 'function' && typeof setUnits === 'function') {
      setUnits('imperial');
      const imp = _factoryDefaultsForUnits();
      imperialResetOk = parseFloat(imp.sacBottom) < 5 && parseInt(imp.cylBot_pres, 10) > 1000;
      setUnits(prevUnits);
    }

    const rdsFn = typeof _doResetToDefaults === 'function' ? _doResetToDefaults.toString() : '';
    const personalDefaultsOk = /userDefaults\?\.gfLowInput/.test(rdsFn) && /_ADV_FIELDS\.forEach/.test(rdsFn);
    let resetUiSyncOk = false;
    if (typeof _doResetToDefaults === 'function') {
      const cSel = document.getElementById('circuitSelect');
      const dGas = document.getElementById('decoGas');
      const trimixO2 = document.getElementById('botTrimixO2Field');
      const trimixHe = document.getElementById('botTrimixHeField');
      const ccrAdv = document.getElementById('ccrAdvSettingsSection');
      const prevC = cSel?.value;
      const prevG = dGas?.value;
      if (cSel && dGas && trimixO2 && trimixHe) {
        cSel.value = 'CCR';
        dGas.value = 'trimix';
        toggleCircuitFields?.();
        toggleBottomTrimix?.();
        _doResetToDefaults(null);
        const trimixHidden = trimixO2.style.display === 'none' && trimixHe.style.display === 'none';
        const ccrHidden = !ccrAdv || ccrAdv.style.display === 'none';
        resetUiSyncOk = cSel.value === 'OC' && dGas.value === 'air' && trimixHidden && ccrHidden;
        if (prevC != null) cSel.value = prevC;
        if (prevG != null) dGas.value = prevG;
        toggleCircuitFields?.();
        toggleBottomTrimix?.();
      }
    }
    let stopRoundingOk = false;
    if (window.VPMEngine) {
      const deep = [{ depth: 50, time: 25, o2: 21, he: 0 }];
      const deco50 = [{ o2: 50, he: 0 }];
      const halfMin = { ...baseVpm, minStopTime: 0.5 };
      const frac = VPMEngine.calculate(deep, deco50, { ...halfMin, wholeMinStops: false }, 'VPMB');
      const whole = VPMEngine.calculate(deep, deco50, { ...halfMin, wholeMinStops: true }, 'VPMB');
      const fracTimes = (frac.plan || []).filter(s => s.type === 'stop').map(s => s.time);
      const wholeTimes = (whole.plan || []).filter(s => s.type === 'stop').map(s => s.time);
      const allWhole = wholeTimes.length > 0 && wholeTimes.every(t => Math.abs(t - Math.round(t)) < 1e-6);
      const differs = JSON.stringify(fracTimes) !== JSON.stringify(wholeTimes);
      stopRoundingOk = !frac.error && !whole.error && allWhole && differs;
    }

    return {
      exposureCarryOk, stateValidationOk, settingsValidationOk, altitudeExposureOk,
      imperialResetOk, personalDefaultsOk, resetUiSyncOk, stopRoundingOk,
      ok: exposureCarryOk && stateValidationOk && settingsValidationOk && altitudeExposureOk
        && imperialResetOk && personalDefaultsOk && resetUiSyncOk && stopRoundingOk,
    };
  })();

  // ── VPM min-deco on no-decompression (NDL) dives ─────────────────────────
  out.sections.vpmMdpNdl = (() => {
    const lv = [{ depth: 12, time: 10, o2: 21, he: 0 }];
    const baseVpm = {
      metric: true, minStopTime: 1, stepSize: 3, lastStop: 3,
      descentRate: 20, ascentRate: 10, decoAscentRate: 3, surfaceAscentRate: 3,
    };
    if (!window.VPMEngine) return { ok: false, reason: 'no engine' };
    const noMdp = VPMEngine.calculate(lv, [], baseVpm, 'VPMB');
    const withMdp = VPMEngine.calculate(lv, [], {
      ...baseVpm,
      minDecoProfile: { enabled: true, m9: 5, m6: 5 },
    }, 'VPMB');
    const stops = (withMdp.stops || []).map(s => ({ depth: s.depth, time: s.time }));
    const has9 = stops.some(s => Math.abs(s.depth - 9) < 0.25 && s.time >= 4.9);
    const has6 = stops.some(s => Math.abs(s.depth - 6) < 0.25 && s.time >= 4.9);
    const noZeroStops = stops.every(s => s.time > 0.01);
    const runtimeDelta = (withMdp.totalRuntime || 0) - (noMdp.totalRuntime || 0);
    return {
      ok: !noMdp.error && !withMdp.error
        && (noMdp.stops || []).length === 0
        && has9 && has6
        && noZeroStops
        && runtimeDelta >= 8,
      stops,
      noRt: noMdp.totalRuntime,
      mdpRt: withMdp.totalRuntime,
    };
  })();

  // ── AI Studio report re-checks (water density, schedule gen, worker guard) ─
  out.sections.studioFixes = (() => {
    const freshBpm = (1000 * 9.80665) / 100000;
    const saltBpm = (1025 * 9.80665) / 100000;
    let waterOk = false;
    if (window.ZhlEngineBundle) {
      ZhlEngineBundle.applyEnvironment({ altSurfaceP: 1.01325, barPerMetre: freshBpm });
      const fresh40 = ZhlEngineBundle.depthBar(40);
      ZhlEngineBundle.applyEnvironment({ altSurfaceP: 1.01325, barPerMetre: saltBpm });
      const salt40 = ZhlEngineBundle.depthBar(40);
      waterOk = salt40 > fresh40 && Math.abs(salt40 - fresh40) > 0.03;
    }
    const workerGuardOk = typeof ZhlWorkerBridge !== 'undefined';
    return {
      ok: waterOk
        && typeof nextDecoScheduleGen === 'function'
        && typeof isStaleDecoScheduleGen === 'function'
        && typeof savePresets === 'function'
        && workerGuardOk,
      waterOk,
      scheduleGenOk: typeof nextDecoScheduleGen === 'function',
      workerGuardOk,
    };
  })();

  // ── Cycle 31 post-fix verification (C-04 trimix inert, pSCR env sync, contingency MOD) ─
  out.sections.cycle31 = (() => {
    let c04Ok = false;
    if (typeof getInspiredInertPressures === 'function') {
      const surfP = typeof altSurfaceP !== 'undefined' ? altSurfaceP : 1.01325;
      const ppH2O = typeof WATER_VAPOR !== 'undefined' ? WATER_VAPOR : 0.0627;
      const barM = BAR_PER_METRE || 0.1;
      const sp = 1.3;
      const fO2 = 0.18;
      const fHe = 0.45;
      const fN2d = Math.max(0, 1 - fO2 - fHe);
      const pAmb40 = surfP + 40 * barM;
      _syncZhlBundleEnv();
      const insp = getInspiredInertPressures(pAmb40, sp, fO2, fHe, { circuit: 'CCR', setpoint: sp });
      const pInert = Math.max(0, pAmb40 - sp - ppH2O);
      const den = Math.max(0.001, fN2d + fHe);
      c04Ok = Math.abs(insp.pN2 - pInert * fN2d / den) < 1e-6
        && Math.abs(insp.pHe - pInert * fHe / den) < 1e-6;
    }
    let pscrLoopSyncOk = false;
    if (typeof computePSCRFractions === 'function') {
      _syncZhlBundleEnv();
      const pAmb = (typeof altSurfaceP !== 'undefined' ? altSurfaceP : 1.01325) + 30 * (BAR_PER_METRE || 0.1);
      const fr5 = computePSCRFractions(pAmb, 0.32, 0, { circuit: 'pSCR', scrLoopVolume: 5, scrMetabolicO2: 1.5 });
      const fr15 = computePSCRFractions(pAmb, 0.32, 0, { circuit: 'pSCR', scrLoopVolume: 15, scrMetabolicO2: 1.5 });
      pscrLoopSyncOk = !!(fr5 && fr15 && Math.abs(fr5.fO2 - fr15.fO2) > 1e-4);
    }
    const shallowPersistOk = typeof appSettings !== 'undefined'
      && Array.isArray(appSettings.DECO_FIELDS)
      && appSettings.DECO_FIELDS.includes('shallowGradient');
    const repetitiveBottomPhaseOk = typeof runUnifiedPlan === 'function'
      && /ccrPhase:\s*['"]bottom['"]/.test(runUnifiedPlan.toString());
    let contingencyModOk = false;
    if (typeof buildContingencyModViolationAlert === 'function') {
      const depthEl = document.getElementById('decoDepth');
      const gasEl = document.getElementById('decoGas');
      const prevD = depthEl?.value;
      const prevG = gasEl?.value;
      if (depthEl) depthEl.value = '55';
      if (gasEl) gasEl.value = 'air';
      const alert = buildContingencyModViolationAlert(5);
      contingencyModOk = typeof alert === 'string' && alert.includes('BEYOND MOD');
      if (depthEl && prevD != null) depthEl.value = prevD;
      if (gasEl && prevG != null) gasEl.value = prevG;
    }
    return {
      ok: c04Ok && pscrLoopSyncOk && shallowPersistOk && contingencyModOk && repetitiveBottomPhaseOk,
      c04Ok,
      pscrLoopSyncOk,
      shallowPersistOk,
      contingencyModOk,
      repetitiveBottomPhaseOk,
    };
  })();

  // ── Cycle 32: contingency bailout dual-check (UI-13 / gas-plan-core) ─────
  out.sections.cycle32 = (() => {
    const rdFn = typeof runDecoSchedule === 'function' ? runDecoSchedule.toString() : '';
    const sacScaleOk = /getContingencySacMultiplier/.test(rdFn) && /contSacMult/.test(rdFn);
    const scratchGasOk = /_contingencyScratchGasConsumed/.test(rdFn);
    const calcFn = typeof calcContingency === 'function' ? calcContingency.toString() : '';
    const bailoutDualOk = /buildContingencyBailoutGasAlert/.test(calcFn)
      && /contLastGasConsumed/.test(calcFn)
      && /warningBailoutContingency/.test(calcFn);
    const gasSwitchOk = typeof revalidateContingencyGasSwitchDepth === 'function'
      && /getConfiguredBailoutMixes/.test(revalidateContingencyGasSwitchDepth.toString());
    const errorRecoveryOk = /finally\s*\{/.test(calcFn)
      && /_contingencyRunning\s*=\s*false/.test(calcFn)
      && /_scheduleWorkerBusy\s*=\s*false/.test(calcFn);
    const persistOk = typeof appSettings !== 'undefined'
      && Array.isArray(appSettings.DECO_FIELDS)
      && appSettings.DECO_FIELDS.includes('contingencySacMultiplier');

    let sacFuncOk = false;
    if (typeof getContingencySacMultiplier === 'function' && typeof scaleGasConsumedMap === 'function') {
      const el = document.getElementById('contingencySacMultiplier');
      const prev = el ? el.value : null;
      if (el) el.value = '2';
      const mult = getContingencySacMultiplier();
      const scaled = scaleGasConsumedMap({ AIR: 100 }, mult);
      sacFuncOk = mult === 2 && Math.abs(scaled.AIR - 200) < 1e-6;
      if (el && prev != null) el.value = prev;
    }

    let bailoutWarnOk = false;
    if (typeof calculateGasRequirementsFromConsumed === 'function' && typeof buildContingencyBailoutGasAlert === 'function') {
      const el = document.getElementById('gpDg1_size');
      const fill = document.getElementById('gpDg1_fill');
      const res = document.getElementById('gpDg1_reserve');
      const prevS = el ? el.value : null;
      const prevF = fill ? fill.value : null;
      const prevR = res ? res.value : null;
      if (el) el.value = '1';
      if (fill) fill.value = '50';
      if (res) res.value = '0';
      const alert = buildContingencyBailoutGasAlert({ 'EAN 50': 5000 });
      bailoutWarnOk = alert.warningBailoutContingency === true
        && typeof alert.html === 'string'
        && alert.html.includes('BAILOUT INSUFFICIENT');
      if (el && prevS != null) el.value = prevS;
      if (fill && prevF != null) fill.value = prevF;
      if (res && prevR != null) res.value = prevR;
    }

    let bailoutEligibilityOk = false;
    if (typeof gpAvailLForGasLabel === 'function') {
      const ids = ['circuitSelect', 'decoGas', 'diluentUseAsBailout', 'gpBot_size', 'gpBot_fill', 'gpBot_reserve'];
      const saved = Object.fromEntries(ids.map(id => [id, document.getElementById(id)?.value]));
      const set = (id, value) => { const el = document.getElementById(id); if (el) el.value = value; };
      set('circuitSelect', 'CCR');
      set('decoGas', 'air');
      set('diluentUseAsBailout', 'off');
      set('gpBot_size', '11');
      set('gpBot_fill', '200');
      set('gpBot_reserve', '50');
      const excluded = gpAvailLForGasLabel('Air', { bailoutFocus: true });
      set('diluentUseAsBailout', 'on');
      const included = gpAvailLForGasLabel('Air', { bailoutFocus: true });
      bailoutEligibilityOk = Math.abs(excluded) < 1e-6 && included >= 1650;
      Object.entries(saved).forEach(([id, value]) => { if (value != null) set(id, value); });
    }

    let gasSwitchDepthOk = false;
    if (typeof revalidateContingencyGasSwitchDepth === 'function') {
      const html = revalidateContingencyGasSwitchDepth(
        { firstStopDepth: 18 },
        { firstStopDepth: 27 },
      );
      gasSwitchDepthOk = typeof html === 'string' && html.includes('GAS SWITCH REVIEW');
    }

    let throwRecoveryOk = false;
    if (typeof runContingencyScenario === 'function') {
      try {
        runContingencyScenario(() => { throw new Error('cycle32 probe'); });
        throwRecoveryOk = _contingencyRunning === false && window._scheduleWorkerBusy === false;
      } catch (_) { throwRecoveryOk = false; }
    }

    let settingsRecoveryOk = false;
    if (typeof appSettings !== 'undefined' && typeof appSettings._restoreFields === 'function') {
      const originalSync = appSettings._syncUiAfterRestore;
      const previousHeadless = window._zhlHeadless;
      window._zhlHeadless = true;
      appSettings._syncUiAfterRestore = () => { throw new Error('settings recovery probe'); };
      try { appSettings._restoreFields({}); } catch (_) {}
      settingsRecoveryOk = appSettings._restoreInProgress === false;
      appSettings._syncUiAfterRestore = originalSync;
      window._zhlHeadless = previousHeadless;
      appSettings._restoreInProgress = false;
    }

    return {
      ok: sacScaleOk && scratchGasOk && bailoutDualOk && gasSwitchOk && errorRecoveryOk && persistOk
        && sacFuncOk && bailoutWarnOk && bailoutEligibilityOk && gasSwitchDepthOk && throwRecoveryOk && settingsRecoveryOk,
      sacScaleOk,
      scratchGasOk,
      bailoutDualOk,
      gasSwitchOk,
      errorRecoveryOk,
      persistOk,
      sacFuncOk,
      bailoutWarnOk,
      bailoutEligibilityOk,
      gasSwitchDepthOk,
      throwRecoveryOk,
      settingsRecoveryOk,
    };
  })();

  // Cycle 33: verify contingency safety, precision, and primary UI isolation.
  out.sections.cycle33 = (() => {
    const ids = [
      'algorithmSelect', 'circuitSelect', 'decoGas', 'decoDepth', 'decoBT',
      'ppo2Bottom', 'dg1Mix', 'dg2Mix', 'gpBot_size', 'gpBot_fill', 'gpBot_reserve',
    ];
    const savedInputs = Object.fromEntries(ids.map(id => [id, document.getElementById(id)?.value]));
    const set = (id, value) => { const el = document.getElementById(id); if (el) el.value = value; };
    const mainTbody = document.getElementById('decoTableBody');
    const summaryEl = document.getElementById('decoSummary');
    const gasSummaryEl = document.getElementById('gasConsumptionSummary');
    const savedUi = {
      table: mainTbody?.innerHTML,
      summary: summaryEl?.innerHTML,
      gasSummary: gasSummaryEl?.innerHTML,
      lastPlan: window._lastPlan,
      lastGasConsumed: window._lastGasConsumed,
      lastBottomPhaseConsumedL: window._lastBottomPhaseConsumedL,
      zhlHeadless: window._zhlHeadless,
    };
    let ppo2ToxicityOk = false;
    let gasPrecisionOk = false;
    let primaryGasStateOk = false;
    let tableSourceOk = false;
    try {
      const depthM = 38.5;
      set('decoDepth', units === 'metric' ? String(depthM) : String(depthM * 3.28084));
      set('decoGas', 'ean32');
      set('ppo2Bottom', '1.4');
      const toxicityAlert = buildContingencyModViolationAlert(3);
      ppo2ToxicityOk = toxicityAlert.includes('BEYOND MOD')
        && toxicityAlert.includes('actual 1.65 bar')
        && toxicityAlert.includes('CNS oxygen toxicity risk');

      set('circuitSelect', 'OC');
      set('decoGas', 'air');
      set('gpBot_size', '1');
      set('gpBot_fill', '100');
      set('gpBot_reserve', '0');
      const precise = calculateGasRequirementsFromConsumed({ Air: 100.1 }, { bailoutFocus: true });
      const preciseRow = precise.rows.find(row => row.label === 'Air');
      gasPrecisionOk = precise.warningBailoutContingency === true
        && preciseRow?.reqL === 100.1
        && Math.abs(preciseRow.shortL - 0.1) < 1e-9;

      set('algorithmSelect', 'ZHLC_GF');
      set('decoDepth', units === 'metric' ? '30' : String(30 * 3.28084));
      set('decoBT', '20');
      set('dg1Mix', 'none');
      set('dg2Mix', 'none');
      window._zhlHeadless = false;
      runDecoSchedule();
      const primaryGas = JSON.stringify(window._lastGasConsumed || {});
      const primaryPlan = window._lastPlan;
      const primaryTable = mainTbody?.innerHTML;
      const primaryGasHtml = gasSummaryEl?.innerHTML;
      const contingency = runContingencyScenario(() => set('decoBT', '25'));
      primaryGasStateOk = contingency.ok === true
        && window._lastPlan === primaryPlan
        && JSON.stringify(window._lastGasConsumed || {}) === primaryGas
        && gasSummaryEl?.innerHTML === primaryGasHtml;
      tableSourceOk = contingency.ok === true
        && mainTbody?.innerHTML === primaryTable
        && !mainTbody?.innerHTML.includes('EMERGENCY CONTINGENCY');
    } catch (_) {
      ppo2ToxicityOk = false;
      gasPrecisionOk = false;
      primaryGasStateOk = false;
      tableSourceOk = false;
    } finally {
      Object.entries(savedInputs).forEach(([id, value]) => { if (value != null) set(id, value); });
      if (mainTbody && savedUi.table != null) mainTbody.innerHTML = savedUi.table;
      if (summaryEl && savedUi.summary != null) summaryEl.innerHTML = savedUi.summary;
      if (gasSummaryEl && savedUi.gasSummary != null) gasSummaryEl.innerHTML = savedUi.gasSummary;
      window._lastPlan = savedUi.lastPlan;
      window._lastGasConsumed = savedUi.lastGasConsumed;
      window._lastBottomPhaseConsumedL = savedUi.lastBottomPhaseConsumedL;
      window._zhlHeadless = savedUi.zhlHeadless;
    }
    return {
      ok: ppo2ToxicityOk && gasPrecisionOk && primaryGasStateOk && tableSourceOk,
      ppo2ToxicityOk,
      gasPrecisionOk,
      primaryGasStateOk,
      tableSourceOk,
    };
  })();

  // ── Cycle 6 audit fixes (rec planner, RDP, pSCR, trimix, Bühlmann BT) ───
  out.sections.cycle6 = (() => {
    const rdp11 = typeof padiTableRowIndex === 'function' ? padiTableRowIndex(11) : null;
    const rdp13 = typeof padiTableRowIndex === 'function' ? padiTableRowIndex(13) : null;
    const ndl11 = typeof getNitroxNDL === 'function' ? getNitroxNDL(11, 'air') : null;
    const ndl13 = typeof getNitroxNDL === 'function' ? getNitroxNDL(13, 'air') : null;
    const ndl25ean32 = typeof getNitroxNDL === 'function' ? getNitroxNDL(25, 'ean32') : null;
    const rdpOk = rdp11 === 1 && rdp13 === 2 && ndl11 === 230 && ndl13 === 100 && ndl25ean32 === 25;

    const depthEl = document.getElementById('depth');
    const btEl = document.getElementById('bt');
    const prevAlgo = typeof algo !== 'undefined' ? algo : null;
    let padiDepthOk = false;
    if (depthEl && btEl && typeof validatePlannerInputs === 'function') {
      const prevD = depthEl.value;
      const prevBt = btEl.value;
      if (typeof algo !== 'undefined') algo = 'padi';
      depthEl.value = '60';
      btEl.value = '5';
      const bad = validatePlannerInputs();
      depthEl.value = prevD;
      btEl.value = prevBt;
      if (prevAlgo != null) algo = prevAlgo;
      padiDepthOk = !!(bad && !bad.ok);
    }

    const decoGasEl = document.getElementById('decoGas');
    const botO2El = document.getElementById('botTrimixO2');
    const botHeEl = document.getElementById('botTrimixHe');
    let trimixOk = false;
    if (decoGasEl && botO2El && botHeEl && typeof validateDomDecoGases === 'function') {
      const prevGas = decoGasEl.value;
      const prevO2 = botO2El.value;
      const prevHe = botHeEl.value;
      decoGasEl.value = 'trimix';
      botO2El.value = '50';
      botHeEl.value = '0';
      const badTrimix = validateDomDecoGases();
      const fr = typeof getBottomGasFractions === 'function' ? getBottomGasFractions() : null;
      decoGasEl.value = prevGas;
      botO2El.value = prevO2;
      botHeEl.value = prevHe;
      trimixOk = !badTrimix.ok && (!fr || Math.abs(fr.fO2 - 0.5) < 1e-6);
    }

    let pscrValOk = false;
    let pscrCanonOk = false;
    if (typeof validateCcrCalculationInputs === 'function') {
      const profile = [{ depth: 40, time: 20, o2: 21, he: 0 }];
      const invalidSettings = [
        { scrLoopVolume: 2.99, scrMetabolicO2: 1.5 },
        { scrLoopVolume: 15.01, scrMetabolicO2: 1.5 },
        { scrLoopVolume: 10, scrMetabolicO2: 0.49 },
        { scrLoopVolume: 10, scrMetabolicO2: 2.51 },
      ];
      pscrValOk = invalidSettings.every(settings => {
        const result = validateCcrCalculationInputs(profile, { circuit: 'pSCR', ...settings }, []);
        return !result.ok;
      }) && [
        { scrLoopVolume: 3, scrMetabolicO2: 0.5 },
        { scrLoopVolume: 15, scrMetabolicO2: 2.5 },
      ].every(settings => validateCcrCalculationInputs(profile, { circuit: 'pSCR', ...settings }, []).ok);
    }
    if (typeof getEffectiveSetpointAtDepth === 'function') {
      pscrCanonOk = getEffectiveSetpointAtDepth(30, { circuit: 'pscr' }, altSurfaceP) === 0;
    }
    let pscrCoreOk = true;
    if (typeof computePSCRFractions === 'function') {
      const invalidCoreSettings = [
        { scrLoopVolume: 2.99, scrMetabolicO2: 1.5 },
        { scrLoopVolume: 15.01, scrMetabolicO2: 1.5 },
        { scrLoopVolume: 10, scrMetabolicO2: 0.49 },
        { scrLoopVolume: 10, scrMetabolicO2: 2.51 },
      ];
      pscrCoreOk = invalidCoreSettings.every(settings => {
        try {
          computePSCRFractions(1.5, 0.21, 0, { circuit: 'pSCR', ...settings });
          return false;
        } catch (_) { return true; }
      }) && [
        { scrLoopVolume: 3, scrMetabolicO2: 0.5 },
        { scrLoopVolume: 15, scrMetabolicO2: 2.5 },
      ].every(settings => {
        try {
          const fractions = computePSCRFractions(1.5, 0.21, 0, { circuit: 'pSCR', ...settings });
          return fractions && Number.isFinite(fractions.fO2);
        } catch (_) { return false; }
      });
    }

    const surfP = typeof altSurfaceP !== 'undefined' ? altSurfaceP : 1.01325;
    const pAmb3 = surfP + 3 * (BAR_PER_METRE || 0.1);
    const pDry3 = pAmb3 - (WATER_VAPOR || 0.0627);
    const ccrCfg = { circuit: 'CCR', descentSetpoint: 0.7, bottomSetpoint: 1.2, decoSetpoint: 1.3, bailout: false };
    const ppo2At3 = typeof getEffectivePpo2 === 'function'
      ? getEffectivePpo2(pAmb3, 1.3, 0.21, ccrCfg, 3, 0) : null;
    const ppo2DryOk = ppo2At3 != null && ppo2At3 <= pDry3 + 1e-6 && ppo2At3 > 1.25;

    let buhlBtOk = false;
    if (typeof initTissues === 'function' && typeof saturate === 'function' && typeof saturateLinear === 'function') {
      const fN2 = 0.79;
      const fHe = 0;
      const depthM = 40;
      const bt = 20;
      const descentRate = 20;
      const descentTime = depthM / descentRate;
      const btAtDepth = Math.max(0, bt - descentTime);
      let tHold = initTissues();
      tHold = saturate(tHold, depthM, bt, fN2, fHe);
      let tSplit = initTissues();
      tSplit = saturateLinear(tSplit, 0, depthM, descentTime, fN2, fHe);
      tSplit = saturate(tSplit, depthM, btAtDepth, fN2, fHe);
      const diff = tSplit.reduce((m, c, i) => Math.max(m, Math.abs((c.pN2 || 0) - (tHold[i].pN2 || 0))), 0);
      buhlBtOk = diff > 0.05;
    }

    return {
      rdpOk, padiDepthOk, trimixOk, pscrValOk, pscrCanonOk, pscrCoreOk, ppo2DryOk, buhlBtOk,
      ndl11, ndl13, ndl25ean32, ppo2At3, pDry3,
      ok: rdpOk && padiDepthOk && trimixOk && pscrValOk && pscrCanonOk && pscrCoreOk && ppo2DryOk && buhlBtOk,
    };
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
    assert_true(i113s.get("ok"), "[AUDIT-REG-02] CCR setpoint zones: descSP shallow, decoSP at 10 m (issue #113 / #128 C-01)", str(i113s))
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
    assert_true(i128.get("ok"), "[AUDIT-REG-01] CCR setpoint at depth + trimix inert PP paths (issue #128 C-01/C-02)", str(i128))
    i123 = s.get("issue123", {})
    assert_true(i123.get("ok"), "issue #123 engine audit fixes (CCR shallow/pSCR/VPM)", str(i123))
    i124 = s.get("issue124", {})
    assert_true(i124.get("ok"), "issue #124 audit fixes (ceiling/gfAt/contingency/pSCR/UI)", str(i124))
    i133 = s.get("issue133", {})
    assert_true(i133.get("c2Ok"), "issue #133 C-2: hypoxic trimix deco rejected", str(i133))
    assert_true(i133.get("l2Ok"), "issue #133 L-2: n2FracFromPercentages null for O2+He>100", str(i133))
    assert_true(i133.get("c4Ok"), "issue #133 C-4: isShallowGradientOn reads select value=on", str(i133))
    assert_true(i133.get("wrapGas"), "issue #133 C-1: getActiveGas wrapper arg order", str(i133))
    i134 = s.get("issue134", {})
    assert_true(i134.get("c1Ok"), "issue #134 C-1: bottom/CCR hypoxic gas not blocked in DOM validation", str(i134))
    assert_true(i134.get("h1Ok"), "issue #134 H-1: gfAtDepth returns gfH when firstStopDepth=0", str(i134))
    assert_true(i134.get("m7Ok"), "issue #134 M-7: ppO2Check returns numeric value", str(i134))
    assert_true(i134.get("shallowNdlOk"), "[AUDIT-REG-05] issue #134 L-6: shallowGradient changes buhNDL", str(i134))
    assert_true(i134.get("saveGuard"), "issue #134 M-4: appSettings.save guards _restoreInProgress", str(i134))
    i135 = s.get("issue135", {})
    assert_true(i135.get("h1Ok"), "issue #135 H-1: contingency returns ok:false on empty schedule", str(i135))
    assert_true(i135.get("h6Ok"), "[AUDIT-REG-03] issue #135 H-6: ppO2Check preserves numeric precision", str(i135))
    assert_true(i135.get("h8Ok"), "issue #135 H-8: contingency uses parseRunMinutes for stop time", str(i135))
    assert_true(i135.get("m2Ok"), "issue #135 M-2: runDecoSchedule skips validation during contingency", str(i135))
    assert_true(i135.get("h4Ok"), "issue #135 H-4: saveZhlRepState persists CNS/OTU", str(i135))
    assert_true(i135.get("ok"), "issue #135 combined regression gate", str(i135))
    i137 = s.get("issue137", {})
    assert_true(i137.get("m17Ok"), "issue #137 M-17: CCR hypoxic deco gas exempt from 18% rule", str(i137))
    assert_true(i137.get("h7Ok"), "issue #137 H-7: schedule gfAt returns gfL pre-anchor (Baker search)", str(i137))
    assert_true(i137.get("m19Ok"), "issue #137 M-19: VPM bubble state survives JSON clone carry", str(i137))
    assert_true(i137.get("h6Ok"), "issue #137 H-6: VPM has no untested worker path", str(i137))
    assert_true(i137.get("m11Ok"), "issue #137 M-11: contingency restores bailout in finally", str(i137))
    assert_true(i137.get("m20Ok"), "issue #137 M-20: runContingencyScenario executes functionally", str(i137))
    assert_true(i137.get("ok"), "issue #137 combined regression gate", str(i137))
    i138 = s.get("issue138", {})
    assert_true(i138.get("h7Ok"), "issue #138 H-7: getZhlRepStateForSchedule carries CNS/OTU", str(i138))
    assert_true(i138.get("h2Ok"), "issue #138 H-2: runDecoSchedule sanitizes error HTML", str(i138))
    assert_true(i138.get("m1Ok"), "issue #138 M-1: CCR validation skipped during contingency", str(i138))
    assert_true(i138.get("h8Ok"), "issue #138 H-8: VPM uses btAtDepthMin", str(i138))
    assert_true(i138.get("l9Ok"), "issue #138 L-9: n2FracFromPercentages rejects fN2 > 1", str(i138))
    assert_true(i138.get("ok"), "issue #138 combined regression gate", str(i138))
    i139 = s.get("issue139", {})
    assert_true(i139.get("l1Ok"), "issue #139 L-1: CCR setpoint inputs persist on change", str(i139))
    assert_true(i139.get("l2Ok"), "issue #139 L-2: safety stop row formats ppO₂", str(i139))
    assert_true(i139.get("l3Ok"), "issue #139 L-3: setCustomGF syncs DOM after GF swap", str(i139))
    assert_true(i139.get("ok"), "issue #139 combined regression gate", str(i139))
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

    ml = s.get("mlContGas", {})
    assert_true(ml.get("gasOk"), "[ZHL-ML-CONT-GAS] multi-level continuation gas preserved on ascent after hold", str(ml))
    assert_true(ml.get("rateOk"), "[ZHL-ML-ASCENT-RATE] continuation no-deco ascent uses main rate not deco rate", str(ml))
    mlb = s.get("mlBottomLabel", {})
    assert_true(mlb.get("ok"), "headless descent/bottom gas label from declared level not first step", str(mlb))

    c6 = s.get("cycle6", {})
    assert_true(c6.get("rdpOk"), "[CYCLE6-RDP-CEILING] PADI RDP uses ceiling depth row not nearest", str(c6))
    assert_true(c6.get("padiDepthOk"), "[CYCLE6-PADI-DEPTH] validatePlannerInputs rejects beyond PADI table depth", str(c6))
    assert_true(c6.get("trimixOk"), "[CYCLE6-TRIMIX-RANGE] bottom trimix >40% rejected without silent clamp", str(c6))
    assert_true(c6.get("pscrValOk") and c6.get("pscrCoreOk"), "[CYCLE6-PSCR-BOUNDS] pSCR UI contract bounds enforced by validator and pure core", str(c6))
    assert_true(c6.get("pscrCanonOk"), "[CYCLE6-PSCR-CANON] lowercase pSCR circuit returns zero setpoint", str(c6))
    assert_true(c6.get("ppo2DryOk"), "[CYCLE6-CCR-DRY-PPO2] CCR ppO2 capped at dry-gas pressure", str(c6))
    assert_true(c6.get("buhlBtOk"), "[CYCLE6-BUHLMANN-BT] Bühlmann rec planner models descent then hold BT", str(c6))

    c7 = s.get("cycle7", {})
    assert_true(c7.get("h1Ok"), "[CYCLE7-H1] contingency uses scratch tbody without clobbering main table", str(c7))
    assert_true(c7.get("h2Ok"), "[CYCLE7-H2] contingency restores inputs on modifyFn throw", str(c7))
    assert_true(c7.get("m1Ok"), "[CYCLE7-M1] contingency slate uses data-label selectors", str(c7))
    assert_true(c7.get("m2Ok"), "[CYCLE7-M2] contingency saves/restores circuitSelect", str(c7))
    assert_true(c7.get("m3Ok"), "[CYCLE7-M3] contingency PDF tissue section uses contLastTissues only", str(c7))
    assert_true(c7.get("m4Ok"), "[CYCLE7-M4] contingency PDF legend from waypoint data", str(c7))
    assert_true(c7.get("l4Ok"), "[CYCLE7-L4] minStopTime 0:01 disabled under whole-minute rounding", str(c7))
    c7b = s.get("cycle7b", {})
    assert_true(c7b.get("h1Ok"), "[CYCLE7b-H1] contingency PDF profile uses scratch tbody not innerHTML swap", str(c7b))
    assert_true(c7b.get("m1Ok"), "[CYCLE7b-M1] contingency PDF restores tissueTableBody after updateTissueViz", str(c7b))
    assert_true(c7b.get("l1Ok"), "[CYCLE7b-L1] buildContingencySlateText has no dead dateStr", str(c7b))
    assert_true(c7b.get("l2Ok"), "[CYCLE7b-L2] drawGraphLegend normalizes rows via legendRowFromTr", str(c7b))
    c7o = s.get("cycle7Official", {})
    assert_true(c7o.get("exposureCarryOk"), "[CYCLE7-VPM-EXPOSURE-CARRY] VPM buildResult preserves _preOTU/_preCNS carry", str(c7o))
    assert_true(c7o.get("stateValidationOk"), "[CYCLE7-VPM-STATE-VALIDATION] malformed repetitive state returns INVALID_REPETITIVE_STATE", str(c7o))
    assert_true(c7o.get("settingsValidationOk"), "[CYCLE7-VPM-SETTINGS-VALIDATION] negative VPM rates rejected", str(c7o))
    assert_true(c7o.get("altitudeExposureOk"), "[CYCLE7-VPM-ALTITUDE-EXPOSURE] altitude changes VPM exposure totals", str(c7o))
    assert_true(c7o.get("imperialResetOk"), "[CYCLE7-IMPERIAL-RESET] factory reset uses imperial SAC/cylinder defaults", str(c7o))
    assert_true(c7o.get("personalDefaultsOk"), "[CYCLE7-PERSONAL-DEFAULTS] reset honours saved GF and adv fields", str(c7o))
    assert_true(c7o.get("resetUiSyncOk"), "[CYCLE7-RESET-UI-SYNC] reset hides CCR and trimix fields after OC/Air restore", str(c7o))
    assert_true(c7o.get("stopRoundingOk"), "[CYCLE7-STOP-ROUNDING] whole-minute mode emits integer-minute VPM stops", str(c7o))
    vmdp = s.get("vpmMdpNdl", {})
    assert_true(vmdp.get("ok"), "[VPM-MDP-NDL] min-deco inserts 9m/6m stops on no-decompression dive", str(vmdp))
    studio = s.get("studioFixes", {})
    assert_true(studio.get("ok"), "[STUDIO-FIXES] water density + schedule gen guards present", str(studio))
    c31 = s.get("cycle31", {})
    assert_true(c31.get("c04Ok"), "[CYCLE31-C04] CCR trimix inert PP uses fN2/(fN2+fHe) ratio", str(c31))
    assert_true(c31.get("pscrLoopSyncOk"), "[CYCLE31-PSCR] pSCR loop volume changes inspired fractions", str(c31))
    assert_true(c31.get("shallowPersistOk"), "[CYCLE31-SHALLOW] shallowGradient in DECO_FIELDS", str(c31))
    assert_true(c31.get("contingencyModOk"), "[CYCLE31-CONTINGENCY-MOD] went-deeper contingency flags MOD violation", str(c31))
    assert_true(c31.get("repetitiveBottomPhaseOk"), "[CYCLE31-CCR-NDL-PHASE] repetitive CCR NDL uses bottom setpoint phase", str(c31))
    c32 = s.get("cycle32", {})
    assert_true(c32.get("bailoutWarnOk"), "[CYCLE32-L6] test_contingency_bailout_insufficiency_warning", str(c32))
    assert_true(c32.get("sacFuncOk") and c32.get("sacScaleOk"), "[CYCLE32-L1] test_contingency_sac_scaling", str(c32))
    assert_true(c32.get("gasSwitchDepthOk") and c32.get("gasSwitchOk"), "[CYCLE32-L3] test_contingency_gas_switch_depth_shift", str(c32))
    assert_true(c32.get("throwRecoveryOk") and c32.get("errorRecoveryOk"), "[CYCLE32-L2] test_contingency_error_recovery", str(c32))
    assert_true(c32.get("bailoutEligibilityOk"), "[CYCLE32-BAILOUT-ELIGIBILITY] disabled diluent is excluded from bailout availability", str(c32))
    assert_true(c32.get("settingsRecoveryOk"), "[CYCLE32-SETTINGS-RECOVERY] restore lock clears after exception", str(c32))
    c33 = s.get("cycle33", {})
    assert_true(c33.get("ppo2ToxicityOk"), "[CYCLE33-PPO2-TOXICITY] test_contingency_ppo2_toxicity_violation", str(c33))
    assert_true(c33.get("primaryGasStateOk"), "[CYCLE33-PRIMARY-GAS-INTEGRITY] test_primary_gas_state_integrity_during_contingency", str(c33))
    assert_true(c33.get("gasPrecisionOk"), "[CYCLE33-GAS-PRECISION] test_gas_volume_rounding_conservatism", str(c33))
    assert_true(c33.get("tableSourceOk"), "[CYCLE33-TABLE-SOURCE] test_table_render_source_consistency", str(c33))
    sw_install = (ROOT / "sw.js").read_text(encoding="utf-8")
    sw_block = sw_install.split("addEventListener('install'")[1].split("addEventListener('activate'")[0] if "addEventListener('install'" in sw_install else ""
    assert_true("clients.matchAll" not in sw_block, "[CYCLE7-L2] SW install handler does not postMessage before claim")

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


def _audit_case_rows():
    from tools.audit.suite_emit import case_row

    def case_ok(case_id: str) -> bool:
        return not any(f"[{case_id}]" in f for f in FAIL)

    return [
        case_row("AUDIT-REG-01", case_ok("AUDIT-REG-01")),
        case_row("AUDIT-REG-02", case_ok("AUDIT-REG-02")),
        case_row("AUDIT-REG-03", case_ok("AUDIT-REG-03")),
        case_row("AUDIT-REG-05", case_ok("AUDIT-REG-05")),
        case_row("ZHL-ML-CONT-GAS", case_ok("ZHL-ML-CONT-GAS")),
        case_row("ZHL-ML-ASCENT-RATE", case_ok("ZHL-ML-ASCENT-RATE")),
        case_row("CYCLE6-RDP-CEILING", case_ok("CYCLE6-RDP-CEILING")),
        case_row("CYCLE6-PADI-DEPTH", case_ok("CYCLE6-PADI-DEPTH")),
        case_row("CYCLE6-TRIMIX-RANGE", case_ok("CYCLE6-TRIMIX-RANGE")),
        case_row("CYCLE6-PSCR-BOUNDS", case_ok("CYCLE6-PSCR-BOUNDS")),
        case_row("CYCLE6-PSCR-CANON", case_ok("CYCLE6-PSCR-CANON")),
        case_row("CYCLE6-CCR-DRY-PPO2", case_ok("CYCLE6-CCR-DRY-PPO2")),
        case_row("CYCLE6-BUHLMANN-BT", case_ok("CYCLE6-BUHLMANN-BT")),
        case_row("CYCLE7-VPM-EXPOSURE-CARRY", case_ok("CYCLE7-VPM-EXPOSURE-CARRY")),
        case_row("CYCLE7-VPM-STATE-VALIDATION", case_ok("CYCLE7-VPM-STATE-VALIDATION")),
        case_row("CYCLE7-VPM-SETTINGS-VALIDATION", case_ok("CYCLE7-VPM-SETTINGS-VALIDATION")),
        case_row("CYCLE7-VPM-ALTITUDE-EXPOSURE", case_ok("CYCLE7-VPM-ALTITUDE-EXPOSURE")),
        case_row("CYCLE7-IMPERIAL-RESET", case_ok("CYCLE7-IMPERIAL-RESET")),
        case_row("CYCLE7-PERSONAL-DEFAULTS", case_ok("CYCLE7-PERSONAL-DEFAULTS")),
        case_row("CYCLE7-RESET-UI-SYNC", case_ok("CYCLE7-RESET-UI-SYNC")),
        case_row("CYCLE7-STOP-ROUNDING", case_ok("CYCLE7-STOP-ROUNDING")),
        case_row("CYCLE31-C04", case_ok("CYCLE31-C04")),
        case_row("CYCLE31-PSCR", case_ok("CYCLE31-PSCR")),
        case_row("CYCLE31-CONTINGENCY-MOD", case_ok("CYCLE31-CONTINGENCY-MOD")),
        case_row("CYCLE31-CCR-NDL-PHASE", case_ok("CYCLE31-CCR-NDL-PHASE")),
        case_row("CYCLE32-L1", case_ok("CYCLE32-L1")),
        case_row("CYCLE32-L2", case_ok("CYCLE32-L2")),
        case_row("CYCLE32-L3", case_ok("CYCLE32-L3")),
        case_row("CYCLE32-L6", case_ok("CYCLE32-L6")),
        case_row("CYCLE32-BAILOUT-ELIGIBILITY", case_ok("CYCLE32-BAILOUT-ELIGIBILITY")),
        case_row("CYCLE32-SETTINGS-RECOVERY", case_ok("CYCLE32-SETTINGS-RECOVERY")),
        case_row("CYCLE33-PPO2-TOXICITY", case_ok("CYCLE33-PPO2-TOXICITY")),
        case_row("CYCLE33-PRIMARY-GAS-INTEGRITY", case_ok("CYCLE33-PRIMARY-GAS-INTEGRITY")),
        case_row("CYCLE33-GAS-PRECISION", case_ok("CYCLE33-GAS-PRECISION")),
        case_row("CYCLE33-TABLE-SOURCE", case_ok("CYCLE33-TABLE-SOURCE")),
    ]


if __name__ == "__main__":
    code = main()
    sys.path.insert(0, str(ROOT))
    from tools.audit.suite_emit import finish_suite

    finish_suite(ROOT, _audit_case_rows(), code)
