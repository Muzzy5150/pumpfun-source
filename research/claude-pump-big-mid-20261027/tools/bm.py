#!/usr/bin/env python3
"""pump-big-mid lane helper around the Pump session's read-only harness (claude-pump-work/harness).

  bm.py build <src crate dir> <label> [--ir] [--rustc-arg ARG ...] [--work DIR]
      Faithful identity-recipe build (harness fastbuild.build, which takes a slot of the shared
      6-slot build pool in claude-pump-work/locks), then score.py against the g04 baseline.
      Writes OUT/<label>/{unstripped.so,candidate.so,build.log,score.json[,pump.ll]}.
      --ir / --rustc-arg add rustc arguments for the pump_recovered crate only (deps untouched);
      such builds use a separate persistent target dir (target-ir) so the main one stays clean.
  bm.py score <unstripped.so> [--json out.json]
      Score only (g04 baseline), printing gains/losses and the status of the big-mid windows.
"""
import argparse, json, os, shutil, subprocess, sys
from pathlib import Path

CPW = Path('/Users/shawwalters/Documents/Codex/2026-10-24/claude-pump-work')
HARNESS = CPW / 'harness'
BASELINE = CPW / 'base/g04/inventory.json'
TARGETS = CPW / 'targets/big-mid.json'
LANE = Path(os.environ.get('BM_LANE', '/private/tmp/claude-501/-Users-shawwalters-Documents-Codex-2026-10-24-pumpfun-source/'
                           'bf960843-6806-451b-a211-62c8b228d301/scratchpad/lanes/pump-big-mid'))
OUT = LANE / 'out'
WRAPPER_DIR = Path(__file__).resolve().parent / 'wrapper'
sys.path.insert(0, str(HARNESS))


def big_mid():
    return [int(w['start'], 16) for w in json.loads(TARGETS.read_text())['windows']]


def do_score(so, js=None):
    cmd = [sys.executable, '-B', str(HARNESS / 'score.py'), str(so), '--baseline', str(BASELINE), '--quiet']
    if js:
        cmd += ['--json', str(js)]
    r = subprocess.run(cmd, capture_output=True, text=True, check=True)
    summ = json.loads(r.stdout)
    mine = {}
    if js:
        w = json.loads(Path(js).read_text())['windows']
        mine = {hex(s): w[str(s)]['normalized'] for s in big_mid()}
    return summ, mine


def report(summ, mine):
    print(f"normalized={summ['normalized']} raw={summ['raw']} (g04 = 806/165)  beyond806={summ['normalized'] - 806}")
    for k in ('gains', 'losses', 'raw_gains', 'raw_losses'):
        print(f"  {k}: {summ[k]}")
    if mine:
        print('  big-mid matched:', [k for k, v in mine.items() if v])


def build(src, label, ir=False, rustc_args=(), work=None):
    import fastbuild
    extra = list(rustc_args)
    if ir:
        extra.append('--emit=llvm-ir')
    work = Path(work) if work else LANE / ('target-ir' if extra else 'target')
    out = OUT / label
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    if extra:
        os.environ['BM_EXTRA_RUSTC_ARGS'] = json.dumps(extra)
        fastbuild.H = WRAPPER_DIR  # only used for the RUSTC_WRAPPER path inside build()
        for ll in (work / 'target-identity').glob('sbpf-solana-solana/release/deps/pump_recovered*.ll'):
            ll.unlink()
    res = fastbuild.build(Path(src), work, out, quiet=True)
    if extra:
        for ll in (work / 'target-identity').glob('sbpf-solana-solana/release/deps/pump_recovered*.ll'):
            shutil.move(str(ll), str(out / 'pump.ll'))
    res['extra_rustc_args'] = extra
    if res['ok']:
        summ, mine = do_score(out / 'unstripped.so', out / 'score.json')
        res['score'] = summ
        res['big_mid'] = mine
    (out / 'result.json').write_text(json.dumps(res, indent=1))
    if not res['ok']:
        log = (out / 'build.log').read_text()
        errs = [i for i, l in enumerate(log.splitlines()) if l.startswith('error')]
        lines = log.splitlines()
        for i in errs[:6]:
            print('\n'.join(lines[i:i + 14]))
        print('BUILD FAILED', res['log'])
        return res
    print(f"[{label}] {res['seconds']}s runtime_valid={res['runtime_valid']} unstripped={res['unstripped_sha256'][:16]}")
    for s in res['stack_warnings']:
        print('  STACK:', s)
    report(res['score'], res['big_mid'])
    return res


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('build'); p.add_argument('src'); p.add_argument('label'); p.add_argument('--ir', action='store_true')
    p.add_argument('--rustc-arg', action='append', default=[]); p.add_argument('--work')
    p = sub.add_parser('score'); p.add_argument('so'); p.add_argument('--json')
    a = ap.parse_args()
    if a.cmd == 'build':
        r = build(a.src, a.label, a.ir, a.rustc_arg, a.work)
        sys.exit(0 if r['ok'] else 1)
    else:
        report(*do_score(a.so, a.json))
