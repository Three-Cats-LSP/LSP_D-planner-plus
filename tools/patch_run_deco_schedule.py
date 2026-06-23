"""Replace inline Bühlmann block in runDecoSchedule with Tier-2 core call."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
html_path = ROOT / "index.html"
lines = html_path.read_text(encoding="utf-8").splitlines(keepends=True)

start_marker = "  // Returns the ppO2 limit for a given fO2 based on O2 fraction bands\n"
end_marker = "  if (window._zhlHeadless) return;\n"

text = "".join(lines)
start = text.find(start_marker)
if start < 0:
    raise SystemExit("start marker not found")
end = text.find(end_marker, start)
if end < 0:
    raise SystemExit("end marker not found")
end += len(end_marker)

replacement = """  // ── Bühlmann via Tier-2 pure core (no inline DOM reads) ───────────────
  const { params: zhlParams, switchDisplays } = buildZhlScheduleParamsFromDom(rawD, depthM, bt);
  applyZhlSwitchDepthDisplays(switchDisplays);
  const zhlCore = runZhlScheduleCore(zhlParams);
  window._lastPlan = zhlCore.lastPlan;
  const collapsed = zhlCore.collapsed;
  const collapsedMDP = zhlCore.collapsedMDP;
  const tissuesAtBottom = zhlCore.tissuesAtBottom;
  const decoStops = zhlCore.decoStops;
  const decoTime = zhlCore.decoTime;
  const hasDeco = zhlCore.hasDeco;
  const gasUsed = zhlCore.gasUsed;
  const descentTime = zhlCore.descentTime;
  const trueDecoZoneStart = zhlCore.trueDecoZoneStart;
  let firstStopDepth = zhlCore.firstStopDepth;
  const gfAt = zhlCore.gfAt;
  const bottomFN2 = zhlCore.bottomFN2;
  const bottomFHe = zhlCore.bottomFHe;
  const bottomFO2 = zhlCore.bottomFO2;
  const bottomMixLabel = zhlCore.bottomMixLabel;
  const dU = zhlCore.dU;
  const bottomMix = document.getElementById('decoGas')?.value || 'air';
  const maxPPO2 = Math.max(ppo2Deco, 1.5, ppo2Bottom);

  // ── Headless mode early return: skip ceiling/graph/DOM work ─────────────
  if (window._zhlHeadless) return;

"""

text = text[:start] + replacement + text[end:]
html_path.write_text(text, encoding="utf-8")
print("replaced inline Bühlmann block with core call")
