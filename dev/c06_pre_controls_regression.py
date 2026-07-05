#!/usr/bin/env python3
"""Run Cycle 06 controls regression against audit-commit CSS, then restore canonical CSS."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "lsp-dplanner-controls.css"
BACKUP = ROOT / "dev" / ".c06-pre-css-backup.css"


def main() -> int:
    if CSS.exists():
        BACKUP.write_bytes(CSS.read_bytes())
    audit = subprocess.run(
        ["git", "show", "fea770d:lsp-dplanner-controls.css"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if audit.returncode != 0:
        print(audit.stderr.decode("utf-8", errors="replace"), file=sys.stderr)
        return audit.returncode
    CSS.write_bytes(audit.stdout)
    try:
        result = subprocess.run(
            [sys.executable, "dev/ui_controls_css_regression.py"],
            cwd=ROOT,
            check=False,
        )
        code = result.returncode
    finally:
        if BACKUP.exists():
            CSS.write_bytes(BACKUP.read_bytes())
            BACKUP.unlink(missing_ok=True)
        subprocess.run(
            [sys.executable, "tools/sync_www.py"],
            cwd=ROOT,
            check=False,
        )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
