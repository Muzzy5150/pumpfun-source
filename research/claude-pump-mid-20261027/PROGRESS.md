# pump-mid lane progress (harvest log and continuation notes)

Lane range: original windows 0x65eb0 … 0xfdf20, restricted to the integration session's
`targets/body-rest.json` claim (66 windows / 211,800 bytes at Round25).
Coordinate-only, nearmiss, identity and libinst families belong to the "Main pump contract completion" session.

## Harvest entries

### Gain 1 — patches 02, 03 (measured on Round25, committed on Round26)

- Base round: Round26 (`repro/pump/main-contract-round26-20261027`, origin/main `0212e1d54`), 721 normalized / 123 raw.
- Lane commit: `4fa246a9bb7d0aba098af73ca0f484ac4d1a5310`.
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
