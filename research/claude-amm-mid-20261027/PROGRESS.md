# amm-mid progress log (final; lane wound down)

Lane range: original windows 0x3d828 … 0x724a0. The dedicated AMM session's buy, sell, multihop, v2, pool and
admin lanes take over this range from here.

Frontier at hand-over: `repro/pump_amm/account-context-recovery-20261027`
(badc9498, 623 normalized / 128 raw / 162 unmatched). Of the unmatched windows, 63 (165,576 bytes) are in range.

## Final state

- Cumulative candidate: `a11fbac3b2f5f7279541015a85bf09f00296cf7b26027a82b9fe73b67a69ebd1`
  (unstripped `6627417e3fb9737d9a707486be663ec85651d64c8e45efdb1a59466d3ef27f69`), built with the frontier's
  Linux v1.44 recipe: **624 normalized / 128 raw / 161 unmatched**, no losses.
- Cumulative source: `source.patch`, against the 623 canonical source (= maintained `programs/pump-amm`).
  Only `programs/pump-amm/src/instructions/swap/trade_v2.rs` changes.
- Evidence: `gains/01-event-context-captures/candidate/` (gzipped ELFs, `sha256.json`) and `measurement.json.gz`.
  Run `python3 -B research/claude-amm-mid-20261027/verify.py` to re-hash and re-measure everything.
- Per-window residual table for the 62 remaining windows on 623 + this patch: `residual-table-623.json`
  (best candidate symbol, size, diff count, diff category, original and candidate line sites).

## Verified gains

| # | Window | Change | Candidate (623 base) | Runtime (0 mismatches) |
| --- | --- | --- | --- | --- |
| 1 | 0x52c58 create_sell_event | capture `context.user*` before `Clock::get()?` (same captures in create_buy_event) | a11fbac3 624/128 | trade_v2 870, buyback 369, cashback 146, sell events 10, buy events 16 |

On the 599 frontier, the same change gave 5e853b84, 600/125, with the same suites (`history-599/`).

## Residual diagnosis, windows examined but not closed

### 0x51d08 buy_transfers (872 vs 880 bytes) — diagnosed, not closed

- **Exact residual.** At the volume-accumulator user check (`memcmp == 0` → copy the user key), the original
  emits one `jne r0, 0, +10` with the copy block as fall-through. The candidate emits `jeq r0, 0, +1; ja +10`.
  That extra instruction is the whole 8-byte gap. Every other difference is a shifted jump offset.
- **IR-level proof.** In the crate's own optimized IR, the error block of the preceding `?` sits between the
  memcmp block and the copy block (`transfer_checked_to_account_info`; block `bb18` in
  `--emit=llvm-ir`). Moving only that block after the copy and join blocks makes `llc` reproduce the original
  window exactly (tokens equal). So ISel must see the copy block as the memcmp block's layout successor. It then
  inverts the condition to fall through; SBF block placement cannot reverse the branch later.
- **Why the simple source forms fail.** rustc creates LLVM blocks lazily, in first-reference order during RPO
  codegen. The `?` switch creates its error block before the following `if`'s blocks, so any plain
  `?; if … {copy}` sequence gives the candidate order.
- **Next steps.** Find a source shape whose block creation puts the copy and join blocks before that error
  block. Ideas: an LLVM-inlined callee whose blocks are spliced in after the call block (MIR inlining defeats
  this), the user update inside the Ok continuation of the last transfer, or a `match` on its result. The copy
  must stay a 32-byte `llvm.memcpy` (`copy_from_slice`, interleaved load/store), not load-all/store-all.
- **Negative controls.** `= a.user.key()` and `= *a.user.key` (copy becomes load-all/store-all; ratio 0.877);
  `UserVolumeAccumulator::set_user_if_default` method (ratio 0.776). Codex's `amm-buy-result-sum-next` notes call
  this "the previously tested empty-jump gap".

### 0x52070 create_buy_event (3048) — reduced to one line immediate

With this packet's captures, the only remaining difference is the `Overflow` site's source line: original
`trade_v2.rs:515`, candidate line 215. It closes when the file's preceding content reaches the original line.

### Source-line-immediate-only windows (29) — not attempted

The only differences are `line` immediates stored by `error!`/`require!` sites; their deltas within each function
already match. They need the original preceding file contents (declarations, accounts structs, docs), not
padding. Codex's pool-source-organization lane reached the same conclusion. Original lines vs candidate lines
(native 623 + patch build):

- multi_hop_swap.rs `error!` closures (520 B; candidate stand-in is the deposit closure): 0x40100 (307),
  0x446a0 (579), 0x448a8 (586), 0x44cc8 (636), 0x44ed0 (671), 0x450d8 (718). The original path is
  `programs/pump-amm/src/instructions/swap/multi_hop_swap.rs`; the candidate still compiles `multi_hop.rs`.
- sell.rs closures (520 B): 0x4bf30 (167), 0x4c138 (179), 0x4c340 (183), 0x4c548 (196); trade_v2.rs closure
  0x57e20 (913).
- trade_v2.rs helpers: 0x4efb8 validate_cashback_coin (103), 0x4f1d8 validate_buyback_token_account (138/146),
  0x4ff18 total_quote (241), 0x50ca8 BuyResult::total_user_quote (302), 0x516e0 calculate_sell_quote
  (376/377/385), 0x52070 (515).
- sell.rs 0x4ea90 validate_pool_v2 (520/526).
- global_config.rs: 0x61d68 set_protocol_fee_recipients (256/263), 0x62c40 set_buyback_basis_points (306),
  0x62e68 validate_buyback_recipient (321/326/336), 0x63778 set_buyback_fee_recipients (347/357).
- pool.rs: 0x6b780 market_cap (386), 0x6ba68 total_accrued_fees (408), 0x6bf50 total_virtual_quote_reserves
  (426), 0x6c328 effective_quote_reserves (439/440), 0x6c768 accrue_fees (458/462/465/469), 0x6d128
  take_accrued_fees (484).
- utils/token.rs: 0x6f608 validate_self_transfer (21). Codex `amm-final-source-data` already measures this one
  matched.

### Code-level windows not examined in depth (automatic classification on 623 + patch)

- 0x6f4b0 (344) vs `OptionBool::deserialize_reader` (368): 13 diffs, no line site. Small, good next target.
- 0x5c590 (2816) vs `close_user_volume_accumulator` (2768): 89 diffs, no line site.
- 0x5dc20 (2904) vs `sync_user_volume_accumulator` (2952): 140 diffs, no line site.
- 0x61630 / 0x61898 / 0x61b00 (616 each): `error!` closure variants 96 bytes larger than the 520-byte closure,
  with global_config.rs lines 220/230/243. Also need lines.
- 0x6bcd0 (640): closure variant, pool.rs 417. Also needs lines.
- 0x3d8d0 (752, multi_hop_swap.rs:239), 0x40308 (1416, :414) and 0x452e0 (1256, :777): nearest is
  `multi_hop::program_for` (1160); ratios 0.74–0.85.
- 0x50598 calculate_buy_result (1808 vs 1776, lines 283/294) and 0x50f00 estimate_buy_quote (2016 vs 1952,
  lines 328/346): owned by Codex buy-result/estimate lanes.
- 0x6f898 (2536), 0x70b60 (2904), 0x5a570 (4168): weak nearest candidates (ratio < 0.5). Attribution is
  uncertain.
- 0x62688 (1464, global_config.rs 292/297), 0x58e08 (1536, swap/mod.rs:164), 0x59408 (4456, sweep_fees.rs),
  0x5b5b8 (4056, token_incentives/claim.rs:228), 0x6d408 (1816, volume_accumulator.rs:104): structural with
  line sites.
- 0x44ab0 (536) vs `multi_hop::apply_hop_fees` (536): 39 non-line diffs. Codex fee-context was on it.

### Structural (large handlers, also with line sites)

0x3dbc0, 0x40a08, 0x45940 (multi_hop_swap.rs handlers); 0x49b50, 0x4c750 (sell.rs); 0x53350, 0x54a20, 0x56710
(trade_v2.rs executors). Codex in flight at last check: 0x58028 (pool-prepare/admin-cto), 0x6db20 and 0x6f3c8
(incentive state), 0x45940 (generated-return-origin), 0x53350 (final-source-data).

## Negative controls (details: negative-controls/negative-controls.json)

- 0x52c58:
  - literal field reorders (user fields last; base_supply/buyback swap; mayhem before holder) — none match;
  - reference captures (`&context.user`) — no change;
  - IR GEP reorders within the block — no change, because MachineSink always lands the 1e15 at the block top;
  - holder conditionals as one IR diamond — 1776 bytes;
  - llc v1.45/v1.46/v1.47/v1.48 on the same IR — identical to v1.44. The residual was IR-shaped, not
    backend-shaped.
- 0x51d08: plain assignment forms and a helper method (above).

## Method notes for the continuation lanes

- Native macOS v1.44 builds (`tools/native_build.sh`) produce bodies identical to Linux for every symbol except
  TypeId-bearing `type_id` helpers (0xa9b0, 0xf8ca0, 0x1016a8, 0x10efd8, 0x111b38). Iterate natively, then confirm
  with `tools/linux_build.py`. It mirrors the frontier's recorded container paths, and reproduced `a4b978ee…`
  byte-for-byte.
- For single-instruction placement residuals, emit the root crate's IR (`tools/native_ir.sh`) and check
  `llc -march=sbf -mattr=+store-imm,+jmp-ext -O3 -relocation-model=pic -function-sections`, which matches the
  real build for the function. Then edit only the target function (`tools/irexp.py`, `ir` block moves; rename
  numbered SSA values first) until `tools/objcmp.py <obj> <mangled> orig <window>` reports equality. Then map the
  IR change back to ordinary source. This closed 0x52c58 and fully diagnosed 0x51d08.
- `-C llvm-args=-print-after-all -C llvm-args=-filter-print-funcs=<mangled>` (`tools/native_trace.sh`) shows
  which machine pass moves an instruction. For 0x52c58 it was MachineSink.
