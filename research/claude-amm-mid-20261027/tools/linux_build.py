#!/usr/bin/env python3
"""Strict offline Linux v1.44 SBPF build of a staged AMM workspace, mirroring the frontier
recipe (repro/pump_amm/native-fee-cpi-recovery-20261027/results/build-driver.py).

Differences from the frontier driver are confined to host-side storage: the lane's own
copies of the source, CARGO_HOME and target cache are bind-mounted at the frontier's
recorded *container* paths, so compiler-visible paths are identical while the primary
checkout is never written. The authenticated SDK is mounted read-only at its own path.
The container is capped at --cpus=2 --memory=3g and runs under both shared build locks.
"""
import argparse, hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path

SP = Path('/private/tmp/claude-501/-Users-shawwalters-Documents-Codex-2026-10-24-pumpfun-source/bf960843-6806-451b-a211-62c8b228d301/scratchpad')
L = SP / 'lanes/amm-mid'
REPO = Path('/Users/shawwalters/Documents/Codex/2026-10-24/pumpfun-source')
IMAGE = 'docker.io/solanafoundation/solana-verifiable-build@sha256:6c73adc767ee7ff212f2532d4695472b12f3d4ac20aea3db22b89d8c614dac50'
SDK = REPO / 'work/amm-linux-v144-20261027/sdk'
C_SOURCE = REPO / 'work/amm-native-fee-cpi-final-20261027/source'
C_HOME = REPO / 'work/amm-pubkey-provenance-final-20261027/cargo-home'
C_TARGET = REPO / 'work/amm-workspace-current-20261027/target'
EXPECTED = {'rust/bin/rustc': 'c8807b7ebede8578ac5a257ea333780f9d89bd356064fd8184af7e996cb71a97',
            'rust/bin/cargo': 'd28444578306fe5a4f40524331411340123004e9e6556322fcabdbe351fe265d'}
STRIP = Path.home() / '.cache/solana/v1.52/platform-tools/llvm/bin/llvm-objcopy'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def tree(root):
    root = Path(root)
    return {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob('*')) if p.is_file()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', type=Path, required=True, help='staged workspace (recipe output)')
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--target', type=Path, default=L / 'target/linux')
    ap.add_argument('--cargo-home', type=Path, default=L / 'cargo-home')
    ap.add_argument('--frontier-record', type=Path,
                    default=Path(__file__).resolve().parents[3] / 'repro/pump_amm/account-context-recovery-20261027/results/build/build-comparison.json' if (Path(__file__).resolve().parents[3] / 'repro').is_dir() else L / 'wt/repro/pump_amm/account-context-recovery-20261027/results/build/build-comparison.json',
                    help='frontier build record whose container source/CARGO_HOME/target paths are mirrored')
    a = ap.parse_args()
    global C_SOURCE, C_HOME, C_TARGET
    rec = json.loads(a.frontier_record.read_text())
    C_HOME = Path(rec['environment']['CARGO_HOME']); C_TARGET = Path(rec['environment']['CARGO_TARGET_DIR'])
    C_SOURCE = Path([c for c in rec['command'] if c.endswith('/Cargo.toml')][0]).parent
    out = a.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    for rel, digest in EXPECTED.items():
        assert sha(SDK / rel) == digest, rel
    src = a.source.resolve()
    before = tree(src)
    # Staged copies can be older than the previous root build; force the root crate
    # (only) to recompile by dropping its fingerprints. Dependency artifacts are kept.
    for fp in (a.target / 'sbpf-solana-solana/release/.fingerprint').glob('pump-amm-recovered-*'):
        shutil.rmtree(fp)
    deps = lambda: {str(f.relative_to(a.target)): sha(f) for f in sorted(a.target.rglob('*'))
                    if f.is_file() and f.suffix in ('.rlib', '.rmeta', '.so')
                    and not f.name.startswith(('libpump_amm_recovered', 'pump_amm_recovered'))}
    cache_before = deps()
    env = {'CARGO_HOME': str(C_HOME), 'CARGO_TARGET_DIR': str(C_TARGET), 'RUSTC': str(SDK / 'rust/bin/rustc'),
           'RUSTDOC': str(SDK / 'rust/bin/rustdoc'), 'CC': str(SDK / 'llvm/bin/clang'), 'AR': str(SDK / 'llvm/bin/llvm-ar'),
           'LD_LIBRARY_PATH': str(SDK / 'rust/lib') + ':' + str(SDK / 'llvm/lib'),
           'CARGO_TARGET_SBPF_SOLANA_SOLANA_RUSTFLAGS': ' -Zremap-cwd-prefix=', 'CARGO_BUILD_JOBS': '2'}
    name = 'claude-amm-mid-' + hashlib.sha256(str(out).encode()).hexdigest()[:10]
    prefix = ['podman', 'run', '--rm', '--pull=never', '--platform=linux/amd64', '--cpus=2', '--memory=3g',
              '--network=none', '--name', name, '--entrypoint=/usr/bin/env']
    for host, cont, mode in [(src, C_SOURCE, 'ro'), (a.cargo_home.resolve(), C_HOME, 'rw'), (SDK, SDK, 'ro'),
                             (a.target.resolve(), C_TARGET, 'rw')]:
        prefix += ['-v', f'{host}:{cont}:{mode}']
    prefix += ['-w', str(C_SOURCE)]
    for k, v in env.items():
        prefix += ['-e', f'{k}={v}']
    prefix += [IMAGE, '-u', 'RUSTFLAGS', '-u', 'CARGO_ENCODED_RUSTFLAGS']
    command = prefix + [str(SDK / 'rust/bin/cargo'), 'build', '--release', '--target', 'sbpf-solana-solana',
                        '--manifest-path', str(C_SOURCE / 'Cargo.toml'), '--locked', '--offline']
    locked = ['python3', str(SP / 'sbf_lock.py'), '--slots', '6', '--name', 'sbf', '--',
              'python3', str(SP / 'sbf_lock.py'), '--slots', '2', '--name', 'podman', '--']
    record = {'scope': __doc__, 'frontier_record': str(a.frontier_record), 'frontier_record_sha256': sha(a.frontier_record),
              'host_source': str(src), 'container_paths': {'source': str(C_SOURCE), 'cargo_home': str(C_HOME),
              'target': str(C_TARGET), 'sdk': str(SDK)}, 'image': IMAGE, 'command': command, 'environment': env,
              'tool_sha256': {k: sha(SDK / k) for k in EXPECTED}, 'source_sha256': before}
    t0 = time.monotonic()
    with (out / 'build.log').open('w') as log:
        rc = subprocess.run(locked + command, stdout=log, stderr=subprocess.STDOUT).returncode
    subprocess.run(['podman', 'rm', '-f', name], capture_output=True)
    record.update(returncode=rc, seconds=time.monotonic() - t0, source_after_sha256=tree(src))
    record['source_unchanged'] = record['source_after_sha256'] == before
    cache_after = deps()
    record['dependency_artifacts_unchanged'] = all(cache_after.get(k) == v for k, v in cache_before.items())
    record['dependency_artifacts_added'] = sorted(set(cache_after) - set(cache_before))
    (out / 'build-record.json').write_text(json.dumps(record, indent=2) + '\n')
    assert rc == 0, 'build failed; see build.log'
    assert record['source_unchanged']
    log_text = (out / 'build.log').read_text()
    assert 'Compiling pump-amm-recovered' in log_text, 'root crate did not rebuild'
    art = out / 'artifacts'; art.mkdir()
    shutil.copy2(a.target / 'sbpf-solana-solana/release/pump_amm_recovered.so', art / 'unstripped.so')
    subprocess.run([str(STRIP), '--strip-all', str(art / 'unstripped.so'), str(art / 'pump_amm_recovered.so')], check=True)
    record.update(unstripped_sha256=sha(art / 'unstripped.so'), candidate_sha256=sha(art / 'pump_amm_recovered.so'),
                  strip_tool_sha256=sha(STRIP))
    (out / 'build-record.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({k: record[k] for k in ('returncode', 'seconds', 'source_unchanged', 'dependency_artifacts_unchanged',
                                             'candidate_sha256', 'unstripped_sha256')}, indent=1))


if __name__ == '__main__':
    main()
