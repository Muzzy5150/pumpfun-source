#!/usr/bin/env python3
"""Bounded immutable Rust-layout values from exact-body reference pairs.

Typed footprints and consumed fields are distinguished from allocation extents.
No equality is inferred from a fixed-size preview, and no executable is changed.
"""
from pathlib import Path
import argparse, collections, hashlib, importlib.util, json, struct, sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

class Image:
    def __init__(self,path):
        self.path=path;self.raw=path.read_bytes();b=self.raw;off=struct.unpack_from('<Q',b,40)[0];size,n,ni=struct.unpack_from('<HHH',b,58);hs=[struct.unpack_from('<IIQQQQIIQQ',b,off+i*size)for i in range(n)];ns=hs[ni];names=b[ns[4]:ns[4]+ns[5]];self.sections=[];self.rel={}
        for h in hs:
            name=names[h[0]:].split(b'\0',1)[0].decode();self.sections.append(dict(name=name,address=h[3],offset=h[4],size=h[5],type=h[1]))
            if h[1]==9:
                for p in range(h[4],h[4]+h[5],16):
                    a,info=struct.unpack_from('<QQ',b,p);self.rel[a]=info&0xffffffff
    def read(self,a,n):
        s=next((s for s in self.sections if s['type']!=8 and s['address']<=a and a+n<=s['address']+s['size']),None)
        if s is None:raise ValueError(('outside file-backed section',a,n))
        p=s['offset']+a-s['address'];return self.raw[p:p+n]
    def word(self,a):return int.from_bytes(self.read(a,8),'little')
    def pointer(self,a):
        raw=self.word(a)
        return dict(site=a,relocation_type=self.rel.get(a),target=raw>>32 if self.rel.get(a)==8 else raw,raw=self.read(a,8).hex())
    def string(self,a,n):
        raw=self.read(a,n)
        return dict(address=a,bytes=n,sha256=hashlib.sha256(raw).hexdigest(),utf8=raw.decode('utf-8',errors='replace'))

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--summary',type=Path);a=p.parse_args()
    frontier_path=ROOT/'work/parallel-main-entrypoint-221/frontier.json';frontier=json.loads(frontier_path.read_text())
    inv_path=ROOT/'work/parallel-main-entrypoint-221/inventory.json';inv=json.loads(inv_path.read_text());by_start={r['start']:r for r in inv['windows']}
    location_path=ROOT/'work/parallel-main-entrypoint-221/locations.json';locations=json.loads(location_path.read_text())
    original=Image(ROOT/'evidence/original/pump/deployed.so');candidate=Image(ROOT/'work/parallel-main-entrypoint-221/clean-default01/unstripped.so')
    assert sha(original.path)==frontier['original_sha256']==locations['original_sha256']==inv['original_sha256']
    assert sha(candidate.path)==frontier['candidate_sha256']==locations['candidate_sha256']==inv['candidate_sha256']
    assert sha(inv_path)==frontier['inventory_sha256']
    op,regs,off,imm=struct.unpack('<BBhi',original.read(0x1b0580,8))
    assert op==0x85 and regs==0x10 and 0x1b0588+imm*8==0x1b0588
    assert by_start[0x1b0580]['bytes']==8 and any('slice_'in m['symbol']and'index_len_fail_rt'in m['symbol']for m in by_start[0x1b0588]['normalized_matches'])
    forwarder_evidence=dict(start=0x1b0580,bytes=8,raw=original.read(0x1b0580,8).hex(),target=0x1b0588,target_candidate_body_labels=[m['symbol']for m in by_start[0x1b0588]['normalized_matches']],qualification='Original instruction forwards unchanged registers; target aliases agree on two usize arguments plus hidden caller location.')
    pairs={int(r['original'],16):r for r in frontier['unambiguous_data_prefixes']if r['original_section']=='.data.rel.ro'}
    trace_path=ROOT/'work/parallel-main-indirect-call-audit/trace.py';spec=importlib.util.spec_from_file_location('bounded_trace',trace_path);trace=importlib.util.module_from_spec(spec);spec.loader.exec_module(trace);analysis=trace.Analyzer()
    # Register roles follow pinned Rust signatures and the observed SBF call ABI.
    contracts={0x1b2288:('location',1,'panic_const track_caller'),0x1ace18:('location',5,'Result::unwrap_failed track_caller'),0x1b0580:('location',3,'forwarding call to slice index failure at0x1b0588'),0x1abb08:('location',1,'BorrowError panic track_caller'),0x1ac528:('location',3,'Option::expect_failed track_caller'),0x1ac9c8:('location',3,'panic_bounds_check track_caller'),0x1ac890:('location',2,'panic_fmt track_caller'),0x1ac500:('location',1,'Option::unwrap_failed track_caller'),0x1adfb0:('Debug_vtable',3,'DebugList/DebugSet entry value vtable'),0x1adb38:('Debug_vtable',3,'DebugTuple field value vtable'),0x1ad4e8:('Debug_vtable',5,'DebugStruct field value vtable'),0x1ae360:('Write_vtable',2,'fmt::write sink vtable')}
    evidence=collections.defaultdict(list);piece_evidence=collections.defaultdict(list)
    owners={int(u['original_function'],16)for r in pairs.values()for u in r['uses']}
    for owner in sorted(owners):
        for pc,(target,args,mem)in analysis.analyze(owner)['calls'].items():
            if target in contracts:
                kind,reg,role=contracts[target]
                for expr in args[reg-1]or[]:
                    address=trace.scalar(expr)
                    if address in pairs:evidence[kind,address].append(dict(owner=owner,call=pc,callee=target,register=reg,role=role,argument=trace.fmt(expr)))
            if target==0x1ac890:
                for expr in args[0]or[]:
                    if expr[0]!='stack':continue
                    frame,offset=expr[1:];addresses={trace.scalar(x)for x in mem.get((frame,offset,64),[])or[]};counts={trace.scalar(x)for x in mem.get((frame,offset+8,64),[])or[]}
                    if len(addresses)==len(counts)==1 and None not in addresses|counts:
                        address=next(iter(addresses));count=next(iter(counts))
                        if address in pairs and 0<count<=16:piece_evidence[address].append(dict(owner=owner,call=pc,pieces_field_offset=0,count_field_offset=8,count=count,role='fmt::Arguments pieces slice passed to panic_fmt'))
    def transport_evidence(address,uses):
        out=[]
        for use in uses:
            refs=[r for r in pairs[address]['uses']if int(r['original_function'],16)==use['owner']]
            assert refs
            for ref in refs:
                cf=int(ref['candidate_function'],16);refpc=cf+ref['offset'];raw=candidate.read(refpc,16)
                pointer=struct.unpack_from('<I',raw,4)[0]|struct.unpack_from('<I',raw,12)[0]<<32
                assert raw[0]==0x18 and pointer==int(pairs[address]['candidate'],16)
                cp=cf+use['call']-use['owner'];op,regs,off,imm=struct.unpack('<BBhi',candidate.read(cp,8))
                assert op==0x85 and regs==0x10
                target=cp+8+imm*8
                original_target=use.get('callee',0x1ac890)
                assert any(m['start']==target for m in by_start[original_target]['normalized_matches'])
                out.append(dict(original_use=use,candidate_function=cf,candidate_call=cp,candidate_callee=target,reference_pair=ref))
                break
        return out
    def function_pointer_field(oa,ca):
        op,cp=original.pointer(oa),candidate.pointer(ca);ow=by_start.get(op['target']);matches=[]if ow is None else[m for m in ow['normalized_matches']if m['start']==cp['target']]
        return dict(original=op,candidate=cp,same_null=op['target']==cp['target']==0,matching_relocation_kind=op['relocation_type']==cp['relocation_type'],target_has_exact_normalized_body_pair=bool(matches),candidate_labels=[m['symbol']for m in matches],target_transitive_identity_proved=False)
    results=[];shape_locations={int(r['original_address'],16):r for r in locations['pairs']}
    for address,row in sorted(shape_locations.items()):
        pair=pairs[address];ca=int(pair['candidate'],16);fields=[]
        for image,addr in [(original,address),(candidate,ca)]:
            ptr=image.pointer(addr);length,line,column=struct.unpack('<QII',image.read(addr+8,16));fields.append(dict(file_pointer=ptr,file=image.string(ptr['target'],length),line=line,column=column))
        left,right=fields;same=all(left[k]==right[k]for k in ['line','column'])and left['file']['sha256']==right['file']['sha256']and left['file']['bytes']==right['file']['bytes']
        uses=evidence.get(('location',address),[])
        results.append(dict(kind='Location_compatible',original=address,candidate=ca,typed_value_bytes=24,allocation_extent_proved=False,type_status='typed_call_role_supported'if uses else'shape_only_unproved',extent_evidence='64-bit Location value: str fat pointer16 +line4 +column4; only a shape hypothesis without typed call transport.'if not uses else'24-byte selected64-bit Location payload, supported by track_caller argument transport and pinned core::panic::Location fields; allocation end remains unknown.',type_evidence=transport_evidence(address,uses),original_fields=left,candidate_fields=right,bounded_fields_equal_after_relocation=same,raw_payload_equal=original.read(address,24)==candidate.read(ca,24),historical_rust_type_identity_proved=False))
    for(kind,address),uses in sorted(evidence.items()):
        if kind not in('Debug_vtable','Write_vtable'):continue
        ca=int(pairs[address]['candidate'],16);methods=1 if kind=='Debug_vtable'else 3;extent=24+methods*8
        osize,oalign=struct.unpack('<QQ',original.read(address+8,16));csize,calign=struct.unpack('<QQ',candidate.read(ca+8,16));fields=[function_pointer_field(address,ca)]+[function_pointer_field(address+24+i*8,ca+24+i*8)for i in range(methods)]
        sane=oalign in(1,2,4,8,16)and calign in(1,2,4,8,16)and all(f['same_null']or f['original']['relocation_type']==f['candidate']['relocation_type']==8 for f in fields)
        corresponding=sane and(osize,oalign)==(csize,calign)and all(f['same_null']or f['target_has_exact_normalized_body_pair']for f in fields)
        results.append(dict(kind=kind,original=address,candidate=ca,typed_value_bytes=extent,allocation_extent_proved=False,type_status='typed_call_role_supported'if sane else'layout_conflict_unproved',extent_evidence=f'Observed64-bit vtable header(drop,size,align)plus{methods} method slots from typed trait consumer and pinned trait definition; minimum typed footprint{extent}B,allocation end unknown.',type_evidence=transport_evidence(address,uses),original_size_alignment=[osize,oalign],candidate_size_alignment=[csize,calign],function_pointer_fields=fields,bounded_fields_correspond=corresponding,raw_payload_equal=original.read(address,extent)==candidate.read(ca,extent),historical_rust_type_identity_proved=False))
    for address,uses in sorted(piece_evidence.items()):
        counts={u['count']for u in uses}
        if len(counts)!=1:continue
        count=next(iter(counts));ca=int(pairs[address]['candidate'],16);fields=[]
        for i in range(count):
            oa=address+i*16;cc=ca+i*16;op,cp=original.pointer(oa),candidate.pointer(cc);on,cn=original.word(oa+8),candidate.word(cc+8)
            left,right=original.string(op['target'],on),candidate.string(cp['target'],cn)
            fields.append(dict(index=i,original_pointer=op,candidate_pointer=cp,original_string=left,candidate_string=right,equal=on==cn and left['sha256']==right['sha256']))
        results.append(dict(kind='format_pieces_slice',original=address,candidate=ca,typed_value_bytes=count*16,allocation_extent_proved=False,type_status='typed_call_role_supported',extent_evidence=f'Caller stores immutablepieces pointer plusliteralcount{count} into fmt::Arguments pieces slice; each str element16B. Read exactly{count*16}B plus each length-bounded string.',type_evidence=transport_evidence(address,uses),elements=fields,bounded_fields_equal_after_relocation=all(f['equal']for f in fields),raw_payload_equal=original.read(address,count*16)==candidate.read(ca,count*16),historical_rust_type_identity_proved=False))
    src=ROOT/'work/fees-compat/toolchains/v1.44/rust/lib/rustlib/src/rust/library/core/src'
    inputs=[original.path,candidate.path,frontier_path,location_path,inv_path,trace_path,Path(__file__),src/'panic/location.rs',src/'fmt/mod.rs',src/'panicking.rs',src/'slice/index.rs',src/'result.rs',src/'option.rs',src/'cell.rs']
    typed=[r for r in results if r['type_status']=='typed_call_role_supported'];examined={r['original']for r in results}
    summary=dict(frontier_pairs=len(frontier['unambiguous_data_prefixes']),data_rel_ro_pairs=len(pairs),records=len(results),kinds=dict(collections.Counter(r['kind']for r in results)),status=dict(collections.Counter(r['type_status']for r in results)),typed_location_field_agreement=sum(r['kind']=='Location_compatible'and r.get('bounded_fields_equal_after_relocation',False)for r in typed),typed_vtable_field_correspondence=sum(r.get('bounded_fields_correspond',False)for r in typed),typed_format_piece_field_agreement=sum(r['kind']=='format_pieces_slice'and r.get('bounded_fields_equal_after_relocation',False)for r in typed),unclassified_data_rel_ro_pairs=len(set(pairs)-examined),all_allocation_extents_unproved=True)
    report=dict(scope=__doc__,input_sha256={str(p.relative_to(ROOT)):sha(p)for p in inputs},summary=summary,contracts={hex(k):dict(kind=v[0],register=v[1],role=v[2])for k,v in contracts.items()},forwarder_evidence=forwarder_evidence,objects=results,unclassified_data_rel_ro_addresses=sorted(set(pairs)-examined),limitations=['A typed value footprint is not a symbol/allocation extent. No complete original allocation identity is claimed.','Location and trait roles use observed register transport plus ABI-equivalent normalized candidate callees and pinned Rust source; original source names/types remain inferred.','Function-pointer comparison proves local normalized body counterparts only, not transitive callee/data identity.','All reads use exact field/string lengths; the frontier64-byte previews are not used as object extents.'])
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(summary,indent=2))
    if a.summary:a.summary.write_text(json.dumps(dict(input_sha256=report['input_sha256'],summary=summary,limitations=report['limitations']),indent=2)+'\n')
if __name__=='__main__':main()
