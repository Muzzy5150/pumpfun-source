#!/usr/bin/env python3
"""List callers (function + offset) of a target address in an SBF ELF. usage: callers.py <so> <target> [--sym]"""
import sys, struct, re, bisect
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sbfdiff import sections, symtab
so = Path(sys.argv[1]); tgt = int(sys.argv[2], 0)
b = so.read_bytes(); s = sections(b); t = s['.text']
code = b[t['offset']:t['offset'] + t['size']]
funcs = []
try:
    syms, funcs = symtab(so)
except Exception: pass
starts = sorted(a for a, n, nm in funcs); names = {a: nm for a, n, nm in funcs}
# for stripped: use inventory windows if given
if len(sys.argv) > 3 and sys.argv[3].endswith('.json.gz'):
    import gzip, json
    iv = json.loads(gzip.decompress(open(sys.argv[3], 'rb').read()))
    starts = sorted(w['start'] for w in iv['windows']); names = {w['start']: f"win{w['start']:#x}/{w['bytes']}" for w in iv['windows']}
i = 0
while i < len(code):
    op = code[i]
    if op == 0x18: i += 16; continue
    if op == 0x85 and code[i+1] >> 4 == 1:
        imm = struct.unpack_from('<i', code, i + 4)[0]
        addr = t['addr'] + i
        if imm != -1 and addr + 8 + imm * 8 == tgt:
            k = bisect.bisect_right(starts, addr) - 1
            f = starts[k] if k >= 0 else 0
            print(hex(addr), hex(f), f'+{addr-f:#x}', re.sub(r'17h[0-9a-f]{16}E$', '', names.get(f, '?'))[-110:])
    i += 8
