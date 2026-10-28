from pathlib import Path
import struct,sys,json
R=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent;sys.path.insert(0,str(R/'scripts'));from pump_compare_function_bytes import sections,body
class Ptr:
 def __init__(self,b,o=0):self.b,self.o=b,o
 def __add__(self,o):return Ptr(self.b,self.o+o)
 def __repr__(self):return f'{self.b}{self.o:+#x}'
 def key(self):return(self.b,self.o)
def trace(p,start,size,invoke):
 raw=p.read_bytes();z=body(raw,sections(raw),start,size);regs={1:Ptr('out'),2:Ptr('target'),3:Ptr('authority'),4:Ptr('mintkey'),5:Ptr('args'),10:Ptr('stack')};mem={('args',o):v for o,v in [(-0x1000,Ptr('tokenkey')),(-0xff8,Ptr('system')),(-0xff0,Ptr('mintinfo')),(-0xfe8,1),(-0xfe0,Ptr('payer')),(-0xfd8,Ptr('tokeninfo'))]};pc=0;path=[];calls=0
 def ld(addr):
  if not isinstance(addr,Ptr):return Ptr(f'*({addr!r})')
  if addr.key() in mem:return mem[addr.key()]
  if addr.b in ['payer','target','authority','mintinfo','system','tokeninfo']:
   return Ptr(addr.b+{0:'.key',8:'.lamports_rc',16:'.data_rc',24:'.owner',32:'.rent',40:'.signer',41:'.writable',42:'.executable'}.get(addr.o,f'.field{addr.o}'))
  return Ptr(f'*({addr!r})')
 for step in range(1500):
  op,rr,off,imm=struct.unpack_from('<BBhi',z,pc);dst,src=rr&15,rr>>4;nextpc=pc+8;v=regs.get(src,Ptr('unknown'))
  if op==0x18:
   regs[dst]=struct.unpack_from('<I',z,pc+4)[0]|struct.unpack_from('<I',z,pc+12)[0]<<32;nextpc+=8
  elif op in [0xb7,0xb4]:regs[dst]=imm
  elif op==0xbf:regs[dst]=v
  elif op in [0x79,0x71,0x69,0x61]:regs[dst]=ld(regs[src]+off)
  elif op in [0x7b,0x73,0x6b,0x63]:mem[(regs[dst]+off).key()]=v
  elif op in [0x7a,0x72,0x6a,0x62]:mem[(regs[dst]+off).key()]=imm
  elif op==0x07:regs[dst]=regs[dst]+imm
  elif op in [0x67,0x77]:
   if isinstance(regs[dst],int):regs[dst]=regs[dst]<<imm if op==0x67 else regs[dst]>>imm
  elif op==0x85:
   dest=start+pc+8+imm*8
   if dest==invoke:
    a=regs[3];out=[str(ld(a+48*i))for i in range(regs[4])];return {'instruction':hex(start+pc),'array':out,'trace':path}
   if dest in [0x1b3678]:regs[0]=0 # expected ATA / system-owned branch
   path.append({'offset':hex(pc),'call':hex(dest)})
  elif op in [0x15,0x55,0x1d,0x5d,0x05]:
   left=regs.get(dst);right=v if op in [0x1d,0x5d]else imm
   eq=isinstance(left,int)and isinstance(right,int)and left==right
   take=op==0x05 or (eq if op in [0x15,0x1d]else not eq)
   if take:nextpc+=off*8
  elif op==0x95:raise Exception('exit before invoke',hex(pc),path[-5:])
  else:raise Exception('unhandled',hex(pc),hex(op))
  pc=nextpc
  if not 0<=pc<len(z):raise Exception('pc',hex(pc))
 raise Exception('timeout')
r=trace(R/'evidence/original/pump/deployed.so',0x14910,6080,0x1a0508);print(r['array']);(W/'INFO-ORDER-TRACE.json').write_text(json.dumps(r,indent=2)+'\n')
