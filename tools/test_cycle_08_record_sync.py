"""Cycle 8 record mirror must stay byte-identical across report and records paths."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CYCLE_8_REPORT = ROOT / "docs/seven-lens-reports/cycle-08-record.json"
CYCLE_8_RECORD = ROOT / "docs/seven-lens-records/cycle-08-shell-results.json"


class Cycle08RecordSyncTests(unittest.TestCase):
    def test_cycle_08_records_are_byte_identical(self):
        report_bytes = CYCLE_8_REPORT.read_bytes()
        record_bytes = CYCLE_8_RECORD.read_bytes()
        self.assertEqual(
            report_bytes,
            record_bytes,
            "cycle-08-record.json and cycle-08-shell-results.json diverged",
        )


if __name__ == "__main__":
    unittest.main()
