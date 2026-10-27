#!/usr/bin/env python3
"""Extract a named function section from an ELF relocatable and compare with a window (masked)."""
import struct, sys, re
sys.path.insert(0, __import__('os').path.dirname(__file__))
import sbfdis
def sections(path):
    b=open(path,'rb').read()
    shoff,=struct.unpack_from('<Q',b,0x28); shentsize,shnum,shstrndx=struct.unpack_from('<HHH',b,0x3a)
    secs=[]
    for i in range(shnum):
        nm,ty,fl,ad,of,sz,ln,inf,al,es=struct.unpack_from('<IIQQQQIIQQ',b,shoff+i*shentsize); secs.append([nm,ty,of,sz])
    so=secs[shstrndx][2]
    out={}
    for nm,ty,of,sz in secs:
        name=b[so+nm:b.index(b'\0',so+nm)].decode()
        out[name]=b[of:of+sz]
    return out
def insns(code):
    out=[];pc=0
    while pc<len(code):
        op,regs,off,imm=struct.unpack_from('<BBhi',code,pc)
        size=16 if op==0x18 else 8
        out.append((pc,code[pc:pc+size]))
        pc+=size
    return out
def norm(code):
    # mask call imm and lddw imm (relocations not resolved in .o) and nothing else
    res=[]
    for pc,raw in insns(code):
        r=bytearray(raw)
        if raw[0]==0x85: r[4:8]=b'\0\0\0\0'
        if raw[0]==0x18: r[4:8]=b'\0\0\0\0'; r[12:16]=b'\0\0\0\0'
        res.append(bytes(r))
    return res
if __name__=='__main__':
    obj,func=sys.argv[1],sys.argv[2]
    secs=sections(obj)
    key=[k for k in secs if func in k]
    print(key[:3])
    code=secs[key[0]]
    open(sys.argv[3],'wb').write(code) if len(sys.argv)>3 else None
    print(len(code))
