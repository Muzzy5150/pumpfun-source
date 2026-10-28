# L06-904: pump-hi H11 + pump-big-lo gain01 on base/L06

**904/165/1,246,688** (L06: 899/165). The gains are exactly 0x38fc0, 0x3a7b8, 0x43ea0, 0x47e28 and 0x502f0. There are no normalized or raw losses, runtime_valid is true, and build.log has no stack-offset warnings.

| lane | commit | windows | file |
|---|---|---|---|
| pump-hi | e1f2933e2 | 0x502f0 migrate_v2 `create_pool` helper; 0x43ea0 migrate `create_pool` helper; 0x47e28 `base_token_program` | src/migrate_v2.rs, src/migrate.rs |
| pump-big-lo | 6ff2f8238 (corpus 72a31c585) | 0x38fc0 `set_creator::set`; 0x3a7b8 `set_creator::sync` | src/set_creator.rs |

- **Patch:** `source-on-L06.patch` is one diff of base/L06/pump against the composed crate. Apply it with `git apply -p1` in a fresh copy of base/L06/pump.
- **Build:** `claude-pump-work/harness/fastbuild.py`, identity recipe.
  - unstripped `1fb409bb…`
  - stripped `4e23b5ae…`
  - Both ELFs are gzipped in `elf/`, with `SHA256SUMS`.
- **Runtime:** `runtime-corpus.json` is bound to the stripped sha.
  - 43 suites ran on this build (10,448 cases).
  - tokenkeg_two_curve ran on an archived-builder build of the identical source (20 cases).
  - Total: 44/44 suites, 10,468 cases, 0 errors, 0 diagnostic mismatches.
- **Check:** `HOME=$(mktemp -d) python3 -B verify.py` (stdlib only). It checks:
  - the ELF hashes;
  - each claimed window, normalized as the scorer does, against `evidence/original/pump/deployed.so`;
  - that the gains equal the claims, and the counts are 904/165;
  - that build.log has no stack-offset warning;
  - the patch hash;
  - the runtime summary.
