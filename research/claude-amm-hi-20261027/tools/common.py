"""Shared helpers for lane amm-hi analysis (read-only on evidence)."""
import gzip, json, struct, sys, hashlib, collections
from pathlib import Path
SP = Path('/private/tmp/claude-501/-Users-shawwalters-Documents-Codex-2026-10-24-pumpfun-source/bf960843-6806-451b-a211-62c8b228d301/scratchpad')
LANE = SP / 'lanes/amm-hi'
WT = LANE / 'wt'
sys.path.insert(0, str(WT / 'repro/pump_amm/claim-self-transfer-v144/static-tool'))
from elf_reader import Elf  # noqa
FRONT = WT / 'repro/pump_amm/account-context-recovery-20261027'
ORIG = WT / 'evidence/original/pump_amm/deployed.so'
LO, HI = 0x73ef0, 0xf6eb0

def load_measure(path=FRONT / 'results/measurement.json.gz'):
    p = Path(path)
    data = p.read_bytes()
    if p.suffix == '.gz':
        data = gzip.decompress(data)
    return json.loads(data)

def windows(elf):
    entries = sorted(set(elf.entries) | {elf.lo})
    return list(zip(entries, entries[1:] + [elf.hi]))

def section_of(elf, addr):
    for name, s in elf.secs.items():
        if s[3] and s[3] <= addr < s[3] + s[5]:
            return name, s
    return None, None

def read_cstr(elf, addr, n=80):
    name, s = section_of(elf, addr)
    if not s:
        return None
    off = s[4] + (addr - s[3])
    return elf.b[off:off + n]

def lddw_targets(elf, start, end):
    out = []
    b = elf.b
    for at in range(start, end, 8):
        if b[at] == 0x18 and at in elf.relocations and elf.relocations[at]['type'] == 8:
            v = struct.unpack_from('<I', b, at + 4)[0] | (struct.unpack_from('<I', b, at + 12)[0] << 32)
            out.append((at - start, v))
    return out

def insns(elf, start, end):
    b = elf.b
    res = []
    at = start
    while at < end:
        op = b[at]
        regs = b[at + 1]
        off = struct.unpack_from('<h', b, at + 2)[0]
        imm = struct.unpack_from('<i', b, at + 4)[0]
        res.append((at, op, regs & 0xf, regs >> 4, off, imm))
        at += 16 if op == 0x18 else 8
    return res
