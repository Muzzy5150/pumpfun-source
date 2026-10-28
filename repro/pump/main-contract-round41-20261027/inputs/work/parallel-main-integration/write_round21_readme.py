"""Write the evidence-bounded Round21 checkpoint description."""
from pathlib import Path
import json
ROOT = Path(__file__).resolve().parents[2]
P = ROOT / 'repro/pump/main-contract-round21-20261027'
cp = json.loads((P / 'CHECKPOINT.json').read_text())
n, total = cp['normalized_windows'], cp['original_windows']
matched, size = cp['matched_text_bytes'], cp['original_text_bytes']
logs = cp['full_log_cases'] + cp['additional_log_cases']
text = f'''# Main Pump verified checkpoint — Round21

The maintained main contract matches **{n:,} / {total:,} original function windows ({100*n/total:.1f}%)**, including **{cp['raw_windows']} raw byte-equal bodies**. Those windows cover **{matched:,} / {size:,} original text bytes ({100*matched/size:.1f}%)**. The closed direct-call subset contains {cp['closed_call_windows_without_data']} windows and excludes data references. Normalization masks specified call/address operands; it does not establish referenced data or whole-program identity. **Whole-ELF identity remains false.** These figures measure binary coverage, not the fraction of engineering work completed.

The captured-loader regression passes **{cp['full_suites']} suites / {cp['full_cases']:,} cases** and **{cp['additional_suites']} focused suites / {cp['additional_cases']:,} executions**, with **{logs:,} matching paired diagnostic-log cases**. These corpora overlap. Diagnostics exclude source coordinates and compute usage. Transactions use normal signatures and captured upgradeable-loader dimensions in local VMs; no current-chain acceptance is implied.

This checkpoint extends Round20 with the actual VariableLenPack metadata-size getter and checked size additions in CreateV2, an exact shared SellV2/SellV3 base-token transfer helper, and the original BuyV2 payment/panic order. Sixty-four new payment-boundary cases fix fourteen earlier differences in panic text and pre-panic inner instructions. The separate creation and transfer prototypes were tested before integration; this package revalidates the full composed source.

A host file-handle exhaustion interrupted the initial corpus run. Completed suites were retained only with matching candidate and explicit harness hashes; unbound or missing results were rerun, ending with one worker after a second host interruption. Initial failure evidence and the resume proof are preserved in this package.

The direct import of the already-locked `spl-type-length-value` 0.7.0 trait changes only the main package's direct dependency declaration and imports. The 254 external lock records are unchanged. Its dependency graph was rebuilt without a cache, then both producer ELFs were reproduced through a new verified external-only cache. The producer target was absent during the final isolated main build. The package preserves those receipts and binaries; old-cache binary identity is not claimed.

Four independent fresh main compilations reproduce both final ELF hashes: the initial combined build, repeat, maintained source and archived source. No compiled main-Pump object is cached. Original executable bytes are never compiler inputs.

The loader optimization retains full actual ProgramData byte equality on every load while caching immutable expected images and hashes. Its earlier controlled benchmark and corruption controls remain applicable; full-suite timings depend on the workload and concurrent jobs.

```sh
python repro/pump/main-contract-round21-20261027/verify.py
python repro/pump/main-contract-round21-20261027/reproduce.py --registry-home ~/.cargo --output work/reproduce-main-round21
```

[Previous maintained checkpoint: Round20](../main-contract-round20-20261027/README.md). The remaining {total-n} function windows, validation paths, data, relocations and original build provenance are unresolved. [Parallel work queue](../../../research/main-pump-parallel-checkpoint-20261027/REMAINING-WORK.json).
'''
(P / 'README.md').write_text(text)
