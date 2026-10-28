#!/usr/bin/env python3
"""Stdlib-only verification of the pump-mid packet's recorded artifacts and window claims.

Checks the artifact SHA-256 sums, the sources recorded in CANDIDATE.json, and
recomputes the normalized/raw window counts of the shipped unstripped ELF against
`evidence/original/pump/deployed.so`. Original windows come from the base round's
inventory. Candidate bodies come from the ELF's own `.symtab` FUNC symbols, using
the repository normalizer (internal direct-call immediates and in-image lddw values masked).
No compiler, objdump or third-party package is used.
"""
import gzip, hashlib, json, struct, sys
from pathlib import Path

P = Path(__file__).resolve().parent
ROOT = next(p for p in P.parents if (p / 'evidence/original/pump/deployed.so').is_file())
sha = lambda b: hashlib.sha256(b).hexdigest()


def sections(blob):
    shoff, = struct.unpack_from('<Q', blob, 0x28)
    shentsize, shnum, shstrndx = struct.unpack_from('<HHH', blob, 0x3a)
    hdrs = [struct.unpack_from('<IIQQQQIIQQ', blob, shoff + i * shentsize) for i in range(shnum)]
    strtab = hdrs[shstrndx]
    name = lambda off: blob[strtab[4] + off:blob.index(b'\0', strtab[4] + off)].decode()
    return {name(h[0]): {'type': h[1], 'addr': h[3], 'offset': h[4], 'size': h[5], 'link': h[6], 'entsize': h[9], 'index': i}
            for i, h in enumerate(hdrs)}, hdrs


def normalize(raw, address, secs):
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


def body(blob, secs, addr, size):
    t = secs['.text']; o = addr - t['addr'] + t['offset']
    return blob[o:o + size]


def functions(blob):
    secs, hdrs = sections(blob)
    sym = secs['.symtab']; strs = hdrs[sym['link']]; text = secs['.text']
    out = []
    for k in range(sym['size'] // 24):
        st_name, st_info, st_other, st_shndx, st_value, st_size = struct.unpack_from('<IBBHQQ', blob, sym['offset'] + 24 * k)
        if st_info & 0xf == 2 and st_shndx == text['index'] and st_size:
            out.append((st_value, st_size))
    return secs, sorted(set(out))


def main():
    rec = json.loads((P / 'CANDIDATE.json').read_text())
    sums = dict(reversed(line.split()) for line in (P / 'artifacts/SHA256SUMS').read_text().splitlines() if line.strip())
    cand = gzip.decompress((P / 'artifacts/candidate.so.gz').read_bytes())
    uns = gzip.decompress((P / 'artifacts/unstripped.so.gz').read_bytes())
    assert sha(cand) == sums['candidate.so'] == rec['candidate_sha256'], 'stripped artifact hash'
    assert sha(uns) == sums['unstripped.so'] == rec['unstripped_sha256'], 'unstripped artifact hash'
    for name, ch in rec['changed_files'].items():
        assert sha((P / 'source/programs/pump' / name).read_bytes()) == ch['sha256'], name
    orig = (ROOT / 'evidence/original/pump/deployed.so').read_bytes(); osec, _ = sections(orig)
    inv = json.loads(gzip.decompress((ROOT / rec['base_round'] / 'inventory.json.gz').read_bytes()))
    csec, funcs = functions(uns)
    by = {}
    for a, n in funcs:
        raw = body(uns, csec, a, n)
        by.setdefault((n, normalize(raw, a, csec)), []).append(raw)
    norm = raw_n = text = 0; gained = []; lost = []; raw_lost = []
    for w in inv['windows']:
        s, n = w['start'], w['bytes']; ob = body(orig, osec, s, n)
        hits = by.get((n, normalize(ob, s, osec)), [])
        ok = bool(hits); r = any(h == ob for h in hits)
        norm += ok; raw_n += r; text += n if ok else 0
        if ok and not w['normalized_matches']: gained.append(hex(s))
        if not ok and w['normalized_matches']: lost.append(hex(s))
        if not r and w['raw_match']: raw_lost.append(hex(s))
    claim = json.loads((P / 'CLAIM.json').read_text())
    result = {'normalized': norm, 'raw': raw_n, 'matched_text_bytes': text, 'gained': gained, 'lost': lost, 'raw_lost': raw_lost}
    for k in ['normalized', 'raw', 'matched_text_bytes', 'gained', 'lost', 'raw_lost']:
        assert result[k] == claim[k], (k, result[k], claim[k])
    print(json.dumps({'verified': True, **result}))


if __name__ == '__main__':
    sys.exit(main())
