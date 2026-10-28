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

## Checkpoints committed

- `checkpoints/cp4-q04-o0075/` (current): **O0075 gained, 433/441 normalized, 100 raw-local, no losses.**
  - Edges 4,314 to 4,363; Source records 456 to 467.
  - Sweep differential: 692 cases, 0 mismatches, 0 non-compute log differences.
  - 14 trade suites: 6,636 cases, 0 mismatches, 0 normalized log differences.
  - Stripped `c1f25d01...`, symbols `73c28d5e...`. No Stack offset warnings. A repeat build is identical.
  - Source edit: `edits/q04_o0075.py`, described in the O0075 section below.
- `checkpoints/cp3-q03-sweep-columns/`.
  - **Diagnostic gain:** the sweep differential's non-compute log differences go from 58 (parent) to **0**. Every sweep panic now reports the original `line:column`.
  - **Change:** whitespace and line placement only (`edits/q03_columns.py` applied to the cp2 source). The sites are 276:84, 296:86, 353:84, 358:37 and 368:86.
  - **Counts:** 432/441 normalized, 100 raw-local, no losses of any kind.
  - **Trade suites:** all 14 (6,636 cases) give 0 mismatches and 0 normalized log differences.
  - **Hashes:** stripped `352328e2...`, symbols `b278b298...`. No Stack offset warnings.
- `checkpoints/cp2-q432-sweep-restructure/`: the sweep restructure plus the sell_amounts zero-check idiom on the 432 parent.
  - 432/100, no losses. Stripped `becda737...`.
  - 17 sweep log differences remained; cp3 fixes them.
  - O0075 is at the original 8,008 bytes with 8 differing instructions (below).
- `checkpoints/cp1-sweep-restructure/`: the same work on the older spr parent (superseded).

## Environment (durable since the 20:43 /tmp wipe)

W = /Users/shawwalters/Documents/Codex/2026-10-24/claude-mayhem-work

- **`W/mayhem-env/sysroot`** (shared, read-only):
  - Mac v1.54 rust plus the 26 official Linux v1.54 target files.
  - build_lane.py hash-checks them against the provider-sharing launch.json, which is copied to `build/provider-sharing-launch.json` and sha-pinned.
- **`W/mayhem-env/parent-432`** (published for other lanes):
  - The pristine parent tree: cp2 with its `source.patch` reversed. All 67 files equal quotes-current `source-inputs.json`.
  - Rebuilt in place: `73dff97e...` / `440b9281...`.
- **`W/mayhem-b/build`:**
  - `layout-lane-linux-target2-sysroot`, a symlink to the shared sysroot.
  - `cargo-home`, an APFS clone of Codex `work/mayhem-priority-20261027/cargo-home`.
  - `qualified/{linker.py,default.ld,ordered.ld}`, from quotes-current `layout/`.
  - The tools.
  - `roots/work`, the working source as a git repo with one commit per step.
- **Outputs and targets:** outputs go to `W/mayhem-b/out/builds/LABEL`. Cargo targets go to `W/mayhem-b/target`, a symlink to `SP/lanes/mayhem-b/target`, which can be recreated.
- **Shared users of the controller** (read-only), each with its own label and target prefix:
  - fees-final (`ff-`, O0073);
  - the buy-side IR workflow (`ir-o77`, `ir-o81`, `ir-o83`).
- **Tools:**
  - `tools/build_lane.py LABEL ROOT [TARGET]` rebuilds the root crate only in ~15-25 s and reproduces the parent bit-for-bit.
  - `tools/measure.py` applies progress.py logic against the parent and reports losses.
  - `tools/batch.py SLOT spec.json` builds several variants per sbf slot.
  - `tools/irbatch.py` dumps IR and MIR.
  - `tools/irsurg.py`, `irperm.py`, `objsec.py` and `cmpobj.py` edit one function's IR, re-run `llc` and compare with the original window.
    - `llc -O3 -mtriple=sbf -mcpu=generic -relocation-model=pic -function-sections` on the rustc-emitted IR reproduces rustc's bytes exactly.
  - `tools/run_trades.py` runs the 14 trade suites.
  - `tools/make_checkpoint.py` assembles a checkpoint that verify.py accepts.

## Coordination notes

- **validate_sweep (O0073, fees-final):** my restructure does not change it.
  - Its definition at fee_recipients.rs:45-65 is untouched. The built function is normalized-identical in parent and cp3 (920 bytes).
  - Only the call site moved: from lib.rs:433 `if !admin {..}` to fee_recipients.rs:272 in the trader sweep.
  - fees-final should keep fee_recipients.rs line counts above line 264 unchanged, because every sweep panic location depends on them.
  - Edits by fees-final: none landed yet.

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

## O0075: closed in cp4

**Original preheader:** token_program, quote_ata and admin field loads, then `remaining.ptr` last. Before cp4 the candidate loaded `remaining.ptr` first, then the three fields in the opposite order. The cause was proven on rustc's IR with `llc` (`tools/prehdr.py`, specs in `tools/irexp/`).

**Fix 1: load `ctx.accounts` in the entry block.**
- The pre-RA list-ilp scheduler ranks a load whose base operand is already live and defined in the same block (LiveUses) ahead of a load from the `ctx` argument. While the accounts pointer was loaded inside the preheader block, `remaining.ptr` always went first.
- With the accounts pointer loaded in the entry block, it becomes a cross-block value: a CopyFromReg, which MachineSink later sinks after the length check. The tie disappears and `remaining.ptr` is scheduled last.
- Source: `let accounts = &*ctx.accounts;` before `require!(ctx.remaining_accounts.len() == 16, ..)`.
- Control: `let accounts = &ctx.accounts;` emits no load and leaves the result unchanged.

**Fix 2: hoisted loads in the order admin, admin_quote_ata, token_program.**
- The scheduler emits these hoisted loads in reverse IR order, so the IR needs admin first.
- Source: bind the three before the loop on the `let mut total` line, as `let x: &AccountInfo<'info> = self.x.as_ref();`, in the order admin, admin_quote_ata, token_program.
- Loop uses: `token_program.key()`, `admin_quote_ata.to_account_info()` and `admin.to_account_info()`.
- Of all 24 IR orders, only rem, 600, 160, 616 with the accounts pointer in the entry block gives 0 differences. The other source orders tried (program/ata/admin, ata/admin/program) leave 4 differences.

**Trader, with the same two changes** (`t2-*` variants):
- Binding orders trader/ata/program and program/ata/trader keep O0075 and give O0076 ratios of 0.281 and 0.282. No change.
- O0076's residual is elsewhere (see below).

## O0076 residual

Same restructure gives 8,464 vs 8,400 bytes; the require! error block is placed at the
end (original: inline after the first native-compare segment), and the limit select uses
520/576 instead of the original 176/232 + 344. Keeping the 344 base separate (llc
surgery) does not fix the placement. The trader loop's frequency structure (validate_sweep,
sweepable) drives MachineBlockPlacement differently; the seed form that fixed O0075's
frame (`let index = &[..]`) lowers O0076's alignment (0.53 -> 0.28 normalized ratio).

**2026-10-27 recheck on cp4** (`tools/irexp/lim.py`, trader IR with the accounts reference and bindings):
- The rustc IR keeps `select(native, 520, 576)` with a single load: 8,496 bytes, 990 differing slots.
- Branch plus phi of the offsets 176/232 on `accounts+344` gives 8,392 bytes and 841 slots. Without the separate 344 base it gives 842 slots.
- A phi of the two loaded values gives 8,464 bytes and 949 slots.
- So the branch form helps, but it is not sufficient.

**Where the trader residual sits (2026-10-27, after cp4)**

The original O0076 entry spills `ctx.accounts` immediately: `ldxdw r2,[r1+8]; stxdw [r10-632]`. It also tail-duplicates the native-mint compare diamonds (624-760) and puts the require! error block (232-616) right after the first compare segment. The limit is a select diamond, `mov r2,176; jne native; mov r2,232`, followed by `ldxdw [accounts+r2+344]`.

**What llc on rustc IR shows** (`tools/irexp/lim.py`, `tools/bindiff.py`):
- With an IR-level **branch** on `native` and a phi of 176/232 in a separate join (pre)header block:
  - the first 92 instructions match;
  - whole-body ratio 0.908 (versus 0.28 now);
  - what remains is register assignment (IV in r8 rather than r7) and one IV reload at the latch.
- An IR **select** of 176/232, with 344 kept separate in either GEP order, changes nothing (990 slots). The block boundary is what matters, not the offset form.
- Permuting the trader field and remaining-pointer loads inside the join did not help (877+ slots).

**Why the branch does not come from ordinary source**

After InstCombine sinks the two loads into a load of a phi of GEPs, SimplifyCFG's `foldTwoEntryPHINode` folds any empty diamond into a select. That happens unless the join has more than 2 phis, the branch carries weights, or the diamond is not simple.

Source forms tried, none of which leaves a branch (O0076 stays 8,464-8,696 bytes, ratio 0.28):
- the accounts reference;
- trader/ata/program bindings in both orders;
- `#[inline(always)]` on the trader method;
- a mut-assign limit;
- a helper taking `&Account<GlobalParams>` or `&GlobalParams`;
- a closure;
- the limit computed inside the loop, as a statement or as the sweepable argument (this one is worse: 8,672-8,696 bytes).

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

## O0079 SellPumpSwap (work in progress, no gain yet)

**Baseline (cp4).** The handler is 8,088 bytes against the original 17,312. With registers and frame offsets masked, the ratio is 0.285 (`tools/hunks.py LABEL O0079 regs`).

**What the original shows:**
- 21 + 2 **inline AccountInfo copies**: Rc strong-count increments with abort-on-overflow, and fields copied in struct order. The candidate instead makes out-of-line `<AccountInfo as Clone>::clone` calls. Only close_account's 3 copies and emit_cpi's 1 copy are real clone calls in the original.
- **No memcpy before the CPI**: the accounts struct is built in place.
- **`native` is computed late**: its WSOL compares come after sell_quote (2016-2136), not at handler entry.
- **effective_quote has one error block**: the i128 overflow and the try_from failure both jump to one MathOverflow conversion at 864.
- **Price math order**: price first (`__multi3`, `__udivti3`), then `checked_mul` (2x `__multi3`), then delta (`__udivti3`).
- **Seed descriptors come late**: they are built after most copies (about 8,544), as in Legacy Sell.

**Source steps** (spec generator `tools/mk_o0079.py`, batches m1-m7; 433 kept, no losses in every variant):

| Variant | Bytes | Masked ratio |
|---|---|---|
| copies through a non-inline helper (not inlined) | 8,088 | n/a |
| `#[inline(always)]` copy helper `info<T: AsRef<AccountInfo>>` | 16,296 | 0.24 |
| + `native`/`native_accounting` moved after sell_quote; inline(always) `price_check(vt,vs,reference,tol) -> Result<(),MayhemError>` computing price before `checked_mul` (m6-pc2) | 16,376 | 0.293 |
| + one `?` for effective_quote: `checked_add(..).and_then(\|q\| u64::try_from(q).ok()).ok_or(MayhemError::MathOverflow)?` (m7a) | 16,824 | 0.628 |
| + accounts struct literal written inside `CpiContext::new_with_signer(..)`, with no `let accounts` (m7b) | 17,728 | 0.709 |
| + inline sell seeds `&[&[b"sol-vault",&[ctx.bumps.sol_vault]]]` (m7c, best) | 17,816 | **0.717** |

**Remaining differences in m7c:**
- The MathOverflow conversion block is placed early. It needs to come after the price check, without its own From<AnchorError>.
- Copy interleaving and the position of the seed construction (a 1,872-byte region).
- Error and event tail placement (about 15,000-16,000).

**Error-conversion detail.** The original's two MayhemError conversions share one From<AnchorError> tail. The effective_quote block at 864 stores code 2. The price-check block at 2424 loads a variable code from a slot preset to 2 after validate_quote. In m7c the effective_quote conversion is constant-folded (`stw 6002`, `stb 2`) and keeps its own tail, adding 216 bytes. So in the original both conversions most likely meet in one IR-level conversion site, with a phi on the code, before constant folding. The source shape that does this is still to be found.

### O0079 round 2 (2026-10-27, after the coordinator's tail hints)

**Shared tail.** Both the original and the candidate already share **one** From<AnchorError> tail; the difference is layout.
- Original: the price-check conversion (code loaded from the slot preset to 2) falls through into the tail, at 2,768. The effective_quote conversion (constant 2, at 864, after the delta division) jumps to it.
- m7c: the effective_quote conversion owns the tail (1,096) and sits before the delta `__udivti3`. The price-check conversion jumps back into it.
- With two `?` (`try_from(..ok_or()?).map_err()?`), the effective_quote conversion moves right after validate_trade (masked ratio 0.595).

**m8 results:**

| Variant | Masked ratio |
|---|---|
| `.and_then(\|q\| q.try_into().ok())` (m8a) | 0.7165 (same as m7c) |
| `.or(Err(..))?` with two `?` (m8b) | 0.585 |
| inline(always) `effective_quote(amount, virtual_quote) -> Result<u64, MayhemError>` plus one `?` (m8c, best) | **0.7192** |
| price_check returning anchor `Result<()>` (m8d) | 0.686 |

**Next:** the layout looks branch-weight driven. `checked_*` carry `unlikely`; `try_from` does not. Check in llc with `!prof` edits on the m8c IR which weights put the delta block before the effective_quote conversion and give the tail to the price-check conversion.

### O0076 round 2

Moving the limit computation to be the last statement before the loop, with or without the bindings and the accounts reference (t6), still yields `select(520, 576)`, at 8,464-8,496 bytes and ratio 0.28. So an empty join block merged into the loop header does not explain the original branch either.

## Sell side handed off (2026-10-27 ~21:50)

O0082 Legacy Sell is now owned by **pump-lo** (`pl-`) and O0084 SellV2 by **pump-mid** (`pm-`). This lane keeps O0076 and O0079.

**Shared helper.** My `src/state.rs` `sell_amounts` edit is in the cp2-cp4 overrides. It is the zero-check idiom, `vs.checked_sub(output).and_then(|d| if d == 0 { None } else { Some(..) })`, with the unwrap at 398:90. It is shared by Legacy Sell and SellV2. Upstream `mayhem-sell-checked-value-price` uses a `?` closure with the same effect, and swapping it in changes neither window.

**Composition results on cp4** (batch `u1`; 433 kept, no losses):

| Variant | O0082 bytes (original 12,992) | O0082 ratio | O0084 |
|---|---|---|---|
| cp4 (sell_amounts idiom only) | 13,008 | 0.328 | 17,960 / 0.287 |
| + value pricing (`mayhem-sell-checked-value-price` pump_interface hunks) | 12,864 | 0.332 | unchanged |
| + inline seeds (`mayhem-legacy-sell-seed-lifetime`) | 12,952 | 0.530 | unchanged |
| + value pricing + inline seeds | 12,848 | **0.538** | unchanged |
| + their sell_amounts closure as well | 12,848 | 0.538 | unchanged |

Specs: `tools/irexp/` does not cover these. The generator is `out/specs/mk_u1.py` in the durable lane dir, copied to `tools/mk_u1.py`.

## Negative controls (beyond those above)

O0075: `&ctx` associated fns, outer `signer_seeds` array, `chunks(2)`, Transfer struct
before CpiContext (all worse); `&&[AccountInfo]` param, `total` before `native`, gp
reference for the limit (no change).
