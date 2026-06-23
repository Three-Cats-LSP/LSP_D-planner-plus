"""Replace inline Bühlmann block in runDecoSchedule with Tier-3 unified core call."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
html_path = ROOT / "index.html"
text = html_path.read_text(encoding="utf-8")

start_marker = "  // Returns the ppO2 limit for a given fO2 based on O2 fraction bands\n"
end_marker = (
    "  // ── Headless mode early return: skip ceiling/graph/DOM work ─────────────\n"
    "  // Guard moved before ceiling waypoints"
)

start = text.find(start_marker)
if start < 0:
    raise SystemExit("start marker not found")
end = text.find(end_marker, start)
if end < 0:
    raise SystemExit("end marker not found")

replacement = """  // ── Bühlmann via Tier-3 unified core (OC + CCR) ───────────────────────
  const { params: zhlParams, switchDisplays } = buildZhlScheduleParamsFromDom(rawD, depthM, bt);
  zhlParams.ccr = mergeCCRSettings(_ccrSettings);
  zhlParams.onLoop = _zhlOnLoop;
  if (_ccrSettings.bailout) {
    zhlParams.gfL = gfL;
    zhlParams.gfH = gfH;
  }
  applyZhlSwitchDepthDisplays(switchDisplays);
  const zhlCore = runZhlScheduleCore(zhlParams);
  const collapsed = zhlCore.collapsed;
  const collapsedMDP = zhlCore.collapsedMDP;
  const tissuesAtBottom = zhlCore.tissuesAtBottom;
  const tissues = zhlCore.lastPlan.finalTissues.map(t => ({ pN2: t.pN2, pHe: t.pHe || 0 }));
  const decoStops = zhlCore.decoStops;
  const decoTime = zhlCore.decoTime;
  const hasDeco = zhlCore.hasDeco;
  const gasUsed = zhlCore.gasUsed;
  const descentTime = zhlCore.descentTime;
  const trueDecoZoneStart = zhlCore.trueDecoZoneStart;
  let firstStopDepth = zhlCore.firstStopDepth;
  const gfAt = zhlCore.gfAt;
  bottomFN2 = zhlCore.bottomFN2;
  bottomFHe = zhlCore.bottomFHe;
  bottomFO2 = zhlCore.bottomFO2;
  const bottomMixLabel = zhlCore.bottomMixLabel;
  const loopMixLabel = loopMixLabelFor(bottomMixLabel, _ccrSettings);
  const runTimeMin = zhlCore.lastPlan.rt;
  const ttsMin = zhlCore.lastPlan.tts;
  const _headlessExposure = accumulateHeadlessPlanExposure(
    depthM, bt, descentRate, bottomFN2, bottomFHe, bottomFO2, _zhlOnLoop, collapsedMDP, _ccrSettings
  );
  window._lastPlan = {
    ...zhlCore.lastPlan,
    totalOTU: _headlessExposure.totalOTU,
    totalCNS: _headlessExposure.totalCNS,
  };
  const bottomMix = document.getElementById('decoGas')?.value || 'air';
  const maxPPO2 = Math.max(ppo2Deco, 1.5, ppo2Bottom);

  // ── Headless mode early return: skip ceiling/graph/DOM work ─────────────
  // Guard moved before ceiling waypoints"""

text = text[:start] + replacement + text[end + len(end_marker):]
html_path.write_text(text, encoding="utf-8")
print("replaced inline Bühlmann block with Tier-3 core call")
