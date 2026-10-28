#!/usr/bin/env python3
"""Compile candidate helper bodies in isolation and compare them with original windows.

  python3 -B tools/mini_cmp.py --rs vars.rs --out DIR --check name=0x17c0f0:744 [--check ...] [--diff N]

The .rs file is a `#![no_std]` library holding `#[inline(never)] pub fn` variants. It is
compiled with the identity recipe's rustc (claude-pump-work/toolchains/hybrid144, target
sbpf-solana-solana) at -C opt-level=3 -C codegen-units=1 -C overflow-checks=on
-C panic=abort, the main crate's release profile, under SP/sbf_lock.py. Each function
whose mangled name contains `name` is compared byte for byte with the original window,
then as normalized instruction text (addresses and labels dropped). This only fits
call-free windows, because relocations are not resolved in an object file.
"""
import argparse, difflib, re, struct, subprocess, sys
from pathlib import Path

HOME = Path.home()
OD = str(HOME / '.cache/solana/v1.52/platform-tools/llvm/bin/llvm-objdump')
RUSTC = '/Users/shawwalters/Documents/Codex/2026-10-24/claude-pump-work/toolchains/hybrid144/rust/bin/rustc'
LOCK = '/private/tmp/claude-501/-Users-shawwalters-Documents-Codex-2026-10-24-pumpfun-source/bf960843-6806-451b-a211-62c8b228d301/scratchpad/sbf_lock.py'
ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'evidence/original/pump/deployed.so').is_file())
ORIG = ROOT / 'evidence/original/pump/deployed.so'


def sections(blob):
    shoff, = struct.unpack_from('<Q', blob, 0x28)
    shentsize, shnum, shstrndx = struct.unpack_from('<HHH', blob, 0x3a)
    hdrs = [struct.unpack_from('<IIQQQQIIQQ', blob, shoff + i * shentsize) for i in range(shnum)]
    st = hdrs[shstrndx]
    name = lambda off: blob[st[4] + off:blob.index(b'\0', st[4] + off)].decode()
    return {name(h[0]): h for h in hdrs}


def insns(cmd):
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    res = []
    for l in out.splitlines():
        m = re.match(r'^\s+[0-9a-f]+:\s+(.*)$', l)
        if m:
            res.append(re.sub(r'\s+', ' ', re.sub(r' <[^>]*>', '', m.group(1))).strip())
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--rs', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--check', action='append', required=True, help='name=0xADDR:LEN')
    ap.add_argument('--diff', type=int, default=0, help='print up to N differing instruction lines')
    ap.add_argument('--side', action='store_true', help='print a numbered side-by-side listing')
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    obj = a.out / (a.rs.stem + '.o')
    subprocess.run(['python3', LOCK, '--slots', '6', '--name', 'sbf', '--', RUSTC, '--edition', '2021', '--crate-type', 'lib',
                    '--crate-name', a.rs.stem.replace('-', '_'), '--target', 'sbpf-solana-solana', '-C', 'opt-level=3',
                    '-C', 'panic=abort', '-C', 'codegen-units=1', '-C', 'overflow-checks=on', '--emit', 'obj',
                    '-o', str(obj), str(a.rs)], check=True)
    blob = obj.read_bytes(); secs = sections(blob)
    orig = ORIG.read_bytes(); text = sections(orig)['.text']
    syms = subprocess.run([OD, '-t', str(obj)], capture_output=True, text=True, check=True).stdout
    funcs = [l.split() for l in syms.splitlines() if ' F ' in l]
    for spec in a.check:
        name, rng = spec.split('='); addr, n = rng.split(':'); addr = int(addr, 16); n = int(n)
        want = orig[text[4] + addr - text[3]: text[4] + addr - text[3] + n]
        o_ins = insns([OD, '-d', '--no-show-raw-insn', f'--start-address={addr}', f'--stop-address={addr + n}', str(ORIG)])
        for f in funcs:
            if name not in f[-1]:
                continue
            value, sec, size = int(f[0], 16), f[3], int(f[4], 16)
            h = secs[sec]
            mine = blob[h[4] + value: h[4] + value + size]
            m_ins = insns([OD, '-d', '--no-show-raw-insn', f'--section={sec}', str(obj)])
            sm = difflib.SequenceMatcher(None, o_ins, m_ins, autojunk=False)
            print(f'{f[-1][:70]}: {size} B vs {n} B at {hex(addr)}, identical={mine == want}, insn ratio={sm.ratio():.4f}')
            if a.side:
                for i in range(max(len(o_ins), len(m_ins))):
                    x = o_ins[i] if i < len(o_ins) else ''
                    y = m_ins[i] if i < len(m_ins) else ''
                    print(f'  {i:3d} {x:34s} {"  " if x == y else "<>"} {y}')
            if a.diff and mine != want:
                shown = 0
                for tag, i1, i2, j1, j2 in sm.get_opcodes():
                    if tag == 'equal':
                        continue
                    for x in o_ins[i1:i2]:
                        print(f'    - {i1:4d} {x}'); shown += 1
                    for x in m_ins[j1:j2]:
                        print(f'    + {j1:4d} {x}'); shown += 1
                    if shown >= a.diff:
                        break


if __name__ == '__main__':
    main()
