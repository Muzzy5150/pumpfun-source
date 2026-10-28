# Lane mayhem-o79 progress: O0079 SellPumpSwap (original start 95848, 17,312 B)

Base: `mayhem-env/parent-433` (433/441; stripped `c1f25d01...`, symbols `73c28d5e...`), reproduced
bit-for-bit from the lane root copy (`o79-0-parent`). Starting point: lane mayhem-b's m8c
(masked ratio 0.7192, 17,776 B handler). Durable scratch: `claude-mayhem-work/mayhem-o79/`.

Metric: `llc79.ratio` = difflib ratio over the handler's instruction text with registers, call
targets, branch targets, `[r10-N]` and `add64 rX, -NNN` masked. (`hunks.py regs` gives slightly
lower numbers for the same build because it does not mask `add64` stack constants.)

## Finding 1: the original's 23 inline CPI account copies are inlined `AccountInfo::clone`

- The original has 4 out-of-line `<AccountInfo as Clone>::clone` calls (3 in close_account, 1 in
  emit_cpi). The 21 Sell accounts plus 2 remaining accounts are copied inline. The copy pattern keeps
  the lamports Rc pointer in a register, and loads the remaining fields (42/41/40/32/24) after the
  NEXT account's first strong-count increment. That needs the scoped-noalias metadata of an inlined
  `&self` (`derive(Clone)` on AccountInfo). mayhem-b's `info()` helper reloads the Rc pointers after
  each store, so it cannot produce this pattern.
- Why parent-433 calls clone 27 times: the inline remark (`-Cremark=inline`, diagnostic build
  `o79-p0-remarks`) says `<AccountInfo as Clone>::clone not inlined into handler because too costly
  to inline (cost=60, threshold=45)`. 45 is the cold-callsite threshold: the handler's call sites
  after the price check are below 2% of entry frequency (`-cold-callsite-rel-freq` default 2).
- Proof: diagnostic build `o79-d1-nocold` (parent source plus `-Cllvm-args=-cold-callsite-rel-freq=0`)
  inlines every clone and reproduces the original copy pattern instruction for instruction. It
  also inlines the close_account clones, which the original does not. So the original's CPI region
  is >= 2% of entry and its close_account region is < 2%.
- Ordinary-source fix: `a.X.to_account_info()` in the Sell literal, plus price/quote checks whose
  error edges carry the library's `unlikely` weights. Those keep the CPI region warm, so clone is
  inlined there (variant g1a: 4 clone calls, like the original).

## Finding 2: the original Sell literal evaluation order

Read from the Rc-increment order in O0079 (accounts-struct offsets 48, 88, 96, 112, 120, 32, 40,
64, 72, 56, 104, 24, 80, 144, 152, 128, 136, 160, 168, 176, 184, then remaining 216, 224):

`user, pool, global_config, pool_base_token_account, pool_quote_token_account,
user_base_token_account, user_quote_token_account, quote_token_program, base_token_program,
system_program, quote_mint, base_mint, associated_token_program, event_authority, program,
protocol_fee_recipient, protocol_fee_recipient_token_account, coin_creator_vault_ata,
coin_creator_vault_authority, fee_config, fee_program`

The program key (`a.pump_swap_program.key()`, first argument of `new_with_signer`) is evaluated
before the literal, and the inline signer seeds after it. That matches the original order: key at
2960, copies, then seeds at 8504.

## Finding 3: price via `checked_div` (unlikely vt==0) and an effective_quote helper

- `(vs*1e15).checked_div(vt).ok_or(MathOverflow)?` gives the vt==0 branch `!prof` unlikely, via
  `intrinsics::unlikely(rhs == 0)` in `checked_div`.
- With the m8c effective_quote helper (variant g2d), the first 736 bytes of the handler equal the
  original, registers included. The layout markers are close: the const-2 conversion is at 888
  (original 864), and the variable conversion falls into the shared tail at 2744/2800 (original
  2720/2776).
- An llc sweep over 128 branch-weight subsets on g1d IR (`tools/x1_weights.py`) points the same
  way: the original layout needs weights on the effective_quote overflow and on vt==0, and none
  on try_from.

## Variants (all keep 433, no losses of any kind)

| Variant | Source | Handler bytes | Ratio (llc79) | Clone calls |
|---|---|---|---|---|
| m8c (mayhem-b) | info() helper copies, IDL order | 17,776 | 0.7192 (hunks) | 4 |
| g1a | to_account_info, original order, eq helper, PC2 | 17,568 | 0.8937 (hunks) | 4 |
| g1b | same, IDL order | 17,584 | 0.7558 (hunks) | 4 |
| g1c | eq = parent form | 9,208 | 0.391 (hunks) | 27 (cold) |
| g1d | eq = and_then chain | 17,528 | 0.9139 | 4 |
| g2d | eq helper + checked_div price (pc3) | 17,504 | 0.9005 | 4 |

## Shared-helper note (pump-lo O0082, pump-mid O0084)

No shared helper has been edited by this lane yet. Finding 1 probably applies to Legacy Sell
(`clone_sell_info`) and SellV2 (`inline_cpi_info`). Those hand-written copy helpers cannot
reproduce the original's interleaved copy pattern. `to_account_info()` with warm call sites can.
