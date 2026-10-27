import sys
sys.path.insert(0,'.')
import sbfdis, measure, calls, winreport
def uses(E, s, e, namefn):
    ins=sbfdis.window_insns(E,s,e)
    w=E.window(s,e)
    out=[]
    for d in w['data_references']:
        src=measure.source(E, d['target'])
        if not src: continue
        # find the next call after this lddw
        idx=[i for i,x in enumerate(ins) if x['pc']-s==d['offset']][0]
        nxt=None
        for x in ins[idx:idx+12]:
            if x['op']==0x85:
                t=x['text']
                nxt=namefn(int(t.split()[1],16)) if t.startswith('call 0x') else t
                break
        out.append((d['offset'], src['path'].rstrip('\0').split('/')[-1], src['line'], src['column'], nxt))
    return out
if __name__=='__main__':
    which=sys.argv[1]
    if which=='o':
        for wid,s,e,pat in winreport.W:
            if wid in sys.argv[2:]:
                for r in uses(calls.O,s,e,calls.on): print(wid,r)
    else:
        C,cf,cn=calls.cand(sys.argv[2])
        for a,(b,n) in sorted(cf.items()):
            if sys.argv[3] in n:
                for r in uses(C,a,b,cn): print(r)
