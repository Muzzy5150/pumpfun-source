#!/usr/bin/env python3
"""Triage unmatched original windows: find most similar candidate function bodies.

Heuristic only. Uses the packet's normalizer (call imm + section lddw masked),
then additionally a 'structural' token form that masks branch offsets and
r10-relative stack offsets, for identifying the corresponding candidate function.
"""
import sys, json, gzip, struct, hashlib, collections, difflib, re, subprocess
from pathlib import Path
WT = Path(sys.argv[1]); PKT = WT / sys.argv[2]; CAND = Path(sys.argv[3]); OUT = Path(sys.argv[4])
LO, HI = int(sys.argv[5], 0), int(sys.argv[6], 0)
sys.path.insert(0, str(PKT / 'inputs/scripts'))
from pump_compare_function_bytes import normalize, body
from pump_quote_control_function_match import sections, candidate_functions
OBJDUMP = str(Path.home() / '.cache/solana/v1.44/platform-tools/llvm/bin/llvm-objdump')

def read(p):
    b = p.read_bytes(); return json.loads(gzip.decompress(b) if b[:2] == b'\x1f\x8b' else b)

def tokens(norm, structural=False):
    out = []; i = 0
    while i < len(norm):
        op = norm[i]
        if op == 0x18:
            out.append(norm[i:i+16] if not structural else bytes([op, norm[i+1]])); i += 16; continue
        s = bytearray(norm[i:i+8])
        if structural:
            cls = op & 7
            if cls in (5, 6) and op not in (0x85, 0x95):  # jumps: mask offset
                s[2:4] = b'\0\0'
            if cls in (1, 2, 3) or (cls == 0 and False):  # ld/st mem: mask offset if r10 based
                dst = s[1] & 0xf; src = s[1] >> 4
                if dst == 10 or src == 10: s[2:4] = b'\0\0'
            if op in (0x07, 0x17) and (s[1] & 0xf) in (1,2,3,4,5,10):  # add/sub imm often frame addr
                pass
        out.append(bytes(s)); i += 8
    return out

ob = (WT / 'evidence/original/pump/deployed.so').read_bytes(); cb = CAND.read_bytes()
os_, cs = sections(ob), sections(cb)
iv = read(PKT / 'inventory.json.gz')
funcs = candidate_functions(CAND, OBJDUMP, '.')
cand = []
for a, n, name in funcs:
    raw = body(cb, cs, a, n); norm, _ = normalize(raw, a, cs)
    cand.append(dict(start=a, bytes=n, symbol=name, tok=tokens(norm), stok=tokens(norm, True)))
# matched candidate starts (already used by matched windows)
matched_c = set()
for w in iv['windows']:
    for m in w['normalized_matches']: matched_c.add(m['start'])
rows = []
for w in iv['windows']:
    if w['normalized_matches'] or not (LO <= w['start'] <= HI): continue
    a, n = w['start'], w['bytes']
    raw = body(ob, os_, a, n); norm, _ = normalize(raw, a, os_)
    ot, ost = tokens(norm), tokens(norm, True)
    oc = collections.Counter(ost)
    pre = []
    for c in cand:
        if c['bytes'] < n * 0.5 or c['bytes'] > n * 2: continue
        cc = collections.Counter(c['stok'])
        inter = sum((oc & cc).values()); uni = sum((oc | cc).values())
        pre.append((inter / uni, c))
    pre.sort(key=lambda x: -x[0])
    best = []
    for j, c in pre[:6]:
        sm = difflib.SequenceMatcher(None, ost, c['stok'], autojunk=False)
        r = sm.ratio()
        sm2 = difflib.SequenceMatcher(None, ot, c['tok'], autojunk=False)
        exact_eq = sum(b.size for b in sm2.get_matching_blocks())
        best.append(dict(start=c['start'], bytes=c['bytes'], symbol=c['symbol'], jaccard=round(j, 4), struct_ratio=round(r, 4),
                         norm_equal_slots=exact_eq, orig_slots=len(ot), cand_slots=len(c['tok']), cand_matched_elsewhere=c['start'] in matched_c))
    best.sort(key=lambda x: -x['struct_ratio'])
    rows.append(dict(start=a, hex=hex(a), bytes=n, best=best[:3]))
    b0 = best[0] if best else {}
    print(hex(a), n, b0.get('bytes'), b0.get('struct_ratio'), b0.get('norm_equal_slots'), '/', b0.get('orig_slots'), re.sub(r'17h[0-9a-f]{16}E$', '', b0.get('symbol', ''))[-110:], flush=True)
OUT.write_text(json.dumps(rows, indent=1))
