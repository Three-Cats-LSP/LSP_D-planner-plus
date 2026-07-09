#!/usr/bin/env python3
"""Phase A: scope legacy mobile deco-table CSS and hoist result widgets into #resultsPanel."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"

HOIST_MAP = {
    "resultTab-profile": ["diveGraphCard", "decoResult"],
    "resultTab-contingency": ["contingencyCard"],
    "resultTab-tissue": ["tissueLoadCard"],
    "resultTab-gfcurve": ["gfCurveInlineCard"],
}

PROFILE_HEAD = (
    '<div class="results-section-head" id="profileSectionHead">'
    '<span class="results-section-label">Dive Profile</span></div>'
)


def extract_element_by_id(html: str, elem_id: str) -> tuple[str, str]:
    """Extract outer HTML of first element with given id. Returns (element_html, html_without)."""
    pattern = rf'(<[^>]+id="{re.escape(elem_id)}"[^>]*>)'
    m = re.search(pattern, html)
    if not m:
        raise SystemExit(f"Element #{elem_id} not found")
    start = m.start()
    tag = m.group(1)
    if tag.endswith("/>"):
        end = m.end()
        return html[start:end], html[:start] + html[end:]

    # depth count for nested divs
    depth = 0
    i = start
    while i < len(html):
        if html[i:i + 4] == "<div":
            depth += 1
        elif html[i:i + 6] == "</div>":
            depth -= 1
            if depth == 0:
                end = i + 6
                return html[start:end], html[:start] + html[end:]
        i += 1
    raise SystemExit(f"Unclosed element #{elem_id}")


def scope_legacy_mobile_css(css: str) -> str:
    """Prefix mobile card-table rules with .legacy-panels where appropriate."""
    start = css.find("/* ── MOBILE: card-style deco table ── */")
    end = css.find("/* ── LSP SLIDER ── */")
    if start < 0 or end < 0:
        raise SystemExit("Mobile deco-table block not found")
    block = css[start:end]
    lines = block.split("\n")
    out = []
    for line in lines:
        stripped = line.lstrip()
        if not stripped:
            out.append(line)
            continue
        # Keep global safety rows and gas-plan-table
        if any(
            x in stripped
            for x in (
                ".gas-bt-cell",
                ".gas-plan-table",
                "body.light-theme .gas-bt-cell",
                "body.light-theme .deco-table tr.gas-tight-row",
                ".deco-table tr.gas-tight-row",
                "#tableViewToggle",
            )
        ):
            out.append(line)
            continue
        if ".deco-table" in stripped and ".legacy-panels" not in stripped:
            indent = line[: len(line) - len(stripped)]
            out.append(indent + ".legacy-panels " + stripped)
        else:
            out.append(line)
    return css[:start] + "\n".join(out) + css[end:]


def hoist_results(html: str) -> str:
    extracted: dict[str, str] = {}
    for ids in HOIST_MAP.values():
        for eid in ids:
            if eid in extracted:
                continue
            el, html = extract_element_by_id(html, eid)
            extracted[eid] = el

    # gasConsumptionSummary -> resultsScratch after resultsPanel
    gas_el, html = extract_element_by_id(html, "gasConsumptionSummary")
    scratch = f'<div id="resultsScratch" hidden aria-hidden="true">\n{gas_el}\n</div>'

    for pane_id, id_list in HOIST_MAP.items():
        pane_pat = rf'(<div class="result-tab-pane[^"]*" id="{re.escape(pane_id)}"[^>]*>)'
        m = re.search(pane_pat, html)
        if not m:
            raise SystemExit(f"Pane #{pane_id} not found")
        insert_at = m.end()
        chunks = []
        if pane_id == "resultTab-profile":
            chunks.append(PROFILE_HEAD)
        chunks.extend(extracted[eid] for eid in id_list)
        html = html[:insert_at] + "\n" + "\n".join(chunks) + html[insert_at:]

    # Insert scratch after </section> closing resultsPanel
    rp_close = re.search(r'(</section>\s*\n</div>\s*\n<!-- TOOLS FULL PAGE -->)', html)
    if not rp_close:
        raise SystemExit("resultsPanel close anchor not found")
    html = html[: rp_close.start()] + scratch + "\n" + html[rp_close.start() :]

    # Update resultsPanel class
    html = html.replace(
        '<section class="v3-panel" id="resultsPanel"',
        '<section class="v3-panel results-panel mobile-active" id="resultsPanel"',
        1,
    )
    return html


def main() -> int:
    html = INDEX.read_text(encoding="utf-8")
    style_m = re.search(r"<style>(.*?)</style>", html, re.DOTALL)
    if not style_m:
        raise SystemExit("No <style> block")
    css = style_m.group(1)
    css = scope_legacy_mobile_css(css)
    html = html[: style_m.start(1)] + css + html[style_m.end(1) :]
    html = hoist_results(html)
    INDEX.write_text(html, encoding="utf-8", newline="\n")
    print("Phase A: scoped legacy mobile CSS + hoisted result widgets")
    return 0


if __name__ == "__main__":
    sys.exit(main())
