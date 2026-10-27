# Main Pump — lane pump-hi (original windows 0x101170 … 0x1ab9b8)

Isolated, ordinary-source recovery for the upper third of the main Pump program. **Whole-ELF identity remains false.**
Every claimed result ships its stripped and unstripped ELFs (gzipped), SHA-256 values and the full score output under
`evidence/elf/<name>/`, so the claims can be recomputed. This packet does not edit `programs/pump`, because the CI
guard pins it to the frontier package. The changed files ship under `source/`, `source.patch` is a `git apply`-able
diff against the frontier's `programs/pump`, and `tools/apply_lane_changes.py` applies every change idempotently
(content-addressed) to later rounds.

## Current result: Round36 (see `RESULT.json`, `PROGRESS.md`)

| build (same plain archived builder for all rows) | normalized | raw | matched text bytes |
|---|---:|---:|---:|
| Round36 primary, unmodified (`evidence/elf/r36-base`) | 738 | 126 | 900,520 |
| + changes 3, 5, 6 (`evidence/elf/r36-noncpi`) | 743 | 126 | 908,888 |
| + change 7 incl. migrate_v2 (`evidence/elf/r36-762-cpi`, **runtime-invalid**) | 762 | 126 | 964,776 |
| **H7**: + change 7 without migrate_v2, collect form, change 8 (`evidence/elf/r36-764-cpi4`) | **764** | 126 | **972,072** |

H7 passes the full public 44-suite corpus: 10,468/10,468 cases, 0 errors, 0 diagnostic mismatches
(`evidence/runtime-full-r36-cpi4.json`). Its build log has no `Stack offset … exceeded` warning.

On the Pump integration composite **i1c** (778/135, shared `fastbuild.py` identity recipe), change 8 adds `0x1176e0`, for
779/135/987,968 with 0 losses and 0 stack warnings (`source-on-i1c.patch`, `evidence/elf/i1c-779-fee8`). i1c already
contains changes 1–7 from `e09aab510` and the `0x10b0b8` form.

**The 762 build is runtime-invalid.** Change 7 had put the generated `create_pool`/`init_boost` clients into
`migrate_v2::execute`. The build log warns `Stack offset of 4104 exceeded max offset of 4096`, and 482 of 827
`pump_migrate_v2_differential` cases fail with `Access violation in stack frame 5`. Change 7 no longer touches
`migrate_v2.rs`; the entries are kept under `rejected_not_applied` in `tools/cpi_changes.json`, with the evidence in
`evidence/runtime-r36-lane-migrate_v2-rejection.json`. Every build log is now checked for that warning, and it blocks adoption.

There are no normalized or raw losses against the same-recipe base. The published Round36 inventory reports 145 raw
because Round36 links with its derived text/data layout (`ordered.ld`, data-order certificate, Linux target-library
profile). Built with the plain archived builder, the unmodified Round36 source loses the same 19 raw windows. So
integration must re-derive the layout with the added functions; the source changes cause no loss.

## Lane changes (tools/apply_lane_changes.py)

| # | windows | change | status |
|---|---|---|---|
| 1 | 0x11b758 dispatcher | `#[program]` handlers in the original discriminator order | in Round36 |
| 2 | 0x1348c0 | `update_global_authority`: by-value handler fn, authority stored first | in Round36 |
| 3 | 0x12a4e0, 0x12abc8 | legacy buy `execute<const EXACT: bool>`: each wrapper calls its own 5-argument specialization | re-applied |
| 4 | 0x19e3b0 | Anchor `system_program::transfer_with_seed` in admin_set_idl_authority | in Round36, equivalent form |
| 5 | 0x1255a8, 0xcf510 | `SetMayhemVirtualParams`: Global unboxed, `sol_vault_authority` owned `AccountInfo` (1,728-byte accounts value) | re-applied |
| 6 | 0x137fc0 | crate-private `execute` inlined into the `#[program]` fn, curve snapshot first, sync arguments direct, `Copy` event | re-applied |
| 7 (`--with-cpi-7`) | 0x10a0e0, 0x10c0b8, 0x10d638, 0x10e938, 0x10fb38, 0x1100f8, 0x110d40, 0x1113c8, 0x112220, 0x1133c8, 0x113f00, 0x114d48, 0x116718, 0x118360, 0x119c50 + helpers 0x163ea8, 0xca628, 0xea68, 0xf130 | `declare_program!(pump_amm)` / `declare_program!(pump_fees)` from the official upstream IDLs (`evidence/upstream`, pump-public-docs `639b87f`; instruction and account discriminators equal the original's), calling the generated clients for create_pool, init_boost, admin_cto_pool, collect_coin_creator_fee, transfer_creator_fees_to_pump_v2 and admin_cto_sharing_config. Spec: `tools/cpi_changes.json`. `collect_coin_creator_fee` builds its accounts inside `if !frozen`, which gains 0x10b0b8. | re-applied, **except `migrate_v2.rs` (rejected: stack overflow, see above)** |
| 8 (`--with-fee-8`) | 0x1176e0 | `pub mod fee_cpi` (stops interprocedural constant propagation of `is_pump_pool`), and account metas computed before the `Instruction` literal, as in Anchor's generated template | H7: +0x1176e0, full corpus passes; +0x1176e0 on i1c |

Behavior is unchanged by construction:
- CPIs keep the same instruction data, account metas, signer seeds and program id (`Program<..>` accounts enforce the ids);
- the buy specializations constant-fold the same code;
- account types keep the same constraints.

The six-change candidate on Round26 and the H7 candidate on Round36 pass the full public 44-suite captured-loader corpus (`RUNTIME.md`). The Round36 762 candidate failed in `migrate_v2` (see above).

## History

| result | base | normalized / raw | commit | ELFs |
|---|---|---|---|---|
| H1 (1, 2) | Round23 | 714 / 123 | `9e2c319bc` (merged `e16ab0756`) | `evidence/elf/r23-714` |
| H3 (1–5) | Round25 | 727 / 125 | `9c4f06050` | `evidence/elf/r25-727` |
| H4 (1–6) | Round26 | 729 / 125, full corpus passes | `475675bf5` | `evidence/elf/r26-729` |
| H5 (1–7) | Round26 | 748 / 125 | `475675bf5` | `evidence/elf/r26-748-cpi` |
| H6 (3, 5–7) | Round36 | 762 / 126, **runtime-invalid** (migrate_v2 stack overflow) | `cbccc4358`, `561969f45`, rejected in `e09aab510` | `evidence/elf/r36-762-cpi` |
| H7 (3, 5–8, collect form) | Round36 / i1c | 764 / 126, full corpus passes; 779 / 135 on i1c | see `PROGRESS.md` | `evidence/elf/r36-764-cpi4`, `evidence/elf/i1c-779-fee8` |

## Remaining windows in this lane's target list (Round36)

| window | diagnosis |
|---|---|
| `0x109488` GlobalConfig body | Reached only through the original migrate helper `0x524f0`: `try_borrow_data`, then generated `GlobalConfig::try_deserialize`, then a config flag gating `init_boost`. The candidate gates on `!mayhem` only, so this is a migration behavior recovery. |
| `0x1557e8` admin_set_idl_authority handler | Holds the account by reference, compares with `system_program.key()`, requires `owner == ID`, reallocs, requires `data_len >= 8`, checks the discriminator, with three Source sites (72/79/90). A rewrite in that form did not yet match. |
| `0x1367c0` set_params handler | Uses helper `0x3e550` and `lib.rs` Source sites. |
| `0x138b20`, `0x13b9b8`, `0x13f630`, `0x144508`, `0x147ba0`, `0x1489f8`, `0x14a8a8`, `0x14c038`, `0x14f4e0`, `0x152888` | Create, V2 and V3 trade, and legacy buy/sell handler bodies (active Codex areas). The legacy buy handlers `0x14c038`/`0x14f4e0` are the two specializations behind change 3. |
| `0x17bc48`, `0x17c0f0` | Token-2022 TLV readers from the original `util/transfer_fee.rs`. |

## Reproduce

```sh
python research/claude-pump-hi-20261027/reproduce.py --registry-home ~/.cargo --output work/pump-hi-reproduce
python research/claude-pump-hi-20261027/tools/apply_lane_changes.py --source-directory <crate> --with-cpi-7 [--with-fee-8]
```
