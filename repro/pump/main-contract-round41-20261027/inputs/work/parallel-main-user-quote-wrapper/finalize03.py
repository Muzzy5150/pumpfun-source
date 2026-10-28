from pathlib import Path
import difflib,gzip,hashlib,importlib.util,json,re,sys
P=Path(__file__).resolve().parent;R=P.parents[1]
sys.path.insert(0,str(R/'scripts'));from pump_diagnostic_audit import audit
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 b=p.read_bytes();return json.loads(gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b)
state=read(P/'runtime-state03.json');assert len(state)==19 and all(x['returncode']==0 for x in state.values())
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
diag=audit(receipts);assert not diag['mismatches'];(P/'diagnostics03.json').write_text(json.dumps(diag,indent=2)+'\n');(P/'invocations03.json').write_text(json.dumps(invokes,indent=2)+'\n')
inv=read(P/'inventory03.json');base=read(P/'inventory02.json');assert inv['counts']==base['counts']=={'total':1035,'raw':124,'normalized':730,'unmatched':305}
sets=lambda j,k:{r['start']for r in j['windows']if r[k]}
gains={}
for key in ['normalized_matches','raw_match']:
 x,y=sets(base,key),sets(inv,key);gains[key]={'gains':[hex(x)for x in sorted(y-x)],'losses':[hex(x)for x in sorted(x-y)]}
assert all(not x['gains']and not x['losses']for x in gains.values())
(P/'window-gains03.json').write_text(json.dumps(gains,indent=2)+'\n')
by={r['start']:r for r in inv['windows']};proof=[]
for name in ['wrapper03.json','native03.json']:
 c=read(P/name);candidate=c['candidates'][0];assert candidate['normalized_equal']
 cc={r['offset']:r for r in candidate['operands']}
 for op in c['original_operands']:
  if op['kind']!='direct-call':continue
  cp=cc[op['offset']];assert cp['kind']=='direct-call';matches=[m for m in by[op['target']]['normalized_matches']if m['start']==cp['target']];assert matches
  proof.append({'source_original':hex(c['original_start']),'source_candidate':hex(candidate['start']),'offset':op['offset'],'original_target':hex(op['target']),'candidate_target':hex(cp['target']),'bytes':by[op['target']]['bytes'],'matching_symbols':[m['symbol']for m in matches]})
(P/'callees03.json').write_text(json.dumps(proof,indent=2)+'\n')
spec=importlib.util.spec_from_file_location('image_audit',R/'work/parallel-main-data-layout-proof/audit.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
o=mod.Image(R/'evidence/original/pump/deployed.so');c=mod.Image(P/'build03/unstripped.so');wrapper=read(P/'wrapper03.json');op=[q for q in wrapper['original_operands']if q['kind']=='elf-pointer'];cp={q['offset']:q for q in wrapper['candidates'][0]['operands']if q['kind']=='elf-pointer'};locations=[]
for q in op:
 sides=[]
 for image,address in [(o,q['value']),(c,cp[q['offset']]['value'])]:
  pointer=image.pointer(address);length=image.word(address+8);line=int.from_bytes(image.read(address+16,4),'little');column=int.from_bytes(image.read(address+20,4),'little');sides.append({'address':hex(address),'path':image.string(pointer['target'],length)['utf8'],'line':line,'column':column,'pointer':pointer})
 assert sides[0]['path']==sides[1]['path']=='programs/pump/src/lib.rs'
 locations.append({'wrapper_instruction_offset':q['offset'],'role':'24-byte Location payload passed to Option::unwrap_failed; allocation extent and historical type identity unproved','original':sides[0],'candidate':sides[1],'equal_path':True,'equal_path_line_column':all(sides[0][k]==sides[1][k]for k in ['path','line','column'])})
(P/'locations03.json').write_text(json.dumps(locations,indent=2)+'\n')
build=read(P/'build03/build-comparison.json');assert build['returncode']==0 and build['source_unchanged']
source=P/'source03'
for label,baseline in [('from02',P/'source02'),('fromR30',R/'work/parallel-main-integration/round30-source/programs/pump')]:
 files=['src/lib.rs','src/trade_v3.rs','src/user_quote_payments.rs']if label=='from02'else['src/lib.rs','src/trade_v3.rs','src/buy_v2.rs'];patch=[]
 for f in files:
  old,new=baseline/f,source/f
  patch.extend(difflib.unified_diff(old.read_text().splitlines(True)if old.exists()else[],new.read_text().splitlines(True)if new.exists()else[],fromfile='a/'+f if old.exists()else'/dev/null',tofile='b/'+f if new.exists()else'/dev/null'))
 (P/f'user-quote-wrapper03-{label}.patch').write_text(''.join(patch))
sources={str(f.relative_to(source)):sha(f)for f in sorted(source.rglob('*'))if f.is_file()};(P/'SOURCE-MANIFEST03.json').write_text(json.dumps(sources,indent=2)+'\n')
result={'status':'validated physical source-placement successor; source02 remains frozen','baseline':'accepted source02','source':'source03','candidate_sha256':sha(P/'build03/candidate.so'),'unstripped_sha256':sha(P/'build03/unstripped.so'),'build_receipt_sha256':sha(P/'build03/build-comparison.json'),'source_hashes':{f:sha(source/f)for f in ['src/lib.rs','src/trade_v3.rs','src/buy_v2.rs']},'removed_file':'src/user_quote_payments.rs','patch_from02_sha256':sha(P/'user-quote-wrapper03-from02.patch'),'patch_fromR30_sha256':sha(P/'user-quote-wrapper03-fromR30.patch'),'inventory':inv['counts'],'gains_vs_source02':gains,'reconstructed_bodies':[{'original':'0x97930','bytes':704,'candidate':hex(read(P/'wrapper03.json')['candidates'][0]['start'])},{'original':'0x8df98','bytes':1208,'candidate':hex(read(P/'native03.json')['candidates'][0]['start'])}],'locations':locations,'runtime':{'counts':counts,'total':sum(counts.values()),'all_signatures_verified':True,'transaction_bytes_identical':True,'fixture_mismatches':[],'diagnostic_mismatches':diag['mismatches'],'exact_invocation_sequences':True},'callees':proof,'limits':['Full ELF equality remains false.','Both Location filename strings now match; their line/column fields still differ. No line or column padding was used.','Same duplicate-normalized-window caveats as source02: two actual recovered bodies, four matching original windows.','Full parent composite qualification remains required.']}
(P/'RESULT03.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'total':sum(counts.values()),'candidate':result['candidate_sha256'],'unstripped':result['unstripped_sha256'],'counts':inv['counts'],'source_hashes':result['source_hashes'],'patch_from02_sha256':result['patch_from02_sha256']},indent=2))
