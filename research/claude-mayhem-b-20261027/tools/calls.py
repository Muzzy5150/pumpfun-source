import sys; sys.path.insert(0,'.')
import sbfdis
L='/private/tmp/claude-501/-Users-shawwalters-Documents-Codex-2026-10-24-pumpfun-source/bf960843-6806-451b-a211-62c8b228d301/scratchpad/lanes/mayhem-b'
O=sbfdis.elf(L+'/wt/evidence/original/mayhem/deployed.so')
pm=sbfdis.plan_map()
wins={s:(i,e) for i,s,e in sbfdis.original_windows()}
def calls(E,s,e,namefn):
  out=[]
  for x in sbfdis.window_insns(E,s,e):
    if x['op']==0x85:
      t=x['text']
      if t.startswith('call 0x'):
        tgt=int(t.split()[1],16); out.append((x['pc']-s,namefn(tgt)))
      else: out.append((x['pc']-s,t))
  return out
on=lambda t: sbfdis.demangle_short(pm.get(t,'?%#x'%t))[:100]+' ['+wins.get(t,('?',))[0]+']'
def cand(path):
  C=sbfdis.elf(path); cf=sbfdis.funcs(C)
  cn=lambda t: sbfdis.demangle_short(cf.get(t,(0,'?%#x'%t))[1])[:100]
  return C,cf,cn
if __name__=='__main__':
  mode=sys.argv[1]
  if mode=='o':
    s=int(sys.argv[2]); e=wins[s][1]
    print('==',wins[s][0],s,e-s)
    for off,n in calls(O,s,e,on): print('  O',off,n)
  else:
    C,cf,cn=cand(sys.argv[2]); pat=sys.argv[3]
    for a,(b,n) in sorted(cf.items()):
      if pat in n:
        print('== C',a,b-a,sbfdis.demangle_short(n))
        for off,nn in calls(C,a,b,cn): print('  C',off,nn)
