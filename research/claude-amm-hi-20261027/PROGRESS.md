# Lane amm-hi progress (PumpSwap, original windows 0x73ef0 … 0xf6eb0) — final

The lane is wound down; the dedicated AMM session owns this range from here. This file is
the hand-off record: what is shipped, what is researched but not applied, and why every
other window in the range is still open.

## Shipped (maintained source, Linux-confirmed on the 623 frontier)

Base `account-context-recovery-20261027` (`badc9498…`, 623/128/162, 727,352 matched bytes).
This branch: **634 normalized, 128 raw, 151 unmatched, 758,296 matched bytes**, Linux
candidate `9d1a23b9…` (`linux/g3r-on-623/`). Eleven gains, no losses. All 25 maintained
suites pass (17,462 cases, 0 mismatches). Windows and causes are in README.md.

The three changes, each self-contained and re-appliable:

1. Source-coordinate placement (0x74900, 0x82630, 0xd1290): transfer_fee.rs error sites on
   32/49/57/67, `#[derive(Accounts)]` on create_config.rs:6 and
   init_user_volume_accumulator.rs:8.
2. SweepFees and handler linkage (0xc6530, 0xe9b90, 0xe9fc0, 0xe8ae8, 0xe8f10, 0xe9338):
   `seeds::program = associated_token::ID`; `pub mod sweep`; trailing
   `pub use trade::{execute_buy, execute_buy_exact_quote, execute_sell}` in lib.rs.
3. Boost harvest (0x74e30, 0xf6eb0): `utils::transfer_fee::harvest_to_mint` calls
   anchor_spl's `harvest_withheld_tokens_to_mint`; `boost_burn` calls the helper.

Codex's private `amm-sweep-program-context` independently made the same SweepFees seeds
change (parser only); the two dispatch wrappers need change 2's linkage as well.

## Researched, not applied: helper crate (`helper-crate/`)

Moving Token-2022 helpers into a local path crate recovers five more windows in this range:
0x73ef0 `supported_mint`, 0xf2d60 / 0xf2ed0 native fee math, 0x74648 `calculate_fee` and
0x74b80 `amount_before_fee`. Native 629 → 634 on top of this branch; **Linux 634 → 639, raw
128, no losses** (candidate `80a95040…`, `linux/helper-crate-on-634/`); all 25 suites pass
(17,462 cases, 0 mismatches). Apply with `git apply -p1 helper-crate/helper-crate.patch`.
Evidence and controls:

- Original 0x73ef0 reloads the data RefCell borrow flag after calling 0xf28b8, so the callee
  is opaque. In-crate callees (private, `pub`, or `#[inline(never)]`, exp5a/5b) let LLVM infer
  read-only memory effects and forward the flag (560 vs 568 bytes). A separate crate matches
  exactly (exp6).
- 0xf28b8, 0xf2d60, 0xf2ed0 and 0xf31d8 are contiguous between the program crate's last
  function and anchor_spl's object, each called once from a main-crate wrapper, with no
  calls (other than compiler-rt) and no data references.
- The original fee wrappers copy the 24-byte fee record before the call. With spl-style
  `&self` methods (not `nocapture`) and a by-value match (`match *data { Some(fee) => … }`)
  the copy and the original frame layout both appear (exp13).
- Negative controls: by-value `self` methods called directly pass the payload pointer (no
  copy; exp7/exp8, deduced `readonly`); free functions delegating to methods copy but lose
  the standalone block layout of 0xf2d60/0xf2ed0 and leave the frame 24 bytes shallower
  (exp9); a per-package `incremental = true` override for the helper copies but changes
  0xf2ed0 (exp11); whole-build `CARGO_INCREMENTAL=1` drops 611 → 475 because incremental
  disables the MIR inliner (exp10).
- The helper crate's name and location are not evidenced by the binary (no strings).

## Residuals (unmatched windows in 0x73ef0 … 0xf6eb0 after this branch)

| Window | Bytes | Function | Diagnosis |
| --- | ---: | --- | --- |
| 0x73ef0 | 568 | `utils::token::supported_mint` | Closed by the helper-crate patch (cross-crate parser call). |
| 0x74128 | 1312 | `utils::transfer_fee::from_mint` | With the helper crate and `Clock::get()` before the `None` check (`Ok(fees.map(…))`, exp14), only the early non-Token-2022 return differs: original stores a zeroed 32-byte `Ok(None)`, ours stores only the tag. Tried an `if/else` expression (exp15a, other branch shape) and a `None`-initialized local (exp15b, stores registers). Open. |
| 0x74648 | 696 | `utils::transfer_fee::calculate_fee` | Closed by the helper-crate patch. |
| 0x74b80 | 688 | `utils::transfer_fee::amount_before_fee` | Closed by the helper-crate patch. |
| 0x92c08 | 5400 | `MigratePoolCoinCreator::try_accounts` | Context layout; Codex `amm-creator-context` reaches 5136 bytes. Not worked here. |
| 0x94120, 0xeab70, 0xec738 | 5416, 1152, 1152 | SetCoinCreator parser; set/migrate wrappers | Context layout (unboxed accounts); privately recovered by Codex `amm-creator-context`. |
| 0x9e3b0, 0xa0068 | 7352, 7528 | CreatePool init helpers | Differ only in origin filename length/line (instructions/create_pool.rs:21); privately recovered by Codex `amm-create-pool-module`. |
| 0xa6c68, 0xea3f0 | 3936, 1272 | ExtendAccount parser/wrapper | `ExtendAccount.account` as owned AccountInfo; privately recovered by Codex `amm-extend-context`. |
| 0xe31a0 | 3064 | `__global::create_pool` | Wrapper copies a larger context and passes the full Context; follows the CreatePool layout work. |
| 0xe7648, 0xe7d88 | 1856 | `__global::buy`, `buy_exact_quote_in` | Original passes `&ctx` plus three scalars; our shared legacy-buy handler takes an extra mode argument on the stack. Needs separate handlers or the original signature (Codex legacy-buy area). |
| 0xaf3b0, 0xb5a90, 0xbd3b0 | 8128 each | LegacyBuy / MultiHop / TradeV2 `try_accounts` closures | Only the origin filename length and line differ: instructions/swap/buy.rs:133, swap/multi_hop_swap.rs:68, swap/trade_v2.rs:31. Requires moving those Accounts structs into the original files at those lines. |
| 0xb3460, 0xb92c8 | 520 each | error-constructor closures | Same two immediates: buy.rs:409 and multi_hop_swap.rs:941. Follows the module moves above. |
| 0xd44e0, 0xd4f90 | 728 each | Global/UserVolumeAccumulator `try_deserialize` | Origin state/volume_accumulator.rs:8 and :25. Codex `amm-volume-state-origin` moved the declarations into that file (lines 3/13, not fitted). |
| 0xf28b8 | 1192 | supported-mint TLV parser (helper crate) | Body differs (ours 1168). Codex's 48 parser variants also missed. Calling convention is right once cross-crate. |
| 0xf2d60, 0xf2ed0 | 368, 776 | native fee math (helper crate) | Closed by the helper-crate patch (Codex's exact standalone bodies). |
| 0xf31d8 | 664 | Token-2022 transfer-fee TLV decoder (helper crate) | Body differs (ours 640–656 depending on form); Codex `amm-fee-native-next` variants also missed. |

## Method notes for whoever continues

- `tools/origins.py` lists every Anchor `Source{filename,line}` immediate in both binaries;
  almost every unmatched window carrying one differs there (plus any real code differences).
- Publicly reachable handlers keep external linkage (crate types `cdylib` + `lib`); private
  ones get argument promotion, which changes the `__global` wrapper.
- Native macOS v1.44 builds match Linux except five TypeId windows and a few tail raw
  windows outside this range. Cargo's mtime freshness can silently reuse a stale root-crate
  artifact; `nbuild.py`/`lbuild.py` touch staged sources and assert "Compiling
  pump-amm-recovered" (`builds/exp5b` was invalid for that reason and is not used).
- Linux builds mount lane copies of the frontier Cargo home and target at the frontier's
  container paths; `linux/control-623` shows the recipe reproduces the base byte-for-byte.
