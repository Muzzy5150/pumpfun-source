#!/usr/bin/env python3
import re, sys
src, out, fn = sys.argv[1:4]
lines = open(src).read().split('\n')
s = next(i for i, l in enumerate(lines) if l.startswith('define') and fn in l)
e = next(i for i in range(s, len(lines)) if lines[i] == '}')
for i in range(s + 1, e):
    lines[i] = re.sub(r'%(\d+)\b', r'%n\1', lines[i])
open(out, 'w').write('\n'.join(lines))
