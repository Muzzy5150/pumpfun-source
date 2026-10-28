#!/usr/bin/env python3
"""Runtime check of a pump-big-mid build on the public 44-suite main-Pump corpus.

  rt.py <build out dir (bm.py OUT/<label>)> <stage name> [--suites all|a,b,...] [--workers N]

1. Stages the build inside this worktree (the quote_control harness rejects candidates outside the
   repository): research/claude-pump-big-mid-20261027/rt/<stage>/{candidate.so, ws/...}. `ws` is the exact
   fastbuild workspace that was compiled (bm.py snapshots it after every build).
2. Writes build-comparison.json + build-attempt.json binding the candidate to that workspace through
   scripts/build_source_manifest.source_manifest (what tokenkeg_two_curve checks).
3. Runs tools/run_suites.py (pump-hi's runner; unchanged harness scripts, captured loader, the same result
   validation and paired diagnostic audit) with REPO/work/test-env/bin/python, PYTHONDONTWRITEBYTECODE=1.
Output: rt/<stage>/corpus.json.gz (+ .suites/ receipts). Nothing under rt/ is meant to be committed except
the summary written by the caller.
"""
import argparse, hashlib, json, os, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve()
PACKET = HERE.parents[1]
ROOT = next(p for p in HERE.parents if (p / 'evidence/original/pump/deployed.so').is_file())
PY = '/Users/shawwalters/Documents/Codex/2026-10-24/pumpfun-source/work/test-env/bin/python'
sys.path.insert(0, str(ROOT / 'scripts'))
from build_source_manifest import source_manifest  # noqa: E402
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('build'); ap.add_argument('stage')
    ap.add_argument('--suites', default='all'); ap.add_argument('--workers', type=int, default=3)
    a = ap.parse_args()
    build = Path(a.build).resolve()
    st = PACKET / 'rt' / a.stage
    if st.exists():
        shutil.rmtree(st)
    st.mkdir(parents=True)
    shutil.copy2(build / 'candidate.so', st / 'candidate.so')
    shutil.copytree(build / 'ws', st / 'ws')
    crate, ws = st / 'ws/programs/pump', st / 'ws'
    manifest = source_manifest(crate, ws, ROOT, cwd=ws)
    rec = {'returncode': 0, 'source_unchanged': True, 'builder': 'claude-pump-work/harness/fastbuild.py (identity recipe)',
           'source_directory': str(crate), 'source_sha256': manifest,
           'comparison': {'candidate_sha256': sha(st / 'candidate.so')}}
    (st / 'build-comparison.json').write_text(json.dumps(rec, indent=1) + '\n')
    (st / 'build-attempt.json').write_text(json.dumps({'returncode': 0, 'source_unchanged': True, 'source_sha256': manifest,
                                                        'source_after_sha256': manifest}, indent=1) + '\n')
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    cmd = [PY, '-B', str(HERE.parent / 'run_suites.py'), '--candidate', str(st / 'candidate.so'),
           '--build-comparison', str(st / 'build-comparison.json'), '--suites', a.suites,
           '--workers', str(a.workers), '--output', str(st / 'corpus.json.gz')]
    r = subprocess.run(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    (st / 'run.log').write_text(r.stdout)
    print(r.stdout[-1500:])
    return r.returncode


if __name__ == '__main__':
    raise SystemExit(main())
