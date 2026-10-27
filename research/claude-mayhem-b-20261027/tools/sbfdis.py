#!/usr/bin/env python3
"""Small SBF disassembler / window differ for lane mayhem-b (static analysis only)."""
import struct, sys, difflib, importlib.util, json, gzip
from pathlib import Path

L = Path(__file__).resolve().parent.parent
PKT = L / 'wt/research/mayhem-provider-sharing'
_spec = importlib.util.spec_from_file_location('mreader', PKT / 'reader.py')
reader = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(reader)

ALU = {0x00: 'add', 0x10: 'sub', 0x20: 'mul', 0x30: 'div', 0x40: 'or', 0x50: 'and', 0x60: 'lsh', 0x70: 'rsh',
       0x80: 'neg', 0x90: 'mod', 0xa0: 'xor', 0xb0: 'mov', 0xc0: 'arsh', 0xd0: 'end'}
JMP = {0x00: 'ja', 0x10: 'jeq', 0x20: 'jgt', 0x30: 'jge', 0x40: 'jset', 0x50: 'jne', 0x60: 'jsgt', 0x70: 'jsge',
       0xa0: 'jlt', 0xb0: 'jle', 0xc0: 'jslt', 0xd0: 'jsle'}
SZ = {0x00: 'w', 0x08: 'h', 0x10: 'b', 0x18: 'dw'}


def elf(path):
    return reader.Elf(Path(path).resolve())


def decode(b, at, start=None, end=None, rel=None, names=None):
    """Return list of dict(pc, size, op, text, norm) for [start,end)."""
    out = []
    pc = start
    while pc < end:
        op, regs, off, imm = struct.unpack_from('<BBhi', b, pc)
        dst, src = regs & 15, regs >> 4
        cls = op & 7
        size = 8
        r = rel.get(pc) if rel else None
        if op == 0x18:
            hi = struct.unpack_from('<I', b, pc + 12)[0]
            val = (imm & 0xffffffff) | hi << 32
            size = 16
            t = f'lddw r{dst}, {val:#x}'
            n = f'lddw r{dst}, ?' if (r and r['type'] == 8) else t
        elif cls in (4, 7):
            name = ALU.get(op & 0xf0, f'alu{op:#x}')
            w = '64' if cls == 7 else '32'
            if (op & 0xf0) == 0xd0:
                t = f'{"be" if op & 8 else "le"}{imm} r{dst}'
            elif (op & 0xf0) == 0x80:
                t = f'neg{w} r{dst}'
            elif op & 8:
                t = f'{name}{w} r{dst}, r{src}'
            else:
                t = f'{name}{w} r{dst}, {imm}'
            n = t
        elif cls == 5 or cls == 6:
            if op == 0x85:
                tgt = pc + 8 + imm * 8
                if r and r['type'] == 10:
                    t = f'call {r["symbol"]}'; n = t
                elif src == 1 or regs == 0x10:
                    nm = names.get(tgt) if names else None
                    t = f'call {tgt:#x}' + (f' <{nm}>' if nm else '')
                    n = 'call ?'
                else:
                    t = f'syscall {imm & 0xffffffff:#x}'; n = t
            elif op == 0x8d:
                t = f'callx r{imm if imm else src}'; n = t
            elif op == 0x95:
                t = 'exit'; n = t
            else:
                name = JMP.get(op & 0xf0, f'j{op:#x}')
                tgt = pc + 8 + off * 8
                if op == 0x05:
                    t = f'ja {tgt:#x}'
                elif op & 8:
                    t = f'{name} r{dst}, r{src}, {tgt:#x}'
                else:
                    t = f'{name} r{dst}, {imm}, {tgt:#x}'
                rel_off = (tgt - start) if start <= tgt < end else 'OUT'
                n = t.rsplit(',', 1)[0] + f', @{rel_off}' if op != 0x05 else f'ja @{rel_off}'
        elif cls == 1:
            t = f'ldx{SZ[op & 0x18]} r{dst}, [r{src}{off:+d}]'; n = t
        elif cls == 2:
            t = f'st{SZ[op & 0x18]} [r{dst}{off:+d}], {imm}'; n = t
        elif cls == 3:
            t = f'stx{SZ[op & 0x18]} [r{dst}{off:+d}], r{src}'; n = t
        else:
            t = f'.byte {b[pc:pc+8].hex()}'; n = t
        out.append(dict(pc=pc, size=size, op=op, text=t, norm=n, raw=b[pc:pc + size]))
        pc += size
    return out


def symbol_names(e):
    names = {}
    for s in e.symbols:
        if s['info'] & 15 == 2 and s['size'] >= 8:
            names.setdefault(s['value'], s['name'])
    return names


def funcs(e):
    """Map start->(end,name) for function symbols in .text."""
    out = {}
    for s in e.symbols:
        if s['info'] & 15 == 2 and s['size'] >= 8 and e.lo <= s['value'] < e.hi:
            out.setdefault(s['value'], (s['value'] + s['size'], s['name']))
    return out


def window_insns(e, start, end, names=None):
    return decode(e.b, None, start, end, e.rel, names)


def show(e, start, end, names=None, norm=False):
    for i in window_insns(e, start, end, names):
        print(f'{i["pc"]:#8x} +{i["pc"]-start:5d}  {i["norm"] if norm else i["text"]}')


def diff(e1, s1, t1, e2, s2, t2, names1=None, names2=None, context=3, maxlines=400):
    a = window_insns(e1, s1, t1, names1)
    b = window_insns(e2, s2, t2, names2)
    sa = [x['norm'] for x in a]
    sb = [x['norm'] for x in b]
    sm = difflib.SequenceMatcher(a=sa, b=sb, autojunk=False)
    print(f'# A {s1:#x}-{t1:#x} ({t1-s1} bytes, {len(a)} insns)  B {s2:#x}-{t2:#x} ({t2-s2} bytes, {len(b)} insns) ratio={sm.ratio():.4f}')
    lines = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            n = i2 - i1
            if n > 2 * context:
                for k in range(context):
                    print(f'  {a[i1+k]["pc"]-s1:6d} {b[j1+k]["pc"]-s2:6d}   {sa[i1+k]}')
                print(f'  ... {n - 2*context} equal ...')
                for k in range(n - context, n):
                    print(f'  {a[i1+k]["pc"]-s1:6d} {b[j1+k]["pc"]-s2:6d}   {sa[i1+k]}')
            else:
                for k in range(n):
                    print(f'  {a[i1+k]["pc"]-s1:6d} {b[j1+k]["pc"]-s2:6d}   {sa[i1+k]}')
            continue
        for k in range(i1, i2):
            print(f'- {a[k]["pc"]-s1:6d}          {a[k]["text"]}')
        for k in range(j1, j2):
            print(f'+        {b[k]["pc"]-s2:6d}   {b[k]["text"]}')
        lines += (i2 - i1) + (j2 - j1)
        if lines > maxlines:
            print('... truncated'); break
    return sm


if __name__ == '__main__':
    pass


def plan_map():
    """original window start -> candidate symbol name (from frontier linker plan)."""
    p = json.load(open(PKT / 'config/plan.json'))
    out = {}
    for x in p['ordered']:
        if x.get('original') is not None:
            sec = x['section']
            nm = sec.split('.text.unlikely.', 1)[-1] if sec.startswith('.text.unlikely.') else sec.split('.text.', 1)[-1]
            out[x['original']] = nm
    return out


def demangle_short(n):
    import re
    s = n
    if s.startswith('_ZN'):
        parts = []
        i = 3
        while i < len(s) and s[i].isdigit():
            j = i
            while s[j].isdigit():
                j += 1
            k = int(s[i:j])
            parts.append(s[j:j + k])
            i = j + k
        parts = [p for p in parts if not (p.startswith('h') and len(p) == 17)]
        s = '::'.join(parts)
    s = s.replace('$LT$', '<').replace('$GT$', '>').replace('$u20$', ' ').replace('$C$', ',').replace('..', '::').replace('$RF$', '&').replace('$BP$', '*').replace('$LP$', '(').replace('$RP$', ')')
    return s


def original_windows():
    d = json.loads(gzip.decompress((PKT / 'inputs/prior-inventory.json.gz').read_bytes()))
    return [(r['id'], r['start'], r['end']) for r in d['original_rows']]


def diff_masked(e1, s1, t1, e2, s2, t2, context=2, maxlines=400, mask_stack=True, mask_regs=False):
    """Diff with r10 stack offsets masked (and optionally registers)."""
    import re
    a = window_insns(e1, s1, t1)
    b = window_insns(e2, s2, t2)
    def m(x):
        t = x['norm']
        if mask_stack:
            t = re.sub(r'\[r10-\d+\]', '[r10-S]', t)
            t = re.sub(r'add64 (r\d), -\d+$', r'add64 \1, -K', t) if 'add64' in t and t.endswith(tuple('0123456789')) else t
        if mask_regs:
            t = re.sub(r'r\d', 'rX', t)
        return t
    sa = [m(x) for x in a]; sb = [m(x) for x in b]
    sm = difflib.SequenceMatcher(a=sa, b=sb, autojunk=False)
    print(f'# masked diff ratio={sm.ratio():.4f}  A {t1-s1} bytes B {t2-s2} bytes')
    lines = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        print(f'@@ A+{a[i1]["pc"]-s1 if i1 < len(a) else "end"} B+{b[j1]["pc"]-s2 if j1 < len(b) else "end"}')
        for k in range(max(0, i1-context), i1):
            print(f'  {a[k]["pc"]-s1:6d}          {a[k]["text"]}')
        for k in range(i1, i2):
            print(f'- {a[k]["pc"]-s1:6d}          {a[k]["text"]}')
        for k in range(j1, j2):
            print(f'+        {b[k]["pc"]-s2:6d}   {b[k]["text"]}')
        lines += (i2 - i1) + (j2 - j1)
        if lines > maxlines:
            print('... truncated'); break
    return sm
