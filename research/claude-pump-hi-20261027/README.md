# Main Pump — lane pump-hi (original windows 0x101170 … 0x1ab9b8)

Review status: the PR #264 review noted that the earlier packet lacked the candidate ELF. Every claimed result
now ships its stripped and unstripped ELFs (gzipped), their SHA-256 values and the score output under
`evidence/elf/<name>/`, so the matches can be recomputed independently. This is still an unpromoted proposal.

Isolated, ordinary-source recovery for the upper third of the main Pump program, measured on
top of the newest published frontier, [Round25](../../repro/pump/main-contract-round25-20261027/README.md).
**Whole-ELF identity remains false.** This packet does not edit `programs/pump`, because the CI guard pins
it to the Round25 package. The changed sources ship here as full files, plus `source.patch`, a `git apply`-able
diff against Round25 `programs/pump`. `tools/apply_lane_changes.py` applies the same five changes,
idempotently and content-addressed, to any later round.

## Result

| | normalized | raw | unmatched | matched text bytes |
|---|---:|---:|---:|---:|
| Round25 frontier (`ef31dfd3…` / `d36b2984…`) | 720 | 123 | 315 | 871,992 |
| Round25 + this lane (`8a45886a…` / `3f9b3814…`) | **727** | **125** | 308 | **890,304** |

There are **no normalized or raw losses**. `evidence/elf/r25-727/` holds `candidate.so.gz`, `unstripped.so.gz`,
`SHA256SUMS`, `score-summary.json` and the full per-window `score.json.gz`. The result was scored by both
`tools/measure.py` and the shared `score.py`, which agree.

| original window | bytes | body | source cause (evidence) |
|---|---:|---|---|
| `0x11b758` | 8,696 | Anchor `entry` / instruction dispatcher | `#[program]` handler order. The original compares the 56 `sha256("global:<name>")[..8]` discriminators in a different order. That order is read from the original dispatcher, and the handler items are permuted to match. Every other dispatcher instruction was already identical. |
| `0x1348c0` | 3,264 | `update_global_authority` | The original assigns `global.authority` before building the event. The `#[program]` entry passes its `Context` by value to a private handler fn, so the bump and accounts pointer are loaded at entry as in the original. |
| `0x12a4e0` | 1,768 | `__global::buy` | The original wrapper calls a five-argument handler (`0x14c038`) without a constant `exact` stack argument. The legacy buy handler takes `exact` as a const generic, so each entry calls its own specialization. The original has two handler bodies, 10,880 B and 13,224 B. |
| `0x12abc8` | 1,768 | `__global::buy_exact_sol_in` | Same change, for the `exact = true` specialization (handler `0x14f4e0`). |
| `0x19e3b0` | 896 | `anchor_lang::system_program::transfer_with_seed` | `admin_set_idl_authority` reclaims an uninitialized IDL account through Anchor's CPI helper. The helper passes three account infos (from/base/to), replacing the hand-built `system_instruction` call. |
| `0x1255a8`† | 1,344 | `__global::set_mayhem_virtual_params` | `SetMayhemVirtualParams` layout: `Global` is unboxed and `sol_vault_authority` is an owned `AccountInfo`. That makes the 1,728-byte accounts value and the original field offsets (Global data +1672, curve +496). |
| `0xcf510`† | 576 | `SetMayhemVirtualParams::exit` | Same layout change. This window is in lane pump-mid's address range. |

† Claimed by another target family in the coordinator's split. It is gained by this lane's change and reported here for dedupe.
`0x198fe8` and `0x19b4e0` additionally become raw byte-equal (already normalized matches).

History: the dispatcher order and `update_global_authority` were first verified on Round21 (709 → 710) and Round23 (712 → 714). That 714 result is in PR #264, with ELFs now in `evidence/elf/r23-714/`. The buy split was verified on Round23 (716, `evidence/elf/r23-716/`). The IDL helper and the SetMayhemVirtualParams layout were verified on Round23 and Round24 (717, 725, then 727), and all five were re-measured on Round25.

## Changed files (vs Round25 `programs/pump`)

- `src/lib.rs`: the `#[program]` items reordered, with text unchanged and one blank separator line dropped. `update_global_authority` delegates to `fn update_global_authority_handler(ctx)`, appended at end of file. The two legacy buy entries call `legacy_buy::execute::<false|true>`.
- `src/buy.rs`: `pub fn execute<'info,const EXACT:bool>(…, track, partial)` with `let exact=EXACT;` on the signature line, so no source line moves.
- `src/admin_set_idl_authority.rs`: `anchor_lang::system_program::transfer_with_seed(CpiContext::new_with_signer(…TransferWithSeed{from,base,to}…), "anchor:idl", &crate::ID, lamports)`. The block keeps its seven lines.
- `src/mayhem_virtual_params.rs`: `sol_vault_authority: AccountInfo<'info>` and `global: Account<'info, Global>`.

Behavior is unchanged: dispatch is an exact-match on distinct discriminators, the event carries the same fields, the buy specializations constant-fold the same code, the transfer-with-seed CPI has the same instruction and signer, and the account types carry the same constraints. See `RUNTIME.md`.

## Builds and measurement

- Recipe: the frontier packet's archived builder (`inputs/scripts/pump_build_verified.py`, v1.44 SDK, workspace layout, physical-source wrapper) with an external-only dependency cache private to this lane. Every build ran under the shared slot lock. The same recipe reproduced the published Round20, Round21, Round23 and Round24 hashes exactly (`evidence/builds/r23-base`; the others are in `PROGRESS.md`).
- Round25 + lane: `evidence/builds/r25-lane` is a fresh Round25 copy changed only by `tools/apply_lane_changes.py`. `evidence/builds/r25-reproduce` is this packet's `reproduce.py` (Round25 primary + `source/`).
- `tools/measure.py` reimplements the frontier inventory using the packet's own normalizer. It agrees with the shared `score.py` on every claim here.

## Target scope (coordinator split, Round25)

This lane now works only the `targets/body-rest.json` windows inside 0x101170 … 0x1ab9b8 (44 windows, 215,312 B), skipping the coordinate-only, near-miss, identity and libinst families. The current state of that list is recorded in `PROGRESS.md`.

## Residual diagnosis for windows examined but not closed

- `0x137fc0` `set_mayhem_virtual_params` handler: the layout now matches. With `execute` made `pub(crate)`, LLVM inlines it into the `#[program]` fn as in the original (0.88 similar). The remaining differences are when the post-sync reserves and the sync arguments are loaded. Variants are being measured (see `PROGRESS.md`).
- `0x10a0e0 … 0x11ad10` (16 windows, about 55 KB) are `declare_program!` CPI clients. Their embedded discriminators identify the instructions:
  - `pump_amm`: `create_pool` (18 accounts), `init_boost` (14), `collect_coin_creator_fee` (8) and `transfer_creator_fees_to_pump_v2` (12);
  - `pump_fees`: `admin_cto_sharing_config` (7);
  - two clients are not yet identified.

  Each client has its own `to_account_metas` and `to_account_infos` bodies. They are called from admin_cto (`0x22a10`) and the migrate helpers (`0x43ea0`, `0x45fa0`, `0x502f0`, `0x52660`). The in-repo IDLs (`programs/pump-fees/idls/pump_amm.json`, `programs/pump-amm/idls/pump_fees.json`) carry the same instruction and account discriminators. Those include GlobalConfig `0xd9b0fca0ca9c0895` and FeeConfig `0x9b4c7bdbbb92348f`, which are the original's `lib.rs:83/84` `try_deserialize` windows `0x1091b0` / `0x1156f0`. So the original evidently declares `declare_program!(pump_amm)` / `declare_program!(pump_fees)`. Recovery means switching the hand-written CPIs at those call sites to the generated clients.
- `0x131128` / `0x1316e8` `__global::distribute_creator_fees(_v2)`: the accounts value is 488 vs 448 bytes. The IDL account list is identical, so the difference is a field type or data layout. `try_accounts` `0xc1d58` is unmatched.
- `0x1557e8` `admin_set_idl_authority` handler: three Source sites at lines 72/79/90 versus the candidate's two, so the body is structurally different.
- `0x14c038` / `0x14f4e0` (legacy buy handlers): the original's `buy` body has its Source sites in `lib.rs` (608–747) and `buy_exact_sol_in` in `buy.rs` (53–232).
- Codex-active trade handlers: `0x138b20`, `0x13b9b8`, `0x13f630`, `0x144508`, `0x147ba0`, `0x1489f8`, `0x14a8a8`, `0x152888`.
- Token-2022 transfer-fee TLV and math: `0x17bc48`, `0x17c0f0`, `0x17c548`. Extension instruction-builder chain: `0x184e38` → `0x1905a8` → `0x18fc98`.
- `0x1367c0` `set_params` handler: it splits work into helper `0x3e550` and raises `lib.rs`-sourced errors.
- `0x109488` GlobalConfig body deserializer: generated by `declare_program!(pump_amm)`.

## Reproduce

```sh
python research/claude-pump-hi-20261027/reproduce.py --registry-home ~/.cargo --output work/pump-hi-reproduce
python research/claude-pump-hi-20261027/tools/apply_lane_changes.py --source-directory <crate dir of a later round>
```

`tools/` also holds the triage, diff and coordination scanners used here: `triage.py`, `sbfdiff.py`, `slotdiff.py`, `ident.py`, `coordinates.py`, `codex_scan.py` and `run_suites.py`. See `PROGRESS.md` for the running log, harvest entries and negative controls.
