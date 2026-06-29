#!/usr/bin/env python3
"""Summarize audit unit coverage from docs/audit-coverage.md and regression tests."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs" / "audit-coverage.md"
REGRESSION = ROOT / "dev" / "engine_regression.py"


def parse_ledger(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    in_table = False
    for line in text.splitlines():
        if line.startswith("| Unit ID |"):
            in_table = True
            continue
        if in_table:
            if not line.startswith("|"):
                in_table = False
                continue
            if line.startswith("|--------") or line.startswith("|------"):
                continue
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) >= 4 and parts[0] not in ("Unit ID", "Date"):
                rows.append(
                    {
                        "id": parts[0],
                        "file": parts[1] if len(parts) > 1 else "",
                        "symbol": parts[2] if len(parts) > 2 else "",
                        "status": parts[3] if len(parts) > 3 else "",
                        "regression": parts[5] if len(parts) > 5 else "",
                    }
                )
    return rows


def count_regression_tests(text: str) -> int:
    return len(re.findall(r"^\s+def test_", text, re.MULTILINE))


def main() -> int:
    if not LEDGER.is_file():
        print(f"Missing ledger: {LEDGER}", file=sys.stderr)
        return 1

    ledger_text = LEDGER.read_text(encoding="utf-8")
    rows = parse_ledger(ledger_text)
    if not rows:
        print("No unit rows parsed from ledger.", file=sys.stderr)
        return 1

    by_status: dict[str, int] = {}
    read_unverified: list[str] = []
    for row in rows:
        st = row["status"].upper()
        if "UNREAD" in st:
            key = "UNREAD"
        elif "VERIFIED" in st:
            key = "VERIFIED"
        elif "READ" in st:
            key = "READ"
        else:
            key = st or "OTHER"
        by_status[key] = by_status.get(key, 0) + 1
        if "READ" in st and "VERIFIED" not in st:
            read_unverified.append(row["id"])

    total = len(rows)
    read_count = by_status.get("READ", 0) + by_status.get("VERIFIED", 0)
    verified = by_status.get("VERIFIED", 0)
    pct_read = round(100 * read_count / total) if total else 0
    pct_verified = round(100 * verified / total) if total else 0

    reg_tests = 0
    if REGRESSION.is_file():
        reg_tests = count_regression_tests(REGRESSION.read_text(encoding="utf-8"))

    print("Audit coverage summary")
    print("======================")
    print(f"Ledger units:     {total}")
    print(f"READ (+partial):  {read_count} ({pct_read}%)")
    print(f"VERIFIED:         {verified} ({pct_verified}%)")
    print(f"UNREAD:           {by_status.get('UNREAD', 0)}")
    print(f"engine_regression test functions: {reg_tests}")
    if read_unverified:
        print(f"\nREAD-but-not-VERIFIED ({len(read_unverified)}): {', '.join(read_unverified[:20])}")
        if len(read_unverified) > 20:
            print(f"  … and {len(read_unverified) - 20} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
