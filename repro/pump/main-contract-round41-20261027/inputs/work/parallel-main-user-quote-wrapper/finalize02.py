from pathlib import Path
import difflib,gzip,hashlib,importlib.util,json,re,sys
P=Path(__file__).resolve().parent;R=P.parents[1]
sys.path.insert(0,str(R/'scripts'));from pump_diagnostic_audit import audit
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 b=p.read_bytes();return json.loads(gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b)
state=read(P/'runtime-state02.json');assert len(state)==19 and all(x['returncode']==0 for x in state.values())
receipts={k:read(Path(v['output']))for k,v in state.items()};counts={};invokes={}
for name,j in receipts.items():
 assert not j.get('mismatches'),name;counts[name]=j['case_count'];bad=[]
 for i,row in enumerate(j['cases']):
  assert not row.get('mismatches')and row.get('match',True),(name,i)
  o,n=row['original'],row['candidate'];verified=lambda x:x.get('signature_verified',x.get('signatures_verified',x.get('verified_signature_count',0)>0))
  assert verified(o)and verified(n),(name,i,'signature');assert o['transaction_base64']==n['transaction_base64'],(name,i,'transaction')
  selected=lambda x:[s for s in x.get('logs',[])if re.match(r'^Program [1-9A-HJ-NP-Za-km-z]+ (?:invoke \[|success$|failed:)',s)]
  if selected(o)!=selected(n):bad.append(i)
 assert not bad,(name,bad);invokes[name]={'cases':j['case_count'],'mismatches':bad}
diag=audit(receipts);assert not diag['mismatches'];(P/'diagnostics02.json').write_text(json.dumps(diag,indent=2)+'\n');(P/'invocations02.json').write_text(json.dumps(invokes,indent=2)+'\n')
inv=read(P/'inventory02.json');base_path=R/'work/parallel-main-integration/build-round30-identity/normalized-inventory.json';base=read(base_path)
assert inv['counts']=={'total':1035,'raw':124,'normalized':730,'unmatched':305}
sets=lambda j,k:{r['start']for r in j['windows']if r[k]}
gains={}
for key in ['normalized_matches','raw_match']:
 x,y=sets(base,key),sets(inv,key);gains[key]={'gains':[hex(x)for x in sorted(y-x)],'losses':[hex(x)for x in sorted(x-y)]}
assert gains=={'normalized_matches':{'gains':['0x8df98','0x8e450','0x97930','0x97bf0'],'losses':[]},'raw_match':{'gains':[],'losses':[]}}
(P/'window-gains02.json').write_text(json.dumps({'baseline':str(base_path.relative_to(R)),'baseline_sha256':sha(base_path),'baseline_counts':base['counts'],'candidate_counts':inv['counts'],'sets':gains},indent=2)+'\n')
by={r['start']:r for r in inv['windows']};proof=[]
for name in ['wrapper02.json','native02.json']:
 c=read(P/name);candidate=c['candidates'][0];assert candidate['normalized_equal']
 cc={r['offset']:r for r in candidate['operands']}
 for op in c['original_operands']:
  if op['kind']!='direct-call':continue
  cp=cc[op['offset']];assert cp['kind']=='direct-call'
  matches=[m for m in by[op['target']]['normalized_matches']if m['start']==cp['target']];assert matches,(op,cp)
  proof.append({'source_original':hex(c['original_start']),'source_candidate':hex(candidate['start']),'offset':op['offset'],'original_target':hex(op['target']),'candidate_target':hex(cp['target']),'bytes':by[op['target']]['bytes'],'matching_symbols':[m['symbol']for m in matches]})
(P/'callees02.json').write_text(json.dumps(proof,indent=2)+'\n')
spec=importlib.util.spec_from_file_location('image_audit',R/'work/parallel-main-data-layout-proof/audit.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
o=mod.Image(R/'evidence/original/pump/deployed.so');c=mod.Image(P/'build02/unstripped.so');wrapper=read(P/'wrapper02.json');op=[q for q in wrapper['original_operands']if q['kind']=='elf-pointer'];cp={q['offset']:q for q in wrapper['candidates'][0]['operands']if q['kind']=='elf-pointer'};locations=[]
for q in op:
 sides=[]
 for image,address in [(o,q['value']),(c,cp[q['offset']]['value'])]:
  pointer=image.pointer(address);length=image.word(address+8);line=int.from_bytes(image.read(address+16,4),'little');column=int.from_bytes(image.read(address+20,4),'little');sides.append({'address':hex(address),'path':image.string(pointer['target'],length)['utf8'],'line':line,'column':column,'pointer':pointer})
 locations.append({'wrapper_instruction_offset':q['offset'],'role':'24-byte Location payload passed to Option::unwrap_failed; allocation extent and historical type identity unproved','original':sides[0],'candidate':sides[1],'equal_path_line_column':all(sides[0][k]==sides[1][k]for k in ['path','line','column'])})
(P/'locations02.json').write_text(json.dumps(locations,indent=2)+'\n')
build=read(P/'build02/build-comparison.json');assert build['returncode']==0 and build['source_unchanged']
source=P/'source02';baseline=R/'work/parallel-main-integration/round30-source/programs/pump';changed=['src/buy_v2.rs','src/trade_v3.rs','src/user_quote_payments.rs'];patch=[]
for f in changed:
 old=baseline/f;new=source/f
 patch.extend(difflib.unified_diff(old.read_text().splitlines(True)if old.exists()else[],new.read_text().splitlines(True),fromfile='a/'+f if old.exists()else'/dev/null',tofile='b/'+f))
(P/'user-quote-wrapper02.patch').write_text(''.join(patch))
sources={str(f.relative_to(source)):sha(f)for f in sorted(source.rglob('*'))if f.is_file()}
(P/'SOURCE-MANIFEST02.json').write_text(json.dumps(sources,indent=2)+'\n')
result={'status':'validated isolated delivery for parent composition','baseline':'frozen Round30 source, identity linker order for full set comparison','source':'source02','candidate_sha256':sha(P/'build02/candidate.so'),'unstripped_sha256':sha(P/'build02/unstripped.so'),'build_receipt_sha256':sha(P/'build02/build-comparison.json'),'source_hashes':{f:sha(source/f)for f in changed},'patch_sha256':sha(P/'user-quote-wrapper02.patch'),'inventory':inv['counts'],'gains_vs_R30_identity':gains,'reconstructed_bodies':[{'original':'0x97930','bytes':704,'candidate':hex(read(P/'wrapper02.json')['candidates'][0]['start'])},{'original':'0x8df98','bytes':1208,'candidate':hex(read(P/'native02.json')['candidates'][0]['start'])}],'duplicate_normalized_windows':['0x97bf0 matches0x97930 except masked operands; its distinct native callee0x8d108 is not reconstructed here.','0x8e450 matches0x8df98 except masked operands; its original migration callers are not refactored here.'],'callees':proof,'runtime':{'counts':counts,'total':sum(counts.values()),'all_signatures_verified':True,'transaction_bytes_identical':True,'fixture_mismatches':[],'diagnostic_mismatches':diag['mismatches'],'exact_invocation_sequences':True},'limits':['Full ELF equality remains false.','Two Location payloads retain different source path/line/column; no coordinate padding was used.','Only V2/V3 pool payment callsites were refactored; MultiHop direct native caller, migration callers, and distinct fee/recipient wrappers remain separate.','R30 identity-link raw set is124. Optional ordered-link R30 result137 is a separate layout baseline and not directly compared here.','Parent composite still requires full regression/build qualification.'],'control01':{'status':'passing but native ABI not reconstructed; superseded by source02','runtime_cases':1055,'wrapper_bytes':704,'wrapper_normalized_equal':True,'native_bytes':1192,'native_normalized_equal':False}}
(P/'RESULT02.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'counts':counts,'total':sum(counts.values()),'candidate':result['candidate_sha256'],'unstripped':result['unstripped_sha256'],'gains':gains},indent=2))
