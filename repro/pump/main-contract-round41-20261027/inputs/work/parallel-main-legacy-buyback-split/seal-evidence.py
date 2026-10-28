from pathlib import Path
import bisect,csv,difflib,gzip,hashlib,json,struct,sys
ROOT=Path(__file__).resolve().parents[2];P=Path(__file__).parent;sys.path.insert(0,str(ROOT/'scripts'))
from pump_compare_function_bytes import body,normalize
from pump_quote_control_function_match import sections,candidate_functions
base=ROOT/'work/parallel-main-buyback-split/source03';source=P/'source03';candidate=P/'build04/unstripped.so'
files=[str(p.relative_to(source)) for p in source.rglob('*') if p.is_file() and (not (base/p.relative_to(source)).exists() or p.read_bytes()!=(base/p.relative_to(source)).read_bytes())]
assert set(files)=={'src/buy_v2.rs','src/v2_recipient_payments.rs','src/legacy_buy.rs','src/legacy_sell.rs'},files
patch=''.join(''.join(difflib.unified_diff((base/name).read_text().splitlines(True),(source/name).read_text().splitlines(True),fromfile='a/programs/pump/'+name,tofile='b/programs/pump/'+name)) for name in files)
(P/'legacy-buyback-split.patch').write_text(patch)
a=json.load(open(P/'inventory03.json'));b=json.load(open(ROOT/'work/parallel-main-buyback-split/inventory03.json'))
am={r['start'] for r in a['windows'] if r['normalized_matches']};bm={r['start'] for r in b['windows'] if r['normalized_matches']}
o=(ROOT/'evidence/original/pump/deployed.so').read_bytes();c=candidate.read_bytes();os=sections(o);cs=sections(c)
comp=json.load(open(P/'helper-comparison03.json'));h=comp['candidates'][0];assert h['normalized_equal']
lengths={int(r['original_start']):int(r['bytes']) for r in csv.DictReader(open(ROOT/'repro/reconstruction-status-2026-10-26/functions.tsv'),delimiter='\t') if r['program']=='pump'}
co=[x for x in h['operands'] if x['kind']=='direct-call'];oo=[x for x in comp['original_operands'] if x['kind']=='direct-call'];callees=[]
for x,y in zip(oo,co):
 assert x['offset']==y['offset'];size=lengths[x['target']]
 eq=normalize(body(o,os,x['target'],size),x['target'],os)[0]==normalize(body(c,cs,y['target'],size),y['target'],cs)[0]
 callees.append({'offset':x['offset'],'original':hex(x['target']),'candidate':hex(y['target']),'bytes':size,'normalized_target_equal':eq});assert eq
funcs=sorted(candidate_functions(candidate,str(Path.home()/'.cache/solana/v1.52/platform-tools/llvm/bin/llvm-objdump'),'.'));starts=[f[0] for f in funcs]
text=body(c,cs,cs['.text']['addr'],cs['.text']['size']);sites=[]
for at in range(0,len(text),8):
 op,regs,off,imm=struct.unpack_from('<BBhi',text,at)
 pos=cs['.text']['addr']+at
 if op==0x85 and regs>>4==1 and pos+8+imm*8==h['start']:
  owner=funcs[bisect.bisect_right(starts,pos)-1];sites.append({'site':hex(pos),'owner_start':hex(owner[0]),'owner':owner[2]})
report={'source':str(source.relative_to(ROOT)),'base':str(base.relative_to(ROOT)),'files':{f:hashlib.sha256((source/f).read_bytes()).hexdigest() for f in files},'candidate_sha256':hashlib.sha256((P/'build04/candidate.so').read_bytes()).hexdigest(),'unstripped_sha256':hashlib.sha256(c).hexdigest(),'inventory':a['counts'],'gained':[hex(i) for i in sorted(am-bm)],'lost':[hex(i) for i in sorted(bm-am)],'helper':{'original':'0x9a048','candidate':hex(h['start']),'bytes':h['bytes'],'normalized_equal':h['normalized_equal'],'callees':callees,'live_callers':sites},'original_payment_order':['creator/cashback fee before buyback lookup','seller proceeds via0x95bd8 at0x153c38','split0x9a048 at0x153ca8','buyback via0x95f38 at0x153f88 if nonzero','net protocol via0x95bd8 at0x153cf8 if nonzero'],'scope':'Main-only Rust source correction. All source coordinates remain truthful. Full original ELF identity remains false.'}
(P/'EXACT-EVIDENCE.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'changed_files':files,'gained':report['gained'],'lost':report['lost'],'helper_live_calls':len(sites),'all_callees_equal':all(x['normalized_target_equal'] for x in callees)}))
