#!/usr/bin/env python3
"""Minimal sBPF decoder + window comparison helpers (lane mayhem-a scratch tool).

Static only: reads ELF bytes, never executes anything.
"""
import json, struct, sys, difflib, gzip, collections, hashlib, re
from pathlib import Path

LANE = Path(__file__).resolve().parents[2]
import os
PKT = LANE / ('wt/research/' + os.environ.get('MAYHEM_PKT', 'mayhem-trade-origins-validator'))


def load_reader():
    import importlib.util
    s = importlib.util.spec_from_file_location('mreader', PKT / 'reader.py')
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


R = load_reader()


class E(R.Elf):
    def __init__(self, path):
        # reader.Elf resolves relative to its inputs dir; absolute paths pass through
        super().__init__(Path(path).resolve())
        self.funcs = {}
        for f in self.symbols:
            if f['info'] & 15 == 2 and f['size'] >= 8 and self.lo <= f['value'] < self.hi:
                self.funcs.setdefault(f['value'], []).append((f['name'], f['size']))


ALU = {0: 'add', 1: 'sub', 2: 'mul', 3: 'div', 4: 'or', 5: 'and', 6: 'lsh', 7: 'rsh', 8: 'neg', 9: 'mod', 10: 'xor', 11: 'mov', 12: 'arsh', 13: 'end'}
JMP = {0: 'ja', 1: 'jeq', 2: 'jgt', 3: 'jge', 4: 'jset', 5: 'jne', 6: 'jsgt', 7: 'jsge', 8: 'call', 9: 'exit', 10: 'jlt', 11: 'jle', 12: 'jslt', 13: 'jsle'}
SZ = {0: 'w', 1: 'h', 2: 'b', 3: 'dw'}


def short(name, n=70):
    try:
        import subprocess
    except Exception:
        pass
    return name[:n]


_dem = {}


def demangle(name):
    if name in _dem:
        return _dem[name]
    import re
    s = name
    m = re.match(r'_ZN(.*)17h[0-9a-f]{16}E$', s)
    if m:
        body = m.group(1)
        parts = []
        i = 0
        while i < len(body):
            j = i
            while j < len(body) and body[j].isdigit():
                j += 1
            if j == i:
                break
            n = int(body[i:j])
            parts.append(body[j:j + n])
            i = j + n
        s = '::'.join(parts)
        s = s.replace('$LT$', '<').replace('$GT$', '>').replace('$u20$', ' ').replace('..', '::').replace('$C$', ',').replace('$RF$', '&').replace('$LP$', '(').replace('$RP$', ')').replace('$BP$', '*').replace('$u7b$', '{').replace('$u7d$', '}').replace('$u5b$', '[').replace('$u5d$', ']').replace('$u3b$', ';')
    _dem[name] = s
    return s


def decode(elf, start, end, namer=None, mask=True):
    """Yield (pc, text, kind) tuples with normalized operand text."""
    out = []
    at = start
    while at < end:
        op, reg, off, imm = struct.unpack_from('<BBhi', elf.b, at)
        dst, src = reg & 15, reg >> 4
        cls = op & 7
        rel = elf.rel.get(at)
        idx = (at - start) // 8
        if op == 0x18:
            imm2 = struct.unpack_from('<i', elf.b, at + 12)[0]
            val = (imm & 0xffffffff) | ((imm2 & 0xffffffff) << 32)
            if rel is not None and rel['type'] == 8:
                t = f'lddw r{dst}, DATA' if mask else f'lddw r{dst}, {val:#x}'
                if namer:
                    t += namer('data', val)
            else:
                t = f'lddw r{dst}, {val:#x}'
            out.append((at, t, 'lddw'))
            at += 16
            continue
        if cls in (4, 7):
            name = ALU.get(op >> 4, f'alu?{op:#x}')
            w = '64' if cls == 7 else '32'
            if op >> 4 == 13:
                t = f'{"be" if op & 8 else "le"}{imm} r{dst}'
            elif op >> 4 == 8:
                t = f'neg{w} r{dst}'
            elif op & 8:
                t = f'{name}{w} r{dst}, r{src}'
            else:
                t = f'{name}{w} r{dst}, {imm:#x}' if abs(imm) > 9 else f'{name}{w} r{dst}, {imm}'
            out.append((at, t, 'alu'))
        elif cls == 1:
            t = f'ldx{SZ[(op >> 3) & 3]} r{dst}, [r{src}{off:+#x}]'
            out.append((at, t, 'ldx'))
        elif cls == 2:
            t = f'st{SZ[(op >> 3) & 3]} [r{dst}{off:+#x}], {imm:#x}'
            out.append((at, t, 'st'))
        elif cls == 3:
            t = f'stx{SZ[(op >> 3) & 3]} [r{dst}{off:+#x}], r{src}'
            out.append((at, t, 'stx'))
        elif cls in (5, 6):
            code = op >> 4
            name = JMP.get(code, f'j?{op:#x}')
            if op == 0x85:
                if rel is not None and rel['type'] == 10:
                    t = f'syscall {rel["symbol"]}'
                elif src == 1:
                    tgt = at + 8 + imm * 8
                    t = 'call ' + (namer('call', tgt) if namer else f'{tgt:#x}')
                else:
                    t = f'call imm {imm:#x}'
                out.append((at, t, 'call'))
            elif op == 0x8d:
                t = f'callx r{imm if imm else dst}'
                out.append((at, t, 'callx'))
            elif op == 0x95:
                out.append((at, 'exit', 'exit'))
            else:
                tgt = at + 8 + off * 8
                rel_t = (tgt - start) // 8
                if code == 0:
                    t = f'ja @{rel_t}'
                elif op & 8:
                    t = f'{name}{"32" if cls == 6 else ""} r{dst}, r{src}, @{rel_t}'
                else:
                    t = f'{name}{"32" if cls == 6 else ""} r{dst}, {imm:#x}, @{rel_t}'
                if not (start <= tgt < end):
                    t += ' OUT'
                out.append((at, t, 'jmp'))
        else:
            out.append((at, f'?? {elf.b[at:at+8].hex()}', '?'))
        at += 8
    # rewrite slot-relative branch targets (@slot) to listing indices (@iN)
    slot2idx = {(pc - start) // 8: i for i, (pc, _, _) in enumerate(out)}
    def fix(m):
        sl = int(m.group(1))
        return f'@{slot2idx[sl]}' if sl in slot2idx else f'@s{sl}'
    out = [(pc, re.sub(r'@(-?\d+)', fix, t) if k == 'jmp' else t, k) for pc, t, k in out]
    return out


def load_audit():
    return json.loads((PKT / 'audit.json').read_text())


def orig_rows():
    a = load_audit()
    return a['rows']
