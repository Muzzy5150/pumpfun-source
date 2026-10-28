from pathlib import Path
import base64,difflib,gzip,hashlib,json,re,struct
from elftools.elf.elffile import ELFFile
from solders.transaction import VersionedTransaction
P=Path(__file__).resolve().parent;R=P.parents[1];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 b=p.read_bytes();return json.loads(gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b)
def elf(p):
 with p.open('rb')as f:
  e=ELFFile(f);t=e.get_section_by_name('.text');syms=[(s.name,s['st_value'],s['st_size'])for s in (e.get_section_by_name('.symtab').iter_symbols()if e.get_section_by_name('.symtab')else[])];return t['sh_addr'],t.data(),syms
state=read(P/'validation01/state.json');assert state['status']=='passed'and not state['failures'];transactions=signatures=0;combined=read(P/'validation01/additional.json.gz')
for name,receipt in state['completed'].items():
 result=read(Path(receipt['output']));assert not combined['suites'][receipt['name']]['invocation_audit']['mismatches']
 for row in result['cases']:
  o=row.get('original',row.get('target'));n=row['candidate'];assert o['transaction_base64']==n['transaction_base64']
  for side in [o,n]:
   t=VersionedTransaction.from_bytes(base64.b64decode(side['transaction_base64']));assert all(t.verify_with_results());transactions+=1;signatures+=len(t.signatures)
assert sum(r['case_count']for r in state['completed'].values())==528
compound=read(P/'compound-new01.json.gz');assert compound['case_count']==28 and not compound['mismatches'] and not compound['diagnostics']['mismatches']and compound['all_deduplicated_input_hashes_match']
inv=read(P/'inventory01.json');baseline=read(R/'work/parallel-main-integration/build-round33-identity/normalized-inventory.json');delta={}
for name in ['normalized_matches','raw_match']:
 f=lambda x:{r['start']for r in x['windows']if r[name]};delta[name]={'gains':sorted(f(inv)-f(baseline)),'losses':sorted(f(baseline)-f(inv))};assert not delta[name]['gains']and not delta[name]['losses']
comp=read(P/'claim01.json');c=comp['candidates'];assert len(c)==1;c=c[0]
original=R/'evidence/original/pump/deployed.so';candidate=P/'build01/unstripped.so';old=R/'work/parallel-main-integration/build-round33-identity/unstripped.so'
proof={}
for label,path in [('original',original),('baseline',old),('candidate',candidate)]:
 start,data,syms=elf(path)
 if label=='original':a,n,target=0x75308,5920,0x1a0530
 else:
  name,a,n=next(s for s in syms if 'claim_token_incentives5claim17h'in s[0]);target=next(s[1]for s in syms if 'solana_program7program13invoke_signed17h'in s[0])
 calls=[]
 for p in range(a,a+n,8):
  op,reg,off,imm=struct.unpack_from('<BBhi',data,p-start)
  if op==0x85 and reg>>4==1 and p+8+imm*8==target:
   pre=[]
   for q in range(max(a,p-64),p,8):
    b=data[q-start:q-start+8];opcode,regs,offset,im=struct.unpack('<BBhi',b);pre.append({'pc':hex(q),'bytes':b.hex(),'op':hex(opcode),'dst':regs&15,'src':regs>>4,'offset':offset,'immediate':im})
   r4=[v for v in pre if v['op']=='0xb7'and v['dst']==4];assert r4
   calls.append({'site':hex(p),'target':hex(target),'account_info_count':r4[-1]['immediate'],'prelude':pre})
 assert len(calls)==1
 proof[label]={'elf_sha256':sha(path),'claim_start':hex(a),'claim_bytes':n,'invoke':calls[0]}
assert proof['original']['invoke']['account_info_count']==proof['candidate']['invoke']['account_info_count']==1
assert proof['baseline']['invoke']['account_info_count']==2
(P/'EVENT-CPI-ABI01.json').write_text(json.dumps(proof,indent=2)+'\n')
name='src/token_incentives/claim_token_incentives.rs';a=R/'work/parallel-main-integration/round33-source/programs/pump'/name;b=P/'source01'/name
patch=''.join(difflib.unified_diff(a.read_text().splitlines(True),b.read_text().splitlines(True),fromfile='a/'+name,tofile='b/'+name));(P/'claim-event-account01.patch').write_text(patch)
base=read(P/'STAGING01.json');assert all(sha(P/'source01'/n)==h for n,h in base['source_hashes'].items())
result={'status':'Validated single-account event-CPI ABI restoration; no normalized-window gain','source_file':name,'source_sha256':sha(b),'baseline_file_sha256':sha(a),'candidate_sha256':sha(P/'build01/candidate.so'),'unstripped_sha256':sha(candidate),'build_receipt_sha256':sha(P/'build01/build-comparison.json'),'patch_sha256':sha(P/'claim-event-account01.patch'),'inventory':inv['counts'],'complete_window_delta':delta,'claim':{k:{'bytes':v['claim_bytes'],'event_account_info_count':v['invoke']['account_info_count']}for k,v in proof.items()},'runtime':{'claim_cases':528,'verified_transactions':transactions,'verified_signatures':signatures,'new_compound_cases':30,'deduplicated_incremental_cases':28,'incremental_driver_replay':28,'diagnostic_mismatches':0,'invocation_sequence_mismatches':0},'limits':['Claim body remains unmatched:5624vsoriginal5920bytes.','No source event schema, worker, context parser, account-meta list or migration changes.','Raw119/normalized733 comparison uses R33 hybrid identity layout; not native or final ordered-layout raw count.','Full original ELF equality remains false.','Only AccountInfo slice supplied to invoke_signed is restored; outer transaction and CPI Instruction AccountMeta lists are unchanged.']}
(P/'RESULT01.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
