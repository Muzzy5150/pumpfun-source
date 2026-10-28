"""Deduplicated signed V1 default-quote admission cases for combined qualification."""
from pathlib import Path
import argparse
import base64
import gzip
import hashlib
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'scripts'))
from pump_diagnostic_audit import audit
from solders.transaction import VersionedTransaction


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cases-file', type=Path, default=HERE / 'incremental-cases.json')
    args = parser.parse_args()
    probe = ROOT / 'work/parallel-main-distribution-parser-audit/probe_quote_gate.py'
    spec = importlib.util.spec_from_file_location('distribution_quote_gate_definitions', probe)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    definitions = json.loads(args.cases_file.read_text())['cases']
    cases = {case['name']: case for case in module.cases()}
    paths = [Path(__file__), probe, Path(module.fixture.__file__), args.cases_file, args.candidate]
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {str(p.resolve()): sha(p) for p in paths}
    rows = []
    for definition in definitions:
        case = cases[definition['name']]
        original, candidate = module.fixture.run(case), module.fixture.run(case, args.candidate)
        identity = hashlib.sha256((original['transaction_base64'] + json.dumps(
            {k: v for k, v in original['before'].items() if v is not None},
            sort_keys=True, separators=(',', ':'))).encode()).hexdigest()
        assert identity == definition['input_hash'], (case['name'], identity)
        assert original['transaction_base64'] == candidate['transaction_base64']
        for side in (original, candidate):
            assert all(VersionedTransaction.from_bytes(base64.b64decode(side['transaction_base64'])).verify_with_results())
        differences = [k for k in ('error', 'before', 'after', 'events', 'inner', 'return')
                       if original[k] != candidate[k]]
        rows.append({'case': case, 'original': original, 'candidate': candidate,
                     'different_fields': differences, 'input_hash': identity})
        print(case['name'], differences, flush=True)
    assert before == {str(p.resolve()): sha(p) for p in paths}
    diagnostics = audit({'v1_quote_gate': rows})
    report = {'scope': __doc__, 'case_count': len(rows), 'cases': rows, 'inputs_sha256': before,
              'mismatches': [r['case']['name'] for r in rows if r['different_fields']],
              'diagnostics': diagnostics}
    args.output.write_bytes(gzip.compress(json.dumps(report).encode(), mtime=0))
    print(json.dumps({'case_count': len(rows), 'mismatches': report['mismatches'],
                      'diagnostic_mismatches': len(diagnostics['mismatches'])}))
    assert not report['mismatches'] and not diagnostics['mismatches']


if __name__ == '__main__':
    main()
