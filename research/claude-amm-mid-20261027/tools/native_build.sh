#!/bin/bash
# Native macOS v1.44 SBPF build of a staged AMM workspace (iteration only; finals use Linux recipe).
# usage: native_build.sh <staged-workspace-dir> <out-dir>
set -euo pipefail
SP=/private/tmp/claude-501/-Users-shawwalters-Documents-Codex-2026-10-24-pumpfun-source/bf960843-6806-451b-a211-62c8b228d301/scratchpad
L=$SP/lanes/amm-mid
SRC=$(cd "$1" && pwd); OUT=$2
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
TC=$HOME/.cache/solana/v1.44/platform-tools
cd "$SRC"
python3 $SP/sbf_lock.py --slots 6 --name sbf -- env -u RUSTFLAGS -u CARGO_ENCODED_RUSTFLAGS \
  CARGO_HOME=$L/cargo-home CARGO_TARGET_DIR=${TGT:-$L/target/native} \
  RUSTC=$TC/rust/bin/rustc RUSTDOC=$TC/rust/bin/rustdoc CC=$TC/llvm/bin/clang AR=$TC/llvm/bin/llvm-ar \
  CARGO_TARGET_SBPF_SOLANA_SOLANA_RUSTFLAGS=' -Zremap-cwd-prefix=' CARGO_BUILD_JOBS=4 \
  $TC/rust/bin/cargo build --release --target sbpf-solana-solana --manifest-path "$SRC/Cargo.toml" --locked --offline > "$OUT/build.log" 2>&1 || { tail -30 "$OUT/build.log"; exit 1; }
cp ${TGT:-$L/target/native}/sbpf-solana-solana/release/pump_amm_recovered.so "$OUT/unstripped.so"
$HOME/.cache/solana/v1.52/platform-tools/llvm/bin/llvm-objcopy --strip-all "$OUT/unstripped.so" "$OUT/candidate.so"
shasum -a 256 "$OUT/candidate.so" "$OUT/unstripped.so"
