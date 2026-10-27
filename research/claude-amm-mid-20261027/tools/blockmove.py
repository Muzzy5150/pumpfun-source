#!/usr/bin/env python3
"""Move one IR basic block (label) to just after another block within a function; write out file."""
import sys
src, out, fn, blk, after = sys.argv[1:6]
lines = open(src).read().split('\n')
s = next(i for i, l in enumerate(lines) if l.startswith('define') and fn in l)
e = next(i for i in range(s, len(lines)) if lines[i] == '}')
body = lines[s + 1:e]
# split into blocks
blocks = []; cur = []
for l in body:
    if l and not l.startswith(' ') and l.split(':')[0].replace('.', '').replace('_', '').isalnum() and ':' in l and not l.startswith(';'):
        if cur: blocks.append(cur)
        cur = [l]
    else:
        cur.append(l)
blocks.append(cur)
name = lambda b: b[0].split(':')[0]
bi = [i for i, b in enumerate(blocks) if name(b) == blk][0]
b = blocks.pop(bi)
ai = [i for i, x in enumerate(blocks) if name(x) == after][0]
blocks.insert(ai + 1, b)
lines[s + 1:e] = [l for b in blocks for l in b]
open(out, 'w').write('\n'.join(lines))
print('order:', [name(x) for x in blocks])
