#!/usr/bin/env python3
"""cmpw.py ELF 0xWIN:SYMREGEX [...]  -- similarity of candidate fns vs original windows (with/without stack offsets/regs)."""
import json, subprocess, sys, re, difflib
PW='/Users/shawwalters/Documents/Codex/2026-10-24/claude-pump-work'
OD='/Users/shawwalters/.cache/solana/v1.52/platform-tools/llvm/bin/llvm-objdump'
ORIG='/private/tmp/claude-501/-Users-shawwalters-Documents-Codex-2026-10-24-pumpfun-source/bf960843-6806-451b-a211-62c8b228d301/scratchpad/lanes/pump-hi/wt/evidence/original/pump/deployed.so'
def ins(path,s,n):
    o=subprocess.run([OD,'-d','--no-show-raw-insn',f'--start-address={s}',f'--stop-address={s+n}',path],capture_output=True,text=True).stdout
    R=[]
    for l in o.splitlines():
        m=re.match(r'^\s+[0-9a-f]+:\s+(.*)$',l)
        if m: R.append(re.sub(r'\s+',' ',re.sub(r' <[^>]*>','',m.group(1))).strip())
    return R
def nrm(l,keep):
    l=re.sub(r'call -?0x[0-9a-f]+','call',l); l=re.sub(r'lddw (r\d), 0x[0-9a-f]+',r'lddw \1, C',l)
    l=re.sub(r'([+-])0x[0-9a-f]+$','J',l) if re.match(r'^(j|ja)',l) else l
    if not keep: l=re.sub(r'r10 - 0x[0-9a-f]+','r10-X',l)
    return l
def syms(elf):
    S=[]
    for l in subprocess.run([OD,'-t',elf],capture_output=True,text=True).stdout.splitlines():
        m=re.match(r'^([0-9a-f]+)\s.*\sF\s\.text\s+([0-9a-f]+)\s+(?:\.hidden\s+)?(\S+)$',l)
        if m: S.append((int(m.group(1),16),int(m.group(2),16),m.group(3)))
    return S
def main(elf,specs,dump=None):
    inv=json.load(open(PW+'/base/L06/inventory.json'))['windows']
    S=syms(elf)
    for w in specs:
        addr,rx=w.split(':',1); oa=int(addr,16); on=inv[str(oa)]['bytes']
        o=ins(ORIG,oa,on)
        cands=[x for x in S if re.search(rx,x[2])]
        if not cands: print(addr,'no symbol',rx); continue
        for ca,cn,nm in cands[:3]:
            c=ins(elf,ca,cn)
            r1=difflib.SequenceMatcher(None,[nrm(x,True) for x in o],[nrm(x,True) for x in c],autojunk=False).ratio()
            r2=difflib.SequenceMatcher(None,[nrm(x,False) for x in o],[nrm(x,False) for x in c],autojunk=False).ratio()
            r3=difflib.SequenceMatcher(None,[re.sub(r'\br\d\b','R',nrm(x,False)) for x in o],[re.sub(r'\br\d\b','R',nrm(x,False)) for x in c],autojunk=False).ratio()
            print(f'{addr} orig {on}B/{len(o)} vs {nm[:80]} @{ca:#x} {cn}B/{len(c)}: ratio {r1:.4f} nostack {r2:.4f} noreg {r3:.4f}')
            if dump: open(dump,'w').write('\n'.join(c)+'\n')
if __name__=='__main__':
    args=sys.argv[1:]; dump=None
    if '--dump' in args: i=args.index('--dump'); dump=args[i+1]; del args[i:i+2]
    main(args[0],args[1:],dump)
