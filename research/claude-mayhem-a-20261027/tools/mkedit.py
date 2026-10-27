#!/usr/bin/env python3
"""mkedit.py OUT.py FILE 'old'=>'new' ... : write an edit script doing exact single replacements in FILE."""
import sys, json
out, f = sys.argv[1], sys.argv[2]
pairs = []
for arg in sys.argv[3:]:
    old, new = arg.split('=>', 1)
    pairs.append((old.encode().decode('unicode_escape'), new.encode().decode('unicode_escape')))
open(out, 'w').write(f'''from pathlib import Path
PAIRS = {json.dumps(pairs)}
def edit(root):
    p = root / {f!r}
    s = p.read_text()
    for old, new in PAIRS:
        assert s.count(old) == 1, (old, s.count(old))
        s = s.replace(old, new)
    p.write_text(s)
''')
