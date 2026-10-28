# Lane pump-lo — main Pump windows 0x340 … 0x65238

Ordinary-source recovery of main-Pump function windows in the low address range. Every claim is
measured with the frontier packet's own normalizer
(`repro/pump/main-contract-round36-20261027/inputs/scripts/pump_compare_function_bytes.py`, via
`tools/measure.py`) against `evidence/original/pump/deployed.so`, and cross-checked with the
integration session's `score.py`. Whole-ELF identity remains false.

## Counts

| build | recipe | normalized | raw | matched text bytes |
|---|---|---|---|---|
| Round37 (`1a4b0664…` unstripped), reproduced byte-for-byte by `tools/r36_build.py` | official Round36/37 recipe (Linux v1.44 SBF libs, text order, data-order certificate) | 744 | 175 | 924,192 |
| **Round37 + p02–p04 + p06** (`9e6eb914…`) — `evidence/r37-g6` (this branch) | same official recipe, 0 stack warnings | **749** | 175 | **930,544** |
| Round36 (`9cc0982e…`), reproduced byte-for-byte | same official recipe | 738 | 145 | 900,520 |
| Round36 + p02–p04 + p06 (`886c7e61…`) — `evidence/r36-g5` | same official recipe, 0 stack warnings | 743 | 145 | 906,872 |
| integration composite i1c (`cf809470…`) | harness `identity` (Linux v1.44 `sbpf-solana-solana` libs) | 778 | 135 | 984,768 |
| **i1c + p06** (`20dd0332…`) — `evidence/i1c-p06` | same `identity` recipe, 0 stack warnings | **779** | 135 | **987,752** |

No normalized window and no raw window is lost in either comparison.

## Newly matched original windows

| window | bytes | original function | change | status |
|---|---|---|---|---|
| **0x2a8e8** | 2984 | `CollectCreatorFeeV2` handler | p06 | **new beyond i1c** |
| 0x340 | 1336 | `anchor_lang::Error::with_values::<(u64,i32)>` | p02 | in i1c (same fix, local named `amount`) |
| 0x8cc58 | 1200 | native lamport `transfer(system_program, &Signer, dest, amount)` | p03 | in i1c (verbatim) |
| 0x3b738 | 416 | 3-arg `ensure_rent_exempt` | p03 | in i1c (verbatim) |
| 0x3b598 | 416 | 4-arg V2 `ensure_rent_exempt(_size, …)` | p04 | in i1c (verbatim) |
| 0x29518 | 472 | AdminCto `token_frozen` | p01 | in Round36 (verbatim) |

### Evidence per fix

* **0x2a8e8 (p06).** The handler's call into the shared creator-fee collector shows the original's
  parameter shapes: `quote_token_program` is passed as the *address* of the `Interface` field
  (`mov r8,r6; add r8,24`) and `system_program` as the already-loaded `&AccountInfo` (`ldxdw [r6+40]`).
  The reconstruction's collector was `pub(crate)`, so LLVM argument-promoted both `&Interface` and
  `&Program`. Exporting `collect` (`pub fn` in the public `collect_v2` module) and declaring
  `system_program: &AccountInfo` (callers pass `a.system_program.as_ref()`) reproduces the call
  setup. Second, the original serializes both the `emit!` log and the `emit_cpi!` payload from a single
  event value (both read the creator key at `[r10-240..-216]`), whereas `emit!(event.clone())` made a
  second 32-byte stack copy; Anchor's `emit!`/`emit_cpi!` take the event by reference, so the original
  form is `emit!(event); emit_cpi!(event);`. Result: all 352 instructions equal. Control `cv1`
  (the two parameter shapes swapped) does not match; `cv2` (interface only) leaves only the event copy.
* **0x29518 (p01).** Original 0x22a10 (AdminCto handler) calls 0x29518 five times; its body equals the
  matched sibling `token_raw_amount` (0x296f0) except for the return `Ok(TokenAccount.state == Frozen)`
  and an internal `data_is_empty → Ok(false)` guard; callers no longer need their own guard.
* **0x340 (p02).** Original 0x340 has `values.0` constant-folded to 0 (all 28 callers are
  `require_gt!(x,0)`/`require_gte!(x,1)` failure paths). One reconstructed caller passed a runtime value
  because `require_gt!` evaluates `input.min(c.real_token_reserves)` twice and the second evaluation
  reloads account data; binding it once restores the fold.
* **0x8cc58 / 0x3b738 (p03).** Neither original helper was argument-promoted (the transfer keeps
  `payer: &Signer`, the rent helper loads `Program.info` itself), i.e. they are exported items; the V2
  helper calls the single shared transfer (the original has one transfer body with three callers).
* **0x3b598 (p04).** Byte-identical to 0x3b738 except for one leading argument that the body never
  reads (`minimum_balance(0)`); all three original callers pass 0 in r2, as the V2 callers pass `size = 0`.

## Changed files (vs Round37 maintained source on this branch)

`programs/pump/src/buy.rs`, `programs/pump/src/legacy_native_payments.rs`,
`programs/pump/src/v2_native_payments.rs`, `programs/pump/src/creator/collect_creator_fee.rs`,
`programs/pump/src/creator/admin_cto.rs` (call site of the collector only; p01 is already in Round36/37).
Full copies in `changed/`, unified diff in `source.patch`, and idempotent re-applicable scripts in
`patches/p01…p06` (each asserts its anchors; `p05` is not used — see negative controls). For the
integration composite, `evidence/i1c-p06/patch-vs-i1c.diff` is the only delta (p06).

## Builds and artifacts

* `evidence/r37-g6/`: the same official recipe on Round37 + patches (this branch's source); the
  wrapper again reproduces the published Round37 hashes (`r37base` lines in `SHA256SUMS`).
* `evidence/r36-g5/`: official Round36 recipe (`tools/r36_build.py`: ordinary cache build, identity
  build with `identity-text.ld`, fresh data-order certificate, final build with `text-order.ld` and the
  certificate, Linux v1.44 SBF target-library profile). The same wrapper reproduces Round36's published
  hashes from its archived primary (`r36base` lines in `SHA256SUMS`).
* `evidence/i1c-p06/`: integration harness `fastbuild.py` (identity recipe) on the i1c source + p06;
  `runtime_valid: true`, zero "exceeded max offset" stack warnings (also zero in the Round36 builds).
* `evidence/r25-g3/`: the first measurement of p01–p04 on Round25 (725/123), two identical builds.

All `candidate.so`/`unstripped.so` are included gzipped with sha256 lists, so the claims can be
re-measured without rebuilding.

## Runtime differential (original vs candidate, captured upgradeable loader)

`evidence/r37-g6/differential/SUMMARY.json` (Round37 official-recipe candidate: 20 suites / 4,136 cases,
0 mismatches; diagnostic audit 4,134 log-bearing cases, 0 mismatches),
`evidence/r36-g5/differential/SUMMARY.json` (Round36 official-recipe candidate: 18 suites / 3,657 cases,
0 mismatches; diagnostic audit 3,655 log-bearing cases, 0 mismatches) and
`evidence/r25-g3/differential/SUMMARY.json` (Round25 candidate, 17 suites / 3,503 cases, 0 mismatches,
3,501 log-bearing cases with 0 diagnostic mismatches). `tools/run_suites.py` mirrors
`scripts/pump_validate_parallel.py`'s per-suite invocation, expected counts and loader checks, and adds
the repository's `pump_diagnostic_audit`.

## Residual diagnosis for windows worked but not closed

* **0x49708 / 0x56658 (384 B, Migrate/MigrateV2 pool-authority refund).** Only the signer-seed frame
  layout differs: the original allocates the outer seed slice, the inner seed array, then the mint-key
  copy and the bump (MIR order), and loads `system_program` after building the seeds. Building the seeds
  inline in the call fixes the frame (`p05`) but moves the `system_program` load first; a `let` with
  `a.mint.key().as_ref()` does not borrow-check (E0716); `&a.mint.key().to_bytes()` fixes frame and load
  order but copies the key with four loads then four stores instead of the original's paired memcpy.
* **0x3a7b8 `set_metaplex_creator` handler (3552 B), 418/419 instructions.** With the event emitted by
  reference (`emit!(e); emit_cpi!(e);`, as for 0x2a8e8) the body has the original length and every
  instruction but one: in the `emit_cpi!` invoke-failure path the original reloads the spilled
  data-`Rc` pointer (`ldxdw r3,[r10-88]`) before the error-value loads, the candidate two slots later.
  Not caused by the `ctx.accounts` alias (control `sync2`). Not adopted until exact.
* **0x3cd50 `prepare_bonding_curve` (1280 B).** The original tests the funding Result tag before
  `current_size > 165`, re-materializes tag 2 and returns the funding value on both skip edges (payload
  register flows through, single exit). Controls: preserve-result (size-first), `and_then`, `match`,
  `is_err()` early return, `if let Err`, `?` (tag-first, but payload load sunk into a split edge and
  1288 B), named-local `?`, `||` guard, nested `if`, swapped `&&` operands.
* **Coordinate-bound windows** (68 of the original 111 in range): bodies embed original `error!` Source
  file-length and line immediates (`buy_v2.rs:995`, `multi_hop_curve_swap.rs:744`, …). Not padded here.

## Reproduce

```sh
# stdlib-only check of every archived ELF and its measurement (works with an empty HOME)
HOME=$(mktemp -d) python3 -B research/claude-pump-lo-20261027/verify.py
# official Round36 recipe on this branch's maintained source (needs the Linux v1.44 SBF libraries)
python3 research/claude-pump-lo-20261027/tools/r36_build.py --prepare-cache --root . \
  --packet repro/pump/main-contract-round37-20261027 --source-directory programs/pump \
  --output work/pump-lo-g5 --dependency-cache work/pump-lo-depcache \
  --target-library-directory ~/.cache/solana/v1.44-linux-probe/platform-tools/rust/lib/rustlib/sbf-solana-solana/lib
python3 research/claude-pump-lo-20261027/tools/measure.py . repro/pump/main-contract-round37-20261027 work/pump-lo-g5/unstripped.so
# re-measure archived artifacts without building
gzip -dc research/claude-pump-lo-20261027/evidence/r37-g6/unstripped.so.gz > /tmp/g6.so
python3 research/claude-pump-lo-20261027/tools/measure.py . repro/pump/main-contract-round37-20261027 /tmp/g6.so
# apply to another round's / composite's maintained source
for p in research/claude-pump-lo-20261027/patches/p0[1-46]*.py; do python3 $p <crate-dir>; done
```
