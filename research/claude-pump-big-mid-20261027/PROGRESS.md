# pump-big-mid progress log (lane `pump-big-mid`, 2026-10-27)

Baseline: g04 = Pump session genuine composite `claude-pump-work/base/g04` (806 normalized / 165 raw,
unstripped 5a13b87f…). Rebuilt here with the harness identity recipe: unstripped 5a13b87f… reproduced exactly.
Scores are `harness/score.py --baseline base/g04/inventory.json`; only gains beyond 806 are reported.

## Scope

Windows (`claude-pump-work/targets/big-mid.json`), after the 21:5x scope change:

| window | bytes | identity (from original callers/callees) | status |
|---|---|---|---|
| 0x6fef8 | 9176 | set_reserved_fee_recipients body | open |
| 0x859b0 | 8944 | buy-side post-trade helper (TradeEvent / PostCompleteBuyEvent), callers 0x147ba0, 0x1489f8 | open |
| 0x6cd78 | 8544 | sell.rs body (called by 0x152888) | open |
| 0x72810 | 7832 | sweep_fees body (sweep_protocol_fee + sweep_creator_fee) | open |
| 0x6a8a8 | 6328 | add_quote_control_mint | open |
| 0x7c720 | 6312 | volume_accumulator::update_schedule (called by 0x746a8) | open |
| 0x75308 | 5920 | claim_token_incentives body | open |
| 0x98af0 | 5464 | Global::set_buyback_fee_recipients (Codex buyback-values packet recovers it) | open |
| 0x7f010 | 3544 | shared validation helper (callers 0x147ba0, 0x1489f8, 0x14a8a8) | open |
| 0x83c00 | 3440 | trade_v3.rs:691 buy-side helper | open |
| 0x65238, 0x68bd8 | | moved to the Pump session's round-4 lanes | dropped |
| 0x746a8, 0x76a28, 0x77940 | | moved to pump-big-lo (emit_cpi! error-path family) | handed off |

## Tools (tools/)

- `bm.py build <src> <label> [--ir] [--rustc-arg ..]`: harness fastbuild (shared 6-slot pool) + score vs g04.
  `--ir`/`--rustc-arg` add rustc args to the pump_recovered crate only (wrapper/), in a separate target dir.
- `irtool.py stub|llc|cmp`: stub every other function body, llc one function, compare with the original window.
  Calibrated: `llc -O3 -mtriple=sbf -mcpu=generic -mattr=+store-imm,+jmp-ext -relocation-model=pic
  -function-sections -data-sections -trap-unreachable -no-trap-after-noreturn` reproduces the linked
  function exactly (calib.py: incentives::execute 3152 B, ratio 1.0000). Without `-no-trap-after-noreturn`
  llc inserts a trap call after every noreturn call.
- `skel.py <orig>`: call/Source-site skeleton diff; `callers.py`: original callers/callees of a window.

## 0x746a8 (incentives::execute) — partial, handed to pump-big-lo

1. `let mint = ctx.accounts.mint.key();` before `Clock::get()?`, reused for update_schedule and the event
   (TECHNIQUES #3): ratio 0.672 → 0.938, size 3296 → 3152 (original 3168). Patch: partial/0x746a8-incentives-mint-capture.patch.
   `emit!(event)` instead of `emit!(event.clone())` gives a byte-identical ELF (no effect here).
2. Residual = the emit_cpi!/`?` return shape. Cause at IR level (pass dump with
   `-Cllvm-args=-print-after-all -filter-print-funcs=…`): rustc's MIR exit drop tree gives the three `?` exits
   (Clock::get, update_schedule, invoke_signed) a shared error-join block (StorageDead chain of the locals live
   across them) before the return block. After SROA it has its own phis, and the first InstCombine folds
   the three `extractvalue %err, 1` incoming values into one aggregate `phi { i64, ptr }`. Consequences:
   - the update_schedule error edge has no block of its own, so the payload load (`ldxdw [r10-0x108]`)
     stays in the call block instead of being sunk into the error edge (MachineSink cannot split critical
     edges on SBF: BPFInstrInfo::analyzeBranch fails on conditional branches);
   - the return pair is register-allocated as tag=r2/payload=r1 instead of the original tag=r1/payload=r2,
     which is the "Rc load scheduled after the From<ProgramError> call" residual in the emit_cpi! failure path
     (`ldxdw r3,[r10-0x58]` placement).
   IR experiment E (ir-experiments/expE.py): remove the error-join block, give each error edge its own
   block with its `extractvalue`, and feed one return-block phi with heterogeneous incoming values
   (`undef`/2 from Ok). llc then reproduces the original's payload-load block and its tag/payload register
   assignment exactly. What remains in expE is block placement: the original keeps the return block last and
   its invoke_signed check is `jeq ok; ja err` (Ok block not the IR successor at ISel), where we get `jne err`.
   Source form still open: the original must avoid the shared drop-tree node for the three exits (e.g. no
   locals live across all of them, or a different exit nesting).
