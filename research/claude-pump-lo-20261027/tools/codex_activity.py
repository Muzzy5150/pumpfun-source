#!/usr/bin/env python3
"""Grep recently-modified Codex work files for window addresses (hex + decimal), one combined regex."""
import os, sys, time, json, re, collections
from pathlib import Path
REPO = Path('/Users/shawwalters/Documents/Codex/2026-10-24/pumpfun-source/work')
hours = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
wins = json.load(open(sys.argv[1]))
cut = time.time() - hours * 3600
files = []
for d in REPO.glob('parallel-main-*'):
    if not d.is_dir(): continue
    for root, dirs, fs in os.walk(d):
        dirs[:] = [x for x in dirs if x not in ('target', 'cargo-home', 'source', 'registry', '.git', 'deps', 'incremental', 'build', 'primary')]
        for f in fs:
            p = Path(root) / f
            if p.suffix not in ('.json', '.md', '.py', '.txt', '.patch', '.tsv'): continue
            try: st = p.stat()
            except OSError: continue
            if st.st_mtime < cut or st.st_size > 3_000_000: continue
            files.append(p)
print(len(files), 'recent files', file=sys.stderr)
key = {}
alts = []
for w in wins:
    a = w['start']; key['0x%x' % a] = a; alts.append('0x0*%x' % a)
    if a > 65536: key[str(a)] = a; alts.append(str(a))
rx = re.compile(r'(?<![0-9a-fA-Fx])(' + '|'.join(sorted(alts, key=len, reverse=True)) + r')(?![0-9a-fA-F])')
hits = collections.defaultdict(set)
for p in files:
    try: t = p.read_text(errors='ignore')
    except OSError: continue
    for m in set(rx.findall(t)):
        s = m.lower()
        a = key.get(s) if s in key else key.get('0x%x' % int(s, 16)) if s.startswith('0x') else None
        if a is not None: hits[a].add(str(p.relative_to(REPO)))
for w in wins:
    h = hits[w['start']]
    dirs = collections.Counter(x.split('/')[0] for x in h)
    print(hex(w['start']), w['bytes'], len(h), ' '.join(f'{k}({v})' for k, v in dirs.most_common(6))[:400])
