from pathlib import Path
import json,hashlib,sys
from solders.pubkey import Pubkey
R=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'scripts'))
from pump_compare_function_bytes import sections
original=R/'evidence/original/pump/deployed.so';blob=original.read_bytes();ss=sections(blob)
def key(address):
 for section in ss.values():
  if section['addr'] <= address < address+32 <= section['addr']+section['size']:
   offset=section['offset']+address-section['addr'];return str(Pubkey(blob[offset:offset+32]))
inv=json.loads((R/'work/parallel-main-integration/build-round30/normalized-inventory.json').read_text());calls=[]
for target in [0x17bc48,0x1a918,0x1e7c0]:
 for row in inv['windows']:
  for op in row['original_operands']:
   if op['kind']=='direct-call' and op['target']==target:
    calls.append({'target':hex(target),'caller':hex(row['start']),'site':hex(row['start']+op['offset']),'offset':hex(op['offset'])})
proof={
 'scope':'Original-backed main mint admission caller and boolean policy. Earlier closed scanner body controls are not repeated.',
 'original_sha256':hashlib.sha256(blob).hexdigest(),
 'call_edges':calls,
 'scanner':'r1=data pointer, r2=len, r3=boolean; only direct call sets r3=1. No main false-policy route identified.',
 'masks':{'0x6015052':[i for i in range(64) if (0x6015052>>i)&1],'0xc0000':[18,19]},
 'wrapper':'0x1a918 borrows account data, calls scanner with true, returns6063 UnsupportedQuoteMint on false; source programs/pump/src/create_v2.rs:528.',
 'caller_exception':{
  'site':'0x22008','prior_branch':hex(17405*8),
  'condition':'Stored quote mint key, same local previously tested against WSOL and9pan, equals constant0x1b5c88; equality skips validation.',
  'pubkey':key(0x1b5c88),
  'other_local_comparisons':{hex(a):key(a) for a in [0x1b5cc8,0x1b5a88]},
  'runtime':'32case matrix: Tokenkeg variants unchanged;6differences occur for literalPUMP quote +Token2022. Corrected by exception under existing Token2022 gate.'},
 'prior_semantic_fix':'work/parallel-main-create-extension-validation/QUOTE-VALIDATOR-REVIEW01.json retained; current scanner matches107additional boundary probes.',
 'evidence_sha256':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [W/'original-create-v2.asm',W/'original-wrapper.asm',W/'original-callsite.asm',W/'gate01.json.gz',W/'policy01.json.gz']}}
(W/'CALLER-POLICY-PROOF.json').write_text(json.dumps(proof,indent=2)+'\n')
print(calls,proof['masks'])
