#!/usr/bin/env python3
"""One-shot helper: extract UI subsystem blocks from index.html into *-core.js files."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"

# (filename, header, list of (start_line, end_line) inclusive 1-based)
EXTRACTIONS: list[tuple[str, str, list[tuple[int, int]]]] = [
    (
        "surf-interval-core.js",
        """/**
 * Surface interval calculator — RUNTIME UI CORE.
 * Loaded by index.html before main inline script.
 * Globals read: units, altSurfaceP, BAR_PER_METRE, WATER_VAPOR, ZHL16C, ZHL16C_HE_HT,
 *   initTissues, saturate, saturateLinear, schreiner, getBottomGasFractions, FN2_AIR,
 *   updateSliderFill
 * Globals written: (none)
 */
""",
        [(11761, 11880), (11882, 11956), (11985, 11996)],
    ),
    (
        "gas-table-core.js",
        """/**
 * Gas table / END / EAD reference — RUNTIME UI CORE.
 * Loaded by index.html before main inline script.
 * Globals read: units, altSurfaceP, BAR_PER_METRE, narcoticN2, narcoticO2, calcEND,
 *   calcGasMODm
 * Globals written: window._endTipTitle, window._endTipText, window._eadTipTitle,
 *   window._eadTipText, window._avgDepthTipTitle, window._avgDepthTipText
 */
""",
        [(11501, 11759)],
    ),
    (
        "gas-plan-core.js",
        """/**
 * Gas plan tab (Rule of Thirds) — RUNTIME UI CORE.
 * Loaded by index.html before main inline script.
 * Globals read: units, document, runDecoSchedule, ensurePDFFontsForPDF, getExportCircuitTag,
 *   showCopyToast, copyFallback, window.jspdf
 * Globals written: _gasRule, window._lastGasPlan
 */
""",
        [(12302, 12823)],
    ),
    (
        "export-core.js",
        """/**
 * Unified export / clipboard / PDF — RUNTIME UI CORE.
 * Loaded by index.html before main inline script.
 * Globals read: units, mGF, altitudeM, altAcclimatized, window._lastPlan, window._lastContingency,
 *   window._lastGasPlan, getExportCircuitTag, getContingencySummaryExport, validateDomDecoGases,
 *   waterDensityDisplayLabel, ensurePDFFontsForPDF, cleanPDF, drawDecoPlanBannerPDF, and DOM ids
 * Globals written: (toast DOM only)
 */
""",
        [(12825, 13474), (13567, 13913), (15587, 16333)],
    ),
    (
        "contingency-core.js",
        """/**
 * Emergency contingency scenario runner — RUNTIME UI CORE.
 * Loaded by index.html before main inline script.
 * Globals read: runDecoSchedule, getBottomGasFractions, getCCRSettingsFromDOM, isRebreatherCircuit,
 *   domDepthToM, parseRunMinutes, getPlanSummaryExport, formatDecoZoneStart, units, mGF, and DOM
 * Globals written: _contingencyRunning, contGasLose, contExtraBT, contExtraDepth, window._lastContingency
 */
""",
        [(3981, 3984), (13475, 13563), (13915, 14787)],
    ),
]

SCRIPT_INSERT_AFTER = '<script src="zhl-worker-bridge.js"></script>'
SCRIPT_TAGS = [
    '<script src="surf-interval-core.js"></script>',
    '<script src="gas-table-core.js"></script>',
    '<script src="gas-plan-core.js"></script>',
    '<script src="export-core.js"></script>',
    '<script src="contingency-core.js"></script>',
]


def extract_lines(text: str, ranges: list[tuple[int, int]]) -> str:
    lines = text.splitlines(keepends=True)
    chunks: list[str] = []
    for start, end in ranges:
        chunks.append("".join(lines[start - 1 : end]))
    return "".join(chunks)


def remove_ranges(text: str, all_ranges: list[tuple[int, int]]) -> str:
    lines = text.splitlines(keepends=True)
    drop = set()
    for start, end in sorted(all_ranges, reverse=True):
        for i in range(start - 1, end):
            drop.add(i)
    return "".join(line for i, line in enumerate(lines) if i not in drop)


def main() -> None:
    html = INDEX.read_text(encoding="utf-8")
    all_ranges: list[tuple[int, int]] = []

    for filename, header, ranges in EXTRACTIONS:
        body = extract_lines(html, ranges)
        out = ROOT / filename
        out.write_text(header + "\n" + body.rstrip() + "\n", encoding="utf-8")
        print(f"wrote {filename} ({len(body.splitlines())} lines)")
        all_ranges.extend(ranges)

    # Remove extracted blocks (reverse order by start line)
    for start, end in sorted(all_ranges, key=lambda r: r[0], reverse=True):
        lines = html.splitlines(keepends=True)
        html = "".join(lines[: start - 1] + lines[end:])

    if SCRIPT_INSERT_AFTER not in html:
        raise SystemExit("script insert anchor missing")
    insert = SCRIPT_INSERT_AFTER + "\n" + "\n".join(SCRIPT_TAGS)
    html = html.replace(SCRIPT_INSERT_AFTER, insert, 1)

    INDEX.write_text(html, encoding="utf-8")
    print(f"updated {INDEX.name}")


if __name__ == "__main__":
    main()
