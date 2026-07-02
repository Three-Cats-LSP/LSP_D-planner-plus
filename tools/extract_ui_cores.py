#!/usr/bin/env python3
"""Extract or verify runtime UI cores from index.html using named sentinel markers.

Extraction contract (replaces line-range model):
  - Inline JS blocks: // LSP-EXTRACT-BEGIN:<block-id> … // LSP-EXTRACT-END:<block-id>
  - Post-extraction head: <!-- LSP-EXTRACT-BEGIN:<block-id> --> <script src="…"> <!-- LSP-EXTRACT-END -->

Default command verifies the already-extracted layout. Use --extract for one-shot extraction
only when inline BEGIN/END markers with JS body are still present.

Usage:
  python tools/extract_ui_cores.py          # verify extracted state (CI-safe)
  python tools/extract_ui_cores.py --extract  # one-shot extraction (fails if already done)
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
MARKER_PREFIX = "LSP-EXTRACT"

BEGIN_JS_RE = re.compile(
    rf"^[ \t]*//\s*{re.escape(MARKER_PREFIX)}-BEGIN:([a-z0-9-]+)\s*$",
    re.MULTILINE,
)
END_JS_RE = re.compile(
    rf"^[ \t]*//\s*{re.escape(MARKER_PREFIX)}-END:([a-z0-9-]+)\s*$",
    re.MULTILINE,
)
BEGIN_HTML_RE = re.compile(
    rf"<!--\s*{re.escape(MARKER_PREFIX)}-BEGIN:([a-z0-9-]+)\s*-->",
)
END_HTML_RE = re.compile(
    rf"<!--\s*{re.escape(MARKER_PREFIX)}-END:([a-z0-9-]+)\s*-->",
)
SCRIPT_SRC_RE = re.compile(r'<script\s+src="([^"]+)"\s*></script>')

SCRIPT_INSERT_AFTER = '<script src="zhl-worker-bridge.js"></script>'


@dataclass(frozen=True)
class UiCoreBlock:
    block_id: str
    filename: str
    header: str


UI_CORE_BLOCKS: tuple[UiCoreBlock, ...] = (
    UiCoreBlock(
        "surf-interval-core",
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
    ),
    UiCoreBlock(
        "gas-table-core",
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
    ),
    UiCoreBlock(
        "gas-plan-core",
        "gas-plan-core.js",
        """/**
 * Gas plan tab (Rule of Thirds) — RUNTIME UI CORE.
 * Loaded by index.html before main inline script.
 * Globals read: units, document, runDecoSchedule, ensurePDFFontsForPDF, getExportCircuitTag,
 *   showCopyToast, copyFallback, window.jspdf
 * Globals written: _gasRule, window._lastGasPlan
 */
""",
    ),
    UiCoreBlock(
        "export-core",
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
    ),
    UiCoreBlock(
        "contingency-core",
        "contingency-core.js",
        """/**
 * Emergency contingency scenario runner — RUNTIME UI CORE.
 * Loaded by index.html before main inline script.
 * Globals read: runDecoSchedule, getBottomGasFractions, getCCRSettingsFromDOM, isRebreatherCircuit,
 *   domDepthToM, parseRunMinutes, getPlanSummaryExport, formatDecoZoneStart, units, mGF, and DOM
 * Globals written: _contingencyRunning, contGasLose, contExtraBT, contExtraDepth, window._lastContingency
 */
""",
    ),
    UiCoreBlock(
        "results-panel",
        "results-panel.js",
        """/**
 * Results panel shell — metrics, chips, tabs, schedule decoration.
 * Loaded by index.html before main inline script.
 */
""",
    ),
    UiCoreBlock(
        "planner-shell",
        "planner-shell.js",
        """/**
 * Planner/tools navigation shell and V4 layout bootstrap.
 * Loaded by index.html before main inline script.
 */
""",
    ),
)

EXPECTED_SCRIPT_ORDER = [b.filename for b in UI_CORE_BLOCKS]

# Spot-check: extracted symbols must not remain as definitions in inline script blocks.
INLINE_FORBIDDEN_DEFS: dict[str, tuple[str, ...]] = {
    "surf-interval-core": ("function calcSurfInt(",),
    "gas-table-core": ("function renderGasTable(", "function calcEND_tool("),
    "gas-plan-core": ("function calcGasPlan(", "let _gasRule"),
    "export-core": ("function buildExportText(", "async function exportPDF("),
    "contingency-core": ("function runContingencyScenario(", "function calcContingency("),
    "results-panel": ("function switchResultTab(", "function _renderResultSummaryStrip("),
    "planner-shell": ("function initV3Layout(", "function setNavMode("),
}


class ExtractionError(Exception):
    pass


def _marker_positions(pattern: re.Pattern[str], text: str) -> list[tuple[int, str]]:
    return [(m.start(), m.group(1)) for m in pattern.finditer(text)]


def _pair_js_blocks(html: str) -> dict[str, list[tuple[int, int, str]]]:
    """Return block_id -> list of (begin_pos, end_pos, body) for inline JS markers."""
    begins = _marker_positions(BEGIN_JS_RE, html)
    ends = _marker_positions(END_JS_RE, html)
    by_id: dict[str, list[tuple[int, int]]] = {}
    for pos, block_id in begins:
        by_id.setdefault(block_id, []).append((pos, "begin"))
    for pos, block_id in ends:
        by_id.setdefault(block_id, []).append((pos, "end"))

    out: dict[str, list[tuple[int, int, str]]] = {}
    for block_id, marks in by_id.items():
        if len(marks) != 2:
            raise ExtractionError(
                f"inline JS marker pair for {block_id!r}: expected 1 BEGIN + 1 END, found {len(marks)} markers"
            )
        marks_sorted = sorted(marks, key=lambda t: t[0])
        if marks_sorted[0][1] != "begin" or marks_sorted[1][1] != "end":
            raise ExtractionError(f"inline JS markers for {block_id!r} are out of order")
        b0, b1 = marks_sorted[0][0], marks_sorted[1][0]
        begin_line_end = html.find("\n", b0)
        if begin_line_end == -1:
            begin_line_end = b0
        end_line_start = html.rfind("\n", 0, b1)
        if end_line_start == -1:
            end_line_start = 0
        body = html[begin_line_end + 1 : end_line_start]
        if not body.strip():
            raise ExtractionError(f"inline JS block {block_id!r} is empty or whitespace-only")
        out.setdefault(block_id, []).append((b0, b1, body))
    return out


def _pair_html_blocks(html: str) -> dict[str, list[tuple[int, int, str]]]:
    """Return block_id -> list of (begin_pos, end_pos, inner_html) for head markers."""
    begins = [(m.start(), m.group(1)) for m in BEGIN_HTML_RE.finditer(html)]
    ends = [(m.start(), m.group(1)) for m in END_HTML_RE.finditer(html)]
    by_id: dict[str, list[tuple[int, str]]] = {}
    for pos, block_id in begins:
        by_id.setdefault(block_id, []).append((pos, "begin"))
    for pos, block_id in ends:
        by_id.setdefault(block_id, []).append((pos, "end"))

    out: dict[str, list[tuple[int, int, str]]] = {}
    for block_id, marks in by_id.items():
        if len(marks) != 2:
            raise ExtractionError(
                f"HTML marker pair for {block_id!r}: expected 1 BEGIN + 1 END, found {len(marks)} markers"
            )
        marks_sorted = sorted(marks, key=lambda t: t[0])
        if marks_sorted[0][1] != "begin" or marks_sorted[1][1] != "end":
            raise ExtractionError(f"HTML markers for {block_id!r} are out of order")
        b0, b1 = marks_sorted[0][0], marks_sorted[1][0]
        begin_tag_end = html.find("-->", b0)
        if begin_tag_end == -1:
            raise ExtractionError(f"malformed HTML BEGIN marker for {block_id!r}")
        inner = html[begin_tag_end + 3 : b1]
        out.setdefault(block_id, []).append((b0, b1, inner))
    return out


def _assert_no_overlap(ranges: list[tuple[int, int, str]], label: str) -> None:
    sorted_ranges = sorted((a, b) for a, b, _ in ranges)
    for i in range(1, len(sorted_ranges)):
        if sorted_ranges[i][0] < sorted_ranges[i - 1][1]:
            raise ExtractionError(f"{label}: extracted blocks overlap")


def has_pending_inline_extraction(html: str) -> bool:
    return bool(BEGIN_JS_RE.search(html))


def is_already_extracted(html: str) -> bool:
    if has_pending_inline_extraction(html):
        return False
    html_blocks = _pair_html_blocks(html)
    return all(block.block_id in html_blocks for block in UI_CORE_BLOCKS)


def verify_extracted_state(html: str | None = None) -> None:
    html = html if html is not None else INDEX.read_text(encoding="utf-8")

    if has_pending_inline_extraction(html):
        raise ExtractionError(
            "inline LSP-EXTRACT-BEGIN markers still present — run with --extract or complete migration"
        )

    html_blocks = _pair_html_blocks(html)
    expected_ids = [b.block_id for b in UI_CORE_BLOCKS]

    for block_id in expected_ids:
        if block_id not in html_blocks:
            raise ExtractionError(f"missing HTML marker pair for {block_id!r}")
        if len(html_blocks[block_id]) != 1:
            raise ExtractionError(f"duplicate HTML marker pair for {block_id!r}")

    extra = set(html_blocks) - set(expected_ids)
    if extra:
        raise ExtractionError(f"unexpected HTML extraction markers: {sorted(extra)}")

    script_tags_in_order: list[str] = []
    for block in UI_CORE_BLOCKS:
        inner = html_blocks[block.block_id][0][2]
        matches = SCRIPT_SRC_RE.findall(inner)
        if len(matches) != 1:
            raise ExtractionError(
                f"block {block.block_id!r}: expected exactly one <script src> between markers, found {len(matches)}"
            )
        if matches[0] != block.filename:
            raise ExtractionError(
                f"block {block.block_id!r}: script src {matches[0]!r} != expected {block.filename!r}"
            )
        script_tags_in_order.append(matches[0])

    if script_tags_in_order != EXPECTED_SCRIPT_ORDER:
        raise ExtractionError(
            f"script tag order mismatch: got {script_tags_in_order}, expected {EXPECTED_SCRIPT_ORDER}"
        )

    for tag in EXPECTED_SCRIPT_ORDER:
        count = html.count(f'<script src="{tag}"></script>')
        if count != 1:
            raise ExtractionError(f'<script src="{tag}"></script> must appear exactly once, found {count}')

    inline_scripts = re.findall(r"<script(?![^>]*src)[^>]*>(.*?)</script>", html, re.DOTALL)
    inline_js = "\n\n".join(inline_scripts)
    for block in UI_CORE_BLOCKS:
        path = ROOT / block.filename
        if not path.is_file():
            raise ExtractionError(f"missing runtime core file {block.filename}")
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            raise ExtractionError(f"runtime core file {block.filename} is empty")
        for needle in INLINE_FORBIDDEN_DEFS.get(block.block_id, ()):
            if needle in inline_js:
                raise ExtractionError(
                    f"inline index.html still defines {needle!r} — extraction incomplete for {block.block_id}"
                )

    anchor_idx = html.find(SCRIPT_INSERT_AFTER)
    if anchor_idx == -1:
        raise ExtractionError("zhl-worker-bridge.js script anchor missing from index.html head")
    head_slice = html[anchor_idx : anchor_idx + 1200]
    pos = 0
    for filename in EXPECTED_SCRIPT_ORDER:
        needle = f'<script src="{filename}"></script>'
        found = head_slice.find(needle, pos)
        if found == -1:
            raise ExtractionError(f"{filename} not found in head after worker bridge in expected order")
        pos = found + len(needle)


def extract(html: str | None = None) -> None:
    html = html if html is not None else INDEX.read_text(encoding="utf-8")

    if is_already_extracted(html):
        raise ExtractionError(
            "already extracted: HTML marker pairs and runtime script tags are present; "
            "refusing to mutate index.html again"
        )

    if not has_pending_inline_extraction(html):
        raise ExtractionError(
            "no inline LSP-EXTRACT-BEGIN markers found — nothing to extract"
        )

    js_blocks = _pair_js_blocks(html)
    all_ranges: list[tuple[int, int, str]] = []
    for block in UI_CORE_BLOCKS:
        if block.block_id not in js_blocks:
            raise ExtractionError(f"missing inline JS marker pair for {block.block_id!r}")
        entries = js_blocks[block.block_id]
        if len(entries) != 1:
            raise ExtractionError(f"duplicate inline JS marker pair for {block.block_id!r}")
        all_ranges.append(entries[0])
        body = entries[0][2]
        out_path = ROOT / block.filename
        out_path.write_text(block.header + "\n" + body.rstrip() + "\n", encoding="utf-8")
        print(f"wrote {block.filename} ({len(body.splitlines())} lines)")

    extra_js = set(js_blocks) - {b.block_id for b in UI_CORE_BLOCKS}
    if extra_js:
        raise ExtractionError(f"unexpected inline JS extraction markers: {sorted(extra_js)}")

    _assert_no_overlap(all_ranges, "inline JS blocks")

    order_positions = [entries[0][0] for block in UI_CORE_BLOCKS if (entries := js_blocks.get(block.block_id))]
    if order_positions != sorted(order_positions):
        raise ExtractionError("inline JS extraction blocks are not in expected file order")

    # Remove inline blocks from end to start (positions stable)
    for b0, b1, _ in sorted(all_ranges, key=lambda t: t[0], reverse=True):
        end_line = html.find("\n", b1)
        if end_line == -1:
            end_line = len(html)
        else:
            end_line += 1
        html = html[:b0] + html[end_line:]

    if SCRIPT_INSERT_AFTER not in html:
        raise ExtractionError("script insert anchor missing")

    insert_lines = [SCRIPT_INSERT_AFTER]
    for block in UI_CORE_BLOCKS:
        insert_lines.append(f"<!-- {MARKER_PREFIX}-BEGIN:{block.block_id} -->")
        insert_lines.append(f'<script src="{block.filename}"></script>')
        insert_lines.append(f"<!-- {MARKER_PREFIX}-END:{block.block_id} -->")
    insert = "\n".join(insert_lines)
    html = html.replace(SCRIPT_INSERT_AFTER, insert, 1)

    INDEX.write_text(html, encoding="utf-8")
    print(f"updated {INDEX.name}")
    verify_extracted_state(html)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--extract",
        action="store_true",
        help="Perform one-shot extraction from inline markers (fails if already extracted)",
    )
    args = parser.parse_args()
    try:
        if args.extract:
            extract()
        else:
            verify_extracted_state()
            print("UI core extraction layout verified.")
        return 0
    except ExtractionError as exc:
        print(f"extract_ui_cores: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
