#!/usr/bin/env python3
"""Extract planner-shell.js and results-panel.js from index.html inline script."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"

RESULTS_FUNCS = (
    "_clearResultSummaryStrip",
    "_splitMetricValUnit",
    "_parseChipNum",
    "renderMetricCards",
    "renderChipRow",
    "_renderResultSummaryStrip",
    "_onPlanResultsReady",
    "setMobilePlanView",
    "_initMobilePlanView",
    "_hideResultEmptyState",
    "_ppo2ClassV3",
    "_gasMixClassV3",
    "decorateDecoTableForV3",
    "_setGasWarningBanner",
    "_updateGasWarningBannerFromCard",
    "switchResultTab",
)

PLANNER_FUNCS = (
    "setNavMode",
    "initV3Layout",
)

RESULTS_CONSTS = ("_PHASE_ICON_SVG",)

HEADERS = {
    "results-panel.js": """/**
 * Results panel shell — metrics, chips, tabs, schedule table decoration.
 * Globals read: units, plannerAlgo, renderSurfIntPanel, updateSliderFill, calcSurfInt,
 *   calcAvgDepth, renderNDLTable, buildDiveBlocks
 * Globals written: (DOM only)
 */
""",
    "planner-shell.js": """/**
 * Planner / tools navigation shell and V4 layout bootstrap.
 * Globals read: plannerAlgo, setPlannerAlgo, toggleReference, syncEnvRowDisplay,
 *   initTools, setBrandIcon, appSettings, moveChildren (local in init)
 * Globals written: navMode, window._v3LayoutDone
 */
""",
}


def _extract_top_level_defs(script: str, names: tuple[str, ...]) -> list[str]:
    chunks: list[str] = []
    for name in names:
        if name.startswith("_") and name.isupper() or name == "_PHASE_ICON_SVG":
            pat = rf"(const {re.escape(name)}\s*=\s*\{{.*?\}};)"
            m = re.search(pat, script, re.DOTALL)
            if not m:
                raise SystemExit(f"const {name} not found")
            chunks.append(m.group(1))
            continue
        pat = rf"(function {re.escape(name)}\s*\([^)]*\)\s*\{{)"
        m = re.search(pat, script)
        if not m:
            raise SystemExit(f"function {name} not found")
        start = m.start()
        depth = 0
        i = m.end() - 1
        while i < len(script):
            ch = script[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    while end < len(script) and script[end] in " \t":
                        end += 1
                    if end < len(script) and script[end] == ";":
                        end += 1
                    chunks.append(script[start:end].rstrip())
                    break
            i += 1
        else:
            raise SystemExit(f"unclosed function {name}")
    return chunks


def _remove_chunks(script: str, chunks: list[str]) -> str:
    out = script
    for ch in sorted(chunks, key=len, reverse=True):
        if ch not in out:
            raise SystemExit("chunk missing during removal")
        out = out.replace(ch, "", 1)
    return re.sub(r"\n{3,}", "\n\n", out)


def main() -> int:
    html = INDEX.read_text(encoding="utf-8")
    marker = "// AUDIT-UNIT:UI-RUNTIME-BOOTSTRAP"
    m = re.search(r"<script(?![^>]*src)[^>]*>(.*?)</script>", html, re.DOTALL)
    # Find main inline script containing runtime bootstrap
    script = None
    for m in re.finditer(r"<script(?![^>]*src)[^>]*>(.*?)</script>", html, re.DOTALL):
        if marker in m.group(1):
            script = m.group(1)
            script_span = m.span(1)
            break
    if script is None:
        raise SystemExit("main inline script with UI-RUNTIME-BOOTSTRAP not found")

    results_chunks = _extract_top_level_defs(script, RESULTS_CONSTS + RESULTS_FUNCS)
    planner_chunks = _extract_top_level_defs(script, PLANNER_FUNCS)

    (ROOT / "results-panel.js").write_text(
        HEADERS["results-panel.js"] + "\n".join(results_chunks) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (ROOT / "planner-shell.js").write_text(
        HEADERS["planner-shell.js"] + "\n".join(planner_chunks) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote results-panel.js ({len(results_chunks)} defs)")
    print(f"wrote planner-shell.js ({len(planner_chunks)} defs)")

    new_script = _remove_chunks(script, results_chunks + planner_chunks)
    new_html = html[: script_span[0]] + new_script + html[script_span[1] :]

    insert_after = "<!-- LSP-EXTRACT-END:contingency-core -->"
    if "results-panel.js" in new_html:
        print("shell scripts already linked")
    else:
        block = (
            "\n<!-- LSP-EXTRACT-BEGIN:results-panel -->\n"
            '<script src="results-panel.js"></script>\n'
            "<!-- LSP-EXTRACT-END:results-panel -->\n"
            "<!-- LSP-EXTRACT-BEGIN:planner-shell -->\n"
            '<script src="planner-shell.js"></script>\n'
            "<!-- LSP-EXTRACT-END:planner-shell -->"
        )
        pos = new_html.find(insert_after)
        if pos < 0:
            raise SystemExit("contingency-core END marker missing")
        pos += len(insert_after)
        new_html = new_html[:pos] + block + new_html[pos:]

    INDEX.write_text(new_html, encoding="utf-8", newline="\n")
    print("updated index.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
