#!/usr/bin/env python3
"""CCR engine differential test runner — issue #2 implementation."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[1]
REPORT_JSON = ROOT / "dev" / "ccr_differential_report.json"
REPORT_MD = ROOT / "docs" / "CCR_DIFFERENTIAL_REPORT.md"


def render_markdown(summary: dict) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# CCR Engine Differential Report",
        "",
        f"**Generated:** {ts}  ",
        f"**LSP version:** {summary.get('appVersion', '?')}  ",
        f"**Scenarios:** {summary.get('scenarios', 0)}  ",
        f"**Failures:** {summary.get('failures', 0)}  ",
        f"**Inconclusive:** {summary.get('inconclusive', 0)}  ",
        "",
        "---",
        "",
    ]
    for row in summary.get("rows", []):
        lines.append(f"## {row.get('scenarioId')} — {row.get('description', '')}")
        lines.append("")
        if row.get("error"):
            lines.append(f"- **Integrity:** {row.get('integrity')} — {row['error']}")
        else:
            ls = (row.get("lsp") or {}).get("summary", {})
            lines.append(
                f"- **LSP:** RT {ls.get('runtimeMin')} min · first stop {ls.get('firstStopDepthM')} m · "
                f"TTS {ls.get('ttsMin')}"
            )
        for cmp in row.get("comparisons", []):
            cls = cmp.get("classification", "?")
            eng = cmp.get("engine", "?")
            detail = cmp.get("detail") or ""
            issues = cmp.get("issues") or []
            if issues:
                detail = "; ".join(
                    f"{i['field']} Δ{i['delta']}" for i in issues if isinstance(i, dict)
                )
            lines.append(f"- **{eng}:** `{cls}` {detail}")
        if row.get("metamorphic"):
            lines.append(f"- **Metamorphic:** {', '.join(row['metamorphic'])}")
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "See [CCR_ENGINE_DIFFERENTIAL_TEST_PLAN.md](CCR_ENGINE_DIFFERENTIAL_TEST_PLAN.md) for methodology."
    )
    defects = summary.get("documentedDefects") or []
    if defects:
        lines.extend(["", "## Documented LSP defects (tracked, not CI-blocking)", ""])
        for d in defects:
            lines.append(f"- **{d.get('defectId', '?')}** ({d.get('scenarioId', '?')}): {d.get('summary', '')}")
    return "\n".join(lines)


def main() -> int:
    from playwright.sync_api import sync_playwright

    sys.path.insert(0, str(ROOT / "dev"))
    from validate_pscr_e2e import serve_root  # noqa: E402

    # Ensure fixtures/goldens are current
    import subprocess

    build = ROOT / "tests" / "ccr-differential" / "build_assets.py"
    subprocess.run([sys.executable, str(build)], cwd=str(ROOT), check=True)

    url_path = "tests-ccr-differential.html"

    with serve_root(ROOT) as base_url:
        page_url = urljoin(base_url, url_path)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(300000)
            page.goto(page_url, wait_until="domcontentloaded", timeout=180000)
            summary = page.evaluate("""async () => {
              if (!window.runCCRDiffAll) throw new Error('runCCRDiffAll missing');
              return await window.runCCRDiffAll();
            }""")
            browser.close()

    REPORT_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    REPORT_MD.write_text(render_markdown(summary), encoding="utf-8")
    print(f"Wrote {REPORT_JSON}")
    print(f"Wrote {REPORT_MD}")
    print(
        f"Verdict: {'PASS' if summary.get('failures', 1) == 0 else 'FAIL'} "
        f"({summary.get('scenarios', 0)} scenarios, {summary.get('inconclusive', 0)} inconclusive, "
        f"{summary.get('missingRequired', 0)} missing required goldens)"
    )
    return 0 if summary.get("failures", 1) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
