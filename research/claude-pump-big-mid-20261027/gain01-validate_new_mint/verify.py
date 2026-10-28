#!/usr/bin/env python3
"""Stdlib-only check of a pump-big-mid gain directory (driven by its MANIFEST.json).

  python3 -B research/claude-pump-big-mid-20261027/<gain dir>/verify.py

Needs no toolchain, cache or network and passes with HOME set to an empty directory:
1. elf/*.gz decompress to the SHA-256 values in elf/SHA256SUMS, and the manifest records the same hashes;
   score-summary.json describes that unstripped ELF and records no normalized or raw losses (same for the
   L06 score summary when present).
2. Every claimed window is a function of the unstripped ELF (found through its symbol table) with the
   original window's length and equal bytes after the scorer's normalization (internal call immediates and
   section-pointer lddw values masked), compared against evidence/original/pump/deployed.so.
3. source.patch has the recorded hash; runtime summaries are for the shipped stripped ELF and are clean
   (every suite at its expected case count, no errors, no paired diagnostic mismatches).
"""
import gzip, hashlib, json, struct
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / 'evidence/original/pump/deployed.so').is_file())
sha = lambda b: hashlib.sha256(b).hexdigest()


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
        yield blob[strtab[4] + name_off:blob.index(b'\0', strtab[4] + name_off)].decode(errors='replace'), value, size


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
    m = json.loads((HERE / 'MANIFEST.json').read_text())
    sums = dict(reversed(line.split()) for line in (HERE / 'elf/SHA256SUMS').read_text().splitlines())
    elves = {}
    for name in ('candidate.so', 'unstripped.so'):
        data = gzip.decompress((HERE / 'elf' / (name + '.gz')).read_bytes())
        assert sha(data) == sums[name] == m['elf_sha256'][name], name
        elves[name] = data
    s = json.loads((HERE / 'score-summary.json').read_text())
    assert s['candidate_sha256'] == sums['unstripped.so'], 'score summary is for another ELF'
    assert not s['losses'] and not s['raw_losses'], 'losses recorded'
    assert sorted(s['gains']) == sorted(m['windows']), (s['gains'], m['windows'])
    if (HERE / 'L06-score-summary.json').exists():
        s6 = json.loads((HERE / 'L06-score-summary.json').read_text())
        assert not s6['losses'] and not s6['raw_losses'] and set(m['windows']) <= set(s6['gains'])
    orig = (ROOT / 'evidence/original/pump/deployed.so').read_bytes()
    assert sha(orig) == m['original_sha256'], 'original image differs'
    osecs = sections(orig)
    blob = elves['unstripped.so']; secs = sections(blob)
    syms = list(symbols(blob, secs))
    for addr_s, w in m['windows'].items():
        addr, n = int(addr_s, 16), w['bytes']
        want = normalize(text_bytes(orig, osecs, addr, n), osecs)
        hits = [(name, v, z) for name, v, z in syms if w['symbol_needle'] in name and z == n]
        assert hits, f"{w['symbol_needle']}: no {n}-byte symbol"
        assert any(normalize(text_bytes(blob, secs, v, z), secs) == want for _, v, z in hits), f'{addr_s}: bytes differ'
    assert sha((HERE / 'source.patch').read_bytes()) == m['patch_sha256'], 'patch hash'
    for rt in m['runtime']:
        r = json.loads((HERE / rt).read_text())
        assert r['candidate_sha256'] == sums['candidate.so'], rt
        assert r['original_sha256'] == m['original_sha256'], rt
        assert not r['errors'] and r['diagnostic_mismatches'] == 0, rt
        assert r['case_count'] == r['expected_cases'] and all(r['counts'][k] == r['expected'][k] for k in r['counts']), rt
    print(f"OK {HERE.name}: windows {', '.join(m['windows'])} match the original; ELF, score, patch and runtime summaries consistent")


if __name__ == '__main__':
    main()
