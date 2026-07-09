#!/usr/bin/env python3
"""Extract or verify UI CSS from index.html using AUDIT-UNIT markers.

Usage:
  python tools/extract_ui_css.py          # verify linked CSS matches markers
  python tools/extract_ui_css.py --extract  # write lsp-dplanner-*.css + replace inline <style>
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"

STYLE_BLOCK_RE = re.compile(r"<style>(.*?)</style>", re.DOTALL)

CSS_UNITS: tuple[tuple[str, str, str], ...] = (
    ("UI-CSS-FOUNDATION", "lsp-dplanner-foundation.css", "/* AUDIT-UNIT:UI-CSS-FOUNDATION */\n"),
    ("UI-CSS-MODES", "lsp-dplanner-modes.css", "/* AUDIT-UNIT:UI-CSS-MODES */\n"),
    ("UI-CSS-CONTROLS", "lsp-dplanner-controls.css", "/* AUDIT-UNIT:UI-CSS-CONTROLS */\n"),
    ("UI-CSS-RESULTS", "lsp-dplanner-results.css", "/* AUDIT-UNIT:UI-CSS-RESULTS */\n"),
)

LINK_TEMPLATE = """<!-- AUDIT-UNIT:UI-CSS-FOUNDATION -->
<link href="lsp-dplanner-foundation.css" rel="stylesheet"/>
<!-- AUDIT-UNIT:UI-CSS-MODES -->
<link href="lsp-dplanner-modes.css" rel="stylesheet"/>
<!-- AUDIT-UNIT:UI-CSS-CONTROLS -->
<link href="lsp-dplanner-controls.css" rel="stylesheet"/>
<!-- AUDIT-UNIT:UI-CSS-RESULTS -->
<link href="lsp-dplanner-results.css" rel="stylesheet"/>"""


class CssExtractionError(Exception):
    pass


def _split_css_sections(css: str) -> dict[str, str]:
    unit_ids = [uid for uid, _, _ in CSS_UNITS]
    inner_markers = [f"/* AUDIT-UNIT:{uid} */" for uid in unit_ids[1:]]

    positions: list[tuple[int, str]] = [(0, unit_ids[0])]
    for marker, uid in zip(inner_markers, unit_ids[1:], strict=True):
        idx = css.find(marker)
        if idx < 0:
            raise CssExtractionError(f"marker {marker!r} not found in <style>")
        positions.append((idx, uid))
    positions.sort(key=lambda t: t[0])

    sections: dict[str, str] = {}
    for i, (pos, unit_id) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(css)
        chunk = css[pos:end].strip()
        if unit_id != unit_ids[0]:
            chunk = chunk.split("\n", 1)[1] if "\n" in chunk else ""
        sections[unit_id] = chunk.strip() + "\n"
    return sections


def extract_css(html: str | None = None) -> None:
    html = html if html is not None else INDEX.read_text(encoding="utf-8")
    if "<style>" not in html:
        raise CssExtractionError("no inline <style> block — already extracted?")

    m = STYLE_BLOCK_RE.search(html)
    if not m:
        raise CssExtractionError("<style> block not found")
    css = m.group(1)
    sections = _split_css_sections(css)

    for unit_id, filename, header in CSS_UNITS:
        body = sections[unit_id]
        (ROOT / filename).write_text(header + body, encoding="utf-8", newline="\n")
        print(f"wrote {filename} ({len(body.splitlines())} lines)")

    foundation_comment = "<!-- AUDIT-UNIT:UI-CSS-FOUNDATION -->"
    fidx = html.find(foundation_comment)
    if fidx < 0:
        raise CssExtractionError("UI-CSS-FOUNDATION HTML comment missing")
    style_start = html.find("<style>", fidx)
    style_end = html.find("</style>", style_start) + len("</style>")
    new_html = html[:fidx] + LINK_TEMPLATE + "\n" + html[style_end:]
    INDEX.write_text(new_html, encoding="utf-8", newline="\n")
    print("replaced inline <style> with linked CSS in index.html")


def verify_css(html: str | None = None) -> None:
    html = html if html is not None else INDEX.read_text(encoding="utf-8")
    if "<style>" in html and 'href="lsp-dplanner-foundation.css"' in html:
        raise CssExtractionError("index.html has both inline <style> and linked CSS")
    if "<style>" in html:
        raise CssExtractionError("inline <style> still present — run --extract")

    for unit_id, filename, header in CSS_UNITS:
        path = ROOT / filename
        if not path.is_file():
            raise CssExtractionError(f"missing {filename}")
        text = path.read_text(encoding="utf-8")
        if f"AUDIT-UNIT:{unit_id}" not in text:
            raise CssExtractionError(f"{filename} missing AUDIT-UNIT:{unit_id}")
        if f'href="{filename}"' not in html:
            raise CssExtractionError(f"index.html missing link to {filename}")

    order = [f for _, f, _ in CSS_UNITS]
    last = -1
    for fn in order:
        pos = html.find(f'href="{fn}"')
        if pos < 0:
            raise CssExtractionError(f"link {fn} not found")
        if pos < last:
            raise CssExtractionError("CSS link order incorrect")
        last = pos
    print("CSS extraction verify OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--extract", action="store_true")
    args = parser.parse_args()
    try:
        if args.extract:
            extract_css()
        else:
            verify_css()
    except CssExtractionError as exc:
        print(f"extract_ui_css: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
