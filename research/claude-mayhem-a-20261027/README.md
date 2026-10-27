# Safe-Rust Mayhem initializer form (artifact-identical) — lane mayhem-a

**Headline: an ordinary safe-Rust source form of the O0193 initializer reproduces the
current 432-window Mayhem artifacts byte for byte.** It replaces the parent's
`#[repr(C)]` / `MaybeUninit` / `unsafe { assume_init_ref() }` construction with plain
Rust and changes no output byte: stripped `73dff97e65535ce7d2552ba6f29f94fe0e08ebd414a51871a81c6cba2d7d6168`
and symbols `440b92811753dd9af1468f6bf2d0e9139309984de3519a8f9a937babfdb6c903`, identical
to the parent's published `builds/current` ELFs. **No window count changes** (432/441
normalized, 100 raw-local, 9 unmatched / 107,952 B). Credit for recovering the O0193
window itself belongs to
[`mayhem-initializer-current-recovery-20261027`](../mayhem-initializer-current-recovery-20261027/README.md);
this packet contributes a more plausible source form for the same bytes.

Parent: [`research/mayhem-quotes-current-recovery-20261027`](../mayhem-quotes-current-recovery-20261027/README.md)
(rebuilt byte-for-byte in this lane from its 67 verified inputs: initializer-current
`source.tar.gz` + ownership-composition `sources/qualified.rs` + sell/quote `overrides/`).

## The exact source change (only `src/state.rs`; lines 531/532 unchanged)

```diff
--- a/src/state.rs
+++ b/src/state.rs
@@ -525,12 +525,12 @@
 
 
 #[inline(always)]
-fn initialize_state(mint_key:&Pubkey, params:&crate::GlobalParams, state:&mut MayhemState)->Result<()> {
+fn initialize_state(mint:&InterfaceAccount<'_, Mint>, params:&crate::GlobalParams, state:&mut MayhemState)->Result<()> { let mut mint_key=Pubkey::default(); let mint=mint.to_account_info(); mint_key=mint.key();
 
     let duration_hours=params.field_6 as i64;
     let now=                 Clock::get().unwrap().unix_timestamp; state.field_8=now as u64;
     state.end_timestamp=       now+duration_hours*3600;
-    state.mint=*mint_key;
+    state.mint=mint_key;
     state.field_56=0;
     state.field_89=now as u64;
     state.flag_88=false;
@@ -544,8 +544,8 @@
 }
 
 
-pub fn initialize(ctx:Context<crate::InitializeMayhemState>)->Result<()> { let mut snapshot=InitMint {key:std::mem::MaybeUninit::uninit(),info:ctx.accounts.mint.to_account_info()}; snapshot.key.write(snapshot.info.key()); initialize_state(unsafe { snapshot.key.assume_init_ref() }, &ctx.accounts.global_params, &mut ctx.accounts.mayhem_state) }
-#[repr(C)] struct InitMint<'info> { key:std::mem::MaybeUninit<Pubkey>, info:AccountInfo<'info> }
+pub fn initialize(ctx:Context<crate::InitializeMayhemState>)->Result<()> { initialize_state(&ctx.accounts.mint, &ctx.accounts.global_params, &mut ctx.accounts.mayhem_state) }
+
```

Full file: `layers/initializer-safe-form/source/src/state.rs`; all 67 input hashes:
`layers/initializer-safe-form/source-inputs.json` (only `src/state.rs` differs from the
parent).

## Why this is the more plausible original form

- It is ordinary, idiomatic safe Rust: a private `#[inline(always)]` helper that takes the
  mint account by reference, derives its `AccountInfo`, reads the key and fills the
  state. No `unsafe`, `MaybeUninit`, `#[repr(C)]` layout control or snapshot struct is
  needed; a 2025 Anchor program is far more likely to contain the former than the latter.
- The two codegen properties the parent forces through layout tricks follow from normal
  compiler behavior here (checked with MIR/IR dumps, `tools/mirdump.sh`/`irdump.sh`):
  * passing `&mut MayhemState` into the helper keeps the key copy's destination pointer
    in the pre-overflow-check block (InstCombine only sinks into an immediate successor),
    giving the original's unfolded `r3 = r7+0x160` descending copy and `xor; jeq X,1`
    overflow test;
  * rustc renumbers MIR locals by first use after copy propagation: an SSA key local is
    replaced by the later call temporary, but the non-SSA
    `let mut mint_key = Pubkey::default(); … mint_key = mint.key();` keeps the key as the
    lower-numbered local, so its alloca is laid out deepest (key, then AccountInfo, then
    Clock), as in the original. The dead default store is removed by the optimizer.
- Behavior is identical by construction (identical ELF), so the parent's runtime evidence
  (6,636 trade and 69 initializer comparisons on `73dff97e…`) applies unchanged.

## Verify (standard library only; no HOME, compiler, VM or network)

```sh
python3 -I -B research/claude-mayhem-a-20261027/verify.py
```

It checks that the shipped `layers/initializer-safe-form/artifacts/*.so.gz` equal the
parent's `builds/current/*.so.gz` byte for byte, that applying `source.patch` to the
parent's `src/state.rs` reproduces the shipped `source/src/state.rs` exactly (and its
recorded hash), that the other 66 inputs are unchanged, and that the initializer region
contains no `unsafe`/`MaybeUninit`/`repr(C)`. It passes under `env -i HOME=<empty dir>`.
Build record: `layers/initializer-safe-form/builds/recovered/` (command, environment,
link map, compiler log; `tools/mbuild.py` qualified mixed-SDK recipe).

Controls on the way (ordinary source; none closes O0193 alone): A (early `mint.key()`
local) 960 B but frame/copy/overflow differ; B (key read before the clone) right frame,
wrong copy order; C/D (explicit `&mut *` deref) identical to A; E (field_89 between the
i128 zeroings — needed, otherwise MemCpyOpt merges them into one memset); F1/G/H
(deferred-init key forms) renumbered like A; K1 (non-SSA key without the helper) right
frame, copy-out/overflow differ; C1 (non-SSA key inside the parent control's
`AccountInfo`-taking helper) only the frame differs; C2 (key passed by value) reverts to
the control; C4 = this form (first measured on the sizing-panic parent at 430/441).

## Secondary: Layer B allocator context on the 432 parent (CONDITIONAL independent reproduction — not a gain)

Main already composes the allocator context with the **complete historical
`declare_program!` macro**: [`mayhem-historical-macro-current-20261027`](../mayhem-historical-macro-current-20261027/README.md)
(78dfdbca8; 429-window parent, stripped `ed5b4020…`), the historical composition in
[`mayhem-initializer-current-recovery-20261027`](../mayhem-initializer-current-recovery-20261027/README.md)
(430/441, 141 raw-local; stripped `9e0e32a9…`, symbols `a6a4e593…`) and
[`mayhem-native-current432-composition`](../mayhem-native-current432-composition/README.md)
(13c846906, shayanel; native Linux, 432/441, 85 native raw-local; stripped `9d6b9032…`).
This layer is only an independent re-derivation in the hand-rendered, Anchor 1.0.0
mixed-source form on the qualified 432 parent. **Its 141-raw artifact is not byte-equal
to any of those** (`2ef6328d…`/`c9abef93…` vs `9e0e32a9…`/`a6a4e593…` and
`9d6b9032…`/`9874fa10…`): the parents differ (430 vs 432 sources; PR #282 vs qualified
Legacy Buy), the toolchain differs for the native packet, and the macro form differs
(rendered parser vs complete historical macro). Its raw-local count must not be added to
any row.

The same two-file curve-crate change (appended rendered `legacy_event_utils` module +
`CreateEvent` IDL entry) composed onto the 432 parent (`layers/allocator-context-432/`):
432/441 normalized (no gain, no loss), **raw-local 100 → 141** (the 39 bodies below plus
O0166 and O0194, which now align because the parent's initializer already has the
original 960-byte size), positive direct edges 4,314 → 4,315, Source records 456 → 456,
no losses (parent `progress.compare()`). Stripped `2ef6328d429dfe2cc99fec477398db59f386d81cd379584d4a41e151b65d90a5`
(755,392 B), symbols `c9abef9305d27417d566e8d5cae323d921275c01c518b1362c937b9bf044aab9`
(gzipped in `layers/allocator-context-432/artifacts/`). Full unchanged 14-suite replay on
this exact stripped ELF: **6,636 comparisons, 13,272 signed records, 0 mismatches, 0
normalized-log differences** (`layers/allocator-context-432/runtime-summary.json`).
This exact qualified-432 composition is not on main (the native Linux composition
`mayhem-native-current432-composition` reports 432/85 native and keeps the historical
430/141 separate). Everything said below about the mechanism, its dead-code nature and
its CONDITIONAL status applies unchanged.

## Layer B — allocator compilation context (CONDITIONAL; first measured on the 429 parent)

**This layer is not claimed as recovered source.** It composes, onto the parent,
the mixed-source diagnostic of
[`research/mayhem-allocator-parser-provenance`](../mayhem-allocator-parser-provenance/README.md)
(startrack3r): the historical Anchor `declare_program!` event-parser template
(the `utils` module emitted on all targets before Anchor commit `624f3ae`),
rendered for the public Pump `CreateEvent` type, plus that event/type in the
curve crate's IDL. That packet's caveat applies unchanged: it is a mixed-source
diagnostic combining an older event-parser template with Anchor 1.0.0-generated
event types from the current published Pump IDL; it does not establish the
original IDL, Anchor revision or source.

What the change does:

- `curve-accounts/src/lib.rs`: the rendered `legacy_event_utils` module (copied
  byte-for-byte from that packet's enabled controller) is **appended at the end of
  the file**, after `pub use anchor_spl::token_interface;`, so no existing line or
  Location record moves.
- `curve-accounts/idls/pump.json`: `events` + `types` entries for `CreateEvent`
  (instructions, address and metadata unchanged).

Mechanism: the parser's `CreateEvent::try_from_slice` instantiates borsh `String`
deserialization (`vec![0u8; n]`) in the curve crate's single codegen unit. That
zeroed allocation keeps `Global::alloc_impl`'s `zeroed` parameter non-constant
for IPSCCP, which changes the curve crate's `alloc::raw_vec::finish_grow` from
312 to 328 bytes — the shape of both original windows O0209 and O0237. **The
parser code itself is dead code: it is absent from the linked output.** Text grows
by exactly 16 bytes and `finish_grow` is the only changed function body. Whether
the original program really contained such a context (historical Anchor
`declare_program!` with an events-bearing Pump IDL) is unproven; the
admissibility of this layer as recovered source is therefore **unproven**.

Measured with the parent's own `progress.compare()` (unchanged code, via
`progress_check.py`) and this packet's `measure.py`:

- normalized 429 → 429 (no gains, no losses);
- raw-local **100 → 139** (+39: O0197 O0198 O0200 O0207 O0208 O0209 O0217 O0219
  O0225 O0227 O0228 O0229 O0233 O0237 O0245 O0259 O0263 O0268 O0272 O0273 O0275
  O0278 O0279 O0280 O0281 O0282 O0287 O0300 O0301 O0312 O0315 O0316 O0322 O0333
  O0334 O0341 O0354 O0358 O0360), no raw loss;
- positive direct edges 4,288 → 4,289 (O0210's reserve now calls a 328-byte
  `finish_grow`, as in the original), positive Source records 446 → 446, no
  observed Source-profile loss.

Artifacts (gzipped, mtime 0) in `layers/allocator-context/artifacts/`:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| candidate.so (stripped) | 755,104 | `ed5b4020ca2659b427739a384bc7c014e2b192f81cce60d7d9b770d4978f0232` |
| symbols.so | — | `90b64207d062d0a6e4d38d83129bd69a47ae1fa478367f3e13efb53f7da4af8f` |

Runtime: the unchanged 14-suite trade replay of the parent
(`research/mayhem-sizing-panic-recovery/replay.py`) ran on this exact stripped
candidate: **14/14 suites, 6,636 comparisons, 13,272 signed transaction records,
0 checked-field mismatches, 0 normalized-log differences**
(`layers/allocator-context/runtime-summary.json`; per-suite receipts and logs in
`layers/allocator-context/runtime/`). Finite local LiteSVM corpus only.

### How this relates to the other allocator packets on main

| Packet | What it shows | Whole-program ELF? |
| --- | --- | --- |
| [mayhem-allocator-context](../mayhem-allocator-context/README.md) (startrack3r) | a zeroed `vec!` in the curve crate is a sufficient context for the 328-byte body | older qualified parent only |
| [mayhem-allocator-parser-provenance](../mayhem-allocator-parser-provenance/README.md) (startrack3r) | the historical event-parser template (rendered, with Anchor 1.0.0 event types) is such a context; the Solana gate reverses it | older parent (428 windows) |
| [mayhem-historical-framework](../mayhem-historical-framework/README.md) (startrack3r, 0a881f726) | with **consistent historical Anchor c0077c2** runtime/derive/macro/registry versions and the unmodified `declare_program!(pump)`, the curve object's helper is 328 B; the historical gate and a no-event control give 312 B | **no** — the historical-runtime roots fail to compile |
| [mayhem-control-work-20261027](../mayhem-control-work-20261027/README.md) (Codex, 2ae5b07af) | composes the rendered parser onto the sizing-panic parent: stripped `ed5b4020…`, 429/139, full replay | yes |
| [mayhem-historical-macro-current-20261027](../mayhem-historical-macro-current-20261027/README.md) | the **complete historical macro** (no hand-rendered parser) on current source reproduces stripped `ed5b4020…` exactly | yes |
| **this layer** | independent whole-program build and measurement of the same composition | yes |

This layer's stripped ELF is byte-identical to the artifact already published by
mayhem-control-work-20261027 and reproduced by mayhem-historical-macro-current-20261027
(`ed5b4020…`); its symbol ELF (`90b64207…`) differs from the latter's (`281c2f67…`) only
where symbol/string tables name the parser's module. It is therefore an
**independent reproduction, not a new gain**: the 39 raw-local bodies must not be
counted twice. Its context is the **Anchor 1.0.0-generated, hand-rendered
mixed-source form** of the parser-provenance packet (rendered `legacy_event_utils`
module + `CreateEvent` IDL entry, current Anchor 1.0.0 runtime). It does **not**
use the historical framework's consistent c0077c2 Anchor inputs, and it does not
use the complete historical macro. The historical-framework packet strengthens
the plausibility of the mechanism (the 328-byte body arises under a consistent
historical Anchor stack) but provides no linked program; this layer and the two
whole-program packets above provide the linked measurement (raw-local 100 → 139,
no losses). The label stays **CONDITIONAL / not recovered source**.

Re-measure without rebuilding (from the repository root):

```sh
python3 -B research/claude-mayhem-a-20261027/measure.py \
  research/claude-mayhem-a-20261027/layers/allocator-context/artifacts/symbols.so.gz \
  --base research/mayhem-sizing-panic-recovery/artifacts/recovered/symbols.so.gz
python3 -B research/claude-mayhem-a-20261027/progress_check.py \
  research/claude-mayhem-a-20261027/layers/allocator-context/artifacts/symbols.so.gz
```

## Build recipe

Same compiler/target/linker recipe as the parent: Mac v1.54 `rustc`/`cargo`
(`c58ec8ad…`/`dc5107a8…`) with the 26 official Linux v1.54 `sbpf-solana-solana`
rlibs (each verified against the official archive `fcc41631…` hashes recorded in
`research/mayhem-sell-quote-call-recovery/provenance/archive-check.json`), the
parent's unchanged qualified `ordered.ld` (rustc's default script is checked
byte-equal to the parent's `default.ld` before substitution), v1.52 `llvm-objcopy
--strip-all`. `tools/mbuild.py` is the driver; `builds/recovered/launch.json`
records the exact command and environment. Source = parent `source.tar.gz` +
`layers/allocator-context/source.patch` (`source-inputs.json` lists all 67 file
hashes).

## Other windows (work in progress; no claim)

See PROGRESS.md for the per-window residual diagnosis (initializer O0193, AMM buy
quote O0092, legacy Buy O0081, BuyV2 O0083, BuyPumpSwap O0077).
