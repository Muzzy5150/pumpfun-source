#!/usr/bin/env python3
"""irvariants.py <module.ll> <orig_start> <fn regex> [...]: llc each matching function from a built module
(other bodies stubbed) and compare with the original window (call/lddw immediates masked)."""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import irtool
ll, start = sys.argv[1], int(sys.argv[2], 0)
text = Path(ll).read_text()
names = re.findall(r'^define [^\n]*@("[^"]+"|[\w.$]+)\(', text, re.M)
out = Path(ll).parent / 'variants'; out.mkdir(exist_ok=True)
for pat in sys.argv[3:]:
    for n in [n for n in names if re.search(pat, n)]:
        st = out / (re.sub(r'[^\w]', '_', n)[-60:] + '.ll')
        irtool.stub(ll, re.escape(n) + '$', st)
        irtool.llc(st, st.with_suffix('.o'))
        sec, code = irtool.obj_function(st.with_suffix('.o'), re.escape(n))
        irtool.compare(code, start, n[-70:])
        irtool.dis(st.with_suffix('.o'), sec, st.with_suffix('.dis'))
