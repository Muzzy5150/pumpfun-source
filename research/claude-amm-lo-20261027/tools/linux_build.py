#!/usr/bin/env python3
"""Strict authenticated Linux v1.44 SBPF build of a staged AMM workspace (lane amm-lo).
Modeled on the frontier results/build-driver.py; lane-owned cargo home and target cache.
Holds the sbf (6) and podman (2) slot locks; container capped at 2 CPU / 3 GB."""
import argparse, hashlib, json, os, subprocess, sys, time, shutil
from pathlib import Path
SP = Path('/private/tmp/claude-501/-Users-shawwalters-Documents-Codex-2026-10-24-pumpfun-source/bf960843-6806-451b-a211-62c8b228d301/scratchpad')
L = SP/'lanes/amm-lo'; WT = L/'wt'
sys.path.insert(0, str(WT/'scripts'))
from compare import compare
IMAGE = 'docker.io/solanafoundation/solana-verifiable-build@sha256:6c73adc767ee7ff212f2532d4695472b12f3d4ac20aea3db22b89d8c614dac50'
SDK = Path('/Users/shawwalters/Documents/Codex/2026-10-24/pumpfun-source/work/amm-linux-v144-20261027/sdk')
EXPECTED = {'rust/bin/rustc': 'c8807b7ebede8578ac5a257ea333780f9d89bd356064fd8184af7e996cb71a97',
            'rust/bin/cargo': 'd28444578306fe5a4f40524331411340123004e9e6556322fcabdbe351fe265d'}
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def tree(root):
    root = Path(root)
    return {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob('*')) if p.is_file() and '/target/' not in str(p)}
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source-root', type=Path, required=True, help='tree containing programs/pump-amm')
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--target-cache', type=Path, default=L/'target/linux')
    ap.add_argument('--allow-dep-changes', action='store_true')
    a = ap.parse_args()
    out = a.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    ws = out/'ws'
    recipe = WT/'repro/pump_amm/account-context-recovery-20261027/workspace_recipe_v2.py'
    stage = subprocess.run([sys.executable, '-B', str(recipe), 'stage', '--source-root', str(a.source_root.resolve()), '--output', str(ws)], capture_output=True, text=True, check=True)
    (out/'stage.json').write_text(stage.stdout)
    for p, d in EXPECTED.items(): assert sha(SDK/p) == d, p
    cache = (L/'cargo-home').resolve(); tc = a.target_cache.resolve()
    # The lane-owned copies are mounted at the container paths used by the frontier build so
    # path-sensitive host/proc-macro fingerprints stay fresh. These are container-namespace mount
    # points only; nothing in the primary checkout is mounted or written.
    C_CACHE = '/Users/shawwalters/Documents/Codex/2026-10-24/pumpfun-source/work/amm-pubkey-provenance-final-20261027/cargo-home'
    C_TC = '/Users/shawwalters/Documents/Codex/2026-10-24/pumpfun-source/work/amm-workspace-current-20261027/target'
    env = {'CARGO_HOME': C_CACHE, 'CARGO_TARGET_DIR': C_TC, 'RUSTC': str(SDK/'rust/bin/rustc'), 'RUSTDOC': str(SDK/'rust/bin/rustdoc'),
           'CC': str(SDK/'llvm/bin/clang'), 'AR': str(SDK/'llvm/bin/llvm-ar'), 'LD_LIBRARY_PATH': str(SDK/'rust/lib')+':'+str(SDK/'llvm/lib'),
           'CARGO_TARGET_SBPF_SOLANA_SOLANA_RUSTFLAGS': ' -Zremap-cwd-prefix=', 'CARGO_BUILD_JOBS': '2'}
    name = 'claude-amm-lo-' + hashlib.sha256(str(out).encode()).hexdigest()[:10]
    prefix = ['podman', 'run', '--rm', '--pull=never', '--platform=linux/amd64', '--cpus=2', '--memory=3g', '--network=none', '--name', name, '--entrypoint=/usr/bin/env']
    for host, cpath, mode in [(ws, ws, 'ro'), (cache, C_CACHE, 'rw'), (SDK, SDK, 'ro'), (out, out, 'rw'), (tc, C_TC, 'rw')]:
        prefix += ['-v', f'{host}:{cpath}:{mode}']
    rec_mounts = {'cargo_home_host': str(cache), 'target_host': str(tc), 'cargo_home_container': C_CACHE, 'target_container': C_TC}
    prefix += ['-w', str(ws)]
    for k, v in env.items(): prefix += ['-e', f'{k}={v}']
    prefix += [IMAGE, '-u', 'RUSTFLAGS', '-u', 'CARGO_ENCODED_RUSTFLAGS']
    cmd = prefix + [str(SDK/'rust/bin/cargo'), 'build', '--release', '--target', 'sbpf-solana-solana', '--manifest-path', str(ws/'Cargo.toml'), '--locked', '--offline']
    deps = lambda: {str(f.relative_to(tc)): sha(f) for f in sorted(tc.rglob('*')) if f.is_file() and f.suffix in ('.rlib', '.rmeta', '.so') and not f.name.startswith(('libpump_amm_recovered', 'pump_amm_recovered'))}
    before_src = tree(ws); before = deps()
    lock = ['python3', str(SP/'sbf_lock.py'), '--slots', '6', '--name', 'sbf', '--', 'python3', str(SP/'sbf_lock.py'), '--slots', '2', '--name', 'podman', '--']
    rec = {'scope': __doc__, 'command': cmd, 'lock_wrapper': lock, 'environment': env, 'image': IMAGE, 'sdk_tool_sha256': EXPECTED,
           'source_sha256': before_src, 'dependency_cache_before': before, 'mounts': rec_mounts}
    t = time.monotonic()
    with (out/'build.log').open('w') as log:
        r = subprocess.run(lock + cmd, stdout=log, stderr=subprocess.STDOUT)
    rec.update(returncode=r.returncode, seconds=time.monotonic()-t, source_after_sha256=tree(ws), dependency_cache_after=deps())
    rec['source_unchanged'] = rec['source_sha256'] == rec['source_after_sha256']
    rec['dependencies_unchanged'] = rec['dependency_cache_after'] == before
    (out/'build-record.json').write_text(json.dumps(rec, indent=1) + '\n')
    subprocess.run(['podman', 'rm', '-f', name], capture_output=True)
    assert r.returncode == 0, 'build failed; see build.log'
    assert rec['source_unchanged']
    if not a.allow_dep_changes: assert rec['dependencies_unchanged'], 'dependency artifacts changed'
    assert 'Compiling pump-amm-recovered' in (out/'build.log').read_text()
    uns = tc/'sbpf-solana-solana/release/pump_amm_recovered.so'
    shutil.copy2(uns, out/'unstripped.so')
    strip = Path.home()/'.cache/solana/v1.52/platform-tools/llvm/bin/llvm-objcopy'
    subprocess.run([str(strip), '--strip-all', str(out/'unstripped.so'), str(out/'candidate.so')], check=True)
    rec.update(unstripped_sha256=sha(out/'unstripped.so'), candidate_sha256=sha(out/'candidate.so'),
               comparison=compare((WT/'evidence/original/pump_amm/deployed.so').read_bytes(), (out/'candidate.so').read_bytes()))
    (out/'build-record.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps({'candidate_sha256': rec['candidate_sha256'], 'unstripped_sha256': rec['unstripped_sha256'], 'seconds': round(rec['seconds'],1), 'dependencies_unchanged': rec['dependencies_unchanged']}))
    m = subprocess.run([sys.executable, str(WT/'repro/pump_amm/focused-diagnostics-20261026/measure.py'), '--candidate', str(out/'candidate.so'), '--symbols', str(out/'unstripped.so'), '--output', str(out/'measure.json')], capture_output=True, text=True, cwd=WT)
    print('\n'.join(l for l in m.stdout.splitlines() if any(k in l for k in ('raw_matches', 'normalized_matches', '"unmatched"'))))
if __name__ == '__main__':
    main()
