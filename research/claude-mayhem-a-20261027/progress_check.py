#!/usr/bin/env python3
"""Run the parent packet's own progress.compare() (unchanged code) on a candidate.

compare() asserts that no baseline raw/normalized match, positive direct-call
edge, positive Source record or observed Source profile is lost.

usage: progress_check.py CANDIDATE_SYMBOLS.so[.gz] [--baseline SYMBOLS.so[.gz]] [--json OUT]
"""
import argparse, gzip, importlib.util, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

def data(p):
    p = Path(p); b = p.read_bytes()
    return gzip.decompress(b) if p.suffix == '.gz' else b

ap = argparse.ArgumentParser()
ap.add_argument('candidate')
ap.add_argument('--baseline', default=str(ROOT / 'research/mayhem-sizing-panic-recovery/artifacts/recovered/symbols.so.gz'))
ap.add_argument('--json')
a = ap.parse_args()
spec = importlib.util.spec_from_file_location('parent_progress', ROOT / 'research/mayhem-trade-origins-validator/progress.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
res = m.compare((ROOT / 'evidence/original/mayhem/deployed.so').read_bytes(), data(a.baseline), data(a.candidate))
print(json.dumps({k: v for k, v in res.items() if k != 'scope'}, indent=1))
if a.json:
    Path(a.json).write_text(json.dumps(res, indent=1) + '\n')
