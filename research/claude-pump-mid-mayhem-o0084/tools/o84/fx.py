#!/usr/bin/env python3
"""usage: fx.py IN.ll OUT.ll [pattern] -- extract one function definition (default sell_v2_handler)."""
import re, sys
s = open(sys.argv[1]).read(); pat = sys.argv[3] if len(sys.argv) > 3 else 'sell_v2_handler'
m = re.search(r'\ndefine[^\n]*' + pat + r'[^\n]*\n', s); st = m.start() + 1
en = s.find('\n}\n', st) + 2
open(sys.argv[2], 'w').write(s[st:en])
print(sys.argv[2], en - st, s[st:en].count('\n'))
