# Lane mayhem-b progress (sweep + sell side)

Scope now: O0075 / O0076 (sweep bodies), O0079 AMM Sell, O0082 Legacy Sell, O0084 SellV2.
(O0093 was closed upstream by the quotes-current packet; O0073 was reassigned to the
fees-final lane. My O0073 notes are kept below for that lane.)

## Parent

`research/mayhem-quotes-current-recovery-20261027` (432/441 normalized, 100 raw-local,
9 unmatched / 107,952 bytes, 4,314 positive direct-call edges, 456 Source records).
Reproduced locally: stripped `73dff97e...`, symbols `440b9281...`. Its 67-file source is
not archived in that packet; it is spr (`mayhem-sizing-panic-recovery/source.tar.gz`)
+ `mayhem-sell-current-recovery-20261027/overrides` + `mayhem-quotes-current-recovery-
20261027/overrides` + `src/instructions/pump_interface.rs` =
`mayhem-current-ownership-composition-20261027/sources/qualified.rs` (all 67 hashes
verified against its source-inputs.json).

## Checkpoints committed (no window gain yet)

- `checkpoints/cp2-q432-sweep-restructure/` (current): on the 432 parent, adds the sweep
  restructure + the sell_amounts zero-check idiom. 432/441, 100 raw-local, 4,314 edges,
  456 Source records, **no losses of any kind** (`measure.json`). Stripped `becda737...`,
  symbols `49b1be5c...` (gzipped ELFs, full source, source.patch vs the 432 parent).
  O0075 is at the original 8,008 bytes with 8 differing instructions (below).
- `checkpoints/cp1-sweep-restructure/`: same work on the older spr parent (superseded).

## Environment (scratch, not in git)

SP = /private/tmp/claude-501/-Users-shawwalters-Documents-Codex-2026-10-24-pumpfun-source/bf960843-6806-451b-a211-62c8b228d301/scratchpad
- `SP/lanes/mayhem-b/build/layout-lane-linux-target2-sysroot` (Mac v1.54 rust + the 26
  official Linux v1.54 target files, hash-checked by build_lane.py), `build/cargo-home`,
  `build/qualified/{linker.py,default.ld,ordered.ld}` (unchanged since trade-origins).
- `build/roots/work/programs/mayhem`: current working source (git; one commit per step).
  `build/roots/work-spr`: the older spr-based tree. `build/src-q432`: pristine parent.
- `tools/build_lane.py LABEL ROOT [TARGET]` (~15-25 s root-only rebuild, reproduces the
  parent bit-for-bit), `tools/measure.py` (progress.py logic vs the parent, reports
  losses), `tools/batch.py SLOT spec.json` (several variants per sbf slot),
  `tools/irbatch.py` (IR + MIR dumps), `tools/irsurg.py`/`irperm.py`/`objsec.py`/
  `cmpobj.py` (edit one function's IR, re-run `llc`, compare with the original window;
  `llc -O3 -mtriple=sbf -mcpu=generic -relocation-model=pic -function-sections` on the
  rustc-emitted IR reproduces rustc's bytes exactly).

## Attribution

- **O0075 = `sweep_fees_admin` program fn with the whole admin sweep inlined**; **O0076 =
  `sweep_fees` (trader) with the trader sweep inlined**. (Independently confirmed for
  O0075 by `mayhem-sweep-admin-attribution-20261027` via the matched wrapper.) The
  `remaining_accounts.len() == 16` require! has AnchorError origin fee_recipients.rs line
  399 (admin) / 431 (trader); panic Source records in fee_recipients.rs 353-378 (admin)
  and 207-208, 276-306 (trader); `#[event]` SweepEvent at fee_recipients.rs:13:1.
- The trader caps token and lamport amounts with a helper at fee_recipients.rs 205-211:
  `total == limit -> 0`, `total + amount >= limit -> limit - total` (207:8, 208:16).
- Indentation of the Source columns (17 for the lamport moves and field updates, 22 for
  a continued `.unwrap()`) implies the loops are methods (8-space bodies).

## O0075 residual (8 instructions, frame layout already exact)

Original preheader: `ldxdw r2,[r10-608]; ldxdw r3,[r2+616]; stx; ldxdw r8,[r2+160];
ldxdw r2,[r2+600]; stx; ldxdw r1,[r1+16]; stx` (token_program, quote_ata, admin, then
remaining.ptr). Candidate: remaining.ptr first, then admin, quote_ata, token_program.
Established with llc on edited IR:
- the SelectionDAG ILP scheduler (default `list-ilp`; source/burr/hybrid/fast are far
  worse) emits these loop-exported loads in **reverse IR order**; explicit pre-loop
  `as_ref()` bindings in the order admin, ata, program give the original order of the
  three (e33), but are not natural source.
- remaining.ptr is scheduled first in every variant tried: its IR position (top, end,
  separate block), ctx `readonly`/`noalias`, alias-scope metadata, an extra later use of
  ctx, `&&[AccountInfo]` / `#[inline(always)]` (no ArgumentPromotion), index / step_by /
  len-based loops, `chunks(2)`, ctx-taking associated fns - none change it. The cause is
  in the DAG's register-pressure ordering (picking the ctx-based load bottom-up is
  never cheaper than the account loads); the original's DAG must differ elsewhere.

## O0076 residual

Same restructure gives 8,464 vs 8,400 bytes; the require! error block is placed at the
end (original: inline after the first native-compare segment), and the limit select uses
520/576 instead of the original 176/232 + 344. Keeping the 344 base separate (llc
surgery) does not fix the placement. The trader loop's frequency structure (validate_sweep,
sweepable) drives MachineBlockPlacement differently; the seed form that fixed O0075's
frame (`let index = &[..]`) lowers O0076's alignment (0.53 -> 0.28 normalized ratio).

## Findings reused upstream / for other lanes

1. Inline vs end placement of `unwrap_failed` (O0082/O0084/O0093): a fused `reserve >
   quote` branch gets ~50/50 weights only if exactly one fused check lacks `unlikely`;
   `checked_sub(..).and_then(|r| if r == 0 { None } else { Some(x / r as u128) })` gives
   the original placement (applied to sell_amounts; upstream's O0093 fix uses a `?`
   closure with the same effect).
2. O0073 (for fees-final): nested `if last != 0 { let interval = ..; if interval != 0 {..} }`
   gives 904 bytes / 23 diff slots under the qualified recipe (the original loads
   current_time inside each native arm and puts the non-native arm first). Computing
   `last` before `Clock::get()` (on line 46) did not help (904 bytes, 37 slots).

## Negative controls (beyond those above)

O0075: `&ctx` associated fns, outer `signer_seeds` array, `chunks(2)`, Transfer struct
before CpiContext (all worse); `&&[AccountInfo]` param, `total` before `native`, gp
reference for the limit (no change).
