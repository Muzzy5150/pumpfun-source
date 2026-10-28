import gzip
import json
import tempfile
import unittest
from pathlib import Path

import audit
from paired_receipt_reader import records


def trace(*messages):
    return [f'Program {audit.PUMP} invoke [1]', *messages,
            f'Program {audit.PUMP} success']


class LogOracleTests(unittest.TestCase):
    def compare(self, left, right):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            report = {'metadata': {'note': 'escaped \\"{}😀' * 12000},
                      'suites': {'example': {'cases': [
                          {'candidate': {'logs': right}, 'original': {'logs': left}}
                      ]}}}
            path = folder / 'input.json.gz'
            with gzip.open(path, 'wt', encoding='utf-8') as stream:
                json.dump(report, stream)
            self.assertEqual(len(list(records(path))), 1)
            return audit.audit_inputs([(path, 1)], folder / 'audit.json',
                                      folder / 'mismatches.jsonl.gz')

    def test_equal(self):
        self.assertEqual(self.compare(trace('Program log: hello'),
                                      trace('Program log: hello'))['status'], 'passed')

    def test_compute_and_coordinates_only_are_ignored(self):
        left = trace('Program log: AnchorError thrown in programs/pump/src/lib.rs:4:8.',
                     f'Program {audit.PUMP} consumed 5 of 100 compute units')
        right = trace('Program log: AnchorError thrown in programs/pump/src/lib.rs:9:2.',
                      f'Program {audit.PUMP} consumed 9 of 100 compute units')
        self.assertEqual(self.compare(left, right)['status'], 'passed')

    def test_missing_message_fails(self):
        report = self.compare(trace('Program log: No cashback to claim'), trace())
        self.assertEqual(report['status'], 'mismatches')
        self.assertEqual(report['counts']['non_filename_mismatches'], 1)

    def test_message_order_fails(self):
        report = self.compare(trace('Program log: a', 'Program log: b'),
                              trace('Program log: b', 'Program log: a'))
        self.assertEqual(report['families'], {'ordinary_message_order': 1})
        self.assertEqual(report['status'], 'mismatches')

    def test_filename_differences_are_retained_separately(self):
        report = self.compare(
            trace('Program log: AnchorError thrown in programs/pump/src/a.rs:1.'),
            trace('Program log: AnchorError thrown in programs/pump/src/b.rs:2.'))
        self.assertEqual(report['families'], {'source_file_path_only': 1})
        self.assertEqual(report['status'], 'passed')
        self.assertEqual(report['counts']['mismatched_main_sequences'], 1)

    def test_error_payload_is_not_hidden_by_filename_handling(self):
        report = self.compare(
            trace('Program log: AnchorError thrown in programs/pump/src/a.rs:1. Code X'),
            trace('Program log: AnchorError thrown in programs/pump/src/b.rs:2. Code Y'))
        self.assertEqual(report['status'], 'mismatches')

    def test_one_sided_main_invocation_fails(self):
        report = self.compare(trace('Program log: executed'), [])
        self.assertEqual(report['families'], {'main_invocation_disagreement': 1})
        self.assertEqual(report['status'], 'mismatches')

    def test_unrelated_outer_harness_is_excluded(self):
        left = ['Program harness invoke [1]', 'Program log: outside-a',
                f'Program {audit.PUMP} invoke [2]', 'Program log: same',
                f'Program {audit.PUMP} success', 'Program harness success']
        right = [line.replace('outside-a', 'outside-b') for line in left]
        self.assertEqual(self.compare(left, right)['status'], 'passed')

    def test_nested_cpi_logs_are_preserved(self):
        left = trace('Program child invoke [2]', 'Program log: nested',
                     'Program child success')
        right = trace('Program child invoke [2]', 'Program child success')
        self.assertEqual(self.compare(left, right)['status'], 'mismatches')

    def test_unbalanced_logs_fail_closed(self):
        with self.assertRaises(AssertionError):
            self.compare([f'Program {audit.PUMP} invoke [1]'], trace())


if __name__ == '__main__':
    unittest.main()
