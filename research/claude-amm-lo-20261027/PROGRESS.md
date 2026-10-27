# Lane amm-lo progress (PumpSwap, original windows 0x2288 .. 0x3a5a0)

Continuation notes for another agent. Newest entries last.

## Setup
- Worktree: `SP/lanes/amm-lo/wt` (branch `claude/amm-lo-20261027`), SP = scratchpad root in LANE-RULES.md.
- Current baseline: `repro/pump_amm/account-context-recovery-20261027`, candidate `badc9498…`,
  623/785 normalized, 128 raw, 162 unmatched (Linux v1.44 SBPF); native build of its canonical source = 618/119.
  (First base was native-fee-cpi `a4b978ee…` 599/125.) My range had 62 unmatched windows at 623.
- Native fast loop: `SP/lanes/amm-lo/out/tools/native_build.sh <src-root> <new-out-dir>`
  (macOS platform-tools v1.44, sbpf-solana-solana, frontier workspace recipe; ~20 s root rebuild).
  Native baseline = 594 normalized / 118 raw. The only normalized differences from Linux are the five
  TypeId windows 0xa9b0, 0xf8ca0, 0x1016a8, 0x10efd8, 0x111b38 (sysroot-owned); none in this range.
- Linux confirmation: `SP/lanes/amm-lo/out/tools/linux_build.py --source-root <tree> --output <dir>`
  (holds sbf + podman locks, 2 CPU / 3 GB, lane-owned clones of the frontier cargo home and target cache
  mounted at the frontier's container paths so all 732 dependency artifacts stay fresh).
- Measurement: `repro/pump_amm/focused-diagnostics-20261026/measure.py` (needs sparse dir
  `repro/pump_amm/claim-self-transfer-v144`). Diff two measurements with `out/tools/cmpm.py`.
- Codex in-flight (skip): curve math 0x11e70/0x123a0/0x13190 etc. (amm-curve-math-next), create handler
  (amm-mint-order-audit), legacy sell/pool-v2 lookup (amm-pool-v2-lookup-next), V2 trade (buyback validator),
  incentives. Codex's next integration (amm-account-fee-final, 612) already gains 0x18530, 0x1bdb0, 0x89d0.

## Gains — re-measured on 623 (`results/linux-rebased-623`, candidate a7aa6bcd…, symbols c1c55d0e…)
623/128/162 -> 648/128/137 (normalized/raw/unmatched); +25 normalized, +24,616 original text bytes;
no normalized or raw loss; none of the 25 overlaps the 623 recovery (`gain-vs-623.json`).
Runtime: 25 suites / 17,462 cases / 0 mismatches. ELFs, SHA256SUMS and measure JSON are in the packet.
Closed windows (skip these):
- 0x17960 disable (code shape: per-field flag updates through `global_config`, borrowed event)
- 0x1b510 0x1b7c0 0x1bb00 toggles (bodies moved to instructions/admin/toggle_*.rs, guards at 21/14/17)
- 0x31710 0x31918 0x31b20 0x31d28 0x31f30 0x32138 0x32340 0x32548 deposit closures (whitespace placement)
- 0x34370 0x34578 0x34780 0x34988 0x34b90 0x34d98 0x34fa0 withdraw closures (whitespace placement)
- 0x37150 get_buyback_accounts, 0x39d80 0x39f88 0x3a190 0x3a398 buy closures, 0xaf3b0 LegacyBuy parser
  (legacy_buy.rs -> instructions/swap/buy.rs, `use instructions::swap::buy as legacy_buy;`, placement 116/121/133/387-404)
Branch commit: see `git log claude/amm-lo-20261027` (program changes only; packet evidence in the follow-up commit).

## Status / next (as of the 648 checkpoint)
- In progress: deposit body 0x2fb38 (ratio .917) — tried `owner == a.token_program.key()` (no gain alone);
  remaining: late `ctx.bumps` load, base/quote reserve load order, shared error-return block.
- Not closed (see README residuals): update_buyback_config 0x1c890 (stack-slot order only),
  0x22c80 boost closure (needs boost.rs+boost_burn.rs merged into instructions/boost.rs),
  create_pool 0x2e260/0x2e468 (needs create.rs -> instructions/create_pool.rs; 0x2e260 also needs the
  TooLittlePoolTokenLiquidity check as an ok_or_else closure), set_reserved_fee_recipients 0x19138 + 0x2288/0xc5d0
  (original performs per-recipient rent checks the reconstruction lacks).
