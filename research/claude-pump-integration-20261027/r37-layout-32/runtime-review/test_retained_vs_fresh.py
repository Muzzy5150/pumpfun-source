#!/usr/bin/env python3
"""Negative controls for the fail-closed L31-to-L32 log transition."""
from pathlib import Path
import importlib.util
import unittest


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("retained_vs_fresh", HERE / "retained_vs_fresh.py")
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class TransitionControls(unittest.TestCase):
    def rejected(self, old, new):
        with self.assertRaises(review.VerificationError):
            review.inserted_message(old, new, "synthetic/case")

    def test_expected_insertions_are_accepted(self):
        old = ["before", "after"]
        for message in review.EXPECTED_INSERTIONS:
            self.assertEqual(review.inserted_message(old, ["before", message, "after"], "case"), message)

    def test_unchanged_sequence_is_accepted(self):
        self.assertIsNone(review.inserted_message(["same"], ["same"], "case"))

    def test_missing_message_is_rejected(self):
        self.rejected(["before", next(iter(review.EXPECTED_INSERTIONS))], ["before"])

    def test_unexpected_message_is_rejected(self):
        self.rejected(["before"], ["before", "Program log: unexpected"])

    def test_replacement_is_rejected(self):
        self.rejected(["before"], ["after"])

    def test_reordering_is_rejected(self):
        self.rejected(["a", "b"], ["b", next(iter(review.EXPECTED_INSERTIONS)), "a"])

    def test_duplicate_insertion_is_rejected(self):
        message = next(iter(review.EXPECTED_INSERTIONS))
        self.rejected(["a"], ["a", message, message])

    def test_structured_outcome_change_is_rejected(self):
        with self.assertRaises(review.VerificationError):
            review.require_equal({"after": {"lamports": 1}}, {"after": {"lamports": 2}}, "state")

    def test_error_change_is_rejected(self):
        with self.assertRaises(review.VerificationError):
            review.require_equal({"error": None}, {"error": "Custom(1)"}, "error")

    def test_event_change_is_rejected(self):
        with self.assertRaises(review.VerificationError):
            review.require_equal({"events": []}, {"events": ["changed"]}, "events")

    def test_duplicate_json_key_is_rejected(self):
        with self.assertRaises(review.VerificationError):
            review._unique_object([("case", 1), ("case", 2)])

    def test_compute_line_is_the_only_log_filter(self):
        lines = ["Program abc consumed 1 of 2 compute units", "Program log: retained"]
        self.assertEqual(review.normalized_logs(lines, "logs"), ["Program log: retained"])
        self.assertEqual(review.normalized_logs(["compute units"], "logs"), ["compute units"])

    def test_missing_input_is_rejected(self):
        with self.assertRaises(review.VerificationError):
            review.sha256(HERE / "does-not-exist")


if __name__ == "__main__":
    unittest.main(verbosity=2)
