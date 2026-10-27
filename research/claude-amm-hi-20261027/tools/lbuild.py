#!/usr/bin/env python3
"""Strict offline Linux v1.44 SBPF build (frontier recipe) of a pump-amm source tree.

Same image, SDK, environment, release profile and `cargo build --locked --offline`
as repro/pump_amm/native-fee-cpi-recovery-20261027/results/build-driver.py. The lane
copies of the frontier Cargo home and target cache are mounted at the frontier's
container paths so dependency fingerprints stay fresh; dependency artifacts are
hashed before and after and must not change. Runs under the shared sbf and podman
slot locks with --cpus=2 --memory=3g.
"""
import argparse, hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path
LANE = Path('/private/tmp/claude-501/-Users-shawwalters-Documents-Codex-2026-10-24-pumpfun-source/bf960843-6806-451b-a211-62c8b228d301/scratchpad/lanes/amm-hi')
SP = LANE.parent.parent; WT = LANE / 'wt'
FRONT = WT / 'repro/pump_amm/account-context-recovery-20261027'
IMAGE = 'docker.io/solanafoundation/solana-verifiable-build@sha256:6c73adc767ee7ff212f2532d4695472b12f3d4ac20aea3db22b89d8c614dac50'
REPO_WORK = '/Users/shawwalters/Documents/Codex/2026-10-24/pumpfun-source/work'
CARGO_HOME_C = REPO_WORK + '/amm-pubkey-provenance-final-20261027/cargo-home'
TARGET_C = REPO_WORK + '/amm-workspace-current-20261027/target'
SDK = Path(REPO_WORK + '/amm-linux-v144-20261027/sdk')
EXPECTED = {'rust/bin/rustc': 'c8807b7ebede8578ac5a257ea333780f9d89bd356064fd8184af7e996cb71a97',
            'rust/bin/cargo': 'd28444578306fe5a4f40524331411340123004e9e6556322fcabdbe351fe265d'}
STRIP = Path.home() / '.cache/solana/v1.52/platform-tools/llvm/bin/llvm-objcopy'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--src', type=Path, default=WT)
    ap.add_argument('--tag', required=True)
    a = ap.parse_args(); a.src = a.src.resolve()
    out = LANE / 'out/builds' / a.tag; assert not out.exists(), out; out.mkdir(parents=True)
    ws = LANE / 'ws' / ('linux-' + a.tag)
    if ws.exists(): shutil.rmtree(ws)
    r = subprocess.run([sys.executable, str(FRONT / 'workspace_recipe_v2.py'), 'stage', '--source-root', str(a.src), '--output', str(ws)],
                       capture_output=True, text=True, cwd=str(WT))
    (out / 'stage.json').write_text(r.stdout + r.stderr); r.check_returncode()
    for p_, d in EXPECTED.items(): assert sha(SDK / p_) == d, p_
    now = time.time()
    for f in ws.rglob('*'):
        if f.is_file(): os.utime(f, (now, now))  # force root-crate rebuild (cargo mtime freshness)
    cache, target = LANE / 'cargo-home', LANE / 'target/linux'
    dep = lambda: {str(f.relative_to(target)): sha(f) for f in sorted(target.rglob('*')) if f.is_file()
                   and f.suffix in ('.rlib', '.rmeta', '.so') and not f.name.startswith(('libpump_amm_recovered', 'pump_amm_recovered'))}
    before = dep()
    env = {'CARGO_HOME': CARGO_HOME_C, 'CARGO_TARGET_DIR': TARGET_C, 'RUSTC': str(SDK / 'rust/bin/rustc'),
           'RUSTDOC': str(SDK / 'rust/bin/rustdoc'), 'CC': str(SDK / 'llvm/bin/clang'), 'AR': str(SDK / 'llvm/bin/llvm-ar'),
           'LD_LIBRARY_PATH': str(SDK / 'rust/lib') + ':' + str(SDK / 'llvm/lib'),
           'CARGO_TARGET_SBPF_SOLANA_SOLANA_RUSTFLAGS': ' -Zremap-cwd-prefix=', 'CARGO_BUILD_JOBS': '2'}
    name = 'claude-amm-hi-' + hashlib.sha256(str(out).encode()).hexdigest()[:8]
    cmd = ['podman', 'run', '--rm', '--pull=never', '--platform=linux/amd64', '--cpus=2', '--memory=3g', '--network=none',
           '--name', name, '--entrypoint=/usr/bin/env']
    for host, cpath, mode in [(ws, str(ws), 'ro'), (cache, CARGO_HOME_C, 'rw'), (SDK, str(SDK), 'ro'), (target, TARGET_C, 'rw')]:
        cmd += ['-v', f'{host}:{cpath}:{mode}']
    cmd += ['-w', str(ws)]
    for k, v in env.items(): cmd += ['-e', k + '=' + v]
    cmd += [IMAGE, '-u', 'RUSTFLAGS', '-u', 'CARGO_ENCODED_RUSTFLAGS', str(SDK / 'rust/bin/cargo'), 'build', '--release',
            '--target', 'sbpf-solana-solana', '--manifest-path', str(ws / 'Cargo.toml'), '--locked', '--offline']
    lock = [sys.executable, str(SP / 'sbf_lock.py'), '--slots', '6', '--name', 'sbf', '--',
            sys.executable, str(SP / 'sbf_lock.py'), '--slots', '2', '--name', 'podman', '--']
    t0 = time.time()
    with open(out / 'build.log', 'w') as log:
        rc = subprocess.run(lock + cmd, stdout=log, stderr=subprocess.STDOUT).returncode
    after = dep()
    rec = {'tag': a.tag, 'recipe': 'linux-v144 frontier driver equivalent', 'command': cmd, 'returncode': rc,
           'seconds': round(time.time() - t0, 1), 'environment': env, 'dependency_artifacts': len(before),
           'dependency_artifacts_unchanged': before == after, 'container': name,
           'dependency_artifacts_changed': sorted(k for k in before if k in after and before[k] != after[k]),
           'dependency_artifacts_removed': sorted(k for k in before if k not in after),
           'dependency_artifacts_added': sorted(k for k in after if k not in before),
           'workspace_inputs': {str(f.relative_to(ws)): sha(f) for f in sorted(ws.rglob('*')) if f.is_file()}}
    if rc != 0:
        (out / 'build.json').write_text(json.dumps(rec, indent=1)); print(open(out / 'build.log').read()[-3000:]); sys.exit(rc)
    assert 'Compiling pump-amm-recovered' in (out / 'build.log').read_text(), 'root crate did not rebuild'
    uns = target / 'sbpf-solana-solana/release/pump_amm_recovered.so'
    shutil.copy2(uns, out / 'unstripped.so')
    subprocess.run([str(STRIP), '--strip-all', str(out / 'unstripped.so'), str(out / 'candidate.so')], check=True)
    rec.update(unstripped_sha256=sha(out / 'unstripped.so'), candidate_sha256=sha(out / 'candidate.so'), strip_sha256=sha(STRIP))
    (out / 'build.json').write_text(json.dumps(rec, indent=1))
    print(json.dumps({k: rec[k] for k in ('tag', 'returncode', 'seconds', 'candidate_sha256', 'dependency_artifacts', 'dependency_artifacts_unchanged', 'dependency_artifacts_changed', 'dependency_artifacts_removed', 'dependency_artifacts_added')}))
    m = subprocess.run([sys.executable, str(WT / 'repro/pump_amm/focused-diagnostics-20261026/measure.py'), '--candidate', str(out / 'candidate.so'),
                        '--symbols', str(out / 'unstripped.so'), '--output', str(out / 'measurement.json')], capture_output=True, text=True, cwd=str(WT))
    if m.returncode: print(m.stderr[-3000:]); sys.exit(m.returncode)
    d = json.loads((out / 'measurement.json').read_text())
    print(json.dumps({k: d[k] for k in ('normalized_matches', 'raw_matches', 'unmatched')}))
main()
