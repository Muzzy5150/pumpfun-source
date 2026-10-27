#!/usr/bin/env python3
"""Lane mayhem-a build driver (modeled on research/mayhem-provider-sharing/build.py).

usage: mbuild.py LABEL SOURCE_ROOT [--sdk mac|mixed] [--linker default|qualified]
                 [--target-name NAME] [--extra-rustc-json JSON]

SOURCE_ROOT must contain programs/mayhem/Cargo.toml.  Every cargo command runs
inside the shared sbf slot lock.  Outputs go to LANE/out/builds/LABEL/.
"""
import argparse, hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path

LANE = Path(__file__).resolve().parents[2]
SP = LANE.parents[1]
LOCK = SP / 'sbf_lock.py'
V154 = Path.home() / '.cache/solana/v1.54/platform-tools'
PKT = LANE / 'wt/research/mayhem-trade-origins-validator'

ap = argparse.ArgumentParser()
ap.add_argument('label')
ap.add_argument('source_root')
ap.add_argument('--sdk', default='mac', choices=['mac', 'mixed'])
ap.add_argument('--linker', default='default', choices=['default', 'qualified'])
ap.add_argument('--target-name', default='main')
ap.add_argument('--extra-rustc-json', default='["--remap-path-prefix=src/account_wrapper.rs=src/account_wrapper.rs"]')
ap.add_argument('--clean', default='mayhem-recovered,anchor-lang,curve-accounts')
ap.add_argument('--ordered-ld', default=str(PKT / 'config/ordered.ld'))
a = ap.parse_args()

sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
src_root = Path(a.source_root).resolve()
src = src_root / 'programs/mayhem'
assert (src / 'Cargo.toml').exists(), src
out = LANE / 'out/builds' / a.label
if out.exists():
    sys.exit(f'output exists: {out}')
out.mkdir(parents=True)
target = LANE / 'target' / a.target_name
target.mkdir(parents=True, exist_ok=True)

if a.sdk == 'mac':
    sdk = V154 / 'rust'
else:
    sdk = LANE / 'sysroot-mixed'
    assert (sdk / 'bin/rustc').exists(), 'mixed sysroot not prepared'
rustc = sdk / 'bin/rustc'
cargo = sdk / 'bin/cargo'
clang = V154 / 'llvm/bin/clang'
strip = Path.home() / '.cache/solana/v1.52/platform-tools/llvm/bin/llvm-objcopy'
env = os.environ.copy()
overrides = {
    'RUSTC': str(rustc), 'RUSTDOC': str(sdk / 'bin/rustdoc'),
    'CARGO_HOME': str(Path.home() / '.cargo'), 'CARGO_TARGET_DIR': str(target),
    'CARGO_NET_OFFLINE': 'true', 'CC': str(clang), 'AR': str(clang.parent / 'llvm-ar'),
    'CARGO_TARGET_SBPF_SOLANA_SOLANA_RUSTFLAGS': '-Zremap-cwd-prefix=',
}
env.update(overrides)
for k in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'CARGO_BUILD_RUSTFLAGS']:
    env.pop(k, None)
cmd = [str(cargo), 'rustc', '--manifest-path', str(src / 'Cargo.toml'), '--release', '--target', 'sbpf-solana-solana',
       '--locked', '--offline', '--verbose', '--jobs', '2', '--', '--remap-path-prefix=src/=programs/mayhem-program/src/']
cmd += json.loads(a.extra_rustc_json)
mapfile = out / 'link.map'
if a.linker == 'qualified':
    # wrapper swaps the default script for ordered.ld (same mechanism as the packet's linker.py)
    wrap = out / 'linker.py'
    real = sdk / 'lib/rustlib/aarch64-apple-darwin/bin/rust-lld'
    wrap.write_text(f'''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
before=sys.argv[1:];after=before.copy();changes=0
for i,arg in enumerate(before):
    if arg in ('--script','-T'):
        inc=Path(before[i+1]).read_bytes();after[i+1]={a.ordered_ld!r};changes+=1
    elif arg.startswith('--script='):
        inc=Path(arg.split('=',1)[1]).read_bytes();after[i]='--script='+{a.ordered_ld!r};changes+=1
assert changes==1
Path({str(out / 'linker-invocation.json')!r}).write_text(json.dumps(dict(incoming=before,forwarded=after,default_script_equal=inc==Path({str(PKT / 'config/default.ld')!r}).read_bytes()),indent=1))
os.execv({str(real)!r},[{str(real)!r},*after])
''')
    wrap.chmod(0o755)
    cmd += [f'-Clinker={wrap}']
cmd += [f'-Clink-arg=-Map={mapfile}']

inputs = {str(f.relative_to(src)): sha(f) for f in sorted(src.rglob('*')) if f.is_file()}
(out / 'launch.json').write_text(json.dumps(dict(command=cmd, cwd=str(src_root), environment_overrides=overrides,
                                                 source_inputs=inputs, sdk=a.sdk, linker=a.linker), indent=1) + '\n')
start = time.monotonic()
with (out / 'stdout').open('wb') as so, (out / 'stderr').open('wb') as se:
    for pkg in [p for p in a.clean.split(',') if p]:
        subprocess.run([sys.executable, str(LOCK), '--slots', '6', '--name', 'sbf', '--', str(cargo), 'clean', '--manifest-path',
                        str(src / 'Cargo.toml'), '--release', '--target', 'sbpf-solana-solana', '-p', pkg],
                       cwd=src_root, env=env, stdout=so, stderr=se, check=True)
    res = subprocess.run([sys.executable, str(LOCK), '--slots', '6', '--name', 'sbf', '--'] + cmd, cwd=src_root, env=env, stdout=so, stderr=se)
rec = dict(returncode=res.returncode, seconds=round(time.monotonic() - start, 1),
           source_unchanged=inputs == {str(f.relative_to(src)): sha(f) for f in sorted(src.rglob('*')) if f.is_file()})
if res.returncode == 0:
    shutil.copyfile(target / 'sbpf-solana-solana/release/mayhem_recovered.so', out / 'symbols.so')
    subprocess.run([str(strip), '--strip-all', str(out / 'symbols.so'), str(out / 'candidate.so')], check=True)
    rec.update(candidate_sha256=sha(out / 'candidate.so'), symbols_sha256=sha(out / 'symbols.so'),
               candidate_bytes=(out / 'candidate.so').stat().st_size)
(out / 'result.json').write_text(json.dumps(rec, indent=1) + '\n')
print(json.dumps(rec, indent=1))
if res.returncode != 0:
    print((out / 'stderr').read_text()[-4000:])
    sys.exit(1)
