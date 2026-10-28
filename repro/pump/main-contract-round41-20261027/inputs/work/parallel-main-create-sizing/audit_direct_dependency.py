from pathlib import Path
import argparse,hashlib,json,os,subprocess
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def identity(x):return [x['package_name'],x['package_version'],x['target_kind'],x['kind'],x['compile_mode']]
def main():
 p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True);a=p.parse_args();b=a.build.resolve();base=a.baseline.resolve();br=json.loads((b/'build-comparison.json').read_text());old=json.loads((base/'build-comparison.json').read_text());assert br['returncode']==0 and br['source_unchanged'];bound={str(b/x):sha(b/x)for x in ['candidate.so','unstripped.so','build-comparison.json']};bound.update({str(ROOT/k):v for k,v in br['source_sha256'].items()})
 target=b.parent/(b.name+'-plan-target');target.mkdir(exist_ok=False);env=os.environ.copy();env.update(br['environment']);env['CARGO_TARGET_DIR']=str(target);env['PUMP_SOURCE_WRAPPER_LOG']=str(b/'audit-source-calls.jsonl');crate=Path(br['source_directory']);workspace=crate.parents[1];command=[str(Path(env['RUSTC']).with_name('cargo')),'build','--manifest-path',str(crate/'Cargo.toml'),'--release','--target','sbf-solana-solana','--locked','--offline','-Z','unstable-options','--build-plan'];r=subprocess.run(command,cwd=workspace,env=env,text=True,capture_output=True);(b/'audit-build-plan.stderr').write_text(r.stderr);r.check_returncode();plan=json.loads(r.stdout);(b/'audit-build-plan.json').write_text(json.dumps(plan,indent=2)+'\n');prior=json.loads((base/'build-plan.json').read_text())
 def normalized(d,build,record,plan_target):
  replacements=[(str(plan_target),'@TARGET'),(record['environment']['CARGO_TARGET_DIR'],'@TARGET'),(record['environment']['CARGO_HOME'],'@CARGO_HOME'),(str(build/'audit-source-calls.jsonl'),'@WRAPPER_LOG'),(record['environment']['PUMP_SOURCE_WRAPPER_LOG'],'@WRAPPER_LOG'),(str(build),'@BUILD')]
  replacements.sort(key=lambda x:-len(x[0]));inv=d['invocations']
  def norm(x):
   if isinstance(x,str):
    for before,after in replacements:x=x.replace(before,after)
    return x
   if isinstance(x,list):return [norm(y)for y in x]
   if isinstance(x,dict):return {norm(k):norm(v)for k,v in x.items()}
   return x
  out=[]
  for x in inv:
   if x['package_name']=='pump-recovered':continue
   y=dict(x);y['deps']=sorted([identity(inv[i])for i in x['deps']],key=lambda x:json.dumps(x));out.append(norm(y))
  return sorted(out,key=lambda x:json.dumps(x,sort_keys=True))
 left=normalized(prior,base,old,Path(old['environment']['CARGO_TARGET_DIR']));right=normalized(plan,b,br,target);ls={json.dumps(x,sort_keys=True):x for x in left};rs={json.dumps(x,sort_keys=True):x for x in right};changes={'removed':[ls[x]for x in sorted(ls.keys()-rs.keys())],'added':[rs[x]for x in sorted(rs.keys()-ls.keys())]}
 cache=Path(old['dependency_cache']['cache_root'])/old['dependency_cache']['key'];manifest=json.loads((cache/'manifest.json').read_text());assert sha(cache/'manifest.json')==old['dependency_cache']['manifest_sha256'];payload=[]
 for relative,expected in manifest['files'].items():
  if Path(relative).suffix not in ['.rlib','.rmeta','.so','.dylib','.a']:continue
  current=b/'target'/relative;payload.append({'path':relative,'baseline_sha256':expected,'actual_sha256':sha(current)if current.is_file()else None})
 assert bound=={k:sha(k)for k in bound},'compiled/source inputs changed during audit'
 out={'scope':'Fresh no-build Cargo plan plus external compiled-output hash comparison for one already-locked direct trait dependency. Main package excluded from comparison; no original bytes are compiler inputs.','build':str(b),'baseline':str(base),'build_sha256':sha(b/'build-comparison.json'),'baseline_sha256':sha(base/'build-comparison.json'),'fresh_plan_sha256':sha(b/'audit-build-plan.json'),'fresh_plan_command':command,'baseline_external_units':len(left),'current_external_units':len(right),'non_main_inputs_identical':not changes['removed']and not changes['added'],'non_main_input_differences':changes,'external_compiled_payloads':payload,'payload_identical':sum(x['actual_sha256']==x['baseline_sha256']for x in payload),'payload_different':sum(x['actual_sha256']is not None and x['actual_sha256']!=x['baseline_sha256']for x in payload),'payload_missing':sum(x['actual_sha256']is None for x in payload),'bound_files_sha256':bound};(b/'direct-dependency-audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k]for k in ['baseline_external_units','current_external_units','non_main_inputs_identical','payload_identical','payload_different','payload_missing']},indent=2))
if __name__=='__main__':main()
