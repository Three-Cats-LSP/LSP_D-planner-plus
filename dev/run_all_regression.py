#!/usr/bin/env python3
"""
Unified regression runner — orchestrates all LSP verification suites.

Usage:
  python dev/run_all_regression.py              # CI tier (audit + export + engine)
  python dev/run_all_regression.py --tier release  # + browser + pSCR + CCR diff
  python dev/run_all_regression.py --tier all      # everything including dev CCR validation

Exit 0 only if every selected suite passes.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE_VALIDATION_SCRIPT = ROOT / "engine_validation_regression.py"
CCR_VALIDATION_SCRIPT = ROOT / "dev" / "engine_validation_regression.py"

SUITES = {
    "audit": {
        "tiers": {"ci", "release", "all"},
        "cmd": [sys.executable, "audit.py"],
        "cwd": ROOT,
    },
    "export": {
        "tiers": {"ci", "release", "all"},
        "cmd": [sys.executable, "export_regression.py"],
        "cwd": ROOT,
    },
    "engine_validation": {
        "tiers": {"ci", "release", "all"},
        "cmd": [sys.executable, str(ENGINE_VALIDATION_SCRIPT)],
        "cwd": ROOT,
        "script": ENGINE_VALIDATION_SCRIPT,
    },
    "engine_full": {
        "tiers": {"ci", "release", "all"},
        "cmd": [sys.executable, "dev/engine_regression.py"],
        "cwd": ROOT,
    },
    "engine_ccr_validation": {
        "tiers": {"release", "all"},
        "cmd": [sys.executable, str(CCR_VALIDATION_SCRIPT)],
        "cwd": ROOT,
        "script": CCR_VALIDATION_SCRIPT,
    },
    "browser": {
        "tiers": {"release", "all"},
        "cmd": [sys.executable, "dev/run_browser_regression.py"],
        "cwd": ROOT,
    },
    "pscr_e2e": {
        "tiers": {"release", "all"},
        "cmd": [sys.executable, "dev/validate_pscr_e2e.py"],
        "cwd": ROOT,
        "env": {"SKIP_AUDIT": "1"},
    },
    "ccr_differential": {
        "tiers": {"release", "all"},
        "cmd": [sys.executable, "dev/run_ccr_differential.py"],
        "cwd": ROOT,
    },
}


def run_suite(name: str, spec: dict) -> dict:
    print(f"\n{'═' * 60}")
    print(f"  Suite: {name}")
    print(f"{'═' * 60}")
    script = spec.get("script")
    if script and not Path(script).is_file():
        print(f"  → SKIP (missing {script})")
        return {"name": name, "ok": False, "skipped": True, "reason": f"missing {script}"}
    env = {**os.environ, **spec.get("env", {})}
    proc = subprocess.run(
        spec["cmd"],
        cwd=str(spec["cwd"]),
        env=env,
        text=True,
        capture_output=True,
    )
    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
    if proc.stderr:
        print(proc.stderr, end="" if proc.stderr.endswith("\n") else "\n", file=sys.stderr)
    ok = proc.returncode == 0
    print(f"  → {'PASS' if ok else 'FAIL'} (exit {proc.returncode})")
    return {
        "name": name,
        "ok": ok,
        "exit_code": proc.returncode,
        "stdout": proc.stdout[-8000:] if proc.stdout else "",
        "stderr": proc.stderr[-8000:] if proc.stderr else "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run LSP regression suites")
    parser.add_argument(
        "--tier",
        choices=["ci", "release", "all"],
        default="ci",
        help="ci=PR checks; release=audit.yml gates; all=+dev CCR validation",
    )
    args = parser.parse_args()

    print("LSP D-Planner — unified regression")
    print(f"Tier: {args.tier}")

    results = []
    for name, spec in SUITES.items():
        if args.tier not in spec["tiers"]:
            continue
        results.append(run_suite(name, spec))

    out = ROOT / "dev" / "regression_summary.json"
    summary = {
        "tier": args.tier,
        "passed": sum(1 for r in results if r.get("ok")),
        "failed": sum(1 for r in results if not r.get("ok") and not r.get("skipped")),
        "skipped": sum(1 for r in results if r.get("skipped")),
        "suites": results,
    }
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")
    print(f"\n{'─' * 60}")
    ran = summary["passed"] + summary["failed"]
    print(f"  {summary['passed']}/{ran} suites passed", end="")
    if summary["skipped"]:
        print(f", {summary['skipped']} skipped", end="")
    print()
    print(f"{'─' * 60}\n")
    return 0 if summary["failed"] == 0 and summary["skipped"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
