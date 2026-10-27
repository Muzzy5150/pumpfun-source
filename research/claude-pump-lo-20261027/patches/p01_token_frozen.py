#!/usr/bin/env python3
"""p01: original 0x29518 token_frozen helper owns the empty-account check (returns Ok(false)).
Callers that guarded token_frozen with !data_is_empty() rely on the helper instead."""
import sys
from pathlib import Path
crate = Path(sys.argv[1])
cands = [p for p in crate.joinpath('src').rglob('*.rs') if 'fn token_frozen(' in p.read_text()]
assert len(cands) == 1, cands
p = cands[0]; t = p.read_text()
old_h = 'fn token_frozen(a:&AccountInfo)->Result<bool>{let d=a.try_borrow_data()?;'
new_h = 'fn token_frozen(a:&AccountInfo)->Result<bool>{if a.data_is_empty(){return Ok(false);}let d=a.try_borrow_data()?;'
a = 'shared&&holder&&!a.coin_creator_vault_ata.data_is_empty()&&token_frozen(&a.coin_creator_vault_ata.to_account_info())?'
b = 'wallet&&!a.current_creator_quote_token_account.data_is_empty()&&token_frozen(&a.current_creator_quote_token_account.to_account_info())?'
if new_h in t: print('p01 already applied', p); sys.exit(0)
for s in (old_h, a, b): assert t.count(s) == 1, ('missing', s)
t = t.replace(old_h, new_h)
t = t.replace(a, 'shared&&holder&&token_frozen(&a.coin_creator_vault_ata.to_account_info())?')
t = t.replace(b, 'wallet&&token_frozen(&a.current_creator_quote_token_account.to_account_info())?')
p.write_text(t); print('p01 applied', p)
