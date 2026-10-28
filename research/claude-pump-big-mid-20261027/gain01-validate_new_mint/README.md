# gain01: `QuoteControl::validate_new_mint` (0x68bd8, 3,488 B)

**Result:** g04 806 → **807** normalized; raw unchanged at 165. No normalized or raw losses, `runtime_valid`,
no stack-offset warnings. On L06: 899 → **900**, gain 0x68bd8, no losses.

| base | before | after | gains | unstripped ELF |
|---|---|---|---|---|
| g04 | 806 | 807 | 0x68bd8 | `2998b92c…` (stripped `73ceea96…`) |
| L06 | 899 | 900 | 0x68bd8 | `0977ffc4…` |

- **Patch:** `source.patch` changes one line of `src/quote_control/state.rs`, so no Source line moves. It applies
  with `git apply -p1` inside a copy of `base/g04/pump` and unchanged to `base/L06/pump`.
- **ELFs:** `elf/` (gzipped stripped and unstripped, `SHA256SUMS`).

## Source form (behaviour unchanged)

```rust
require_eq!(
    self.mints.iter().position(|entry| entry.mint == *mint).is_some(),   // was: self.contains(mint)
    false,
    PumpError::QuoteMintAlreadyWhitelisted
);
```

`contains` returned the same `position(..).is_some()` from a separate function, so the check's value and both
evaluations of it (the compared value is evaluated again for `with_values`) are unchanged.

## Why it matches (IR-first proof)

g04 already had every block of the original; only the layout differed: the return block came last instead of
right after the `len > 255` check, and the `require_gt!` error block came first.

1. **IR proof.** `tools/irtool.py` reproduces the linked g04 function exactly with the v1.44 `llc`
   (`-no-trap-after-noreturn` is required). Moving only the return block so that it follows the
   `require_gt!` check in IR order reproduces 0x68bd8 byte for byte (`ir-experiments` notes in PROGRESS.md).
   Any other position fails. Branch weights on the error edges do not help.
2. **Why IR order decides.** `BPFInstrInfo::analyzeBranch` cannot analyze conditional branches.
   - MachineBlockPlacement pre-merges every block that ends in a conditional branch with its fall-through
     successor ("unanalyzable fallthrough").
   - So whatever ISel leaves as the fall-through of the `jgt len, 255` block (the next IR block, if it is a
     branch target) stays its layout successor.
3. **Why the source form decides IR order.**
   - rustc creates LLVM blocks when a terminator first references them, and codegens MIR in reverse postorder.
   - With `self.contains(mint)` the check is `switchInt(contains) -> [0: continue, otherwise: error]`, so the
     error block is created right after the `require_gt!` block, and the return block is created last.
   - With `position(..).is_some()` at the call site, `is_some` is MIR-inlined and its bool is threaded into
     the discriminant dispatch (PreCodegen MIR): `switchInt(discriminant(_44)) -> [1: error, 0: require_gt!
     check, otherwise: unreachable]`. The Some/error target is listed first, so its block is created first.
   - Reverse-postorder codegen then emits that error chain before the `require_gt!` check. Its
     `goto -> return` creates the return block immediately after the `require_gt!` block.
   - This is exactly the order the IR proof needs.
4. **Variants tried** (each copy compiled in the real crate and compared with `llc` against the original; only
   the Source line immediates of the copies differ):
   - `position(..).is_some()` at the call site matches.
   - So does an `Option<usize>` helper with `.is_some()` at the call site.
   - `contains` with `any`, `find`, `for`, an index loop, `#[inline]`, `#[inline(always)]`, `matches!` or
     `!is_none()` does not match.
   - Explicit `if`/`return Ok(())`/scoping variants of the `require_gt!` tail do not match either.

## Runtime

- `runtime-quote_control.json`: quote_control suite (`add_quote_control_mint` calls `validate_new_mint`):
  507/507 cases, 0 errors, 507 paired diagnostic-log cases, 0 diagnostic mismatches.
- `runtime-corpus44.json`: the full 44-suite corpus on the same stripped ELF: **44/44 suites, 10,468/10,468 cases,
  0 errors, 10,464 paired diagnostic-log cases, 0 diagnostic mismatches**.
- Runner: `tools/rt.py` → `tools/run_suites.py` (pump-hi's runner), repository harness scripts unchanged. The
  candidate is staged inside the worktree, and tokenkeg_two_curve is bound to the exact compiled fastbuild
  workspace through `scripts/build_source_manifest.py`.

`verify.py` is stdlib only and passes with `HOME` set to an empty directory.
