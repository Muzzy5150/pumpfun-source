# pump-big-mid progress log (lane `pump-big-mid`, 2026-10-27)

Baseline: g04 = Pump session genuine composite `claude-pump-work/base/g04` (806 normalized / 165 raw,
unstripped 5a13b87f…). Rebuilt here with the harness identity recipe: unstripped 5a13b87f… reproduced exactly.
Scores are `harness/score.py --baseline base/g04/inventory.json`; only gains beyond 806 are reported.

## Scope

Windows (`claude-pump-work/targets/big-mid.json`) after the coordinator's 22:1x/22:2x corrections: 11 windows.
Off-limits: 0x746a8/0x76a28/0x77940 (pump-big-lo, emit_cpi! family), 0x98af0 (already matched in L06), and
the 86 windows of `targets/r4-{pumpquote,quotectl,coordbody,plainbody}.json`.

| window | bytes | identity (from original callers/callees) | status |
|---|---|---|---|
| 0x68bd8 | 3488 | QuoteControl::validate_new_mint | **matched: gain01** |
| 0x6fef8 | 9176 | set_reserved_fee_recipients body | open |
| 0x859b0 | 8944 | buy-side post-trade helper (TradeEvent / PostCompleteBuyEvent), callers 0x147ba0, 0x1489f8 | open |
| 0x6cd78 | 8544 | sell.rs body (called by 0x152888) | open |
| 0x72810 | 7832 | sweep_fees body (sweep_protocol_fee + sweep_creator_fee) | open |
| 0x6a8a8 | 6328 | add_quote_control_mint | in progress |
| 0x7c720 | 6312 | volume_accumulator::update_schedule (called by 0x746a8) | open |
| 0x75308 | 5920 | claim_token_incentives body | open |
| 0x7f010 | 3544 | shared validation helper (callers 0x147ba0, 0x1489f8, 0x14a8a8) | open |
| 0x83c00 | 3440 | trade_v3.rs:691 buy-side helper | open |
| 0x65238 | 3192 | pump_quote.rs:406-415 helper (called by 0x65eb0) | open |

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

## gain01: 0x68bd8 validate_new_mint (807 on g04, 900 on L06)

- Change: `require_eq!(self.mints.iter().position(|entry| entry.mint == *mint).is_some(), false, ..)` in place of
  `self.contains(mint)` (one line, no Source line moves). Directory `gain01-validate_new_mint/`.
- IR proof: the g04 IR with only the return block moved right after the `require_gt!` check block reproduces
  0x68bd8 exactly with llc (ir-experiments/0x68bd8/vnmexp4.py scans every position; only that one matches).
  Branch weights do not change the layout.
- Mechanism (general, worth reusing): `BPFInstrInfo::analyzeBranch` cannot analyze conditional branches.
  - MachineBlockPlacement therefore pre-merges every conditional-branch block with its fall-through block in
    the initial (IR) order. The IR block creation order (rustc creates an LLVM block at the first terminator
    reference while codegenning MIR in reverse postorder) fixes those fall-throughs.
  - Here the MIR-inlined `is_some` gives `switchInt(discriminant) -> [1: error, 0: next, otherwise: unreachable]`,
    so the error chain is codegenned first and creates the return block right after the `require_gt!` check.
- Variant search (tools/irvariants.py compiles copies in the real crate and llc-compares each, ignoring only Source
  lines): call-site `position().is_some()` and an `Option<usize>` helper + `.is_some()` match; `contains` via
  any/find/for/index/#[inline]/#[inline(always)]/matches!/!is_none and explicit if/return/scope tails do not.
- Runtime: quote_control 507/507, 0 errors, 0 diagnostic mismatches; full corpus recorded in the gain directory.

## 0x6a8a8 add_quote_control_mint (in progress)

- `.ok_or(error!(Overflow))?` builds the error eagerly. The original builds it lazily
  (`ok_or_else`/`match` give identical code here).
- The original computes `required.saturating_sub(lamports)` and branches `if diff > 0`. With these two edits:
  0.49 → 0.65, 5848 B vs 6328.
- Remaining: the three AccountInfo clones for the transfer CPI are not inlined. The inline remarks show cold
  call sites (cost 60 > ColdCallSiteThreshold 45).
  - Diagnostic only: with `-inline-cold-callsite-threshold=100` the body grows to 6344 B and the frame-slot
    differences remain.
  - So a source form that keeps the transfer path above the 2 % cold limit is still needed (the original's
    branch hints).

## Next steps (exact, for a continuation)

1. 0x6a8a8 add_quote_control_mint (WIP patch `wip/0x6a8a8-add_quote_control_mint-WIP.patch`, apply on top of gain01):
   lazy Overflow error + `saturating_sub`/`if diff > 0` keep every line; ratio 0.65 (5848 B vs 6328).
   - Blocker: the transfer-path clones are cold call sites (inline remark cost 60 vs threshold 45). The path
     frequency is validate? x overflow x space? x (new_space > data_len) x Rent? x (diff>0, 62.5 %) ~ 1.95 %, just
     under the 2 % ColdCallSiteRelFreq.
   - The original must keep one more branch biased (most likely the checked_add `unlikely` hint).
   - Next: generate copies of the handler that differ only in the overflow/`?` forms (let-else, explicit
     overflowing_add, MIR-visible `checked_add` match); count out-of-line `AccountInfo::clone` calls in the IR;
     llc-compare each with tools/irvariants.py.
   - Then fix the frame-slot differences (space() sret at -0xe0 in the original).
2. 0x75308 claim_token_incentives / 0x859b0 (3 sites): first classify each emit_cpi!/`?` error edge with
   `git show 67a1705f8:research/claude-pump-big-lo-20261027/tools/errpath.py`.
   - Apply big-lo's `return Ok(())` drop-tree rule only on data-first edges.
   - Confirm no regression of 0x662c8 0x66fa8 0x67c38 0x6c160 0x79bc0 0x7a6c0 0x1348c0 0x135d60 0x137fc0.
3. 0x7c720 update_schedule: the original's sites are volume_accumulator.rs 297-394 and g04's are 151-198, so
   the body is structurally different. Start from tools/skel.py 0x7c720 (calls end_day twice, has an extra
   `unwrap_failed`).
4. Remaining large bodies (0x6fef8, 0x6cd78, 0x72810, 0x859b0, 0x7f010, 0x83c00, 0x65238): use tools/skel.py and
   tools/callers.py first. Apply the gain01 rule to any block-order-only residual: check whether the IR block
   order makes the right block the fall-through of the conditional branch, because SBF block placement keeps
   ISel fall-throughs.
