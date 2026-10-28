from pathlib import Path
import gzip,hashlib,json,sys
R=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent;sys.path.insert(0,str(R/'scripts'));import pump_create_quote_differential as old
read=lambda p:json.loads(gzip.decompress(p.read_bytes())if p.read_bytes()[:2]==b'\x1f\x8b'else p.read_bytes())
def key(c):
 d={k:v for k,v in c.items()if k!='case'};d.setdefault('instruction','create')
 for empty in ['quote_extensions','mutations','global_patches']:
  if empty in d and not d[empty]:d.pop(empty)
 for k,v in [('quote_token22',False),('quote_whitelisted',True)]:
  if d.get(k)==v:d.pop(k)
 return json.dumps(d,sort_keys=True,separators=(',',':'))
seen={key(c):'public_create_quote'for c in old.cases()};old26=read(R/'work/parallel-main-create-extension-validation/before.json.gz')['cases']
for r in old26:seen[key(r['case'])]='accepted_quote_tlv26'
kept=[];overlap=[];groups={}
for report,name in [('policy01.json.gz','boundary107'),('gate01.json.gz','gate32')]:
 entries=read(W/report)['cases'];groups[name]={'raw_count':len(entries),'new_count':0,'overlap_count':0}
 for r in entries:
  c=r['case'];k=key(c)
  if k in seen:overlap.append({'group':name,'case':c['case'],'same_effective_input_as':seen[k]});groups[name]['overlap_count']+=1
  else:seen[k]=name+':'+c['case'];kept.append(c);groups[name]['new_count']+=1
(W/'incremental-cases.json').write_text(json.dumps(kept,indent=2)+'\n');(W/'DEDUPLICATION.json').write_text(json.dumps({'scope':'Exact effective fixture-argument deduplication against public297 CreateV2/quote cases, accepted26 TLV cases, then within combined107+32 inputs. Names removed; empty optional collections, default false quote_token22 / true quote_whitelisted normalized. This does not claim non-overlap against every other distinct harness/context in the global corpus.','groups':groups,'kept_count':len(kept),'overlaps':overlap,'case_sha256':hashlib.sha256((W/'incremental-cases.json').read_bytes()).hexdigest()},indent=2)+'\n');print(groups,len(kept))
s=(W/'probe_program_gate.py').read_text();a=s.index("pump='pumpCmX");b=s.index('inputs=[',a);s=s[:a]+"defs=W/'incremental-cases.json';cases=json.loads(defs.read_text())\n"+s[b:];s=s.replace('inputs=[Path(__file__),','inputs=[defs,Path(__file__),');s=s.replace("'Actual CreateV2 scanner invocation gate: token program versus observed literal quote-mint bypass. Normally signed identical transactions and captured dependencies.'","'Incremental CreateV2 quote-admission cases after exact input deduplication; normal signed transactions and captured dependencies.'")
(W/'probe_incremental.py').write_text(s);(W/'incremental-manifest.json').write_text(json.dumps([{'name':'quote_admission_incremental','script':str((W/'probe_incremental.py').relative_to(R)),'count':len(kept)}],indent=2)+'\n')
manifest=json.loads((R/'work/parallel-main-create-extension-validation/manifest.json').read_text());manifest.extend([{'name':'quote_policy_boundary107','script':str((W/'probe_policy_boundaries.py').relative_to(R)),'count':107},{'name':'quote_program_mint_gate32','script':str((W/'probe_program_gate.py').relative_to(R)),'count':32}]);(W/'validation-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
