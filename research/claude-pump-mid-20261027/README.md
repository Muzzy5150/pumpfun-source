# Main Pump lane `pump-mid`: CurveHop operand order and Mayhem context layout

This packet measures two small source patches on top of the verified
[Round26](../../repro/pump/main-contract-round26-20261027/README.md) main-Pump source (`0212e1d54`).
The lane covers original windows with `original_start` 0x65eb0 … 0xfdf20.

Composed on Round26, the patches match **724 / 1,035 normalized windows**, up from 721.
They keep all **123 raw byte-equal bodies**, and raise matched text from 874,352 to **879,784 bytes**.
No normalized or raw window is lost. Whole-ELF identity remains false.

| | Round26 | Round26 + patches 02, 03 |
| --- | ---: | ---: |
| Normalized windows | 721 | **724** |
| Raw byte-equal windows | 123 | 123 |
| Unmatched windows | 314 | 311 |
| Unmatched windows in this lane's address range | 118 | 116 |
| Matched original text bytes | 874,352 | 879,784 |

Counts are given by both tools, which agree:
- the shared exact scorer (`score.py`, a replica of Codex `inventory_current.py`; output in `builds/*/score.json.gz`);
- this lane's `tools/measure.py` (`builds/*/measure.json.gz`).

`measure.py` also reproduces the published Round20, Round21, Round23, Round24 and Round25 counts on reproduced builds of those rounds. Earlier lane results: 723/123 on Round25, 717/123 on Round23 (with the reference patch 01).

## Newly matched original windows

| Window | Bytes | Function | Patch | Cause of the former mismatch |
| --- | ---: | --- | --- | --- |
| 0xdd700 | 3,512 | `CurveHop::try_accounts` | 02 | Operand order of the first `Pubkey ==` in the quote-mint constraint (memcmp argument order) |
| 0xcf510 | 576 | `SetMayhemVirtualParams::exit` | 03 | Context layout: `global` unboxed, `sol_vault_authority` held as `AccountInfo` (bonding curve at +0x1e8, not +0x1b8) |
| 0x1255a8 | 1,344 | `__global::set_mayhem_virtual_params` wrapper | 03 | Same context layout (outside this lane's range; reported for dedupe) |

0xdd700 and 0xcf510 are also in the integration session's `nearmiss` claim, and 0x1255a8 lies outside this lane. They are reported for dedupe at integration.

## Source changes

Each patch is a small diff against the maintained `programs/pump/src`. Both were applied and measured on Round21 (patch 02 before the Round22 `multi_hop_curve.rs` rename), Round23, Round24, Round25 and Round26.

- **`patches/02-curvehop-operand-order.patch`** (`src/multi_hop_curve_swap.rs`) changes one expression in the `CurveHop` constraint.
  - `bonding_curve.quote_mint==quote_mint.key()` becomes `quote_mint.key()==bonding_curve.quote_mint`. The boolean result is unchanged.
- **`patches/03-mayhem-context-layout.patch`** (`src/mayhem_virtual_params.rs`) changes three field types in `SetMayhemVirtualParams`:
  - `sol_vault_authority: AccountInfo<'info>` (was `UncheckedAccount`);
  - `global: Account<'info, Global>` (was boxed);
  - `token_program: Program<'info, Token2022>`, which replaces `Interface<TokenInterface>` plus `address = token_2022::ID`.

  The binary supports each change:
  - The original try_accounts begins by cloning an `AccountInfo`.
  - It copies the 1,071-byte `Global` into the context with two `memcpy 0x42f`.
  - Its output-struct stores show three 48-byte `AccountInfo` blobs.
  - It has no `token_program` constraint failure. The published IDL gives `token_program` a fixed address, which matches `Program<Token2022>`.
  - The candidate's try_accounts output-store offsets now equal the original's.

`patches/coordinate-only-reference/01-derive-origins.patch` is kept for reference only.
It closes the coordinate-only windows 0xdf2d8 and 0xfdf20, using the derive line and the original `token_incentives/init_user_volume_accumulator.rs` path.
Those windows belong to the integration session's coordinate repositioning, so this patch is **not** part of the lane candidate.
Measured on Round24 it gave 725/123 with no losses.

`CANDIDATE.json` gives each changed file's Round26 base hash and new hash. Full changed files are in `source/programs/pump/src/…`.

## Builds and artifacts

| Build | Stripped SHA-256 | Unstripped SHA-256 |
| --- | --- | --- |
| Round25 control (maintained source, earlier base) | `ef31dfd3…02ab` (= published) | `d36b2984…3ea9` (= published) |
| Lane build 1 (Round26 base) | `b120fa20eea758a3ac82c0898ff4e4abe37ad549b28dd87c964d40bcd653e148` | `dfe2e5d6ca1d1b4709d683e3780733bd7d48d8a077b99fccc86d567e74d8442b` |
| `reproduce.py` (Round26 primary + packet sources) | identical | identical |

`artifacts/` holds `candidate.so.gz`, `unstripped.so.gz` and `SHA256SUMS`, so reviewers can re-measure without rebuilding.
`builds/*/` holds build-comparison, build-attempt, the gzipped log, measure and score outputs.
All builds use the unchanged `scripts/pump_build_verified.py --workspace-layout` with a verified external-only dependency cache. Main Rust is always compiled anew.

## Runtime differential (original vs candidate, captured upgradeable loader)

`runtime/SUMMARY.json`: 352 signed cases, all accepted. The diagnostic audit pairs 352 / 352 log-bearing cases with 0 mismatches.

| Suite | Cases | Exercises |
| --- | ---: | --- |
| virtual_reserve_sync | 192 | SetMayhemVirtualParams through Mayhem CPI |
| set_mayhem_virtual_params | 84 | SetMayhemVirtualParams account/constraint boundaries |
| multi_hop_curve_partial | 56 | CurveHop parsing in multi-hop routes |
| tokenkeg_two_curve | 20 | CurveHop parsing in multi-hop routes |

The same patches also passed on Round23, with patch 01 included: 1,266 cases across seven suites (adding quote_control, volume and volume_sync), with 0 mismatches.
`scripts/pump_set_mayhem_params_synthetic_cpi.py` fails in fixture setup for the original program as well, so it is not counted.

## Residual diagnosis for windows worked but not closed

- **0xcd3d8 `SetMayhemVirtualParams::try_accounts`** (8,504 bytes; body-rest): after patch 03 the candidate is 8,472 bytes, with identical output layout and field order.
  - With frame offsets masked, only the `associated_token` constraint of `mayhem_token_vault` differs.
  - The original loads `token_program.key()` once and keeps a 32-byte stack copy, which it reuses for `get_associated_token_address_with_program_id`. The candidate re-reads it through the pointer, giving +32 bytes of frame and 4 instructions.
  - `Program<Token2022>` and `Interface<TokenInterface>` (no address constraint) compile identically here.
- **0xa23f0 `BondingCurve::sync_virtual_quote_reserves`** (nearmiss): one load-order swap in the multiplication-overflow error block.
  - `ok_or_else` and an explicit `match … return Err(….into())` produce the identical binary.
  - Swapping the operands changes bytes but adds no match.

## Negative controls

| Variant | Result |
| --- | --- |
| Mayhem context: `AccountInfo` for both `sol_vault_authority` and `token_program`, `global` unboxed | 0 gains (layout wrong) |
| Mayhem context: `token_program: AccountInfo`, `sol_vault_authority` unchanged, `global` unboxed | +2; try_accounts 8,576 bytes; prologue differs |
| Mayhem context: patch 03 with `Interface<TokenInterface>` instead of `Program<Token2022>` | identical try_accounts; +2 |
| Mayhem context: patch 03 but keep `address = token_2022::ID` | +2; try_accounts 8,952 bytes |
| `sync_virtual_quote_reserves` multiplication with `ok_or_else` / explicit `match` | identical binary |
| `sync_virtual_quote_reserves` multiplication operands swapped | different binary, no gain |

## Verify without rebuilding

```sh
HOME=$(mktemp -d) python3 -B research/claude-pump-mid-20261027/verify.py
```

`verify.py` uses only the standard library. It checks `artifacts/SHA256SUMS`, `CANDIDATE.json` and the shipped source files.
It then recomputes the window counts of `artifacts/unstripped.so.gz` against `evidence/original/pump/deployed.so`, using the ELF's own `.symtab` and the repository normalizer.
The result must equal `CLAIM.json`: 724 normalized / 123 raw on Round26, gaining 0xcf510, 0xdd700 and 0x1255a8, with no normalized or raw loss.

## Reproduce

```sh
python3 research/claude-pump-mid-20261027/reproduce.py --registry-home ~/.cargo \
  [--dependency-cache <verified external cache>] --output work/claude-pump-mid-reproduce
python3 research/claude-pump-mid-20261027/tools/measure.py work/claude-pump-mid-reproduce/unstripped.so \
  --base repro/pump/main-contract-round26-20261027/inventory.json.gz
<test-env python> research/claude-pump-mid-20261027/tools/runsuites.py \
  --candidate work/claude-pump-mid-reproduce/candidate.so \
  --source-directory work/claude-pump-mid-reproduce/source/programs/pump --out <dir> \
  virtual_reserve_sync set_mayhem_virtual_params=pump_set_mayhem_virtual_params_differential.py \
  multi_hop_curve_partial tokenkeg_two_curve
```

`reproduce.py` checks every Round26 primary hash and each replaced file's base hash, then asserts both recorded ELF hashes.
The suites need the sparse paths `research/imported-lab/analysis/pump_fun`, `repro/pump/native-curve-partial-fortyeight/harness` and `repro/pump/tokenkeg-two-curve-fortyeight/harness`.
`tools/` also holds the triage helpers used here: `triage.py`, `lineonly.py`, `wdiff.py`, `fdiff.py`, `origins.py` and `strs.py`.
