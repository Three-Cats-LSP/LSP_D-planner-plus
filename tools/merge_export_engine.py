#!/usr/bin/env python3
"""One-shot merge: consolidate copy/text/PDF export into export-core.js."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

INDEX = ROOT / "index.html"
EXPORT = ROOT / "export-core.js"
CONTINGENCY = ROOT / "contingency-core.js"
GAS_PLAN = ROOT / "gas-plan-core.js"

INDEX_RANGES = [(4086, 4561)]
CONTINGENCY_RANGES = [(563, 1144)]
GAS_PLAN_RANGES = [(547, 682)]

PLAN_HEADER_MARKER = "// LSP-EXPORT-ENGINE:PLAN-HEADER"
PDF_INFRA_MARKER = "// LSP-EXPORT-ENGINE:PDF-INFRA"
CONTINGENCY_PDF_MARKER = "// LSP-EXPORT-ENGINE:CONTINGENCY-PDF"
GAS_PLAN_PDF_MARKER = "// LSP-EXPORT-ENGINE:GAS-PLAN-PDF"

CLEAN_PDF_TEXT_FN = r'''
// ── Shared PDF text sanitization (single canonical copy) ──
function cleanPdfText(s) {
  if (!s) return '';
  s = String(s);
  s = s.replace(/[\u2080-\u2089]/g, c => String.fromCharCode(c.charCodeAt(0) - 0x2050));
  s = s.replace(/[\u00B2\u00B3\u00B9]/g, c => ({ '\u00B2': '2', '\u00B3': '3', '\u00B9': '1' }[c] || c));
  s = s.replace(/\u00B7|\u2022|\u2027/g, '*').replace(/\u2014/g, '--').replace(/\u2013/g, '-')
    .replace(/\u2018|\u2019/g, "'").replace(/\u201C|\u201D/g, '"');
  s = s.replace(/[\u2600-\u269F\u26A1-\u26FF\u2700-\u2712\u2714-\u2716\u2718-\u27FF\u2B00-\u2BFF\u2300-\u23FF\uFE0F]/g, '');
  s = s.replace(/[^\x20-\x7E\xA0-\u024F\u2190-\u2193\u2713\u2717\u26A0]/g, '');
  return s.replace(/^\s*[!&*#^~]+\s*/, '').trim();
}
'''.strip() + "\n"


def slice_lines(path: Path, ranges: list[tuple[int, int]]) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    out: list[str] = []
    for start, end in ranges:
        out.extend(lines[start - 1 : end])
    return out


def remove_ranges(path: Path, ranges: list[tuple[int, int]]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    drop = set()
    for start, end in ranges:
        for i in range(start - 1, end):
            drop.add(i)
    new_lines = [ln for i, ln in enumerate(lines) if i not in drop]
    path.write_text("".join(new_lines), encoding="utf-8")


def dedent_block(text: str) -> str:
    lines = text.splitlines(keepends=True)
    fixed = []
    for ln in lines:
        if ln.startswith("  function ") or (ln.startswith("  ") and ln.strip().startswith("function ")):
            fixed.append(ln[2:])
        else:
            fixed.append(ln)
    return "".join(fixed)


def strip_nested_clean_pdf(js: str) -> str:
    pattern = re.compile(
        r"\n  function cleanPDF\(s\)\{[\s\S]*?\n  \}\n",
        re.MULTILINE,
    )
    return pattern.sub("\n  const cleanPDF = cleanPdfText;\n", js)


def main() -> None:
    index_block = "".join(slice_lines(INDEX, INDEX_RANGES))
    contingency_block = dedent_block("".join(slice_lines(CONTINGENCY, CONTINGENCY_RANGES)))
    gas_plan_block = "".join(slice_lines(GAS_PLAN, GAS_PLAN_RANGES))

    export_text = EXPORT.read_text(encoding="utf-8")

    export_text = export_text.replace(
        " * Unified export / clipboard / PDF — RUNTIME UI CORE.",
        " * Unified export engine — copy, text export, clipboard, slate, and all PDF variants.",
    )
    export_text = export_text.replace(
        " *   waterDensityDisplayLabel, ensurePDFFontsForPDF, cleanPDF, drawDecoPlanBannerPDF, and DOM ids",
        " *   waterDensityDisplayLabel, getBottomGasFractions, drawDecoProfile, and DOM ids",
    )

    anchor = "  ].forEach((line) => lines.push(line));\n}\n\nfunction exportScheduleCell"
    if PLAN_HEADER_MARKER not in export_text:
        export_text = export_text.replace(
            anchor,
            "  ].forEach((line) => lines.push(line));\n}\n\n"
            + PLAN_HEADER_MARKER + "\n"
            + index_block
            + "\nfunction exportScheduleCell",
            1,
        )

    pdf_infra = (
        PDF_INFRA_MARKER + "\n"
        + CLEAN_PDF_TEXT_FN
        + "\n"
        + contingency_block.split("function showContingencyPDFDialog")[0]
    )
    contingency_pdf = (
        CONTINGENCY_PDF_MARKER + "\n"
        + "function showContingencyPDFDialog"
        + contingency_block.split("function showContingencyPDFDialog", 1)[1]
    )
    gas_plan_pdf = GAS_PLAN_PDF_MARKER + "\n" + gas_plan_block

    if PDF_INFRA_MARKER not in export_text:
        export_text = export_text.replace(
            "\nfunction showPDFExportDialog()",
            "\n" + pdf_infra + "\nfunction showPDFExportDialog()",
            1,
        )

    if CONTINGENCY_PDF_MARKER not in export_text:
        marker = "\n  doc.save(fileName);\n  showExportToast();\n}\n"
        idx = export_text.rfind(marker)
        if idx == -1:
            raise SystemExit("Could not find exportPDF end marker")
        insert_at = idx + len(marker)
        export_text = (
            export_text[:insert_at]
            + "\n" + contingency_pdf + "\n" + gas_plan_pdf + "\n"
            + export_text[insert_at:]
        )

    export_text = strip_nested_clean_pdf(export_text)

    EXPORT.write_text(export_text, encoding="utf-8")

    remove_ranges(INDEX, INDEX_RANGES)
    remove_ranges(CONTINGENCY, CONTINGENCY_RANGES)
    remove_ranges(GAS_PLAN, GAS_PLAN_RANGES)

    print("Merged export engine:")
    print(f"  {EXPORT.name}: {len(EXPORT.read_text(encoding='utf-8').splitlines())} lines")
    print(f"  removed from index.html: {INDEX_RANGES}")
    print(f"  removed from contingency-core.js: {CONTINGENCY_RANGES}")
    print(f"  removed from gas-plan-core.js: {GAS_PLAN_RANGES}")


if __name__ == "__main__":
    main()
