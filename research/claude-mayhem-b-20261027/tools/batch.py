#!/usr/bin/env python3
"""Run several source variants sequentially under ONE shared build-slot acquisition.

usage: batch.py SLOT SPEC.json
SPEC.json: [{"label": "...", "reps": [[file, old, new], ...]}, ...]
Each variant starts from the current roots/work tree (working copy, not HEAD),
applies its literal replacements, builds (root crate only), measures, and prints
a one-line window report.  The caller must NOT hold the lock; this script
re-execs itself under sbf_lock.py.
"""
import json, os, subprocess, sys
SP = '/private/tmp/claude-501/-Users-shawwalters-Documents-Codex-2026-10-24-pumpfun-source/bf960843-6806-451b-a211-62c8b228d301/scratchpad'
L = SP + '/lanes/mayhem-b'
B = L + '/build'
if os.environ.get('LANE_BATCH_LOCKED') != '1':
    env = dict(os.environ, LANE_BATCH_LOCKED='1')
    sys.exit(subprocess.call(['python3', SP + '/sbf_lock.py', '--slots', '6', '--name', 'sbf', '--',
                              'python3', __file__] + sys.argv[1:], env=env))
slot, spec = sys.argv[1], json.load(open(sys.argv[2]))
root = f'{B}/roots/{slot}'
dst = f'{root}/programs/mayhem'
os.makedirs(f'{root}/programs', exist_ok=True)
for v in spec:
    label = v['label']
    subprocess.run(['rsync', '-a', '--delete', '--exclude', '.git', f'{B}/roots/work/programs/mayhem/', dst + '/'], check=True)
    ok = True
    for f, old, new in v.get('reps', []):
        p = f'{dst}/{f}'; s = open(p).read()
        if s.count(old) != 1:
            print(f'{label}: replacement not unique/missing in {f}: {old[:60]!r} count={s.count(old)}', flush=True); ok = False; break
        open(p, 'w').write(s.replace(old, new))
    if not ok:
        continue
    env = dict(os.environ, LANE_CLEAN_ANCHOR='0')
    r = subprocess.run(['python3', f'{B}/build_lane.py', label, root, slot], env=env, capture_output=True, text=True)
    if r.returncode != 0:
        err = open(f'{L}/out/builds/{label}/stderr').read() if os.path.exists(f'{L}/out/builds/{label}/stderr') else r.stderr
        lines = [l for l in err.splitlines() if l.startswith('error') or l.startswith('  -->')][:8]
        print(f'{label}: BUILD FAILED ' + ' | '.join(lines), flush=True)
        continue
    subprocess.run(['python3', f'{B}/measure.py', f'{L}/out/builds/{label}/symbols.so', '--json', f'{L}/out/builds/{label}/measure.json'], capture_output=True)
    d = json.load(open(f'{L}/out/builds/{label}/measure.json'))
    losses = {k: d[k] for k in ['body_losses', 'raw_losses', 'edge_losses', 'source_losses', 'profile_losses'] if d[k]}
    print(f'== {label}: {d["statuses"]} gains={d["gains"]} raw_gains={d["raw_gains"]} losses={json.dumps(losses)[:300]} src+{len(d["source_gains"])}', flush=True)
    w = subprocess.run(['python3', f'{B}/winreport.py', f'{L}/out/builds/{label}/symbols.so'] + v.get('windows', []), capture_output=True, text=True)
    print(w.stdout, flush=True)
