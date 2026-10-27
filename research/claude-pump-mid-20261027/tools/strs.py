"""List rodata strings referenced (lddw + nearby length immediate) by a function window."""
import sys, struct
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import pm
def refs(blob, secs, start, size):
    raw = pm.body(blob, secs, start, size); out = []; i = 0; ins = []
    while i < len(raw):
        op, regs, off, imm = struct.unpack_from('<BBhi', raw, i)
        if op == 0x18:
            v = struct.unpack_from('<I', raw, i+4)[0] | struct.unpack_from('<I', raw, i+12)[0] << 32
            ins.append((i, op, regs, off, v)); i += 16
        else:
            ins.append((i, op, regs, off, imm)); i += 8
    for k, (i, op, regs, off, v) in enumerate(ins):
        if op != 0x18: continue
        d = pm.vread(blob, secs, v, 80)
        if d is None: continue
        # look for a small immediate (mov r, n / stdw n) in next 4 instructions as a length
        cands = [x[4] for x in ins[k+1:k+5] if x[1] in (0xb7, 0x7a, 0x62) and 0 < x[4] < 80]
        txt = None
        for n in cands:
            s = d[:n]
            if all(32 <= c < 127 for c in s): txt = s.decode(); break
        out.append((i, hex(v), txt))
    return out
if __name__ == '__main__':
    which, start, size = sys.argv[1], int(sys.argv[2], 0), int(sys.argv[3], 0)
    path = pm.ORIG if which == 'o' else Path(which)
    blob = path.read_bytes(); secs = pm.sections(blob)
    for r in refs(blob, secs, start, size):
        if r[2]: print(r)
