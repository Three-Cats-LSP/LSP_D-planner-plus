"""Build zhl-engine-bundle.js — self-contained Tier 3 Bühlmann module (main thread + worker)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
html = (ROOT / "index.html").read_text(encoding="utf-8")
core_path = ROOT / "zhl-schedule-core.js"
if not core_path.is_file():
    raise SystemExit("zhl-schedule-core.js missing — run tools/extract_zhl_core.py first")
core_fn = core_path.read_text(encoding="utf-8")
# Drop file header comment block
if core_fn.startswith("/**"):
    end = core_fn.find("*/")
    core_fn = core_fn[end + 2 :].lstrip()

# Extract gas helpers from index.html
ga_start = html.find("function getActiveGas(")
ga_end = html.find("// ── VPM SCHEDULE RUNNER", ga_start)
if ga_start < 0 or ga_end < 0:
    raise SystemExit("getActiveGas block not found")
gas_helpers = html[ga_start:ga_end].strip()

# enforceMinDecoProfile (must end before getActiveGas)
emd_start = html.find("function enforceMinDecoProfile(")
emd_end = html.find("\n\n\nlet _confirmCallback", emd_start)
if emd_start < 0 or emd_end < 0:
    raise SystemExit("enforceMinDecoProfile block not found")
enforce = html[emd_start:emd_end].strip()

core_fn = core_fn.replace(
    "\nif (typeof window !== 'undefined') window.runZhlScheduleCore = runZhlScheduleCore;\n",
    "\n",
)
core_fn = core_fn.replace(
    "function runZhlScheduleCore(params) {",
    "function runZhlScheduleCore(params) {\n  applyEnvironment(params.environment || defaultEnvironment());",
    1,
)

preamble = r'''/**
 * ZHL Engine Bundle — Tier 3 isolated Bühlmann module.
 * Loaded on main thread and in zhl-schedule-worker.js (importScripts).
 */
(function (global) {
  'use strict';

  const ZHL16C = [
    [4.0,1.2599,0.5050],[8.0,1.0000,0.6514],[12.5,0.8618,0.7222],[18.5,0.7562,0.7825],
    [27.0,0.6200,0.8126],[38.3,0.5043,0.8434],[54.3,0.4410,0.8693],[77.0,0.4000,0.8910],
    [109.0,0.3750,0.9092],[146.0,0.3500,0.9222],[187.0,0.3295,0.9319],[239.0,0.3065,0.9403],
    [305.0,0.2835,0.9477],[390.0,0.2610,0.9544],[498.0,0.2480,0.9602],[635.0,0.2327,0.9653],
  ];
  const ZHL16C_HE_HT = [1.88,3.02,4.72,6.99,10.21,14.48,20.53,29.11,41.20,55.19,70.69,90.34,115.29,147.42,188.24,240.03];
  const ZHL16C_HE_AB = [
    [1.7424,0.4245],[1.3830,0.5747],[1.1919,0.6527],[1.0458,0.7223],[0.9220,0.7582],[0.8205,0.7957],
    [0.7305,0.8279],[0.6502,0.8553],[0.5950,0.8757],[0.5545,0.8903],[0.5333,0.8997],[0.5189,0.9073],
    [0.5181,0.9122],[0.5176,0.9171],[0.5172,0.9217],[0.5119,0.9267],
  ];
  const OTU_EXPONENT = 0.8333;
  const SEA_LEVEL_P = 1.01325;

  let altSurfaceP = SEA_LEVEL_P;
  let BAR_PER_METRE = 0.1;
  let WATER_VAPOR = 0.0627;
  let altAcclimatized = true;
  let allowO2AtMOD = true;

  function applyEnvironment(env) {
    env = env || {};
    altSurfaceP = env.altSurfaceP ?? SEA_LEVEL_P;
    BAR_PER_METRE = env.barPerMetre ?? 0.1;
    WATER_VAPOR = env.waterVapor ?? 0.0627;
    altAcclimatized = env.altAcclimatized !== false;
    allowO2AtMOD = env.allowO2AtMOD !== false;
  }

  function defaultEnvironment() {
    return {
      altSurfaceP: SEA_LEVEL_P,
      barPerMetre: 0.1,
      waterVapor: 0.0627,
      altAcclimatized: true,
      allowO2AtMOD: true,
    };
  }

  function depthBar(m) { return altSurfaceP + m * BAR_PER_METRE; }
  function schreiner(p0, pGas, ht, t) { return pGas + (p0 - pGas) * Math.exp(-Math.LN2 / ht * t); }
  function schreinerLinear(p0, fN2, ht, t, p0Amb, R) {
    const k = Math.LN2 / ht;
    const piN2 = (p0Amb - WATER_VAPOR) * fN2;
    const rN2 = R * fN2;
    return piN2 + rN2 * (t - 1 / k) - (piN2 - p0 - rN2 / k) * Math.exp(-k * t);
  }

  function initTissues() {
    const surfP = altAcclimatized ? altSurfaceP : SEA_LEVEL_P;
    const pN2 = (surfP - WATER_VAPOR) * 0.7902;
    return ZHL16C.map(() => ({ pN2, pHe: 0 }));
  }

  function saturateLinear(tissues, fromDepth, toDepth, t, fN2, fHe) {
    if (t <= 0) return tissues;
    const p0Amb = depthBar(fromDepth);
    const pEndAmb = depthBar(toDepth);
    const R = (pEndAmb - p0Amb) / t;
    const fH = fHe || 0;
    return tissues.map((t0, i) => ({
      pN2: schreinerLinear(t0.pN2, fN2, ZHL16C[i][0], t, p0Amb, R),
      pHe: fH > 0 ? schreinerLinear(t0.pHe, fH, ZHL16C_HE_HT[i], t, p0Amb, R) : t0.pHe,
    }));
  }

  function saturate(tissues, depthM, t, fN2, fHe) {
    const pAmb = depthBar(depthM);
    const pN2insp = (pAmb - WATER_VAPOR) * fN2;
    const pHeinsp = (pAmb - WATER_VAPOR) * (fHe || 0);
    return tissues.map((t0, i) => ({
      pN2: schreiner(t0.pN2, pN2insp, ZHL16C[i][0], t),
      pHe: schreiner(t0.pHe, pHeinsp, ZHL16C_HE_HT[i], t),
    }));
  }

  function ceiling(tissues, gfHigh) {
    let maxC = 0;
    tissues.forEach((t0, i) => {
      const pN2 = t0.pN2;
      const pHe = t0.pHe || 0;
      const pTotal = pN2 + pHe;
      let a, b;
      if (pHe > 0 && pTotal > 0) {
        a = (pN2 * ZHL16C[i][1] + pHe * ZHL16C_HE_AB[i][0]) / pTotal;
        b = (pN2 * ZHL16C[i][2] + pHe * ZHL16C_HE_AB[i][1]) / pTotal;
      } else {
        [, a, b] = ZHL16C[i];
      }
      const pAmbMin = (pTotal - gfHigh * a) / (1 - gfHigh + gfHigh / b);
      const cM = Math.max(0, (pAmbMin - altSurfaceP) / BAR_PER_METRE);
      if (cM > maxC) maxC = cM;
    });
    return maxC;
  }

  function computeSurfaceGF(tissues) {
    if (!tissues || !tissues.length) return null;
    const P_surf = altSurfaceP;
    let maxGF = -Infinity;
    tissues.forEach((t, i) => {
      const pTotal = (t.pN2 || 0) + (t.pHe || 0);
      if (pTotal <= 0) return;
      let a, b;
      const pN2 = t.pN2 || 0, pHe = t.pHe || 0;
      if (pHe > 0 && pTotal > 0) {
        a = (pN2 * ZHL16C[i][1] + pHe * ZHL16C_HE_AB[i][0]) / pTotal;
        b = (pN2 * ZHL16C[i][2] + pHe * ZHL16C_HE_AB[i][1]) / pTotal;
      } else {
        [, a, b] = ZHL16C[i];
      }
      const mValue = a + P_surf / b - P_surf;
      if (mValue <= 0) return;
      const gf = (pTotal - P_surf) / mValue;
      if (gf > maxGF) maxGF = gf;
    });
    return maxGF === -Infinity ? 0 : Math.max(0, maxGF * 100);
  }

  function ambientCrossingDepth(tissues) {
    let maxD = 0;
    tissues.forEach(t0 => {
      const pTotal = t0.pN2 + (t0.pHe || 0);
      const d = (pTotal - altSurfaceP) / BAR_PER_METRE;
      if (d > maxD) maxD = d;
    });
    return Math.max(0, maxD);
  }

'''

postamble = r'''

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
      travelInfo: null,
      repState: (s._preTissues && s._preTissues.length)
        ? { tissues: s._preTissues, surfaceIntervalMin: s._surfaceInterval || 0 }
        : null,
      continuationLevels: (profileSplit && profileSplit.continuation) || [],
      minDecoProfile: { enabled: false, m9: 1, m6: 3, isMetric: true },
      decoGases: gases,
      environment: environment || defaultEnvironment(),
    };
  }

  function addHeadlessExposure(hCNSfrac, hOTU, ppO2, dur) {
    if (ppO2 > 0.5 && dur > 0) {
      hOTU.v += dur * Math.pow((ppO2 - 0.5) / 0.5, OTU_EXPONENT);
      const lims = {6:720,7:570,8:450,9:360,10:300,11:240,12:210,13:180,14:150,15:120,16:45};
      const lo = Math.floor(ppO2 * 10), hi = lo + 1;
      const lim = (lims[lo] || 0) + ((lims[hi] || 0) - (lims[lo] || 0)) * (ppO2 * 10 - lo);
      const safeLim = lim > 0 ? lim : 45;
      hCNSfrac.v += dur / safeLim;
    }
  }

  function computeHeadlessCnsOtu(lp, level, s) {
    if (!lp || lp.totalCNS != null) return;
    const fO2bot = level.o2 / 100;
    const hCNSfrac = { v: 0 };
    const hOTU = { v: 0 };
    const hDescentRate = s.descentRate || 20;
    const hDescentTime = level.depth / hDescentRate;
    addHeadlessExposure(hCNSfrac, hOTU, (altSurfaceP + (level.depth / 2) * BAR_PER_METRE) * fO2bot, hDescentTime);
    addHeadlessExposure(hCNSfrac, hOTU, (altSurfaceP + level.depth * BAR_PER_METRE) * fO2bot, level.time);
    (lp.steps || []).forEach(seg => {
      const d = seg.depth != null ? seg.depth : (seg.type === 'ascent' ? (seg.from + seg.to) / 2 : 0);
      const fO2s = seg.fN2 !== undefined ? Math.max(0, 1 - seg.fN2 - (seg.fHe || 0)) : fO2bot;
      addHeadlessExposure(hCNSfrac, hOTU, fO2s * (altSurfaceP + d * BAR_PER_METRE), seg.dur || 0);
    });
    lp.totalCNS = parseFloat((hCNSfrac.v * 100).toFixed(1));
    lp.totalOTU = Math.round(hOTU.v);
  }

  function mapToEngineReturn(lp, level, s, isMetric) {
    const fO2bot = level.o2 / 100;
    const stops = (lp.stops || []).map(st => ({
      depth: st.depth, time: st.dur, gas: st.gas, type: 'stop',
    }));
    const plan = (lp.steps || []).map(st => ({
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
      const bottomGasLabel = plan.length > 0 ? (plan[0].gas || 'bottom') : 'bottom';
      plan.unshift({ type: 'bottom', depth: level.depth, time: level.time, run: descentTime + level.time, gas: bottomGasLabel, o2: level.o2, he: level.he || 0 });
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
    OTU_EXPONENT,
  };

  global.ZhlEngineBundle = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof self !== 'undefined' ? self : globalThis);
'''

out = preamble + "\n" + gas_helpers + "\n\n" + enforce + "\n\n" + core_fn + "\n" + postamble
(ROOT / "zhl-engine-bundle.js").write_text(out, encoding="utf-8")
print("Wrote zhl-engine-bundle.js", len(out), "bytes")
