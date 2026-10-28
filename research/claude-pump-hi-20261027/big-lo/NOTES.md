# big-lo upper half (start > 0x3a7b8): working notes

Assignment: 16 handler-body windows, 0x3b8d8 … 0x5b3b0, measured on g04 + H10 (808/165).
0x3a7b8 (set_metaplex_creator) belongs to pump-big-lo.

## Window map (original call graph)

| window | size | Source sites | role |
|---|---:|---|---|
| 0x3fb70 | 5,440 | migrate.rs:251 | migrate helper; calls 0x414c0, 0x43060, 0x43ea0 |
| 0x414c0 | 4,440 | — | hand-built CPI with 7 accounts (invoke_signed, drop [AccountInfo;7]); also calls 0x47e28 |
| 0x43060 | 3,648 | — | native wrap: lamports move, spl_token instruction pack, invoke |
| 0x43ea0 | 8,448 | — | migrate (v1) create_pool helper: generated `pump_amm::cpi::create_pool` (0x10c0b8) |
| 0x49888 | 8,888 | migrate_v2.rs:243/249/335 | migrate_v2 helper; calls 0x4c158, 0x4eb28, 0x502f0 |
| 0x4c158 | 8,368 | — | ATA creation CPIs (invoke_signed, drops of [AccountInfo;6]/[7]) |
| 0x4eb28 | 6,088 | — | token_2022 transfer_checked plus sync_native (pack, invoke) |
| 0x502f0 | 8,704 | — | migrate_v2 create_pool helper: `fn(ctx: &Context<MigrateV2>, base, quote)` |
| 0x5b3b0 | 18,584 | multi_hop_curve_swap.rs | multi-hop body; calls 0x58f58, 0x5a260 |
| 0x58f58 | 4,872 | — | multi-hop native payments (transfer_native, invoke_signed) |
| 0x5a260 | 4,432 | — | multi-hop token transfer_checked |

## 0x502f0 create_pool helper (in progress)

The original loads every account in the same order as the generated CreatePool literal:
1. base_mint key for the seeds;
2. pump_amm as the CPI program;
3. pool, amm_global_config, pool_authority (creator), base_mint, quote_mint, lp_mint, the pool-authority accounts, the pool token accounts and the programs;
4. pump_amm_event_authority and pump_amm;
5. bonding_curve fields for the arguments.

It reads ctx.bumps.pool_authority at +0x24 of the Context, so the parameter is `&Context`, not promoted.

`wip-create_pool-helper-on-g04mv.patch` (cp5) does three things:
- extracts `pub fn create_pool(ctx: &Context<MigrateV2>, base, quote)` with `#[inline(never)]`;
- uses the generated client;
- keeps the line count of migrate_v2.rs.

Results:
- Measured 8,816 B against the original's 8,704 B.
- Normalized-instruction similarity is 0.45; ignoring registers and stack slots it is 0.79.
- `pub` blocks ArgumentPromotion, which otherwise rewrote the parameter to (accounts, bump).
- The remaining differences are scheduling of the AccountInfo clones and the order of the byte copies for the CPI metas.

Behaviour is unchanged: the same CPI bytes as the hand-built `call`. Not delivered; it gains nothing yet.
