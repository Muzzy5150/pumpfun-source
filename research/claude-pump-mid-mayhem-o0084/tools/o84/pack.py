#!/usr/bin/env python3
"""usage: pack.py LABEL TRADES_DIR -- refresh the O0084 packet in the lane worktree from build LABEL (root o84/roots/LABEL).

Writes source.patch (vs mayhem-env/parent-434), artifacts/ (gzipped ELFs, SHA256SUMS, launch/result/stderr,
stack-offset count), measure/measure-LABEL-vs-434.json, runtime/ (summary + per-suite SHA256SUMS), CLAIM.json.
"""
import gzip, hashlib, json, os, shutil, subprocess, sys
from pathlib import Path
MW = Path('/Users/shawwalters/Documents/Codex/2026-10-24/claude-mayhem-work')
WT = Path('/private/tmp/claude-501/-Users-shawwalters-Documents-Codex-2026-10-24-pumpfun-source/bf960843-6806-451b-a211-62c8b228d301/scratchpad/lanes/pump-mid/wt')
PK = WT / 'research/claude-pump-mid-mayhem-o0084'
PY = '/Users/shawwalters/Documents/Codex/2026-10-24/pumpfun-source/work/test-env/bin/python'
label, trades = sys.argv[1], Path(sys.argv[2])
B = MW / 'mayhem-b/out/builds' / label
root = MW / 'o84/roots' / label
F = 'programs/mayhem/src/instructions/pump_interface_v2.rs'
sha = lambda b: hashlib.sha256(b).hexdigest()
# source.patch
d = subprocess.run(['diff', '-u', '--label', 'a/' + F, '--label', 'b/' + F, str(MW / 'mayhem-env/parent-434' / F), str(root / F)],
                   capture_output=True, text=True)
assert d.returncode == 1, d.stderr
(PK / 'source.patch').write_text(d.stdout)
# every other source input must equal parent-434
r = subprocess.run(['diff', '-rq', '-x', 'pump_interface_v2.rs', str(MW / 'mayhem-env/parent-434/programs'), str(root / 'programs')], capture_output=True, text=True)
assert r.returncode == 0 and not r.stdout, r.stdout
# artifacts
A = PK / 'artifacts'
stderr = (B / 'stderr').read_bytes()
nstack = stderr.count(b'Stack offset')
assert nstack == 0, 'Stack offset warning'
cand = (B / 'candidate.so').read_bytes(); syms = (B / 'symbols.so').read_bytes()
(A / 'candidate.so.gz').write_bytes(gzip.compress(cand, mtime=0))
(A / 'symbols.so.gz').write_bytes(gzip.compress(syms, mtime=0))
(A / 'SHA256SUMS').write_text(f'{sha(cand)}  candidate.so\n{sha(syms)}  symbols.so\n')
shutil.copyfile(B / 'launch.json', A / 'build-launch.json')
shutil.copyfile(B / 'result.json', A / 'build-result.json')
(A / 'build-stderr.gz').write_bytes(gzip.compress(stderr, mtime=0))
(A / 'stack-offset-warnings.txt').write_text(f'{nstack}\n')
# measure
M = PK / 'measure' / f'measure-{label.replace("o84-", "")}-vs-434.json'
subprocess.run([PY, '-B', str(MW / 'mayhem-b/build/measure.py'), str(B / 'symbols.so'), str(MW / 'mayhem-b/out/builds/pm-o84-b434/symbols.so'), '--json', str(M)], check=True, capture_output=True)
mj = json.loads(M.read_text())
assert mj['no_losses'] and mj['counts']['matched_after'] >= 434 and mj['counts']['raw_after'] >= 100
# runtime
s = json.loads((trades / 'summary.json').read_text())
assert s['all_ok'] and s['total_mismatches'] == 0 and s['total_noncompute_log_diffs'] == 0 and s['total_cases'] == 6636
assert sha(Path(s['candidate']).read_bytes()) == sha(cand), s['candidate']  # suites ran on byte-identical candidate
(PK / 'runtime/trades-summary.json').write_text(json.dumps(s, indent=2) + '\n')
lines = [f'{sha(p.read_bytes())}  {p.name}' for p in sorted(trades.glob('*.json')) if p.name != 'summary.json']
assert len(lines) == 14
(PK / 'runtime/suite-output-SHA256SUMS').write_text('\n'.join(lines) + '\n')
# claim
claim = json.loads((PK / 'CLAIM.json').read_text())
sell = None
sys.path.insert(0, str(MW / 'o84/tools')); import irx
code = irx.elf_code(str(B / 'symbols.so'))
claim.update(candidate_sha256=sha(cand), symbols_sha256=sha(syms), source_patch_sha256=sha((PK / 'source.patch').read_bytes()),
             matched=mj['counts']['matched_after'], raw=mj['counts']['raw_after'], unmatched=sorted(mj['unmatched_ids']),
             sell_v2_handler_bytes=[len(code)])
(PK / 'CLAIM.json').write_text(json.dumps(claim, indent=1) + '\n')
print(json.dumps({'label': label, 'candidate': sha(cand), 'symbols': sha(syms), 'bytes': len(code), 'score': irx.score(code),
                  'matched': claim['matched'], 'raw': claim['raw'], 'measure': M.name}))
