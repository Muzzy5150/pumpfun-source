#!/usr/bin/env python3
"""Stdlib-only check of the pump-hi r37g4 delivery (runs with HOME set to an empty directory).

  python3 -B research/claude-pump-hi-20261027/r37g4/verify.py

1. The gzipped ELFs decompress to the SHA-256 values in elf/SHA256SUMS, and the score
   summary refers to that unstripped ELF.
2. Each claimed window is present as a function, located through the unstripped ELF's
   symbol table, whose bytes are identical to the original window in
   evidence/original/pump/deployed.so. The claimed windows contain no call or lddw
   operands, so raw equality is the scorer's normalized equality.
3. The patch is the recorded one, and the runtime summary is clean.
"""
import gzip, hashlib, json, struct, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / 'evidence/original/pump/deployed.so').is_file())
CLAIMS = {0x17c0f0: (744, 'required_quote_account_len')}
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
    for addr, (n, needle) in CLAIMS.items():
        want = text_bytes(orig, osecs, addr, n)
        hits = [(s, v, z) for s, v, z in syms if needle in s and z == n]
        assert hits, f'{needle}: no {n}-byte symbol'
        assert any(text_bytes(blob, secs, v, z) == want for _, v, z in hits), f'{hex(addr)}: bytes differ'
        assert hex(addr) in summary['gains'], f'{hex(addr)} not in the score gains'
        print(f'{hex(addr)}: {hits[0][0][:60]} is byte-identical ({n} B)')
    assert hashlib.sha256((HERE / 'source-on-r37g4.patch').read_bytes()).hexdigest() == manifest['patch_sha256'], 'patch changed'
    rt = json.loads((HERE / 'runtime-migrate_v2.json').read_text())
    assert rt['candidate_sha256'] == sums['candidate.so'] and not rt['errors'] and rt['diagnostic_mismatches'] == 0
    print('verified:', summary['normalized'], '/', summary['raw'], 'gains', summary['gains'])


if __name__ == '__main__':
    main()
