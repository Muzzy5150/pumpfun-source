"""Run only new distribution cases; the outer wrapper records captured loads."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from pump_diagnostic_audit import audit

def execute(item):
 import pump_minimum_fee_differential as minimum
 import pump_creator_distribution_differential as distribution
 label,c,candidate=item
 module=minimum if label=='minimum' else distribution
 o=module.run(c);n=module.run(c,candidate)
 fields=['error','before','after','events']+([] if label=='minimum' else ['inner','return'])
 diff=[k for k in fields if o[k]!=n[k]]
 if label=='minimum':diff += [k for k in ['return_data','inner_instructions'] if o['metadata'][k]!=n['metadata'][k]]
 return label,{'case':c,'original':o,'candidate':n,'different_fields':diff},[]

def main():
 import pump_minimum_fee_differential as minimum
 import pump_creator_distribution_differential as distribution
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--workers',type=int,default=2);a=p.parse_args()
 suites={'minimum':[],'distribution':[]}
 for name,suite in [('before-probe','minimum'),('extreme-before','minimum'),('distribution-before','distribution')]:
  d=json.loads(gzip.decompress((ROOT/'work/parallel-main-minimum-audit'/(name+'.json.gz')).read_bytes()));suites[suite]+=[r['case'] for r in d['cases']]
 auth=str(distribution.AUTH.pubkey());other=str(distribution.OTHER.pubkey());quote=distribution.Pubkey.from_bytes(bytes([88])*32)
 for token22 in [False,True]:
  token=distribution.TOKEN22 if token22 else distribution.TOKEN
  ata=distribution.Pubkey.find_program_address([bytes(distribution.AUTH.pubkey()),bytes(token),bytes(quote)],distribution.ATA)[0]
  stable={'op':'distribute_creator_fees_v2','quote':str(quote),'curve_patches':[(83,bytes(quote).hex())],'remaining_atas':True,'grouped_remaining':True,'token22':token22,'pump_tokens':1000000}
  suites['distribution'] += [
   {**stable,'name':'planner-late-zero-share','old_shareholders':[(auth,5000),(other,0)],'ata_writable':False},
   {**stable,'name':'planner-duplicate-empty-ata','old_shareholders':[(auth,5000),(auth,5000)],'account_mutations':{'remaining_ata_0':{'missing':True},'remaining_ata_1':{'missing':True}}},
   {**stable,'name':'planner-zero-share-wrong-ata','old_shareholders':[(auth,0)],'remaining_atas':False,'remaining':[(auth,True),(other,True)]},
   {**stable,'name':'planner-executable-wrong-ata','old_shareholders':[(str(distribution.PUMP),10000)],'remaining_atas':False,'remaining':[(str(distribution.PUMP),False),(other,True)]},
   {**stable,'name':'planner-overflow-readonly-ata','pump_tokens':1844674407370956,'ata_writable':False},
  ]
 paths=[Path(__file__),a.candidate,Path(minimum.__file__),Path(distribution.__file__),ROOT/'scripts/pump_captured_loader.py',ROOT/'evidence/original/pump/deployed.so',ROOT/'evidence/original/pump_fees/deployed.so',ROOT/'evidence/original/pump_amm/deployed.so',ROOT/'evidence/original/pump/capture.json',ROOT/'evidence/original/pump/program-account.bin',ROOT/'evidence/original/pump/programdata-account.bin']
 paths += [ROOT/'work/parallel-main-minimum-audit'/(name+'.json.gz') for name in ['before-probe','extreme-before','distribution-before']]
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before={str(p):sha(p) for p in paths};rows={k:[] for k in suites};loads=[]
 items=[(name,c,str(a.candidate.resolve())) for name,cases in suites.items() for c in cases]
 assert len(items)==62,len(items)
 # The outer wrapper installs captured accounts before importing this script.
 # Stay in that process so its loader receipt covers every execution.
 for i,(name,r,ls) in enumerate(map(execute,items)):
  rows[name].append(r)
  if r['different_fields']:print('MISMATCH',name,json.dumps(r['case']),r['different_fields'],flush=True)
  elif i%40==0:print('progress',i+1,len(items),flush=True)
 assert before=={str(p):sha(p) for p in paths}
 report={'scope':'62 additional normally signed offline distribution comparisons under the outer captured loader; stock cases remain in the full corpus. Full state, event, return and CPI comparison, plus strict diagnostics. This does not establish whole ELF identity.','provenance':before,'case_count':len(items),'suites':rows,'mismatches':[{'suite':name,'index':i} for name,rs in rows.items() for i,r in enumerate(rs) if r['different_fields']]}
 diag=audit(rows);report['diagnostics']=diag;a.output.write_bytes(gzip.compress(json.dumps(report).encode()));a.output.with_suffix('.diagnostics.json').write_text(json.dumps(diag,indent=2)+'\n')
 print(json.dumps({'case_count':len(items),'mismatches':report['mismatches'],'diagnostic_mismatches':len(diag['mismatches']),'loader_receipt':'recorded by outer wrapper'}),flush=True)
 return bool(report['mismatches'] or diag['mismatches'])
if __name__=='__main__':raise SystemExit(main())
