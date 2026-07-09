#!/usr/bin/env python3
"""Extract UI markup partials and assemble index.html at build time.

Partials live in ui/*.html keyed by AUDIT-UNIT:UI-MARKUP-* markers.
Committed index.html is the deploy artifact; run --assemble after editing partials.

Usage:
  python tools/assemble_ui_html.py --extract   # write ui/*.html from current index.html
  python tools/assemble_ui_html.py --assemble  # inject partials into index.html
  python tools/assemble_ui_html.py --verify    # partials match index.html sections
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
UI_DIR = ROOT / "ui"

REC_PLACEHOLDER = "__ASSEMBLE_REC_PLANNER__"
TEC_PLACEHOLDER = "__ASSEMBLE_TEC_PLANNER__"

MARKUP_UNITS: tuple[tuple[str, str], ...] = (
    ("UI-MARKUP-HEADER", "markup-header.html"),
    ("UI-MARKUP-CONSUMPTION", "markup-consumption.html"),
    ("UI-MARKUP-TOOLS", "markup-tools.html"),
    ("UI-MARKUP-MODALS", "markup-modals.html"),
)

# Standalone partials injected into header placeholders (verified by audit, not index markers).
EMBEDDED_PARTIALS: tuple[tuple[str, str], ...] = (
    ("UI-MARKUP-REC-PLANNER", "markup-rec-planner.html"),
    ("UI-MARKUP-TEC-PLANNER", "markup-tec-planner.html"),
)

MARKER_RE = re.compile(r"<!--\s*AUDIT-UNIT:(UI-MARKUP-[A-Z]+)\s*-->")


class AssembleError(Exception):
    pass


def _inject_planner_partials(header_html: str) -> str:
    rec = (UI_DIR / "markup-rec-planner.html").read_text(encoding="utf-8")
    tec = (UI_DIR / "markup-tec-planner.html").read_text(encoding="utf-8")
    if REC_PLACEHOLDER not in header_html:
        raise AssembleError(f"markup-header.html missing {REC_PLACEHOLDER}")
    if TEC_PLACEHOLDER not in header_html:
        raise AssembleError(f"markup-header.html missing {TEC_PLACEHOLDER}")
    return header_html.replace(REC_PLACEHOLDER, rec).replace(TEC_PLACEHOLDER, tec)


def _strip_legacy_planner_marker(html: str) -> str:
    legacy = re.compile(
        r"<!--\s*AUDIT-UNIT:UI-MARKUP-PLANNER\s*-->[\s\S]*?(?=<!--\s*AUDIT-UNIT:UI-MARKUP-CONSUMPTION\s*-->)"
    )
    return legacy.sub("", html)


def _find_sections(html: str) -> dict[str, tuple[int, int, str]]:
    hits = [(m.start(), m.end(), m.group(1)) for m in MARKER_RE.finditer(html)]
    if len(hits) != len(MARKUP_UNITS):
        raise AssembleError(f"expected {len(MARKUP_UNITS)} markup markers, found {len(hits)}")

    ordered_ids = [uid for uid, _ in MARKUP_UNITS]
    found_ids = [h[2] for h in hits]
    if found_ids != ordered_ids:
        raise AssembleError(f"marker order mismatch: {found_ids} != {ordered_ids}")

    sections: dict[str, tuple[int, int, str]] = {}
    for i, (start, marker_end, unit_id) in enumerate(hits):
        content_start = marker_end
        content_end = hits[i + 1][0] if i + 1 < len(hits) else html.find("<script>", marker_end)
        if content_end < 0:
            raise AssembleError("could not find end boundary for modals section")
        body = html[content_start:content_end]
        sections[unit_id] = (start, content_end, body)
    return sections


def extract_partials() -> None:
    html = INDEX.read_text(encoding="utf-8")
    sections = _find_sections(html)
    UI_DIR.mkdir(parents=True, exist_ok=True)
    for unit_id, filename in MARKUP_UNITS:
        _, _, body = sections[unit_id]
        if unit_id == "UI-MARKUP-HEADER":
            # Split injected rec/tec views back into placeholders for editable partials.
            rec_m = re.search(r'(<section[^>]*id="recPlannerView"[\s\S]*?</section>)', body)
            tec_m = re.search(r'(<section[^>]*id="tecPlannerView"[\s\S]*?</section>)', body)
            if rec_m and tec_m:
                body = body.replace(rec_m.group(1), REC_PLACEHOLDER)
                body = body.replace(tec_m.group(1), TEC_PLACEHOLDER)
        path = UI_DIR / filename
        path.write_text(body, encoding="utf-8", newline="\n")
        print(f"wrote ui/{filename} ({len(body.splitlines())} lines)")
    for unit_id, filename in EMBEDDED_PARTIALS:
        rec_m = re.search(r'(<section[^>]*id="recPlannerView"[\s\S]*?</section>)', html)
        tec_m = re.search(r'(<section[^>]*id="tecPlannerView"[\s\S]*?</section>)', html)
        if unit_id == "UI-MARKUP-REC-PLANNER" and rec_m:
            (UI_DIR / filename).write_text(rec_m.group(1), encoding="utf-8", newline="\n")
            print(f"wrote ui/{filename} ({len(rec_m.group(1).splitlines())} lines)")
        elif unit_id == "UI-MARKUP-TEC-PLANNER" and tec_m:
            (UI_DIR / filename).write_text(tec_m.group(1), encoding="utf-8", newline="\n")
            print(f"wrote ui/{filename} ({len(tec_m.group(1).splitlines())} lines)")


def assemble_index() -> None:
    html = _strip_legacy_planner_marker(INDEX.read_text(encoding="utf-8"))
    sections = _find_sections(html)
    out = []
    cursor = 0
    for unit_id, filename in MARKUP_UNITS:
        start, end, _old = sections[unit_id]
        partial = (UI_DIR / filename).read_text(encoding="utf-8")
        if unit_id == "UI-MARKUP-HEADER":
            partial = _inject_planner_partials(partial)
        marker = f"<!-- AUDIT-UNIT:{unit_id} -->"
        out.append(html[cursor:start])
        out.append(marker)
        out.append(partial)
        cursor = end
    out.append(html[cursor:])
    assembled = "".join(out)
    INDEX.write_text(assembled, encoding="utf-8", newline="\n")
    print("assembled index.html from ui/*.html partials")


def verify_partials() -> None:
    html = _strip_legacy_planner_marker(INDEX.read_text(encoding="utf-8"))
    sections = _find_sections(html)
    for unit_id, filename in MARKUP_UNITS:
        path = UI_DIR / filename
        if not path.is_file():
            raise AssembleError(f"missing partial ui/{filename}")
        _, _, live = sections[unit_id]
        disk = path.read_text(encoding="utf-8")
        if unit_id == "UI-MARKUP-HEADER":
            live_cmp = _inject_planner_partials(disk)
        else:
            live_cmp = disk
        if live != live_cmp:
            raise AssembleError(f"ui/{filename} out of sync with index.html — run --assemble")
    for unit_id, filename in EMBEDDED_PARTIALS:
        path = UI_DIR / filename
        if not path.is_file():
            raise AssembleError(f"missing partial ui/{filename}")
        disk = path.read_text(encoding="utf-8")
        if unit_id == "UI-MARKUP-REC-PLANNER":
            if 'id="recPlannerView"' not in html or disk.strip() not in html:
                raise AssembleError(f"ui/{filename} not found in assembled index.html — run --assemble")
        elif unit_id == "UI-MARKUP-TEC-PLANNER":
            if 'id="tecPlannerView"' not in html or disk.strip() not in html:
                raise AssembleError(f"ui/{filename} not found in assembled index.html — run --assemble")
    print("UI partial verify OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--extract", action="store_true")
    parser.add_argument("--assemble", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    try:
        if args.extract:
            extract_partials()
        elif args.assemble:
            assemble_index()
        else:
            verify_partials()
    except AssembleError as exc:
        print(f"assemble_ui_html: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
