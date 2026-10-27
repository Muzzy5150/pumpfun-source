# Lane mayhem-a progress (buy side + initializer + allocator)

Parent: `research/mayhem-sizing-panic-recovery` (origin/main 8aa06f247; its parent is
mayhem-trade-origins-validator e2b9060f6): 429/441 normalized, 100 raw-local,
12 unmatched (111,288 B); stripped f4f6a368…, symbols 2f6e9ad9…, reproduced
byte-for-byte locally (lane tree b/v3, build mixed-v3-qual).
Owned windows: O0083 BuyV2, O0081 Buy, O0077 BuyPumpSwap, O0092 AMM buy quote,
O0193 initializer, allocator gap (O0209/O0210). O0095 was closed by the
trade-origins-validator parent.

## Environment (reproduced)
- Mixed sysroot `SP/lanes/mayhem-a/sysroot-mixed`: Mac v1.54 rustc/cargo/rustdoc
  (c58ec8ad…/dc5107a8…/ed86c6dd…) + the 26 Linux v1.54 sbpf-solana-solana rlibs,
  each verified against `research/mayhem-sell-quote-call-recovery/provenance/archive-check.json`.
- Builds: `tools/mbuild.py` (packet build.py command/env; CARGO_HOME=~/.cargo offline;
  qualified link swaps rustc's default script, verified byte-equal to config/default.ld,
  for the trade-origins-validator config/ordered.ld). Every cargo call holds the sbf slot lock.
- Variant loop: `tools/variant.py` (copies a tree, applies an edit script, rsyncs into one
  work tree WITHOUT -t so changed files get fresh mtimes, builds, measures).
  NOTE: an earlier `rsync -a` let cargo reuse a stale curve-crate object (mtime restored);
  results from that window (init-k1/k2/p2/q1 raw counts) were discarded and K1 rebuilt
  with a clean curve crate.
- Mac-only SDK reproduces 427/441 (loses O0236/O0337 only) — used only for orientation.

## Current parent (re-based)
research/mayhem-quotes-current-recovery-20261027: 432/441, 100 raw-local, 9 unmatched
(107,952 B); stripped 73dff97e…, symbols 440b9281… — rebuilt byte-for-byte in this lane
(tree b/v4 = initializer-current source.tar.gz + ownership-composition sources/qualified.rs
+ sell-current and quotes-current overrides; all 67 source hashes verified).
Remaining owned windows: O0083 BuyV2, O0081 Legacy Buy, O0077 AMM Buy (O0092/O0093/O0193
closed upstream).

## Results on the 432 parent
- Layer A (safe-Rust O0193 form, layers/initializer-safe-form): byte-identical stripped and
  symbol ELF to the parent (73dff97e…/440b9281…); replaces the parent's MaybeUninit/unsafe/
  repr(C) form. No count change.
- Layer B-432 (CONDITIONAL allocator context, layers/allocator-context-432): 432/441,
  raw-local 141 (+41), edges 4314→4315, Source 456→456, no losses; stripped 2ef6328d…,
  symbols c9abef93…; 14/14 replay, 6,636 comparisons, 0 mismatches, 0 log differences.
- BuyV2 (O0083) port into pump_interface_v2.rs (edits/bv2_a.py, WIP, not committed as a gain):
  18,344 B vs 18,648 original (parent 7,688), structural ratio 0.31 → 0.74, 432/100 kept.

## Verified results (history, 429 parent)
1. Layer B allocator context — CONDITIONAL (not recovered source; see README):
   build alloc-b = parent + appended rendered event-parser module + CreateEvent in the
   curve IDL. 429/441, raw-local 139 (+39), no losses (parent progress.compare passes;
   positive edges 4288→4289, Source 446→446). Stripped ed5b4020…, symbols 90b64207….
   Runtime: complete — 14/14 suites, 6,636 comparisons, 13,272 signed records,
   0 mismatches, 0 normalized-log differences (runtime-summary.json, runtime/).
   POSITIONING: the stripped ELF ed5b4020… is byte-identical to the artifact already
   published by research/mayhem-control-work-20261027 (Codex) and reproduced from the
   complete historical macro by research/mayhem-historical-macro-current-20261027; this
   layer is an independent reproduction in the hand-rendered Anchor-1.0.0 mixed-source
   form, NOT a new gain (do not double count). research/mayhem-historical-framework
   (startrack3r, 0a881f726) shows the 328 B body under consistent historical Anchor
   c0077c2 inputs but has no whole-program ELF.

## Per-window residuals (work in progress)
- O0193 initializer (960 B original; parent 920 B). Best variant `init-k1`
  (edits/init_k1.py): 960 B, 116/116 instructions, all stack slots, the Rc clone/drop,
  the zero-store pairs and the Location records equal. Findings:
  * the key is copied to a stack local BEFORE Clock::get (original reads it early);
  * the original's key local has a lower MIR index than the AccountInfo local (frame:
    key deepest) — reproduced by a non-SSA local `let mut mint_key=Pubkey::default(); …
    mint_key=mint.key();` (SSA forms are renumbered by copy-prop/SimplifyLocals);
  * field_89 must be assigned between the two i128 zeroings (otherwise MemCpyOpt merges
    them into one memset and the hi/lo store order differs).
  Two residuals remain: (a) the original copies the key out through an unfolded base
  `r3 = r7+0x160`, descending, i.e. the memcpy destination GEP lives in the pre-check
  block (MIR GVN/ReferencePropagation rewrites every `state` form tried into per-use place
  projections); (b) the signed-add overflow test is `xor; jeq X,1` in the original (unique
  to O0193 in the whole original binary; every other sadd check, and every reconstruction
  function, uses `xor; and 1; jne X,0`). Next: llc IR-edit experiments (build init-k1-bc).
- O0092 AMM buy quote (1256 B; parent 1120 B). [Touched by mayhem-a; the near-miss
  workflow has two agents on O0092 — this lane stops here to avoid duplication.] `native_mint::id()` + selected cap with
  zero-guarded min (edits/bq_a.py) gives 1176 B, ratio 0.67; the original additionally
  tail-duplicates the cap load/compare into all three quote-mint paths (default/native/
  other). Four further spellings of the min/cap expression canonicalize identically.
- O0081 legacy Buy (13848 B; parent 13680 B): call skeleton aligned; residuals are the
  price-check multiply/divide order (orig mul,mul,mul,div,div) and error-block placement.
- O0083 BuyV2 (18648 B; parent 7688 B): original code lives in pump_interface_v2.rs
  (Location 393:25/394:26 and a Source record there); original inlines 27 of 28
  AccountInfo clones (inline_cpi_info/clone_info idiom), uses the legacy-Buy
  `cpi_result` error idiom and the closure price check.
- O0077 BuyPumpSwap (9736 B; parent 9024 B): call order and CPI construction differ
  (ratio 0.22); candidate's outlined `math()` helper (merged with buy_v2::math) has no
  original counterpart.
