#!/usr/bin/env python3
"""p03 (Round25 layout): exported native rent/transfer helpers, as original 0x3b738 and 0x8cc58.
The original has a single transfer body called by both rent helpers (0x3b598, 0x3b738) and
0x72810; its &Signer payer argument is not argument-promoted, i.e. the item is exported.
- legacy_native_payments.rs: `pub fn ensure_rent_exempt` (0x3b738 loads Program.info itself, no
  argument promotion) and `pub fn transfer`; buy.rs exposes `pub mod native_payments`.
- v2_native_payments.rs: drop the duplicate transfer body and call the shared helper."""
import sys, re
from pathlib import Path
s = Path(sys.argv[1]) / 'src'
buy = s / 'buy.rs'; leg = s / 'legacy_native_payments.rs'; v2 = s / 'v2_native_payments.rs'
b, l, v = buy.read_text(), leg.read_text(), v2.read_text()
if 'pub fn transfer<' in l and 'pub fn ensure_rent_exempt<' in l and 'pub(super) fn transfer<' not in v:
    print('p03 already applied'); sys.exit(0)
ob = '#[path="legacy_native_payments.rs"]\npub(crate) mod native_payments;'
assert b.count(ob) == 1 and l.count('pub(super) fn transfer<') == 1 and l.count('pub(crate) fn ensure_rent_exempt<') == 1
b = b.replace(ob, '#[path="legacy_native_payments.rs"]\npub mod native_payments;')
l = l.replace('pub(super) fn transfer<', 'pub fn transfer<').replace('pub(crate) fn ensure_rent_exempt<', 'pub fn ensure_rent_exempt<')
i = v.index('#[inline(never)]\npub(super) fn transfer<')
assert v[i:].count('fn ') == 1, 'unexpected items after v2 transfer'
v = v[:i].rstrip() + '\n'
v = v.replace('transfer(system_program.as_ref(), payer, destination, minimum)',
              'crate::legacy_buy::native_payments::transfer(system_program.as_ref(), payer, destination, minimum)')
assert 'crate::legacy_buy::native_payments::transfer(' in v
buy.write_text(b); leg.write_text(l); v2.write_text(v); print('p03 applied')
