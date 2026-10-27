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
| H3 | **Round25** | see the commit that adds this row | `3f9b38145fc777c88ec291a8e25a2687193af05d422ad419a156fda505d23ca3` (`8a45886afb3003205f16b0b085d377dc64f6c478ee6f40cb91be4b815dfaf843`) | **727 / 125 / 890,304** | 0x11b758, 0x1348c0, 0x12a4e0, 0x12abc8, 0x19e3b0, 0x1255a8†, 0xcf510† | none |

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
