# w17a35: CP111 wallet / sweep re-pricing

Target: Pump Main `admin_cto::execute`, original `0x22a10`, 27,400 bytes.
Base: `0881307b0f678a1116aa5322d53f1dd098a64589` (CP111).

This lane reprices retained wallet-collection and creator-fee sweep hypotheses after the CP111 frame-layout change.
It uses real maintained identity builds and the official scorer. No candidate qualified; the source was restored to
the exact base and no upstream PR was opened.

## Fresh baseline

- source-tree digest: `aa3b28c9ad21b697d8445860a754815f323419becb612a7d61cd674af349681e`
- unstripped ELF: `e250a17fc9aad05618f6300605c82263f5570c06e576c96fa5732e68942bdfa5`
- stripped ELF: `f090fdc8d137210d7a55ece039545e65d2a5e0e82654e1a4ef68c502b174f79f`
- `admin_cto::execute`: 27,400 bytes, 3,339 instruction tokens, 2,322 matched tokens, ratio `0.69542`, 3,224
  positional differing slots, 154 internal calls and 3 syscall-or-relocated calls
- whole program: 1,034 normalized and 1,034 raw windows, of 1,035; no stack warnings
- identity rustc SHA-256: `1f26338cc2cabd0a6057dcbd0528bba262b23ca1296d357a55304ee31d1d9e5a`
- linker SHA-256: `a4d765c822f68b267e87765771da87a0fd4d640d9df27884bd10c0750d1b58f4`
- ordered linker script SHA-256: `6954d9901b005312be6e7f980cb5e74a1440c174547c2040a881acf2e5c25b45`

The local receipt root is
`/Users/muzzy5150/admin-cto-wallet-sweep-evidence-20261101`. It contains the baseline build, official score,
target metric, residual analysis, stack-access report, register/stack provenance report, event maps, and every trial
build with source-input and link receipts.

## Machine observations

The event maps make the source regions identifiable without guessing from source line numbers:

- wallet eligibility reaches `memcmp` at relative `0x1cc8` in the original and `0x1c58` in CP111;
- the PumpSwap fee-transfer CPI is at `0x3b70` original versus `0x3b28` candidate;
- the Pump Fees sharing CPI is at `0x4a78` original versus `0x49f0` candidate;
- wallet collection starts at `0x4be8` original versus `0x4b80` candidate;
- the late wallet/sweep CPI runs reconverge: `collect_creator_fee::collect` is `0x61d8` in both and
  `collect_coin_creator_fee` is `0x6a20` in both.

The original token sweep calls `token_raw_amount` before `token_frozen` (`0x20c8`, `0x2110`); CP111 calls them in
the opposite order (`0x2068`, `0x20c0`). That ordering was already measured as the historical `a1` size knob. It was
not repeated alone because its retained current-family measurement is off-size and does not satisfy raw-window
preservation.

Fresh residual analysis reports 3,339 instructions on both sides, 378 original versus 380 candidate reachable
blocks, 303 matched blocks, 62 ambiguous matches, and 75/77 unmatched original/candidate blocks. Stack/register
provenance reports 1,473 versus 1,424 proven stack accesses and 39 versus 29 suspected spill/reload sites. These are
machine observations, not recovered-source claims.

## Real-build trials

`M` is the exact sum of `SequenceMatcher` matching blocks over normalized instruction tokens. Unequal-size trials
cannot preserve raw windows because later function addresses move; they are diagnostic only.

| trial | source mechanism | bytes | M | ratio | calls | outcome |
| --- | --- | ---: | ---: | ---: | --- | --- |
| 01 | passthrough on sweep program-clone `is_writable` | 27,408 | 2,296 | 0.68753 | 154/3 | rejected; historical IR cell does not survive CP111 |
| 02 | move wallet owner materialization to executable flag | 27,376 | **2,323** | **0.69603** | 154/3 | off-size lead; raw losses, not admissible |
| 03 | trial 02 plus sequential token-sweep `?` propagation | 27,432 | 1,789 | 0.53547 | 154/3 | rejected; non-compositional collapse |
| 04 | raw-byte executable comparison materialization | 27,392 | 1,763 | 0.52808 | 154/3 | rejected |
| 05 | trial 02 plus `collection_native == false` | 27,384 | 2,320 | 0.69503 | 154/3 | rejected; loses three tokens from trial 02 |
| 06 | move wallet owner pin to sweep native-route compare | 27,432 | 2,194 | 0.65669 | 154/3 | rejected |
| 07 | peel sweep program-clone owner volatile load | 27,400 | 2,322 | 0.69542 | 154/3 | neutral; 3,224 slots, zero raw/normalized losses |
| 08 | trial 07 plus natural `key, owner` field order | 27,400 | 2,322 | 0.69542 | 154/3 | neutral; 3,224 slots, zero raw/normalized losses |
| 09 | move wallet owner pin to frozen-vault amount guard | 27,408 | 2,317 | 0.69382 | 154/3 | rejected |
| 10 | reallocate both wallet pins to shared/sweep guards | 27,232 | 2,175 | 0.65345 | 154/3 | rejected; source effects are not size-additive |

Every build was serialized through one fastbuild work directory. Disk remained above 49 GiB. No generated machine
code, normalization rule, linker input, captured artifact, or runtime behavior was patched.

## Conclusion

The best current-main signal is trial 02: one additional matched token, but 24 bytes short. Its raw-window losses
make it unqualified, and every evidence-backed size repayment tested either loses the token or destabilizes the
function. Trials 07 and 08 prove that the old sweep owner pin and its first two field-order choices now sit on a
strict metric plateau; neither is useful as an upstream change.

Do not resubmit these variants without a new upstream/codegen composition. A future lane should start from the
trial-02 source identity and search for a genuinely semantic, exact `+24`-byte mechanism using a fresh current-main
build—not artificial padding and not the rejected sequential-`?` or native-route pins above.
