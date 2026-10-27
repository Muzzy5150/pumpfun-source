#!/usr/bin/env python3
"""Disassemble an original window, naming call targets via inventory matches. usage: origdis.py <start> <bytes> [inventory]"""
import sys, json, gzip, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sbfdiff import sections, dis
L = Path('/private/tmp/claude-501/-Users-shawwalters-Documents-Codex-2026-10-24-pumpfun-source/bf960843-6806-451b-a211-62c8b228d301/scratchpad/lanes/pump-lo')
inv = Path(sys.argv[3]) if len(sys.argv) > 3 else L / 'wt/repro/pump/main-contract-round20-20261027/inventory.json.gz'
iv = json.loads(gzip.decompress(inv.read_bytes()))
names = {}
for w in iv['windows']:
    if w['normalized_matches']:
        names[w['start']] = re.sub(r'17h[0-9a-f]{16}E$', '', w['normalized_matches'][0]['symbol'])
    else:
        names[w['start']] = f'UNMATCHED_{w["start"]:#x}/{w["bytes"]}'
O = (L / 'wt/evidence/original/pump/deployed.so').read_bytes(); s = sections(O); t = s['.text']
a, n = int(sys.argv[1], 0), int(sys.argv[2], 0)
code = O[a - t['addr'] + t['offset']: a - t['addr'] + t['offset'] + n]
for x in dis(code, a, s, names):
    print(f'{x[0]-a:5x} {x[2]}')
