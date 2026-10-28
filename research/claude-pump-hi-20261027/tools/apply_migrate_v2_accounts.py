#!/usr/bin/env python3
"""H10: MigrateV2 accounts in the original form (windows 0xd5af0 try_accounts, 0x12ba48 wrapper).

  python3 -B tools/apply_migrate_v2_accounts.py --source-directory <crate>

1. #[event_cpi] replaces the explicit UncheckedAccount event_authority/program fields.
2. The bonding_curve constraint follows the original evaluation order:
   quote_mint==bc.quote_mint || (bc.quote_mint==default && quote_mint==native).
3. Three combined field lines are split one per line, so src/migrate_v2.rs keeps its
   line count and no later Source coordinate moves.
Content-addressed: re-running is a no-op.
"""
import argparse
from pathlib import Path

SUBS = [
    ("#[derive(Accounts)]\npub struct MigrateV2<'info>{\n", "#[event_cpi]\n#[derive(Accounts)]\npub struct MigrateV2<'info>{\n"),
    ("constraint=(if bonding_curve.quote_mint==Pubkey::default(){quote_mint.key()==anchor_spl::token::spl_token::native_mint::ID}else{quote_mint.key()==bonding_curve.quote_mint}) @ PumpError::MintDoesNotMatchBondingCurve",
     "constraint=quote_mint.key()==bonding_curve.quote_mint||(bonding_curve.quote_mint==Pubkey::default()&&quote_mint.key()==anchor_spl::token::spl_token::native_mint::ID) @ PumpError::MintDoesNotMatchBondingCurve"),
    (" pub system_program:Program<'info,System>,pub pump_amm:Program<'info,admin_cto::Amm>,\n",
     " pub system_program:Program<'info,System>,\n pub pump_amm:Program<'info,admin_cto::Amm>,\n"),
    (" pub base_token_program:Interface<'info,TokenInterface>,pub quote_token_program:Interface<'info,TokenInterface>,\n",
     " pub base_token_program:Interface<'info,TokenInterface>,\n pub quote_token_program:Interface<'info,TokenInterface>,\n"),
    (" pub token_2022_program:Program<'info,Token2022>,pub associated_token_program:Program<'info,AssociatedToken>,\n",
     " pub token_2022_program:Program<'info,Token2022>,\n pub associated_token_program:Program<'info,AssociatedToken>,\n"),
    (" /// CHECK: canonical event PDA.\n #[account(seeds=[b\"__event_authority\"],bump)]pub event_authority:UncheckedAccount<'info>,\n /// CHECK: forwarded event CPI program account.\n pub program:UncheckedAccount<'info>,\n}\n", "}\n"),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--source-directory', type=Path, required=True)
    a = ap.parse_args()
    p = a.source_directory / 'src/migrate_v2.rs'
    t = p.read_text()
    before = t.count('\n')
    if all(new in t for _, new in SUBS[:5]) and SUBS[5][0] not in t:
        print('MigrateV2 accounts: already applied')
        return
    for old, new in SUBS:
        assert t.count(old) == 1, 'MigrateV2 source differs from the expected text: ' + old[:60]
        t = t.replace(old, new)
    assert t.count('\n') == before, (before, t.count('\n'))
    p.write_text(t)
    print('MigrateV2 accounts: applied')


if __name__ == '__main__':
    main()
