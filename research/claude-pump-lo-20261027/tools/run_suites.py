#!/usr/bin/env python3
"""Run selected frontier differential suites (original vs candidate) via the captured loader.
Mirrors scripts/pump_validate_parallel.py run_suite + validate_result; adds diagnostic audit.
usage: run_suites.py <wt> <candidate.so> <outdir> <workers> suite [suite...] | all"""
import sys, json, gzip, hashlib, subprocess, tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
ROOT = Path(sys.argv[1]).resolve(); cand = Path(sys.argv[2]).resolve(); out = Path(sys.argv[3]).resolve(); workers = int(sys.argv[4]); names = sys.argv[5:]
sys.path.insert(0, str(ROOT / 'scripts'))
import pump_validate_all as base
import pump_validate_parallel as par
from pump_diagnostic_audit import audit
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
suites = dict(base.SUITES)
if names == ['all']: names = list(suites)
orig = ROOT / 'evidence/original/pump/deployed.so'
out.mkdir(parents=True, exist_ok=True)
def run(name):
    try:
        return _run(name)
    except Exception as e:
        return name, None, 'ERROR %r' % (e,)
def _run(name):
    script = ROOT / suites[name] if suites[name].startswith('repro/') else ROOT / 'scripts' / suites[name]
    if name == 'tokenkeg_two_curve': return name, None, 'skipped (needs build-binding report)'
    with tempfile.TemporaryDirectory(prefix='pl-' + name + '-') as tmp:
        o = Path(tmp) / 'result.json'; rec = out / (name + '.loader.json')
        cmd = [sys.executable, str(ROOT / 'scripts/pump_with_captured_loader.py'), '--receipt', str(rec), str(script), '--candidate', str(cand), '--output', str(o)]
        src = script.read_text()
        if "'--source-directory'" in src or '"--source-directory"' in src:
            cmd += ['--source-directory', str(ROOT / 'programs/pump')]
        cp = subprocess.run(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        (out / (name + '.log')).write_text(cp.stdout)
        if cp.returncode: return name, None, 'FAILED rc=%d' % cp.returncode
        raw = o.read_bytes(); res = json.loads(gzip.decompress(raw) if raw[:2] == b'\x1f\x8b' else raw)
    (out / (name + '.json.gz')).write_bytes(gzip.compress(json.dumps(res, separators=(',', ':')).encode(), mtime=0))
    try:
        count = par.validate_result(name, res, cand, orig)
    except AssertionError as e:
        return name, res, 'VALIDATION FAILED %r' % (e,)
    loads = json.loads(rec.read_text())['loads']
    elfs = {x['elf_sha256'] for x in loads}
    ok = elfs == {sha(cand), sha(orig)} and all(x['program_bytes'] == 36 and x['programdata_bytes'] == 10485760 and x['elf_prefix_unchanged'] and x['zero_allocation_tail'] for x in loads)
    return name, res, 'ok cases=%d loads=%d loader_ok=%s' % (count, len(loads), ok)
results = {}; summary = {}
with ThreadPoolExecutor(workers) as ex:
    futs = [ex.submit(run, n) for n in names]
    for f in as_completed(futs):
        n, res, status = f.result(); print(n, status, flush=True); summary[n] = {'status': status}
        if res is not None: results[n] = res
a = audit(results) if results else {}
summary_out = {'candidate_sha256': sha(cand), 'original_sha256': sha(orig), 'suites': summary,
               'total_cases': sum(int(s['status'].split('cases=')[1].split()[0]) for s in summary.values() if 'cases=' in s['status']),
               'diagnostic_audit': {k: (v if not isinstance(v, (list, dict)) else len(v)) for k, v in a.items() if k != 'scope'}}
(out / 'SUMMARY.json').write_text(json.dumps(summary_out, indent=1) + '\n')
print(json.dumps(summary_out, indent=1))
