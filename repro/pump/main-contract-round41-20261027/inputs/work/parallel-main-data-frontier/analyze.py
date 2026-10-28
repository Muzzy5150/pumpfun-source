"""Rank unmatched instruction bodies and map unambiguous exact-body data references.

These are triage observations, not new body matches or data-object identity claims.
Fixed-size data prefixes may include bytes beyond the referenced object's bounds.
"""
from pathlib import Path
import argparse, collections, hashlib, json, struct, sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from pump_compare_function_bytes import body,normalize
from pump_quote_control_function_match import sections,candidate_functions
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--candidate',type=Path,required=True)
parser.add_argument('--inventory',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
original_path=ROOT/'evidence/original/pump/deployed.so'
ob=original_path.read_bytes();cb=args.candidate.read_bytes();os=sections(ob);cs=sections(cb)
sha=lambda data:hashlib.sha256(data).hexdigest()
inventory=json.loads(args.inventory.read_text())
assert sha(ob)==inventory['original_sha256'] and sha(cb)==inventory['candidate_sha256']
functions=collections.defaultdict(list)
for start,length,symbol in candidate_functions(args.candidate,str(Path.home()/'.cache/solana/v1.52/platform-tools/llvm/bin/llvm-objdump'),'.'):
    raw=body(cb,cs,start,length);norm,operands=normalize(raw,start,cs)
    slots=struct.unpack('<'+'Q'*(length//8),norm)
    functions[length].append((start,symbol,norm,slots,operands))
nearest=[];references=collections.defaultdict(lambda:collections.defaultdict(list))
for row in inventory['windows']:
    raw=body(ob,os,row['start'],row['bytes']);norm,operands=normalize(raw,row['start'],os)
    if not row['normalized_matches']:
        slots=struct.unpack('<'+'Q'*(len(norm)//8),norm)
        ranks=[]
        for start,symbol,cn,cslots,co in functions[row['bytes']]:
            distance=sum(a!=b for a,b in zip(slots,cslots))
            ranks.append((distance,start,symbol,cn,co))
        for distance,start,symbol,cn,co in sorted(ranks,key=lambda x:(x[0],x[1]))[:3]:
            diffs=[]
            if distance<=12:
                for offset in range(0,len(norm),8):
                    if norm[offset:offset+8]!=cn[offset:offset+8]:
                        diffs.append({'offset':offset,'original':norm[offset:offset+8].hex(),'candidate':cn[offset:offset+8].hex(),'original_fields':struct.unpack('<BBhi',norm[offset:offset+8]),'candidate_fields':struct.unpack('<BBhi',cn[offset:offset+8])})
            nearest.append({'original_start':hex(row['start']),'bytes':row['bytes'],'candidate_start':hex(start),'candidate_symbol':symbol,'different_slots':distance,'slot_count':len(slots),'fraction_different':distance/len(slots),'differences':diffs})
    elif len(row['normalized_matches'])==1:
        match=row['normalized_matches'][0]
        co={x['offset']:x for x in match['operands']}
        for item in operands:
            other=co.get(item['offset'])
            if item['kind']=='elf-pointer' and other and other['kind']=='elf-pointer':
                references[item['value']][other['value']].append({'original_function':hex(row['start']),'candidate_function':hex(match['start']),'offset':item['offset']})
def prefix(image,image_sections,address,size=64):
    choices=[(name,sec)for name,sec in image_sections.items()if sec['addr']>0 and sec['addr']<=address<sec['addr']+sec['size']]
    if not choices:return None
    name,sec=choices[0];n=min(size,sec['addr']+sec['size']-address);offset=sec['offset']+address-sec['addr']
    return name,image[offset:offset+n]
data_rows=[];ambiguous=[]
for address,candidates in sorted(references.items()):
    if len(candidates)!=1:
        ambiguous.append({'original':hex(address),'candidate_addresses':[hex(x)for x in candidates]});continue
    candidate,uses=next(iter(candidates.items()));left=prefix(ob,os,address);right=prefix(cb,cs,candidate)
    if left is None or right is None:continue
    n=min(len(left[1]),len(right[1]));common=0
    while common<n and left[1][common]==right[1][common]:common+=1
    data_rows.append({'original':hex(address),'candidate':hex(candidate),'original_section':left[0],'candidate_section':right[0],'examined_prefix_bytes':n,'raw_common_prefix_bytes':common,'original_prefix':left[1].hex(),'candidate_prefix':right[1].hex(),'uses':uses})
nearest.sort(key=lambda row:(row['different_slots'],row['fraction_different'],-row['bytes']))
result={'scope':__doc__,'original_sha256':sha(ob),'candidate_sha256':sha(cb),'inventory_sha256':sha(args.inventory.read_bytes()),'analysis_script_sha256':sha(Path(__file__).read_bytes()),'counts':{'unmatched_original_windows':inventory['counts']['unmatched'],'ranked_equal_length_pairs':len(nearest),'near_pairs_at_most_3_slots':sum(x['different_slots']<=3 for x in nearest),'unambiguous_data_reference_pairs':len(data_rows),'ambiguous_data_references':len(ambiguous)},'nearest_equal_length':nearest,'unambiguous_data_prefixes':data_rows,'ambiguous_data_references':ambiguous,'goal_complete':False}
args.output.write_text(json.dumps(result,indent=2)+'\n')
print(result['counts'])
print([{k:r[k]for k in ['original_start','bytes','candidate_symbol','different_slots']}for r in nearest[:20]])
