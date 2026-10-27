# pump-hi progress log

Lane: main Pump original windows `0x101170 … 0x1ab9b8`. The branch is `claude/pump-hi-20261027`. Work happens in the
lane worktree; `work/` is gitignored scratch for builds.

## Harvest entries (verified gains)

Each entry gives:
- the base round;
- the lane commit holding the source (when filled in after commit);
- the unstripped `.so` SHA-256, with the stripped hash beside it;
- gained and lost windows (hex starts).

ELFs, SHA-256 and score output are under `evidence/elf/<name>/`.

| # | base round | lane commit | unstripped sha256 (stripped) | normalized / raw / bytes | gained | lost |
|---|---|---|---|---|---|---|
| H1 | Round23 | `9e2c319bc`, merged as `e16ab0756` | `5b65eade056826eed16c14e356a4a13be53d9fbe52349e790f04cfc0f0282ca9` (`07f3f871ed8027c8b10f9c9c77369e565af72dc974814924c18b76059fc249bd`) | 714 / 123 / 864,904 | 0x11b758, 0x1348c0 | none |
| H2 | Round23 | superseded by H3 (not committed separately) | `ccea809baa4dbb26e3da71e660adaae8c51fe4c12a81e6ee32ba9d7fa862ea19` (`b69f014a4d8d3f5a0686df194a5519caebeea2c82503fc36b9f6defe369e55c7`) | 716 / 123 / 868,440 | 0x11b758, 0x1348c0, 0x12a4e0, 0x12abc8 | none |
| H3 | **Round25** | `9c4f06050119d4e8bb90c4caf82bd3e0d986facd` | `3f9b38145fc777c88ec291a8e25a2687193af05d422ad419a156fda505d23ca3` (`8a45886afb3003205f16b0b085d377dc64f6c478ee6f40cb91be4b815dfaf843`) | **727 / 125 / 890,304** | 0x11b758, 0x1348c0, 0x12a4e0, 0x12abc8, 0x19e3b0, 0x1255a8†, 0xcf510† | none |

| H4 | Round26 | see the commit that adds this row | `7854036b36e9f9eec1d5bd8791fb832ab6568ad4f3ae683a86753241171490df` (`4cbe303da77b6a4cbdc24302f24b038b86a568fc9568dcd09d4d8621416046e3`) | 729 / 125 / 895,576 | H3 set + 0x137fc0 (set_mayhem_virtual_params handler) | none |
| H5 | Round26 | same commit (measured; corpus pending) | `c578b83e1684826e37e8a5d74a6d2058ad9e597d56ab4504e7c31d06e45c6c57` (`20961029e5e7fa78b0ea9863d85c52bd3bfc9b8599f34b1977ff6834cdca8a1b`) | **748 / 125 / 951,464** | H4 set + generated CPI clients 0x10a0e0, 0x10c0b8, 0x10d638, 0x10e938, 0x10fb38, 0x1100f8, 0x110d40, 0x1113c8, 0x112220, 0x1133c8, 0x113f00, 0x114d48, 0x116718, 0x118360, 0x119c50 + helpers 0x163ea8, 0xca628†, 0xea68†, 0xf130† | none |

| H6 | **Round36** | see the commit that adds this row | `af3a7529160d5ff55f8cad5fc08b6c3dbbea856435420973b5401071c016a493` (`e11320e4c1c2c29feb775182c90d88ea41defcf2015b6f7a907a8c53f8ae8c81`) | **762 / 126 / 964,776** | 0xea68, 0xf130, 0xca628, 0xcf510, 0x10a0e0, 0x10c0b8, 0x10d638, 0x10e938, 0x10fb38, 0x1100f8, 0x110d40, 0x1113c8, 0x112220, 0x1133c8, 0x113f00, 0x114d48, 0x116718, 0x118360, 0x119c50, 0x1255a8, 0x12a4e0, 0x12abc8, 0x137fc0, 0x163ea8 | **normalized: none. Raw: none vs a same-recipe base**. Against the published inventory, 19 raw are recipe-dependent (0xa7e0, 0x18a3b0, 0x18a4d8, 0x194998, 0x194ae0, 0x197508, 0x1991e0, 0x19a758, 0x19a8a0, 0x1a0f68, 0x1a2340, 0x1a6370, 0x1a6940, 0x1ab220, 0x1ab730, 0x1b3220, 0x1b38c0, 0x1b4088, 0x1b40d0); see the control |
| H7 | **Round36** (same-recipe base 738/126) | see the commit that adds this row | `a0f3aa555a06e16a95512fb3897c26dff3a2ddf362a2f4355aff674604d8ed81` (`d875b109fddfb254ecfd06e48e627f40d08d6b81cba676fe21d3a0937ae8179c`) | **764 / 126 / 972,072**, full corpus passes, 0 stack warnings | H6 set + 0x10b0b8 (collect_coin_creator_fee accounts inside `if !frozen`) + 0x1176e0 (change 8) | none (migrate_v2 part of change 7 removed) |
| H7 on i1c | Pump composite **i1c** (778/135/984,768, identity recipe) | same commit | `88f345dc99b32b605c103fc29f542ed8d5cf8d12ed5e34e31fa6fd22656e8f6a` (`ddff3906b69d29f24aeb62eabd485b1972963af9fc29f5e68fba9ae55c93433e`) | **779 / 135 / 987,968**, 0 stack warnings | beyond i1c: 0x1176e0 | none |

H3 raw gains are 0x198fe8 and 0x19b4e0. † These are in other claim families or lanes and are gained by this lane's SetMayhemVirtualParams layout change; they are reported for dedupe.

## State for a continuation agent

- Frontier: Round25 (`repro/pump/main-contract-round25-20261027`, 720/123/871,992). Rebase before every commit, because Codex and the Pump session publish rounds frequently.
- Scope: only the `targets/body-rest.json` windows in this address range. They live in the coordinator scratchpad `…/bfdcc76c-…/scratchpad/targets/`. Skip coord, nearmiss, identity and libinst.
- Build loop: `tools/trial.sh <name> <source dir in worktree> [packet]` runs a cached frontier-recipe build under `sbf_lock.py --slots 6 --name sbf`, then `tools/measure.py`. The dependency cache is `SP/lanes/pump-hi/out/depcache`. The shared `fastbuild.py`, `score.py` and `win.py` (coordinator scratchpad `shared/`) are equivalent and faster.
- Apply this lane's changes to a new round with `python3 tools/apply_lane_changes.py --source-directory <crate>`.
- Runtime check: run `tools/run_suites.py --suites all --workers 3` with `REPO/work/test-env/bin/python` and `PYTHONDONTWRITEBYTECODE=1`. The sparse checkout must include `research/imported-lab`, `repro/pump/claim-token-incentives`, `repro/pump/native-curve-partial-fortyeight` and `repro/pump/tokenkeg-two-curve-fortyeight`.

## Target list (body-rest ∩ range, Round25): 44 windows, 215,312 B

- Gained by H3: 0x11b758, 0x1348c0, 0x12a4e0, 0x12abc8, 0x19e3b0.
- In progress: 0x137fc0 (mayhem handler).
- Open:
  - CPI-client family: 0x10a0e0, 0x10b0b8, 0x10c0b8, 0x10d638, 0x10e938, 0x10fb38, 0x1100f8, 0x110d40, 0x1113c8, 0x112220, 0x1133c8, 0x113f00, 0x114d48, 0x116718, 0x118360, 0x119c50.
  - Others: 0x109488, 0x1176e0, 0x131128, 0x1316e8, 0x1367c0, 0x138b20, 0x13b9b8, 0x13f630, 0x144508, 0x147ba0, 0x1489f8, 0x14a8a8, 0x14c038, 0x14f4e0, 0x152888, 0x1557e8, 0x17bc48, 0x17c0f0, 0x17c548, 0x184e38, 0x18fc98, 0x1905a8.

## Log

| when | base | change | result |
|---|---|---|---|
| 06:13 | Round20 | `#[program]` handler order from the original dispatcher | +0x11b758 (706/120), no losses |
| 06:22 | Round21 | same | +0x11b758 (709/123) |
| 06:27 | Round21 | + by-value `update_global_authority_handler` | +0x1348c0 (710) |
| 06:31 | Round23 | both | 714/123/864,904; full corpus 10,468/10,468, 0 diagnostic mismatches |
| 06:47 | Round23 | + legacy buy `execute<const EXACT>` | +0x12a4e0, +0x12abc8 (716); full corpus passes |
| 06:55 | Round23 | + Anchor `system_program::transfer_with_seed` in admin_set_idl_authority | +0x19e3b0 (717/125; raw +0x198fe8, +0x19b4e0) |
| 06:58 | Round23 | + unboxed Global only in SetMayhemVirtualParams | no gain (struct 1,688 vs original 1,728 B) |
| 07:03 | Round24 | four changes (725/125); + owned `sol_vault_authority` (a) | 727 (+0x1255a8, +0xcf510) |
| 07:03 | Round24 | + owned `token_program` instead (b) | 727 (same gains); (c) both → 725 |
| 07:12 | Round25 | five changes | 727/125/890,304, no losses; reproduced Round20/21/23/24 base hashes exactly |
| 07:20 | Round25 | `execute` made `pub(crate)` (mvh1); + curve fields first and mint key after Clock (mvh2) | no gain; mvh2 window is now the inlined `#[program]` fn, 0.88 similar |

## Round36 rebase (H6)

- Already in Round36: change 1 (dispatcher order, 0x11b758), change 2 (update_global_authority, 0x1348c0), and an equivalent of change 4 (Anchor `transfer_with_seed`, 0x19e3b0). Round36 also matches the distribution wrappers 0x131128 and 0x1316e8.
- Re-applied: changes 3 (buy split), 5 and 6 (SetMayhemVirtualParams layout and handler), and 7 (generated CPI clients; the `init_boost` edits are now substring-based because Round36 changed those lines).
- Measured 762/126/964,776 with no normalized losses.
- Control: unmodified Round36 built with the same plain archived builder gives **738/126** and the same 19 raw differences (`evidence/elf/r36-base`). Round36's 145 raw comes from its layout-linked recipe (`ordered.ld`, data-order certificate, Linux target-library profile). The lane changes therefore lose nothing against a same-recipe base, and integration must re-derive the layout including the added functions.
- Split: changes 3, 5 and 6 alone give 743/126/908,888 (`evidence/elf/r36-noncpi`); adding change 7 gives 762/126/964,776.
- **Runtime rejection of the 762 build.** In the full corpus, `migrate_v2` fails 482 of 827 cases with `Access violation in stack frame 5 at address 0x200005fe8 of size 8` (ProgramFailedToComplete). Change 7 had put the generated `create_pool`/`init_boost` clients into `migrate_v2::execute`, and the build log warns `Stack offset of 4104 exceeded max offset of 4096 by 8 bytes` for that function. The changes 3, 5, 6 control (`r36-noncpi`) equals the original on the failing cases (`tools/probe_cases.py`, cases 0, 1, 3, 8). The three `migrate_v2.rs` entries now sit under `rejected_not_applied` in `tools/cpi_changes.json`, so `migrate_v2` keeps the frontier hand-built `call(...)` CPIs. `migrate.rs` still instantiates both generated clients. Evidence: `evidence/runtime-r36-lane-migrate_v2-rejection.json`. The Pump integration composite i1b carries the same warning (estimated frame 4,416 B); the coordinator has been alerted. Rule from now on: a `Stack offset … exceeded` warning in any build log blocks adoption.
- H7 (corrected candidate `r36-cpi4`: change 7 without migrate_v2, plus the collect form, plus change 8): 764/126/972,072, no losses against r36-base or the 762 build, no `Stack offset` warning. Full 44-suite corpus 10,468/10,468, 0 errors, 0 diagnostic mismatches (`evidence/runtime-full-r36-cpi4.json`); migrate_v2 827/827. On the composite i1c (identity recipe) change 8 adds 0x1176e0: 779/135/987,968 (`source-on-i1c.patch`, `evidence/elf/i1c-779-fee8`).
- Measured on top of the 762 build, same recipe, no normalized or raw losses: `r36-cpi2` (`collect_coin_creator_fee` accounts built inside `if !frozen`) gives 763/126/968,872 (+0x10b0b8). `r36-cpi3` (cpi2 + change 8) gives 764/126/972,072 (+0x10b0b8, +0x1176e0). Both still contain the rejected `migrate_v2` part. They are re-measured without it before any claim (`r36-cpi4`).

## Round37 (origin/main b855ede02, 744/175 published)

- Round37 itself declares `declare_program!(pump_fees)` (lib.rs:65), ships `idls/pump_fees.json` (equal to `evidence/upstream`) and matches 0x1176e0 through the generated `pump_fees::cpi::get_fees_with_quote_mint`. Change 8 is therefore superseded there.
- `tools/apply_lane_changes.py` is now Round37-aware:
  - `lib_append` adds only the `declare_program!` lines that are missing, so pump_fees is never declared twice;
  - an IDL that already exists in the crate is never overwritten, which keeps Round37's `idls/pump_fees.json` and any derived `idls/pump_amm.json` of a composite;
  - change 8 reports `superseded by the frontier` when `fee_cpi.rs` uses the generated client.
- Checks of `--with-cpi-7 --with-fee-8`:
  - on Round37: a single pump_fees declaration (lib.rs:65), pump_amm appended, `pump_fees.json` byte-identical, and a second run changes nothing;
  - on Round36: the output equals the corpus-validated H7 source (`r36-cpi4`);
  - on i1c: the output equals `i1c-fee8` (779).
- Identity recipe (`fastbuild.py`), same-recipe base: Round37 unmodified builds to 749/133/924,472 (+5 identity-recipe windows against the published inventory). Round37 + lane changes + the GlobalConfig boost change gives 775/133/995,984, with 26 gains and no normalized or raw losses. The GlobalConfig boost change duplicates the integration's nearmiss2-03 delivery (0x109488 and siblings), so it was removed from the tool and is not claimed. The exact tool output (`--with-cpi-7 --with-fee-8`, `evidence/elf/r37-774-lane`) gives **774/133/992,824**: 25 gains against the same-recipe base (`evidence/elf/r37-749-base`), 0 normalized and 0 raw losses, `stack_warnings=[]`.
- Runtime evidence for nearmiss2-03, from this lane's independent GlobalConfig-IDL build (`r37-lane`, candidate `377c18f4…`): `migration` 228/228 and `migrate_v2` 827/827 pass per-suite validation. The paired diagnostic audit finds 1,055 log cases and 0 mismatches (`evidence/runtime-r37-globalconfig-migration.json`).

## Round26 findings

- H4: full public 44-suite corpus passes on `4cbe303d…` (10,468/10,468, 0 diagnostic mismatches; `evidence/runtime-full-r26-lane.json`). `virtual_reserve_sync` also passes on its own (192/192).
- H5: change 7, `apply_lane_changes.py --with-cpi-7`, is described in `tools/cpi_changes.json`. It adds `declare_program!(pump_amm)` and `declare_program!(pump_fees)` from the official upstream IDLs (`evidence/upstream`, pump-public-docs `639b87f`) and calls the generated clients for create_pool, init_boost, admin_cto_pool, collect_coin_creator_fee, transfer_creator_fees_to_pump_v2 and admin_cto_sharing_config. It gains 19 windows, 0 losses (`evidence/elf/r26-748-cpi`).
- DistributeCreatorFees with one more owned `AccountInfo` closes `0x131128` (730, 0 losses) with either system_program (d1) or event_authority (d2) owned. The v2 wrapper `0x1316e8` additionally needs `quote_mint` boxed: the original's v2 value is v1 + 40 bytes.
- No gain: `pub mod fee_cpi` (technique 1) for `0x1176e0`, and the reference-holding admin_set_idl_authority rewrite for `0x1557e8`.

## Negative controls (do not repeat)

- `update_global_authority` with the assignment moved first, still in the `#[program]` fn body (`r21-uga`): the binary changed but there was no match. The bump stays a late load through the saved `ctx`.
- The same handler as an `#[inline(always)]` fn (`r21-uga3`): no match. Only the plain private `fn` reproduces the entry-time loads.
- Handler reorder alone on Round20: +0x11b758 only.
- Codex's older const-split control (about 04:10, base 643) shrank the wrappers to 1,584 B with `#[inline(always)]` dispatch and gained nothing. A plain const generic with unchanged body text gains both wrappers.
- SetMayhemVirtualParams with Global unboxed only (`r23-mvp`): no gain. Owned `token_program` and owned `sol_vault_authority` both close the wrapper and exit. Owned `sol_vault_authority` is kept because the original `try_accounts` `0xcd3d8` is closer (0.49 vs 0.31). Both together lose the gain.

## Windows examined and left to others

- `0x180cc0`, `0x192c20` (token_2022 burn) were delivered by Codex `parallel-main-migration-burn` and are matched in Round23.
- `0x12ba48` (migrate_v2 wrapper; MigrateV2 accounts value 274+ vs 192 B) is migration context work.
- The 30 coordinate-only windows in range are exactly the coordinator's coordinate-only list and are left to integration.
