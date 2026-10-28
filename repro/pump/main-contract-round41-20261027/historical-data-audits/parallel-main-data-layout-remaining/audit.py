#!/usr/bin/env python3
"""Read-only classification of the 240 previously unclassified data pairs.

Candidate symbol extents are facts about that ELF. Candidate-sized original
reads and Rust-role hypotheses do not authenticate original allocation extents.
"""
from pathlib import Path
import argparse, collections, importlib.util, json, struct, sys, hashlib
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);out=importlib.util.module_from_spec(spec);spec.loader.exec_module(out);return out

def objects(image, symbol_type=1):
    raw=image.raw;at=struct.unpack_from('<Q',raw,40)[0];width,n,ni=struct.unpack_from('<HHH',raw,58);headers=[struct.unpack_from('<IIQQQQIIQQ',raw,at+i*width)for i in range(n)];rows=collections.defaultdict(list)
    for h in headers:
        if h[1]not in(2,11):continue
        st=headers[h[6]];strings=raw[st[4]:st[4]+st[5]]
        for p in range(h[4],h[4]+h[5],h[9]):
            name,info,other,index,value,size=struct.unpack_from('<IBBHQQ',raw,p)
            if info&15==symbol_type and size:rows[value].append(dict(name=strings[name:].split(b'\0',1)[0].decode(),start=value,bytes=size,section_index=index))
    return rows

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--summary',type=Path,required=True);args=p.parse_args()
    helper_path=ROOT/'work/parallel-main-data-layout-proof/audit.py';helper=module('bounded_layout',helper_path)
    trace_path=ROOT/'work/parallel-main-indirect-call-audit/trace.py';trace=module('bounded_trace',trace_path)
    original=helper.Image(ROOT/'evidence/original/pump/deployed.so');candidate=helper.Image(ROOT/'work/parallel-main-integration/build-round24-final/unstripped.so');symbols=objects(candidate);function_symbols=objects(candidate,2)
    previous_path=ROOT/'work/parallel-main-data-layout-proof/AUDIT.json';previous=json.loads(previous_path.read_text());remaining=set(previous['unclassified_data_rel_ro_addresses'])
    frontier_path=ROOT/'work/parallel-main-data-frontier/round24-frontier.json';frontier=json.loads(frontier_path.read_text());pairs={int(r['original'],16):r for r in frontier['unambiguous_data_prefixes']}
    inventory_path=ROOT/'work/parallel-main-integration/build-round24-final/normalized-inventory.json';inventory=json.loads(inventory_path.read_text());by_start={r['start']:r for r in inventory['windows']}
    assert sha(original.path)==frontier['original_sha256'] and sha(candidate.path)==frontier['candidate_sha256']
    assert sha(inventory_path)==frontier['inventory_sha256'] and len(remaining)==240
    analyzer=trace.Analyzer();owners={int(u['original_function'],16)for a in remaining for u in pairs[a]['uses']}
    format_uses=collections.defaultdict(list);constructors=[]
    constructor_calls=[c for c in analyzer.inventory['calls']if c['target']==0x1a9db0]
    owners|={c['owner']for c in constructor_calls}
    for owner in sorted(owners):
        for pc,(target,call_args,mem)in analyzer.analyze(owner)['calls'].items():
            if target==0x1a9db0:
                vals={trace.scalar(v)for v in call_args[2]or[]};constructors.append(dict(owner=owner,call=pc,vtable_values=sorted(v for v in vals if v is not None),unknown=call_args[2]is None or None in vals))
            arg={0x1ab248:2,0x1ac890:1,0x1ae360:3}.get(target)
            if arg is None:continue
            for expression in call_args[arg-1]or[]:
                if expression[0]!='stack':continue
                frame,offset=expression[1:];ptrs={trace.scalar(v)for v in mem.get((frame,offset,64),[])or[]};counts={trace.scalar(v)for v in mem.get((frame,offset+8,64),[])or[]}
                if len(ptrs)==len(counts)==1 and None not in ptrs|counts:
                    address=next(iter(ptrs));count=next(iter(counts))
                    if address in remaining:format_uses[address].append(dict(owner=owner,call=pc,callee=target,count=count,argument_register=arg))
    def code_field(oa,ca):
        op,cp=original.pointer(oa),candidate.pointer(ca);row=by_start.get(op['target']);matched=[]if row is None else[m for m in row['normalized_matches']if m['start']==cp['target']]
        out=dict(offset=None,original=op,candidate=cp,normalized_body_correspondence=bool(matched),candidate_labels=[m['symbol']for m in matched],candidate_symbols=[r['name']for r in function_symbols.get(cp['target'],[])])
        if row and row['bytes']==56 and not matched:
            ob=original.read(op['target'],56);cb=candidate.read(cp['target'],56);pattern=[(0,0x18),(16,0x7b),(24,0x18),(40,0x7b),(48,0x95)]
            if all(ob[n]==cb[n]==opcode for n,opcode in pattern):
                norm=lambda b:b[:4]+bytes(4)+b[8:12]+bytes(4)+b[16:28]+bytes(4)+b[32:36]+bytes(4)+b[40:]
                if norm(ob)==norm(cb):
                    ids=[]
                    for b in(ob,cb):
                        hi=struct.unpack_from('<I',b,4)[0]|struct.unpack_from('<I',b,12)[0]<<32;lo=struct.unpack_from('<I',b,28)[0]|struct.unpack_from('<I',b,36)[0]<<32;ids.append(f'{hi:016x}{lo:016x}')
                    out['constant_only_128bit_return_difference']=dict(original_u128=ids[0],candidate_u128=ids[1],other_instruction_bytes_equal=True)
        return out
    def table(oa,ca,size,derived_from=None):
        code_offsets=[0,24]if size==32 else[0,24,32,40]if size==48 else[0,24,32,48,56,64,72,80]
        fields=[]
        for k in code_offsets:
            f=code_field(oa+k,ca+k);f['offset']=k;fields.append(f)
        r=dict(original=oa,candidate=ca,candidate_symbols=symbols.get(ca,[]),compared_footprint_bytes=size,original_allocation_extent_proved=False,
            size_alignment_equal=original.read(oa+8,16)==candidate.read(ca+8,16),original_size_alignment=list(struct.unpack('<QQ',original.read(oa+8,16))),candidate_size_alignment=list(struct.unpack('<QQ',candidate.read(ca+8,16))),code_pointer_fields=fields,
            raw_bytes_equal=original.read(oa,size)==candidate.read(ca,size),derived_from=derived_from)
        if size==88:
            op,cp=original.pointer(oa+40),candidate.pointer(ca+40);r['nested_supertrait_table']=dict(offset=40,original=op,candidate=cp,candidate_symbols=symbols.get(cp['target'],[]),role='Display-supertrait vtable inferred from Error: Debug+Display and observed layout')
        return r
    rows=[];nested=[]
    for address in sorted(remaining):
        pair=pairs[address];ca=int(pair['candidate'],16);ss=symbols.get(ca,[]);sizes={s['bytes']for s in ss};assert len(sizes)==1,(hex(address),ss)
        size=next(iter(sizes));record=dict(original=address,candidate=ca,candidate_symbols=ss,candidate_symbol_extent_proved=True,candidate_bytes=size,original_allocation_extent_proved=False,reference_uses=pair['uses'])
        first=original.pointer(address);align=original.word(address+16)if size>=24 else 0;payload=original.word(address+8)if size>=24 else 0
        if size in(32,48,88)and first['relocation_type']==8 and first['target']in by_start and align in(1,2,4,8,16)and payload<100000:
            record['classification']='single_method_trait_vtable' if size==32 else 'Write_vtable' if size==48 else 'dyn_Error_vtable'
            if size == 32 and any('core..any..Any' in r['name'] for r in function_symbols.get(candidate.pointer(ca+24)['target'],[])):
                record['classification'] = 'Any_vtable'
                record['candidate_method_symbols'] = [r['name'] for r in function_symbols.get(candidate.pointer(ca+24)['target'],[])]
                record['candidate_payload_role'] = 'core::panic::PanicInfo::internal_constructor::NoPayload, inferred from selected core source and panic_fmt consumer'
            record['type_status']='consumer_and_trait_layout_inference';record['fields']=table(address,ca,size)
            if size==88:
                field=record['fields']['nested_supertrait_table'];no,nc=field['original']['target'],field['candidate']['target'];assert {s['bytes']for s in symbols[nc]}=={32};nested.append(table(no,nc,32,dict(parent_original=address,parent_candidate=ca,offset=40)))
        elif size==24:
            ptr=original.pointer(address);cp=candidate.pointer(ca);n,kind=original.word(address+8),original.word(address+16);cn,ck=candidate.word(ca+8),candidate.word(ca+16)
            record.update(classification='io_SimpleMessage_compatible',type_status='static_message_role_and_layout_inference',original_fields=dict(pointer=ptr,message=original.string(ptr['target'],n),error_kind_discriminant=kind),candidate_fields=dict(pointer=cp,message=candidate.string(cp['target'],cn),error_kind_discriminant=ck));record['bounded_fields_equal_after_relocation']=n==cn and kind==ck and original.read(ptr['target'],n)==candidate.read(cp['target'],cn)
        else:
            assert size%16==0
            fields=[]
            for k in range(size//16):
                op,cp=original.pointer(address+16*k),candidate.pointer(ca+16*k);on,cn=original.word(address+16*k+8),candidate.word(ca+16*k+8)
                assert on <= 32031 and cn <= 32031
                empty = on == cn == 0 and op['relocation_type'] is None and cp['relocation_type'] is None and op['target'] == cp['target'] == 1
                assert empty or op['relocation_type'] == cp['relocation_type'] == 8, (hex(address), k, op, cp, on, cn)
                os,cs=original.string(op['target'],on),candidate.string(cp['target'],cn);fields.append(dict(index=k,original_pointer=op,candidate_pointer=cp,original_string=os,candidate_string=cs,equal=on==cn and os['sha256']==cs['sha256']))
            uses=format_uses.get(address,[]);record.update(classification='string_slice_table',type_status='typed_format_pieces_transport'if uses else'layout_only_role_unproved',typed_call_evidence=uses,elements=fields,bounded_fields_equal_after_relocation=all(f['equal']for f in fields))
            if uses:assert all(u['count']*16==size for u in uses)
        rows.append(record)
    error_tables={r['original']for r in rows if r['classification']=='dyn_Error_vtable'};assert len(error_tables)==4
    assert len(constructors)==6 and all(not r['unknown']and set(r['vtable_values'])<=error_tables for r in constructors)
    counts=collections.Counter(r['classification']for r in rows);typeids=[f for r in rows if'fields'in r for f in r['fields']['code_pointer_fields']if'constant_only_128bit_return_difference'in f]
    inputs=[original.path,candidate.path,previous_path,frontier_path,inventory_path,helper_path,trace_path,Path(__file__),ROOT/'work/fees-compat/toolchains/v1.44/rust/lib/rustlib/src/rust/library/core/src/error.rs',ROOT/'work/fees-compat/toolchains/v1.44/rust/lib/rustlib/src/rust/library/core/src/panic/panic_info.rs',ROOT/'work/fees-compat/toolchains/v1.44/rust/lib/rustlib/src/rust/library/std/src/io/error.rs']
    summary=dict(new_reference_pairs=len(rows),candidate_symbol_extents_verified=len(rows),candidate_extent_histogram=dict(collections.Counter(r['candidate_bytes']for r in rows)),classifications=dict(counts),new_typed_format_arrays=len(format_uses),derived_supertrait_vtables=len(nested),constant_only_128bit_return_differences=len(typeids), error_type_id_differences=sum(r['classification']=='dyn_Error_vtable' for r in rows),original_allocation_extents_proved=0)
    report=dict(scope=__doc__,input_sha256={str(p.relative_to(ROOT)):sha(p)for p in inputs},summary=summary,objects=rows,derived_supertrait_tables=nested,error_constructor_pool=dict(callee=0x1a9db0,static_calls=constructors,vtable_values=sorted(error_tables),no_known_address_taking=not any(r['target']==0x1a9db0 for r in analyzer.inventory['pointer_relocations']),qualification='Pool is complete for the six known direct constructor calls, not a proof of all heap origins or per-callsite targets.'),limitations=['Original ranges use candidate symbol sizes as comparison footprints, not as proof of original allocation boundaries.','Single-method trait roles require individual consumer evidence; a 32-byte vtable shape alone does not establish Debug, Display or Any, and normalized target labels do not authenticate original type identity.','Function-pointer correspondence is local normalized body evidence, not transitive code/data equality.'])
    args.output.write_text(json.dumps(report,indent=2)+'\n');args.summary.write_text(json.dumps(dict(input_sha256=report['input_sha256'],summary=summary,limitations=report['limitations']),indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
