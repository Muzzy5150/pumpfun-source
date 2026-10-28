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
| H11 | **L06** (899/165, identity recipe) | see the commit that adds this row (`L06/`) | `6844f8d6026bd3d896ef161e5a4028ba2ce7abfbfd2aca0c5719fbb7b610c225` (`33a7c58e3c61c1117b63d89b84de9daba578749fa031d6c53546e74c8dc41221`) | **902 / 165 / 1,237,000**, full corpus passes (44/44, 10,468 cases), 0 stack warnings | 0x502f0 (migrate_v2 create_pool helper), 0x43ea0 (migrate create_pool helper), 0x47e28 (base_token_program; Pump-session plainbody window, parked there) | none |

H3 raw gains are 0x198fe8 and 0x19b4e0. † These are in other claim families or lanes and are gained by this lane's SetMayhemVirtualParams layout change; they are reported for dedupe.

## State for a continuation agent (big-lo upper half, base L06)

- Assignment: the big-lo windows with start > 0x3a7b8 (16 handler bodies, 0x3b8d8 … 0x5b3b0). `big-lo/NOTES.md` has the window map.
- Baseline: `claude-pump-work/base/L06/pump` (899/165). It rebuilds bit-for-bit (`7bc1563b…`).
  - Measure with `claude-pump-work/harness/fastbuild.py` and `score.py --baseline base/L06/inventory.json`.
  - Deliver patches that `git apply -p1` cleanly in a copy of `base/L06/pump`.
- L06 has layout padding (blank lines) that puts every Source site on its original line.
  - Never change the line number of an existing line.
  - Replace an N-line statement with N lines, and append new helpers after the last line of the file.
- Durable scratch is `claude-mayhem-work/pump-hi/` (`fb/`, `trials/`, `out/`, `mini/`).
  - `mini/exp.py NAME EDIT.py --win 0xADDR:SYMREGEX` copies L06, applies an edit script, builds, scores and compares windows. Edit scripts are in `mini/ed/`.
  - `mini/cmpw.py` gives similarity with and without stack offsets and registers.
- Delivered: H11 (`L06/`), 902/165. Open next, at the coordinator's request:
  - 0x43060, 0x4eb28 and 0x52660, using pump-big-lo's `?` error-path rule.
  - 0x43060 is the migrate v1 quote funding: `sub_lamports`/`add_lamports` plus a hand-built 3-account SyncNative `invoke`. As a helper it reaches noreg 0.975 (`mini/ed/wq1.py`). The original reloads the account pointers from `&Migrate` after each call, while this build keeps them in registers.
- Parked by the coordinator (r4 plainbody): 0xcd3d8, 0x17bc48.
- Tools:
  - `tools/fb_record.py` and `tools/run_suites.py` run the corpus. The candidate must sit under `wt/work/`.
  - tokenkeg_two_curve needs an archived build: `tools/build.py --packet repro/pump/main-contract-round37-20261027`, run under `SP/sbf_lock.py`.

## State for a continuation agent (pre-reboot, historical)

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

## r37g4 restart (upper body set, 24 windows; base r37g4 785/164)

- Environment: after the 20:43 reboot, durable scratch lives in `claude-mayhem-work/pump-hi/` (fastbuild work, trials, outputs). `fastbuild.py` (identity) rebuilt the unmodified r37g4 bit-for-bit (`71fd74ad…`).
- **H8: 0x17c0f0 (`required_quote_account_len`, 744 B)**. The helper becomes `#[inline(never)]` and walks the TLV with `loop { let rest = tlv.get(cursor..)?; ... }`. kind and length are read through `u16::from_le_bytes(rest[..2].try_into().unwrap())`, which gives the original's single `ldxh`. Known kinds go through an `Option` payload match with a u64 `seen` bitset, so duplicates are skipped exactly as in the original; the frontier returned None for them. The line count of migrate_v2.rs is unchanged.
  - Compiled in isolation (`tools/mini_cmp.py`), the function is byte-identical to the original window.
  - Full build on r37g4: **786/165/1,012,168**, gains 0x17c0f0 (normalized and raw), no losses, `runtime_valid` true, no stack warnings.
  - Runtime: migrate_v2 suite 827/827, 0 errors, 0 diagnostic mismatches.
  - Delivery: `r37g4/` with a patch against base/r37g4/pump, ELFs, score and a stdlib `verify.py`.
- **H9: 0xc5650 (`DistributeFeeToHolders::try_accounts`, 7,344 B)** comes from the anchor-lang feature `allow-missing-optionals` (Cargo.toml).
  - The original builds AccountNotEnoughKeys (0xbbd) twice in that function; the frontier builds it three times. The extra one is the empty-list error for the optional `holder_rewards_token_account`, which the feature turns into `None` (anchor-lang `Option<T>::try_accounts`).
  - On r37g4 + H8 it measures **787/165/1,019,512** (+0xc5650 normalized), no losses, no stack warnings.
  - Runtime: 43 public suites, 10,448 cases, 0 errors, 0 diagnostic mismatches. quote_control was re-run with an in-repo candidate path, because that harness rejects paths outside the repository. tokenkeg_two_curve needs an archived-builder build report and is run on an archived build of the same source.
  - Behaviour note: a transaction that omits trailing optional accounts now gets `None` instead of error 3005, as in the original.
- **H10: 0xd5af0 (`MigrateV2::try_accounts`, 23,608 B), with 0x12ba48 (`__global::migrate_v2`, 1,072 B; libinst/libnear family, reported for dedupe)**. Two changes to migrate_v2.rs:
  1. `#[event_cpi]` replaces the explicit `event_authority`/`program` UncheckedAccount fields. The generated owned AccountInfo pair gives the original struct layout, which matches the dispatcher wrapper as well.
  2. The bonding_curve constraint uses the original's evaluation order: `quote_mint.key()==bonding_curve.quote_mint||(bonding_curve.quote_mint==Pubkey::default()&&quote_mint.key()==native_mint::ID)`. The original compares against `bonding_curve.quote_mint` first, then against the default key, then against native. The frontier's `if/else` compared against the default first. The two are equivalent for any account that deserializes as a Mint.
  - Three combined field lines are split one per line, so migrate_v2.rs keeps its 170 lines and later Source lines do not move.
  - `rent: Sysvar<Rent>` was tested and rejected: it loses 0x12850 (`Sysvar<T>::try_accounts`).
  - On r37g4 + H8 + H9: **789/165/1,044,192**, no losses, no stack warnings.
  - Full corpus for the shipped source: 43 suites on the identity build, plus tokenkeg_two_curve on an archived build of the same source. 44/44 suites, 10,468 cases, 0 errors, 0 diagnostic mismatches.
- Body-only fixes for the original lib.rs helper cluster (lib.rs 2428–2554). They are coordinate-bound and are delivered as `r37g4/body-only/fee_cpi-on-r37L2.patch`, which applies to both r37L2 and r37g8 and keeps fee_cpi.rs's line count.
  - 0xa0070 `buy_quote` (1,224 B): compute the u128 numerator first and the denominator with u128 `checked_sub`. On r37L2 the remaining diff is only the coordinates (lib.rs:2428/2430 against fee_cpi.rs:10/11, filename length 24 against 28).
  - 0xa08f8 `market_cap` (760 B): `(supply*vqr).checked_div(vtr).ok_or_else(|| error!(DivisionByZero))` in place of a leading `require!`. The original jumps forward to its error block and falls through into the computation. The remaining diff is only the coordinates (lib.rs:2481). `trade::buy_fee_market_cap` is an identical duplicate; the original has one shared function.
- Analysis of the rest of the cluster, for the integrator. None of these exists as a separate function in the candidate; the handlers compute them inline.
  - 0xa0538 `sell_quote(curve, amount) -> Result<u128>`: the denominator is u128 vtr + amount, the `require!(den != 0, DivisionByZero)` is at lib.rs:2454, and the result is amount·vqr/den. Callers: 0x5b3b0, sell_v2 0x144508, trade_v3 0x14a8a8, legacy sell 0x152888.
  - 0xa0bf0 apply-buy: checked vtr−=t, rtr−=t, vqr+=q, rqr+=q, with Overflow at lib.rs:2496/2501/2506/2511. Callers: 0x5b3b0, 0x83c00, buy_v2 0x13b9b8/0x13f630.
  - 0xa13e0 apply-sell (lib.rs 2520–2535). Callers: 0x5b3b0, sell_v2, trade_v3.
  - 0xa1bd8 fee accrual (lib.rs 2550/2554). It reads curve +0x9a and global +0x418, computes x·bps/10 000 and adds it into curve +0x78/+0x70.
- Leads:
  - 0xcd3d8 (SetMayhemVirtualParams::try_accounts): with `token_program` as `Program<Token2022>`, or as `Interface` without the address constraint, the original has no ConstraintAddress. That gives 8,472 B against the original's 8,504 B, with normalized-instruction similarity 0.98. The original copies `token_program.key()` into a second 32-byte temporary before the token-program `memcmp`, which accounts for the 32-byte larger frame and 4 more instructions.
  - 0xcd3d8 negative controls: explicit `event_authority` with `program: Program<PumpRecovered>` loses the wrappers (0xcf510, 0x1255a8, 0x137fc0). Dropping `associated_token::token_program` gives 8,168 B, ratio 0.43, and 13 raw losses. `Program<Token2022>` and an address-free `Interface` are equivalent (8,472 B, 0.514).
- 0x17bc48 (`quote_extensions_supported`) is in progress.
  - Its loop is unswitched on `allow_token_extensions` unless the TransferHook program-id check is a pre-unrolled helper over `&[u8; 32]`. A helper `fn(&[u8;32]) -> bool { k.iter().all(..) }` with a single caller gets inlined after its own simplification, so the loop is never unswitched.
  - With that change the function is 1,200 B (original 1,192 B) and the only remaining differences are loop layout and register assignment: the original spills the cursor where this one spills the TLV base.
- 0x109488 remains open on r37g4 because the GlobalConfig IDL change (nearmiss2-03) is not in r37g4. Per the coordinator's dedupe it is left to that delivery.

## L06: create_pool helpers (H11, 899 → 902/165)

- The original's migrate_v2 execute (0x49888) and migrate execute (0x3fb70) call standalone pool-creation helpers.
  - 0x502f0 (8,704 B) is the migrate_v2 helper and 0x43ea0 (8,448 B) is the migrate helper.
  - Each takes `(ctx: &Context<…>, base, quote)` and calls the generated `pump_amm::cpi::create_pool`, which is 0x10c0b8.
- Matched form (behaviour unchanged):

```rust
fn create_pool<'info>(ctx:&Context<'_,'_,'_,'info,MigrateV2<'info>>,base:u64,quote:u64)->Result<()>{
 let bump=ctx.bumps.pool_authority;let a=&ctx.accounts;
 let create=move |signer_seeds:&[&[&[u8]];1]|pump_amm::cpi::create_pool(CpiContext::new_with_signer(a.pump_amm.to_account_info(),pump_amm::cpi::accounts::CreatePool{…18 accounts in IDL order…},signer_seeds),0,base,quote,a.bonding_curve.creator,a.bonding_curve.is_mayhem_mode,OptionBool(..),OptionU64(..),OptionBool(..),OptionBool(..));
 create(&[&[b"pool-authority",a.base_mint.key().as_ref(),&[bump]]])
}
```

- The frame fixes the seeds construction. Allocas appear in reverse MIR-local order, so the original's layout (low to high) is signer array, seeds array, mint key temp, bump array, then CpiContext. That order requires:
  - the seeds to be built in a call argument with `key()` inline, so the mint temp comes after the seeds array;
  - the CpiContext to be created after them, which happens inside a closure body.
- What the variants measured:

| variant | result |
|---|---|
| `let mint=…` before `let signer=…` (cp5/cpL1) | mint lands below signer; noreg 0.787 |
| seeds inline in `new_with_signer` (cpL2) | seeds evaluated after the clones; 0.757 |
| `&key().to_bytes()` inline (cpL3) | slot order correct, but 4 loads before 4 stores instead of the interleaved key memcpy |
| non-`move` closure (cpL4/cpL8) | exact frame, but precise captures load the bonding_curve and quote_mint boxes early; noreg 0.84 |
| `move` closure, `let bump` first (cpL6) | **exact**; `pub` and `#[inline(never)]` are not needed (cpL6a/b/c) |

- The migrate (v1) helper is identical except for `base_token_program:base_token_program(a.mint.as_ref().as_ref(),&a.token_program,&a.token_2022_program)`.
- That callee is window 0x47e28: `#[inline(never)] fn base_token_program(mint,token_program,token_2022_program:&AccountInfo)->AccountInfo`, returning `token_program` when `*mint.to_account_info().owner==anchor_spl::token::ID` and `token_2022_program` otherwise. It replaces L06's `mint.owner==tok.key` selection, which is equivalent because `token_program` is address-checked.
- Call sites: `create_pool(&ctx,base,` / `quote)?;` replaces the 2-line hand-built CPI in each execute, so line counts are unchanged.
- Runtime:
  - migrate_v2 and migration suites first: 1,055 cases, 0 mismatches.
  - Full corpus: 43 suites on the identity build (10,448 cases) plus tokenkeg_two_curve on an archived build (20 cases). 0 errors, 0 diagnostic mismatches.

## L06-904 compose (for the Pump session's PR)

- This is base/L06/pump plus the H11 patch plus pump-big-lo gain01 (`72a31c585:…/gain01-set_creator/source.patch`, set_creator.rs). Both patches applied cleanly with `git apply -p1`.
- Result: 904/165/1,246,688; gains exactly {0x38fc0, 0x3a7b8, 0x43ea0, 0x47e28, 0x502f0}, with no losses and no stack warnings.
  - unstripped `1fb409bb6f1be6a9da4a0f0744b62db271bfa45bb02c51bd1b465c56d129f9d6`
  - stripped `4e23b5ae865ede92836d6302f9663b673ceef82169c038c87fa43c9e9f904b03`
- Corpus: 44/44 suites, 10,468 cases, 0 errors, 0 diagnostic mismatches. tokenkeg_two_curve ran on archived build `2b586a07…`.
- Package: `L06-904/`, with the combined patch, ELFs, score, runtime summary, MANIFEST crediting both lanes, and verify.py.

## g04 baseline (806/165, unstripped 5a13b87f…)

- g04 does not contain H10: its MigrateV2 still has the explicit UncheckedAccount event fields and the if/else constraint. `tools/apply_migrate_v2_accounts.py` re-applies H10 idempotently and keeps the 191 lines of migrate_v2.rs.
- On g04 it measures **808/165/1,069,560**, gains 0xd5af0 and 0x12ba48, no losses, `runtime_valid` true, no stack warnings. The unmodified g04 rebuilds bit-for-bit (`5a13b87f…`).
- Full corpus for the shipped g04 source: 43 suites on the identity build, plus tokenkeg_two_curve on an archived build of the same source. 44/44 suites, 10,468 cases, 0 errors, 0 diagnostic mismatches.
- Delivery: `g04/`, with `source-on-g04.patch`, ELFs, score, runtime summary and a stdlib `verify.py`.
- Dedupe with the Codex Round37 series on origin/main:
  - pump-round37-marketcap-checked (0xa08f8) and pump-round37-curve-price (0xa0070, 0xa0538) cover the same source forms as this lane's body-only `fee_cpi` patch, which is withdrawn.
  - pump-round37-curve-apply (0xa0bf0, 0xa13e0) and pump-round37-curve-fee-accrual (0xa1bd8) cover the rest of the lib.rs helper cluster.

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
