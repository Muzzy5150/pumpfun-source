# Lane amm-lo final progress (PumpSwap, original windows 0x2288 .. 0x3a5a0)

Lane stopped on coordinator wind-down. The range passes to the AMM completion
session's lanes. Read this file before picking a window in this range.

## Final state
- Branch `claude/amm-lo-20261027`: `ac873ff27` (program changes) + `67e058b19` (evidence) +
  the wind-down commit that adds this file and `results/deposit-near-miss/`.
- Baseline: `repro/pump_amm/account-context-recovery-20261027`, candidate `badc9498…`,
  623/785 normalized, 128 raw, 162 unmatched (authenticated Linux v1.44 SBPF).
- Lane result on that source (`results/linux-rebased-623/`): candidate `a7aa6bcd…`,
  symbols `c1c55d0e…`, **648/128/137**, +25 normalized, +24,616 original text bytes, no
  normalized/raw loss, no overlap with the 623 recovery (`gain-vs-623.json`).
  Runtime: 25 suites, 17,462 cases, 35,074 transactions, 35,418 signature fields, 0 mismatches.
  ELFs, SHA256SUMS and `measure.py` JSON are in the packet and re-measure identically.

## Closed windows (skip)
| Window(s) | How |
| --- | --- |
| 0x17960 disable | `let global_config = &mut ctx.accounts.global_config;` + one assignment per flag (original reloads the Box pointer per update); `emit!(event)` instead of `emit!(event.clone())` |
| 0x1b510 0x1b7c0 0x1bb00 toggles | bodies moved unchanged to `instructions/admin/toggle_{cashback_enabled,boost,mayhem_mode}.rs`, guards at lines 21/14/17 |
| 0x31710 0x31918 0x31b20 0x31d28 0x31f30 0x32138 0x32340 0x32548 | deposit error closures; whitespace placement at 91/99/143/152/154/156/160/162 (body Sources 56/77/79/100 also placed) |
| 0x34370 0x34578 0x34780 0x34988 0x34b90 0x34d98 0x34fa0 | withdraw error closures; whitespace placement at 98/106/150/160/162/166/170 (body Sources 57/62/84/86/107 also placed) |
| 0x37150 0x39d80 0x39f88 0x3a190 0x3a398 (+0xaf3b0, amm-hi range) | `legacy_buy.rs` -> `instructions/swap/buy.rs` via `use instructions::swap::buy as legacy_buy;`; `get_buyback_accounts` at 116/121, `#[derive(Accounts)]` at 133, closures at 387/391/395/404 |

## Residual diagnosis per examined, unclosed window (623 baseline + lane changes)
- **0x2fb38 deposit handler (7,128)** — closest. `results/deposit-near-miss/deposit-near-miss.patch`
  (three ordinary changes, not on the branch because the window is still unmatched):
  1. `pub use instructions::{admin, liquidity};` in lib.rs (same line count; `#[program]` stays on 36).
     The handler keeps external linkage, is no longer inlined into the program fn, and loads
     `ctx.bumps` late as the original does. 7,016 -> 7,128 bytes (= original), ratio .917 -> .987.
  2. `a.{base,quote}_mint.to_account_info().owner == a.token_program.key` (reference compare;
     the original memcmps against the passed Token program key, not the `token::ID` constant).
     Using `.key()` (by value) instead grows the body to 7,176 bytes (negative).
  3. Reserve reads in the order user_base, user_quote, pool_base, pool_quote (machine order then
     equals the original).
  Result: 866/868 slots equal. Remaining: slots 563/564 swapped — the original loads `a.pool`
  (`ldxdw r1 [r8+0]`) before the `change` low word (`ldxdw r4 [r10-832]`) in
  `a.pool.virtual_quote_reserves.checked_add(change)`. Negative: moving `i128::try_from(change)`
  into the `checked_add` argument (7,120 bytes, and it moved the line-160 closure). Try instead a
  binding such as `let pool = &mut a.pool;` before the boost block, or computing `change` before
  `if a.pool.can_boost()`; keep the closure lines at 152/154/156/160/162.
- **0x32750 withdraw handler (7,200)** — the same `pub use` change takes it from 7,064 to 7,176
  bytes, ratio .901 -> .952 (65 unequal slots). Not investigated further; apply the deposit
  recipe (Token-program key reference compare for both mint program selections, read order).
- **0x1c890 update_buyback_config (1,344)** — instruction-for-instruction equal except Source
  path/line and stack-slot order: the original places the inlined to_string temporaries, then the
  `PumpAmmError::name()` String and the AnchorError nearer r10 than the 256-byte recipients array;
  the candidate places the array second. Moving the handler to
  `instructions/admin/update_buyback_config.rs` with the guard on line 40 fixes path/line
  (`results/update_buyback_config.rs.research`, neutral alone). Negative controls (all keep or worsen
  the slot order): `core::array::from_fn`, `iter_mut().zip`, array declared before the guard
  (1,704 bytes), helper returning `Result<[Pubkey; 8]>` (1,416), helper doing only the guard (1,640).
- **0x22c80 (520)** — 6023 Overflow closure at `instructions/boost.rs:258` (len 43). Needs
  `boost.rs` + `boost_burn.rs` merged into `instructions/boost.rs` (init_boost Source at 22,
  boost_buy_and_burn Sources 238..403); one of the candidate's 6023 closures then placed at 258.
- **0x2e468 initial_liquidity (696)** — Source only: `create_pool.rs:339` (len 49) vs `create.rs:246`.
  **0x2e260 (520)** — 6003 TooLittlePoolTokenLiquidity closure at `create_pool.rs:290`; the candidate
  uses an inline `require!(liquidity >= 100, …)`, the original an `ok_or_else(|| error!(…))` closure
  (e.g. `checked_sub(100)`). Both need `create.rs` -> `instructions/create_pool.rs`; create body
  0x2ba60 (ratio .28) has original Sources 171..279.
- **0x19138 set_reserved_fee_recipients (9,176)** with helpers **0x2288 (232)** and **0xc5d0 (1,240)**
  — behaviour gap: the original calls `Rent::get`, then for each of 8 remaining accounts compares
  the key, reads lamports/`try_data_len` and calls `Rent::is_exempt`, builds diagnostics with
  `alloc::fmt::format` and `String::clone` (0x2288 clones into an `Option<String>`-like slot), uses
  `with_values`/`with_pubkeys`, and Borsh-serializes a `[Pubkey; 7]` (0xc5d0) twice. The candidate
  (6,824 bytes) has none of the rent checks. Needs semantic recovery plus a runtime probe of
  non-rent-exempt recipients.
- **0x376b0 legacy buy (9,936) / 0x3a5a0 legacy buy_exact_quote_in (12,936)** — the candidate has one
  19,768-byte `execute` for both; the original has two handlers (buy Sources 317/326/327/405 and
  closures 387..404; exact Sources 625..781). Split `execute` in `instructions/swap/buy.rs`.
  **0x351a8 (8,104)** — buy.rs helper with Sources 44/54/57/98/98, best candidate
  `distribute_cashback` (8,136, ratio .26); unidentified.
- **0x14920 admin_cto_pool (6,152; ratio .27, Sources admin_cto_pool.rs 64..121)** and its helper
  **0x118e0 (232)**; **0x1ef90 init_boost (3,912; .19)** and helpers **0x1ecd8 (696; .825 vs
  liquidity_floor_ratio)**, **0x2b9a0 (192)**; **0x1fed8 boost_buy_and_burn (11,688 vs 14,280; .24;**
  candidate has five 520-byte closures, original one); **0x23e40 migrate_pool_coin_creator (.48)**,
  **0x24fd8 set_coin_creator (.44)**, **0x26da8 / 0x28dd0 transfer_creator_fees_to_pump{,_v2} (~.10)**,
  **0x2e720 extend_account (.32)**: structural recovery, not attempted.
- **0x2b8e0 (192)** is called only from parser 0x92c08; **0xbb80** (`RawVec<[u8;32]>::grow_one`,
  candidate has only the 34-byte AccountMeta instance) and **0xfb08** (`[V]::concat`) are called only
  from multihop 0x3dbc0 (amm-mid range).
- **Left to in-flight Codex work at the time**: curve math 0x11e70/0x123a0 (constant_product.rs
  45/47 and 85/87; one candidate body serves both), 0x12840 (112), 0x12b08 (fees.rs 19/21),
  0x13190 (32), 0x13d30 (160) — all differ only in Source lines; 0x119c8, 0x13458, 0x14088 curve
  bodies; 0x16128 (incentives); 0x22e88 collect (4,024, ratio .79).

## Method notes for the next lane
- Native loop: `tools/native_build.sh <tree> <out>`; native == Linux for normalized counts except the
  five sysroot TypeId windows (outside this range). ~25 s root rebuild.
- Linux: `tools/linux_build.py --source-root <tree> --output <out>` reproduced `a4b978ee…` byte-for-byte.
- Public reachability (`pub use instructions::…`) changes inlining and is a strong lever for handler
  bodies that the original keeps as separate functions.
- `tools/place.py` performs and verifies whitespace-only placement (token stream unchanged).
