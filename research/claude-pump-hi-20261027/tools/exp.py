#!/usr/bin/env python3
"""Experiment driver: copy a base crate, apply an edit script, fastbuild, score vs a baseline, compare windows.

exp.py NAME EDIT.py [--base DIR] [--baseline inventory.json] [--win 0xADDR:SYMREGEX ...]
EDIT.py is exec'd with `src` (Path to the copied crate's src dir) and helper `sub(path, old, new, count=1)`.
"""
import argparse, json, shutil, subprocess, sys, re, difflib
from pathlib import Path
D=Path('/Users/shawwalters/Documents/Codex/2026-10-24/claude-mayhem-work/pump-hi')
PW=Path('/Users/shawwalters/Documents/Codex/2026-10-24/claude-pump-work')
PY='/Users/shawwalters/Documents/Codex/2026-10-24/pumpfun-source/work/test-env/bin/python'
OD='/Users/shawwalters/.cache/solana/v1.52/platform-tools/llvm/bin/llvm-objdump'
NM='/Users/shawwalters/.cache/solana/v1.52/platform-tools/llvm/bin/llvm-nm'
ORIG='/private/tmp/claude-501/-Users-shawwalters-Documents-Codex-2026-10-24-pumpfun-source/bf960843-6806-451b-a211-62c8b228d301/scratchpad/lanes/pump-hi/wt/evidence/original/pump/deployed.so'
ap=argparse.ArgumentParser(); ap.add_argument('name'); ap.add_argument('edit'); ap.add_argument('--base',default=str(D/'trials/L06'))
ap.add_argument('--baseline',default=str(PW/'base/L06/inventory.json')); ap.add_argument('--win',action='append',default=[])
ap.add_argument('--noscore',action='store_true'); ap.add_argument('--nobuild',action='store_true')
a=ap.parse_args()
t=D/'trials'/a.name
if t.exists(): shutil.rmtree(t)
shutil.copytree(a.base,t)
src=t/'src'
def sub(path,old,new,count=1):
    p=src/path; s=p.read_text(); n=s.count(old)
    assert n>=1, f'pattern not found in {path}: {old[:80]!r}'
    if count==1: assert n==1, f'pattern not unique ({n}) in {path}: {old[:80]!r}'
    p.write_text(s.replace(old,new) if count!=1 else s.replace(old,new,1))
def lines(path): return (src/path).read_text().count('\n')
exec(open(a.edit).read(),{'src':src,'sub':sub,'lines':lines,'Path':Path,'re':re})
out=D/'out'/a.name
r=subprocess.run([PY,'-B','fastbuild.py','--src',str(t),'--work',str(D/'fb'),'--out',str(out)],cwd=PW/'harness',capture_output=True,text=True)
(D/'out'/(a.name+'.fb.json')).write_text(r.stdout); (D/'out'/(a.name+'.fb.err')).write_text(r.stderr)
try: fb=json.loads(r.stdout)
except Exception: print('BUILD FAILED'); print(r.stderr[-3000:]); sys.exit(1)
print('build ok=%s runtime_valid=%s stack_warnings=%d'%(fb['ok'],fb['runtime_valid'],len(fb['stack_warnings'])))
if not a.noscore:
    js=D/'out'/(a.name+'.score.json')
    r=subprocess.run([PY,'-B','score.py',str(out/'unstripped.so'),'--baseline',a.baseline,'--json',str(js),'--quiet'],cwd=PW/'harness',capture_output=True,text=True)
    try:
        s=json.loads(js.read_text()); sm=s.get('summary',s)
        print('score normalized=%s raw=%s gains=%s losses=%s raw_gains=%s raw_losses=%s'%(sm.get('normalized'),sm.get('raw'),sm.get('gains'),sm.get('losses'),sm.get('raw_gains'),sm.get('raw_losses')))
    except Exception as e: print('score parse failed',e,r.stdout[-2000:],r.stderr[-2000:])
sys.path.insert(0,str(D/'mini'))
import cmpw
cmpw.main(str(out/'unstripped.so'),a.win)
