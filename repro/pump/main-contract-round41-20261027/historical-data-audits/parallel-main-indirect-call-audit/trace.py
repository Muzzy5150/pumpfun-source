#!/usr/bin/env python3
"""Conservative intraprocedural provenance for original Pump CALL_REG sites.

This is static register/stack analysis, not execution. Unknown operations and
caller-clobbered registers are widened to unknown; all branches are retained.
"""
from pathlib import Path
import argparse, bisect, collections, hashlib, json, struct

ROOT=Path(__file__).resolve().parents[2]
LIMIT=8
UNKNOWN=None

def values(x): return frozenset([x])
def union(a,b):
    if a is None or b is None:return None
    c=a|b
    return c if len(c)<=LIMIT else None
def scalar(x):
    if x[0]=='const':return x[1]
    if x[0]=='roload':return x[3]
    return None
def add(x,n):
    if n==0:return x
    if x[0]=='stack':return ('stack',x[1],x[2]+n)
    if x[0]=='const':return ('const',(x[1]+n)&((1<<64)-1))
    if x[0]=='add':return ('add',x[1],x[2]+n)
    return ('add',x,n)
def depth(x):return 1+max([depth(v)for v in x[1:]if isinstance(v,tuple)]or[0])
def map_values(v,fn):
    if v is None:return None
    out=frozenset(fn(x)for x in v)
    return out if len(out)<=LIMIT and all(depth(x)<=7 for x in out)else None
def fmt(x):
    if x is None:return 'unknown'
    if x[0]=='const':return hex(x[1])
    if x[0]=='arg':return f'arg_r{x[2]}@{x[1]:#x}'
    if x[0]=='stack':return f'frame@{x[1]:#x}[{x[2]:+#x}]'
    if x[0]=='add':return f'({fmt(x[1])}{x[2]:+#x})'
    if x[0]=='load':return f'load{x[1]}({fmt(x[2])})@{x[3]:#x}'
    if x[0]=='roload':return f'roload{x[4]}({x[2]:#x})={x[3]:#x}@{x[1]:#x}'
    return str(x)

class Analyzer:
    def __init__(self):
        self.path=ROOT/'evidence/original/pump/deployed.so';self.data=self.path.read_bytes()
        self.inventory=json.loads((ROOT/'work/parallel-main-window-boundary-audit/AUDIT.json').read_text())
        self.windows=self.inventory['windows'];self.starts=[w['start']for w in self.windows];self.by_start={w['start']:w for w in self.windows}
        self.instructions={};self.reloc={};self.sections=[]
        b=self.data;shoff=struct.unpack_from('<Q',b,40)[0];size,n,ni=struct.unpack_from('<HHH',b,58);hs=[struct.unpack_from('<IIQQQQIIQQ',b,shoff+i*size)for i in range(n)];st=hs[ni];names=b[st[4]:st[4]+st[5]]
        for h in hs:
            name=names[h[0]:].split(b'\0',1)[0].decode();self.sections.append(dict(name=name,address=h[3],offset=h[4],size=h[5],type=h[1]))
            if h[1]==9:
                for p in range(h[4],h[4]+h[5],16):
                    at,info=struct.unpack_from('<QQ',b,p);self.reloc[at]=info&0xffffffff
        text=next(s for s in self.sections if s['name']=='.text');self.lo=text['address'];self.hi=self.lo+text['size'];pc=self.lo
        while pc<self.hi:
            op,regs,off,imm=struct.unpack_from('<BBhi',b,text['offset']+pc-self.lo);width=16 if op==0x18 else 8
            self.instructions[pc]=(op,regs&15,regs>>4,off,imm,width);pc+=width
        self.noreturn=set(self.inventory['nonreturning_cfg_inference']['functions'])
        self.cache={}
    def read_ro(self,address,width,site):
        s=next((s for s in self.sections if s['name']in('.rodata','.data.rel.ro')and s['address']<=address and address+width//8<=s['address']+s['size']),None)
        if not s:return None
        off=s['offset']+address-s['address'];raw=self.data[off:off+width//8]
        value=int.from_bytes(raw,'little')
        if width==64 and self.reloc.get(address)==8:value>>=32
        return ('roload',site,address,value,width)
    def load(self,base,width,site,mem):
        if base is None:return None
        out=[]
        for x in base:
            if x[0]=='stack':
                v=mem.get((x[1],x[2],width))
                if v is None:return None
                out.extend(v)
            elif (n:=scalar(x))is not None and (r:=self.read_ro(n,width,site))is not None:out.append(r)
            else:out.append(('load',width,x,site))
        r=frozenset(out)
        return r if len(r)<=LIMIT and all(depth(x)<=7 for x in r)else None
    def analyze(self,start):
        if start in self.cache:return self.cache[start]
        w=self.by_start[start];end=w['end'];initial=tuple(values(('arg',start,i))if 1<=i<=5 else values(('stack',start,0))if i==10 else None for i in range(11))
        states={start:(initial,{})};todo=collections.deque([start]);callx={};calls={};updates=0
        def merge(pc,regs,mem):
            nonlocal updates
            if not start<=pc<end:return
            state=(tuple(regs),mem)
            if pc not in states:states[pc]=state;todo.append(pc);return
            oldr,oldm=states[pc];newr=tuple(union(a,b)for a,b in zip(oldr,regs));newm={k:union(oldm.get(k),mem.get(k))for k in oldm.keys()|mem.keys()}
            newm={k:v for k,v in newm.items()if v is not None}
            if newr!=oldr or newm!=oldm:states[pc]=(newr,newm);todo.append(pc);updates+=1
        while todo:
            pc=todo.popleft();rr,mm=states[pc];regs=list(rr);mem=mm.copy();op,dst,src,off,imm,width=self.instructions[pc];nextpc=pc+width
            if op==0x95:continue
            if op in (0x85,0x8d):
                if op==0x8d:
                    v=regs[imm]if 0<=imm<=10 else None
                    callx[pc]=union(callx[pc],v)if pc in callx else v
                elif self.reloc.get(pc)!=10:
                    target=pc+8+imm*8
                    args=tuple(regs[1:6])
                    if pc in calls:
                        old=calls[pc];joined={k:union(old[2].get(k),mem.get(k))for k in old[2].keys()|mem.keys()}
                        calls[pc]=(target,tuple(union(a,b)for a,b in zip(old[1],args)),{k:v for k,v in joined.items()if v is not None})
                    else:calls[pc]=(target,args,mem.copy())
                    if target in self.noreturn:continue
                # Only frame slots are modeled; conservatively forget them at calls.
                for i in range(6):regs[i]=None
                mem={};merge(nextpc,regs,mem);continue
            if op==0x18:
                n=struct.unpack_from('<I',self.data,pc+4)[0]|struct.unpack_from('<I',self.data,pc+12)[0]<<32
                regs[dst]=values(('const',n))
            elif op&7 in(4,7):
                operation=op&0xf0;rhs=regs[src]if op&8 else values(('const',imm&((1<<64)-1)))
                if operation==0xb0:regs[dst]=rhs
                elif operation==0 and rhs is not None and len(rhs)==1 and scalar(next(iter(rhs)))is not None:
                    n=scalar(next(iter(rhs)));n=n-(1<<64)if n>>63 else n;regs[dst]=map_values(regs[dst],lambda x:add(x,n))
                elif operation==0x10 and rhs is not None and len(rhs)==1 and scalar(next(iter(rhs)))is not None:
                    n=scalar(next(iter(rhs)));regs[dst]=map_values(regs[dst],lambda x:add(x,-n))
                else:regs[dst]=None
            elif op&7==1:
                bits={0:32,8:16,16:8,24:64}.get(op&0x18)
                regs[dst]=self.load(map_values(regs[src],lambda x:add(x,off)),bits,pc,mem)if bits else None
            elif op&7 in(2,3):
                bits={0:32,8:16,16:8,24:64}.get(op&0x18);address=map_values(regs[dst],lambda x:add(x,off))
                val=regs[src]if op&7==3 else values(('const',imm&((1<<bits)-1)))
                if address is not None and len(address)==1 and next(iter(address))[0]=='stack':
                    frame,a=next(iter(address))[1:]
                    for k in list(mem):
                        if frame==k[0] and a<k[1]+k[2]//8 and k[1]<a+bits//8:mem.pop(k)
                    if val is not None:mem[(frame,a,bits)]=val
                else:mem={}
            elif op&7 in(5,6):
                merge(pc+8+off*8,regs,mem)
                if op&0xf0==0:continue
            else:
                regs[dst]=None
            merge(nextpc,regs,mem)
        result=dict(callx=callx,calls=calls,updates=updates,state_count=len(states));self.cache[start]=result;return result
    def instantiate(self,expr,callee,args,mem):
        kind=expr[0]
        if kind=='arg':return args[expr[2]-1]if expr[1]==callee else values(expr)
        if kind=='add':return map_values(self.instantiate(expr[1],callee,args,mem),lambda x:add(x,expr[2]))
        if kind=='load':return self.load(self.instantiate(expr[2],callee,args,mem),expr[1],expr[3],mem)
        return values(expr)

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();x=Analyzer();rows=[]
    for site in x.inventory['indirect_calls']:
        r=x.analyze(site['owner']);v=r['callx'].get(site['site']);constant=sorted({n for e in v or[]if(n:=scalar(e))is not None});unresolved=v is None or any(scalar(e)is None for e in v)
        rows.append(dict(**site,provenance=[fmt(e)for e in sorted(v or[],key=str)]if v is not None else['unknown'],expressions=list(v)if v is not None else None,constant_values=constant,all_paths_constant=not unresolved,constant_text_targets=[n for n in constant if n in x.by_start]))
    direct_edges=[]
    targets={r['owner']for r in rows}
    callers={r['owner']for r in x.inventory['calls']if r['target']in targets}
    by_owner=collections.defaultdict(list)
    for r in rows:by_owner[r['owner']].append(r)
    for caller in sorted(callers):
        for callsite,(callee,args,mem)in x.analyze(caller)['calls'].items():
            if callee not in targets:continue
            for site in by_owner[callee]:
                local=x.analyze(callee)['callx'].get(site['site'])
                target_values=frozenset()
                for expr in local or []:target_values=union(target_values,x.instantiate(expr,callee,args,mem))
                if local is None:target_values=None
                constants=sorted({n for e in target_values or []if(n:=scalar(e))is not None and n in x.by_start})
                if constants:
                    direct_edges.append(dict(caller=caller,direct_callsite=callsite,callee=callee,indirect_callsite=site['site'],targets=constants,
                        exhaustive_for_this_callsite=target_values is not None and all(scalar(e)in x.by_start for e in target_values),
                        provenance=[fmt(e)for e in sorted(target_values or[],key=str)]))
    d=dict(scope=__doc__,original_sha256=hashlib.sha256(x.data).hexdigest(),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),counts=dict(sites=len(rows),owners=len(targets),analyzed_functions=len(x.cache),all_paths_constant=sum(r['all_paths_constant']for r in rows),with_constant_text_targets=sum(bool(r['constant_text_targets'])for r in rows),resolved_direct_call_contexts=len(direct_edges)),sites=rows,direct_call_contexts=direct_edges)
    a.output.write_text(json.dumps(d,indent=2)+'\n');print(d['counts'])
if __name__=='__main__':main()
