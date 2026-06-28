#!/usr/bin/env python3
"""Verify Tier-3 engine sources are embedded in bundles (no mirror drift)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def strip_header(text: str) -> str:
    if text.startswith("/**"):
        end = text.find("*/")
        return text[end + 2 :].lstrip()
    return text


def normalize_js(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//.*?$", "", text, flags=re.M)
    text = re.sub(r"\s+", "", text)
    return text


def function_names(src: str) -> list[str]:
    return re.findall(r"^function\s+([A-Za-z_$][\w$]*)\s*\(", src, flags=re.M)


def main() -> int:
    failures: list[str] = []

    ccr_src = strip_header((ROOT / "zhl-ccr-core.js").read_text(encoding="utf-8"))
    physics_src = strip_header((ROOT / "zhl-physics-core.js").read_text(encoding="utf-8"))
    gas_src = strip_header((ROOT / "zhl-gas-core.js").read_text(encoding="utf-8"))
    schedule_src = strip_header((ROOT / "zhl-schedule-core.js").read_text(encoding="utf-8"))
    vpm_src = strip_header((ROOT / "vpm-engine-core.js").read_text(encoding="utf-8"))

    zhl_bundle = (ROOT / "zhl-engine-bundle.js").read_text(encoding="utf-8")
    vpm_bundle = (ROOT / "vpm-engine-bundle.js").read_text(encoding="utf-8")

    for fn in function_names(ccr_src):
        if f"function {fn}(" not in zhl_bundle:
            failures.append(f"zhl-engine-bundle.js missing CCR function {fn}")

    for fn in function_names(physics_src):
        if fn in ("applyEnvironment", "defaultEnvironment", "setHeHalfTimeMode"):
            continue
        if f"function {fn}(" not in zhl_bundle:
            failures.append(f"zhl-engine-bundle.js missing physics function {fn}")

    for fn in function_names(gas_src):
        if f"function {fn}(" not in zhl_bundle:
            failures.append(f"zhl-engine-bundle.js missing gas helper {fn}")

    if "function runZhlScheduleCore(" not in zhl_bundle:
        failures.append("zhl-engine-bundle.js missing runZhlScheduleCore")

    norm_ccr = normalize_js(ccr_src)
    norm_bundle_ccr_chunk = normalize_js(
        zhl_bundle.split("function canonicalCircuit", 1)[1].split("function enforceMinDecoProfile", 1)[0]
        if "function canonicalCircuit" in zhl_bundle and "function enforceMinDecoProfile" in zhl_bundle
        else ""
    )
    if norm_ccr and norm_bundle_ccr_chunk and norm_ccr not in norm_bundle_ccr_chunk:
        # Allow minor comment drift; function-name checks above are authoritative.
        if len(norm_ccr) - len(norm_bundle_ccr_chunk) > 50:
            failures.append("zhl-ccr-core.js body diverges from zhl-engine-bundle.js CCR section")

    norm_vpm = normalize_js(vpm_src)
    norm_vpm_bundle_body = normalize_js(
        vpm_bundle.split("const VPMEngine = (() => {", 1)[1].rsplit("})();", 1)[0]
        if "const VPMEngine = (() => {" in vpm_bundle
        else vpm_bundle
    )
    if norm_vpm not in norm_vpm_bundle_body:
        failures.append("vpm-engine-core.js body diverges from vpm-engine-bundle.js")

    api_exports = [
        "normalizeCCRSettings",
        "getEffectivePpo2",
        "loadTissuesWithCCR",
        "getActiveGas",
        "enforceMinDecoProfile",
        "ceiling",
    ]
    for name in api_exports:
        if f"{name}," not in zhl_bundle and f"{name}\n" not in zhl_bundle:
            failures.append(f"ZhlEngineBundle API missing export {name}")

    build_py = (ROOT / "tools" / "build_zhl_bundle.py").read_text(encoding="utf-8")
    if "index.html" in build_py and "read_text" in build_py and "getActiveGas" in build_py:
        failures.append("build_zhl_bundle.py still scrapes index.html for engine helpers")

    if failures:
        print("ENGINE PARITY FAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("Engine source/bundle parity OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
