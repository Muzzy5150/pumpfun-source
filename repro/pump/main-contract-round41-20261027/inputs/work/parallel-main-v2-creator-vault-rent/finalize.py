from pathlib import Path
import base64,gzip,hashlib,json,sys
from solders.transaction import Transaction
R=Path(__file__).resolve().parents[2];P=Path(__file__).parent
sys.path.insert(0,str(R/'scripts'));from pump_diagnostic_audit import audit
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(d):
 s=d.get('suites');return [x for a in s.values() for x in a] if s else d.get('cases',[])
full=json.load(open(P/'after01-full-summary.json'));focused=json.load(open(P/'after01-focused-summary.json'))
archives=[R/x['archive'] for x in full['results']+focused['results']]+[P/'after01-sweeps.json.gz',P/'after01.json.gz']
total=strict=txs=loads=0;results=[]
for path in archives:
 d=json.load(gzip.open(path,'rt'));rs=rows(d);diag=audit(d.get('suites') or {path.stem:rs});assert not diag['mismatches'];assert all(not x.get('different_fields') for x in rs)
 for row in rs:
  for side in ['original','candidate']:
   result=row[side];encoded=result.get('transaction_base64')
   if encoded:Transaction.from_bytes(base64.b64decode(encoded)).verify();txs+=1
  loads+=len(row.get('loader',[]))
 n=len(rs);total+=n;strict+=diag['log_bearing_cases'];results.append({'archive':str(path.relative_to(R)),'sha256':digest(path),'cases':n,'strict_cases':diag['log_bearing_cases'],'mismatches':0,'strict_mismatches':0})
# The old waiver probe stores its per-case loader bindings in a separate receipt.
receipt=json.load(open(P/'after01-waiver.loader.json'))
print('waiver receipt keys',list(receipt))
# Its full-schema payload is preserved for the source/build/load audit.
waiver_loads=receipt.get('loads') or receipt.get('loader_records')
if waiver_loads is None:
 for val in receipt.values():
  if isinstance(val,list) and val and isinstance(val[0],dict) and 'elf_sha256' in val[0]:waiver_loads=val;break
assert waiver_loads is not None
loads+=len(waiver_loads)
a=json.load(open(R/'work/parallel-main-integration/build-round24/normalized-inventory.json'));b=json.load(open(P/'inventory01.json'));sets={}
for label,key in [('normalized','normalized_matches'),('raw','raw_match')]:
 sa={x['start'] for x in a['windows'] if x[key]};sb={x['start'] for x in b['windows'] if x[key]};sets[label]={'gains':sorted(sb-sa),'losses':sorted(sa-sb)};assert not sets[label]['gains'] and not sets[label]['losses']
(P/'SET-COMPARISON.json').write_text(json.dumps(sets,indent=2)+'\n')
r=json.load(open(P/'DELIVERY.json'));r.update(status='frozen; all selected signed regressions passed',total_cases=total,strict_cases=strict,verified_transactions=txs,captured_main_loads=loads,regressions=results,window_sets=sets,waiver_loader_receipt='after01-waiver.loader.json',duplicates=json.load(open(P/'DUPLICATES.json')))
# Check the selected source bytes remain the exact build-bound bytes.
build=json.load(open(P/'build01/build-comparison.json'))
for f,h in r['source_files'].items():
 assert digest(P/'source01'/f)==h
 key=str((P/'source01'/f).relative_to(R));assert build['primary_source_sha256'][key]==h
assert digest(P/'build01/candidate.so')==r['candidate_sha256']
(P/'FINAL-RESULT.json').write_text(json.dumps(r,indent=2)+'\n')
m=json.load(open(P/'CLI-MANIFEST.json'));m.update(new_unique_observable_fixtures=r['duplicates']['new_unique_observable_fixtures'],prior_overlap_count=r['duplicates']['unique_prior_overlaps'],full_delivery='FINAL-RESULT.json');(P/'CLI-MANIFEST.json').write_text(json.dumps(m,indent=2)+'\n')
(P/'SEALED.md').write_text('Source01, build01 and all archived probes are frozen. The three-file SellV2 creator-vault funding patch passed108new cases plus2150previous signedcases; FINAL-RESULT.json binds source/build/load/diagnostic hashes. Original3b598 remains416B/22different slots; no byte-identity gainclaimed. The12baseline differences arefixed. Neverresume stoppedownerexperiment.\n')
print(json.dumps({k:r[k] for k in ['status','total_cases','strict_cases','verified_transactions','captured_main_loads','window_sets']},indent=2))
