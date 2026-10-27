#!/usr/bin/env python3
"""p04: V2 rent helper (original 0x3b598) keeps its leading size parameter in the exported
signature but funds the zero-data rent minimum, exactly as the original body: every original
caller passes r2=0 and the callee ignores r2, otherwise identical to the 3-arg helper 0x3b738."""
import sys
from pathlib import Path
p = Path(sys.argv[1]) / 'src/v2_native_payments.rs'; t = p.read_text()
if '    _size: usize,\n' in t: print('p04 already applied'); sys.exit(0)
assert t.count('    size: usize,\n') == 1 and t.count('minimum_balance(size)') == 1
p.write_text(t.replace('    size: usize,\n', '    _size: usize,\n').replace('minimum_balance(size)', 'minimum_balance(0)')); print('p04 applied')
