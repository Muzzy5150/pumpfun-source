"""Run selected published main-Pump differential suites (original vs candidate) under the
captured upgradeable loader, then apply the frontier's acceptance checks
(expected case counts, no mismatches) and the paired diagnostic-log audit."""
import argparse, gzip, json, subprocess, sys, hashlib, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
WT = next(p for p in Path(__file__).resolve().parents if (p / 'evidence/original/pump/deployed.so').is_file())
PY = sys.executable  # run this tool with the repo's test-env Python (3.12 + solders 0.27.1)
sys.path.insert(0, str(WT / 'scripts'))
import importlib.util
spec = importlib.util.spec_from_file_location('vc', WT / 'repro/pump/main-contract-round26-20261027/inputs/work/parallel-main-integration/validate_combined.py')
vc = importlib.util.module_from_spec(spec); spec.loader.exec_module(vc)
SUITES = dict(vc.SUITES); EXPECTED = vc.EXPECTED_CASES
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
ap = argparse.ArgumentParser(); ap.add_argument('--candidate', type=Path, required=True); ap.add_argument('--out', type=Path, required=True)
ap.add_argument('--workers', type=int, default=3); ap.add_argument('--source-directory', type=Path); ap.add_argument('suites', nargs='+')
a = ap.parse_args(); a.out = a.out.resolve(); a.out.mkdir(parents=True, exist_ok=True)
cand = a.candidate.resolve(); orig = WT / 'evidence/original/pump/deployed.so'
def run(name):
    if '=' in name:
        name, fn = name.split('=', 1)
        SUITES[name] = fn
    fn = SUITES[name]; script = WT / fn if fn.startswith('repro/') else WT / 'scripts' / fn
    out = a.out / f'{name}.json'; t = time.time()
    cmd = [PY, str(WT / 'scripts/pump_with_captured_loader.py'), '--receipt', str(a.out / f'{name}.loader.json'), str(script), '--candidate', str(cand), '--output', str(out)]
    txt = script.read_text()
    if a.source_directory and ("'--source-directory'" in txt or '"--source-directory"' in txt):
        cmd += ['--source-directory', str(a.source_directory.resolve())]
    r = subprocess.run(cmd, cwd=WT, capture_output=True, text=True)
    if r.returncode: return name, {'error': r.stderr[-2000:], 'seconds': time.time() - t}
    raw = out.read_bytes(); res = json.loads(gzip.decompress(raw) if raw[:2] == b'\x1f\x8b' else raw)
    try:
        if name == 'quote_control':
            count = res['cases']; assert count == len(res['results']); assert all(x['matches'] and not x['different_fields'] for x in res['results'])
        elif name == 'multi_hop_curve_partial':
            count = res['case_count']; assert res['passed'] == count and all(not x['mismatches'] for x in res['cases'])
        elif name == 'tokenkeg_two_curve':
            count = vc.validate_two_curve(res, sha(cand), sha(orig))
        else:
            count = res['case_count'] if 'case_count' in res else len(res['cases'])
            assert not res.get('mismatches', res.get('failures', []))
        if name in EXPECTED: assert count == EXPECTED[name], (count, EXPECTED[name])
        else: assert count and count > 0
        def walk(x):
            if isinstance(x, dict):
                for k, v in x.items():
                    if k in ('different_fields', 'differences', 'mismatches'): assert not v, (k, str(v)[:300])
                    else: walk(v)
            elif isinstance(x, list):
                for y in x: walk(y)
        walk(res)
        ok = True; err = None
    except AssertionError as e:
        ok = False; err = repr(e); count = None
    return name, {'ok': ok, 'cases': count, 'error': err, 'seconds': round(time.time() - t, 1), 'output_sha256': sha(out)}
with ThreadPoolExecutor(a.workers) as ex:
    results = dict(ex.map(run, a.suites))
summary = {'candidate': str(cand), 'candidate_sha256': sha(cand), 'original_sha256': sha(orig), 'suites': results,
           'total_cases': sum(v.get('cases') or 0 for v in results.values()), 'all_ok': all(v.get('ok') for v in results.values())}
try:
    from pump_diagnostic_audit import audit
    loaded = {}
    for n in [x.split('=')[0] for x in a.suites]:
        p = a.out / f'{n}.json'
        if p.exists():
            raw = p.read_bytes(); loaded[n] = json.loads(gzip.decompress(raw) if raw[:2] == b'\x1f\x8b' else raw)
    au = audit(loaded); summary['diagnostic_audit'] = {'log_bearing_cases': au['log_bearing_cases'], 'mismatches': len(au['mismatches'])}
except Exception as e:
    summary['diagnostic_audit'] = {'error': repr(e)}
(a.out / 'SUMMARY.json').write_text(json.dumps(summary, indent=1))
print(json.dumps({k: v for k, v in summary.items() if k != 'suites'}), json.dumps({k: (v.get('ok'), v.get('cases'), v.get('seconds')) for k, v in results.items()}))
