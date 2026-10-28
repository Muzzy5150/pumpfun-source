#!/usr/bin/env python3
"""Lane mayhem-o79 batch runner (adapted from mayhem-b/build/batch.py).

usage: b79.py SLOT SPEC.json [--ir FUNCPAT]
SLOT must start with 'o79' (cargo target name and root dir name).
SPEC.json: [{"label": "...", "reps": [[file, old, new], ...]}, ...]
Each variant starts from mayhem-o79/root (working copy), applies literal
replacements, builds the root crate under the shared sbf lock (mayhem-b
build_lane.py, label 'o79-<label>'), measures against parent-433 and prints
the O0079 report.  With --ir, also emits LLVM IR (label 'o79-<label>-ir',
copied to out/ir/<label>.ll) and the MIR after finalize-isel for FUNCPAT.
"""
import json, os, subprocess, sys
W = '/Users/shawwalters/Documents/Codex/2026-10-24/claude-mayhem-work'
L = W + '/mayhem-o79'
B = L + '/build'
BL = W + '/mayhem-b/build/build_lane.py'
BUILDS = W + '/mayhem-b/out/builds'
if os.environ.get('LANE_BATCH_LOCKED') != '1':
    env = dict(os.environ, LANE_BATCH_LOCKED='1')
    sys.exit(subprocess.call(['python3', W + '/sbf_lock.py', '--slots', '6', '--name', 'sbf', '--',
                              'python3', __file__] + sys.argv[1:], env=env))
args = sys.argv[1:]
irpat = None
if '--ir' in args:
    i = args.index('--ir'); irpat = args[i + 1]; del args[i:i + 2]
slot, spec = args[0], json.load(open(args[1]))
assert slot.startswith('o79')
root = f'{L}/roots/{slot}'
dst = f'{root}/programs/mayhem'
os.makedirs(f'{root}/programs', exist_ok=True)
for v in spec:
    label = 'o79-' + v['label'] + ('-ir' if irpat else '')
    if os.path.exists(f'{BUILDS}/{label}'):
        print(f'{label}: exists, skipped', flush=True); continue
    subprocess.run(['rsync', '-a', '--delete', '--exclude', '.git', f'{L}/root/programs/mayhem/', dst + '/'], check=True)
    ok = True
    for f, old, new in v.get('reps', []):
        p = f'{dst}/{f}'; s = open(p).read()
        if s.count(old) != 1:
            print(f'{label}: replacement not unique/missing in {f}: {old[:60]!r} count={s.count(old)}', flush=True); ok = False; break
        open(p, 'w').write(s.replace(old, new))
    if not ok:
        continue
    env = dict(os.environ, LANE_CLEAN_ANCHOR='0')
    if irpat:
        env['MAYHEM_ROOT_RUSTC_ARGS_JSON'] = json.dumps(['--emit=llvm-ir,link', f'-Cllvm-args=-print-after=finalize-isel -filter-print-funcs={irpat}'])
    r = subprocess.run(['python3', BL, label, root, slot], env=env, capture_output=True, text=True)
    if irpat:
        ll = f'{W}/mayhem-b/target/{slot}/sbpf-solana-solana/release/deps/mayhem_recovered.ll'
        if os.path.exists(ll):
            os.replace(ll, f'{L}/out/ir/{v["label"]}.ll')
    if r.returncode != 0:
        err = open(f'{BUILDS}/{label}/stderr').read() if os.path.exists(f'{BUILDS}/{label}/stderr') else r.stderr
        lines = [l for l in err.splitlines() if l.startswith('error') or l.startswith('  -->')][:8]
        print(f'{label}: BUILD FAILED ' + ' | '.join(lines), flush=True)
        continue
    so = open(f'{BUILDS}/{label}/stderr').read()
    if 'Stack offset' in so:
        print(f'{label}: WARNING Stack offset present', flush=True)
    subprocess.run(['python3', '-B', f'{B}/measure.py', f'{BUILDS}/{label}/symbols.so', '--json', f'{BUILDS}/{label}/measure.json'], capture_output=True)
    d = json.load(open(f'{BUILDS}/{label}/measure.json'))
    losses = {k: d[k] for k in ['body_losses', 'raw_losses', 'edge_losses', 'source_losses', 'profile_losses'] if d[k]}
    print(f'== {label}: {d["statuses"]} gains={d["gains"]} raw_gains={d["raw_gains"]} losses={json.dumps(losses)[:300]} src+{len(d["source_gains"])}', flush=True)
    w = subprocess.run(['python3', '-B', f'{B}/winreport.py', f'{BUILDS}/{label}/symbols.so'] + v.get('windows', ['O0079']), capture_output=True, text=True)
    print(w.stdout.strip(), flush=True)
    h = subprocess.run(['python3', '-B', f'{B}/hunks.py', label, 'O0079', 'regs'], capture_output=True, text=True, cwd=B)
    c = subprocess.run(['python3', '-B', f'{B}/calls.py', 'c', f'{BUILDS}/{label}/symbols.so', 'sell_pump_swap7handler'], capture_output=True, text=True, cwd=B)
    nclone = c.stdout.count('Clone')
    mk = subprocess.run(['python3', '-B', '-c', 'import sys; sys.path.insert(0, %r); import llc79, mark79; c = mark79.code_of(%r); print(f"size {len(c)} ratio79 {llc79.ratio(c):.4f} prefix {llc79.prefix(c)} rd2800 {llc79.regdiff(c,0,2800)} rdall {llc79.regdiff(c)} | " + " ".join(llc79.markers(c)))' % (B, label)], capture_output=True, text=True)
    print('   ' + (mk.stdout.strip() or mk.stderr[-300:]), flush=True)
    print((h.stdout.splitlines()[0] if h.stdout else h.stderr[-300:]) + f'  clone-calls={nclone}', flush=True)
