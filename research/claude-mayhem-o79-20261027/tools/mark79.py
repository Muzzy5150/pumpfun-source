#!/usr/bin/env python3
"""Print size / masked ratio / layout markers of O0079 for built labels (ELF) or llc .bin files."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sbfdis, llc79
B = '/Users/shawwalters/Documents/Codex/2026-10-24/claude-mayhem-work/mayhem-b/out/builds'
def code_of(label):
    if label.endswith('.bin'):
        return open(label, 'rb').read()
    C = sbfdis.elf(f'{B}/{label}/symbols.so'); cf = sbfdis.funcs(C)
    a = [a for a, (b, n) in cf.items() if 'sell_pump_swap7handler' in n][0]
    return C.b[a:cf[a][0]]
if __name__ == '__main__':
    print(f'orig: size {len(llc79.ORIG)} | {" ".join(llc79.markers(llc79.ORIG))}')
    for lab in sys.argv[1:]:
        c = code_of(lab)
        print(f'{lab}: size {len(c)} ratio {llc79.ratio(c):.4f} | {" ".join(llc79.markers(c))}')
