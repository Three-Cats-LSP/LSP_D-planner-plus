"""Build vpm-engine-bundle.js — Tier 3 VPM-B / VPM-B+GFS module (main thread).

Source of truth: vpm-engine-core.js (IIFE body). Re-extract from index.html with:
  python tools/build_vpm_bundle.py --extract
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE_PATH = ROOT / "vpm-engine-core.js"
BUNDLE_PATH = ROOT / "vpm-engine-bundle.js"
INDEX_PATH = ROOT / "index.html"

HEADER = """/**
 * VPM Engine Bundle — Tier 3 isolated VPM-B / VPM-B+GFS module.
 * Loaded on main thread; exposes window.VPMEngine for tests and runVPMSchedule().
 *
 * Host runtime deps (resolved at calculate() time, not load time):
 *   validateEngineInputs, validateCcrCalculationInputs, engineValidationError,
 *   isRebreatherCircuit, mergeCCRSettings, getEffectivePpo2, computePlanExposureTotals
 *   globals: altSurfaceP, BAR_PER_METRE (exposure fallbacks)
 */
"""

FOOTER = """
if (typeof module !== 'undefined') module.exports = VPMEngine;
if (typeof window !== 'undefined') window.VPMEngine = VPMEngine;
"""


def extract_core_from_index(html: str) -> str:
    start = html.find("const VPMEngine = (() => {")
    if start < 0:
        raise SystemExit("const VPMEngine = (() => { not found in index.html")
    body_start = html.find("{", start) + 1
    # Match closing `})();` before END VPM ENGINE comment
    end_marker = html.find("// ── END VPM ENGINE ──", body_start)
    if end_marker < 0:
        raise SystemExit("END VPM ENGINE marker not found")
    chunk = html[body_start:end_marker]
    # Trim back to closing `})();`
    close = chunk.rfind("})();")
    if close < 0:
        raise SystemExit("VPMEngine IIFE close not found")
    return chunk[:close].rstrip() + "\n"


CORE_HEADER = """/**
 * VPM engine core (Tier 3) — BUILD SOURCE ONLY.
 * Not loaded by index.html at runtime.
 * Rebuilt into vpm-engine-bundle.js via tools/build_vpm_bundle.py.
 */

"""


def ensure_core_header(core: str) -> str:
    if "BUILD SOURCE ONLY" in core[:500]:
        return core
    return CORE_HEADER + core.lstrip("\n")


def build_bundle(core: str) -> str:
    return HEADER + "const VPMEngine = (() => {\n" + core + "})();\n" + FOOTER


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--extract",
        action="store_true",
        help="Re-extract vpm-engine-core.js from index.html before building",
    )
    args = parser.parse_args()

    if args.extract or not CORE_PATH.is_file():
        if not INDEX_PATH.is_file():
            raise SystemExit(f"{INDEX_PATH} missing")
        html = INDEX_PATH.read_text(encoding="utf-8")
        core = extract_core_from_index(html)
        core = ensure_core_header(core)
        CORE_PATH.write_text(core, encoding="utf-8")
        print(f"Wrote {CORE_PATH.name}", len(core), "bytes")

    core = CORE_PATH.read_text(encoding="utf-8")
    core = ensure_core_header(core)
    # Bundle body is IIFE only — strip BUILD SOURCE header from runtime bundle
    body = core
    if body.startswith("/**"):
        end = body.find("*/")
        if end >= 0:
            body = body[end + 2 :].lstrip("\n")
    out = build_bundle(body)
    BUNDLE_PATH.write_text(out, encoding="utf-8")
    print(f"Wrote {BUNDLE_PATH.name}", len(out), "bytes")


if __name__ == "__main__":
    main()
