from __future__ import annotations

import unittest

from tools.seven_lens_browser_trace import evaluate_assertion


class SevenLensBrowserTraceTests(unittest.TestCase):
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
