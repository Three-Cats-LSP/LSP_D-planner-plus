#!/usr/bin/env python3
"""Extract VPM + Bühlmann schedule results rendering from index.html into results-render-core.js."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
OUT = ROOT / "results-render-core.js"
MARKUP_HEADER = ROOT / "ui" / "markup-header.html"

HEADER = '''/**
 * Schedule results rendering — VPM table/summary and Bühlmann deco table + gas consumption.
 * Loaded by index.html before main inline script.
 * Globals read: units, altSurfaceP, BAR_PER_METRE, OTU_EXPONENT, mGF, narcoticN2, narcoticO2,
 *   _contingencyRunning, _gasRule, fmtPpO2, ppO2Check, calcEND, getTravelGasInfo, toMMSS,
 *   formatDecoZoneStart, formatDecoStopDepth, updateDecoSummaryHtml, buildPlanInfoRowHtml,
 *   _renderResultSummaryStrip, _onPlanResultsReady, injectTtsCells, decorateDecoTableForV3,
 *   scheduleDecoScheduleStackSync, renderDecoAlerts, _syncCylToGasPlan, calcGasPlan,
 *   lspVolUnit, lspSacUnit, gpVolWithUnit, _applyGasWarningStyles, _updateGasWarningBannerFromCard,
 *   _setGasWarningBanner, ccrGasLitres, accumGasLitres, addBailoutStressReserve, sacDomToLpm,
 *   getContingencySacMultiplier, mToFt, loopMixLabelFor, getGasLabel, mergeCCRSettings,
 *   isRebreatherCircuit, getEffectivePpo2, getEffectiveSetpointAtDepth, updateTissueViz
 * Globals written: lastTissues, window._lastPlan, window._lastGasConsumed,
 *   window._lastBottomPhaseConsumedL, window._contingencyScratchGasConsumed
 */

'''

VPM_RANGE = (6276, 6805)
GET_PPO2_RANGE = (7281, 7286)
ZHL_RANGE = (7392, 7903)

ZHL_PREFIX = '''// AUDIT-UNIT:UI-ZHL-RESULTS
function renderZhlScheduleResults(ctx) {
  const {
    depthM, bt, rawD, descentRate,
    bottomFN2, bottomFHe, bottomFO2, bottomMixLabel,
    collapsedMDP, tissues, decoTime, hasDeco, firstStopDepth, trueDecoZoneStart,
    zhlCore, zhlOnLoop: _zhlOnLoop, ccrSettings: _ccrSettings, dU, loopMixLabel,
    ppo2Deco, ppo2Bottom,
  } = ctx;
  function getPPO2Limit(fO2) {
    const fO2pct = fO2 * 100;
    if (fO2pct >= 45) return ppo2Deco;
    if (fO2pct >= 28) return 1.5;
    return ppo2Bottom;
  }

'''

ZHL_SUFFIX = "\n}\n"

ZHL_CALL = """  renderZhlScheduleResults({
    depthM, bt, rawD, descentRate,
    bottomFN2, bottomFHe, bottomFO2, bottomMixLabel,
    collapsedMDP, tissues, decoTime, hasDeco, firstStopDepth, trueDecoZoneStart,
    zhlCore, zhlOnLoop: _zhlOnLoop, ccrSettings: _ccrSettings, dU, loopMixLabel,
    ppo2Deco, ppo2Bottom,
  });
"""

PPO2_FIX_OLD = "_ccrPpo2Opts(depthM, true, fo2, phase || 'bottom')"
PPO2_FIX_NEW = """{
        ccr: { ..._ccrSettings, scrRuntimeMin: rowRT },
        onLoop: true,
        fO2: fo2,
      }"""

SCRIPT_TAG = """<!-- LSP-EXTRACT-BEGIN:results-render-core -->
<script src="results-render-core.js"></script>
<!-- LSP-EXTRACT-END:results-render-core -->
"""

INSERT_AFTER = "<!-- LSP-EXTRACT-END:results-panel -->"


def slice_1indexed(lines: list[str], start: int, end: int) -> list[str]:
    return lines[start - 1 : end]


def insert_script_tag(html: str) -> str:
    if "LSP-EXTRACT-BEGIN:results-render-core" in html:
        return html
    if INSERT_AFTER not in html:
        raise SystemExit(f"anchor not found: {INSERT_AFTER}")
    return html.replace(INSERT_AFTER, INSERT_AFTER + "\n" + SCRIPT_TAG, 1)


def main() -> None:
    lines = INDEX.read_text(encoding="utf-8").splitlines(keepends=True)

    vpm_body = "".join(slice_1indexed(lines, *VPM_RANGE))
    zhl_body = "".join(slice_1indexed(lines, *ZHL_RANGE))
    zhl_body = zhl_body.replace(PPO2_FIX_OLD, PPO2_FIX_NEW)

    OUT.write_text(HEADER + vpm_body + "\n" + ZHL_PREFIX + zhl_body + ZHL_SUFFIX, encoding="utf-8")

    vpm_start, vpm_end = VPM_RANGE
    ppo2_start, ppo2_end = GET_PPO2_RANGE
    zhl_start, zhl_end = ZHL_RANGE

    new_lines: list[str] = []
    for i, line in enumerate(lines):
        n = i + 1
        if vpm_start <= n <= vpm_end:
            continue
        if ppo2_start <= n <= ppo2_end:
            continue
        if zhl_start <= n <= zhl_end:
            if n == zhl_start:
                new_lines.append(ZHL_CALL)
            continue
        new_lines.append(line)

    index_text = "".join(new_lines)
    INDEX.write_text(insert_script_tag(index_text), encoding="utf-8")

    if MARKUP_HEADER.exists():
        mh = MARKUP_HEADER.read_text(encoding="utf-8")
        MARKUP_HEADER.write_text(insert_script_tag(mh), encoding="utf-8")

    out_lines = len(OUT.read_text(encoding="utf-8").splitlines())
    print(f"Created {OUT.name}: {out_lines} lines")
    print(f"Removed VPM {VPM_RANGE}, getPPO2Limit {GET_PPO2_RANGE}, ZHL {ZHL_RANGE}")


if __name__ == "__main__":
    main()
