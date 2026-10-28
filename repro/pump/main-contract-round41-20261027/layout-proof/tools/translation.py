#!/usr/bin/env python3
"""Prove a reordered build is the default-layout build with only its functions permuted.

From the two lld maps, derive the bijection between `.text` input sections
(same object/member and section name, same size). Then predict every byte of
the reordered ELF from the baseline ELF:
  * instructions are equal except direct-call immediates (src=1), which must
    reach the translated callee, and lddw values into `.text`, which must be the
    translated address; every local branch must stay inside its own section;
  * `.rodata` and every other allocated section are equal, except `.text`
    pointers in data, the dynamic symbol values and relocation offsets, which
    must equal their translations (relocation records are compared as a
    translated multiset);
  * section and program headers are equal; the entry point is translated.
No ELF is written. Exit status 0 means every byte is accounted for.
"""
import argparse
import bisect
import collections
import hashlib
import json
import struct
from pathlib import Path

import mapfile


class Elf:
    def __init__(self, path):
        self.b = Path(path).read_bytes()
        b = self.b
        assert b[:4] == b'\x7fELF' and b[4] == 2
        (self.entry, phoff, shoff) = struct.unpack_from('<QQQ', b, 24)
        phentsize, phnum, shentsize, shnum, shstrndx = struct.unpack_from('<HHHHH', b, 54)
        self.phoff, self.phnum, self.phentsize = phoff, phnum, phentsize
        hdrs = [struct.unpack_from('<IIQQQQIIQQ', b, shoff + i * shentsize) for i in range(shnum)]
        strtab = hdrs[shstrndx]
        name = lambda off: b[strtab[4] + off:b.index(b'\0', strtab[4] + off)].decode()
        self.sections = {}
        self.section_list = []
        for h in hdrs:
            s = dict(name=name(h[0]), type=h[1], flags=h[2], addr=h[3], offset=h[4], size=h[5], link=h[6], info=h[7], align=h[8], entsize=h[9])
            self.sections[s['name']] = s
            self.section_list.append(s)
        self.shoff, self.shnum, self.shentsize = shoff, shnum, shentsize

    def data(self, name):
        s = self.sections[name]
        return self.b[s['offset']:s['offset'] + s['size']]


def check(a_elf, a_map, b_elf, b_map):
    A, B = Elf(a_elf), Elf(b_elf)
    ra = [r for r in mapfile.parse(a_map) if r['out'] == '.text']
    rb = [r for r in mapfile.parse(b_map) if r['out'] == '.text']
    key = lambda r: (mapfile.owner_pattern(r), r['section'])
    ka, kb = {key(r): r for r in ra}, {key(r): r for r in rb}
    assert len(ka) == len(ra) and len(kb) == len(rb) and ka.keys() == kb.keys(), 'input-section sets differ'
    ta, tb = A.sections['.text'], B.sections['.text']
    assert (ta['addr'], ta['size']) == (tb['addr'], tb['size'])
    pos = ta['addr']
    for r in ra:
        assert r['address'] == pos and r['size'] == ka[key(r)]['size'] == kb[key(r)]['size']
        pos += r['size']
    assert pos == ta['addr'] + ta['size'], 'baseline map does not tile .text'
    pos = tb['addr']
    for r in rb:
        assert r['address'] == pos
        pos += r['size']
    assert pos == tb['addr'] + tb['size'], 'reordered map does not tile .text'
    starts = [r['address'] for r in ra]

    def pi(addr):
        i = bisect.bisect_right(starts, addr) - 1
        r = ra[i]
        assert r['address'] <= addr < r['address'] + r['size'] or addr == ta['addr'] + ta['size']
        return kb[key(r)]['address'] + addr - r['address']

    in_text = lambda v: ta['addr'] <= v < ta['addr'] + ta['size']
    counts = collections.Counter()
    atext, btext = A.data('.text'), B.data('.text')
    for r in ra:
        rbx = kb[key(r)]
        oa, ob = r['address'] - ta['addr'], rbx['address'] - tb['addr']
        i = 0
        while i < r['size']:
            ia, ib = atext[oa + i:oa + i + 8], btext[ob + i:ob + i + 8]
            op, regs, off, imm = struct.unpack('<BBhi', ia)
            if op == 0x18:
                va = struct.unpack_from('<I', atext, oa + i + 4)[0] | struct.unpack_from('<I', atext, oa + i + 12)[0] << 32
                vb = struct.unpack_from('<I', btext, ob + i + 4)[0] | struct.unpack_from('<I', btext, ob + i + 12)[0] << 32
                want = pi(va) if in_text(va) else va
                assert vb == want and ia[:4] == ib[:4] and atext[oa + i + 8:oa + i + 12] == btext[ob + i + 8:ob + i + 12], (hex(r['address'] + i), 'lddw')
                counts['lddw_text' if in_text(va) else 'lddw_other'] += 1
                i += 16
                continue
            if op == 0x85 and regs >> 4 == 1 and imm != -1:
                target = r['address'] + i + 8 + imm * 8
                want = (pi(target) - (rbx['address'] + i + 8)) // 8
                assert ib[:4] == ia[:4] and struct.unpack('<i', ib[4:])[0] == want, (hex(r['address'] + i), 'call')
                counts['direct_calls'] += 1
            else:
                assert ia == ib, (hex(r['address'] + i), 'instruction')
                if op & 7 in (5, 6) and op not in (0x85, 0x8d, 0x95):  # ja and conditional jumps
                    t = i + 8 + off * 8
                    assert 0 <= t < r['size'], (hex(r['address'] + i), 'branch leaves its section')
                    counts['local_branches'] += 1
            i += 8
    # headers
    assert A.b[:24] == B.b[:24] and A.b[32:64] == B.b[32:64], 'ELF header'
    assert B.entry == pi(A.entry)
    ph = slice(A.phoff, A.phoff + A.phnum * A.phentsize)
    assert A.b[ph] == B.b[ph], 'program headers'
    assert [(s['name'], s['type'], s['flags'], s['addr'], s['size'], s['align']) for s in A.section_list] == \
           [(s['name'], s['type'], s['flags'], s['addr'], s['size'], s['align']) for s in B.section_list], 'section headers'
    rel = lambda d: collections.Counter(struct.unpack_from('<QQ', d, o) for o in range(0, len(d), 16))
    # allocated data sections
    for s in A.section_list:
        n = s['name']
        if not s['addr'] or n in ('.text', '.dynsym', '.rel.dyn'):
            continue
        da, db = A.data(n), B.data(n)
        if n == '.data.rel.ro':
            relocated = {o for o, info in rel(A.data('.rel.dyn'))}
            for off in range(0, len(da) - len(da) % 8, 8):
                va, vb = struct.unpack_from('<Q', da, off)[0], struct.unpack_from('<Q', db, off)[0]
                # SBF stores a relocated data pointer's address in the upper 32 bits of its qword
                if s['addr'] + off in relocated and va & 0xffffffff == 0 and in_text(va >> 32):
                    assert vb == pi(va >> 32) << 32, (n, off)
                    counts['data_text_pointers'] += 1
                else:
                    assert va == vb, (n, off)
            assert da[len(da) - len(da) % 8:] == db[len(db) - len(db) % 8:]
        else:
            assert da == db, n
        counts['data_sections_checked'] += 1
    # dynsym values
    sa, sb = A.data('.dynsym'), B.data('.dynsym')
    for off in range(0, len(sa), 24):
        na, ia_, oa_, sha_, va, za = struct.unpack_from('<IBBHQQ', sa, off)
        nb, ib_, ob_, shb, vb, zb = struct.unpack_from('<IBBHQQ', sb, off)
        assert (na, ia_, oa_, sha_, za) == (nb, ib_, ob_, shb, zb)
        assert vb == (pi(va) if in_text(va) else va), ('dynsym', off)
        counts['dynsym_entries'] += 1
    # relocations as a translated multiset
    tr = lambda v: pi(v) if in_text(v) else v
    expect = collections.Counter({(tr(o), info): n for (o, info), n in rel(A.data('.rel.dyn')).items()})
    assert expect == rel(B.data('.rel.dyn')), 'relocation multiset'
    counts['relocations'] = sum(expect.values())
    counts['relocation_sites_in_text'] = sum(n for (o, info), n in expect.items() if in_text(o))
    moved = sum(1 for k in ka if ka[k]['address'] != kb[k]['address'])
    return {'sections': len(ka), 'moved_sections': moved, 'text_bytes': ta['size'],
            'entry': [A.entry, B.entry], **counts,
            'baseline_sha256': hashlib.sha256(A.b).hexdigest(), 'reordered_sha256': hashlib.sha256(B.b).hexdigest()}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--baseline', type=Path, required=True)
    ap.add_argument('--baseline-map', type=Path, required=True)
    ap.add_argument('--reordered', type=Path, required=True)
    ap.add_argument('--reordered-map', type=Path, required=True)
    ap.add_argument('--output', type=Path)
    a = ap.parse_args()
    r = check(a.baseline, a.baseline_map, a.reordered, a.reordered_map)
    r['scope'] = __doc__.split('\n')[0]
    if a.output:
        a.output.write_text(json.dumps(r, indent=1) + '\n')
    print(json.dumps(r, indent=1))


if __name__ == '__main__':
    main()
