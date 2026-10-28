#!/usr/bin/env python3
"""Verify the pump-lo packet with the standard library only (works with HOME set to an empty dir).

1. Every gzipped ELF under evidence/ decompresses to bytes whose sha256 is listed in that
   directory's SHA256SUMS.
2. Every evidence build with a measure.json is re-measured against its frontier round inventory
   (repro/pump/main-contract-roundNN-20261027/inventory.json.gz) and the original
   evidence/original/pump/deployed.so, using the frontier normalizer's rule: mask internal
   direct-call immediates (op 0x85, src=1, imm != -1) and lddw values pointing into an ELF
   section. Counts, matched text bytes and gains/losses must equal measure.json.
"""
import gzip, hashlib, json, struct, sys
from pathlib import Path

sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
ROOT = next(p for p in P.parents if (p / 'evidence/original/pump/deployed.so').is_file())
sha = lambda b: hashlib.sha256(b).hexdigest()


def sections(blob):
    shoff, = struct.unpack_from('<Q', blob, 0x28)
    shentsize, shnum, shstrndx = struct.unpack_from('<HHH', blob, 0x3a)
    hdrs = [struct.unpack_from('<IIQQQQIIQQ', blob, shoff + i * shentsize) for i in range(shnum)]
    strtab = hdrs[shstrndx]
    name = lambda off: blob[strtab[4] + off:blob.index(b'\0', strtab[4] + off)].decode()
    return {name(h[0]): {'type': h[1], 'addr': h[3], 'offset': h[4], 'size': h[5], 'link': h[6], 'entsize': h[9]}
            for h in hdrs}, hdrs


def functions(blob):
    """(addr, size) of every sized STT_FUNC symbol in .symtab (ELF64 little endian)."""
    secs, hdrs = sections(blob)
    sym = secs['.symtab']; strs = hdrs[sym['link']]
    out = set()
    for i in range(sym['size'] // 24):
        st_name, st_info, st_other, st_shndx, st_value, st_size = struct.unpack_from('<IBBHQQ', blob, sym['offset'] + 24 * i)
        if st_info & 0xf == 2 and st_size:
            out.add((st_value, st_size))
    return sorted(out)


def normalize(raw, secs):
    m = bytearray(raw); i = 0
    while i < len(raw):
        op, regs, off, imm = struct.unpack_from('<BBhi', raw, i)
        if op == 0x18:
            v = struct.unpack_from('<I', raw, i + 4)[0] | struct.unpack_from('<I', raw, i + 12)[0] << 32
            if any(s['addr'] > 0 and s['addr'] <= v < s['addr'] + s['size'] for s in secs.values()):
                m[i + 4:i + 8] = bytes(4); m[i + 12:i + 16] = bytes(4)
            i += 16
        else:
            if op == 0x85 and regs >> 4 == 1 and imm != -1:
                m[i + 4:i + 8] = bytes(4)
            i += 8
    return bytes(m)


def body(blob, secs, a, n):
    t = secs['.text']; o = a - t['addr'] + t['offset']
    return blob[o:o + n]


def measure(candidate, inventory):
    ob = (ROOT / 'evidence/original/pump/deployed.so').read_bytes(); os_, _ = sections(ob)
    cs, _ = sections(candidate)
    norm, raw = set(), set()
    for a, n in functions(candidate):
        r = body(candidate, cs, a, n); raw.add((n, sha(r))); norm.add((n, sha(normalize(r, cs))))
    N = R = T = 0; cn, cr = set(), set()
    for w in inventory['windows']:
        a, n = w['start'], w['bytes']; r = body(ob, os_, a, n)
        assert sha(r) == w['raw_sha256'], hex(a)
        if (n, sha(normalize(r, os_))) in norm: N += 1; T += n; cn.add(a)
        if (n, sha(r)) in raw: R += 1; cr.add(a)
    bn = {w['start'] for w in inventory['windows'] if w['normalized_matches']}
    br = {w['start'] for w in inventory['windows'] if w['raw_match']}
    return {'normalized': N, 'raw': R, 'matched_text_bytes': T,
            'normalized_gains': [hex(x) for x in sorted(cn - bn)], 'normalized_losses': [hex(x) for x in sorted(bn - cn)],
            'raw_gains': [hex(x) for x in sorted(cr - br)], 'raw_losses': [hex(x) for x in sorted(br - cr)]}


ROUND_OF = {'r36-g5': 'repro/pump/main-contract-round36-20261027', 'r37-g6': 'repro/pump/main-contract-round37-20261027',
            'r25-g3': 'repro/pump/main-contract-round25-20261027'}


def main():
    checked = []
    for d in sorted((P / 'evidence').iterdir()):
        sums = d / 'SHA256SUMS'
        if not sums.is_file():
            continue
        listed = {line.split()[0] for line in sums.read_text().splitlines() if line.strip()}
        elfs = {}
        for gz in sorted(d.glob('*.so.gz')):
            data = gzip.decompress(gz.read_bytes()); assert sha(data) in listed, (gz, 'hash not listed')
            elfs[gz.name] = data
        result = {'evidence': d.name, 'elfs_verified': sorted(elfs)}
        packet = ROUND_OF.get(d.name)
        if packet and (d / 'measure.json').is_file() and (ROOT / packet / 'inventory.json.gz').is_file():
            inv = json.loads(gzip.decompress((ROOT / packet / 'inventory.json.gz').read_bytes()))
            got = measure(elfs['unstripped.so.gz'], inv)
            want = json.loads((d / 'measure.json').read_text())
            for k, v in got.items():
                assert want[k] == v, (d.name, k, want[k], v)
            result['remeasured'] = {k: got[k] for k in ('normalized', 'raw', 'matched_text_bytes', 'normalized_gains', 'normalized_losses', 'raw_losses')}
        elif packet:
            result['remeasured'] = 'skipped (round packet not in this checkout)'
        checked.append(result)
    assert checked, 'no evidence verified'
    print(json.dumps({'verified': True, 'evidence': checked}, indent=1))


if __name__ == '__main__':
    main()
