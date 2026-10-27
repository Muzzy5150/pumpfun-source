#!/usr/bin/env python3
"""Create, build and measure a source variant.

usage: variant.py NAME --base b/v2 --edit EDITS.py [--sdk mac|mixed] [--linker default|qualified]
                  [--windows O0193,...] [--cand-names state10initialize,...] [--no-build]

EDITS.py defines edit(root: Path) applying ordinary source edits under root/programs/mayhem.
The variant tree is kept at LANE/b/NAME for the record; builds run from LANE/b/work-<sdk>
(rsync --checksum so only changed files get new mtimes).
"""
import argparse, json, os, shutil, subprocess, sys, runpy, difflib
from pathlib import Path

LANE = Path(__file__).resolve().parents[2]
T = LANE / 'out/tools'
ap = argparse.ArgumentParser()
ap.add_argument('name')
ap.add_argument('--base', default='b/v3')
ap.add_argument('--edit')
ap.add_argument('--sdk', default='mac')
ap.add_argument('--linker', default='default')
ap.add_argument('--windows', default='')
ap.add_argument('--no-build', action='store_true')
ap.add_argument('--measure-base', default=None)
a = ap.parse_args()

base = (LANE / a.base).resolve()
dst = LANE / 'b' / a.name
if dst.exists():
    sys.exit(f'exists: {dst}')
shutil.copytree(base, dst, symlinks=False)
if a.edit:
    ns = runpy.run_path(a.edit)
    ns['edit'](dst / 'programs/mayhem')
    shutil.copyfile(a.edit, LANE / 'out/edits' / (a.name + '.py')) if (LANE / 'out/edits').exists() else None
# record diff vs base
diff = []
for f in sorted((dst / 'programs/mayhem').rglob('*')):
    if f.is_file():
        rel = f.relative_to(dst)
        g = base / rel
        if not g.exists():
            diff.append(f'+++ new file {rel}\n')
            continue
        x, y = g.read_bytes(), f.read_bytes()
        if x != y:
            diff += difflib.unified_diff(x.decode().splitlines(True), y.decode().splitlines(True), f'a/{rel}', f'b/{rel}')
(LANE / 'out/diffs').mkdir(exist_ok=True)
(LANE / 'out/diffs' / (a.name + '.diff')).write_text(''.join(diff))
print(''.join(diff)[:6000])
if a.no_build:
    sys.exit()
work = LANE / 'b' / f'work-{a.sdk}'
work.mkdir(exist_ok=True)
subprocess.run(['rsync', '-rlpgoD', '--checksum', '--delete', f'{dst}/', f'{work}/'], check=True)  # no -t: changed files get fresh mtimes (cargo fingerprints by mtime)
label = a.name
tname = 'main' if a.sdk == 'mac' else 'mixed'
r = subprocess.run([sys.executable, str(T / 'mbuild.py'), label, str(work), '--sdk', a.sdk, '--linker', a.linker,
                    '--target-name', tname, '--clean', os.environ.get('VARIANT_CLEAN', '')], capture_output=True, text=True)
print(r.stdout[-1500:], r.stderr[-3000:])
if r.returncode:
    sys.exit(r.returncode)
mb = a.measure_base or ('out/builds/mac-v2-default/symbols.so' if a.sdk == 'mac' else 'out/art/v3-symbols.so')
m = subprocess.run([sys.executable, str(T / 'measure.py'), str(LANE / 'out/builds' / label / 'symbols.so'), '--base', str(LANE / mb),
                    '--json', str(LANE / 'out/builds' / label / 'measure.json')], capture_output=True, text=True)
print(m.stdout, m.stderr[-2000:])
