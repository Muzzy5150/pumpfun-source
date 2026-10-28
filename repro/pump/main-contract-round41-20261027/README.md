# Main Pump verified checkpoint — Round41

The maintained main contract matches **817 / 1,035 original function windows (78.9%)**, including **203 raw byte-equal bodies**. Those windows cover **1,085,456 / 1,792,208 original text bytes (60.6%)**. The closed direct-call subset contains 151 windows and excludes data references. Normalization masks specified call/address operands; it does not establish referenced data or whole-program identity. **Whole-ELF identity remains false.** These metrics measure binary coverage, not engineering work completed.

The captured-loader regression passes **44 suites / 10,468 cases** and **161 focused suites / 7,642 executions**, with **18,106 matching paired diagnostic-log cases**. These corpora overlap. Paired diagnostics compare structured Anchor errors, panic payloads and comparison operands, excluding source coordinates and compute usage. The separate ordered raw-log audit covers every complete recorded main invocation and requires zero non-filename differences, retaining nested CPI, event and return logs. It reports 651 remaining source-filename mismatches explicitly. Every original/candidate result retains its serialized transaction bytes; signatures and main-instruction attribution are rechecked. The complete corpus contains 18,110 paired executions. No current-chain acceptance is implied.

This round restores observed ordinary messages and ordering and corrects the ClaimCashbackV2 quote-program guard. Raw-log coverage remains bounded by the recorded inputs; source filenames are not silently normalized away.

This round adds exactly 1 distinct cashback quote-program guard input and retains all 18,109 paired cases from Round40, including its signed nonzero-volume SellV3 witness. The earlier reversed stored-range scheduler case remains parser-admitted; its historical reachability is still unproved. The strengthened 308-case extension suite remains unchanged.

The selected compiler profile restores the five original TypeId bodies. Selected source changes are listed below and retain the earlier TradeEvent and scheduler corrections. Generated external-program interfaces remain compiler inputs for the main contract. All previously validated R38 corrections are retained. Source, runtime, layout and provenance claims retain their distinct evidence boundaries. The selected primary files are bound by the frozen integration plan:

- `src/creator/admin_cto.rs`
- `src/creator/distribute_creator_fee_v2.rs`
- `src/creator/set_creator.rs`
- `src/creator/set_metaplex_creator.rs`
- `src/curve_quote_payments.rs`
- `src/distribution.rs`
- `src/lib.rs`
- `src/set_creator.rs`
- `src/set_reserved_fee_recipients.rs`
- `src/sweep_fees.rs`
- `src/token_incentives/claim_token_incentives.rs`
- `src/volume_sync.rs`

Actual window changes against Round40 are +1 normalized and +1 raw. The entire previously matched normalized-window set is retained. This description is generated from final evidence and does not infer source correctness from a count gain.

The source-specific pure text recipe is preserved as `text-order.ld`. The final compiler recipe `ordered.ld` includes the bounded two-object `.data.rel.ro` ordering. The fixed Borsh Location and debug-argument table have 0/2 original-relative starts before and 2/2 after the selected data order. These are only the two checked objects, not a whole-data-layout metric. The proof independently finds their original owner bodies and LDDW references, verifies Location/table fields and methods, and accounts for every text/data byte, pointer, relocation, symbol and remaining file byte. There is no post-link editing, padding, or injected original code/data. The concrete original table type, complete allocation extents, remaining data layout remain unresolved. The five tracked TypeId constants now match; the complete original SDK and host recipe remain unproved.

The opt-in `linux-v1.44-sbpf` profile uses the pinned native macOS v1.44 compiler/host libraries with exactly25 SBPF target libraries from the official Linux x86_64 v1.44 archive. Per-build inventories prove that only that target-library directory changed. This is a reproducible hybrid recipe, not proof of the original SDK. Its separate external-only cache has an ordinary clean producer, fresh cached parity and producer-unavailable controls. Every main crate is compiled again; no compiled main-Pump object enters that cache.

Four final compilations reproduce both ELF hashes: initial, repeat, maintained-source and archived-source builds. Two separate identity compilations support the initial and archived data-order certificates. Archive reproduction actually builds a fresh identity from archived primary, derives a new certificate with pure `text-order.ld`, then compiles a fresh final and requires both expected ELF hashes. The original admitted certificate is preserved unchanged as provenance. The read-only verifier uses explicit bundled artifact paths; its local transformation replay is not represented as fresh admission.

```sh
python repro/pump/main-contract-round41-20261027/verify.py
python repro/pump/main-contract-round41-20261027/reproduce.py \
  --registry-home /path/to/qualified/cargo-home \
  --dependency-cache /path/to/qualified/external-cache \
  --sdk /path/to/native-macos-v1.44 \
  --target-library-directory /path/to/linux-v1.44/rust/lib/rustlib/sbpf-solana-solana/lib \
  --output work/reproduce-main-round41
```

The reproduction creates separate sibling identity and certificate paths; `--output` remains the final build directory. The native SDK and official target libraries are external, hash-bound inputs, not bundled or downloaded by the archive. A changed cache/profile context needs its own ordinary producer and parity proof. The original executable is used for evidence/comparison only, never as compiler or linker code/data input.

[Previous maintained checkpoint: Round40](../main-contract-round40-20261027/README.md). The remaining 218 function windows, validation paths, data, relocations and original build provenance remain open. [Parallel work queue](../../../research/main-pump-parallel-checkpoint-20261027/REMAINING-WORK.json).
