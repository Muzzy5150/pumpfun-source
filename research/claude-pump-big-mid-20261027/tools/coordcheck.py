#!/usr/bin/env python3
"""coordcheck.py <orig_start> <unstripped.so> <symbol regex>

Positional comparison (scorer normalization) of an original window against an equal-length candidate
function, separating Source-coordinate slots (filename length / line immediates, as harness triage.py)
from body differences. Prints sizes, diff counts and the original vs candidate Source sites."""
import re, sys
from pathlib import Path
CPW = Path('/Users/shawwalters/Documents/Codex/2026-10-24/claude-pump-work')
sys.path.insert(0, str(CPW / 'harness'))
from score import sections, body, normalize, original_windows, candidate_functions  # noqa
from coords import sites, ORIG, OS  # noqa
from win import demangle  # noqa

st = int(sys.argv[1], 0); so = Path(sys.argv[2]); pat = sys.argv[3]
w = next(x for x in original_windows() if x['start'] == st)
b = so.read_bytes(); cs = sections(b)
fs = [f for f in candidate_functions(so) if re.search(pat, f[2]) or re.search(pat, demangle(f[2]))]
for s, n, nm in fs:
    print(f'cand {s:#x} {n} B {demangle(nm)[:100]}  (orig {w["bytes"]} B)')
    if n != w['bytes']:
        continue
    raw = body(b, cs, s, n)
    on = normalize(w['raw'], st, OS); cn = normalize(raw, s, cs)
    osites = sites(ORIG, OS, st, w['raw']); csites = sites(b, cs, s, raw)
    cslots = set()
    for x in osites:
        cslots |= {x['len_slot'], x['line_slot']}
    diff = [i for i in range(0, len(on), 8) if on[i:i + 8] != cn[i:i + 8]]
    nc = [d for d in diff if d not in cslots]
    print(f'  diff slots {len(diff)}  non-coordinate {len(nc)}  first non-coord offsets {[hex(x) for x in nc[:12]]}')
    print('  orig sites:', [(x['path'].split('/src/')[-1], x['line']) for x in osites])
    print('  cand sites:', [(x['path'].split('/src/')[-1], x['line']) for x in csites])
