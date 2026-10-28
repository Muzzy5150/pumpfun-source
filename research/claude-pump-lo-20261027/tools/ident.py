#!/usr/bin/env python3
"""Read-only identification of original windows: callees/callers named via a composite score.json."""
import sys, json, struct, re, bisect
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sbfdiff import sections, dis
O = Path(sys.argv[1]).read_bytes(); score = json.load(open(sys.argv[2])); starts = [int(x, 16) for x in sys.argv[3].split(',')]
W = {int(k): v for k, v in score['windows'].items()}
wstarts = sorted(W)
def name(a):
    w = W.get(a)
    if w is None: return hex(a)
    if w['normalized'] and w['symbols']:
        s = re.sub(r'17h[0-9a-f]{16}E$', '', w['symbols'][0])
        return s[-70:]
    return f'UNMATCHED_{a:#x}/{w["bytes"]}'
s = sections(O); t = s['.text']; text = O[t['offset']:t['offset'] + t['size']]
calls = {}
i = 0
while i < len(text):
    op = text[i]
    if op == 0x18: i += 16; continue
    if op == 0x85 and text[i + 1] >> 4 == 1:
        imm = struct.unpack_from('<i', text, i + 4)[0]
        if imm != -1:
            a = t['addr'] + i; tgt = a + 8 + imm * 8
            k = bisect.bisect_right(wstarts, a) - 1
            calls.setdefault(tgt, []).append(wstarts[k])
    i += 8
for st in starts:
    n = W[st]['bytes']; code = O[st - t['addr'] + t['offset']: st - t['addr'] + t['offset'] + n]
    d = dis(code, st, s, {a: name(a) for a in W})
    callees = [x[2].split(' ', 1)[1] for x in d if x[2].startswith('call ')]
    consts = sorted({x[2].split(',')[1].strip() for x in d if x[2].startswith('lddw') and '<' not in x[2]})
    sysc = sorted({x[2] for x in d if x[2].startswith('syscall')})
    callers = sorted(set(calls.get(st, [])))
    print(f'## {st:#x} ({n} B)')
    print('   callees:', '; '.join(dict.fromkeys(callees))[:600])
    print('   callers:', ', '.join(name(c) for c in callers)[:500])
    if consts: print('   consts:', ' '.join(consts)[:200])
    if sysc: print('   syscalls:', ' '.join(sysc))
