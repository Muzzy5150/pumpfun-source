#!/usr/bin/env python3
"""Print size + normalized/raw sha of named candidate functions across builds."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sbf
name = sys.argv[1]
for p in sys.argv[2:]:
    E = sbf.E(p)
    hits = [(a, n, s) for a, ns in E.funcs.items() for n, s in ns if name in n]
    for a, n, s in hits:
        w = E.window(a, a + s)
        print(f'{Path(p).parent.name:28s} {a:7d} {s:6d} norm={w["normalized_sha256"][:12]} raw={w["raw_sha256"][:12]}')
