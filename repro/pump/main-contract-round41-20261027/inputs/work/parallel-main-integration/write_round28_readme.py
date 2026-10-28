"""Write the evidence-bounded Round28 checkpoint description."""
from pathlib import Path
import json
ROOT = Path(__file__).resolve().parents[2]
P = ROOT / 'repro/pump/main-contract-round28-20261027'
cp = json.loads((P / 'CHECKPOINT.json').read_text())
n, total = cp['normalized_windows'], cp['original_windows']
matched, size = cp['matched_text_bytes'], cp['original_text_bytes']
logs = cp['full_log_cases'] + cp['additional_log_cases']
text = f'''# Main Pump verified checkpoint — Round28

The maintained main contract matches **{n:,} / {total:,} original function windows ({100*n/total:.1f}%)**, including **{cp['raw_windows']} raw byte-equal bodies**. Those windows cover **{matched:,} / {size:,} original text bytes ({100*matched/size:.1f}%)**. The closed direct-call subset contains {cp['closed_call_windows_without_data']} windows and excludes data references. Normalization masks specified call/address operands; it does not establish referenced data or whole-program identity. **Whole-ELF identity remains false.** These figures measure binary coverage, not the fraction of engineering work completed.

The captured-loader regression passes **{cp['full_suites']} suites / {cp['full_cases']:,} cases** and **{cp['additional_suites']} focused suites / {cp['additional_cases']:,} executions**, with **{logs:,} matching paired diagnostic-log cases**. These corpora overlap. Diagnostics exclude source coordinates and compute usage. Tests use captured upgradeable-loader dimensions in local VMs. The verifier requires serialized transaction bytes for every original/candidate result and rechecks signatures and instruction attribution. No current-chain acceptance is implied.

This checkpoint extends Round27 with main-owned MigrateV2 token-extension parsing. The required token-account size recognizes PausableConfig, and the later transfer-fee query retains raw extension tags. This corrects six captured migrations that succeeded in the original program but failed in the prior reconstruction. The dependency programs are unchanged.

The new matrix adds 20 signed migration executions. Complete serialized transaction retention remains mandatory for every original/candidate result. Source and build provenance, unmatched bodies and complete data/relocation identity remain unfinished.

Every case's paired CPI invocation sequence is also audited, including failed transactions. One bounded queue schedules both corpora and keeps per-suite results for verified resumption; the preserved queue state records any retry history.

The direct import of the already-locked `spl-type-length-value` 0.7.0 trait changes only the main package's direct dependency declaration and imports. The 254 external lock records are unchanged. Its dependency graph was rebuilt without a cache, then both producer ELFs were reproduced through a new verified external-only cache. The producer target was absent during the final isolated main build. The package preserves those receipts and binaries; old-cache binary identity is not claimed.

Four independent fresh main compilations reproduce both final ELF hashes: the initial combined build, repeat, maintained source and archived source. No compiled main-Pump object is cached. Original executable bytes are never compiler inputs.

The loader optimization retains full actual ProgramData byte equality on every load while caching immutable expected images and hashes. Its earlier controlled benchmark and corruption controls remain applicable; full-suite timings depend on the workload and concurrent jobs.

```sh
python repro/pump/main-contract-round28-20261027/verify.py
python repro/pump/main-contract-round28-20261027/reproduce.py --registry-home ~/.cargo --output work/reproduce-main-round28
```

[Previous maintained checkpoint: Round27](../main-contract-round27-20261027/README.md). The remaining {total-n} function windows, validation paths, data, relocations and original build provenance are unresolved. [Parallel work queue](../../../research/main-pump-parallel-checkpoint-20261027/REMAINING-WORK.json).
'''
(P / 'README.md').write_text(text)
