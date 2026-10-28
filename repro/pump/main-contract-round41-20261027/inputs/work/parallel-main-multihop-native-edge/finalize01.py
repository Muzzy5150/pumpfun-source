from pathlib import Path
import base64,difflib,gzip,hashlib,json,re,struct,sys
from solders.transaction import Transaction
from elftools.elf.elffile import ELFFile
P=Path(__file__).resolve().parent;R=P.parents[1];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sys.path.insert(0,str(R/'scripts'));from pump_diagnostic_audit import audit
read=lambda p:json.loads(gzip.decompress(p.read_bytes())if p.read_bytes()[:2]==b'\x1f\x8b'else p.read_bytes())
state=read(P/'runtime-state01.json');assert len(state)==5 and all(x['returncode']==0 for x in state.values());receipts={k:read(Path(v['output']))for k,v in state.items()};counts={};sig=0;invs={}
for name,j in receipts.items():
 assert not j.get('mismatches');counts[name]=j['case_count'];bad=[]
 for i,row in enumerate(j['cases']):
  assert not row.get('mismatches')and not row.get('different_fields'),(name,i)
  o,n=row['original'],row['candidate'];assert o['transaction_base64']==n['transaction_base64']
  for side in [o,n]:assert all(Transaction.from_bytes(base64.b64decode(side['transaction_base64'])).verify_with_results());sig+=1
  seq=lambda x:[l for l in x['logs']if re.match(r'^Program [1-9A-HJ-NP-Za-km-z]+ (?:invoke \[|success$|failed:)',l)]
  if seq(o)!=seq(n):bad.append(i)
 assert not bad;invs[name]={'cases':j['case_count'],'mismatches':bad}
assert sum(counts.values())==113 and sig==226
d= audit(receipts);assert not d['mismatches'];(P/'diagnostics01.json').write_text(json.dumps(d,indent=2)+'\n');(P/'invocations01.json').write_text(json.dumps(invs,indent=2)+'\n')
system='11111111111111111111111111111111';native=[]
for row in receipts['native-lamports']['cases']:
 c=row['case'];logs=row['original']['logs'];enters=any(l==f'Program {system} invoke [3]'for l in logs)
 if c['amount']==0:assert not enters and '6002'in row['original']['error']
 elif c['curve_lamports']is None:assert enters and row['original']['error']is None
 else:assert enters and 'ArithmeticOverflow'in row['original']['error']
 native.append({'case':c,'pump_nested_system_transfer_entered':enters,'error':row['original']['error']})
(P/'native-boundary-audit01.json').write_text(json.dumps({'cases':native,'zero_amount_precedes_edge':3,'successful_edge_cases':2,'system_overflow_edge_cases':4},indent=2)+'\n')
a=read(P/'baseline-inventory.json');b=read(P/'inventory01.json');assert a['counts']==b['counts']=={'total':1035,'raw':124,'normalized':733,'unmatched':302};diff=read(P/'window-gains01.json');assert all(not r['gains']and not r['losses']for r in diff['sets'].values())
for build in ['baseline-build','build01']:
 r=read(P/build/'build-comparison.json');assert r['returncode']==0 and r['source_unchanged']
def manifest(root):return {str(x.relative_to(root)):sha(x)for x in sorted(root.rglob('*'))if x.is_file()}
base=manifest(P/'baseline-source');assert base==read(P/'BASE-MANIFEST.json');current=manifest(P/'source01');changed=[k for k in base.keys()|current.keys()if base.get(k)!=current.get(k)];assert changed==['src/multi_hop_curve_swap.rs']
pair=read(P/'native01.json');native_target=pair['candidates'][0]['start'];assert pair['candidates'][0]['normalized_equal']
def incoming(elfpath,target):
 with elfpath.open('rb')as f:
  e=ELFFile(f);t=e.get_section_by_name('.text');raw=t.data();start=t['sh_addr'];symbols=[(s['st_value'],s['st_size'],s.name)for s in e.get_section_by_name('.symtab').iter_symbols()if s['st_info']['type']=='STT_FUNC'and s['st_size']];out=[];off=0
  while off<len(raw):
   op,regs,_,imm=struct.unpack_from('<BBhi',raw,off);at=start+off
   if op==0x85 and regs>>4==1 and at+8+imm*8==target:out.append({'site':hex(at),'target':hex(target),'owners':[{'start':hex(s),'bytes':n,'symbol':name}for s,n,name in symbols if s<=at<s+n]})
   off+=16 if op==0x18 else 8
  return out
old=next(m['start']for w in a['windows']if w['start']==0x8df98 for m in w['normalized_matches']if 'user_quote_payments' in m['symbol']and'transfer_native17'in m['symbol']);old_calls=incoming(P/'baseline-build/unstripped.so',old);new_calls=incoming(P/'build01/unstripped.so',native_target);assert len(old_calls)==1 and len(new_calls)==2;assert any('multi_hop_curve' in o['symbol']for c in new_calls for o in c['owners'])
edge={'original_calls':[{'site':'0x5e030','owner':'0x5b3b0'},{'site':'0x979b8','owner':'0x97930'}],'baseline_incoming':old_calls,'candidate_incoming':new_calls,'native_normalized_exact':True,'old_edge_count':1,'new_edge_count':2,'large_caller_body_identity_proved':False};(P/'CALL-EDGE-COMPARISON.json').write_text(json.dumps(edge,indent=2)+'\n')
f='src/multi_hop_curve_swap.rs';patch=''.join(difflib.unified_diff((P/'baseline-source'/f).read_text().splitlines(True),(P/'source01'/f).read_text().splitlines(True),fromfile='a/'+f,tofile='b/'+f));(P/'multihop-native01.patch').write_text(patch)
result={'status':'validated real native helper caller reuse; no normalized-window gain claimed','baseline':'exact stable R32-draft snapshot, one unchanged native-profile control','candidate_sha256':sha(P/'build01/candidate.so'),'unstripped_sha256':sha(P/'build01/unstripped.so'),'baseline_candidate_sha256':sha(P/'baseline-build/candidate.so'),'baseline_unstripped_sha256':sha(P/'baseline-build/unstripped.so'),'source_file':f,'source_sha256':current[f],'baseline_source_sha256':base[f],'patch_sha256':sha(P/'multihop-native01.patch'),'inventory':b['counts'],'full_sets':diff['sets'],'exact_callee':{'original':'0x8df98','bytes':1208,'candidate':hex(native_target)},'caller_edges':edge,'runtime':{'case_counts':counts,'total_cases':113,'signatures_verified':sig,'transaction_bytes_identical':True,'diagnostic_mismatches':[],'invocation_sequence_mismatches':[],'new_native_lamport_cases':9,'successful_edge_baselines':2,'system_overflow_edge_cases':4,'zero_before_edge':3},'limits':['No new normalized or raw function-window matches; this closes the genuine missing MultiHop incoming edge.','The18,584-byte original caller and current large execute body remain unmatched.','Full ELF equality remains false.','Parent combined qualification remains required.']};(P/'RESULT01.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k]for k in ['candidate_sha256','unstripped_sha256','source_sha256','patch_sha256','inventory','runtime']},indent=2))
