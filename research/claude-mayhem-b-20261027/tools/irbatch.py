#!/usr/bin/env python3
"""Like batch.py but emits LLVM IR and MIR-after-isel for one function per variant (analysis only)."""
import json, os, subprocess, sys, re
SP='/private/tmp/claude-501/-Users-shawwalters-Documents-Codex-2026-10-24-pumpfun-source/bf960843-6806-451b-a211-62c8b228d301/scratchpad'
L=SP+'/lanes/mayhem-b'; B=L+'/build'
if os.environ.get('LANE_BATCH_LOCKED')!='1':
    env=dict(os.environ,LANE_BATCH_LOCKED='1')
    sys.exit(subprocess.call(['python3',SP+'/sbf_lock.py','--slots','6','--name','sbf','--','python3',__file__]+sys.argv[1:],env=env))
slot,spec,func=sys.argv[1],json.load(open(sys.argv[2])),sys.argv[3]
root=f'{B}/roots/{slot}'; dst=f'{root}/programs/mayhem'
os.makedirs(f'{root}/programs',exist_ok=True)
for v in spec:
    label=v['label']+'-ir'
    subprocess.run(['rsync','-a','--delete','--exclude','.git',f'{B}/roots/work/programs/mayhem/',dst+'/'],check=True)
    for f,old,new in v.get('reps',[]):
        p=f'{dst}/{f}'; s=open(p).read(); assert s.count(old)==1; open(p,'w').write(s.replace(old,new))
    env=dict(os.environ,LANE_CLEAN_ANCHOR='0',MAYHEM_ROOT_RUSTC_ARGS_JSON=json.dumps(['--emit=llvm-ir',f'-Cllvm-args=-print-after=finalize-isel -filter-print-funcs={func}']))
    r=subprocess.run(['python3',f'{B}/build_lane.py',label,root,slot],env=env,capture_output=True,text=True)
    ll=f'{L}/target/{slot}/sbpf-solana-solana/release/deps/mayhem_recovered.ll'
    if os.path.exists(ll): os.replace(ll,f'{L}/out/ir/{label}.ll')
    print(label, 'rc', r.returncode, flush=True)
