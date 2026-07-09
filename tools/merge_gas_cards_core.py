#!/usr/bin/env python3
"""Extract deco/travel gas card UI from index.html into gas-cards-core.js."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
GAS_CARDS = ROOT / "gas-cards-core.js"
MARKUP_HEADER = ROOT / "ui" / "markup-header.html"

HEADER = '''/**
 * Deco / travel / bailout gas card UI — MOD displays, dynamic cards, travel gas.
 * Loaded by index.html before main inline script.
 * Globals read: units, altSurfaceP, BAR_PER_METRE, allowO2AtMOD, FN2_AIR, FN2_EAN32, FN2_EAN36,
 *   calcGasMODm, validateGasFractionsPct, getBottomGasFractions, getDecoCardFractions,
 *   getDomBottomGasPct, getDomDecoGasPct, getGasLabel, getBailoutPpo2Limit, isCcrGasUiMode,
 *   updateCcrGasValidation, toggleDecoCustomO2, toggleDecoTrimix, replanAfterEnvChange,
 *   shortMixLabel, CUFT_PER_LITRE
 * Globals written: _dgNextIdx, _travelGasFractionWarning
 */

let _travelGasFractionWarning = '';

'''

INDEX_RANGES = [(6808, 7305)]

SCRIPT_TAG = '''<!-- LSP-EXTRACT-BEGIN:gas-cards-core -->
<script src="gas-cards-core.js"></script>
<!-- LSP-EXTRACT-END:gas-cards-core -->
'''

INSERT_AFTER = "<!-- LSP-EXTRACT-END:gas-plan-core -->"


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
    if "LSP-EXTRACT-BEGIN:gas-cards-core" in html:
        return html
    if INSERT_AFTER not in html:
        raise SystemExit(f"anchor not found: {INSERT_AFTER}")
    return html.replace(INSERT_AFTER, INSERT_AFTER + "\n" + SCRIPT_TAG, 1)


def main() -> None:
    body = slice_lines(INDEX, INDEX_RANGES)
    # Drop duplicate global if still in extracted body from index
    body = body.replace("let _travelGasFractionWarning = '';\n", "", 1)
    GAS_CARDS.write_text(HEADER + body, encoding="utf-8")

    remove_ranges(INDEX, INDEX_RANGES)
    index_text = INDEX.read_text(encoding="utf-8")
    INDEX.write_text(insert_script_tag(index_text), encoding="utf-8")

    if MARKUP_HEADER.exists():
        mh = MARKUP_HEADER.read_text(encoding="utf-8")
        MARKUP_HEADER.write_text(insert_script_tag(mh), encoding="utf-8")

    print(f"Created {GAS_CARDS.name}: {len(GAS_CARDS.read_text(encoding='utf-8').splitlines())} lines")
    print(f"Removed from index.html: {INDEX_RANGES}")


if __name__ == "__main__":
    main()
