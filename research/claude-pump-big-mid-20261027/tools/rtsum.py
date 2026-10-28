#!/usr/bin/env python3
"""rtsum.py <corpus.json.gz from run_suites.py> <out summary.json>: compact runtime summary (per-suite case
counts against the harness expectations, errors, paired diagnostic audit, bound file hashes)."""
import gzip, hashlib, json, sys
from pathlib import Path

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
raw = src.read_bytes()
r = json.loads(gzip.decompress(raw))
summary = {
    'report_sha256': hashlib.sha256(raw).hexdigest(),
    'candidate_sha256': r['candidate_sha256'],
    'original_sha256': r['original_sha256'],
    'suites': len(r['counts']),
    'suites_requested': len(r['suites_requested']),
    'case_count': r['case_count'],
    'expected_cases': sum(r['expected'].values()),
    'errors': [{'suite': e['suite'], 'error': e['error'][:400]} for e in r['errors']],
    'diagnostic_log_cases': r['diagnostics']['log_bearing_cases'],
    'diagnostic_mismatches': len(r['diagnostics']['mismatches']),
    'counts': r['counts'],
    'expected': r['expected'],
    'bound_files_sha256': {Path(k).name: v for k, v in r['bound_files_sha256'].items()},
    'runner': 'tools/run_suites.py (pump-hi runner) via tools/rt.py; REPO/work/test-env/bin/python (3.12, solders 0.27.1)',
}
assert all(summary['counts'][k] == summary['expected'][k] for k in summary['counts'])
dst.write_text(json.dumps(summary, indent=1) + '\n')
print(json.dumps({k: summary[k] for k in ('suites', 'case_count', 'expected_cases', 'diagnostic_log_cases', 'diagnostic_mismatches')},
                 ) + f" errors={len(summary['errors'])}")
