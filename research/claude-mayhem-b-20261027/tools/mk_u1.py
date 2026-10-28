import json,sys,difflib
PE,SP,D=sys.argv[1:4]
F_PI='src/instructions/pump_interface.rs'; F_ST='src/state.rs'
par_pi=open(PE+'/'+F_PI).read(); scvp_pi=open(SP+'/scvp-pi.rs').read()
work_st=open(D+'/build/roots/work/programs/mayhem/'+F_ST).read(); scvp_st=open(SP+'/scvp-state.rs').read()
def hunks(a,b):
    al=a.split('\n'); bl=b.split('\n'); out=[]
    sm=difflib.SequenceMatcher(a=al,b=bl,autojunk=False)
    for tag,i1,i2,j1,j2 in sm.get_opcodes():
        if tag=='equal': continue
        c0=max(i1-1,0); c1=min(i2+1,len(al))
        out.append(['\n'.join(al[c0:c1]),'\n'.join(al[c0:i1]+bl[j1:j2]+al[i2:c1])])
    return out
vp=[[F_PI,o,n] for o,n in hunks(par_pi,scvp_pi)]
s1o=" let bump=[ctx.bumps.sol_vault];let seeds:&[&[u8]]=&[b\"sol-vault\",&bump];\n crate::pump::cpi::sell("
s1n=" \n crate::pump::cpi::sell("
s2o=" },&[seeds])\n  .with_remaining_accounts(vec![clone_sell_info(a.bonding_curve_v2.as_ref())"
s2n=" },&[&[b\"sol-vault\",&[ctx.bumps.sol_vault]]])\n  .with_remaining_accounts(vec![clone_sell_info(a.bonding_curve_v2.as_ref())"
assert par_pi.count(s1o)==1 and par_pi.count(s2o)==1, (par_pi.count(s1o), par_pi.count(s2o))
seed=[[F_PI,s1o,s1n],[F_PI,s2o,s2n]]
st=[[F_ST,o,n] for o,n in hunks(work_st,scvp_st)]
print('vp hunks',len(vp),'st hunks',len(st))
W=['O0082','O0084']
specs=[{'label':'u1-vp','reps':vp,'windows':W},{'label':'u1-vp-st','reps':vp+st,'windows':W},
       {'label':'u1-seed','reps':seed,'windows':W},{'label':'u1-vp-seed','reps':vp+seed,'windows':W},
       {'label':'u1-vp-st-seed','reps':vp+st+seed,'windows':W}]
json.dump(specs,open(D+'/out/specs/u1.json','w'),indent=1)
