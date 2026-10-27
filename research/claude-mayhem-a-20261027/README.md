# Mayhem lane mayhem-a: buy side, initializer and allocator gap

Parent: [`research/mayhem-sizing-panic-recovery`](../mayhem-sizing-panic-recovery/README.md)
(429/441 normalized, 100 raw-local, 12 unmatched windows / 111,288 original text bytes;
stripped `f4f6a368…`, symbols `2f6e9ad9…`). Both parent artifacts were rebuilt
byte-for-byte in this lane before any change (see [PROGRESS.md](PROGRESS.md)).

## Status at a glance

| Layer | Normalized | Raw-local | Unmatched | Status |
| --- | ---: | ---: | ---: | --- |
| Parent (sizing-panic-recovery) | 429/441 | 100 | 12 (111,288 B) | reproduced |
| **Layer B: allocator context** | 429/441 | **139** | 12 (111,288 B) | **CONDITIONAL; independent reproduction of an already-published artifact — see below** |

No complete new function window is recovered by this packet so far. Layer B's
raw-local gain duplicates the artifact `ed5b4020…` already on main
(mayhem-control-work-20261027 / mayhem-historical-macro-current-20261027) and must
not be counted again.

## Layer B — allocator compilation context (CONDITIONAL)

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
