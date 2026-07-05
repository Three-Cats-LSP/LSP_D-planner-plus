from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.seven_lens_protocol import validate_record
from tools.seven_lens_protocol_migrations import (
    MIGRATION_RECEIPT_EXIT_V1,
    MIGRATION_RESOLUTION_COMMIT_V1,
    apply_protocol_migrations,
    apply_receipt_exit_v1,
    derive_resolution_commit_v1,
    finding_has_proven_resolution,
    migration_allows_registry_finding_change,
    migration_fingerprint,
)


class SevenLensMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        tools = self.root / "tools"
        tools.mkdir()
        (tools / "seven_lens_evidence.py").write_text("executor\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_migration_fingerprint_is_stable(self):
        first = migration_fingerprint()
        second = migration_fingerprint()
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)

    def test_receipt_exit_v1_overrides_declared_zero(self):
        receipt = {
            "schema_version": 1,
            "evidence_id": "static",
            "command_argv": ["python", "-m", "tools.audit", "check", "--profile", "static"],
            "commit": "abc1234",
            "exit_code": 1,
            "case_ids": [],
            "worktree_clean_before": True,
            "worktree_clean_after": True,
            "started_at": "2026-07-05T00:00:00Z",
            "finished_at": "2026-07-05T00:01:00Z",
            "stdout_sha256": "a" * 64,
            "stderr_sha256": "b" * 64,
            "executor_sha256": "c" * 64,
        }
        receipt_path = self.root / "dev/seven-lens-evidence-c06-static.json"
        receipt_path.parent.mkdir(parents=True)
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        import hashlib

        receipt_hash = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
        record = {
            "evidence_runs": [{
                "id": "static",
                "kind": "gate",
                "exit_code": 0,
                "worktree_clean": True,
                "receipt_path": "dev/seven-lens-evidence-c06-static.json",
                "receipt_sha256": receipt_hash,
            }],
        }
        migrated = apply_receipt_exit_v1(self.root, record)
        self.assertEqual(migrated["evidence_runs"][0]["exit_code"], 1)

    def test_derive_resolution_from_post_fix_commit(self):
        record = {
            "verified_source_commit": "verified9",
            "findings": [{
                "id": "SL-C03-H-01",
                "status": "CLOSED",
                "severity": "HIGH",
                "regression_ids": ["CASE-1"],
                "evidence_ids": ["before", "after", "restore", "static"],
                "pre_fix_evidence_id": "before",
                "post_fix_evidence_id": "after",
                "state_restoration_evidence_id": "restore",
            }],
            "evidence_runs": [
                {"id": "before", "kind": "baseline_failure", "exit_code": 1, "case_ids": ["CASE-1"]},
                {"id": "after", "kind": "post_fix", "exit_code": 0, "case_ids": ["CASE-1"], "commit": "fixcommit1"},
                {"id": "restore", "kind": "state_restoration", "exit_code": 0, "case_ids": ["CASE-1"]},
                {"id": "static", "kind": "gate", "exit_code": 0, "case_ids": []},
            ],
        }
        self.assertTrue(finding_has_proven_resolution(record, record["findings"][0]))

        def fake_git(*args, root):
            if args[:2] == ("show", "verified9:docs/audit-units.json"):
                return json.dumps({"findings": []})
            if args == ("rev-parse", "fixcommit1"):
                return "fixcommit1" * 5
            raise AssertionError(args)

        derived = derive_resolution_commit_v1(
            self.root, record, record["findings"][0], git_fn=fake_git
        )
        self.assertEqual(derived, "fixcommit1" * 5)

    def test_legacy_record_passes_close_after_in_memory_migration(self):
        source = self.root / "unit.js"
        source.write_text("line\n", encoding="utf-8")
        resolved = {"UNIT": {"path": "unit.js", "start_line": 1, "end_line": 1, "line_count": 1}}
        record = {
            "schema_version": 4,
            "cycle": 3,
            "target_branch": "dev",
            "record_path": "docs/seven-lens-records/cycle-03.json",
            "integration_base_commit": "verified9",
            "baseline_commit": "verified9",
            "baseline_registry_fingerprint": "a" * 64,
            "baseline_findings": [],
            "audit_commit": "audit001",
            "verified_source_commit": "verified9",
            "verification_status": "PASSED",
            "parts": [{
                "id": "UNIT-P01", "unit_id": "UNIT", "path": "unit.js",
                "start_line": 1, "end_line": 1, "line_count": 1,
                "content_fingerprint": "0" * 64,
                "review_session": "review-1",
                "verification_session": "verify-1",
                "lens_results": {
                    f"L{i}": {
                        "trace": "Concrete source and caller trace for this lens.",
                        "boundary_cases": ["zero"],
                        "evidence": "Source trace and focused runtime probe.",
                        "result": "NO_FINDING",
                    }
                    for i in range(1, 8)
                },
            }],
            "findings": [{
                "id": "SL-C03-L-01",
                "severity": "LOW",
                "unit_id": "UNIT",
                "location": "unit.js:1",
                "root_cause": "Concrete root cause.",
                "failure_path": "Repro path.",
                "impact": "Impact.",
                "evidence": "Evidence.",
                "recommendation": "Fix.",
                "status": "CLOSED",
                "evidence_ids": ["static"],
            }],
            "evidence_runs": [
                {
                    "id": "static", "kind": "gate", "case_ids": [],
                    "command": "python -m tools.audit check --profile static",
                    "commit": "verified9", "exit_code": 0, "worktree_clean": True,
                    "command_argv": ["python", "-m", "tools.audit", "check", "--profile", "static"],
                },
                {
                    "id": "ci", "kind": "gate", "case_ids": [],
                    "command": "python -m tools.audit run --profile ci",
                    "commit": "verified9", "exit_code": 0, "worktree_clean": True,
                    "command_argv": ["python", "-m", "tools.audit", "run", "--profile", "ci"],
                },
            ],
            "changed_paths": [],
        }

        def fake_git(*args, root):
            if args[:2] == ("show", "verified9:docs/audit-units.json"):
                return json.dumps({"findings": []})
            if args == ("rev-parse", "verified9"):
                return "verified9" * 5
            if args[0] == "show" and args[1].endswith(":docs/audit-units.json"):
                return json.dumps({"findings": []})
            return ""

        with patch("tools.seven_lens_protocol._resolved_registry", return_value=({"findings": []}, resolved)):
            with patch("tools.seven_lens_protocol._git", side_effect=fake_git):
                migrated, errors = apply_protocol_migrations(self.root, record, git_fn=fake_git)
        self.assertEqual([], errors)
        self.assertIn(MIGRATION_RESOLUTION_COMMIT_V1, migrated["protocol_migrations"])
        self.assertIn(MIGRATION_RECEIPT_EXIT_V1, migrated["protocol_migrations"])
        self.assertTrue(migrated["findings"][0]["resolution_commit"])

    def test_schema_five_requires_explicit_resolution_commit(self):
        record = copy.deepcopy({
            "schema_version": 5,
            "findings": [{"id": "SL-C06-L-01", "status": "CLOSED"}],
        })
        from tools.seven_lens_protocol_migrations import requires_explicit_resolution_commit

        self.assertTrue(requires_explicit_resolution_commit(record, 5))
        self.assertFalse(requires_explicit_resolution_commit({"schema_version": 4}, 5))

    def test_migration_allows_proven_cross_cycle_registry_closure(self):
        records = self.root / "docs" / "seven-lens-records"
        records.mkdir(parents=True)
        (records / "cycle-05-css.json").write_text(
            json.dumps({
                "schema_version": 4,
                "cycle": 5,
                "protocol_migrations": [MIGRATION_RESOLUTION_COMMIT_V1, MIGRATION_RECEIPT_EXIT_V1],
                "verified_source_commit": "abc1234567890",
                "findings": [{
                    "id": "SL-C05-M-01",
                    "severity": "MEDIUM",
                    "unit_id": "UI-CSS",
                    "status": "CLOSED",
                    "summary": "Mode-isolation CSS targets removed row",
                    "evidence_ids": ["static", "ci"],
                    "regression_ids": ["REG-76"],
                    "pre_fix_evidence_id": "pre",
                    "post_fix_evidence_id": "post",
                    "state_restoration_evidence_id": "restore",
                }],
                "evidence_runs": [
                    {"id": "static", "kind": "gate", "exit_code": 0, "commit": "abc1234567890"},
                    {"id": "ci", "kind": "gate", "exit_code": 0, "commit": "abc1234567890"},
                    {"id": "pre", "kind": "pre_fix", "exit_code": 1, "commit": "abc1234567890"},
                    {"id": "post", "kind": "post_fix", "exit_code": 0, "commit": "fix1234567890"},
                    {"id": "restore", "kind": "state_restoration", "exit_code": 0, "commit": "abc1234567890"},
                ],
            }),
            encoding="utf-8",
        )
        registry_path = self.root / "docs" / "audit-units.json"
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(
            json.dumps({
                "findings": [{
                    "id": "SL-C05-M-01",
                    "unit_id": "UI-CSS",
                    "severity": "MEDIUM",
                    "status": "CLOSED",
                    "issue": "Seven-lens Cycle 05 CSS audit",
                    "summary": "Mode-isolation CSS targets removed row",
                    "affected_units": ["UI-CSS"],
                    "resolution_commit": "fix1234",
                    "evidence_cases": ["REG-76"],
                }],
                "evidence_catalog": {"REG-76": {"case_id": "REG-76"}},
            }),
            encoding="utf-8",
        )

        def fake_git(*args, root):
            if args == ("rev-parse", "fix1234567890"):
                return "fix1234567890" * 5
            if args == ("rev-parse", "abc1234567890"):
                return "abc1234567890" * 5
            if args[0] == "show" and ":docs/audit-units.json" in args[1]:
                return json.dumps({"findings": []})
            return ""

        before = {
            "id": "SL-C05-M-01",
            "status": "OPEN",
            "severity": "MEDIUM",
            "unit_id": "UI-CSS",
        }
        after = json.loads(registry_path.read_text())["findings"][0]
        allowed = migration_allows_registry_finding_change(
            self.root, "SL-C05-M-01", before, after, git_fn=fake_git
        )
        self.assertTrue(allowed)
        self.assertTrue(
            migration_allows_registry_finding_change(
                self.root, "SL-C05-M-01", before, after, git_fn=fake_git
            )
        )
        tampered = dict(after)
        tampered["resolution_commit"] = "deadbeef"
        self.assertFalse(
            migration_allows_registry_finding_change(
                self.root, "SL-C05-M-01", before, tampered, git_fn=fake_git
            )
        )


if __name__ == "__main__":
    unittest.main()
