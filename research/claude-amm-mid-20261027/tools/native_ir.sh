#!/bin/bash
# Diagnostic only: emit optimized LLVM IR (and link) for the root crate of a staged workspace.
# usage: native_ir.sh <staged-workspace> <out.ll>
set -euo pipefail
SP=/private/tmp/claude-501/-Users-shawwalters-Documents-Codex-2026-10-24-pumpfun-source/bf960843-6806-451b-a211-62c8b228d301/scratchpad
L=$SP/lanes/amm-mid
SRC=$(cd "$1" && pwd); OUTLL=$(cd "$(dirname "$2")" && pwd)/$(basename "$2")
TC=$HOME/.cache/solana/v1.44/platform-tools
cd "$SRC"
python3 $SP/sbf_lock.py --slots 6 --name sbf -- env -u RUSTFLAGS -u CARGO_ENCODED_RUSTFLAGS \
  CARGO_HOME=$L/cargo-home CARGO_TARGET_DIR=${TGT:-$L/target/trace} RUSTC=$TC/rust/bin/rustc \
  CARGO_TARGET_SBPF_SOLANA_SOLANA_RUSTFLAGS=' -Zremap-cwd-prefix=' \
  $TC/rust/bin/cargo rustc --release --target sbpf-solana-solana --lib -p pump-amm-recovered \
  --manifest-path "$SRC/Cargo.toml" --locked --offline -- --emit=llvm-ir,link > "$OUTLL.log" 2>&1 || { tail -20 "$OUTLL.log"; exit 1; }
cp ${TGT:-$L/target/trace}/sbpf-solana-solana/release/deps/pump_amm_recovered.ll "$OUTLL"
ls -la "$OUTLL"
