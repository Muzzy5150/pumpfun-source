#!/usr/bin/env python3
"""Signed local legacy-migration probes for boolean decoder group boundaries."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import pump_migrate_v2_probe as fixture


def cases():
    cases=[]
    # Inclusive wire-size gates: prior versions ignore bytes beyond the last
    # complete historical layout; the next version decodes bool strictly.
    for off, first_size in [(81,82),(82,83),(123,124),(124,125)]:
        for size in [first_size-1, first_size, 166]:
            for value in [2,255]:
                cases.append({'name': f'bool-{off}-size-{size}-value-{value}', 'boost': True,
                    'mutations': {'bonding_curve': {'length': size, 'patches': [(off,bytes([value]).hex())]}}})
    return cases


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--candidate', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    paths = [Path(__file__).resolve(), Path(fixture.__file__).resolve(), a.candidate.resolve(), ROOT / 'evidence/original/pump/deployed.so']
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {str(p): sha(p) for p in paths}
    rows = []
    for c in cases():
        x, y = fixture.run(c), fixture.run(c, a.candidate)
        for value in [x, y]:
            value['events'] = [line for line in value['logs'] if line.startswith('Program data:')]
        diff = [key for key in ['error', 'before', 'after', 'inner', 'return', 'events'] if x[key] != y[key]]
        rows.append({'case': c, 'original': x, 'candidate': y, 'different_fields': diff})
        if diff:
            print(c['name'], diff, flush=True)
    assert before == {str(p): sha(p) for p in paths}
    result = {'scope': 'Normally signed offline migration with synthetic truncated curve data; original immutable main and captured dependencies are the oracle.', 'inputs_sha256': before, 'candidate_sha256': sha(a.candidate), 'original_sha256': sha(ROOT / 'evidence/original/pump/deployed.so'), 'case_count': len(rows), 'cases': rows, 'mismatches': [r['case']['name'] for r in rows if r['different_fields']]}
    a.output.write_text(json.dumps(result, indent=2) + '\n')
    print('cases', len(rows), 'mismatches', len(result['mismatches']))
    return bool(result['mismatches'])


if __name__ == '__main__':
    raise SystemExit(main())
