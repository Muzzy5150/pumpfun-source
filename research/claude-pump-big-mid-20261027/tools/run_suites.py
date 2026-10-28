#!/usr/bin/env python3
"""Run selected suites of the public 44-suite main-Pump differential corpus.

(Copied unchanged in behaviour from research/claude-pump-hi-20261027/tools/run_suites.py, lane pump-hi.)

Mirrors scripts/pump_validate_parallel.py exactly per suite (captured upgradeable
loader wrapper, unchanged harness scripts, the same result validation and the same
paired-diagnostic audit), but lets the caller choose a subset of suites. The output
is a gzip JSON report with per-suite results, loader receipts and the audit.

Run with REPO/work/test-env/bin/python and PYTHONDONTWRITEBYTECODE=1.
"""
import argparse, gzip, hashlib, json, subprocess, sys, tempfile, traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = next(p for p in HERE.parents if (p / 'evidence/original/pump/deployed.so').is_file())
sys.path.insert(0, str(ROOT / 'scripts'))
import pump_validate_all as base  # noqa: E402
import pump_validate_parallel as par  # noqa: E402
from pump_diagnostic_audit import audit  # noqa: E402
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--candidate', type=Path, required=True)
    ap.add_argument('--build-comparison', type=Path, required=True)
    ap.add_argument('--suites', required=True, help="comma list of suite names or 'all'")
    ap.add_argument('--workers', type=int, default=2)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    names = [n for n, _ in base.SUITES] if a.suites == 'all' else a.suites.split(',')
    table = dict(base.SUITES)
    assert all(n in table for n in names), [n for n in names if n not in table]
    candidate = a.candidate.resolve()
    original = ROOT / 'evidence/original/pump/deployed.so'
    record = json.loads(a.build_comparison.read_text())
    assert record['returncode'] == 0 and record['source_unchanged']
    assert record['comparison']['candidate_sha256'] == sha(candidate)
    source_dir = Path(record['source_directory'])
    wrapper = ROOT / 'scripts/pump_with_captured_loader.py'
    out = a.output.resolve()
    retained = out.parent / (out.name + '.suites')
    retained.mkdir(parents=True, exist_ok=True)
    scripts = {n: (ROOT / table[n] if table[n].startswith('repro/') else ROOT / 'scripts' / table[n]) for n in names}
    bound = {str(p): sha(p) for p in [candidate, original, wrapper, wrapper.with_name('pump_captured_loader.py'),
                                       Path(par.__file__), Path(base.__file__), ROOT / 'scripts/pump_diagnostic_audit.py',
                                       *scripts.values()]}

    def run(name):
        script = scripts[name]
        with tempfile.TemporaryDirectory(prefix='pumphi-suite-' + name + '-') as tmp:
            output = Path(tmp) / 'result.json'
            receipt = retained / (name + '.loader.json')
            cmd = [sys.executable, str(wrapper), '--receipt', str(receipt), str(script), '--candidate', str(candidate), '--output', str(output)]
            text = script.read_text()
            if "'--source-directory'" in text or '"--source-directory"' in text:
                cmd += ['--source-directory', str(source_dir)]
            if name == 'tokenkeg_two_curve':
                cmd += ['--build-report', str(a.build_comparison.resolve())]
                if '--source-directory' not in cmd:
                    cmd += ['--source-directory', str(source_dir)]
            done = subprocess.run(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            (retained / (name + '.log')).write_text(done.stdout)
            done.check_returncode()
            raw = output.read_bytes()
            result = json.loads(gzip.decompress(raw) if raw[:2] == b'\x1f\x8b' else raw)
        count = par.validate_result(name, result, candidate, original)
        loaded = json.loads(receipt.read_text())
        assert {r['elf_sha256'] for r in loaded['loads']} == {sha(candidate), sha(original)}, name
        assert all(r['program_bytes'] == 36 and r['programdata_bytes'] == 10485760 and r['elf_prefix_unchanged'] and r['zero_allocation_tail'] for r in loaded['loads']), name
        result['case_count'] = count
        (retained / (name + '.json.gz')).write_bytes(gzip.compress(json.dumps(result, separators=(',', ':')).encode(), mtime=0))
        return name, count, result

    suites, counts, errors = {}, {}, []
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        jobs = {ex.submit(run, n): n for n in sorted(names, key=lambda n: -base.EXPECTED_CASES[n])}
        for f in as_completed(jobs):
            try:
                n, c, r = f.result()
                suites[n], counts[n] = r, c
                print(json.dumps({'completed': n, 'cases': c, 'done': len(suites), 'of': len(names)}), flush=True)
            except Exception as exc:  # retain and report
                errors.append({'suite': jobs[f], 'error': repr(exc), 'traceback': traceback.format_exc()})
                print(json.dumps({'failed': jobs[f], 'error': repr(exc)}), flush=True)
    assert all(sha(Path(p)) == d for p, d in bound.items()), 'bound input changed during run'
    diagnostics = audit(suites) if suites else {'mismatches': [], 'log_bearing_cases': 0}
    report = {'scope': __doc__, 'candidate_sha256': sha(candidate), 'original_sha256': sha(original),
              'bound_files_sha256': bound, 'compiled_source_sha256': record['source_sha256'],
              'suites_requested': names, 'case_count': sum(counts.values()), 'counts': counts,
              'expected': {n: base.EXPECTED_CASES[n] for n in names}, 'errors': errors,
              'diagnostics': diagnostics, 'mismatches': diagnostics['mismatches'], 'suites': suites}
    out.write_bytes(gzip.compress(json.dumps(report, separators=(',', ':')).encode(), mtime=0))
    print(json.dumps({'case_count': report['case_count'], 'suites': len(suites), 'errors': len(errors),
                      'diagnostic_log_cases': diagnostics['log_bearing_cases'],
                      'diagnostic_mismatches': len(diagnostics['mismatches'])}))
    return 1 if errors or diagnostics['mismatches'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
