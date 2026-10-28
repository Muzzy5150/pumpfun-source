# pump-mid lane progress (harvest log and continuation notes)

Lane range: original windows 0x65eb0 … 0xfdf20, restricted to the integration session's
`targets/body-rest.json` claim (66 windows / 211,800 bytes at Round25).
Coordinate-only, nearmiss, identity and libinst families belong to the "Main pump contract completion" session.

## Harvest entries

### Gain 1 — patches 02, 03 (measured on Round25, committed on Round26)

- Base round: Round26 (`repro/pump/main-contract-round26-20261027`, origin/main `0212e1d54`), 721 normalized / 123 raw.
- Lane commit: `b975a696d` (rebased onto Round36; originally `4fa246a9b` on Round26).
- Unstripped sha256: `dfe2e5d6ca1d1b4709d683e3780733bd7d48d8a077b99fccc86d567e74d8442b`.
- Stripped sha256: `b120fa20eea758a3ac82c0898ff4e4abe37ad549b28dd87c964d40bcd653e148`.
- Result: 724 normalized / 123 raw, 879,784 text bytes.
- On Round25 the same patches gave 723/123 (unstripped `2a6f9472…ca70`).
- Gained: 0xdd700, 0xcf510 (both in the `nearmiss` claim) and 0x1255a8 (outside this lane's range).
- Lost: none (normalized or raw).
- Runtime: 352 signed cases, 0 mismatches.
- Reproduction: two identical builds (lane build and packet `reproduce.py`).

### Reference only (not in the candidate)

- `patches/coordinate-only-reference/01-derive-origins.patch` closes coordinate-only windows 0xdf2d8 and 0xfdf20.
- It was measured on Round24 at 725/123 with no losses.
- Those windows are integration's automatic repositioning, so the patch is not claimed.

## How to continue

1. `git fetch origin`; rebase to the newest round and `git sparse-checkout add` its packet.
2. Copy `programs/pump` to `work/exp/<name>/pump`, then apply `patches/02…` and `patches/03…` with `patch -p3 -d work/exp/<name>/pump`.
3. Build under the shared slot lock with `scripts/pump_build_verified.py --workspace-layout --dependency-cache …`, or with the shared `fastbuild.py`.
4. Score with the shared `score.py` (`--baseline <round inventory>`) or `tools/measure.py`.
5. Runtime: `<test-env python> tools/runsuites.py --candidate … --source-directory <build>/source/programs/pump --out … <suites>`.

## Open leads (body-rest windows in range)

- 0xcd3d8 SetMayhemVirtualParams::try_accounts: 8,472 vs 8,504 bytes after patch 03.
  - Only the associated-token constraint region differs: the original keeps a 32-byte copy of `token_program.key()`.

## Restart after the 20:43 machine reboot (2026-10-27 ~21:45)

- Scratch (`/private/tmp/...`) was wiped. The branch survived (`e0ebe1e6e`).
  Analysis tools live in this packet's `tools/`. Builds now use the Pump session's durable harness
  `claude-pump-work/harness/fastbuild.py`: the identity recipe (Linux v1.44 `sbpf-solana-solana` target libraries),
  with the internal slot lock on the shared `claude-pump-work/locks` pool.
- Integration status: patch 02 (CurveHop operand order, 0xdd700) and the patch 03 layout windows
  (0xcf510 and 0x1255a8; integrated with `Interface<TokenInterface>` kept) are already in the Pump composite.
- Baseline now: `claude-pump-work/deliveries/integ-genuine-r37-04/src`, 806 / 165 against `base/round37/inventory.json`.
  - Fastbuild reproduced unstripped `5a13b87f89d0a18232a7b5d6a3146871cd21d75469c3fd7a0ef886cea06e911b`.
  - `runtime_valid` is true, with no stack warnings.
- Next: wait for the coordinator's confirmed slice (`targets/nearmiss.json` + a chosen set), then report only gains beyond the composite.

### Nearmiss slice check against integ-genuine-r37-04 (806/165)

Both `targets/nearmiss.json` windows are now coordinate-only in the composite. Their only differing slots are Anchor Source-line immediates; the path lengths are equal.

| Window | Function | Original lines | Candidate lines | Composite candidate |
| --- | --- | --- | --- | --- |
| 0x7e0b0 | `trade::validate_trade` | `trade_v3.rs` 149 and 150 | 75 and 76 | 0x90538 |
| 0x1091b0 | `pump_amm::accounts::GlobalConfig::try_deserialize` | `lib.rs` 83 | 66 | 0x115e40 |

- 0x7e0b0's earlier branch-order difference was already closed by nearmiss2's allow-first form.
- For 0x1091b0, the line is that of the `declare_program!(pump_amm)` invocation.
- Neither has a remaining genuine (non-coordinate) difference, so both belong to the integration session's line positioning.
