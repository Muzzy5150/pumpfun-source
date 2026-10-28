"""Write the evidence-bounded, actual-metrics R41 checkpoint description."""
from pathlib import Path
import hashlib,json,struct
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'repro/pump/main-contract-round41-20261027'
cp=json.loads((P/'CHECKPOINT.json').read_text())
assert cp['archived_recipe_reproduced'] and cp['archive_identity_freshly_compiled']
corpus_path=P/'inputs/work/parallel-main-integration/unified-main-corpus-round41.json'
assert hashlib.sha256(corpus_path.read_bytes()).hexdigest()==cp['frozen_corpus_sha256']
corpus=json.loads(corpus_path.read_text())
for group,total in corpus['counts'].items():
 rows=[r for r in corpus['suites']if r['group']==group]
 assert sum(r['cases']for r in rows)==total==cp[group+'_cases']
 assert len(rows)==len({r['name']for r in rows})==cp[group+'_suites']
assert cp['new_distinct_case_definitions']==sum(r['new_cases']for r in cp['case_addition_breakdown']['components'])
assert cp['extension_definition_retained_unchanged']
n,total=cp['normalized_windows'],cp['original_windows']
matched,size=cp['matched_text_bytes'],cp['original_text_bytes']
logs=cp['full_log_cases']+cp['additional_log_cases']
previous=json.loads((ROOT/'repro/pump/main-contract-round40-20261027/CHECKPOINT.json').read_text())
changes='\n'.join('- `'+name+'`'for name in sorted(cp['selected_source_changes']))
new_components=', '.join(r['name']+' ('+str(r['new_cases'])+')'for r in cp['case_addition_breakdown']['components'])
proof=json.loads((P/'data-order/archive-proof.json').read_text())
def data_start(path):
 raw=path.read_bytes();at=struct.unpack_from('<Q',raw,40)[0];width,count,names_i=struct.unpack_from('<HHH',raw,58)
 heads=[struct.unpack_from('<IIQQQQIIQQ',raw,at+i*width)for i in range(count)];names=heads[names_i];strings=raw[names[4]:names[4]+names[5]]
 for h in heads:
  if strings[h[0]:].split(b'\0',1)[0]==b'.data.rel.ro':return h[3]
 raise AssertionError('missing data section')
original_start=data_start(ROOT/'evidence/original/pump/deployed.so')
before_start=data_start(P/'layout-proof/baseline.so');after_start=data_start(P/'unstripped.so')
before=sum(r['candidate']-before_start==r['original']-original_start for r in proof['roles']['baseline'])
after=sum(r['candidate']-after_start==r['original']-original_start for r in proof['roles']['final'])
text=f'''# Main Pump verified checkpoint — Round41

The maintained main contract matches **{n:,} / {total:,} original function windows ({100*n/total:.1f}%)**, including **{cp['raw_windows']} raw byte-equal bodies**. Those windows cover **{matched:,} / {size:,} original text bytes ({100*matched/size:.1f}%)**. The closed direct-call subset contains {cp['closed_call_windows_without_data']} windows and excludes data references. Normalization masks specified call/address operands; it does not establish referenced data or whole-program identity. **Whole-ELF identity remains false.** These metrics measure binary coverage, not engineering work completed.

The captured-loader regression passes **{cp['full_suites']} suites / {cp['full_cases']:,} cases** and **{cp['additional_suites']} focused suites / {cp['additional_cases']:,} executions**, with **{logs:,} matching paired diagnostic-log cases**. These corpora overlap. Paired diagnostics compare structured Anchor errors, panic payloads and comparison operands, excluding source coordinates and compute usage. The separate ordered raw-log audit covers every complete recorded main invocation and requires zero non-filename differences, retaining nested CPI, event and return logs. It reports {cp['ordinary_logs']['families'].get('source_file_path_only',0):,} remaining source-filename mismatches explicitly. Every original/candidate result retains its serialized transaction bytes; signatures and main-instruction attribution are rechecked. The complete corpus contains {cp['full_cases']+cp['additional_cases']:,} paired executions. No current-chain acceptance is implied.

This round restores observed ordinary messages and ordering and corrects the ClaimCashbackV2 quote-program guard. Raw-log coverage remains bounded by the recorded inputs; source filenames are not silently normalized away.

This round adds exactly {cp['new_distinct_case_definitions']} distinct cashback quote-program guard input and retains all 18,109 paired cases from Round40, including its signed nonzero-volume SellV3 witness. The earlier reversed stored-range scheduler case remains parser-admitted; its historical reachability is still unproved. The strengthened {cp['strengthened_existing_case_definitions']}-case extension suite remains unchanged.

The selected compiler profile restores the five original TypeId bodies. Selected source changes are listed below and retain the earlier TradeEvent and scheduler corrections. Generated external-program interfaces remain compiler inputs for the main contract. All previously validated R38 corrections are retained. Source, runtime, layout and provenance claims retain their distinct evidence boundaries. The selected primary files are bound by the frozen integration plan:

{changes}

Actual window changes against Round40 are {n-previous['normalized_windows']:+d} normalized and {cp['raw_windows']-previous['raw_windows']:+d} raw. The entire previously matched normalized-window set is retained. This description is generated from final evidence and does not infer source correctness from a count gain.

The source-specific pure text recipe is preserved as `text-order.ld`. The final compiler recipe `ordered.ld` includes the bounded two-object `.data.rel.ro` ordering. The fixed Borsh Location and debug-argument table have {before}/2 original-relative starts before and {after}/2 after the selected data order. These are only the two checked objects, not a whole-data-layout metric. The proof independently finds their original owner bodies and LDDW references, verifies Location/table fields and methods, and accounts for every text/data byte, pointer, relocation, symbol and remaining file byte. There is no post-link editing, padding, or injected original code/data. The concrete original table type, complete allocation extents, remaining data layout remain unresolved. The five tracked TypeId constants now match; the complete original SDK and host recipe remain unproved.

The opt-in `linux-v1.44-sbpf` profile uses the pinned native macOS v1.44 compiler/host libraries with exactly25 SBPF target libraries from the official Linux x86_64 v1.44 archive. Per-build inventories prove that only that target-library directory changed. This is a reproducible hybrid recipe, not proof of the original SDK. Its separate external-only cache has an ordinary clean producer, fresh cached parity and producer-unavailable controls. Every main crate is compiled again; no compiled main-Pump object enters that cache.

Four final compilations reproduce both ELF hashes: initial, repeat, maintained-source and archived-source builds. Two separate identity compilations support the initial and archived data-order certificates. Archive reproduction actually builds a fresh identity from archived primary, derives a new certificate with pure `text-order.ld`, then compiles a fresh final and requires both expected ELF hashes. The original admitted certificate is preserved unchanged as provenance. The read-only verifier uses explicit bundled artifact paths; its local transformation replay is not represented as fresh admission.

```sh
python repro/pump/main-contract-round41-20261027/verify.py
python repro/pump/main-contract-round41-20261027/reproduce.py \\
  --registry-home /path/to/qualified/cargo-home \\
  --dependency-cache /path/to/qualified/external-cache \\
  --sdk /path/to/native-macos-v1.44 \\
  --target-library-directory /path/to/linux-v1.44/rust/lib/rustlib/sbpf-solana-solana/lib \\
  --output work/reproduce-main-round41
```

The reproduction creates separate sibling identity and certificate paths; `--output` remains the final build directory. The native SDK and official target libraries are external, hash-bound inputs, not bundled or downloaded by the archive. A changed cache/profile context needs its own ordinary producer and parity proof. The original executable is used for evidence/comparison only, never as compiler or linker code/data input.

[Previous maintained checkpoint: Round40](../main-contract-round40-20261027/README.md). The remaining {total-n} function windows, validation paths, data, relocations and original build provenance remain open. [Parallel work queue](../../../research/main-pump-parallel-checkpoint-20261027/REMAINING-WORK.json).
'''
(P/'README.md').write_text(text)
