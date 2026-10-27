#!/usr/bin/env python3
"""Negative tests for verify.py (standard library only, temporary copies only).

Each case copies the files verify.py reads into a temporary repository root,
mutates one of them, and requires verify.py to fail; the unmodified copy must pass.
"""
import gzip, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PARENT = 'research/mayhem-quotes-current-recovery-20261027'
NEEDED = [f'{PARENT}/builds/current/candidate.so.gz', f'{PARENT}/builds/current/symbols.so.gz',
          f'{PARENT}/source-inputs.json', f'{PARENT}/overrides/src/state.rs']


def stage(td):
    t = Path(td)
    for rel in NEEDED:
        (t / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, t / rel)
    pkt = t / 'research/claude-mayhem-a-20261027'
    shutil.copytree(HERE / 'layers/initializer-safe-form', pkt / 'layers/initializer-safe-form')
    shutil.copyfile(HERE / 'verify.py', pkt / 'verify.py')
    return t, pkt


def run(pkt, root):
    r = subprocess.run([sys.executable, '-I', '-B', str(pkt / 'verify.py'), '--repository-root', str(root)],
                       capture_output=True, text=True)
    return r.returncode


def mutate_state(pkt, root):
    p = pkt / 'layers/initializer-safe-form/source/src/state.rs'
    p.write_text(p.read_text().replace('let mut mint_key=Pubkey::default();', 'let mut mint_key = Pubkey::default();'))


def mutate_elf(pkt, root):
    p = pkt / 'layers/initializer-safe-form/artifacts/candidate.so.gz'
    b = bytearray(gzip.decompress(p.read_bytes())); b[-1] ^= 1
    p.write_bytes(gzip.compress(bytes(b), mtime=0))


def mutate_parent_state(pkt, root):
    p = root / PARENT / 'overrides/src/state.rs'
    p.write_text(p.read_text() + '\n')


def add_unsafe(pkt, root):
    for rel in ['source/src/state.rs']:
        p = pkt / 'layers/initializer-safe-form' / rel
        p.write_text(p.read_text().replace('pub fn initialize(ctx:', 'pub fn initialize(ctx:', 1))
    patch = pkt / 'layers/initializer-safe-form/source.patch'
    patch.write_text(patch.read_text().replace('+pub fn initialize(ctx:Context<crate::InitializeMayhemState>)->Result<()> { initialize_state(',
                                               '+pub fn initialize(ctx:Context<crate::InitializeMayhemState>)->Result<()> { unsafe{} initialize_state('))


def main():
    with tempfile.TemporaryDirectory() as td:
        root, pkt = stage(td)
        assert run(pkt, root) == 0, 'unmodified copy must verify'
    for name, fn in [('tampered source', mutate_state), ('tampered ELF', mutate_elf),
                     ('tampered parent state', mutate_parent_state), ('patch adds unsafe', add_unsafe)]:
        with tempfile.TemporaryDirectory() as td:
            root, pkt = stage(td)
            fn(pkt, root)
            assert run(pkt, root) != 0, f'{name} was not rejected'
            print(f'rejected: {name}')
    print('OK: 4 negative cases rejected, unmodified copy verifies')


if __name__ == '__main__':
    main()
