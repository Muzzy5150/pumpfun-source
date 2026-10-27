"""Extract anchor error! Source origins (file, line, code) from function windows.

Heuristic: an lddw whose value points at a 'programs/' path string, with a nearby
`stdw [..], len` equal to the path length and `stw [..], line` immediates.
"""
import sys, struct, json, re, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import pm

def scan(blob, secs, start, size):
    raw = pm.body(blob, secs, start, size)
    ins = []
    i = 0
    while i < len(raw):
        op, regs, off, imm = struct.unpack_from('<BBhi', raw, i)
        if op == 0x18:
            v = struct.unpack_from('<I', raw, i + 4)[0] | struct.unpack_from('<I', raw, i + 12)[0] << 32
            ins.append((i, op, regs, off, v)); i += 16
        else:
            ins.append((i, op, regs, off, imm)); i += 8
    res = []
    for k, (i, op, regs, off, v) in enumerate(ins):
        if op != 0x18: continue
        s = pm.vread(blob, secs, v, 64)
        if not s or not s.startswith(b'programs/'): continue
        # find length
        win = ins[max(0, k - 12):k + 14]
        lens = [x for x in win if x[1] == 0x7a and 10 < x[4] < 64]  # stdw imm
        cand_len = None
        for x in lens:
            t = s[:x[4]]
            if t.endswith(b'.rs'):
                cand_len = x[4]; break
        if cand_len is None: continue
        fname = s[:cand_len].decode()
        lines = [x[4] for x in win if x[1] == 0x62 and 0 < x[4] < 5000]  # stw imm
        codes = [x[4] for x in win if x[1] == 0x62 and 6000 <= x[4] < 7000 or (x[1] == 0x62 and 100 <= x[4] < 6000 and x[4] not in lines)]
        res.append({'offset': i, 'file': fname, 'stw_imms': [x[4] for x in win if x[1] == 0x62], 'stb': [x[4] for x in win if x[1] == 0x72]})
    return res

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--candidate'); ap.add_argument('--out')
    a = ap.parse_args()
    inv = pm.read_json(pm.WT / 'repro/pump/main-contract-round26-20261027/inventory.json.gz')
    if a.candidate:
        blob = Path(a.candidate).read_bytes(); secs = pm.sections(blob)
        wins = [(s, n, name) for s, n, name in pm.candidate_functions(a.candidate)]
    else:
        blob = pm.ORIG.read_bytes(); secs = pm.sections(blob)
        wins = [(w['start'], w['bytes'], 'M' if w['normalized_matches'] else 'U') for w in inv['windows']]
    out = []
    for s, n, tag in wins:
        for r in scan(blob, secs, s, n):
            r['start'] = s; r['tag'] = tag; out.append(r)
    Path(a.out).write_text(json.dumps(out, indent=0))
    print(len(out))
