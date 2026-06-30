#!/usr/bin/env python3
"""Compatibility wrapper for the registry-driven audit orchestrator."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.audit.cli import main as audit_main

# Compatibility metadata retained while legacy_v1.py remains a blocking gate.
# Execution is delegated to the registry suite catalog, which is authoritative.
SUITES = {
    "engine_full": {"script": "dev/engine_regression.py"},
    "browser": {"script": "dev/run_browser_regression.py"},
    "ccr_differential": {"script": "dev/run_ccr_differential.py"},
    "engine_ccr_validation": {"script": "dev/ccr_engine_validation_regression.py"},
    "native_bridge": {"script": "dev/run_native_regression.py"},
}
BUILD_PAGES_SCRIPT = "tools/build_pages_site.py"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run LSP verification suites")
    parser.add_argument("--tier", choices=("ci", "release", "all"), default="ci")
    args = parser.parse_args()
    profile = "release" if args.tier == "all" else args.tier
    return audit_main(["run", "--profile", profile])


if __name__ == "__main__":
    raise SystemExit(main())
