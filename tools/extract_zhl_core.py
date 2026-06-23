"""One-off helper: extract runZhlScheduleCore from index.html Bühlmann block."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
lines = (ROOT / "index.html").read_text(encoding="utf-8").splitlines(keepends=True)

core_lines = lines[9195:9629]
core = "".join(core_lines)

subs = [
    (
        "window._zhlRepState && Array.isArray(window._zhlRepState.tissues)",
        "params.repState && Array.isArray(params.repState.tissues)",
    ),
    ("const rep = window._zhlRepState;", "const rep = params.repState;"),
    (
        "(window._zhlHeadless && Array.isArray(window._zhlContinuationLevels))\n"
        "    ? window._zhlContinuationLevels : []",
        "Array.isArray(params.continuationLevels) ? params.continuationLevels : []",
    ),
    (
        "const sgOn = document.getElementById('shallowGradient')?.value === 'on';",
        "const sgOn = !!params.shallowGradient;",
    ),
    (
        "const _mdpEnabled   = document.getElementById('minDecoProfileEnable')?.value === 'yes';",
        "const _mdpEnabled   = !!params.minDecoProfile?.enabled;",
    ),
    (
        "const _mdp9m        = parseFloat(document.getElementById('minDeco9m')?.value) || 1;",
        "const _mdp9m        = params.minDecoProfile?.m9 ?? 1;",
    ),
    (
        "const _mdp6m        = parseFloat(document.getElementById('minDeco6m')?.value) || 3;",
        "const _mdp6m        = params.minDecoProfile?.m6 ?? 3;",
    ),
    (
        "const _mdpIsMetric  = document.getElementById('unitSel')?.value !== 'imperial';",
        "const _mdpIsMetric  = params.minDecoProfile?.isMetric !== false;",
    ),
    ("window._lastPlan = {", "const lastPlan = {"),
]

for old, new in subs:
    if old not in core:
        print("MISSING:", old[:70])
    core = core.replace(old, new)

header = """/**
 * ZHL Bühlmann schedule core (Tier 2) — pure computation, no DOM.
 * Requires Bühlmann helpers from index.html (initTissues, saturate, etc.).
 */
function runZhlScheduleCore(params) {
  const depthM = params.depthM;
  const bt = params.bt;
  const rate = params.ascentRate;
  const decoRate = params.decoAscentRate;
  const surfaceRate = params.surfaceAscentRate;
  const descentRate = params.descentRate;
  const gfL = params.gfL;
  const gfH = params.gfH;
  const ppo2Bottom = params.ppo2Bottom;
  const ppo2Deco = params.ppo2Deco;
  const minStopT = params.minStopTime;
  const switchPauseT = params.switchPauseT || 0;
  const mdCompatMode = params.mdCompatMode !== false;
  const lastStop = params.lastStop;
  const decoStep = params.decoStep;
  const ppo2High = ppo2Deco;
  const ppo2Mid = 1.5;
  const ppo2Low = params.ppo2Bottom;
  const bottomFN2 = params.bottomFN2;
  const bottomFHe = params.bottomFHe;
  const bottomFO2 = params.bottomFO2;
  const bottomMixLabel = params.bottomMixLabel;
  const decoGases = params.decoGases;

  function getPPO2Limit(fO2) {
    const fO2pct = fO2 * 100;
    if (fO2pct >= 45) return ppo2High;
    if (fO2pct >= 28) return ppo2Mid;
    return ppo2Low;
  }

  const travelInfo = params.travelInfo || null;
  const travelSwitchM = travelInfo ? Math.min(travelInfo.switchDepthM, depthM) : 0;

"""

footer = """
  return {
    lastPlan,
    collapsed,
    collapsedMDP,
    tissuesAtBottom,
    decoStops,
    decoTime,
    hasDeco,
    gasUsed,
    descentTime,
    trueDecoZoneStart,
    firstStopDepth,
    gfAt,
    depthM,
    bt,
    rate,
    decoRate,
    surfaceRate,
    descentRate,
    bottomFN2,
    bottomFHe,
    bottomFO2,
    bottomMixLabel,
    rawD: params.rawD,
    dU: params.metric,
  };
}

if (typeof window !== 'undefined') window.runZhlScheduleCore = runZhlScheduleCore;
"""

out = header + core + footer
(ROOT / "zhl-schedule-core.js").write_text(out, encoding="utf-8")
print("written", len(out), "chars to zhl-schedule-core.js")
