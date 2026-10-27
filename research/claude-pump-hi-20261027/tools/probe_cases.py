#!/usr/bin/env python3
"""Re-run selected cases of a public differential fixture and print what differs.

  python tools/probe_cases.py --fixture pump_migrate_v2_differential --candidate X.so \
      --indices 0,1,3 [--candidate2 Y.so]

Runs under the captured main-program loader, like scripts/pump_with_captured_loader.py.
With --candidate2, compares the two candidates against each other as well (used for
same-recipe controls). Only the fields the fixture itself compares are reported.
"""
import argparse, importlib, json, sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'evidence/original/pump/deployed.so').is_file())
sys.path.insert(0, str(ROOT / 'scripts'))
import pump_captured_loader as loader  # noqa: E402

FIELDS = ['error', 'before', 'after', 'events', 'inner', 'return']


def short(v, n=600):
    s = json.dumps(v, sort_keys=True, default=str)
    return s if len(s) <= n else s[:n] + '...'


def first_diff(a, b, path=''):
    if type(a) != type(b):
        return path, a, b
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b), key=str):
            if a.get(k) != b.get(k):
                return first_diff(a.get(k), b.get(k), f'{path}.{k}')
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            for i, (x, y) in enumerate(zip(a, b)):
                if x != y:
                    return first_diff(x, y, f'{path}[{i}]')
            return f'{path}.len', len(a), len(b)
        for i, (x, y) in enumerate(zip(a, b)):
            if x != y:
                return first_diff(x, y, f'{path}[{i}]')
        return None
    return (path, a, b) if a != b else None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--fixture', required=True)
    ap.add_argument('--candidate', type=Path, required=True)
    ap.add_argument('--candidate2', type=Path)
    ap.add_argument('--indices', required=True)
    a = ap.parse_args()
    loader.install()
    fx = importlib.import_module(a.fixture)
    p = fx.p
    for i in [int(x) for x in a.indices.split(',')]:
        c = fx.cases[i]
        runs = {'original': p.run(c), 'candidate': p.run(c, a.candidate)}
        if a.candidate2:
            runs['candidate2'] = p.run(c, a.candidate2)
        for r in runs.values():
            r['events'] = [l for l in r['logs'] if l.startswith('Program data:')]
        print(f'== case {i}: {short(c, 300)}')
        for name in [n for n in runs if n != 'original']:
            diff = [k for k in FIELDS if runs['original'][k] != runs[name][k]]
            print(f'  {name}: differs in {diff}')
            for k in diff:
                print(f'    {k}: first difference {short(first_diff(runs["original"][k], runs[name][k]))}')
        if a.candidate2:
            diff = [k for k in FIELDS if runs['candidate'][k] != runs['candidate2'][k]]
            print(f'  candidate vs candidate2: differs in {diff}')
        sys.stdout.flush()


if __name__ == '__main__':
    main()
