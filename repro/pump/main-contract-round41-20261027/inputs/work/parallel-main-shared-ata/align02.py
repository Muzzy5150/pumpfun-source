from pathlib import Path
import struct,sys,json,difflib
R=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent;sys.path.insert(0,str(R/'scripts'));from pump_compare_function_bytes import sections,body,normalize
j=json.loads((W/'helper02.json').read_text());c=j['candidates'][0]
def read(p,start,n):
 b=p.read_bytes();z,_=normalize(body(b,sections(b),start,n),start,sections(b));out=[]
 for i in range(0,n,8):
  op,reg,off,imm=struct.unpack_from('<BBhi',z,i)
  # Ignore register allocation and frame-slot positions to locate structural changes only.
  if op&7 in [4,7] and op not in [0xb7,0xb4]:imm=0
  if op&7 in [5,6] and op not in [0x85,0x95]:imm=0
  out.append((op,imm))
 return out
a=read(R/'evidence/original/pump/deployed.so',j['original_start'],j['original_bytes']);b=read(W/'build02/unstripped.so',c['start'],c['bytes']);s=difflib.SequenceMatcher(None,a,b,autojunk=False)
ops=[{'kind':t,'original':[hex(i*8),hex(e*8)],'candidate':[hex(k*8),hex(l*8)],'original_ops':a[i:e],'candidate_ops':b[k:l]}for t,i,e,k,l in s.get_opcodes()if t!='equal'];(W/'STRUCTURAL-ALIGN02.json').write_text(json.dumps({'scope':'Opcode-only alignment for local structural localization; NOT an equality mask or byte-equivalence claim.','edits':ops},indent=2)+'\n')
for row in ops:print(row)
