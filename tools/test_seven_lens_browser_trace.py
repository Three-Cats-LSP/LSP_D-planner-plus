from __future__ import annotations

import unittest

from tools.seven_lens_browser_trace import (
    _capture_is_finite,
    evaluate_assertion,
    validate_trace_spec,
)


def valid_spec():
    return {
        "schema_version": 2,
        "repeat": 2,
        "traces": [{
            "id": "TRACE-UNIT-ROUNDTRIP",
            "entry_event": "User changes the visible units selector.",
            "consumer_path": ["unitsSelect change", "setUnits", "physical consumer"],
            "state": {
                "selectors": ["#unitsSelect", "#depth"],
                "restore_order": ["#depth", "#unitsSelect"],
                "globals": [],
            },
            "setup": [],
            "steps": [
                {"capture": "before", "values": {"depth": "Number(depth.value)"}},
                {"action": "select", "selector": "#unitsSelect", "value": "imperial"},
                {"capture": "after", "values": {"depth": "Number(depth.value)"}},
            ],
            "assertions": [{
                "id": "physical-depth-preserved",
                "left": "$.before.depth",
                "op": "not_equal",
                "right": "$.after.depth",
            }],
        }],
    }


class SevenLensBrowserTraceTests(unittest.TestCase):
    def test_empty_trace_list_is_rejected(self):
        spec = valid_spec()
        spec["traces"] = []
        self.assertIn("traces must be a non-empty list", validate_trace_spec(spec))

    def test_empty_assertion_list_is_rejected(self):
        spec = valid_spec()
        spec["traces"][0]["assertions"] = []
        self.assertTrue(any("assertions must be non-empty" in error for error in validate_trace_spec(spec)))

    def test_forced_tested_action_is_rejected(self):
        spec = valid_spec()
        spec["traces"][0]["steps"][1]["force"] = True
        self.assertTrue(any("tested user actions must not use force" in error for error in validate_trace_spec(spec)))

    def test_single_run_cannot_claim_repeatability(self):
        spec = valid_spec()
        spec["repeat"] = 1
        self.assertTrue(any("repeat must be" in error for error in validate_trace_spec(spec)))

    def test_non_finite_or_evaluation_error_capture_is_rejected(self):
        self.assertFalse(_capture_is_finite({"physical_depth": float("nan")}))
        self.assertFalse(_capture_is_finite({"consumer": {"traceError": "missing function"}}))

    def test_close_assertion_uses_exact_captured_value(self):
        captures = {"metric": {"canonical_m": 30.0}, "imperial": {"canonical_m": 29.870399}}
        ok, _ = evaluate_assertion(
            {"left": "$.metric.canonical_m", "op": "close", "right": 30, "tolerance": 1e-9},
            captures,
        )
        drifted, _ = evaluate_assertion(
            {"left": "$.imperial.canonical_m", "op": "close", "right": 30, "tolerance": 1e-9},
            captures,
        )
        self.assertTrue(ok)
        self.assertFalse(drifted)

    def test_equal_assertion_resolves_both_capture_paths(self):
        captures = {"before": {"value": "30"}, "after": {"value": "30"}}
        ok, _ = evaluate_assertion(
            {"left": "$.before.value", "op": "equal", "right": "$.after.value"}, captures
        )
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
