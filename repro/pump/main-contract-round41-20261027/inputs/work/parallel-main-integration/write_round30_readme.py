"""Write the evidence-bounded Round30 checkpoint description."""
from pathlib import Path
import json
ROOT = Path(__file__).resolve().parents[2]
P = ROOT / 'repro/pump/main-contract-round30-20261027'
cp = json.loads((P / 'CHECKPOINT.json').read_text())
n, total = cp['normalized_windows'], cp['original_windows']
matched, size = cp['matched_text_bytes'], cp['original_text_bytes']
logs = cp['full_log_cases'] + cp['additional_log_cases']
text = f'''# Main Pump verified checkpoint — Round30

The maintained main contract matches **{n:,} / {total:,} original function windows ({100*n/total:.1f}%)**, including **{cp['raw_windows']} raw byte-equal bodies**. Those windows cover **{matched:,} / {size:,} original text bytes ({100*matched/size:.1f}%)**. The closed direct-call subset contains {cp['closed_call_windows_without_data']} windows and excludes data references. Normalization masks specified call/address operands; it does not establish referenced data or whole-program identity. **Whole-ELF identity remains false.** These figures measure binary coverage, not the fraction of engineering work completed.

The captured-loader regression passes **{cp['full_suites']} suites / {cp['full_cases']:,} cases** and **{cp['additional_suites']} focused suites / {cp['additional_cases']:,} executions**, with **{logs:,} matching paired diagnostic-log cases**. These corpora overlap. Diagnostics exclude source coordinates and compute usage. Tests use captured upgradeable-loader dimensions in local VMs. The verifier requires serialized transaction bytes for every original/candidate result and rechecks signatures and instruction attribution. No current-chain acceptance is implied.

This checkpoint recovers the native transfer-fee and inverse-fee helpers, including their 24-byte fee carrier, and the raw-equal six-account ATA cleanup helper. It preserves native extra-curve account handling and all instruction metadata. The only dependency change pins solana-program-entrypoint to 2.2.1; all 254 other package records are unchanged. That source version restores 17 original source-location bytes without fabricated line padding.

The qualified linker recipe is rederived from this exact source and dependency graph. Every original/candidate result still retains signed transaction bytes. The standalone verifier recomputes allocated-image translation from archived maps and the default-layout candidate; unallocated symbol data and some ELF header fields remain outside that proof.

Every case's paired CPI invocation sequence is also audited, including failed transactions. One bounded queue schedules both corpora and keeps per-suite results for verified resumption; the preserved queue state records any retry history.

The changed dependency graph was rebuilt with no cached artifacts through an ordinary physical-wrapper producer, then reproduced by a separately fresh cache consumer. Both matched hashes are retained, and the producer target was absent during independent consumer checks. Only verified external dependencies are reused; each main contract is freshly compiled.

Four independent fresh main compilations reproduce both final ELF hashes: the initial combined build, repeat, maintained source and archived source. No compiled main-Pump object is cached. Original executable bytes are never compiler inputs.

The loader optimization retains full actual ProgramData byte equality on every load while caching immutable expected images and hashes. Its earlier controlled benchmark and corruption controls remain applicable; full-suite timings depend on the workload and concurrent jobs.

```sh
python repro/pump/main-contract-round30-20261027/verify.py
python repro/pump/main-contract-round30-20261027/reproduce.py --registry-home ~/.cargo --output work/reproduce-main-round30
```

[Previous maintained checkpoint: Round29](../main-contract-round29-20261027/README.md). The remaining {total-n} function windows, validation paths, data, relocations and original build provenance are unresolved. [Parallel work queue](../../../research/main-pump-parallel-checkpoint-20261027/REMAINING-WORK.json).
'''
(P / 'README.md').write_text(text)
