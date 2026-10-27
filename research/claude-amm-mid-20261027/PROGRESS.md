# amm-mid progress log

Lane range: original windows 0x3d828 … 0x724a0.
Current frontier: `repro/pump_amm/account-context-recovery-20261027`
(badc9498, 623 normalized / 128 raw / 162 unmatched; 63 unmatched windows / 165,576 bytes in range).

## Current state (re-measured on 623)

- Cumulative candidate: `a11fbac3b2f5f7279541015a85bf09f00296cf7b26027a82b9fe73b67a69ebd1`
  (unstripped `6627417e…`), Linux v1.44 recipe: **624 normalized / 128 raw / 161 unmatched**, no losses.
- Cumulative source: `source.patch` (against the 623 canonical source = maintained `programs/pump-amm`).
- Evidence for every claim: `gains/*/candidate/{pump_amm_recovered.so.gz,unstripped.so.gz,sha256.json}`
  + `gains/*/measurement.json.gz`; `verify.py` re-measures all of them.
- Files changed (packet copies only; maintained source untouched because CI binds it to the frontier):
  - `programs/pump-amm/src/instructions/swap/trade_v2.rs` (create_sell_event, create_buy_event captures)

## Verified gains

| # | Window | Change | Candidate (623 base) | Runtime |
| --- | --- | --- | --- | --- |
| 1 | 0x52c58 create_sell_event | capture `context.user*` before `Clock::get()?` (same captures in create_buy_event) | a11fbac3 624/128 | trade_v2 870/0, buyback 369/0, cashback 146/0, sell events 10/0, buy events 16/0 |

(History: gain 1 on the 599 frontier → 5e853b84 600/125, same runtime suites 0 mismatches.)

## Windows closed by this lane (skip)

- 0x52c58

## How to resume

1. Lane scratch: `SP/lanes/amm-mid/{stage,out,target,cargo-home,ir}`; tools mirrored in `tools/`.
   `stage/base3` = recipe-staged 623 frontier; `stage/cum3` = base3 + source.patch.
2. Native iteration: `tools/variant.sh <name> <src-relative patch> [base-stage] [compare-measure]`
   (native cum3 = 619/119; native differs from Linux only in 5 TypeId windows outside this range).
3. IR experiments: `tools/native_ir.sh <stage> <out.ll>`, edit one function with `tools/irexp.py`
   (rename numbered values first), compile with
   `llc -march=sbf -mattr=+store-imm,+jmp-ext -O3 -relocation-model=pic -function-sections -filetype=obj`,
   compare with `tools/objcmp.py <obj> <mangled> orig <window>`.
4. Confirm with `tools/linux_build.py --source <stage> --output <dir>` (holds sbf + podman locks;
   mirrors the frontier's recorded container paths), measure with
   `repro/pump_amm/focused-diagnostics-20261026/measure.py`, run relevant suites with `work/test-env/bin/python`,
   then package ELFs (gzip), sha256.json and measurement into `gains/NN-*/` and run `verify.py`.

## Window status (range, 623 base)

- matched by this lane: 0x52c58
- line-immediate-only residual (needs original file contents, not padding): 0x40100 0x446a0 0x448a8 0x44cc8
  0x44ed0 0x450d8 0x4bf30 0x4c138 0x4c340 0x4c548 0x57e20 0x50ca8 0x516e0 0x52070 0x61d68 0x62c40 0x63778
  0x6b780 0x6ba68 0x6bf50 0x6c328 0x6c768 0x6d128 0x6f608
- Codex in flight at last check (skip): 0x58028 0x4efb8 0x4f1d8 0x62e68 0x6db20 0x6f3c8 0x44ab0
- being worked next: 0x51d08 (buy_transfers: only a branch-encoding difference, `jne` vs `jeq +1; ja`)
- other code-level candidates (no line sites): 0x6f4b0 (OptionBool deserialize_reader), 0x5c590 / 0x5dc20
  (volume accumulator close/sync), 0x6f898, 0x70b60, 0x5a570

## Negative controls (summary; details in negative-controls/negative-controls.json)

- 0x52c58: literal field reorders (a/b/c), reference captures, IR GEP reorders, holder branch diamond,
  other llc versions — all non-matching.
- 0x51d08: plain assignment `user = a.user.key()` / `*a.user.key` instead of `copy_from_slice` — worse (ratio 0.88).
