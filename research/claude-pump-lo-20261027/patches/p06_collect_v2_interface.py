#!/usr/bin/env python3
"""p06: CollectCreatorFeeV2 handler (original 0x2a8e8).
- the shared creator-fee collector is an exported item: the original passes quote_token_program
  as the &Interface field address (no argument promotion) and system_program as an already
  loaded &AccountInfo (handler passes `a.system_program.as_ref()`; AdminCto call updated alike);
- the event is emitted by reference (`emit!(event); emit_cpi!(event);`, both macros borrow it):
  the original serializes both copies from one event value, with no clone."""
import sys
from pathlib import Path
s = Path(sys.argv[1]) / 'src'
c = s / 'creator/collect_creator_fee.rs'; a = s / 'creator/admin_cto.rs'
t, u = c.read_text(), a.read_text()
if 'pub fn collect<' in t and 'emit!(event);emit_cpi!(event);' in t: print('p06 already applied'); sys.exit(0)
reps = [("pub(crate) fn collect<'info>(", "pub fn collect<'info>("),
        ("quote_token_program:&Interface<'info,anchor_spl::token_interface::TokenInterface>,system_program:&Program<'info,System>,",
         "quote_token_program:&Interface<'info,anchor_spl::token_interface::TokenInterface>,system_program:&AccountInfo<'info>,"),
        ("a.quote_mint.as_ref().as_ref(),&a.quote_token_program,&a.system_program)",
         "a.quote_mint.as_ref().as_ref(),&a.quote_token_program,a.system_program.as_ref())"),
        ("creator:a.creator.key(),creator_fee:amount,quote_mint};emit!(event.clone());emit_cpi!(event);",
         "creator:a.creator.key(),creator_fee:amount,quote_mint};emit!(event);emit_cpi!(event);")]
for o, n in reps:
    assert t.count(o) == 1, ('anchor missing', o); t = t.replace(o, n)
o = "a.quote_mint.as_ref().as_ref(),&a.quote_token_program,&a.system_program)"
assert u.count(o) == 1, 'admin_cto anchor missing'
u = u.replace(o, "a.quote_mint.as_ref().as_ref(),&a.quote_token_program,a.system_program.as_ref())")
c.write_text(t); a.write_text(u); print('p06 applied')
