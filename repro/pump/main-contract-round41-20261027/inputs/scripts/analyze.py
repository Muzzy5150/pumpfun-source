#!/usr/bin/env python3
"""Offline ELF layout, string provenance and public-interface inventory."""
import hashlib,json,pathlib,re,struct
ROOT=pathlib.Path(__file__).resolve().parents[1]
def elf_layout(b):
    assert b[:6]==b'\x7fELF\x02\x01'
    h=struct.unpack_from('<HHIQQQIHHHHHH',b,16)
    _,machine,_,entry,phoff,shoff,flags,ehsize,phsize,phnum,shsize,shnum,shstr=h
    assert phsize==56 and shsize==64 and shnum>0
    raw=[struct.unpack_from('<IIQQQQIIQQ',b,shoff+i*shsize) for i in range(shnum)]
    names=b[raw[shstr][4]:raw[shstr][4]+raw[shstr][5]]
    end=max(ehsize,phoff+phsize*phnum,shoff+shsize*shnum)
    sections=[]
    for s in raw:
        name=names[s[0]:].split(b'\0')[0].decode()
        if s[1]!=8: end=max(end,s[4]+s[5])
        sections.append({'name':name,'type':s[1],'offset':s[4],'size':s[5],'address':s[3],'flags':s[2]})
    for i in range(phnum):
        p=struct.unpack_from('<IIQQQQQQ',b,phoff+i*phsize); end=max(end,p[2]+p[5])
    assert end<=len(b)
    return {'machine':machine,'entry':entry,'flags':flags,'elf_extent':end,'allocation_bytes':len(b),'trailing_bytes':len(b)-end,'trailing_all_zero':not any(b[end:]),'elf_sha256':hashlib.sha256(b[:end]).hexdigest(),'sections':sections}
def analyze():
    out={}
    for name in json.loads((ROOT/'repro/programs.json').read_text()):
        b=(ROOT/f'evidence/original/{name}/deployed.so').read_bytes(); r=elf_layout(b)
        r['source_path_evidence']=[{'offset':m.start(),'path':m.group().decode()} for m in re.finditer(rb'(?:programs|/home/runner/work/platform-tools)[a-zA-Z0-9_./-]+?\.rs',b)]
        r['instruction_log_names']=sorted(set(m.group(1).decode() for m in re.finditer(rb'Instruction: ([A-Z][A-Za-z0-9]*?)(?=Instruction:|[^A-Za-z0-9]|$)',b)))
        r['compiler_version']='unresolved'; r['dependency_versions']='unresolved'; out[name]=r
    (ROOT/'evidence/binary-analysis.json').write_text(json.dumps(out,indent=2)+'\n')
    inventory={}
    for f in (ROOT/'evidence/upstream').glob('pump*.json'):
        d=json.loads(f.read_text()); addresses={}
        def walk(accounts,ix):
            for a in accounts:
                if 'address' in a: addresses.setdefault(a['address'],[]).append({'instruction':ix,'account':a['name']})
                walk(a.get('accounts',[]),ix)
        for ix in d['instructions']: walk(ix['accounts'],ix['name'])
        inventory[f.stem]={'address':d['address'],'metadata':d.get('metadata'),'instructions':len(d['instructions']),'fixed_addresses':addresses}
    (ROOT/'evidence/interface-inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
    for n,r in out.items(): print(n,'ELF',r['elf_extent'],'padding',r['trailing_bytes'],'zero',r['trailing_all_zero'])
if __name__=='__main__': analyze()
