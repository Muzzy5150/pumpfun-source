#!/bin/bash
# usage: build.sh <tag> [source-crate-dir] ; env SLOT=n selects workspace/target slot (default 0)
set -euo pipefail
SP=/private/tmp/claude-501/-Users-shawwalters-Documents-Codex-2026-10-24-pumpfun-source/bf960843-6806-451b-a211-62c8b228d301/scratchpad
L=$SP/lanes/pump-lo
tag=$1; SRC=${2:-$L/wt/programs/pump}; SLOT=${SLOT:-0}
TC=$HOME/.cache/solana/v1.44/platform-tools
if [ "$SLOT" = 0 ]; then W=$L/iter/source; T=$L/target; else W=$L/iter$SLOT/source; T=$L/target$SLOT; fi
if [ ! -d $T ]; then cp -c -R $L/target $T; fi
if [ ! -d $W ]; then mkdir -p $W; cp $L/iter/source/Cargo.toml $L/iter/source/Cargo.lock $W/; fi
mkdir -p $W/programs/pump
rsync -a --delete --exclude README.md $SRC/src/ $W/programs/pump/src/
rsync -a --delete --exclude README.md $SRC/recovered/ $W/programs/pump/recovered/
python3 - "$SRC/Cargo.toml" "$W/programs/pump/Cargo.toml" <<'PY'
import sys
t=open(sys.argv[1]).read(); c=t[:t.index('[profile.release]')].rstrip()+'\n'
try:
    if open(sys.argv[2]).read()==c: sys.exit(0)
except FileNotFoundError: pass
open(sys.argv[2],'w').write(c)
PY
cmp -s $SRC/Cargo.lock $W/Cargo.lock || cp $SRC/Cargo.lock $W/Cargo.lock
OUT=$L/out/builds/$tag; mkdir -p $OUT
cd $W
env RUSTC_WRAPPER=$L/wt/scripts/pump_physical_source_wrapper.py \
  PUMP_LOGICAL_REGISTRY_SRC=$L/iter/cargo-home/registry/src \
  CARGO_HOME=$L/iter/cargo-home CARGO_TARGET_DIR=$T CARGO_BUILD_JOBS=2 \
  RUSTC=$TC/rust/bin/rustc CC=$TC/llvm/bin/clang AR=$TC/llvm/bin/llvm-ar \
  OBJDUMP=$TC/llvm/bin/llvm-objdump OBJCOPY=$TC/llvm/bin/llvm-objcopy \
  CARGO_TARGET_SBF_SOLANA_SOLANA_RUSTFLAGS=-Zremap-cwd-prefix= \
  python3 $SP/sbf_lock.py --slots 6 --name sbf -- \
  $TC/rust/bin/cargo build --manifest-path $W/programs/pump/Cargo.toml --release --target sbf-solana-solana --locked --offline > $OUT/build.log 2>&1 || { grep -E "^error|^warning: unused" -A6 $OUT/build.log | head -60; exit 1; }
cp $T/sbf-solana-solana/release/pump_recovered.so $OUT/unstripped.so
$TC/llvm/bin/llvm-objcopy --strip-all $OUT/unstripped.so $OUT/candidate.so
shasum -a 256 $OUT/candidate.so $OUT/unstripped.so | sed "s#$OUT/##"
grep -E "Finished" $OUT/build.log | tail -1
python3 $L/tools/measure.py $L/wt ${PKT:-repro/pump/main-contract-round25-20261027} $OUT/unstripped.so $OUT/measure.json | python3 -c "import json,sys; d=json.load(sys.stdin); print({k:d[k] for k in ['normalized','raw','matched_text_bytes','normalized_gains','normalized_losses','raw_gains','raw_losses']})"
