import sys
sys.path.insert(0,'.')
import sbfdis, calls, measure
O=calls.O
def annotate(E, s, e, namefn, start=None, end=None):
    w=E.window(s,e)
    data={d['pc']:d for d in w['data_references']}
    for x in sbfdis.window_insns(E,s,e):
        off=x['pc']-s
        if start is not None and off<start: continue
        if end is not None and off>=end: break
        t=x['text']
        if x['op']==0x85 and t.startswith('call 0x'):
            t='call '+namefn(int(t.split()[1],16))
        if x['pc'] in data:
            d=data[x['pc']]; src=measure.source(E,d['target'])
            if src: t+=f'   ; LOC {src["path"].rstrip(chr(0)).split("/")[-1]}:{src["line"]}:{src["column"]}'
            else:
                tgt=d['target']
                # try string
                try:
                    bs=E.b[tgt:tgt+40]
                    txt=bs.split(b'\0')[0][:40]
                    t+=f'   ; DATA {tgt:#x} {txt!r}'
                except Exception: pass
        if (x['op'] & 7) == 5 and x['op'] not in (0x85,0x8d,0x95):
            # branch: show relative target
            import re
            m=re.search(r'(0x[0-9a-f]+)$',t)
            if m:
                tg=int(m.group(1),16); t=t[:m.start()]+f'@{tg-s}'
        print(f'{off:6d}  {t}')
if __name__=='__main__':
    if sys.argv[1]=='o':
        s=int(sys.argv[2]); e=calls.wins[s][1]
        annotate(O,s,e,calls.on,int(sys.argv[3]) if len(sys.argv)>3 else None,int(sys.argv[4]) if len(sys.argv)>4 else None)
    else:
        C,cf,cn=calls.cand(sys.argv[2])
        a=[a for a,(b,n) in cf.items() if sys.argv[3] in n][0]
        annotate(C,a,cf[a][0],cn,int(sys.argv[4]) if len(sys.argv)>4 else None,int(sys.argv[5]) if len(sys.argv)>5 else None)
