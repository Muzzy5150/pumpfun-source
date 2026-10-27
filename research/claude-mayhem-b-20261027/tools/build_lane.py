#!/usr/bin/env python3
"""Lane mayhem-b build controller.

Mirrors research/mayhem-provider-sharing/build.py (mixed host/target SDK,
qualified linker script, same cargo command and environment) with lane-local
paths.  Must be run under the shared slot lock:

  python3 SP/sbf_lock.py --slots 6 --name sbf -- python3 build_lane.py LABEL ROOT [TARGET_NAME]

ROOT contains programs/mayhem/Cargo.toml.  Output goes to OUT/builds/LABEL.
"""
from pathlib import Path
import hashlib, json, os, shutil, subprocess, sys, time

B = Path(__file__).resolve().parent
L = B.parent
label, root = sys.argv[1], Path(sys.argv[2]).resolve()
target_name = sys.argv[3] if len(sys.argv) > 3 else 'main'
clean_anchor = os.environ.get('LANE_CLEAN_ANCHOR', '1') == '1'
sdk = B / 'layout-lane-linux-target2-sysroot'
target = L / 'target' / target_name
target.mkdir(parents=True, exist_ok=True)
src = root / 'programs/mayhem'
output = L / 'out/builds' / label
output.mkdir(parents=True)
sha = lambda p: hashlib.file_digest(p.open('rb'), 'sha256').hexdigest()
inventory = lambda p: {str(f.relative_to(p)): sha(f) for f in p.rglob('*') if f.is_file()}
launch = json.loads((L / 'wt/research/mayhem-provider-sharing/builds/recovered/launch.json').read_bytes())
target_inputs = launch['target_inputs']
assert target_inputs['archive_sha256'] == 'fcc41631c7f77561bf5412218bf297501dccf0305ea280f338f0ace2aab9f31e'
for path, digest in target_inputs['files'].items():
    assert sha(sdk / path) == digest, path
inputs = inventory(src)
strip = Path('/Users/shawwalters/.cache/solana/v1.52/platform-tools/llvm/bin/llvm-objcopy')
clang = Path('/Users/shawwalters/.cache/solana/v1.54/platform-tools/llvm/bin/clang')
ar = clang.parent / 'llvm-ar'
tools = {str(p): sha(p) for p in [sdk / 'bin/rustc', sdk / 'bin/rustdoc', sdk / 'bin/cargo', strip, clang, ar]}
env = os.environ.copy()
overrides = {'RUSTC': str(sdk / 'bin/rustc'), 'RUSTDOC': str(sdk / 'bin/rustdoc'), 'CARGO_HOME': str(B / 'cargo-home'),
             'CARGO_TARGET_DIR': str(target), 'RUSTUP_HOME': str(B / 'rustup'), 'CARGO_NET_OFFLINE': 'true',
             'CC': str(clang), 'AR': str(ar), 'CARGO_TARGET_SBPF_SOLANA_SOLANA_RUSTFLAGS': '-Zremap-cwd-prefix='}
env.update(overrides)
qualified = B / 'qualified'
cmd = [str(sdk / 'bin/cargo'), 'rustc', '--manifest-path', str(src / 'Cargo.toml'), '--release', '--target',
       'sbpf-solana-solana', '--locked', '--offline', '--verbose', '--jobs', '2', '--',
       '--remap-path-prefix=src/=programs/mayhem-program/src/',
       '--remap-path-prefix=src/account_wrapper.rs=src/account_wrapper.rs',
       '-Clinker=' + str(qualified / 'linker.py'), '-Clink-arg=-Map=' + str(output / 'clean.map')]
cmd += json.loads(os.environ.get('MAYHEM_ROOT_RUSTC_ARGS_JSON', '[]'))
record = {'command': cmd, 'cwd': str(root), 'environment_overrides': overrides, 'source_inputs': inputs,
          'controller_sha256': sha(Path(__file__)), 'checked_tools': tools, 'target_inputs': target_inputs,
          'clean_anchor': clean_anchor, 'linker_script_sha256': sha(qualified / 'ordered.ld'),
          'scope': 'lane mayhem-b replica of the provider-sharing mixed host/target recipe'}
(output / 'launch.json').write_text(json.dumps(record, indent=2) + '\n')
start = time.monotonic()
with (output / 'stdout').open('wb') as out, (output / 'stderr').open('wb') as err:
    for package in ['mayhem-recovered'] + (['anchor-lang'] if clean_anchor else []):
        subprocess.run([str(sdk / 'bin/cargo'), 'clean', '--manifest-path', str(src / 'Cargo.toml'), '--release',
                        '--target', 'sbpf-solana-solana', '-p', package], cwd=root, env=env, stdout=out, stderr=err,
                       check=True)
    result = subprocess.run(cmd, cwd=root, env=env, stdout=out, stderr=err)
rr = {'returncode': result.returncode, 'seconds': time.monotonic() - start, 'source_unchanged': inputs == inventory(src),
      'tools_unchanged': all(sha(Path(p)) == h for p, h in tools.items()),
      'target_libraries_unchanged': all(sha(sdk / p) == h for p, h in target_inputs['files'].items()),
      'stdout_sha256': sha(output / 'stdout'), 'stderr_sha256': sha(output / 'stderr')}
if result.returncode == 0:
    shutil.copyfile(target / 'sbpf-solana-solana/release/mayhem_recovered.so', output / 'symbols.so')
    subprocess.run([str(strip), '--strip-all', str(output / 'symbols.so'), str(output / 'candidate.so')], check=True)
    shutil.copyfile(qualified / 'invocation.json', output / 'invocation.json')
    rr.update(candidate_sha256=sha(output / 'candidate.so'), symbols_sha256=sha(output / 'symbols.so'),
              candidate_bytes=(output / 'candidate.so').stat().st_size)
(output / 'result.json').write_text(json.dumps(rr, indent=2) + '\n')
print(json.dumps(rr, indent=2))
assert result.returncode == 0 and rr['source_unchanged'] and rr['tools_unchanged'] and rr['target_libraries_unchanged']
