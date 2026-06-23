"""Insert Tier-2 ZHL core + builders into index.html before runDecoSchedule."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
html_path = ROOT / "index.html"
core_path = ROOT / "zhl-schedule-core.js"

builders = r'''
// ═══════════════════════════════════════════════
// ZHL SCHEDULE CORE — Tier 2 param builders (DOM + engine)
// ═══════════════════════════════════════════════

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

function injectZhlTravelGasAscent(decoGases, bottomFO2, depthM, ppo2Bottom) {
  const travelInfo = null; // headless engine path has no travel gas
  if (!travelInfo) return decoGases;
  return decoGases;
}

function buildZhlScheduleParamsFromEngine(levels, decoGases, settings, profileSplit) {
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
  let gases = buildZhlDecoGasesFromEngine(decoGases, switchCtx);
  const params = {
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
    continuationLevels: profileSplit.continuation || [],
    minDecoProfile: { enabled: false, m9: 1, m6: 3, isMetric: true },
    decoGases: gases,
  };
  return params;
}

function buildZhlScheduleParamsFromDom(rawD, depthM, bt) {
  const rate = Math.max(1, parseInt(document.getElementById('ascentRate').value) || 9);
  const decoRate = Math.max(1, parseInt(document.getElementById('decoAscentRate').value) || 9);
  const surfaceRate = Math.max(1, parseInt(document.getElementById('surfaceAscentRate').value) || 9);
  const descentRate = Math.max(1, parseInt(document.getElementById('descentRate').value) || 22);
  const ppo2Bottom = parseFloat(document.getElementById('ppo2Bottom').value) || 1.4;
  const ppo2Deco = parseFloat(document.getElementById('ppo2Deco').value) || 1.6;
  const minStopTime = parseFloat(document.getElementById('minStopTime').value) || 1;
  const lastStop = parseInt(document.getElementById('lastDecoStop').value) || 3;
  const decoStep = parseInt(document.getElementById('decoStep').value) || 3;
  const metric = units === 'metric';
  const switchCtx = { ppo2Bottom, ppo2Deco, lastStop, decoStep, metric };
  const _botFracs = getBottomGasFractions();
  const bottomFN2 = _botFracs.fN2;
  const bottomFHe = _botFracs.fHe;
  const bottomFO2 = _botFracs.fO2;
  const bottomMixLabel = getGasLabel(bottomFO2, bottomFHe);
  const dU = metric;
  const decoGases = [];
  const switchDisplays = [];
  for (const idx of getAllDecoGasIds()) {
    const dgf = getDecoCardFractions(idx);
    const fN2 = dgf ? dgf.fN2 : getDecoGasFrac(`dg${idx}Mix`, `dg${idx}CustomO2`);
    const fHe = dgf ? (dgf.fHe || 0) : 0;
    const fO2 = dgf ? dgf.fO2 : (fN2 != null ? Math.max(0, 1 - fN2 - fHe) : null);
    const label = getDecoGasLabel(`dg${idx}Mix`, `dg${idx}CustomO2`);
    const depth = fN2 !== null ? zhlOptimalSwitchDepth(fO2 ?? Math.max(0, 1 - fN2 - fHe), switchCtx) : null;
    if (depth !== null && fN2 !== null) {
      switchDisplays.push({
        idx,
        text: (dU ? depth + 'm' : mToFt(depth) + 'ft') + '  (ppO₂ ' +
          ((altSurfaceP + depth * BAR_PER_METRE) * (fO2 != null ? fO2 : (1 - fN2))).toFixed(2) + ')',
      });
      decoGases.push({ depth, fN2, fHe, fO2: fO2 ?? Math.max(0, 1 - fN2 - fHe), label });
    } else {
      switchDisplays.push({ idx, text: '—' });
    }
  }
  decoGases.sort((a, b) => b.depth - a.depth);
  const travelInfo = getTravelGasInfo();
  if (travelInfo) {
    const botMODm = bottomFO2 > 0
      ? Math.floor((ppo2Bottom / bottomFO2 - altSurfaceP) / BAR_PER_METRE)
      : depthM;
    const travelFO2 = 1 - travelInfo.fN2;
    const ppO2AtBotMOD = (altSurfaceP + botMODm * BAR_PER_METRE) * travelFO2;
    if (ppO2AtBotMOD <= ppo2Bottom + 0.01) {
      decoGases.push({
        depth: botMODm,
        fN2: travelInfo.fN2,
        fHe: 0,
        fO2: travelFO2,
        label: travelInfo.label,
        isTravelGas: true,
      });
      decoGases.sort((a, b) => b.depth - a.depth);
    }
  }
  return {
    params: {
      depthM, bt, rawD, metric,
      ascentRate: rate,
      decoAscentRate: decoRate,
      surfaceAscentRate: surfaceRate,
      descentRate,
      gfL: mGF.low / 100,
      gfH: mGF.high / 100,
      ppo2Bottom, ppo2Deco,
      minStopTime,
      switchPauseT: 0,
      mdCompatMode: (document.getElementById('decoTransitMode')?.value || 'multideco') === 'multideco',
      lastStop, decoStep,
      shallowGradient: document.getElementById('shallowGradient')?.value === 'on',
      bottomFN2, bottomFHe, bottomFO2, bottomMixLabel,
      travelInfo,
      repState: (window._zhlRepState && Array.isArray(window._zhlRepState.tissues)) ? window._zhlRepState : null,
      continuationLevels: (window._zhlHeadless && Array.isArray(window._zhlContinuationLevels))
        ? window._zhlContinuationLevels : [],
      minDecoProfile: {
        enabled: document.getElementById('minDecoProfileEnable')?.value === 'yes',
        m9: parseFloat(document.getElementById('minDeco9m')?.value) || 1,
        m6: parseFloat(document.getElementById('minDeco6m')?.value) || 3,
        isMetric: document.getElementById('unitSel')?.value !== 'imperial',
      },
      decoGases,
    },
    switchDisplays,
  };
}

function applyZhlSwitchDepthDisplays(switchDisplays) {
  if (!switchDisplays || window._zhlHeadless) return;
  switchDisplays.forEach(({ idx, text }) => {
    const swEl = document.getElementById(`dg${idx}SwitchDepthDisplay`);
    if (swEl) swEl.value = text;
  });
}

'''

core = core_path.read_text(encoding='utf-8')
idx = core.find('function runZhlScheduleCore')
if idx < 0:
    raise SystemExit('runZhlScheduleCore not found in core file')
core_fn = core[idx:].strip()

html = html_path.read_text(encoding='utf-8')
marker = 'function runDecoSchedule() {'
if marker not in html:
    raise SystemExit('marker not found')

if 'function runZhlScheduleCore' in html:
    print('already inserted — skip')
    raise SystemExit(0)

insert = builders + '\n' + core_fn + '\n\n'
html = html.replace(marker, insert + marker, 1)
html_path.write_text(html, encoding='utf-8')
print('inserted Tier-2 core before runDecoSchedule')
