#!/usr/bin/env python3
"""Apply this lane's post-composite fixes to a crate that already carries change 7 as
published in ed6d9819c (e.g. the Pump integration composite i1b).

  python tools/apply_on_composite.py --source-directory <crate> [--no-migrate-v2-fix]
      [--no-collect-fix] [--no-fee-8]

1. migrate_v2 fix: undo the rejected change-7 entries (tools/cpi_changes.json
   rejected_not_applied), restoring the frontier hand-built CPIs in migrate_v2.rs.
2. collect fix (0x10b0b8): rewrite the ed6d9819c collect_coin_creator_fee lines to the
   current cpi_changes.json form (accounts built inside `if !frozen`).
3. change 8 (0x1176e0): tools/apply_lane_changes.py FEE_SUBS.
Every step is content-addressed: it is skipped when the target text is already present
and fails when neither the source nor the target text is found.
"""
import argparse, json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import apply_lane_changes as lane  # noqa: E402

# collect_coin_creator_fee lines exactly as ed6d9819c's cpi_changes.json wrote them
ED6_COLLECT = [
    "  let cpi_accounts=crate::pump_amm::cpi::accounts::CollectCoinCreatorFee{quote_mint:a.quote_mint.to_account_info(),quote_token_program:a.quote_token_program.to_account_info(),coin_creator:a.current_creator.to_account_info(),coin_creator_vault_authority:a.coin_creator_vault_authority.to_account_info(),coin_creator_vault_ata:a.coin_creator_vault_ata.to_account_info(),coin_creator_token_account:a.current_creator_quote_token_account.to_account_info(),event_authority:a.pump_amm_event_authority.to_account_info(),program:a.pump_amm.to_account_info()};",
    "  if !frozen{crate::pump_amm::cpi::collect_coin_creator_fee(CpiContext::new(a.pump_amm.to_account_info(),cpi_accounts))?;}",
]


def replace_line(path, old, new):
    lines = path.read_text().split('\n')
    if new in lines:
        return 'already'
    assert lines.count(old) == 1, f'{path.name}: neither the source nor the target line was found: {old[:70]}'
    lines[lines.index(old)] = new
    path.write_text('\n'.join(lines))
    return 'applied'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--source-directory', type=Path, required=True)
    ap.add_argument('--no-migrate-v2-fix', action='store_true')
    ap.add_argument('--no-collect-fix', action='store_true')
    ap.add_argument('--no-fee-8', action='store_true')
    a = ap.parse_args()
    crate = a.source_directory
    spec = json.loads((HERE / 'cpi_changes.json').read_text())
    if not a.no_migrate_v2_fix:
        states = []
        for c in spec['rejected_not_applied']['entries']:
            p = crate / c['file']
            t = p.read_text()
            if c['old'] in t and c['new'] not in t:
                states.append('already')
                continue
            assert t.count(c['new']) == 1, f'{c["file"]}: rejected change-7 text not found: {c["new"][:70]}'
            p.write_text(t.replace(c['new'], c['old']))
            states.append('applied')
        print('migrate_v2 fix (frontier hand-built CPIs restored):', states)
    if not a.no_collect_fix:
        current = [c for c in spec['line_replacements'] if c['file'] == 'src/creator/admin_cto.rs' and ('CollectCoinCreatorFee' in c['new'] or 'collect_coin_creator_fee(' in c['new'])]
        assert len(current) == 2, current
        p = crate / 'src/creator/admin_cto.rs'
        states = [replace_line(p, old, c['new']) for old, c in zip(ED6_COLLECT, current)]
        print('collect_coin_creator_fee accounts inside if !frozen:', states)
    if not a.no_fee_8:
        lane.apply_fee_client_order(crate)


if __name__ == '__main__':
    main()
