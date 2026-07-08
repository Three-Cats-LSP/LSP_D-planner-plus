from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.seven_lens_protocol import (
    LENSES,
    _attestation_only_path,
    _closure_only_path,
    _file_sha256,
    _forbidden_closure_path,
    _part_hash,
    _validate_evidence_receipt,
    _validate_registry_closure_mutations,
    _validate_trace_artifact,
    _validate_unreferenced_receipts,
    make_plan,
    sync_reviewed_boundaries,
    validate_record,
    validate_reviewed_cycles,
)


def lens_results():
    return {
        lens: {
            "trace": "Concrete source and caller trace for this lens.",
            "boundary_cases": ["zero", "maximum"],
            "evidence": "Source trace and focused runtime probe.",
            "result": "NO_FINDING",
        }
        for lens in LENSES
    }


class SevenLensProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        source = self.root / "unit.js"
        source.write_text("\n".join(f"line {i}" for i in range(1, 701)) + "\n", encoding="utf-8")
        self.resolved = {
            "UNIT": {"path": "unit.js", "start_line": 1, "end_line": 700, "line_count": 700}
        }
        self.record = {
            "schema_version": 1,
            "target_branch": "dev",
            "audit_commit": "abcdef1",
            "verified_source_commit": "abcdef2",
            "verification_status": "PASSED",
            "parts": [],
            "findings": [],
            "evidence_runs": [
                {"id": "static", "kind": "gate", "case_ids": [], "command": "python audit static", "commit": "abcdef2", "exit_code": 0, "worktree_clean": True},
                {"id": "ci", "kind": "gate", "case_ids": [], "command": "python audit ci", "commit": "abcdef2", "exit_code": 0, "worktree_clean": True},
            ],
            "changed_paths": [],
        }
        for idx, (start, end) in enumerate(((1, 350), (351, 700)), 1):
            digest = _part_hash(source, start, end)
            self.record["parts"].append({
                "id": f"UNIT-P{idx:02d}", "unit_id": "UNIT", "path": "unit.js",
                "start_line": start, "end_line": end, "line_count": end - start + 1,
                "content_fingerprint": digest, "review_session": f"review-{idx}",
                "verification_session": f"verify-{idx}", "lens_results": lens_results(),
            })

    def tearDown(self):
        self.temp.cleanup()

    def validate(self, record, phase="close"):
        with patch("tools.seven_lens_protocol._resolved_registry", return_value=({}, self.resolved)):
            return validate_record(
                self.root, record, phase, check_git=False, enforce_current_schema=False
            )

    def test_complete_record_passes(self):
        self.assertEqual([], self.validate(self.record))

    def test_combined_session_over_budget_fails(self):
        broken = copy.deepcopy(self.record)
        for part in broken["parts"]:
            part["review_session"] = "same-review"
        self.assertTrue(any("700 lines exceeds 600" in e for e in self.validate(broken)))

    def test_same_review_and_verification_session_fails(self):
        broken = copy.deepcopy(self.record)
        broken["parts"][0]["verification_session"] = broken["parts"][0]["review_session"]
        self.assertTrue(any("different session" in e for e in self.validate(broken)))

    def test_missing_lens_trace_fails(self):
        broken = copy.deepcopy(self.record)
        broken["parts"][0]["lens_results"]["L3"]["trace"] = ""
        self.assertTrue(any("L3: concrete trace missing" in e for e in self.validate(broken)))

    def test_stale_fingerprint_fails(self):
        broken = copy.deepcopy(self.record)
        broken["parts"][0]["content_fingerprint"] = "0" * 64
        self.assertTrue(any("fingerprint is stale" in e for e in self.validate(broken)))

    def test_sync_reviewed_boundaries_repairs_same_part_count_drift(self):
        docs = self.root / "docs"
        records = docs / "seven-lens-records"
        records.mkdir(parents=True)
        (docs / "seven-lens-manual-ledger.json").write_text(json.dumps({
            "reviews": [{
                "cycle_id": "SL-C01",
                "unit_id": "UNIT",
                "review_status": "SEVEN_LENS_REVIEWED",
                "verification_status": "PASSED",
                "verified_source_commit": "abcdef2",
                "findings_open": [],
            }]
        }), encoding="utf-8")
        record = copy.deepcopy(self.record)
        record["cycle"] = 1
        record["parts"][1]["start_line"] = 501
        record["parts"][1]["end_line"] = 690
        record["parts"][1]["line_count"] = 190
        record["parts"][1]["content_fingerprint"] = "0" * 64
        path = records / "cycle-01-unit.json"
        path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        with patch("tools.seven_lens_protocol._resolved_registry", return_value=({}, self.resolved)):
            changed, errors = sync_reviewed_boundaries(self.root, write=True)
        self.assertEqual([], errors)
        self.assertEqual(["docs/seven-lens-records/cycle-01-unit.json"], changed)
        repaired = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(501, repaired["parts"][1]["start_line"])
        self.assertEqual(700, repaired["parts"][1]["end_line"])
        self.assertEqual(200, repaired["parts"][1]["line_count"])
        self.assertEqual(_part_hash(self.root / "unit.js", 501, 700), repaired["parts"][1]["content_fingerprint"])

    def test_sync_reviewed_boundaries_blocks_new_part_without_rereview(self):
        docs = self.root / "docs"
        records = docs / "seven-lens-records"
        records.mkdir(parents=True)
        (docs / "seven-lens-manual-ledger.json").write_text(json.dumps({
            "reviews": [{
                "cycle_id": "SL-C01",
                "unit_id": "UNIT",
                "review_status": "SEVEN_LENS_REVIEWED",
                "verification_status": "PASSED",
                "verified_source_commit": "abcdef2",
                "findings_open": [],
            }]
        }), encoding="utf-8")
        path = records / "cycle-01-unit.json"
        path.write_text(json.dumps(self.record, indent=2) + "\n", encoding="utf-8")
        grown = {"UNIT": {"path": "unit.js", "start_line": 1, "end_line": 1001, "line_count": 1001}}
        with patch("tools.seven_lens_protocol._resolved_registry", return_value=({}, grown)):
            changed, errors = sync_reviewed_boundaries(self.root, write=True)
        self.assertEqual([], changed)
        self.assertTrue(any("re-review required" in error for error in errors))

    def test_open_finding_blocks_close(self):
        broken = copy.deepcopy(self.record)
        broken["findings"] = [{
            "id": "SL-C01-M-01", "severity": "MEDIUM", "unit_id": "UNIT",
            "location": "unit.js:10", "root_cause": "A concrete root cause.",
            "failure_path": "A reproducible failure path.", "impact": "Wrong output.",
            "evidence": "Focused probe fails.", "recommendation": "Correct the contract.",
            "status": "OPEN",
        }]
        self.assertTrue(any("open findings block closure" in e for e in self.validate(broken)))

    def test_closed_medium_requires_regression(self):
        broken = copy.deepcopy(self.record)
        broken["findings"] = [{
            "id": "SL-C01-M-01", "severity": "MEDIUM", "unit_id": "UNIT",
            "location": "unit.js:10", "root_cause": "A concrete root cause.",
            "failure_path": "A reproducible failure path.", "impact": "Wrong output.",
            "evidence": "Focused probe fails.", "recommendation": "Correct the contract.",
            "status": "CLOSED", "evidence_ids": ["static"], "regression_ids": [],
        }]
        self.assertTrue(any("regression IDs" in e for e in self.validate(broken)))

    def test_closed_medium_requires_observable_before_after_and_restore(self):
        broken = copy.deepcopy(self.record)
        broken["findings"] = [{
            "id": "SL-C01-M-01", "severity": "MEDIUM", "unit_id": "UNIT",
            "location": "unit.js:10", "root_cause": "A concrete root cause.",
            "failure_path": "A reproducible failure path.", "impact": "Wrong output.",
            "evidence": "Focused probe fails.", "recommendation": "Correct the contract.",
            "status": "CLOSED", "evidence_ids": ["static"], "regression_ids": ["CASE-1"],
        }]
        errors = self.validate(broken)
        self.assertTrue(any("observable_contract" in e for e in errors))
        self.assertTrue(any("pre_fix_evidence_id" in e for e in errors))

    def test_baseline_failure_must_actually_fail(self):
        broken = copy.deepcopy(self.record)
        broken["evidence_runs"].append({
            "id": "before", "kind": "baseline_failure", "case_ids": ["CASE-1"],
            "observable_assertions": ["Rendered schedule contains expected stop"],
            "state_restored": True, "command": "python probe.py", "commit": "abcdef1",
            "exit_code": 0, "worktree_clean": True,
        })
        self.assertTrue(any("must fail before the fix" in e for e in self.validate(broken)))

    def test_audit_commit_cannot_equal_baseline(self):
        broken = copy.deepcopy(self.record)
        broken["baseline_commit"] = "abcdef1"
        broken["audit_commit"] = "abcdef1"
        with patch("tools.seven_lens_protocol._resolved_registry", return_value=({}, self.resolved)):
            with patch("tools.seven_lens_protocol._git", return_value=""):
                errors = validate_record(self.root, broken, "verify", check_git=True)
        self.assertTrue(any("report-only commit after baseline" in e for e in errors))

    def test_evidence_requires_command_and_commit(self):
        broken = copy.deepcopy(self.record)
        broken["evidence_runs"][0]["command"] = ""
        broken["evidence_runs"][0]["commit"] = ""
        errors = self.validate(broken)
        self.assertTrue(any("command missing" in e for e in errors))
        self.assertTrue(any("commit missing" in e for e in errors))

    def test_v2_state_restoration_requires_matching_hashes(self):
        broken = copy.deepcopy(self.record)
        broken["schema_version"] = 2
        broken["integration_base_commit"] = "base123"
        broken["baseline_commit"] = "base123"
        broken["baseline_registry_fingerprint"] = "a" * 64
        broken["baseline_findings"] = []
        broken["evidence_runs"].append({
            "id": "restore", "kind": "state_restoration", "case_ids": ["CASE-1"],
            "observable_assertions": ["state restored"], "state_restored": True,
            "state_before_sha256": "a" * 64, "state_after_sha256": "b" * 64,
            "command": "python probe.py", "commit": "abcdef2", "exit_code": 0,
            "worktree_clean": True,
        })
        self.assertTrue(any("state snapshots differ" in e for e in self.validate(broken)))

    def test_v2_closed_finding_requires_complete_runtime_trace(self):
        broken = copy.deepcopy(self.record)
        broken.update({
            "schema_version": 2, "integration_base_commit": "base123",
            "baseline_commit": "base123", "baseline_registry_fingerprint": "a" * 64,
            "baseline_findings": [],
        })
        broken["findings"] = [{
            "id": "SL-C01-M-01", "severity": "MEDIUM", "unit_id": "UNIT",
            "location": "unit.js:10", "root_cause": "A concrete root cause.",
            "failure_path": "A reproducible failure path.", "impact": "Wrong output.",
            "evidence": "Focused probe fails.", "recommendation": "Correct the contract.",
            "observable_contract": "The user-visible result preserves the physical input.",
            "status": "CLOSED", "regression_ids": ["CASE-1"],
            "evidence_ids": ["before", "after", "restore"],
            "pre_fix_evidence_id": "before", "post_fix_evidence_id": "after",
            "state_restoration_evidence_id": "restore",
        }]
        common = {"case_ids": ["CASE-1"], "observable_assertions": ["observable"],
                  "command": "python probe.py", "commit": "abcdef2", "worktree_clean": True}
        broken["evidence_runs"].extend([
            {**common, "id": "before", "kind": "baseline_failure", "exit_code": 1,
             "state_restored": True},
            {**common, "id": "after", "kind": "post_fix", "exit_code": 0,
             "state_restored": False, "runtime_trace": {"entry_event": "input change"}},
            {**common, "id": "restore", "kind": "state_restoration", "exit_code": 0,
             "state_restored": True, "state_before_sha256": "a" * 64,
             "state_after_sha256": "a" * 64},
        ])
        errors = self.validate(broken)
        self.assertTrue(any("consumer path" in e for e in errors))
        self.assertTrue(any("trace lacks stages" in e for e in errors))
        self.assertTrue(any("artifact hash" in e for e in errors))

    def test_v2_historical_finding_cannot_disappear(self):
        record = copy.deepcopy(self.record)
        record.update({
            "schema_version": 2, "integration_base_commit": "base123",
            "baseline_commit": "base123", "baseline_registry_fingerprint": "a" * 64,
            "baseline_findings": [{"id": "OLD-HIGH", "severity": "HIGH", "status": "OPEN"}],
        })
        with patch("tools.seven_lens_protocol._resolved_registry", return_value=({"findings": []}, self.resolved)):
            errors = validate_record(self.root, record, "close", check_git=False)
        self.assertTrue(any("historical finding OLD-HIGH was deleted" in e for e in errors))

    def test_plan_refuses_branch_that_already_diverged_from_origin_dev(self):
        registry = {"cycles": [{"cycle": 1, "application_units": ["UNIT"]}], "findings": []}

        def fake_git(*args, root):
            if args == ("status", "--porcelain"):
                return ""
            if args == ("rev-parse", "HEAD"):
                return "branch-change"
            if args == ("rev-parse", "origin/dev"):
                return "integration-base"
            raise AssertionError(args)

        with patch("tools.seven_lens_protocol._resolved_registry", return_value=(registry, self.resolved)):
            with patch("tools.seven_lens_protocol._git", side_effect=fake_git):
                with self.assertRaisesRegex(RuntimeError, "HEAD must equal origin/dev"):
                    make_plan(self.root, 1)

    def test_failed_browser_trace_artifact_cannot_support_closure(self):
        artifact = self.root / "trace.json"
        artifact.write_text(json.dumps({
            "passed": False,
            "traces": [{
                "id": "TRACE-1", "passed": False, "repeatable": False,
                "state_restored": False, "assertions": [],
            }],
        }), encoding="utf-8")
        trace = {
            "trace_id": "TRACE-1",
            "artifact_path": "trace.json",
            "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        }
        errors = _validate_trace_artifact(self.root, "FINDING-1", trace, True)
        self.assertTrue(any("did not pass" in error for error in errors))
        self.assertTrue(any("not passing and repeatable" in error for error in errors))
        self.assertTrue(any("did not restore state" in error for error in errors))
        self.assertTrue(any("assertion set" in error for error in errors))

    def test_reviewed_ledger_cannot_hide_legacy_record(self):
        docs = self.root / "docs"
        records = docs / "seven-lens-records"
        records.mkdir(parents=True)
        (docs / "seven-lens-manual-ledger.json").write_text(json.dumps({
            "reviews": [{
                "cycle_id": "SL-C02", "unit_id": "UNIT",
                "review_status": "SEVEN_LENS_REVIEWED",
                "verification_status": "PASSED",
                "verified_source_commit": "abcdef2", "findings_open": [],
            }],
        }), encoding="utf-8")
        (records / "cycle-02.json").write_text(json.dumps(self.record), encoding="utf-8")
        with patch("tools.seven_lens_protocol._resolved_registry", return_value=({}, self.resolved)):
            errors = validate_reviewed_cycles(self.root)
        self.assertTrue(any("schema 4 or 5" in error for error in errors))

    def test_real_closure_rejects_non_current_schema(self):
        with patch("tools.seven_lens_protocol._resolved_registry", return_value=({}, self.resolved)):
            errors = validate_record(self.root, self.record, "close", check_git=False)
        self.assertTrue(any("schema_version must be current" in error for error in errors))

    def test_current_schema_evidence_requires_executed_receipt(self):
        current = copy.deepcopy(self.record)
        current.update({
            "schema_version": 4,
            "record_path": "docs/seven-lens-records/cycle-01.json",
            "integration_base_commit": "base123",
            "baseline_commit": "base123",
            "baseline_registry_fingerprint": "a" * 64,
            "baseline_findings": [],
        })
        errors = self.validate(current)
        self.assertTrue(any("command_argv" in error for error in errors))
        self.assertTrue(any("receipt_path" in error for error in errors))

    def test_evidence_receipt_binds_command_commit_and_executor(self):
        tools = self.root / "tools"
        tools.mkdir()
        executor = tools / "seven_lens_evidence.py"
        executor.write_text("print('executor')\n", encoding="utf-8")
        evidence = {
            "id": "static", "command_argv": ["python", "audit.py"],
            "commit": "abcdef2", "exit_code": 0, "case_ids": [],
            "receipt_path": "receipt.json",
        }
        receipt = {
            "schema_version": 1, "evidence_id": "static",
            "command_argv": evidence["command_argv"], "commit": "abcdef2",
            "exit_code": 0, "case_ids": [], "worktree_clean_before": True,
            "worktree_clean_after": True, "started_at": "2026-07-04T00:00:00Z",
            "finished_at": "2026-07-04T00:01:00Z",
            "stdout_sha256": "a" * 64, "stderr_sha256": "b" * 64,
            "executor_sha256": _file_sha256(executor),
        }
        receipt_path = self.root / "receipt.json"
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        evidence["receipt_sha256"] = _file_sha256(receipt_path)
        self.assertEqual([], _validate_evidence_receipt(self.root, evidence))
        evidence["command_argv"] = ["python", "different.py"]
        errors = _validate_evidence_receipt(self.root, evidence)
        self.assertTrue(any("command_argv does not match" in error for error in errors))

    def test_browser_trace_artifacts_are_attestation_only_paths(self):
        self.assertTrue(_attestation_only_path("dev/seven-lens-browser-trace-cycle05.json"))
        self.assertTrue(_attestation_only_path("dev\\seven-lens-browser-trace-cycle05-pre.json"))
        self.assertTrue(_attestation_only_path("dev/seven-lens-evidence-c06-static.json"))
        self.assertTrue(_attestation_only_path("docs/seven-lens-reports/cycle-05-record.json"))
        self.assertTrue(_attestation_only_path("docs/audit-coverage.md"))
        self.assertFalse(_attestation_only_path("docs/audit-units.json"))
        self.assertFalse(_attestation_only_path("lsp-dplanner-foundation.css"))
        self.assertFalse(_attestation_only_path("dev/ui_css_regression.py"))

    def test_closure_only_path_rejects_application_source(self):
        self.assertTrue(_closure_only_path("docs/audit-units.json"))
        self.assertTrue(_closure_only_path("dev/seven-lens-evidence-c06-ci.json"))
        self.assertFalse(_closure_only_path("lsp-dplanner-controls.css"))
        self.assertFalse(_closure_only_path("docs/seven-lens-traces/cycle-06-controls.json"))
        self.assertTrue(_forbidden_closure_path("dev/ui_controls_css_regression.py"))
        self.assertTrue(_forbidden_closure_path("docs/seven-lens-traces/cycle-06-controls.json"))
        self.assertFalse(_forbidden_closure_path("tools/seven_lens_protocol.py"))
        self.assertFalse(_forbidden_closure_path("tools/test_seven_lens_protocol.py"))
        self.assertFalse(_forbidden_closure_path("dev/seven-lens-evidence-c06-static.json"))

    def test_post_verification_guard_excludes_browser_trace_artifacts(self):
        protected = {
            "lsp-dplanner-foundation.css",
            "dev/ui_css_regression.py",
            "dev/seven-lens-browser-trace-cycle05.json",
            "docs/seven-lens-reports/cycle-05-record.json",
        }
        guarded = sorted(
            path for path in protected if path.strip() and not _attestation_only_path(path)
        )
        self.assertEqual(
            guarded,
            ["dev/ui_css_regression.py", "lsp-dplanner-foundation.css"],
        )

    def test_reviewed_cycle_without_record_requires_explicit_exemption(self):
        docs = self.root / "docs"
        (docs / "seven-lens-records").mkdir(parents=True)
        (docs / "seven-lens-manual-ledger.json").write_text(json.dumps({
            "reviews": [{
                "cycle_id": "SL-C01", "unit_id": "UNIT",
                "review_status": "SEVEN_LENS_REVIEWED",
            }],
        }), encoding="utf-8")
        errors = validate_reviewed_cycles(self.root)
        self.assertTrue(any("no protocol record or exemption" in error for error in errors))

    def test_registry_closure_allows_cycle_finding_rows(self):
        docs = self.root / "docs"
        docs.mkdir(parents=True)
        before = {
            "schema_version": 3,
            "findings": [],
            "units": [],
            "evidence_catalog": {
                "REG-82": {"suite_id": "SUITE-X", "case_id": "SL-C06-SEG-FOCUS-VISIBLE"},
            },
            "suites": {},
            "rules": {},
            "cycles": [],
        }
        after = copy.deepcopy(before)
        after["findings"] = [{
            "id": "SL-C06-M-01",
            "unit_id": "UI-CSS-CONTROLS",
            "severity": "MEDIUM",
            "status": "CLOSED",
            "issue": "Seven-lens Cycle 06 controls CSS audit",
            "summary": "Segmented controls suppress keyboard focus ring",
            "affected_units": ["UI-CSS-CONTROLS"],
            "resolution_commit": "abcdef2",
            "evidence_cases": ["REG-82"],
        }]
        (docs / "audit-units.json").write_text(json.dumps(after), encoding="utf-8")
        record = {
            "cycle": 6,
            "findings": [{
                "id": "SL-C06-M-01",
                "unit_id": "UI-CSS-CONTROLS",
                "severity": "MEDIUM",
                "status": "CLOSED",
                "regression_ids": ["SL-C06-SEG-FOCUS-VISIBLE"],
                "resolution_commit": "abcdef2",
            }],
        }
        with patch(
            "tools.seven_lens_protocol._git",
            return_value=json.dumps(before),
        ):
            errors = _validate_registry_closure_mutations(self.root, record, "abcdef2")
        self.assertEqual([], errors)

    def test_registry_closure_allows_already_closed_unchanged_finding(self):
        docs = self.root / "docs"
        docs.mkdir(parents=True)
        finding = {
            "id": "SL-C06-M-01",
            "unit_id": "UI-CSS-CONTROLS",
            "severity": "MEDIUM",
            "status": "CLOSED",
            "issue": "Seven-lens Cycle 06 controls CSS audit",
            "summary": "Segmented controls suppress keyboard focus ring",
            "affected_units": ["UI-CSS-CONTROLS"],
            "resolution_commit": "7470b4e",
            "evidence_cases": ["REG-82"],
        }
        registry = {
            "schema_version": 3,
            "findings": [finding],
            "units": [],
            "evidence_catalog": {
                "REG-82": {"suite_id": "SUITE-X", "case_id": "SL-C06-SEG-FOCUS-VISIBLE"},
            },
            "suites": {},
            "rules": {},
            "cycles": [],
        }
        (docs / "audit-units.json").write_text(json.dumps(registry), encoding="utf-8")
        record = {
            "cycle": 6,
            "findings": [{
                "id": "SL-C06-M-01",
                "unit_id": "UI-CSS-CONTROLS",
                "severity": "MEDIUM",
                "status": "CLOSED",
                "regression_ids": ["SL-C06-SEG-FOCUS-VISIBLE"],
                "resolution_commit": "7470b4e",
            }],
        }
        with patch(
            "tools.seven_lens_protocol._git",
            return_value=json.dumps(registry),
        ):
            errors = _validate_registry_closure_mutations(self.root, record, "verified1")
        self.assertEqual([], errors)

    def test_registry_closure_uses_record_resolution_commit(self):
        docs = self.root / "docs"
        docs.mkdir(parents=True)
        before = {
            "schema_version": 3,
            "findings": [{
                "id": "SL-C06-L-04",
                "unit_id": "UI-CSS-CONTROLS",
                "severity": "LOW",
                "status": "OPEN",
                "issue": "Seven-lens Cycle 06 controls CSS audit",
                "summary": "Field inputs lack invalid-state styling",
                "affected_units": ["UI-CSS-CONTROLS"],
                "resolution_commit": "",
                "evidence_cases": ["REG-87"],
            }],
            "units": [],
            "evidence_catalog": {
                "REG-87": {"suite_id": "SUITE-X", "case_id": "SL-C06-FIELD-INVALID-STATE"},
            },
            "suites": {},
            "rules": {},
            "cycles": [],
        }
        after = copy.deepcopy(before)
        after["findings"][0]["status"] = "CLOSED"
        after["findings"][0]["resolution_commit"] = "7d403f4"
        (docs / "audit-units.json").write_text(json.dumps(after), encoding="utf-8")
        record = {
            "cycle": 6,
            "findings": [{
                "id": "SL-C06-L-04",
                "unit_id": "UI-CSS-CONTROLS",
                "severity": "LOW",
                "status": "CLOSED",
                "regression_ids": ["SL-C06-FIELD-INVALID-STATE"],
                "resolution_commit": "7d403f4",
            }],
        }
        with patch(
            "tools.seven_lens_protocol._git",
            return_value=json.dumps(before),
        ):
            errors = _validate_registry_closure_mutations(self.root, record, "verified1")
        self.assertEqual([], errors)

    def test_evidence_receipt_rejects_altered_hash(self):
        tools = self.root / "tools"
        tools.mkdir()
        executor = tools / "seven_lens_evidence.py"
        executor.write_text("print('executor')\n", encoding="utf-8")
        evidence = {
            "id": "static", "command_argv": ["python", "audit.py"],
            "commit": "abcdef2", "exit_code": 0, "case_ids": [],
            "receipt_path": "receipt.json",
            "receipt_sha256": "0" * 64,
        }
        receipt = {
            "schema_version": 1, "evidence_id": "static",
            "command_argv": evidence["command_argv"], "commit": "abcdef2",
            "exit_code": 0, "case_ids": [], "worktree_clean_before": True,
            "worktree_clean_after": True, "started_at": "2026-07-04T00:00:00Z",
            "finished_at": "2026-07-04T00:01:00Z",
            "stdout_sha256": "a" * 64, "stderr_sha256": "b" * 64,
            "executor_sha256": _file_sha256(executor),
        }
        (self.root / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
        errors = _validate_evidence_receipt(self.root, evidence)
        self.assertTrue(any("receipt hash does not match" in error for error in errors))

    def test_unreferenced_cycle_receipt_is_rejected(self):
        dev = self.root / "dev"
        dev.mkdir()
        orphan = dev / "seven-lens-evidence-c06-orphan.json"
        orphan.write_text("{}", encoding="utf-8")
        record = {
            "cycle": 6,
            "evidence_runs": [{
                "id": "static",
                "receipt_path": "dev/seven-lens-evidence-c06-static.json",
            }],
        }
        errors = _validate_unreferenced_receipts(self.root, record)
        self.assertTrue(any("unreferenced attestation receipt" in error for error in errors))

    def test_gate_evidence_binds_to_closure_evidence_commit(self):
        record = copy.deepcopy(self.record)
        record.update({
            "schema_version": 4,
            "verified_source_commit": "verified1",
            "closure_evidence_commit": "closure1",
            "evidence_runs": [
                {
                    "id": "static", "kind": "gate", "case_ids": [],
                    "command": "python audit static", "commit": "closure1",
                    "exit_code": 0, "worktree_clean": True,
                },
                {
                    "id": "ci", "kind": "gate", "case_ids": [],
                    "command": "python audit ci", "commit": "closure1",
                    "exit_code": 0, "worktree_clean": True,
                },
                {
                    "id": "after", "kind": "post_fix", "case_ids": ["CASE-1"],
                    "observable_assertions": ["ok"], "state_restored": False,
                    "command": "python probe.py", "commit": "verified1",
                    "exit_code": 0, "worktree_clean": True,
                },
            ],
        })
        errors = self.validate(record)
        self.assertFalse(any("must run at verified_source_commit" in e for e in errors if "static" in e or "ci" in e))
        record["evidence_runs"][0]["commit"] = "verified1"
        errors = self.validate(record)
        self.assertTrue(any("must run at closure_evidence_commit" in e for e in errors))

    def test_registry_closure_rejects_unrelated_finding_edits(self):
        docs = self.root / "docs"
        docs.mkdir(parents=True)
        before = {
            "schema_version": 3,
            "findings": [{
                "id": "SL-C05-M-01",
                "unit_id": "UI-CSS-FOUNDATION",
                "severity": "MEDIUM",
                "status": "OPEN",
                "issue": "Seven-lens Cycle 05 CSS audit",
                "summary": "Mode-isolation CSS targets removed #gfPresetsRow",
                "affected_units": ["UI-CSS-FOUNDATION"],
                "resolution_commit": "",
                "evidence_cases": ["REG-76"],
            }],
            "units": [],
            "evidence_catalog": {
                "REG-76": {"suite_id": "SUITE-X", "case_id": "SL-C05-GF-ROW-MODE-ISOLATION"},
                "REG-82": {"suite_id": "SUITE-X", "case_id": "SL-C06-SEG-FOCUS-VISIBLE"},
            },
            "suites": {},
            "rules": {},
            "cycles": [],
        }
        after = copy.deepcopy(before)
        after["findings"][0]["summary"] = "tampered summary"
        after["findings"].append({
            "id": "SL-C06-M-01",
            "unit_id": "UI-CSS-CONTROLS",
            "severity": "MEDIUM",
            "status": "CLOSED",
            "issue": "Seven-lens Cycle 06 controls CSS audit",
            "summary": "Segmented controls suppress keyboard focus ring",
            "affected_units": ["UI-CSS-CONTROLS"],
            "resolution_commit": "abcdef2",
            "evidence_cases": ["REG-82"],
        })
        (docs / "audit-units.json").write_text(json.dumps(after), encoding="utf-8")
        record = {
            "cycle": 6,
            "findings": [{
                "id": "SL-C06-M-01",
                "unit_id": "UI-CSS-CONTROLS",
                "severity": "MEDIUM",
                "status": "CLOSED",
                "regression_ids": ["SL-C06-SEG-FOCUS-VISIBLE"],
                "resolution_commit": "abcdef2",
            }],
        }
        with patch(
            "tools.seven_lens_protocol._git",
            return_value=json.dumps(before),
        ):
            errors = _validate_registry_closure_mutations(self.root, record, "abcdef2")
        self.assertTrue(any("unrelated finding SL-C05-M-01" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
