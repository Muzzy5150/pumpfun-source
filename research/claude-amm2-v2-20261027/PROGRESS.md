# v2 lane PROGRESS (amm2 workflow, PumpSwap V2 trade family)

Base: main `repro/pump_amm/event-decoder-recovery-20261027` (candidate 0881a95d…, Linux 647/148/138).
Native baseline of that source on this lane: 642/139 (the usual 5 TypeId + 9 raw sysroot windows).
Scratch: `SP/lanes/v2/out` (src647/<variant> trees, nb-<variant> native builds, lx-<name> Linux builds, ir-<variant> IR).

## Ownership notes
- 0xe8ae8 0xe8f10 0xe9338 (V2 dispatch wrappers): already matched by Codex `work/amm-event-quote-final-20261027` (653, unpublished):
  V2 bodies moved into the public `instructions/swap/trade_v2.rs` module => full 40-byte Context ABI. Not worked here.
- Line-immediate-only windows in trade_v2.rs / sell.rs (0x4efb8 0x4f1d8 0x4ff18 0x50ca8 0x516e0 0x52070 0x57e20 0x4ea90):
  placement lane (DIRECTIVES 07:42). Every v2 edit keeps the line count of trade.rs / trade_v2.rs unchanged.

## Windows
| window | status | note |
|---|---|---|
| 0x51d08 buy_transfers | native MATCH (642->643, 0 lost) | last transfer `if let Err(e) = transfer_checked_to_account_info(..) { return Err(e); }` |
| 0x50598 calculate_buy_result | in progress | same calls; zero-path block + r6/r8 swap + phi'd Ok/Err discriminant store; lines 283/294 |
| 0x50f00 estimate_buy_quote | analysed | original has extra `available == 0` jump-threaded into the 6039 site (line 328), saturating_add operand order protocol+lp |
| 0x53350 0x54a20 0x56710 handlers | pending | wait for Codex 653 module move (full Context ABI) |

## 0x51d08 mechanism (IR-verified)
rustc creates LLVM blocks in first-reference order; for `?` the Ok block is created before the Err block, so the
memcmp block (Ok continuation of the 4th transfer) had the 4th error block as layout successor and ISel emitted
`jeq +1; ja` (SBF cannot reverse branches later). `if let Err(e) = … { return Err(e); }` switches on the Err
variant, creating the error block first; the copy block becomes the memcmp block's layout successor (`jne`).

## Negative controls
- 0x51d08: `match r { Ok(()) => {}, Err(e) => return Err(e) }` keeps the error block between memcmp and copy (IR) — no change.
  (amm-mid: `= a.user.key()`, `= *a.user.key`, set_user_if_default method — worse.)
