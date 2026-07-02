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

MARKUP_UNITS: tuple[tuple[str, str], ...] = (
    ("UI-MARKUP-HEADER", "markup-header.html"),
    ("UI-MARKUP-PLANNER", "markup-planner.html"),
    ("UI-MARKUP-CONSUMPTION", "markup-consumption.html"),
    ("UI-MARKUP-TOOLS", "markup-tools.html"),
    ("UI-MARKUP-MODALS", "markup-modals.html"),
)

MARKER_RE = re.compile(r"<!--\s*AUDIT-UNIT:(UI-MARKUP-[A-Z]+)\s*-->")


class AssembleError(Exception):
    pass


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
        path = UI_DIR / filename
        path.write_text(body, encoding="utf-8", newline="\n")
        print(f"wrote ui/{filename} ({len(body.splitlines())} lines)")


def assemble_index() -> None:
    html = INDEX.read_text(encoding="utf-8")
    sections = _find_sections(html)
    out = []
    cursor = 0
    for unit_id, filename in MARKUP_UNITS:
        start, end, _old = sections[unit_id]
        partial = (UI_DIR / filename).read_text(encoding="utf-8")
        marker = f"<!-- AUDIT-UNIT:{unit_id} -->"
        out.append(html[cursor:start])
        out.append(marker)
        out.append(partial)
        cursor = end
    out.append(html[cursor:])
    INDEX.write_text("".join(out), encoding="utf-8", newline="\n")
    print("assembled index.html from ui/*.html partials")


def verify_partials() -> None:
    html = INDEX.read_text(encoding="utf-8")
    sections = _find_sections(html)
    for unit_id, filename in MARKUP_UNITS:
        path = UI_DIR / filename
        if not path.is_file():
            raise AssembleError(f"missing partial ui/{filename}")
        _, _, live = sections[unit_id]
        disk = path.read_text(encoding="utf-8")
        if live != disk:
            raise AssembleError(f"ui/{filename} out of sync with index.html — run --assemble")
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
