#!/usr/bin/env python3
"""mkvariant.py <name> <file-rel-to-src> <old-file> <new-file> [base-dir]: copy base crate, replace exact text."""
import sys, shutil, subprocess
from pathlib import Path
L = Path('/private/tmp/claude-501/-Users-shawwalters-Documents-Codex-2026-10-24-pumpfun-source/bf960843-6806-451b-a211-62c8b228d301/scratchpad/lanes/pump-lo')
name, rel, oldf, newf = sys.argv[1:5]
base = Path(sys.argv[5]) if len(sys.argv) > 5 else L / 'wt/programs/pump'
dst = L / 'variants' / name
if dst.exists(): shutil.rmtree(dst)
subprocess.check_call(['cp', '-c', '-R', str(base), str(dst)])
p = dst / 'src' / rel
t = p.read_text(); old = Path(oldf).read_text(); new = Path(newf).read_text()
assert t.count(old) == 1, ('old text occurrences', t.count(old))
p.write_text(t.replace(old, new))
print(dst)
