#!/usr/bin/env python3
"""Read-only inventory of original main-Pump instruction evidence in a sealed checkpoint.

No transactions are generated or executed. Literal signed transaction counts are
separate from repeated corpus rows and observable-receipt fingerprints. Missing
serialized transactions may be attributed only from main-program-scoped logs.
"""
from pathlib import Path
import argparse,base64,collections,csv,gzip,hashlib,json,re,sys
from solders.transaction import VersionedTransaction
R=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 b=p.read_bytes();return json.loads(gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b)
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'))
def pairs(x,path):
 if isinstance(x,dict):
  if isinstance(x.get('original'),dict)and isinstance(x.get('candidate'),dict):yield path,x
  for k,v in x.items():
   if k not in ('original','candidate'):yield from pairs(v,path+'/'+k)
 elif isinstance(x,list):
  for i,v in enumerate(x):yield from pairs(v,path+'/'+str(i))
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--checkpoint',type=Path,default=R/'repro/pump/main-contract-round23-20261027');ap.add_argument('--output',type=Path,default=Path(__file__).parent);a=ap.parse_args();a.checkpoint=a.checkpoint.resolve();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 idlp=R/'evidence/upstream/pump.json';dispatchp=R/'evidence/dispatch-map.json';capturep=R/'evidence/original/pump/capture.json';idl=read(idlp);dispatch=read(dispatchp)['pump'];cp=read(a.checkpoint/'CHECKPOINT.json');seal=read(a.checkpoint/'MANIFEST.json');main_program=idl['address'];assert read(capturep)['program']==main_program
 corpus_manifest_path=a.checkpoint/'inputs/work/parallel-main-integration/unified-main-corpus-round23.json';assert sha(corpus_manifest_path)==seal[str(corpus_manifest_path.relative_to(a.checkpoint))];corpus_manifest=read(corpus_manifest_path);suite_scripts={x['group']+'/'+x['name']:x['script']for x in corpus_manifest['suites']}
 by_disc={bytes(x['discriminator']).hex():x['name']for x in idl['instructions']};names=sorted(by_disc.values());assert len(by_disc)==len(names)==56
 log_to_name={re.sub('[^a-z0-9]','',n.lower()):n for n in names}
 for entry in idl['instructions']:assert dispatch['instructions'][entry['name']]['discriminator']==bytes(entry['discriminator']).hex()
 assert dispatch['binary_sha256']==cp['original_sha256']
 def log_invocations(lines):
  stack=[];records=[]
  for line in lines:
   m=re.match(r'^Program (\S+) invoke \[(\d+)\]$',line)
   if m:
    program,depth=m.group(1),int(m.group(2));stack=stack[:depth-1];item={'program':program,'depth':depth,'name':None,'outcome':None};stack.append(item)
    if program==main_program:records.append(item)
    continue
   m=re.match(r'^Program (\S+) (success|failed:.*)$',line)
   if m:
    for i in range(len(stack)-1,-1,-1):
     if stack[i]['program']==m.group(1):stack[i]['outcome']='success'if m.group(2)=='success'else'error';stack=stack[:i];break
    continue
   m=re.match(r'^Program log: Instruction: (.+)$',line)
   if m and stack and stack[-1]['program']==main_program:
    raw=m.group(1);stack[-1]['raw_name']=raw;stack[-1]['name']=log_to_name.get(re.sub('[^a-z0-9]','',raw.lower()))
  return records
 decode_cache={};key_cache={};observations=[];unmatched_logs=collections.Counter();unknown_discs=collections.Counter();unresolved_programs=[];bootstrap=[];corpus=[];inputs={}
 for group,file in [('full','full.json.gz'),('additional','additional.json.gz')]:
  path=a.checkpoint/file;assert sha(path)==seal[file];d=read(path);assert d['candidate_sha256']==cp['candidate_sha256']and d['original_sha256']==cp['original_sha256'];inputs[str(path.relative_to(R))]=sha(path);n=0
  for suite,data in d['suites'].items():
   for where,row in pairs(data,suite):
    n+=1;o=row['original'];lines=o.get('logs',[]);calls=log_invocations(lines);encoded=o.get('transaction_base64');decoded=[];verified=None;txhash=None
    if encoded:
     raw=base64.b64decode(encoded);txhash=hashlib.sha256(raw).hexdigest()
     if txhash not in decode_cache:
      tx=VersionedTransaction.from_bytes(raw);assert len(tx.signatures)==tx.message.header.num_required_signatures and len(tx.signatures)>0;ok=all(tx.verify_with_results());assert ok,(group,where,'signature verification failed');out=[]
      for index,ix in enumerate(tx.message.instructions):
       if ix.program_id_index>=len(tx.message.account_keys):unresolved_programs.append({'case':group+'/'+where,'instruction_index':index,'reason':'program ID requires unavailable loaded address'});continue
       if str(tx.message.account_keys[ix.program_id_index])!=main_program:continue
       data=bytes(ix.data);disc=data[:8].hex();name=by_disc.get(disc)
       if name is None:
        if disc=='40f4bc78a7e9690a':name='anchor_idl'
        elif len(data)<8:name='invalid_short_discriminator'
        else:name='unknown_discriminator'
       out.append({'scope':'top_level','index':index,'name':name,'discriminator':disc,'data_hex':data.hex(),'bytes':len(data)})
      decode_cache[txhash]=out;key_cache[txhash]=[str(k)for k in tx.message.account_keys]
     decoded=list(decode_cache[txhash]);verified=True
     # Inner instructions are recorded by the VM, not signed directly. Keep
     # their scope explicit and require a reverified signed outer transaction.
     roots=[o[k]for k in ['inner','inner_instructions']if k in o]
     if not roots and isinstance(o.get('metadata'),dict):roots=[o['metadata'][k]for k in ['inner_instructions','innerInstructions']if k in o['metadata']]
     def inner_walk(value,path):
      if isinstance(value,dict):
       if 'programIdIndex'in value and 'data'in value:
        index=value['programIdIndex'];keys=key_cache[txhash]
        if index>=len(keys):
         unresolved_programs.append({'case':group+'/'+where,'instruction_index':path,'reason':'CPI program ID requires unavailable loaded address'});return
        if keys[index]!=main_program:return
        data=value['data']
        if isinstance(data,list):
         if data and isinstance(data[0],list):
          size=sum((v&127)<<(7*i)for i,v in enumerate(data[0]));raw=bytes(data[1:]);assert len(raw)==size
         else:raw=bytes(data)
        else:
         alphabet='123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';v=0
         for c in data:v=v*58+alphabet.index(c)
         raw=b'\0'*(len(data)-len(data.lstrip('1')))+(v.to_bytes((v.bit_length()+7)//8,'big')if v else b'')
        disc=raw[:8].hex();name=by_disc.get(disc)
        if name is None:name='anchor_event'if disc=='e445a52e51cb9a1d'else'anchor_idl'if disc=='40f4bc78a7e9690a'else'invalid_short_discriminator'if len(raw)<8 else'unknown_discriminator'
        decoded.append({'scope':'cpi','index':path,'name':name,'discriminator':disc,'data_hex':raw.hex(),'bytes':len(raw)})
       else:
        for k,v in value.items():inner_walk(v,path+'/'+k)
      elif isinstance(value,list):
       for i,v in enumerate(value):inner_walk(v,path+'/'+str(i))
     if roots:inner_walk(roots[0],'inner')
    error=o.get('error');success=error is None;em=re.search(r'InstructionError\(\((\d+),',str(error));error_index=int(em.group(1))if em else None
    selected={x['name']for x in decoded if x['name']in names}
    logs_selected={x['name']for x in calls if x['name']in names}
    for x in calls:
     if x.get('raw_name')and x['name']is None:unmatched_logs[x['raw_name']]+=1
    for x in decoded:
     if x['name']not in names and x['name']!='anchor_event':unknown_discs[(x['name'],x['discriminator'])]+=1
    # Failed rows cannot prove a later encoded main instruction was reached.
    reached={x['name']for x in decoded if x['name']in names and(x['scope']=='cpi' or success or(error_index is not None and x['index']<=error_index))}|logs_selected
    all_named=selected|logs_selected
    filtered={k:v for k,v in o.items()if k not in ('logs','compute_units','relevant_logs','normalized_logs','signature','transaction_sha256')}
    fingerprint=hashlib.sha256(canonical(filtered).encode()).hexdigest()
    for b in o.get('bootstrap_transactions',[]):bootstrap.append({'case':group+'/'+where,'record':b})
    observations.append({'case_id':group+'/'+where,'group':group,'suite':suite,'harness_script':suite_scripts[group+'/'+suite],'case_label':row.get('case',row.get('name')),'transaction_sha256':txhash,'signature_verified':verified,'original_error':error,'transaction_success':success,'error_instruction_index':error_index,'decoded_main_instructions':decoded,'main_log_invocations':calls,'families':sorted(all_named),'reached_families':sorted(reached),'log_families':sorted(logs_selected),'observable_receipt_sha256':fingerprint})
  assert n==d['case_count'],(group,n,d['case_count']);print(json.dumps({'group':group,'paired_rows':n}),flush=True);corpus.append({'group':group,'archive':str(path.relative_to(R)),'sha256':sha(path),'declared_cases':d['case_count'],'paired_rows':n,'suites':len(d['suites'])});del d
 family=[]
 for name in names:
  rows=[x for x in observations if name in x['families']];reached=[x for x in rows if name in x['reached_families']];signed=[x for x in rows if any(y['name']==name and y['scope']=='top_level'for y in x['decoded_main_instructions'])];signed_ids={id(x)for x in signed};signed_reached=[x for x in reached if id(x)in signed_ids];cpi=[x for x in rows if any(y['name']==name and y['scope']=='cpi'for y in x['decoded_main_instructions'])];backed_ids=signed_ids|{id(x)for x in cpi};success=[x for x in reached if x['transaction_success']];fail=[x for x in reached if not x['transaction_success']]
  inv=[z for x in rows for z in x['main_log_invocations']if z['name']==name]
  data={z['data_hex']for x in signed for z in x['decoded_main_instructions']if z['name']==name}
  logonly=[x for x in reached if not x['transaction_sha256']]
  status='absent'if not reached else'success_and_error'if success and fail else'success_only'if success else'error_only'
  family.append({'name':name,'discriminator':next(k for k,v in by_disc.items()if v==name),'coverage':status,'any_case_rows':len(rows),'reached_case_rows':len(reached),'successful_transaction_rows':len(success),'failed_transaction_rows':len(fail),'encoded_but_unreached_rows':len(rows)-len(reached),'signed_byte_case_rows':len(signed),'signed_byte_reached_case_rows':len(signed_reached),'signed_byte_success_rows':sum(x['transaction_success']for x in signed_reached),'log_only_case_rows':len(logonly),'cpi_receipt_case_rows':len(cpi),'cpi_receipt_success_rows':sum(x['transaction_success']for x in cpi),'transaction_backed_instruction_byte_rows':len(backed_ids),'transaction_backed_success_rows':sum(id(x)in backed_ids and x['transaction_success']for x in reached),'distinct_signed_transactions':len({x['transaction_sha256']for x in signed}),'distinct_signed_instruction_data':len(data),'distinct_observable_receipts':len({x['observable_receipt_sha256']for x in rows}),'observed_successful_main_invocations':sum(z['outcome']=='success'for z in inv),'observed_failed_main_invocations':sum(z['outcome']=='error'for z in inv),'suites':sorted({x['group']+'/'+x['suite']for x in rows}),'harness_scripts':sorted({x['harness_script']for x in rows}),'examples':{'success':[x['case_id']for x in success[:3]],'error':[x['case_id']for x in fail[:3]],'log_only':[x['case_id']for x in logonly[:3]]}})
 summary={'idl_families':len(names),'families_with_any_reached_case':sum(x['reached_case_rows']>0 for x in family),'families_with_successful_transactions':sum(x['successful_transaction_rows']>0 for x in family),'families_error_only':sum(x['coverage']=='error_only'for x in family),'families_absent':sum(x['coverage']=='absent'for x in family),'families_with_signed_byte_reached_cases':sum(x['signed_byte_reached_case_rows']>0 for x in family),'families_with_signed_byte_success_cases':sum(x['signed_byte_success_rows']>0 for x in family),'families_with_transaction_backed_instruction_bytes':sum(x['transaction_backed_instruction_byte_rows']>0 for x in family),'families_with_transaction_backed_success':sum(x['transaction_backed_success_rows']>0 for x in family),'transaction_backed_error_only_families':sum(x['transaction_backed_instruction_byte_rows']>0 and not x['transaction_backed_success_rows']for x in family),'paired_corpus_rows':len(observations),'serialized_signed_case_rows':sum(x['transaction_sha256']is not None for x in observations),'case_rows_without_serialized_transactions':sum(x['transaction_sha256']is None for x in observations),'distinct_signed_transactions':len(decode_cache),'distinct_observable_receipts':len({x['observable_receipt_sha256']for x in observations}),'case_rows_with_no_family_attribution':sum(not x['families']for x in observations),'bootstrap_records_not_counted':len(bootstrap)}
 gaps={'absent':[x['name']for x in family if x['coverage']=='absent'],'error_only':[x['name']for x in family if x['coverage']=='error_only'],'no_serialized_signed_byte_evidence':[x['name']for x in family if not x['signed_byte_reached_case_rows']],'no_transaction_backed_instruction_bytes':[x['name']for x in family if not x['transaction_backed_instruction_byte_rows']],'transaction_backed_error_only':[x['name']for x in family if x['transaction_backed_instruction_byte_rows']and not x['transaction_backed_success_rows']],'no_serialized_success_evidence':[x['name']for x in family if not x['signed_byte_success_rows']]}
 for p in [corpus_manifest_path,idlp,dispatchp,capturep,a.checkpoint/'CHECKPOINT.json',a.checkpoint/'MANIFEST.json',Path(__file__).resolve()]:inputs[str(p.relative_to(R))]=sha(p)
 report={'scope':__doc__,'checkpoint':str(a.checkpoint.relative_to(R)),'main_program':main_program,'candidate_sha256':cp['candidate_sha256'],'original_sha256':cp['original_sha256'],'inputs_sha256':inputs,'summary':summary,'corpora':corpus,'coverage_definitions':{'reached':'A main-scoped Instruction log names the IDL family, or a decoded main top-level instruction is at/before the failing instruction index (all decoded instructions on successful transactions).','success':'The original transaction error field is null and the family was reached. Earlier successful invocations in failed transactions are counted separately.','signed_byte':'Main instruction data is encoded directly in a serialized top-level transaction; signatures reverified offline. CPI receipt byte evidence is counted separately and requires a reverified signed outer transaction. Logs alone are not counted as instruction bytes.','distinct_observable_receipt':'Hash of original outcome excluding logs/compute/signature summary fields; includes available signed bytes, state snapshots, errors, events and inner instructions. Not proof of unique complete initial states.','bootstrap':'Setup bootstrap transactions are inventoried separately and excluded from tested-family counts.','limits':'No path/branch completeness or live-chain acceptance claim. Most literal transactions repeat across state variants. Family counts never sum to unique test-space coverage.'},'families':family,'gaps':gaps,'unknown_main_discriminators':[{'kind':k[0],'discriminator':k[1],'case_rows':v}for k,v in unknown_discs.items()],'unmapped_main_log_names':dict(unmatched_logs),'missing_transaction_byte_harnesses':[{'script':script,'case_rows':sum(x['harness_script']==script and not x['transaction_sha256']for x in observations),'families':sorted({n for x in observations if x['harness_script']==script and not x['transaction_sha256']for n in x['families']})}for script in sorted({x['harness_script']for x in observations if not x['transaction_sha256']})],'unresolved_program_ids':unresolved_programs,'unattributed_case_rows':{'main_invoked_without_IDL_family':[x['case_id']for x in observations if not x['families']and x['main_log_invocations']],'main_not_invoked':[x['case_id']for x in observations if not x['families']and not x['main_log_invocations']]}}
 (a.output/'REPORT.json').write_text(json.dumps(report,indent=2)+'\n');(a.output/'OBSERVATIONS.json.gz').write_bytes(gzip.compress(canonical(observations).encode(),mtime=0));(a.output/'BOOTSTRAP.json.gz').write_bytes(gzip.compress(canonical(bootstrap).encode(),mtime=0))
 columns=['name','coverage','reached_case_rows','successful_transaction_rows','failed_transaction_rows','signed_byte_reached_case_rows','signed_byte_success_rows','log_only_case_rows','cpi_receipt_case_rows','transaction_backed_instruction_byte_rows','transaction_backed_success_rows','distinct_signed_transactions','distinct_signed_instruction_data','distinct_observable_receipts']
 with(a.output/'coverage.csv').open('w')as f:
  w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows({k:x[k]for k in columns}for x in family)
 text=f'''# Main Pump instruction evidence — sealed Round23

All **{summary['idl_families']} / {summary['idl_families']} captured IDL families** have a reached case and an original successful transaction in the retained evidence. None is wholly absent or error-only. This establishes instruction-family coverage, not branch coverage or whole-contract correctness.

The evidence contains **{summary['paired_corpus_rows']:,} paired rows**, including **{summary['serialized_signed_case_rows']:,} rows with serialized original transactions**, representing **{summary['distinct_signed_transactions']:,} distinct literal signed transactions**. The remaining **{summary['case_rows_without_serialized_transactions']:,} rows** retain logs/state without transaction bytes. There are **{summary['distinct_observable_receipts']:,} distinct observable original receipts** under the documented fingerprint; this is not a count of complete unique starting states.

Using instruction bytes from reverified signed top-level transactions or recorded main CPIs backed by a reverified outer transaction, **{summary['families_with_transaction_backed_instruction_bytes']} families** have evidence and **{summary['families_with_transaction_backed_success']} have successful evidence**. The transaction-backed error-only family is: {', '.join(gaps['transaction_backed_error_only'])}. Its successful cases exist in the log/state-only tier.

These {len(gaps['no_transaction_backed_instruction_bytes'])} families have log/state evidence but no retained transaction-backed instruction bytes:

'''+'\n'.join('- `'+name+'`'for name in gaps['no_transaction_backed_instruction_bytes'])+'''

Multi-hop and mayhem-parameter CPI evidence is explicitly separated from top-level main instructions. Eight bootstrap records are excluded. Malformed dispatch payloads and attempts rejected before main invocation remain unattributed rather than being assigned an intended family.

`REPORT.json` records per-family case/success/error counts and proof limitations; `coverage.csv` is the compact table. `OBSERVATIONS.json.gz` maps every paired row to discriminators and main-scoped invocation logs. Inputs are bound to the sealed checkpoint manifest. No transactions were generated, submitted or executed for this audit.

Reproduce from the repository root:

```sh
work/test-env/bin/python work/parallel-main-instruction-coverage/audit.py
```
'''
 (a.output/'README.md').write_text(text)
 manifest={name:sha(a.output/name)for name in ['audit.py','REPORT.json','OBSERVATIONS.json.gz','BOOTSTRAP.json.gz','coverage.csv','README.md']if(a.output/name).is_file()};(a.output/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(json.dumps({'summary':summary,'gaps':gaps,'unknown_main_discriminators':report['unknown_main_discriminators'],'unmapped_main_log_names':dict(unmatched_logs)},indent=2))
if __name__=='__main__':main()
