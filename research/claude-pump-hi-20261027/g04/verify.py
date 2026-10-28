#!/usr/bin/env python3
"""Stdlib-only check of the pump-hi g04 delivery (runs with HOME set to an empty directory).

  python3 -B research/claude-pump-hi-20261027/r37g4/verify.py

1. The gzipped ELFs decompress to the SHA-256 values in elf/SHA256SUMS, and the score
   summary refers to that unstripped ELF.
2. Each claimed window is present as a function, located through the unstripped ELF's
   symbol table, that equals the original window in evidence/original/pump/deployed.so
   after the scorer's normalization (internal call immediates and section-pointer lddw
   values masked); a raw-identical claim must match unmasked.
3. The patch is the recorded one, and the runtime summary is clean.
"""
import gzip, hashlib, json, struct, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / 'evidence/original/pump/deployed.so').is_file())
CLAIMS = {0xd5af0: (23608, 'MigrateV2$u20$as$u20$anchor_lang..Accounts', False),
          0x12ba48: (1072, '8__global10migrate_v2', False)}
PATCH_SHA256 = None  # filled below from MANIFEST.json


def sections(blob):
    shoff, = struct.unpack_from('<Q', blob, 0x28)
    shentsize, shnum, shstrndx = struct.unpack_from('<HHH', blob, 0x3a)
    hdrs = [struct.unpack_from('<IIQQQQIIQQ', blob, shoff + i * shentsize) for i in range(shnum)]
    st = hdrs[shstrndx]
    name = lambda off: blob[st[4] + off:blob.index(b'\0', st[4] + off)].decode()
    return {name(h[0]): h for h in hdrs}


def symbols(blob, secs):
    sym, strtab = secs['.symtab'], secs['.strtab']
    for i in range(sym[5] // 24):
        name_off, info, other, shndx, value, size = struct.unpack_from('<IBBHQQ', blob, sym[4] + i * 24)
        name = blob[strtab[4] + name_off:blob.index(b'\0', strtab[4] + name_off)].decode(errors='replace')
        yield name, value, size


def normalize(raw, secs):
    masked = bytearray(raw)
    i = 0
    while i < len(raw):
        op, regs, off, imm = struct.unpack_from('<BBhi', raw, i)
        if op == 0x18:
            value = struct.unpack_from('<I', raw, i + 4)[0] | struct.unpack_from('<I', raw, i + 12)[0] << 32
            if any(h[3] > 0 and h[3] <= value < h[3] + h[5] for h in secs.values()):
                masked[i + 4:i + 8] = bytes(4); masked[i + 12:i + 16] = bytes(4)
            i += 16
        else:
            if op == 0x85 and regs >> 4 == 1 and imm != -1:
                masked[i + 4:i + 8] = bytes(4)
            i += 8
    return bytes(masked)


def text_bytes(blob, secs, addr, n):
    t = secs['.text']
    return blob[t[4] + addr - t[3]: t[4] + addr - t[3] + n]


def main():
    manifest = json.loads((HERE / 'MANIFEST.json').read_text())
    sums = dict(reversed(l.split()) for l in (HERE / 'elf/SHA256SUMS').read_text().splitlines())
    elves = {}
    for name in ('candidate.so', 'unstripped.so'):
        data = gzip.decompress((HERE / 'elf' / (name + '.gz')).read_bytes())
        assert hashlib.sha256(data).hexdigest() == sums[name], name
        elves[name] = data
    summary = json.loads((HERE / 'score-summary.json').read_text())
    assert summary['candidate_sha256'] == sums['unstripped.so'], 'score summary is for another ELF'
    assert not summary['losses'] and not summary['raw_losses'], 'losses recorded'
    orig = (ROOT / 'evidence/original/pump/deployed.so').read_bytes()
    osecs = sections(orig)
    blob = elves['unstripped.so']; secs = sections(blob)
    syms = list(symbols(blob, secs))
    for addr, (n, needle, raw) in CLAIMS.items():
        want = text_bytes(orig, osecs, addr, n)
        hits = [(s, v, z) for s, v, z in syms if needle in s and z == n]
        assert hits, f'{needle}: no {n}-byte symbol'
        if raw:
            assert any(text_bytes(blob, secs, v, z) == want for _, v, z in hits), f'{hex(addr)}: bytes differ'
        else:
            nw = normalize(want, osecs)
            assert any(normalize(text_bytes(blob, secs, v, z), secs) == nw for _, v, z in hits), f'{hex(addr)}: normalized bytes differ'
        assert hex(addr) in summary['gains'], f'{hex(addr)} not in the score gains'
        print(f'{hex(addr)}: {hits[0][0][:70]} matches ({"raw" if raw else "normalized"}, {n} B)')
    assert hashlib.sha256((HERE / 'source-on-g04.patch').read_bytes()).hexdigest() == manifest['patch_sha256'], 'patch changed'
    rt = json.loads((HERE / 'runtime-corpus.json').read_text())
    assert rt['candidate_sha256'] == sums['candidate.so']
    assert not rt['errors'] and rt['diagnostic_mismatches'] == 0 and rt['suites'] == 44 and rt['case_count'] == 10468
    print('verified:', summary['normalized'], '/', summary['raw'], 'gains', summary['gains'])


if __name__ == '__main__':
    main()
