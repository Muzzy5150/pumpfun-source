# Lane mayhem-b progress (sell side + sweep)

Windows owned: O0084 SellV2, O0082 Sell, O0079 SellPumpSwap, O0093 AMM sell quote,
O0075 / O0076 (attributed below), O0073 sweep-rate (`FeeRecipient::validate_sweep`).

## Baseline (parent)

`research/mayhem-sizing-panic-recovery` (successor of trade-origins-validator), which is
main's current Mayhem row: 429/441 normalized, 100 raw-local, 12 unmatched (111,288
bytes), 4,288 positive direct-call edges, 446 matched Source records.
Reproduced locally with the lane recipe: stripped `f4f6a368...`, symbols `2f6e9ad9...`.
(The provider-sharing frontier `04257040...`/`b537ac29...` and the trade-origins
parent `64da4560...`/`6e88b2bc...` also reproduce exactly.)

## Checkpoints committed

- `checkpoints/cp1-sweep-restructure/` (NOT a window gain; harvestable WIP):
  429/441 normalized, 100 raw-local, 4,288 edges, 446 Source records, no losses of any
  kind versus the parent (`measure.json`). Stripped `a593869c...`, symbols `43423a90...`
  (`ELF-SHA256.txt`; gzipped ELFs included). Full 67-file `source.tar.gz` and
  `source.patch` against the parent. Window state (`windows.txt`):
  - O0075 admin sweep: 8,008 = original size, 12 instruction slots differ (only the
    order of four loop-preheader loads).
  - O0093: 1,120 = original size, 24 slots differ (r1/r2 for the cap offset).
  - O0082 / O0084: closer (normalized-diff ratio 0.317->0.328, 0.264->0.287).
  - O0076 trader sweep: 8,464 vs 8,400; layout still differs (see below).

## Environment (scratch, not in git)

SP = /private/tmp/claude-501/-Users-shawwalters-Documents-Codex-2026-10-24-pumpfun-source/bf960843-6806-451b-a211-62c8b228d301/scratchpad
- `SP/lanes/mayhem-b/build/layout-lane-linux-target2-sysroot`: clone of
  ~/.cache/solana/v1.54/platform-tools/rust with the 26 official Linux v1.54
  sbpf-solana-solana target files (hash-checked against
  `research/mayhem-provider-sharing/builds/recovered/launch.json` by build_lane.py).
- `SP/lanes/mayhem-b/build/cargo-home`: offline registry clone (same crates as the packets).
- `SP/lanes/mayhem-b/build/qualified/{linker.py,default.ld,ordered.ld}`: the
  trade-origins-validator qualified linker config (`chmod +x linker.py`).
- `SP/lanes/mayhem-b/build/roots/work/programs/mayhem`: working source (a git repo with
  one commit per accepted step).
- `tools/build_lane.py LABEL ROOT [TARGET]`: same cargo command/env as the packet
  build.py. Root-only rebuild (`LANE_CLEAN_ANCHOR=0`) takes ~15-25 s and reproduces
  identical bytes (verified on the parent and on frontier hashes).
- `tools/measure.py SYMBOLS.so`: packet reader.py normalizer; replicates progress.py
  (normalized/raw/edges/Source/profiles) against the parent, reporting losses/gains.
- `tools/winreport.py`, `tools/mdiff.sh`, `tools/mdiff2.sh` (stack-offset-masked diff),
  `tools/odis.py` (annotated disassembly), `tools/srcrec.py` (Source records per window),
  `tools/batch.py SLOT spec.json` (several variants under one sbf slot).

## Attribution (new)

- **O0075 = `sweep_fees_admin` program fn with the whole admin sweep inlined**;
  **O0076 = `sweep_fees` (trader) with the trader sweep inlined**. Both are called from
  `__global::sweep_fees_admin` / `__global::sweep_fees` at +432. Evidence: the
  `remaining_accounts.len() == 16` require! carries AnchorError origin
  `fee_recipients.rs` line 399 (admin) / 431 (trader); panic Source records in
  fee_recipients.rs 353-378 (admin) and 207-208, 276-306 (trader); the `#[event]`
  SweepEvent sits at fee_recipients.rs:13:1. The candidate's former `sweep_remaining`
  (7,272-byte tail section) disappears once each handler owns its loop.
- The trader caps both the token and lamport amounts with a helper at fee_recipients.rs
  205-211: `total == limit -> 0`, `total + amount >= limit -> limit - total` (207:8 add,
  208:16 sub), else `amount`.

## Findings

1. Inline vs end placement of `unwrap_failed` (O0093, O0082, O0084): the original's
   fused `reserve > quote` branch has ~50/50 weights, which happens when exactly one of
   the two fused checks carries an `unlikely` hint. In the Linux v1.54 core MIR both
   `checked_sub` and `checked_div` are hinted -> (4000000:4001) -> end placement.
   `checked_sub(..).and_then(|r| if r == 0 { None } else { Some(x / r as u128) })`
   reproduces the original placement.
2. `native_mint::id()` instead of `::ID` in sell_quote's cap selection reproduces the
   original `mov r1, 96` before the mint loads (as trade-origins found for validate_quote).
3. Sweep frame layout: seeds written as `let index = &[recipient.index]; let seeds:
   &[&[u8]] = &[b"fee-recipient", index, &[recipient.bump]];` reproduce the original
   stack slots exactly (index at r10-321, bump at r10-265).
4. O0075 residual: original preheader order is token_program(616), quote_ata(160),
   admin(600), then remaining.ptr; candidate emits remaining.ptr first and the three
   account loads in reverse. Explicit pre-loop `as_ref()` bindings in reverse order
   (admin, ata, program) fix the three-load order (e33), but remaining.ptr stays first.
   The scheduler emits these loop-exported loads in reverse IR order.

## Negative controls

O0093: `filter(|r| *r != 0)` (1,224 bytes); nested cap form (1,080); `cap == 0` /
`cap > 0` / `cap.min(quote)`; `u128::from(retained)`; operand order; `retained as u128`
at definition; `let native = ..` variable (1,104) - none fix the r1/r2 residual.
O0073: `if !native`, casts inside arms, `match native` - identical to the parent.
O0075: `&ctx` associated fns (worse), `signer_seeds` outer array (worse),
`chunks(2)` (worse), Transfer struct before CpiContext (worse), `&&[AccountInfo]`
slice parameter and `total` before `native` (no change).
