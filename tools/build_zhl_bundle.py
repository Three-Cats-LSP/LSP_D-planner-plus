"""Build zhl-engine-bundle.js — self-contained Tier 3 Bühlmann module (main thread + worker)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def strip_build_header(text: str) -> str:
    if text.startswith("/**"):
        end = text.find("*/")
        return text[end + 2 :].lstrip()
    return text


def read_core(name: str) -> str:
    path = ROOT / name
    if not path.is_file():
        raise SystemExit(f"{name} missing")
    return strip_build_header(path.read_text(encoding="utf-8"))


physics_core = read_core("zhl-physics-core.js")
ccr_core = read_core("zhl-ccr-core.js")
gas_core = read_core("zhl-gas-core.js")
core_fn = read_core("zhl-schedule-core.js")

core_fn = core_fn.replace(
    "\nif (typeof window !== 'undefined') window.runZhlScheduleCore = runZhlScheduleCore;\n",
    "\n",
)
core_fn = core_fn.replace(
    "function runZhlScheduleCore(params) {",
    "function runZhlScheduleCore(params) {\n  applyEnvironment(params.environment || defaultEnvironment());",
    1,
)

iife_start = """/**
 * ZHL Engine Bundle — Tier 3 isolated Bühlmann module.
 * Loaded on main thread and in zhl-schedule-worker.js (importScripts).
 */
(function (global) {
  'use strict';

"""


postamble = r'''

  const _scheduleCoreGetGasLabel = getGasLabel;

  function getGasLabel(fO2, fHe) {
    const o2 = Math.round(fO2 * 100);
    const he = Math.round((fHe || 0) * 100);
    if (he > 0) return o2 + '/' + he;
    if (o2 === 21) return 'Air';
    if (o2 === 32) return 'EAN32';
    if (o2 === 36) return 'EAN36';
    if (o2 === 50) return 'EAN50';
    if (o2 >= 99) return '100%';
    return 'EAN' + o2;
  }

  function zhlOptimalSwitchDepth(fO2, ctx) {
    const ppo2High = ctx.ppo2Deco;
    const ppo2Mid = 1.5;
    const ppo2Low = ctx.ppo2Bottom;
    function getPPO2Limit(fo2) {
      const pct = fo2 * 100;
      if (pct >= 45) return ppo2High;
      if (pct >= 28) return ppo2Mid;
      return ppo2Low;
    }
    if (fO2 <= 0) return 0;
    if (fO2 >= 0.995) return Math.max(ctx.lastStop, ctx.metric ? 6 : 20);
    const limit = getPPO2Limit(fO2);
    const exactMOD = (limit / fO2 - altSurfaceP) / BAR_PER_METRE;
    const snapped = Math.floor(exactMOD / ctx.decoStep) * ctx.decoStep;
    return Math.max(ctx.lastStop, Math.max(0, snapped));
  }

  function buildZhlDecoGasesFromEngine(decoGases, ctx) {
    const list = (decoGases || []).map(g => {
      const o2pct = g.o2;
      const hePct = g.he || 0;
      const fO2 = o2pct / 100;
      const fHe = hePct / 100;
      const fN2 = Math.max(0, 1 - fO2 - fHe);
      let label;
      if (o2pct === 100) label = '100%';
      else if (o2pct === 50 && hePct === 0) label = 'EAN50';
      else if (o2pct === 80 && hePct === 0) label = 'EAN80';
      else label = getGasLabel(fO2, fHe);
      const depth = zhlOptimalSwitchDepth(fO2, ctx);
      return { depth, fN2, fHe, fO2, label };
    });
    list.sort((a, b) => b.depth - a.depth);
    return list;
  }

  function splitZhlProfileLevels(levels) {
    if (!levels || levels.length <= 1) return { primary: levels || [], continuation: [] };
    let deepest = 0;
    for (let i = 1; i < levels.length; i++) {
      if (levels[i].depth > levels[deepest].depth) deepest = i;
    }
    let continuation = [];
    let primary = levels;
    if (deepest < levels.length - 1) {
      let monotonic = true;
      for (let i = deepest + 1; i < levels.length; i++) {
        if (levels[i].depth > levels[i - 1].depth) { monotonic = false; break; }
      }
      if (monotonic) {
        continuation = levels.slice(deepest + 1);
        primary = levels.slice(0, deepest + 1);
      }
    }
    return { primary, continuation };
  }

  function buildZhlScheduleParamsFromEngine(levels, decoGases, settings, profileSplit, environment) {
    const s = settings || {};
    const level = levels[0];
    const metric = s.metric !== false;
    const fO2bot = level.o2 / 100;
    const fHeBot = (level.he || 0) / 100;
    const fN2bot = Math.max(0, 1 - fO2bot - fHeBot);
    const switchCtx = {
      ppo2Bottom: s.ppO2Bottom || 1.4,
      ppo2Deco: s.ppO2Deco || 1.6,
      lastStop: s.lastStop || 3,
      decoStep: s.stepSize || 3,
      metric,
    };
    const gases = buildZhlDecoGasesFromEngine(decoGases, switchCtx);
    return {
      depthM: level.depth,
      bt: level.time,
      rawD: metric ? level.depth : Math.round(level.depth * 3.28084),
      metric,
      ascentRate: Math.max(1, s.ascentRate || 10),
      decoAscentRate: Math.max(1, s.decoAscentRate || 3),
      surfaceAscentRate: Math.max(1, s.surfaceAscentRate || s.decoAscentRate || 3),
      descentRate: Math.max(1, s.descentRate || 20),
      gfL: (s.gfLo || s.gfLow || 30) / 100,
      gfH: (s.gfHi || s.gfHigh || 85) / 100,
      ppo2Bottom: switchCtx.ppo2Bottom,
      ppo2Deco: switchCtx.ppo2Deco,
      minStopTime: s.minStopTime || 1,
      switchPauseT: 0,
      mdCompatMode: s.mdCompatMode !== false,
      lastStop: switchCtx.lastStop,
      decoStep: switchCtx.decoStep,
      shallowGradient: !!s.shallowGradient,
      bottomFN2: fN2bot,
      bottomFHe: fHeBot,
      bottomFO2: fO2bot,
      bottomMixLabel: getGasLabel(fO2bot, fHeBot),
      travelInfo: s.travelInfo || null,
      repState: (s._preTissues && s._preTissues.length)
        ? {
            tissues: s._preTissues,
            surfaceIntervalMin: s._surfaceInterval || 0,
            surfaceP: (environment || defaultEnvironment()).altSurfaceP,
          }
        : null,
      continuationLevels: (profileSplit && profileSplit.continuation) || [],
      minDecoProfile: s.minDecoProfile || { enabled: false, m9: 1, m6: 3, isMetric: metric !== false },
      decoGases: gases,
      environment: environment || defaultEnvironment(),
      ccr: {
        circuit: s.circuit || 'OC',
        setpoint: s.setpoint,
        descentSetpoint: s.descentSetpoint,
        bottomSetpoint: s.bottomSetpoint,
        decoSetpoint: s.decoSetpoint != null ? s.decoSetpoint : s.setpoint,
        bailout: !!s.bailout,
        bailoutGfLow: s.bailoutGfLow,
        bailoutGfHigh: s.bailoutGfHigh,
        scrLoopVolume: s.scrLoopVolume,
        scrMetabolicO2: s.scrMetabolicO2,
        sacStress: s.sacStress,
        sacDecoCcr: s.sacDecoCcr,
        stressTimeMin: s.stressTimeMin,
        problemSolveMin: s.problemSolveMin,
      },
      onLoop: isRebreatherCircuit(s.circuit || 'OC') && !s.bailout,
    };
  }

  function addHeadlessExposure(hCNSfrac, hOTU, ppO2, dur) {
    if (ppO2 > 0.5 && dur > 0) {
      hOTU.v += dur * Math.pow((ppO2 - 0.5) / 0.5, OTU_EXPONENT);
      if (ppO2 >= 1.6) {
        hCNSfrac.v += dur / 45;
        return;
      }
      const lims = {6:720,7:570,8:450,9:360,10:300,11:240,12:210,13:180,14:150,15:120,16:45};
      const lo = Math.floor(ppO2 * 10), hi = lo + 1;
      const lim = (lims[lo] || 0) + ((lims[hi] || 0) - (lims[lo] || 0)) * (ppO2 * 10 - lo);
      const safeLim = lim > 0 ? lim : 45;
      hCNSfrac.v += dur / safeLim;
    }
  }

  function headlessSegPpo2(depthM, fO2, fHe, s) {
    const pAmb = altSurfaceP + depthM * BAR_PER_METRE;
    const cfg = normalizeCCRSettings(s);
    if (!isRebreatherCircuit(cfg.circuit) || cfg.bailout) return fO2 * pAmb;
    if (cfg.circuit === 'pSCR') {
      const fr = computePSCRFractions(pAmb, fO2, fHe, cfg);
      return fr.fO2 * pAmb;
    }
    const sp = getEffectiveSetpointAtDepth(depthM, cfg, altSurfaceP);
    return Math.min(pAmb, Math.max(sp, fO2 * pAmb));
  }

  function computeHeadlessCnsOtu(lp, level, s) {
    if (!lp || lp.totalCNS != null) return;
    const fO2bot = level.o2 / 100;
    const fHebot = (level.he || 0) / 100;
    const onLoop = isRebreatherCircuit(s.circuit || 'OC') && !s.bailout;
    const hCNSfrac = { v: 0 };
    const hOTU = { v: 0 };
    const hDescentRate = s.descentRate || 20;
    const hDescentTime = level.depth / hDescentRate;
    const ppO2DescMid = onLoop
      ? headlessSegPpo2(level.depth / 2, fO2bot, fHebot, s)
      : (altSurfaceP + (level.depth / 2) * BAR_PER_METRE) * fO2bot;
    const ppO2Bottom = onLoop
      ? headlessSegPpo2(level.depth, fO2bot, fHebot, s)
      : (altSurfaceP + level.depth * BAR_PER_METRE) * fO2bot;
    addHeadlessExposure(hCNSfrac, hOTU, ppO2DescMid, hDescentTime);
    const btAtDepthMin = Math.max(0, level.time - hDescentTime);
    addHeadlessExposure(hCNSfrac, hOTU, ppO2Bottom, btAtDepthMin);
    (lp.steps || []).forEach(seg => {
      if (seg.decoTransit) return; // mdCompatMode: transit folded into stop display
      const d = seg.depth != null ? seg.depth : (seg.type === 'ascent' ? (seg.from + seg.to) / 2 : 0);
      const fHeS = seg.fHe !== undefined ? seg.fHe : fHebot;
      const fO2s = seg.fN2 !== undefined ? Math.max(0, 1 - seg.fN2 - fHeS) : fO2bot;
      const ppO2 = onLoop
        ? headlessSegPpo2(d, fO2s, fHeS, s)
        : fO2s * (altSurfaceP + d * BAR_PER_METRE);
      addHeadlessExposure(hCNSfrac, hOTU, ppO2, seg.dur || 0);
    });
    lp.totalCNS = parseFloat((hCNSfrac.v * 100).toFixed(1));
    lp.totalOTU = Math.round(hOTU.v);
  }

  function mapToEngineReturn(lp, level, s, isMetric) {
    const fO2bot = level.o2 / 100;
    const stops = (lp.stops || []).map(st => ({
      depth: st.depth, time: st.dur, gas: st.gas, type: 'stop',
    }));
    const plan = (lp.steps || [])
      .filter(st => !(st.type === 'ascent' && st.decoTransit))
      .map(st => ({
      type: st.type === 'deco' ? 'stop' : st.type === 'safety' ? 'stop' : st.type,
      depth: st.type === 'ascent' ? st.to : st.depth,
      time: st.dur,
      run: null,
      gas: st.gas,
      o2: Math.round((st.fN2 !== undefined ? (1 - st.fN2 - (st.fHe || 0)) : fO2bot) * 100),
      he: Math.round((st.fHe || 0) * 100),
    }));
    if (plan.length === 0 || plan[0].type !== 'descent') {
      const descentTime = level.depth / (s.descentRate || 20);
      const btAtDepthMin = Math.max(0, level.time - descentTime);
      const bottomGasLabel = getGasLabel(fO2bot, (level.he || 0) / 100);
      plan.unshift({ type: 'bottom', depth: level.depth, time: btAtDepthMin, run: descentTime + btAtDepthMin, gas: bottomGasLabel, o2: level.o2, he: level.he || 0 });
      plan.unshift({ type: 'descent', depth: level.depth, time: descentTime, run: descentTime, gas: bottomGasLabel, o2: level.o2, he: level.he || 0 });
    }
    let runAccum = 0;
    plan.forEach(seg => {
      if (seg.run == null) {
        runAccum += (seg.time || 0);
        seg.run = Math.round(runAccum * 10) / 10;
      } else {
        runAccum = seg.run;
      }
    });
    return {
      plan, stops,
      totalRuntime: lp.rt || 0,
      tts: lp.tts || 0,
      totalOTU: lp.totalOTU || 0,
      totalCNS: lp.totalCNS || 0,
      finalTissues: lp.finalTissues || null,
      depthUnit: isMetric ? 'm' : 'ft',
      error: null,
    };
  }

  function calculate(levels, decoGases, settings, profileSplit, environment) {
    applyEnvironment(environment || defaultEnvironment());
    const s = settings || {};
    const isMetric = s.metric !== false;
    const level = levels[0];
    const params = buildZhlScheduleParamsFromEngine(levels, decoGases, s, profileSplit, environment);
    let coreResult;
    try {
      coreResult = runZhlScheduleCore(params);
    } catch (e) {
      return { error: e.message, stops: [], plan: [], totalRuntime: 0 };
    }
    const lp = coreResult.lastPlan;
    if (!lp) return { error: 'No plan generated', stops: [], plan: [], totalRuntime: 0 };
    computeHeadlessCnsOtu(lp, level, s);
    return mapToEngineReturn(lp, level, s, isMetric);
  }

  const api = {
    runZhlScheduleCore,
    buildZhlScheduleParamsFromEngine,
    splitZhlProfileLevels,
    zhlOptimalSwitchDepth,
    calculate,
    defaultEnvironment,
    applyEnvironment,
    setHeHalfTimeMode,
    OTU_EXPONENT,
    PSCR_MIN_PPO2,
    PSCR_LOOP_VOLUME_MIN,
    PSCR_LOOP_VOLUME_MAX,
    PSCR_METABOLIC_O2_MIN,
    PSCR_METABOLIC_O2_MAX,
    ZHL16C,
    ZHL16C_HE_HT,
    ZHL16C_HE_HT_BAKER,
    ZHL16C_HE_HT_BUHL2003,
    ZHL16C_HE_AB,
    initTissues,
    depthBar,
    schreiner,
    schreinerLinear,
    saturateLinear,
    saturate,
    ceiling,
    computeSurfaceGF,
    ambientCrossingDepth,
    gfAtDepth,
    ndlClearAtDepth,
    buhNDL,
    getActiveGas,
    enforceMinDecoProfile,
    ppO2Check,
    n2FracFromCustomO2,
    n2FracFromPercentages,
    validateHypoxicDecoGas,
    canonicalCircuit,
    normalizeCCRSettings,
    isRebreatherCircuit,
    loopMixLabelForCore,
    depthAtSetpointCrossing,
    getEffectiveSetpointAtDepth,
    getCcrMetabolicO2Rate,
    computePSCRFractions,
    ccrLoopGasBelowSetpoint,
    getInspiredInertPressures,
    getCCRInertSchreinerParams,
    getSetpointBoundaryDepths,
    splitLinearDepthAtBoundaries,
    splitSegmentAtSetpoint,
    schreinerLinearCCR,
    saturateLinearCCR,
    saturateCCR,
    loadTissuesWithCCR,
    getEffectivePpo2,
    getGasLabel: _scheduleCoreGetGasLabel,
  };

  global.ZhlEngineBundle = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof self !== 'undefined' ? self : globalThis);
'''

out = (
    iife_start
    + physics_core
    + "\n\n"
    + gas_core
    + "\n\n"
    + ccr_core
    + "\n\n"
    + core_fn
    + "\n"
    + postamble
)
(ROOT / "zhl-engine-bundle.js").write_text(out, encoding="utf-8")
print("Wrote zhl-engine-bundle.js", len(out), "bytes")
