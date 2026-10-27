#!/bin/bash
# usage: native_build.sh <source-root containing programs/pump-amm> <out-dir (new)>
# Native macOS v1.44 SBPF build of the AMM via the frontier's explicit workspace recipe.
set -euo pipefail
SP=/private/tmp/claude-501/-Users-shawwalters-Documents-Codex-2026-10-24-pumpfun-source/bf960843-6806-451b-a211-62c8b228d301/scratchpad
L=$SP/lanes/amm-lo
SRC=$(cd "$1" && pwd); OUT=$2
[ -e "$OUT" ] && { echo "output exists: $OUT"; exit 2; }
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
RECIPE=$L/wt/repro/pump_amm/account-context-recovery-20261027/workspace_recipe_v2.py
python3 -B "$RECIPE" stage --source-root "$SRC" --output "$OUT/ws" > "$OUT/stage.json"
TC=$HOME/.cache/solana/v1.44/platform-tools
STRIP=$HOME/.cache/solana/v1.52/platform-tools/llvm/bin/llvm-objcopy
TGT=${TARGET_DIR:-$L/target/native}
cd "$OUT/ws"
set +e
env -u RUSTFLAGS -u CARGO_ENCODED_RUSTFLAGS \
  CARGO_HOME=$L/cargo-home CARGO_TARGET_DIR=$TGT \
  RUSTC=$TC/rust/bin/rustc RUSTDOC=$TC/rust/bin/rustdoc CC=$TC/llvm/bin/clang AR=$TC/llvm/bin/llvm-ar \
  CARGO_TARGET_SBPF_SOLANA_SOLANA_RUSTFLAGS=' -Zremap-cwd-prefix=' CARGO_BUILD_JOBS=${JOBS:-4} \
  python3 $SP/sbf_lock.py --slots 6 --name sbf -- \
  $TC/rust/bin/cargo build --release --target sbpf-solana-solana --manifest-path "$OUT/ws/Cargo.toml" --locked --offline > "$OUT/build.log" 2>&1
rc=$?
set -e
if [ $rc -ne 0 ]; then echo "BUILD FAILED rc=$rc"; grep -E "^error|^warning: unused" -A5 "$OUT/build.log" | head -60; exit $rc; fi
cp "$TGT/sbpf-solana-solana/release/pump_amm_recovered.so" "$OUT/unstripped.so"
"$STRIP" --strip-all "$OUT/unstripped.so" "$OUT/candidate.so"
shasum -a 256 "$OUT/candidate.so" "$OUT/unstripped.so"
cd $L/wt
python3 repro/pump_amm/focused-diagnostics-20261026/measure.py --candidate "$OUT/candidate.so" --symbols "$OUT/unstripped.so" --output "$OUT/measure.json" | grep -E '"(raw_matches|normalized_matches|unmatched)"'
