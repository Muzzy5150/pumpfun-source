import sys, struct
sys.path.insert(0,'.')
import sbfdis, measure
from pathlib import Path
def recs(E, s, e):
    out=[]
    w=E.window(s,e)
    for d in w['data_references']:
        src=measure.source(E, d['target'])
        if src: out.append((d['offset'], src['path'].rstrip('\0'), src['line'], src['column']))
    return out
def raw_loc(E, addr):
    # Location { file: &str (ptr,len), line: u32, col: u32 }
    ptr,ln=struct.unpack_from('<QQ',E.b,addr); line,col=struct.unpack_from('<II',E.b,addr+16)
    return ptr,ln,line,col
if __name__=='__main__':
    import winreport
    O=winreport.O
    C=sbfdis.elf(sys.argv[1]); cf=sbfdis.funcs(C)
    for wid,s,e,pat in winreport.W:
        if len(sys.argv)>2 and wid not in sys.argv[2:]: continue
        a=[a for a,(b,n) in cf.items() if pat in n][0]; b=cf[a][0]
        ro=recs(O,s,e); rc=recs(C,a,b)
        print(wid,'orig',[(r[1].split('/')[-1],r[2],r[3]) for r in ro])
        print(wid,'cand',[(r[1].split('/')[-1],r[2],r[3]) for r in rc])
