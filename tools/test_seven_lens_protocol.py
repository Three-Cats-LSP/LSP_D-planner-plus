from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.seven_lens_protocol import LENSES, validate_record


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
        lines = source.read_bytes().splitlines(keepends=True)
        self.resolved = {
            "UNIT": {"path": "unit.js", "start_line": 1, "end_line": 700, "line_count": 700}
        }
        self.record = {
            "target_branch": "dev",
            "audit_commit": "abcdef1",
            "verified_source_commit": "abcdef2",
            "verification_status": "PASSED",
            "parts": [],
            "findings": [],
            "evidence_runs": [
                {"id": "static", "command": "python audit static", "commit": "abcdef2", "exit_code": 0, "worktree_clean": True},
                {"id": "ci", "command": "python audit ci", "commit": "abcdef2", "exit_code": 0, "worktree_clean": True},
            ],
            "changed_paths": [],
        }
        for idx, (start, end) in enumerate(((1, 350), (351, 700)), 1):
            digest = hashlib.sha256(b"".join(lines[start - 1:end])).hexdigest()
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
            return validate_record(self.root, record, phase, check_git=False)

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

    def test_evidence_requires_command_and_commit(self):
        broken = copy.deepcopy(self.record)
        broken["evidence_runs"][0]["command"] = ""
        broken["evidence_runs"][0]["commit"] = ""
        errors = self.validate(broken)
        self.assertTrue(any("command missing" in e for e in errors))
        self.assertTrue(any("commit missing" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
