"""Rank unmatched original windows by similarity to unmatched candidate functions.

Heuristic triage only: callee-multiset similarity (callees mapped through matched
windows) plus normalized-slot sequence similarity. Never an equivalence claim.
"""
import sys, json, collections, difflib, struct, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import pm

ap = argparse.ArgumentParser()
ap.add_argument('--round', default='main-contract-round20-20261027')
ap.add_argument('--candidate', default=None, help='unstripped candidate (default: packet unstripped.so)')
ap.add_argument('--inventory', default=None)
ap.add_argument('--lo', type=lambda s: int(s, 0), default=0x65eb0)
ap.add_argument('--hi', type=lambda s: int(s, 0), default=0xfdf20)
ap.add_argument('--out', required=True)
a = ap.parse_args()
P = pm.WT / 'repro/pump' / a.round
cand_path = Path(a.candidate) if a.candidate else P / 'unstripped.so'
inv = pm.read_json(a.inventory or P / 'inventory.json.gz')
ob = pm.ORIG.read_bytes(); cb = cand_path.read_bytes()
osec, csec = pm.sections(ob), pm.sections(cb)
funcs = pm.candidate_functions(cand_path)
names = {f[0]: f[2] for f in funcs}
dem = dict(zip([f[2] for f in funcs], pm.demangle([f[2] for f in funcs])))
win = {w['start']: w for w in inv['windows']}
o2c = {w['start']: [m['start'] for m in w['normalized_matches']] for w in inv['windows']}
c2o = collections.defaultdict(list)
for o, cs in o2c.items():
    for c in cs: c2o[c].append(o)
# original callee lists
ocalls = {}; onorm = {}
for w in inv['windows']:
    raw = pm.body(ob, osec, w['start'], w['bytes'])
    ocalls[w['start']] = pm.calls(raw, w['start'])
    onorm[w['start']] = pm.normalize(raw, w['start'], osec)[0]
ccalls = {}; cnorm = {}
for s, n, name in funcs:
    raw = pm.body(cb, csec, s, n)
    ccalls[s] = pm.calls(raw, s)
    cnorm[s] = pm.normalize(raw, s, csec)[0]
ocallers = collections.defaultdict(set)
for o, cl in ocalls.items():
    for t in cl:
        if isinstance(t, int): ocallers[t].add(o)
ccallers = collections.defaultdict(set)
for c, cl in ccalls.items():
    for t in cl:
        if isinstance(t, int): ccallers[t].add(c)

def short(n):
    d = dem.get(n, n)
    return d[:150]

def omap(t):
    # map original call target to a canonical token: matched -> candidate name set id; else unmatched-orig addr
    if isinstance(t, tuple): return ('sys', t[1])
    cs = o2c.get(t)
    if cs: return ('c', min(cs))
    return ('o', t)

def cmap(t):
    if isinstance(t, tuple): return ('sys', t[1])
    os_ = c2o.get(t)
    if os_:
        return ('c', min(o2c[min(os_)]))
    return ('cu', t)

unmatched_c = [f for f in funcs if f[0] not in c2o]
rows = []
for w in inv['windows']:
    s = w['start']
    if w['normalized_matches'] or not (a.lo <= s <= a.hi): continue
    oc = collections.Counter(omap(t) for t in ocalls[s])
    ocr = collections.Counter(omap(t) for t in ocallers[s])
    oslots = pm.slots(onorm[s]); oops = [x[0] for x in oslots]
    scored = []
    for cs_, cn, cname in funcs:
        if cs_ in c2o and False: continue
        cc = collections.Counter(cmap(t) for t in ccalls[cs_])
        inter = sum((oc & cc).values()); union = sum((oc | cc).values())
        jac = inter / union if union else (1.0 if not oc and not cc else 0.0)
        lr = min(cn, w['bytes']) / max(cn, w['bytes'])
        if lr < 0.5 and jac < 0.5: continue
        scored.append((jac * 0.6 + lr * 0.4, jac, lr, cs_, cn, cname))
    scored.sort(reverse=True)
    best = []
    for sc, jac, lr, cs_, cn, cname in scored[:12]:
        cslots = pm.slots(cnorm[cs_])
        sm = difflib.SequenceMatcher(None, oslots, cslots, autojunk=False)
        r = sm.ratio()
        best.append({'cand_start': cs_, 'bytes': cn, 'jaccard': round(jac, 3), 'len_ratio': round(lr, 3), 'slot_ratio': round(r, 3), 'matched_to_original': [hex(x) for x in c2o.get(cs_, [])], 'name': short(cname)})
    best.sort(key=lambda b: -(b['slot_ratio'] * 0.7 + b['jaccard'] * 0.3))
    callees = []
    for t in ocalls[s]:
        if isinstance(t, tuple): callees.append(f'syscall:{t[1]:#x}'); continue
        cs = o2c.get(t)
        callees.append(f'{t:#x}=' + (short(names[cs[0]])[:90] if cs else ('UNMATCHED' if t in win else '?')))
    callers = []
    for c in sorted(ocallers[s]):
        cs = o2c.get(c)
        callers.append(f'{c:#x}=' + (short(names[cs[0]])[:90] if cs else 'UNMATCHED'))
    rows.append({'start': s, 'hex': hex(s), 'bytes': w['bytes'], 'callees': callees, 'callers': callers, 'best': best[:5]})
Path(a.out).write_text(json.dumps(rows, indent=1))
for r in rows:
    b = r['best'][0] if r['best'] else None
    print(r['hex'], r['bytes'], 'callers', len(r['callers']), 'callees', len(r['callees']), '|', (f"{b['slot_ratio']} j{b['jaccard']} {b['bytes']} m{b['matched_to_original']} {b['name'][:100]}" if b else '-'))
