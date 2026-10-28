#!/usr/bin/env python3
"""usage: irnorm.py IN.ll OUT.ll -- canonically rename %values and block labels in order of first appearance (for diffing)."""
import re, sys
s = open(sys.argv[1]).read()
# strip debug/metadata attachments
s = re.sub(r', !(dbg|noundef|range|align|nonnull|prof|alias\.scope|noalias|tbaa|srcloc) ![0-9]+', '', s)
names = {}
def ren(m):
    n = m.group(1)
    if n not in names: names[n] = f'v{len(names)}'
    return '%' + names[n]
lines = []
for line in s.split('\n'):
    lm = re.match(r'^([A-Za-z0-9_.$-]+):(.*)$', line)
    if lm:
        n = lm.group(1)
        if n not in names: names[n] = f'v{len(names)}'
        lines.append(names[n] + ':'); continue
    line = re.sub(r'%([A-Za-z0-9_.$-]+)', ren, line)
    lines.append(line)
open(sys.argv[2], 'w').write('\n'.join(lines))
