#!/usr/bin/env python3
"""Side-by-side normalized diff of an original window vs a candidate function.
usage: sbfdiff.py <original.so> <candidate-unstripped.so> <orig_start> <orig_bytes> <cand_start|symbol-regex> [--all]
"""
import sys, struct, re, subprocess, difflib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
OBJDUMP = str(Path.home() / '.cache/solana/v1.44/platform-tools/llvm/bin/llvm-objdump')

def sections(blob):
    shoff, = struct.unpack_from('<Q', blob, 0x28)
    shentsize, shnum, shstrndx = struct.unpack_from('<HHH', blob, 0x3a)
    hdrs = [struct.unpack_from('<IIQQQQIIQQ', blob, shoff + i * shentsize) for i in range(shnum)]
    strtab = hdrs[shstrndx]
    name = lambda off: blob[strtab[4] + off:blob.index(b'\0', strtab[4] + off)].decode()
    return {name(h[0]): {'addr': h[3], 'offset': h[4], 'size': h[5]} for h in hdrs}

ALU = {0x0:'add',0x1:'sub',0x2:'mul',0x3:'div',0x4:'or',0x5:'and',0x6:'lsh',0x7:'rsh',0x8:'neg',0x9:'mod',0xa:'xor',0xb:'mov',0xc:'arsh',0xd:'end'}
JMP = {0x0:'ja',0x1:'jeq',0x2:'jgt',0x3:'jge',0x4:'jset',0x5:'jne',0x6:'jsgt',0x7:'jsge',0xa:'jlt',0xb:'jle',0xc:'jslt',0xd:'jsle'}
SZ = {0x00:'w',0x08:'h',0x10:'b',0x18:'dw'}

def section_of(secs, v):
    for n, s in secs.items():
        if s['addr'] > 0 and s['addr'] <= v < s['addr'] + s['size']: return n
    return None

def dis(code, base, secs, symbols=None):
    out = []; i = 0
    while i < len(code):
        op, regs, off, imm = struct.unpack_from('<BBhi', code, i)
        dst, src = regs & 0xf, regs >> 4
        addr = base + i
        if op == 0x18:
            hi = struct.unpack_from('<i', code, i + 12)[0]
            v = (imm & 0xffffffff) | ((hi & 0xffffffff) << 32)
            sec = section_of(secs, v)
            txt = f'lddw r{dst}, {hex(v)}' + (f' <{sec}>' if sec else '')
            key = f'lddw r{dst}, ' + (f'<{sec}>' if sec else hex(v))
            out.append((addr, 16, txt, key, key)); i += 16; continue
        cls = op & 7
        if cls in (4, 7):  # alu
            name = ALU.get(op >> 4, '?'); w = '64' if cls == 7 else '32'
            if (op >> 4) == 0xd:
                txt = f'{"be" if op & 8 else "le"}{imm} r{dst}'
            elif (op >> 4) == 0x8:
                txt = f'neg{w} r{dst}'
            elif op & 8: txt = f'{name}{w} r{dst}, r{src}'
            else: txt = f'{name}{w} r{dst}, {imm}'
            key = txt; skey = txt
        elif cls in (5, 6):
            if op == 0x85:
                if src == 1 and imm != -1:
                    tgt = addr + 8 + imm * 8
                    name = symbols.get(tgt, hex(tgt)) if symbols else hex(tgt)
                    txt = f'call {name}'; key = 'call <internal>'
                else:
                    txt = f'syscall {imm & 0xffffffff:#x}'; key = txt
                skey = key
            elif op == 0x95: txt = 'exit'; key = txt; skey = key
            elif op == 0x8d: txt = f'callx r{imm if imm else dst}'; key = txt; skey = key
            else:
                name = JMP.get(op >> 4, '?') + ('32' if cls == 6 else '')
                tgt = addr + 8 + off * 8
                if op & 8: txt = f'{name} r{dst}, r{src}, {off:+d}'
                else: txt = f'{name} r{dst}, {imm}, {off:+d}'
                if op == 0x05: txt = f'ja {off:+d}'
                key = txt; skey = re.sub(r', [+-]\d+$', '', txt) if op != 0x05 else 'ja'
        elif cls == 1:  # ldx
            sz = SZ.get(op & 0x18, '?'); txt = f'ldx{sz} r{dst}, [r{src}{off:+d}]'; key = txt
            skey = f'ldx{sz} r{dst}, [r{src}+F]' if src == 10 else txt
        elif cls == 2:  # st imm
            sz = SZ.get(op & 0x18, '?'); txt = f'st{sz} [r{dst}{off:+d}], {imm}'; key = txt
            skey = f'st{sz} [r{dst}+F], {imm}' if dst == 10 else txt
        elif cls == 3:
            sz = SZ.get(op & 0x18, '?'); txt = f'stx{sz} [r{dst}{off:+d}], r{src}'; key = txt
            skey = f'stx{sz} [r{dst}+F], r{src}' if dst == 10 else txt
        else:
            txt = f'op{op:#x} {regs:#x} {off} {imm}'; key = txt; skey = txt
        out.append((addr, 8, txt, key, skey)); i += 8
    return out

def symtab(path):
    t = subprocess.check_output([OBJDUMP, '-t', str(path)], text=True)
    syms = {}; funcs = []
    for line in t.splitlines():
        m = re.match(r'^([0-9a-f]+) .* F \.text\s+([0-9a-f]+)\s+(?:\.hidden\s+)?(\S+)$', line)
        if m:
            a, n, name = int(m.group(1), 16), int(m.group(2), 16), m.group(3)
            syms[a] = re.sub(r'17h[0-9a-f]{16}E$', '', name); funcs.append((a, n, name))
    return syms, funcs

def main():
    orig, cand = Path(sys.argv[1]), Path(sys.argv[2])
    ostart, olen = int(sys.argv[3], 0), int(sys.argv[4], 0)
    sel = sys.argv[5]; show_all = '--all' in sys.argv; structural = '--struct' in sys.argv
    ob, cb = orig.read_bytes(), cand.read_bytes(); os_, cs = sections(ob), sections(cb)
    syms, funcs = symtab(cand)
    try:
        cstart = int(sel, 0); clen = next(n for a, n, _ in funcs if a == cstart)
    except ValueError:
        cands = [(a, n, nm) for a, n, nm in funcs if re.search(sel, nm)]
        for c in cands: print('match', hex(c[0]), c[1], c[2][:150], file=sys.stderr)
        cstart, clen, _ = cands[0]
    ot = os_['.text']; ct = cs['.text']
    ocode = ob[ostart - ot['addr'] + ot['offset']: ostart - ot['addr'] + ot['offset'] + olen]
    ccode = cb[cstart - ct['addr'] + ct['offset']: cstart - ct['addr'] + ct['offset'] + clen]
    od = dis(ocode, ostart, os_); cd = dis(ccode, cstart, cs, syms)
    k = 4 if structural else 3
    a = [x[k] for x in od]; b = [x[k] for x in cd]
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    print(f'# orig {hex(ostart)} len {olen} ({len(od)} ins)  cand {hex(cstart)} len {clen} ({len(cd)} ins) {syms.get(cstart,"")[:120]}')
    print(f'# ratio {sm.ratio():.4f}')
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            if show_all:
                for x, y in zip(od[i1:i2], cd[j1:j2]): print(f'  {x[0]-ostart:5x} {x[2]:<44} | {y[2]}')
            else:
                print(f'  ... {i2-i1} equal')
            continue
        n = max(i2 - i1, j2 - j1)
        for t in range(n):
            x = od[i1 + t] if i1 + t < i2 else None; y = cd[j1 + t] if j1 + t < j2 else None
            l = f'{x[0]-ostart:5x} {x[2]}' if x else ''
            r = f'{y[0]-cstart:5x} {y[2]}' if y else ''
            print(f'{tag[0]} {l:<50} | {r}')
if __name__ == "__main__": main()
