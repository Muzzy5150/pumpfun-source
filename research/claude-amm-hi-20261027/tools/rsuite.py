#!/usr/bin/env python3
"""Run the 25 maintained AMM differential suites (original vs candidate) directly.

Same harness commands and expected case counts as the frontier replay_parallel.py
(repro/pump_amm/pool-serialization-thirty-seven/replay-commands.json and summary.json);
the signature-observer wrapper is omitted. Each harness compares the original and the
candidate per case (state, errors, events, inner instructions, return data).
"""
import argparse, concurrent.futures, hashlib, json, subprocess, sys, time
from pathlib import Path
LANE = Path('/private/tmp/claude-501/-Users-shawwalters-Documents-Codex-2026-10-24-pumpfun-source/bf960843-6806-451b-a211-62c8b228d301/scratchpad/lanes/amm-hi')
WT = LANE / 'wt'
PY = '/Users/shawwalters/Documents/Codex/2026-10-24/pumpfun-source/work/test-env/bin/python'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
ap = argparse.ArgumentParser(); ap.add_argument('--candidate', type=Path, required=True); ap.add_argument('--output', type=Path, required=True)
ap.add_argument('--suites', default=''); ap.add_argument('--workers', type=int, default=4)
a = ap.parse_args(); cand = a.candidate.resolve(); out = a.output.resolve(); out.mkdir(parents=True, exist_ok=False)
specs = json.loads((LANE / 'out/runtime/replay-commands.json').read_text())['commands']
counts = json.loads((LANE / 'out/runtime/suite-summary.json').read_text())['suites']
want = set(a.suites.split(',')) if a.suites else None
specs = [s for s in specs if not want or s['suite'] in want]
specs.sort(key=lambda s: counts[s['suite']], reverse=True)
def run(spec):
    name = spec['suite']; cmd = list(spec['command']); cmd[0] = PY; cmd[1] = str(WT / cmd[1])
    cmd[cmd.index('--candidate') + 1] = str(cand); receipt = out / (name + '.json'); cmd[cmd.index('--output') + 1] = str(receipt)
    t0 = time.monotonic()
    with (out / (name + '.log')).open('w') as log:
        rc = subprocess.run(cmd, cwd=WT, stdout=log, stderr=subprocess.STDOUT).returncode
    row = {'suite': name, 'returncode': rc, 'seconds': round(time.monotonic() - t0, 1), 'expected_cases': counts[name]}
    if receipt.exists():
        d = json.loads(receipt.read_text())
        row.update(case_count=d.get('case_count'), mismatches=len(d.get('mismatches', [])), candidate_sha256=d.get('candidate_sha256'),
                   original_sha256=d.get('original_sha256'), receipt_sha256=sha(receipt))
    print(json.dumps(row), flush=True); return row
rows = []
with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:
    for f in concurrent.futures.as_completed([ex.submit(run, s) for s in specs]): rows.append(f.result())
ok = all(r['returncode'] == 0 and r.get('case_count') == r['expected_cases'] and r.get('mismatches') == 0 and r.get('candidate_sha256') == sha(cand) for r in rows)
summary = {'candidate_sha256': sha(cand), 'suites': len(rows), 'cases': sum(r.get('case_count') or 0 for r in rows),
           'mismatches': sum(r.get('mismatches') or 0 for r in rows), 'all_pass': ok, 'rows': sorted(rows, key=lambda r: r['suite']),
           'scope': __doc__}
(out / 'summary.json').write_text(json.dumps(summary, indent=1) + '\n')
print(json.dumps({k: summary[k] for k in ('candidate_sha256', 'suites', 'cases', 'mismatches', 'all_pass')}))
