# PumpSwap lane amm-hi (original windows 0x73ef0 … 0xf6eb0)

Review history: an earlier copy of this packet (PR #264) was native-only and shipped no
candidate ELF. This revision rebases the lane's three source changes onto the current AMM
frontier, confirms them with the Linux v1.44 recipe and the maintained runtime suites, and
ships the gzipped stripped and unstripped ELFs, their hashes and the measure.py output.

## Result on the 623 frontier (Linux-confirmed)

Base: `repro/pump_amm/account-context-recovery-20261027`, candidate
`badc94982f2ae20adc2a6be7fd22bba9d900c289de7c3b9e7475847af960ca7d`.
The lane's Linux recipe rebuilds that base byte-for-byte (`linux/control-623`).

| | Normalized | Raw | Unmatched | Matched text bytes |
| --- | ---: | ---: | ---: | ---: |
| Base (623 frontier) | 623 | 128 | 162 | 727,352 |
| This branch (maintained source) | **634** | **128** | **151** | **758,296** |

Final Linux candidate `9d1a23b9ee025470cc60f57622db6812065c4f980819f7631bb6f2ecd1762b29`,
symbols `2d57130d7476568a4dae053a5b86d9740ea8413c89bb0066042ad899d28cb737`
(`linux/g3r-on-623/`, both gzipped; `summary.json` records raw and gzip SHA-256).
Eleven windows gained, none lost (normalized or raw). The maintained source in this
commit is byte-identical to the 48 workspace inputs of that build.

Runtime: all 25 maintained suites pass on that candidate, **17,462 cases, 0 mismatches**
(`linux/g3r-on-623/runtime/summary.json`; receipts for the suites that exercise these
changes are included). boost_burn includes 15 `writable-harvest` cases that execute the
Token-2022 harvest CPI; sweep, trade_v2, accumulator, liquidity, boost and create cover
the other changes.

### Newly matched original windows

| Window | Bytes | Function | Source change |
| --- | ---: | --- | --- |
| 0x74900 | 640 | `utils::transfer_fee::amount_after_fee` | `error!` site on transfer_fee.rs:57 |
| 0x82630 | 5896 | `CreateConfig::try_accounts` | `#[derive(Accounts)]` on create_config.rs:6 |
| 0xd1290 | 7824 | `InitUserVolumeAccumulator::try_accounts` | derive on init_user_volume_accumulator.rs:8 |
| 0xc6530 | 7104 | `SweepFees::try_accounts` | `seeds::program = associated_token::ID` (original stores the ATA id via four `lddw`) |
| 0xe9b90 | 1072 | `__global::sweep_protocol_fee` | `pub mod sweep` (shared handler keeps external linkage) |
| 0xe9fc0 | 1072 | `__global::sweep_creator_fee` | same |
| 0xe8ae8 | 1064 | `__global::buy_v2` | `pub use trade::{execute_buy, execute_buy_exact_quote, execute_sell}` |
| 0xe8f10 | 1064 | `__global::buy_exact_quote_in_v2` | same |
| 0xe9338 | 1064 | `__global::sell_v2` | same |
| 0x74e30 | 1480 | `utils::transfer_fee::harvest_to_mint` | boost harvest through a public helper |
| 0xf6eb0 | 2664 | `anchor_spl::token_2022_extensions::transfer_fee::harvest_withheld_tokens_to_mint` | called by that helper |

Changed files (all `programs/pump-amm/src`, see `source.patch`): `lib.rs`, `sweep.rs`,
`boost_burn.rs`, `utils/transfer_fee.rs`, `instructions/admin/create_config.rs`,
`instructions/token_incentives/init_user_volume_accumulator.rs`. No Accounts field types,
IDL, dependencies or build flags change. Line placement uses ordinary layout (doc comments,
rustfmt-style chains, imports); it adds no code.

Not counted here: the lib.rs:36 IDL windows (0xe0148, 0xe0720, 0xf23f0) that an earlier
revision of this packet recovered are already in the 623 frontier (Codex moved the imports).

## Helper-crate research (not applied to maintained source)

`helper-crate/` holds a separate, self-contained patch on top of this branch that recovers
five more windows in this range by moving Token-2022 helpers into a local path crate:
0x73ef0, 0x74648, 0x74b80, 0xf2d60 and 0xf2ed0. Linux v1.44 candidate
`80a95040c4ca7cfeb1c9d99d872fc0f4b43f97f376f2f464e6db89ded297e412` measures **639/128**
(634 → 639, no losses), and all 25 suites pass (17,462 cases, 0 mismatches); artifacts in
`linux/helper-crate-on-634/`. It is kept as a patch because it adds a crate (a structural
hypothesis whose name and location the binary does not evidence); see
`helper-crate/README.md` for the evidence and negative controls.

## Residual diagnosis for this range

See `PROGRESS.md` ("Residuals") for every window in 0x73ef0 … 0xf6eb0 that this lane worked
but did not close, with the negative controls.

## Reproduce

```sh
# native iteration (macOS v1.44), measure against the original
python3 research/claude-amm-hi-20261027/tools/nbuild.py --src . --tag mytag
# Linux v1.44 frontier recipe (needs the lane copies of the frontier Cargo home/target)
python3 research/claude-amm-hi-20261027/tools/lbuild.py --src . --tag mytag-linux
# measure any candidate
python3 repro/pump_amm/focused-diagnostics-20261026/measure.py --candidate candidate.so \
  --symbols unstripped.so --output measurement.json
# runtime suites (original vs candidate), REPO/work/test-env Python
python3 research/claude-amm-hi-20261027/tools/rsuite.py --candidate candidate.so --output out-dir
```

The tool paths assume this lane's scratch layout (`LANE` constant at the top of each tool);
adjust it to reuse them elsewhere.
