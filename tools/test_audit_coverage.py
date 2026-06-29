#!/usr/bin/env python3
"""Failure-mode tests for tools/audit_coverage.py."""
from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_coverage as coverage

AUDIT_EVIDENCE_ID = "[AUDIT-COV-01]"


class AuditCoverageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "app.js").write_text(
            "// AUDIT-UNIT:APP-A\nconst a = 1;\n// AUDIT-UNIT:APP-B\nconst b = 2;\n",
            encoding="utf-8",
        )
        (self.root / "suite.py").write_text(
            'print("[AUDIT-CASE-1] verified")\n', encoding="utf-8"
        )
        self.registry = {
            "schema_version": 1,
            "baseline_commit": "fixture",
            "source_policy": {
                "extensions": [".js", ".py"],
                "exact_names": [],
                "generated": [],
                "excluded": [],
            },
            "evidence_catalog": {
                "CASE-1": {
                    "path": "suite.py",
                    "needle": "[AUDIT-CASE-1]",
                    "command": "python suite.py",
                }
            },
            "findings": [],
            "units": [
                {
                    "id": "APP-A",
                    "path": "app.js",
                    "layer": "app",
                    "priority": "P0",
                    "status": "READ",
                    "boundary": {"type": "marker", "marker": "AUDIT-UNIT:APP-A"},
                },
                {
                    "id": "APP-B",
                    "path": "app.js",
                    "layer": "app",
                    "priority": "P1",
                    "status": "VERIFIED",
                    "boundary": {"type": "marker", "marker": "AUDIT-UNIT:APP-B"},
                    "evidence": ["python suite.py"],
                    "issue": "fixture #1",
                    "regression_cases": ["CASE-1"],
                },
                {
                    "id": "SUITE",
                    "path": "suite.py",
                    "layer": "test_infrastructure",
                    "priority": "P2",
                    "status": "UNREAD",
                    "boundary": {"type": "whole_file"},
                },
            ],
            "cycles": [
                {
                    "cycle": 5,
                    "max_new_application_lines": 600,
                    "application_units": ["APP-A"],
                    "engine_reverification": [],
                    "acceptance": "fixture",
                }
            ],
        }
        coverage.refresh_fingerprints(self.registry, self.root)
        self.tracked = ["app.js", "suite.py"]

    def tearDown(self) -> None:
        self.temp.cleanup()

    def errors(self, registry: dict | None = None, tracked: list[str] | None = None) -> list[str]:
        errors, _ = coverage.validate_registry(
            registry or self.registry,
            self.root,
            self.tracked if tracked is None else tracked,
        )
        return errors

    def test_valid_registry_and_golden_totals(self) -> None:
        errors, resolved = coverage.validate_registry(self.registry, self.root, self.tracked)
        self.assertEqual([], errors)
        data = coverage.summary(self.registry, resolved)
        self.assertEqual(3, data["total"])
        self.assertEqual(1, data["statuses"]["VERIFIED"])
        self.assertIn("| **Total** | **3**", coverage.render_coverage(self.registry, resolved))

    def test_duplicate_unit_id_fails(self) -> None:
        broken = copy.deepcopy(self.registry)
        broken["units"][1]["id"] = "APP-A"
        self.assertTrue(any("duplicate" in error for error in self.errors(broken)))

    def test_missing_and_duplicate_markers_fail(self) -> None:
        (self.root / "app.js").write_text("const a = 1;\n", encoding="utf-8")
        self.assertTrue(any("occurs 0 times" in error for error in self.errors()))
        (self.root / "app.js").write_text(
            "// AUDIT-UNIT:APP-A\n// AUDIT-UNIT:APP-A\n// AUDIT-UNIT:APP-B\n",
            encoding="utf-8",
        )
        self.assertTrue(any("occurs 2 times" in error for error in self.errors()))

    def test_uncovered_prefix_fails(self) -> None:
        (self.root / "app.js").write_text(
            "const uncovered = true;\n// AUDIT-UNIT:APP-A\n// AUDIT-UNIT:APP-B\n",
            encoding="utf-8",
        )
        self.assertTrue(any("first audit marker" in error for error in self.errors()))

    def test_source_edit_makes_read_and_verified_units_stale(self) -> None:
        (self.root / "app.js").write_text(
            "// AUDIT-UNIT:APP-A\nconst a = 9;\n// AUDIT-UNIT:APP-B\nconst b = 2;\n",
            encoding="utf-8",
        )
        errors = self.errors()
        self.assertTrue(any("APP-A: stored fingerprint is stale" in error for error in errors))
        self.assertTrue(any("APP-A: READ unit changed" in error for error in errors))

    def test_invalid_status_and_verified_without_evidence_fail(self) -> None:
        broken = copy.deepcopy(self.registry)
        broken["units"][0]["status"] = "READ partial"
        broken["units"][1]["evidence"] = []
        errors = self.errors(broken)
        self.assertTrue(any("invalid status" in error for error in errors))
        self.assertTrue(any("VERIFIED requires evidence" in error for error in errors))

    def test_missing_regression_id_fails(self) -> None:
        broken = copy.deepcopy(self.registry)
        broken["units"][1]["regression_cases"] = ["DOES-NOT-EXIST"]
        self.assertTrue(any("unknown regression cases" in error for error in self.errors(broken)))

    def test_unregistered_source_file_fails(self) -> None:
        (self.root / "new.js").write_text("const surprise = true;\n", encoding="utf-8")
        errors = self.errors(tracked=[*self.tracked, "new.js"])
        self.assertTrue(any("unregistered source files: new.js" in error for error in errors))

    def test_generated_source_requires_metadata_but_not_a_unit(self) -> None:
        broken = copy.deepcopy(self.registry)
        broken["source_policy"]["generated"] = [
            {
                "pattern": "generated.js",
                "generator": "python build.py",
                "check": "python check.py",
                "reason": "fixture",
            }
        ]
        (self.root / "generated.js").write_text("generated\n", encoding="utf-8")
        self.assertEqual([], self.errors(broken, [*self.tracked, "generated.js"]))
        broken["source_policy"]["generated"][0]["check"] = ""
        self.assertTrue(any("incomplete metadata" in error for error in self.errors(broken)))

    def test_open_high_finding_and_cycle_over_budget_fail(self) -> None:
        broken = copy.deepcopy(self.registry)
        broken["findings"] = [
            {
                "id": "F-1",
                "unit_id": "APP-A",
                "severity": "HIGH",
                "status": "OPEN",
                "issue": "fixture #2",
            }
        ]
        broken["cycles"][0]["max_new_application_lines"] = 601
        errors = self.errors(broken)
        self.assertTrue(any("release-blocking" in error for error in errors))
        self.assertTrue(any("line budget exceeds 600" in error for error in errors))

    def test_refresh_downgrades_changed_verified_unit(self) -> None:
        (self.root / "app.js").write_text(
            "// AUDIT-UNIT:APP-A\nconst a = 1;\n// AUDIT-UNIT:APP-B\nconst b = 3;\n",
            encoding="utf-8",
        )
        coverage.refresh_fingerprints(self.registry, self.root)
        unit = next(unit for unit in self.registry["units"] if unit["id"] == "APP-B")
        self.assertEqual("IN_PROGRESS", unit["status"])
        self.assertEqual([], unit["evidence"])
        self.assertEqual([], unit["regression_cases"])


if __name__ == "__main__":
    unittest.main()
