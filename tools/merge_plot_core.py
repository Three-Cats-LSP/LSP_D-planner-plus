#!/usr/bin/env python3
"""Extract dive profile plot engine from index.html into plot-core.js."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
PLOT_CORE = ROOT / "plot-core.js"
MARKUP_HEADER = ROOT / "ui" / "markup-header.html"

HEADER = '''/**
 * Dive profile graph — canvas render, waypoints, zoom/pan interaction.
 * Loaded by index.html before main inline script.
 * Globals read: units, document, window._decoGasSegments, window._decoCeilingWps,
 *   _lspCssVar, _syncGraphsSectionHeads, scheduleDecoScheduleStackSync (indirect)
 * Globals written: window._decoWaypoints, window._plannerWaypoints, window._plannerGasSegments,
 *   window._plannerGasColorMap, window._plannerCeilingWps, _graphZoom, _graphOpts
 */

'''

# 1-indexed inclusive ranges to remove from index.html
INDEX_RANGES = [
    (9241, 9956),   # setupHiDPI … drawDecoProfileFull
    (11081, 11346), # _graphOpts, drawDiveProfile, attachDiveProfileInteraction
]

SCRIPT_TAG = '''<!-- LSP-EXTRACT-BEGIN:plot-core -->
<script src="plot-core.js"></script>
<!-- LSP-EXTRACT-END:plot-core -->
'''

INSERT_AFTER = "<!-- LSP-EXTRACT-END:export-core -->"


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
    if "LSP-EXTRACT-BEGIN:plot-core" in html:
        return html
    if INSERT_AFTER not in html:
        raise SystemExit(f"anchor not found: {INSERT_AFTER}")
    return html.replace(INSERT_AFTER, INSERT_AFTER + "\n" + SCRIPT_TAG, 1)


def main() -> None:
    body = slice_lines(INDEX, INDEX_RANGES)
    PLOT_CORE.write_text(HEADER + body, encoding="utf-8")

    remove_ranges(INDEX, INDEX_RANGES)
    index_text = INDEX.read_text(encoding="utf-8")
    INDEX.write_text(insert_script_tag(index_text), encoding="utf-8")

    if MARKUP_HEADER.exists():
        mh = MARKUP_HEADER.read_text(encoding="utf-8")
        MARKUP_HEADER.write_text(insert_script_tag(mh), encoding="utf-8")

    print(f"Created {PLOT_CORE.name}: {len(PLOT_CORE.read_text(encoding='utf-8').splitlines())} lines")
    print(f"Removed from index.html: {INDEX_RANGES}")


if __name__ == "__main__":
    main()
