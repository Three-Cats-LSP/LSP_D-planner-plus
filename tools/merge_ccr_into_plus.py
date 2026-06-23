#!/usr/bin/env python3
"""Merge CCR index.html into LSP D-Planner+ with OC Tier-3 ZHL additions."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CCR_ROOT = ROOT.parent / "LSP_D-planner-CCR"
OC_ROOT = ROOT.parent / "LSP_D-planner"

CCR_INDEX = CCR_ROOT / "index.html"
OC_INDEX = OC_ROOT / "index.html"
PLUS_INDEX = ROOT / "index.html"
CCR_AUDIT = CCR_ROOT / "audit.py"
OC_AUDIT = OC_ROOT / "audit.py"
PLUS_AUDIT = ROOT / "audit.py"

TIER3_START = "// ═══════════════════════════════════════════════\n// ZHL SCHEDULE CORE — Tier 3"
TIER3_END = "if (typeof window !== 'undefined') window.runZhlScheduleCore = runZhlScheduleCore;\n\nfunction runDecoSchedule()"

ZHL_ENGINE_START = (
    "// ═══════════════════════════════════════════════\n"
    "// ZHL ENGINE — headless Bühlmann interface for test harnesses"
)
ZHL_ENGINE_END = "if (typeof window !== 'undefined') window.ZHLEngine = ZHLEngine; // expose for test harnesses"

SPLIT_OLD = """/** Deepest level + monotonic-shallower continuation (matches VPMEngine profile split). */
function splitZhlProfileLevels(levels) {
  if (!levels || levels.length <= 1) return { primary: levels || [], continuation: [] };
  let deepest = 0;
  for (let i = 1; i < levels.length; i++) {
    if (levels[i].depth > levels[deepest].depth) deepest = i;
  }
  let continuation = [];
  let primary = levels;
  if (deepest < levels.length - 1) {
    let monotonic = true;
    for (let i = deepest + 1; i < levels.length; i++) {
      if (levels[i].depth > levels[i - 1].depth) { monotonic = false; break; }
    }
    if (monotonic) {
      continuation = levels.slice(deepest + 1);
      primary = levels.slice(0, deepest + 1);
    }
  }
  return { primary, continuation };
}"""

SPLIT_NEW = """/** Deepest level + monotonic-shallower continuation (matches VPMEngine profile split). */
function splitZhlProfileLevels(levels) {
  return ZhlEngineBundle.splitZhlProfileLevels(levels);
}"""


def extract_between(text: str, start: str, end: str, label: str) -> str:
    s = text.find(start)
    e = text.find(end, s)
    if s < 0 or e < 0:
        raise SystemExit(f"{label}: markers not found (start={s}, end={e})")
    return text[s:e]


def build_hybrid_zhl_engine(ccr_calculate_body: str) -> str:
    """OC Tier-3 ZHLEngine with CCR DOM delegate for rebreather circuits."""
    # ccr_calculate_body is the inner function from CCR's calculate(levels,...)
    return f"""{ZHL_ENGINE_START}
// Tier 3: ZhlEngineBundle (sync OC) + ZhlWorkerBridge (async OC)
// CCR/pSCR: DOM-based path via runDecoSchedule (full CCR loop physics)
// Mirrors VPMEngine.calculate(levels, gases, settings, 'ZHLC_GF').
// ═══════════════════════════════════════════════
const ZHLEngine = (() => {{
  function setEl(id, val) {{
    const el = document.getElementById(id);
    if (el) el.value = val;
  }}

  function calculateCcrViaDom(levels, decoGases, settings) {{
{ccr_calculate_body}
  }}

  function isCcrCircuit(settings) {{
    const s = settings || {{}};
    const circuit = s.circuit || 'OC';
    return typeof isRebreatherCircuit === 'function' && isRebreatherCircuit(circuit);
  }}

  function calculate(levels, decoGases, settings) {{
    const s = settings || {{}};
    const ccrVal = validateCcrCalculationInputs(levels, s, decoGases);
    if (!ccrVal.ok) return engineValidationError(ccrVal);
    if (isCcrCircuit(s)) {{
      return calculateCcrViaDom(levels, decoGases, settings);
    }}
    const validation = validateEngineInputs(levels, decoGases);
    if (!validation.ok) return engineValidationError(validation);
    const profileVal = validateZhlHeadlessProfile(levels);
    if (!profileVal.ok) {{
      return engineValidationError({{ ok: false, errors: [profileVal] }});
    }}
    const profileSplit = ZhlEngineBundle.splitZhlProfileLevels(levels);
    return ZhlEngineBundle.calculate(levels, decoGases, s, profileSplit, getZhlEnvironment());
  }}

  async function calculateInWorker(levels, decoGases, settings) {{
    const s = settings || {{}};
    const ccrVal = validateCcrCalculationInputs(levels, s, decoGases);
    if (!ccrVal.ok) return engineValidationError(ccrVal);
    if (isCcrCircuit(s)) {{
      return calculateCcrViaDom(levels, decoGases, settings);
    }}
    const validation = validateEngineInputs(levels, decoGases);
    if (!validation.ok) return engineValidationError(validation);
    const profileVal = validateZhlHeadlessProfile(levels);
    if (!profileVal.ok) {{
      return engineValidationError({{ ok: false, errors: [profileVal] }});
    }}
    const profileSplit = ZhlEngineBundle.splitZhlProfileLevels(levels);
    try {{
      return await ZhlWorkerBridge.calculateInWorker(
        levels, decoGases, s, profileSplit, getZhlEnvironment()
      );
    }} catch (e) {{
      return {{ error: e.message, stops: [], plan: [], totalRuntime: 0 }};
    }}
  }}

  return {{ calculate, calculateInWorker, MODEL: 'ZHLC_GF' }};
}})();

"""


def merge_index() -> None:
    ccr = CCR_INDEX.read_text(encoding="utf-8")
    oc = OC_INDEX.read_text(encoding="utf-8")

    # Tier 3 helpers from OC (between tier3 markers, before runDecoSchedule)
    tier3_block = extract_between(oc, TIER3_START, TIER3_END, "Tier3 block")
    tier3_block = tier3_block.rstrip() + "\n\n"

    # CCR calculate() body for DOM path
    zhl_block = extract_between(ccr, ZHL_ENGINE_START, ZHL_ENGINE_END, "ZHLEngine")
    m = re.search(
        r"function calculate\(levels, decoGases, settings\) \{\n(.*?)\n  \}\n\n  return \{ calculate",
        zhl_block,
        re.DOTALL,
    )
    if not m:
        raise SystemExit("Could not extract CCR calculate() body")
    ccr_body = m.group(1)
    # Re-indent body for nested function (add 2 spaces)
    ccr_body = "\n".join("  " + line if line else line for line in ccr_body.split("\n"))

    html = ccr

    # ── Head: rebrand meta ──
    html = html.replace(
        "<title>LSP D-Planner + CCR · Rec &amp; Tec</title>",
        "<title>LSP D-Planner+ · Rec &amp; Tec</title>",
    )
    html = html.replace(
        '<meta content="D-Planner+CCR" name="apple-mobile-web-app-title"/>',
        '<meta content="LSP+" name="apple-mobile-web-app-title"/>',
    )
    html = html.replace(
        '<meta content="Professional CCR/pSCR dive planner with Bühlmann ZH-L16C decompression, setpoint scheduling, and OC bailout gas management." name="description"/>',
        '<meta content="Unified open-circuit and CCR/pSCR dive planner — Bühlmann ZHL-16C + VPM-B decompression, setpoint scheduling, and bailout gas management." name="description"/>',
    )

    # ── Fonts: self-hosted ──
    html = re.sub(
        r'<link href="https://fonts\.googleapis\.com[^"]*" rel="stylesheet"/>',
        '<link href="vendor/fonts/fonts.css" rel="stylesheet"/>',
        html,
        count=1,
    )

    # ── jsPDF vendored + Tier-3 scripts ──
    html = re.sub(
        r'<script src="https://cdnjs\.cloudflare\.com/ajax/libs/jspdf[^"]*"></script>\s*'
        r'(?:<!-- Capacitor[^>]*-->\s*)?'
        r'<script src="capacitor-bridge\.js"></script>',
        """<!-- jsPDF: vendored locally — defer so app startup is not blocked on CDN -->
<script src="capacitor-bridge.js"></script>
<script src="zhl-engine-bundle.js"></script>
<script src="zhl-worker-bridge.js"></script>
<script defer src="vendor/jspdf.umd.min.js"></script>""",
        html,
        count=1,
    )
    if "zhl-engine-bundle.js" not in html:
        html = html.replace(
            '<script src="capacitor-bridge.js"></script>',
            '<script src="capacitor-bridge.js"></script>\n'
            '<script src="zhl-engine-bundle.js"></script>\n'
            '<script src="zhl-worker-bridge.js"></script>',
            1,
        )

    # ── Insert Tier 3 param builders before runDecoSchedule ──
    run_deco_marker = "function runDecoSchedule() {"
    if "function buildZhlScheduleParamsFromDom" not in html:
        idx = html.find(run_deco_marker)
        if idx < 0:
            raise SystemExit("runDecoSchedule not found")
        html = html[:idx] + tier3_block + html[idx:]

    # ── splitZhlProfileLevels → bundle wrapper ──
    if SPLIT_OLD in html:
        html = html.replace(SPLIT_OLD, SPLIT_NEW, 1)

    # ── Hybrid ZHLEngine ──
    zs = html.find(ZHL_ENGINE_START)
    ze = html.find(ZHL_ENGINE_END)
    if zs < 0 or ze < 0:
        raise SystemExit(f"ZHLEngine block not found: {zs} {ze}")
    html = html[:zs] + build_hybrid_zhl_engine(ccr_body) + ZHL_ENGINE_END + html[ze + len(ZHL_ENGINE_END) :]

    # ── APP_VERSION ──
    html = re.sub(
        r"const APP_VERSION = '[^']+';",
        "const APP_VERSION = '2.50.00';",
        html,
        count=1,
    )

    # ── Reference panel & links: plus branding, remove CCR-only cross-links ──
    html = html.replace(
        "https://github.com/Three-Cats-LSP/LSP_D-planner-CCR",
        "https://github.com/Three-Cats-LSP/LSP_D-planner-plus",
    )
    html = html.replace(
        "LSP D-Planner + CCR · Open Source on GitHub",
        "LSP D-Planner+ · Open Source on GitHub",
    )
    html = html.replace(
        "GitHub · Three-Cats-LSP/LSP_D-planner-CCR",
        "GitHub · Three-Cats-LSP/LSP_D-planner-plus",
    )
    html = html.replace(
        "https://threecats-lsp.com/d-planner-ccr/download.html",
        "https://threecats-lsp.com/d-planner-plus/download.html",
    )
    html = html.replace(
        "LSP D-Planner + CCR · Download Android APK",
        "LSP D-Planner+ · Download Android APK",
    )
    html = html.replace(
        'title="Download LSP D-Planner + CCR APK"',
        'title="Download LSP D-Planner+ APK"',
    )
    html = html.replace(
        'alt="LSP D-Planner + CCR"',
        'alt="LSP D-Planner+"',
    )

    # GIW icon: self-hosted
    html = html.replace(
        'src="https://threecats-lsp.com/get-in-water/icon-192.png"',
        'src="vendor/icons/giw-icon-192.png"',
    )

    # Export footers
    html = html.replace(
        "L.push('LSP D-Planner + CCR — threecats-lsp.com/d-planner-ccr');",
        "L.push('LSP D-Planner+ — threecats-lsp.com/d-planner-plus');",
    )
    html = html.replace(
        "lines.push('https://threecats-lsp.com/d-planner-ccr/');",
        "lines.push('https://threecats-lsp.com/d-planner-plus/');",
    )

    # Docs / disclaimer / PWA install strings
    html = html.replace("LSP D-Planner + CCR", "LSP D-Planner+")

    PLUS_INDEX.write_text(html, encoding="utf-8")
    print(f"Wrote merged index.html ({len(html):,} bytes)")


def merge_audit() -> None:
    ccr_audit = CCR_AUDIT.read_text(encoding="utf-8")
    oc_audit = OC_AUDIT.read_text(encoding="utf-8")

    # Start from CCR (more complete for CCR checks)
    audit = ccr_audit

    # Insert Tier-3 bundle merge block from OC if missing
    bundle_block = """# Tier 3: Bühlmann core lives in zhl-engine-bundle.js — merge for ZHL pattern checks
bundle_path = os.path.join(os.path.dirname(path) if os.path.dirname(path) else ".", "zhl-engine-bundle.js")
if not os.path.isabs(bundle_path):
    bundle_path = os.path.join(os.path.dirname(os.path.abspath(path)), "zhl-engine-bundle.js")
zhl_bundle_js = ""
if os.path.isfile(bundle_path):
    with open(bundle_path, encoding="utf-8") as f:
        zhl_bundle_js = f.read()
zhl_src = js + "\\n" + zhl_bundle_js

"""
    if "zhl_bundle_js" not in audit:
        audit = audit.replace(
            "js_lines = js.split(\"\\n\")\n\n# Helper: line number in JS block",
            "js_lines = js.split(\"\\n\")\n\n" + bundle_block + "# Helper: line number in JS block",
        )

    # Use zhl_src for phaseNextStop check (OC parity)
    audit = audit.replace(
        '"phaseNextStop" in js',
        '"phaseNextStop" in zhl_src',
    )

    # Append OC-only offline / Tier-3 groups not in CCR
    oc_plus_marker = "# GROUP 41 (OC) — Design sync with CCR shared layer"
    oc_end_marker = "# GROUP 62 (OC) — ZHL multi-level headless"
    oc_start = oc_audit.find(oc_plus_marker)
    oc_group62 = oc_audit.find(oc_end_marker)
    if oc_start >= 0 and oc_group62 >= 0:
        # Take GROUP 41 OC through end of GROUP 62 OC (before print)
        oc_tail_start = oc_audit.find("\nprint(f\"\\nLSP D-Planner Audit", oc_group62)
        oc_extra = oc_audit[oc_start:oc_tail_start].rstrip() + "\n\n"
        if oc_plus_marker not in audit:
            audit = audit.replace(
                "\nprint(f\"\\nLSP D-Planner Audit",
                "\n" + oc_extra + "print(f\"\\nLSP D-Planner+ Audit",
                1,
            )
        else:
            audit = audit.replace(
                "print(f\"\\nLSP D-Planner Audit",
                "print(f\"\\nLSP D-Planner+ Audit",
                1,
            )
    else:
        audit = audit.replace(
            "print(f\"\\nLSP D-Planner Audit",
            "print(f\"\\nLSP D-Planner+ Audit",
        )

    # Version alignment for plus
    audit = re.sub(
        r"APP_VERSION = '2\.\d+\.\d+'",
        "APP_VERSION = '2.50.00'",
        audit,
    )
    audit = audit.replace("lsp-dplanner-v2.", "lsp-dplanner-plus-v2.")
    audit = audit.replace('"name": "lsp-d-planner"', '"name": "lsp-d-planner-plus"')
    audit = audit.replace("LSP D-Planner + CCR", "LSP D-Planner+")
    audit = audit.replace("dplannerccr", "dplannerplus")
    audit = audit.replace("sync-apk-d-planner-ccr", "sync-apk-d-planner-plus")
    audit = audit.replace("sync-apk-d-planner-plus-ccr", "sync-apk-d-planner-plus")

    PLUS_AUDIT.write_text(audit, encoding="utf-8")
    print("Wrote merged audit.py")


def update_config_files() -> None:
    import json

    pkg_path = ROOT / "package.json"
    pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
    pkg["name"] = "lsp-d-planner-plus"
    pkg["version"] = "2.50.00"
    pkg["description"] = "LSP D-Planner+ — unified OC + CCR decompression planning app"
    pkg_path.write_text(json.dumps(pkg, indent=2) + "\n", encoding="utf-8")

    for mf in (ROOT / "manifest.json", ROOT / "www" / "manifest.json"):
        if mf.is_file():
            m = json.loads(mf.read_text(encoding="utf-8"))
            m["name"] = "LSP D-Planner+"
            m["short_name"] = "LSP+"
            m["description"] = (
                "Unified open-circuit and CCR/pSCR planner — Bühlmann ZHL-16C + VPM-B decompression"
            )
            mf.write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")

    for sw in (ROOT / "sw.js", ROOT / "www" / "sw.js"):
        if sw.is_file():
            text = sw.read_text(encoding="utf-8")
            text = re.sub(
                r"const CACHE_VERSION = '[^']+';",
                "const CACHE_VERSION = 'lsp-dplanner-plus-v2.50.00';",
                text,
                count=1,
            )
            if "d-planner-plus" not in text:
                text = text.replace(
                    "if (p.includes('/d-planner')) return '/d-planner/';",
                    "if (p.includes('/d-planner-plus')) return '/d-planner-plus/';\n"
                    "  if (p.includes('/d-planner')) return '/d-planner/';",
                )
            sw.write_text(text, encoding="utf-8")

    cap = ROOT / "capacitor.config.json"
    if cap.is_file():
        c = json.loads(cap.read_text(encoding="utf-8"))
        c["appId"] = "com.threecats.lsp.dplannerplus"
        c["appName"] = "LSP+"
        cap.write_text(json.dumps(c, indent=2) + "\n", encoding="utf-8")


def update_changelog() -> None:
    cl = ROOT / "CHANGELOG.md"
    entry = """## v2.50.00 — 2026-06-24

### Release — LSP D-Planner+ unified OC + CCR

- **Merge** — CCR edition (circuit select, setpoints, pSCR, diluent/bailout gas cards, CCR-aware VPM/ZHL) combined with OC Tier-3 ZHL engine (`zhl-engine-bundle.js` + Web Worker bridge).
- **ZHLEngine** — OC open-circuit headless path uses `ZhlEngineBundle.calculate` / `calculateInWorker`; CCR/pSCR delegates to DOM-based `runDecoSchedule` with full loop physics.
- **Offline shell** — Self-hosted fonts, vendored jsPDF, local Get In Water icon (from OC 2.40).
- **Branding** — `LSP D-Planner+`, app id `com.threecats.lsp.dplannerplus`, site `threecats-lsp.com/d-planner-plus`.

- **`APP_VERSION`** — bumped to `2.50.00`.

---

"""
    text = cl.read_text(encoding="utf-8")
    if "v2.50.00" not in text:
        text = text.replace(
            "# Changelog\n\nAll notable changes to LSP D-Planner are documented here.\n\n---\n\n",
            "# Changelog\n\nAll notable changes to LSP D-Planner+ are documented here.\n\n---\n\n" + entry,
        )
        cl.write_text(text, encoding="utf-8")


def update_readme() -> None:
    rd = ROOT / "README.md"
    text = rd.read_text(encoding="utf-8")
    text = text.replace("# LSP D-Planner\n", "# LSP D-Planner+\n")
    text = text.replace(
        "https://threecats-lsp.com/d-planner/",
        "https://threecats-lsp.com/d-planner-plus/",
    )
    text = text.replace(
        "https://threecats-lsp.com/d-planner/download.html",
        "https://threecats-lsp.com/d-planner-plus/download.html",
    )
    text = text.replace("**Current version: 2.40.02**", "**Current version: 2.50.00**")
    text = re.sub(
        r">\s*\*\*Looking for rebreather planning\?\*\*[^>]+>\n\n---\n\n",
        "---\n\n",
        text,
        count=1,
    )
    text = text.replace(
        "| **LSP D-Planner** ← *this app* | Open-circuit decompression planning — Bühlmann, VPM-B, Rec/Tec | [Repo](https://github.com/Three-Cats-LSP/LSP_D-planner) |",
        "| **LSP D-Planner+** ← *this app* | Unified OC + CCR/pSCR decompression planning — Bühlmann, VPM-B, Rec/Tec | [Repo](https://github.com/Three-Cats-LSP/LSP_D-planner-plus) |",
    )
    text = text.replace(
        "| **[LSP D-Planner + CCR](https://threecats-lsp.com/d-planner-ccr/)** | Rebreather planning — CCR, pSCR, bailout | [Repo](https://github.com/Three-Cats-LSP/LSP_D-planner-CCR) |\n",
        "",
    )
    if "CCR" not in text.split("## Algorithms")[0]:
        pass  # CCR features documented below
    if "### Technical Mode" in text and "CCR / pSCR" not in text:
        text = text.replace(
            "### Technical Mode\n",
            "### Technical Mode\n"
            "- **CCR / pSCR** — circuit select, setpoint scheduling, diluent & bailout gases, on-loop Bühlmann + VPM\n",
        )
    rd.write_text(text, encoding="utf-8")


def main() -> None:
    if not CCR_INDEX.is_file():
        raise SystemExit(f"CCR index not found: {CCR_INDEX}")
    merge_index()
    merge_audit()
    update_config_files()
    update_changelog()
    update_readme()
    print("Merge complete.")


if __name__ == "__main__":
    main()
