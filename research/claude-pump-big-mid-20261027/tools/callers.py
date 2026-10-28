#!/usr/bin/env python3
"""Callers of original windows: callers.py <orig_start> [...]. Prints each calling window (with its g04 match
symbol when matched) and the call sites. Also prints the window's callees (named through g04 matches)."""
import struct, sys
from pathlib import Path
CPW = Path('/Users/shawwalters/Documents/Codex/2026-10-24/claude-pump-work')
sys.path.insert(0, str(CPW / 'harness'))
from score import original_windows, score  # noqa
from win import demangle, ORIG, ORIG_SECS  # noqa

wins = original_windows()
cur = score(CPW / 'base/g04/unstripped.so')
starts = sorted(w['start'] for w in wins)
import bisect


def owner(addr):
    i = bisect.bisect_right(starts, addr) - 1
    return starts[i] if i >= 0 else None


def name(s):
    r = cur.get(s)
    if r and r['symbols']:
        return demangle(r['symbols'][0]).replace('pump_recovered::', '')[:100]
    b = next(w['bytes'] for w in wins if w['start'] == s)
    return f'<unmatched {b}B>'


calls = []  # (site, target)
for w in wins:
    raw = w['raw']; i = 0
    while i < len(raw):
        op = raw[i]
        if op == 0x85:
            _, regs, off, imm = struct.unpack_from('<BBhi', raw, i)
            if regs >> 4 == 1:
                calls.append((w['start'] + i, w['start'] + i + 8 + imm * 8))
        i += 16 if op == 0x18 else 8

for a in sys.argv[1:]:
    t = int(a, 0)
    print(f'== {t:#x} {name(t)}')
    for site, tgt in calls:
        if tgt == t:
            o = owner(site)
            print(f'   caller {o:#x} (site {site:#x})  {name(o)}')
    seen = []
    for site, tgt in calls:
        if owner(site) == t and tgt not in seen:
            seen.append(tgt)
    print('   callees:', ', '.join(f'{x:#x} {name(x) if x in cur else "?"}' for x in seen))
