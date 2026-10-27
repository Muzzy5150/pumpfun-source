import sys,re
sys.path.insert(0,'/private/tmp/claude-501/-Users-shawwalters-Documents-Codex-2026-10-24-pumpfun-source/bf960843-6806-451b-a211-62c8b228d301/scratchpad/lanes/mayhem-b/build')
import irsurg, sbfdis, objsec
L=irsurg.L
pat='sweep_fees_admin17h34ff'
SEC='mayhem_recovered16mayhem_recovered16sweep_fees_admin17'
def renumber(body): return re.sub(r'%(\d+)\b', lambda m: '%v'+m.group(1), body)
def find(lines, pred):
    r=[k for k,l in enumerate(lines) if pred(l.strip())]; assert len(r)==1,(r,); return r[0]
def show(label):
    code=open(f'{L}/out/llc/{label}.bin','rb').read()
    out=[]
    for pc,raw in objsec.insns(code):
        if 1008<=pc<=1072:
            out.append(sbfdis.decode(code,None,pc,pc+len(raw),None,None)[0]['text'])
    print('   ', ' | '.join(out))
def move(lines, src_preds, dst_pred, after=True):
    """move lines matching src_preds (in given order) to after/before the line matching dst_pred"""
    picked=[lines[find(lines,p)] for p in src_preds]
    for t in picked: lines.remove(t)
    d=find(lines,dst_pred)
    pos=d+1 if after else d
    lines[pos:pos]=picked
    return lines
