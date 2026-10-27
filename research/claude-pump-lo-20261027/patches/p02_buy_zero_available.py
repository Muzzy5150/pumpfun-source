#!/usr/bin/env python3
"""p02: legacy buy partial-fill zero check binds the clamped amount once.
require_gt! evaluates its operand twice; with the bound local the error path's
compared value is provably 0, as in every original with_values::<u64,i32> caller (0x340)."""
import sys
from pathlib import Path
crate = Path(sys.argv[1])
p = crate / 'src/buy.rs'; t = p.read_text()
old = 'if !exact && partial{require_gt!(input.min(c.real_token_reserves),0,PumpError::BuyZeroAmount);}'
new = 'if !exact && partial{let available=input.min(c.real_token_reserves);require_gt!(available,0,PumpError::BuyZeroAmount);}'
if new in t: print('p02 already applied'); sys.exit(0)
assert t.count(old) == 1, 'p02 anchor missing'
p.write_text(t.replace(old, new)); print('p02 applied', p)
