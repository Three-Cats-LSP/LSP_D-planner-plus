"""Replace ZHLEngine with Tier-2 pure core path (no DOM mutation)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
html_path = ROOT / "index.html"
text = html_path.read_text(encoding="utf-8")

start = text.find("// ZHL ENGINE — headless Bühlmann interface")
end = text.find("if (typeof window !== 'undefined') window.ZHLEngine = ZHLEngine;", start)
if start < 0 or end < 0:
    raise SystemExit("ZHLEngine markers not found")

new_block = r'''// ZHL ENGINE — headless Bühlmann interface for test harnesses
// Tier 2: pure runZhlScheduleCore(params) — no DOM reads or writes.
// Mirrors VPMEngine.calculate(levels, gases, settings, 'ZHLC_GF').
// ═══════════════════════════════════════════════
const ZHLEngine = (() => {
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
    const hAltP = altSurfaceP || 1.01325;
    const hBAR = BAR_PER_METRE || 0.1;
    const hDescentRate = s.descentRate || 20;
    const hDescentTime = level.depth / hDescentRate;
    addHeadlessExposure(hCNSfrac, hOTU, (hAltP + (level.depth / 2) * hBAR) * fO2bot, hDescentTime);
    addHeadlessExposure(hCNSfrac, hOTU, (hAltP + level.depth * hBAR) * fO2bot, level.time);
    (lp.steps || []).forEach(seg => {
      const d = seg.depth != null ? seg.depth : (seg.type === 'ascent' ? (seg.from + seg.to) / 2 : 0);
      const fO2s = seg.fN2 !== undefined ? Math.max(0, 1 - seg.fN2 - (seg.fHe || 0)) : fO2bot;
      addHeadlessExposure(hCNSfrac, hOTU, fO2s * (hAltP + d * hBAR), seg.dur || 0);
    });
    lp.totalCNS = parseFloat((hCNSfrac.v * 100).toFixed(1));
    lp.totalOTU = Math.round(hOTU.v);
  }

  function mapToEngineReturn(lp, level, s, isMetric) {
    const fO2bot = level.o2 / 100;
    const stops = (lp.stops || []).map(st => ({
      depth: st.depth, time: st.dur, gas: st.gas, type: 'stop'
    }));
    const plan = (lp.steps || []).map(st => ({
      type: st.type === 'deco' ? 'stop' : st.type === 'safety' ? 'stop' : st.type,
      depth: st.type === 'ascent' ? st.to : st.depth,
      time: st.dur,
      run: null,
      gas: st.gas,
      o2: Math.round((st.fN2 !== undefined ? (1 - st.fN2 - (st.fHe || 0)) : fO2bot) * 100),
      he: Math.round((st.fHe || 0) * 100)
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
      plan,
      stops,
      totalRuntime: lp.rt || 0,
      tts: lp.tts || 0,
      totalOTU: lp.totalOTU || 0,
      totalCNS: lp.totalCNS || 0,
      finalTissues: lp.finalTissues || null,
      depthUnit: isMetric ? 'm' : 'ft',
      error: null
    };
  }

  function calculate(levels, decoGases, settings) {
    const validation = validateEngineInputs(levels, decoGases);
    if (!validation.ok) return engineValidationError(validation);
    const s = settings || {};
    const isMetric = s.metric !== false;
    const profileVal = validateZhlHeadlessProfile(levels);
    if (!profileVal.ok) {
      return engineValidationError({ ok: false, errors: [profileVal] });
    }
    const profileSplit = splitZhlProfileLevels(levels);
    const level = levels[0];
    const params = buildZhlScheduleParamsFromEngine(levels, decoGases, s, profileSplit);
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

  return { calculate, MODEL: 'ZHLC_GF' };
})();
'''

text = text[:start] + new_block + "\n" + text[end:]
html_path.write_text(text, encoding="utf-8")
print("replaced ZHLEngine with Tier-2 pure path")
