#!/usr/bin/env python3
"""pm-o84 source-variant runner.

usage: var.py SPEC.json [--jobs N]
SPEC: [{"label": "pm-o84-vNN", "reps": [[file, old, new], ...], "base": "root"(default)}]
Each variant: rsync base root -> pm-o84/roots/<label>, apply replacements, build with build_lane.py
(under sbf_lock), then score O0084 (masked ratio/diff lines) and run measure.py (losses).
"""
import json, os, subprocess, sys, re, difflib
from concurrent.futures import ThreadPoolExecutor
MW = '/Users/shawwalters/Documents/Codex/2026-10-24/claude-mayhem-work'
P = MW + '/pm-o84'
B = MW + '/mayhem-b/build'
PY = '/Users/shawwalters/Documents/Codex/2026-10-24/pumpfun-source/work/test-env/bin/python'
sys.path.insert(0, B); sys.path.insert(0, P + '/tools')
import sbfdis, objsec, irx

def score_elf(path):
    C = sbfdis.elf(path); cf = sbfdis.funcs(C)
    a = [a for a, (b, n) in cf.items() if 'sell_v2_handler' in n][0]
    code = C.b[a:cf[a][0]]
    return irx.score(code)

def run(v):
    label = v['label']; root = f"{P}/roots/{label}"
    base = f"{P}/{v.get('base', 'root')}"
    os.makedirs(root, exist_ok=True)
    subprocess.run(['rsync', '-a', '--delete', '--exclude', '.git', base + '/', root + '/'], check=True)
    subprocess.run(['chmod', '-R', 'u+w', root], check=True)
    for f, old, new in v.get('reps', []):
        p = f'{root}/programs/mayhem/{f}'; s = open(p).read()
        if s.count(old) != 1:
            return label, {'error': f'replacement count {s.count(old)} in {f}: {old[:60]!r}'}
        open(p, 'w').write(s.replace(old, new))
    log = f'{P}/out/{label}.log'
    r = subprocess.run(['python3', MW + '/sbf_lock.py', '--slots', '6', '--name', 'sbf', '--', 'python3', B + '/build_lane.py', label, root, 'pm-o84-' + str(v.get('slot', 'a'))],
                       stdout=open(log, 'w'), stderr=subprocess.STDOUT)
    out = f'{MW}/mayhem-b/out/builds/{label}'
    if r.returncode or not os.path.exists(out + '/symbols.so'):
        return label, {'error': 'build failed', 'log': log}
    stack = 'Stack offset' in open(out + '/stderr', errors='ignore').read()
    sc = score_elf(out + '/symbols.so')
    m = subprocess.run([PY, '-B', B + '/measure.py', out + '/symbols.so', v.get('measure_base', f'{MW}/mayhem-b/out/builds/pm-o84-1/symbols.so'), '--json', f'{P}/out/{label}-measure.json'], capture_output=True, text=True)
    mj = json.load(open(f'{P}/out/{label}-measure.json'))
    return label, {'bytes': sc[0], 'pos': sc[1], 'ratio': sc[2], 'difflines': sc[3], 'stack_warning': stack,
                   'gains': mj['gains'], 'losses': mj['body_losses'] + mj['raw_losses'] + mj['edge_losses'] + mj['source_losses'],
                   'matched': mj['counts']['matched_after'], 'raw': mj['counts']['raw_after']}

if __name__ == '__main__':
    spec = json.load(open(sys.argv[1])); jobs = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[2] == '--jobs' else 2
    for i, v in enumerate(spec): v.setdefault('slot', chr(ord('a') + i % jobs))
    with ThreadPoolExecutor(jobs) as ex:
        for label, res in ex.map(run, spec):
            print(label, json.dumps(res), flush=True)
