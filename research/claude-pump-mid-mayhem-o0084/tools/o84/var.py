#!/usr/bin/env python3
"""o84 source-variant runner (from pm-o84/tools/var.py).

usage: var.py SPEC.json [--jobs N]
SPEC: [{"label": "o84-xNN", "reps": [[file, old, new], ...], "base": "base-w23"(default)}]
Each variant: rsync o84/<base> -> o84/roots/<label>, apply replacements (each `old` must occur exactly once),
build with build_lane.py under sbf_lock (target o84-<slot>), then score O0084 (masked lines), check
O0084 Source records against the original, and run measure.py against the parent-434 symbols (losses).
"""
import json, os, queue, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
MW = '/Users/shawwalters/Documents/Codex/2026-10-24/claude-mayhem-work'
P = MW + '/o84'
B = MW + '/mayhem-b/build'
PY = '/Users/shawwalters/Documents/Codex/2026-10-24/pumpfun-source/work/test-env/bin/python'
BASE434 = MW + '/mayhem-b/out/builds/pm-o84-b434/symbols.so'
sys.path.insert(0, B); sys.path.insert(0, P + '/tools')
import sbfdis, objsec, irx, winreport, srcrec

def score_elf(path):
    return irx.score(irx.elf_code(path))

def src_ok(path):
    O = winreport.O; C = sbfdis.elf(path); cf = sbfdis.funcs(C)
    wid, s, e, pat = [w for w in winreport.W if w[0] == 'O0084'][0]
    a = [a for a, (b, n) in cf.items() if pat in n][0]; b = cf[a][0]
    ro = [(r[1].split('/')[-1], r[2], r[3]) for r in srcrec.recs(O, s, e)]
    rc = [(r[1].split('/')[-1], r[2], r[3]) for r in srcrec.recs(C, a, b)]
    return ro == rc, rc

SLOTS = queue.Queue()

def run(v):
    slot = SLOTS.get()
    try:
        return run1(v, slot)
    finally:
        SLOTS.put(slot)

def run1(v, slot):
    label = v['label']; root = f"{P}/roots/{label}"
    base = f"{P}/{v.get('base', 'base-w23')}"
    os.makedirs(root, exist_ok=True)
    subprocess.run(['rsync', '-a', '--delete', '--exclude', '.git', base + '/', root + '/'], check=True)
    subprocess.run(['chmod', '-R', 'u+w', root], check=True)
    for f, old, new in v.get('reps', []):
        p = f'{root}/programs/mayhem/{f}'; s = open(p).read()
        if s.count(old) != 1:
            return label, {'error': f'replacement count {s.count(old)} in {f}: {old[:60]!r}'}
        open(p, 'w').write(s.replace(old, new))
    out = f'{MW}/mayhem-b/out/builds/{label}'
    subprocess.run(['rm', '-rf', out])
    log = f'{P}/out/{label}.log'
    env = os.environ.copy(); env.update(v.get('env', {}))
    r = subprocess.run(['python3', MW + '/sbf_lock.py', '--slots', '6', '--name', 'sbf', '--', 'python3', B + '/build_lane.py', label, root, 'o84-' + slot],
                       stdout=open(log, 'w'), stderr=subprocess.STDOUT, env=env)
    if r.returncode or not os.path.exists(out + '/symbols.so'):
        err = open(out + '/stderr', errors='ignore').read()[-1500:] if os.path.exists(out + '/stderr') else ''
        return label, {'error': 'build failed', 'log': log, 'stderr_tail': err}
    stack = 'Stack offset' in open(out + '/stderr', errors='ignore').read()
    sc = score_elf(out + '/symbols.so')
    ok, rc = src_ok(out + '/symbols.so')
    res = {'bytes': sc[0], 'pos': sc[1], 'ratio': sc[2], 'difflines': sc[3], 'stack_warning': stack, 'src_equal': ok}
    if not ok: res['src'] = rc
    if v.get('measure', True):
        subprocess.run([PY, '-B', B + '/measure.py', out + '/symbols.so', v.get('measure_base', BASE434), '--json', f'{P}/out/{label}-measure.json'], capture_output=True, text=True)
        mj = json.load(open(f'{P}/out/{label}-measure.json'))
        res.update(gains=mj['gains'], losses=mj['body_losses'] + mj['raw_losses'] + mj['edge_losses'] + mj['source_losses'] + mj['profile_losses'],
                   matched=mj['counts']['matched_after'], raw=mj['counts']['raw_after'])
    return label, res

if __name__ == '__main__':
    spec = json.load(open(sys.argv[1])); jobs = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[2] == '--jobs' else 2
    for i in range(jobs): SLOTS.put(chr(ord('a') + i))
    with ThreadPoolExecutor(jobs) as ex:
        for label, res in ex.map(run, spec):
            print(label, json.dumps(res), flush=True)
