from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

from .cli import effective_statuses, invalid_closed_findings
from .model import SuiteResult
from .model import AuditReport, CheckResult
from .reporting import render_markdown, write_reports
from .registry import load_registry, validate_migration, validate_registry_v2
from .rules import run_parser
from .runner import run_suites

ROOT = Path(__file__).resolve().parents[2]


class AuditSystemTests(unittest.TestCase):
    def test_repository_registry_and_migration_are_complete(self) -> None:
        registry = load_registry(ROOT)
        errors, _ = validate_registry_v2(ROOT, registry)
        self.assertEqual([], errors)
        self.assertEqual([], validate_migration(ROOT))

    def test_recursive_evidence_command_is_rejected(self) -> None:
        registry = load_registry(ROOT)
        broken = copy.deepcopy(registry)
        broken["suite_catalog"][0]["command"] = ["{python}", "dev/run_all_regression.py"]
        errors, _ = validate_registry_v2(ROOT, broken)
        self.assertTrue(any("recursive umbrella" in error for error in errors))

    def test_closed_finding_and_unknown_case_are_rejected(self) -> None:
        registry = load_registry(ROOT)
        broken = copy.deepcopy(registry)
        broken["findings"][0].pop("resolution_commit", None)
        broken["evidence_catalog"]["REG-01"]["case_id"] = "not-declared"
        errors, _ = validate_registry_v2(ROOT, broken)
        self.assertTrue(any("resolution_commit" in error for error in errors))
        self.assertTrue(any("not declared" in error for error in errors))

    def test_failed_evidence_downgrades_verified_unit_and_invalidates_finding(self) -> None:
        registry = {
            "evidence_catalog": {"CASE": {"suite_id": "S", "case_id": "case"}},
            "units": [{
                "id": "U", "status": "VERIFIED", "fingerprint": "x",
                "last_read_fingerprint": "x", "regression_cases": ["CASE"],
            }],
            "findings": [{"id": "F", "status": "CLOSED", "evidence_cases": ["CASE"]}],
        }
        suites = [SuiteResult("S", "FAIL", ["false"], 1, 1)]
        effective = effective_statuses(registry, {"U": {"current_fingerprint": "x"}}, suites)
        self.assertEqual("READ", effective["U"]["effective"])
        self.assertEqual("F", invalid_closed_findings(registry, suites)[0]["id"])
        missing = invalid_closed_findings(registry, [], require_all=True)
        self.assertIn("not executed", missing[0]["reason"])

    def test_static_run_never_claims_unexecuted_evidence(self) -> None:
        registry = {
            "evidence_catalog": {"CASE": {"suite_id": "RELEASE", "case_id": "case"}},
            "units": [{
                "id": "U", "status": "VERIFIED", "fingerprint": "x",
                "last_read_fingerprint": "x", "regression_cases": ["CASE"],
            }],
        }
        effective = effective_statuses(registry, {"U": {"current_fingerprint": "x"}}, [])
        self.assertEqual("READ", effective["U"]["effective"])
        self.assertIn("not executed", effective["U"]["reason"])

    def test_runner_deduplicates_identical_commands(self) -> None:
        registry = {"suite_catalog": [
            {"id": "A", "command": ["{python}", "-c", "print('ok')"], "profiles": ["ci"], "timeout_seconds": 10},
            {"id": "B", "command": ["{python}", "-c", "print('ok')"], "profiles": ["ci"], "timeout_seconds": 10},
        ]}
        results = run_suites(ROOT, registry, "ci")
        self.assertEqual(["PASS", "PASS"], [item.status for item in results])
        self.assertIn("Deduplicated", results[1].stdout)

    def test_runner_reports_timeout(self) -> None:
        registry = {"suite_catalog": [{
            "id": "SLOW", "command": ["{python}", "-c", "import time; time.sleep(2)"],
            "profiles": ["ci"], "timeout_seconds": 1,
        }]}
        result = run_suites(ROOT, registry, "ci")[0]
        self.assertEqual("ERROR", result.status)
        self.assertIn("timed out", result.error or "")

    def test_parser_reports_invalid_js_html_css_and_accepts_formatting(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "good.js").write_text(
                "function sample( ) {\n  return true;\n}\n", encoding="utf-8"
            )
            (root / "bad.js").write_text("function broken( {", encoding="utf-8")
            (root / "bad.html").write_text(
                "<div id='x' id='y'></div><style>a {</style><script>const = 1;</script>", encoding="utf-8"
            )
            registry = {"source_policy": {"generated": []}, "units": [
                {"path": "good.js"}, {"path": "bad.js"}, {"path": "bad.html"},
            ]}
            parsed, errors = run_parser(root, registry)
            self.assertEqual([], errors)
            diagnostics = parsed["diagnostics"]
            self.assertTrue(any(item["path"] == "bad.js" for item in diagnostics))
            self.assertTrue(any(item["path"] == "bad.html" and item["kind"] == "javascript" for item in diagnostics))
            self.assertTrue(any(item["path"] == "bad.html" and item["kind"] == "html" for item in diagnostics))
            self.assertTrue(any(item["path"] == "bad.html" and item["kind"] == "css" for item in diagnostics))
            self.assertFalse(any(item["path"] == "good.js" for item in diagnostics))

    def test_dom_reference_rule_reports_missing_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "app.html").write_text(
                "<div id='present'></div><script>document.getElementById('missing')</script>", encoding="utf-8"
            )
            registry = {
                "source_policy": {"generated": []},
                "units": [{"path": "app.html"}],
                "rule_catalog": [{
                    "id": "DOM", "kind": "html.dom_references_resolve", "severity": "HIGH",
                    "unit_ids": ["U"], "paths": ["app.html"], "rationale": "r", "remediation": "x",
                }],
            }
            from .rules import evaluate_rules
            results, errors = evaluate_rules(root, registry)
            self.assertEqual([], errors)
            self.assertEqual("FAIL", results[0].status)
            self.assertIn("missing", results[0].message)

    def test_json_and_markdown_reports_are_generated(self) -> None:
        report = AuditReport(2, "static", "check", "abc")
        report.checks.append(CheckResult("R", "PASS", "LOW", ["U"], "ok"))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "dev").mkdir()
            write_reports(root, report)
            data = json.loads((root / "dev" / "audit-results.json").read_text(encoding="utf-8"))
            self.assertTrue(data["summary"]["ok"])
            self.assertIn("LSP Audit Report", render_markdown(report))

    def test_ccr_evidence_is_behavioral_not_a_source_window(self) -> None:
        registry = load_registry(ROOT)
        self.assertEqual("SUITE-CCR-DIFFERENTIAL", registry["evidence_catalog"]["REG-07"]["suite_id"])
        source = (ROOT / "tools" / "audit" / "registry.py").read_text(encoding="utf-8")
        self.assertNotIn("[:900]", source)


if __name__ == "__main__":
    unittest.main()
