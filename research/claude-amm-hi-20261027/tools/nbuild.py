#!/usr/bin/env python3
"""Native macOS v1.44 SBPF build of a pump-amm source tree via the frontier workspace recipe.

usage: nbuild.py --src <root containing programs/pump-amm> --tag <name> [--jobs N]
Stages the explicit workspace into ws/iter (rsync --checksum so unchanged files keep
mtimes), builds under the shared sbf lock, strips with v1.52 llvm-objcopy and
measures with the repo's focused-diagnostics measure.py.
"""
import argparse, hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path
LANE = Path('/private/tmp/claude-501/-Users-shawwalters-Documents-Codex-2026-10-24-pumpfun-source/bf960843-6806-451b-a211-62c8b228d301/scratchpad/lanes/amm-hi')
SP = LANE.parent.parent
WT = LANE / 'wt'
FRONT = WT / 'repro/pump_amm/account-context-recovery-20261027'
TC = Path.home() / '.cache/solana/v1.44/platform-tools'
STRIP = Path.home() / '.cache/solana/v1.52/platform-tools/llvm/bin/llvm-objcopy'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', type=Path, default=WT)
    ap.add_argument('--tag', required=True)
    ap.add_argument('--jobs', default='4')
    ap.add_argument('--ws', type=Path, default=LANE / 'ws/iter')
    ap.add_argument('--target', type=Path, default=LANE / 'target/native')
    ap.add_argument('--no-measure', action='store_true')
    ap.add_argument('--env', action='append', default=[], help='extra KEY=VALUE for cargo')
    a = ap.parse_args()
    a.src = a.src.resolve()
    out = LANE / 'out/builds' / a.tag
    assert not out.exists(), out
    out.mkdir(parents=True)
    stage = LANE / 'ws' / ('stage-' + a.tag)
    if stage.exists(): shutil.rmtree(stage)
    r = subprocess.run([sys.executable, str(FRONT / 'workspace_recipe_v2.py'), 'stage', '--source-root', str(a.src), '--output', str(stage)],
                       capture_output=True, text=True, cwd=str(WT))
    (out / 'stage.json').write_text(r.stdout + r.stderr)
    r.check_returncode()
    a.ws.mkdir(parents=True, exist_ok=True)
    subprocess.run(['rsync', '-a', '--checksum', '--delete', '--exclude', 'target', str(stage) + '/', str(a.ws) + '/'], check=True)
    shutil.rmtree(stage)
    now = time.time()
    for f in (a.ws / 'programs').rglob('*'):
        if f.is_file(): os.utime(f, (now, now))  # force root-crate rebuild (cargo mtime freshness)
    env = {k: v for k, v in os.environ.items() if k not in ('RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTUP_TOOLCHAIN')}
    env.update(CARGO_HOME=str(LANE / 'cargo-home'), CARGO_TARGET_DIR=str(a.target),
               RUSTC=str(TC / 'rust/bin/rustc'), RUSTDOC=str(TC / 'rust/bin/rustdoc'),
               CC=str(TC / 'llvm/bin/clang'), AR=str(TC / 'llvm/bin/llvm-ar'),
               CARGO_TARGET_SBPF_SOLANA_SOLANA_RUSTFLAGS=' -Zremap-cwd-prefix=', CARGO_BUILD_JOBS=a.jobs)
    for kv in a.env:
        k, v = kv.split('=', 1); env[k] = v
    cmd = [str(TC / 'rust/bin/cargo'), 'build', '--release', '--target', 'sbpf-solana-solana',
           '--manifest-path', str(a.ws / 'Cargo.toml'), '--locked', '--offline']
    lock = [sys.executable, str(SP / 'sbf_lock.py'), '--slots', '6', '--name', 'sbf', '--']
    t0 = time.time()
    with open(out / 'build.log', 'w') as log:
        rc = subprocess.run(lock + cmd, cwd=str(a.ws), env=env, stdout=log, stderr=subprocess.STDOUT).returncode
    rec = {'tag': a.tag, 'src': str(a.src), 'command': cmd, 'cwd': str(a.ws), 'returncode': rc, 'seconds': round(time.time() - t0, 1),
           'env': {k: env[k] for k in ('CARGO_HOME', 'CARGO_TARGET_DIR', 'RUSTC', 'CARGO_TARGET_SBPF_SOLANA_SOLANA_RUSTFLAGS', 'CARGO_BUILD_JOBS')}, 'extra_env': a.env,
           'rustc_sha256': sha(TC / 'rust/bin/rustc'), 'strip_sha256': sha(STRIP)}
    if rc != 0:
        (out / 'build.json').write_text(json.dumps(rec, indent=1))
        print(open(out / 'build.log').read()[-4000:]); sys.exit(rc)
    uns = a.target / 'sbpf-solana-solana/release/pump_amm_recovered.so'
    shutil.copy2(uns, out / 'unstripped.so')
    subprocess.run([str(STRIP), '--strip-all', str(out / 'unstripped.so'), str(out / 'candidate.so')], check=True)
    rec.update(unstripped_sha256=sha(out / 'unstripped.so'), candidate_sha256=sha(out / 'candidate.so'))
    (out / 'build.json').write_text(json.dumps(rec, indent=1))
    assert 'Compiling pump-amm-recovered' in (out / 'build.log').read_text(), 'root crate did not rebuild'
    print(json.dumps({k: rec[k] for k in ('tag', 'returncode', 'seconds', 'candidate_sha256')}))
    if not a.no_measure:
        m = subprocess.run([sys.executable, str(WT / 'repro/pump_amm/focused-diagnostics-20261026/measure.py'), '--candidate', str(out / 'candidate.so'),
                            '--symbols', str(out / 'unstripped.so'), '--output', str(out / 'measurement.json')], capture_output=True, text=True, cwd=str(WT))
        if m.returncode: print(m.stdout[-2000:], m.stderr[-3000:]); sys.exit(m.returncode)
        d = json.loads((out / 'measurement.json').read_text())
        print(json.dumps({k: d[k] for k in ('normalized_matches', 'raw_matches', 'unmatched')}))
main()
