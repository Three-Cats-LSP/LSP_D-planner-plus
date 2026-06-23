"""Patch index.html for Tier 3: bundle load, thin wrappers, remove inline core."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
html_path = ROOT / "index.html"
html = html_path.read_text(encoding="utf-8")

# 1. Script tags in <head>
needle = '<script src="capacitor-bridge.js"></script>'
insert = needle + """
<script src="zhl-engine-bundle.js"></script>
<script src="zhl-worker-bridge.js"></script>"""
if "zhl-engine-bundle.js" not in html:
    html = html.replace(needle, insert, 1)

# 2. Replace Tier-2 block (builders + inline core) with Tier-3 thin layer
start_marker = "// ═══════════════════════════════════════════════\n// ZHL SCHEDULE CORE — Tier 2 param builders (DOM + engine)"
end_marker = "if (typeof window !== 'undefined') window.runZhlScheduleCore = runZhlScheduleCore;\n\nfunction runDecoSchedule()"

start = html.find(start_marker)
end = html.find(end_marker)
if start < 0 or end < 0:
    raise SystemExit(f"Tier block markers not found: start={start} end={end}")

tier3_block = r'''// ═══════════════════════════════════════════════
// ZHL SCHEDULE CORE — Tier 3 (bundle + DOM param builder)
// ═══════════════════════════════════════════════

function getZhlEnvironment() {
  return {
    altSurfaceP: typeof altSurfaceP !== 'undefined' ? altSurfaceP : 1.01325,
    barPerMetre: BAR_PER_METRE,
    waterVapor: WATER_VAPOR,
    altAcclimatized: typeof altAcclimatized !== 'undefined' ? altAcclimatized : true,
    allowO2AtMOD: typeof allowO2AtMOD !== 'undefined' ? allowO2AtMOD : true,
  };
}

function zhlOptimalSwitchDepth(fO2, ctx) {
  ZhlEngineBundle.applyEnvironment(getZhlEnvironment());
  return ZhlEngineBundle.zhlOptimalSwitchDepth(fO2, ctx);
}

function buildZhlScheduleParamsFromEngine(levels, decoGases, settings, profileSplit) {
  return ZhlEngineBundle.buildZhlScheduleParamsFromEngine(
    levels, decoGases, settings, profileSplit, getZhlEnvironment()
  );
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
      environment: getZhlEnvironment(),
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

function runZhlScheduleCore(params) {
  if (!params.environment) {
    params = Object.assign({}, params, { environment: getZhlEnvironment() });
  }
  return ZhlEngineBundle.runZhlScheduleCore(params);
}

'''

html = html[:start] + tier3_block + end_marker + html[end + len(end_marker):]

# 3. Replace duplicate splitZhlProfileLevels with thin wrapper
split_old = """/** Deepest level + monotonic-shallower continuation (matches VPMEngine profile split). */
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
}"""

split_new = """/** Deepest level + monotonic-shallower continuation (matches VPMEngine profile split). */
function splitZhlProfileLevels(levels) {
  return ZhlEngineBundle.splitZhlProfileLevels(levels);
}"""

if split_old in html:
    html = html.replace(split_old, split_new, 1)

# 4. Simplify ZHLEngine to delegate to bundle + worker
zhl_old_start = "// ═══════════════════════════════════════════════\n// ZHL ENGINE — headless Bühlmann interface for test harnesses\n// Tier 2:"
zhl_old_end = "if (typeof window !== 'undefined') window.ZHLEngine = ZHLEngine; // expose for test harnesses"

zs = html.find(zhl_old_start)
ze = html.find(zhl_old_end)
if zs < 0 or ze < 0:
    raise SystemExit(f"ZHLEngine block not found: {zs} {ze}")

zhl_new = r'''// ═══════════════════════════════════════════════
// ZHL ENGINE — headless Bühlmann interface for test harnesses
// Tier 3: ZhlEngineBundle (sync) + ZhlWorkerBridge (async worker)
// Mirrors VPMEngine.calculate(levels, gases, settings, 'ZHLC_GF').
// ═══════════════════════════════════════════════
const ZHLEngine = (() => {
  function calculate(levels, decoGases, settings) {
    const validation = validateEngineInputs(levels, decoGases);
    if (!validation.ok) return engineValidationError(validation);
    const profileVal = validateZhlHeadlessProfile(levels);
    if (!profileVal.ok) {
      return engineValidationError({ ok: false, errors: [profileVal] });
    }
    const s = settings || {};
    const profileSplit = ZhlEngineBundle.splitZhlProfileLevels(levels);
    return ZhlEngineBundle.calculate(levels, decoGases, s, profileSplit, getZhlEnvironment());
  }

  async function calculateInWorker(levels, decoGases, settings) {
    const validation = validateEngineInputs(levels, decoGases);
    if (!validation.ok) return engineValidationError(validation);
    const profileVal = validateZhlHeadlessProfile(levels);
    if (!profileVal.ok) {
      return engineValidationError({ ok: false, errors: [profileVal] });
    }
    const s = settings || {};
    const profileSplit = ZhlEngineBundle.splitZhlProfileLevels(levels);
    try {
      return await ZhlWorkerBridge.calculateInWorker(
        levels, decoGases, s, profileSplit, getZhlEnvironment()
      );
    } catch (e) {
      return { error: e.message, stops: [], plan: [], totalRuntime: 0 };
    }
  }

  return { calculate, calculateInWorker, MODEL: 'ZHLC_GF' };
})();

'''

html = html[:zs] + zhl_new + zhl_old_end + html[ze + len(zhl_old_end):]

html_path.write_text(html, encoding="utf-8")
print("Patched index.html for Tier 3")
