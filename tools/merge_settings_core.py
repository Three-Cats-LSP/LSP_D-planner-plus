#!/usr/bin/env python3
"""Extract UI-ENVIRONMENT + UI-MODE-STATE from index.html into settings-core.js."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
OUT = ROOT / "settings-core.js"
MARKUP_HEADER = ROOT / "ui" / "markup-header.html"

HEADER = '''/**
 * Environment (altitude, water density, narcosis) and app mode/planner state orchestration.
 * Loaded by index.html before other UI runtime cores.
 * Globals read: ZhlEngineBundle, VPMEngine, ZHL16C_HE_HT, ZHL16C_HE_HT_BAKER, ZHL16C_HE_HT_BUHL2003,
 *   runDecoSchedule, runPlanner, renderNDLTable, buildDiveBlocks, setDecoAlgorithm, switchResultTab,
 *   _clearResultSummaryStrip, _setGasWarningBanner, _applyGasWarningStyles, refreshTravelGasFractionWarning,
 *   _travelGasFractionWarning, updateGasMODDisplays, updateTravelGasMOD, calcMODTool, renderModRefTable,
 *   calcBestMixTec, calcBestMix, renderEADTable, renderGasTable, calcCNS, onConservatismChange,
 *   updateCcrGasValidation, calcContingency, syncRecGasMixDisplay, toggleCustomO2, _syncVpmModeUI,
 *   handleGFSelect, setGF, scheduleDecoScheduleStackSync, decorateDecoTableForV3, drawPlannerProfile,
 *   drawDecoProfile, drawDecoProfileFull, drawGFCurve, setMainNav, appSettings
 * Globals written: BAR_PER_METRE, altSurfaceP, altitudeM, altAcclimatized, WATER_VAPOR, narcoticN2, narcoticO2,
 *   navMode, plannerAlgo, algo, units, mGF, allowO2AtMOD, lastTissues, _pendingDecoAlerts,
 *   _pendingDecoAlertsNarcotic, _vpmHeHtSyncFailed, window._lastPlan, _lastVPMResult, window._lastVPMExport
 */

'''

# Keep CUFT_PER_LITRE + OTU_EXPONENT in index.html (2580-2581)
INDEX_RANGES = [
    (2579, 2579),
    (2582, 3534),
]

SCRIPT_TAG = """<!-- LSP-EXTRACT-BEGIN:settings-core -->
<script src="settings-core.js"></script>
<!-- LSP-EXTRACT-END:settings-core -->
"""

INSERT_BEFORE = "<!-- LSP-EXTRACT-BEGIN:surf-interval-core -->"


def slice_lines(path: Path, ranges: list[tuple[int, int]]) -> str:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    out: list[str] = []
    for start, end in ranges:
        out.extend(lines[start - 1 : end])
    return "".join(out)


def remove_ranges(path: Path, ranges: list[tuple[int, int]]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    drop = set()
    for start, end in ranges:
        for i in range(start - 1, end):
            drop.add(i)
    path.write_text("".join(lines[i] for i in range(len(lines)) if i not in drop), encoding="utf-8")


def insert_script_tag(html: str) -> str:
    if "LSP-EXTRACT-BEGIN:settings-core" in html:
        return html
    if INSERT_BEFORE not in html:
        raise SystemExit(f"anchor not found: {INSERT_BEFORE}")
    return html.replace(INSERT_BEFORE, SCRIPT_TAG + "\n" + INSERT_BEFORE, 1)


def main() -> None:
    body = slice_lines(INDEX, INDEX_RANGES)
    OUT.write_text(HEADER + body, encoding="utf-8")

    remove_ranges(INDEX, INDEX_RANGES)
    index_text = INDEX.read_text(encoding="utf-8")
    INDEX.write_text(insert_script_tag(index_text), encoding="utf-8")

    if MARKUP_HEADER.exists():
        mh = MARKUP_HEADER.read_text(encoding="utf-8")
        MARKUP_HEADER.write_text(insert_script_tag(mh), encoding="utf-8")

    out_lines = len(OUT.read_text(encoding="utf-8").splitlines())
    print(f"Created {OUT.name}: {out_lines} lines")
    print(f"Removed from index.html: {INDEX_RANGES}")


if __name__ == "__main__":
    main()
