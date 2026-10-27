# Helper-crate research patch (not applied to maintained source)

`helper-crate.patch` applies with `git apply -p1` (or `patch -p1`) on top of this branch's
maintained source. It adds a local path crate `programs/pump-amm/token-ext` and moves into it:

- `supported_mint_data` (Token-2022 mint extension policy),
- a native `TransferFee` record with spl-style `calculate_fee(&self, …)` and
  `calculate_pre_fee_amount(&self, …)` (Codex's exact standalone bodies from
  `work/amm-fee-native-next-20261027`),
- `decode_transfer_fees` (TLV decoder).

The program crate keeps `supported_mint` (with its PUMP-mint short circuit), `from_mint`,
`calculate_fee`, `amount_after_fee`, `amount_before_fee` and `harvest_to_mint`; the two fee
wrappers match by value (`match *data { … }`). Error sites stay on transfer_fee.rs
32/49/57/67. The crate needs no dependencies; `Cargo.toml`/`Cargo.lock` gain one path entry.
The workspace recipe materializes it automatically (it is under `programs/pump-amm`).

## Windows recovered on top of this branch

| Window | Bytes | Function |
| --- | ---: | --- |
| 0x73ef0 | 568 | `utils::token::supported_mint` |
| 0xf2d60 | 368 | `token_ext::TransferFee::calculate_fee` |
| 0xf2ed0 | 776 | `token_ext::TransferFee::calculate_pre_fee_amount` |
| 0x74648 | 696 | `utils::transfer_fee::calculate_fee` |
| 0x74b80 | 688 | `utils::transfer_fee::amount_before_fee` |

Native (macOS v1.44): 629 → 634 on top of this branch's 629 native, no losses
(`native/exp12`, `native/exp13`).

**Linux v1.44 recipe:** candidate
`80a95040c4ca7cfeb1c9d99d872fc0f4b43f97f376f2f464e6db89ded297e412` measures **639/785
normalized, 128 raw, 146 unmatched** against this branch's 634/128 (exactly the five windows
above, no normalized or raw loss). Artifacts, hashes and measure output are in
`../linux/helper-crate-on-634/`. None of the frontier's 479 dependency artifacts changed;
the build adds only the new `token_ext` rlib/rmeta.

**Runtime:** all 25 maintained suites pass on that Linux candidate, **17,462 cases,
0 mismatches** (`../linux/helper-crate-on-634/runtime/summary.json`, with receipts for the
create, boost, boost_burn, liquidity, sweep and trade_v2 suites that exercise the moved
mint-policy and transfer-fee paths).

Behavior note: `from_mint` is unchanged in this patch (it still returns before reading the
clock when the decoded mint has no fee record). The exp14 variant that also reorders
`Clock::get()` ahead of that check, as the original binary does, is a residual and is not
included.

## Why a separate crate

- The original `supported_mint` (0x73ef0) reloads the data RefCell borrow flag after calling
  the parser 0xf28b8. With any in-crate callee (private, `pub`, `#[inline(never)]`) LLVM
  infers the parser's memory effects and forwards the flag instead (560 vs 568 bytes).
  Only a cross-crate call reproduces the reload.
- 0xf28b8, 0xf2d60, 0xf2ed0 and 0xf31d8 lie between the program crate's last function and
  anchor_spl's object in the original layout; each is called once from a program-crate
  wrapper and contains no calls (except compiler-rt) and no data references.
- The original fee wrappers copy the 24-byte record and pass a pointer to the copy. A
  cross-crate `&self` method (not `nocapture`) called on a by-value binding reproduces the
  copy and the original frame layout; by-value `self` methods do not (deduced `readonly`
  lets the caller pass the payload pointer), and delegating free functions change the
  callee block layout.

The crate's name and location are a reconstruction choice; the binary carries no strings
for it. Open in this group: 0xf28b8 (parser body), 0xf31d8 (decoder body) and 0x74128
(`from_mint`, early `Ok(None)` store shape); see PROGRESS.md.
