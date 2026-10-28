#!/usr/bin/env python3
"""Bind all 144 indirect sites to operand evidence and scoped target results."""
from pathlib import Path
import argparse, collections, hashlib, json, struct

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    source=ROOT/'evidence/original/pump/deployed.so';raw=source.read_bytes()
    local_path=HERE/'LOCAL-PROVENANCE.json';local=json.loads(local_path.read_text())
    boundary_path=ROOT/'work/parallel-main-window-boundary-audit/AUDIT.json';boundary=json.loads(boundary_path.read_text())
    inventory_path=ROOT/'work/parallel-main-integration/build-round24-final/normalized-inventory.json';inventory=json.loads(inventory_path.read_text())
    frontier_path=ROOT/'work/parallel-main-data-frontier/round24-frontier.json';frontier=json.loads(frontier_path.read_text())
    assert all(x['original_sha256']==sha(source) for x in [local,inventory,frontier])
    assert boundary['inputs']['evidence/original/pump/deployed.so']==sha(source)
    by_owner={w['start']:w for w in inventory['windows']};rows=[]
    for r in local['sites']:
        pc=r['site'];reg=r['immediate'];before=[]
        for at in range(max(r['owner'],pc-96),pc,8):
            op,regs,off,imm=struct.unpack_from('<BBhi',raw,at)
            before.append(dict(site=at,raw=raw[at:at+8].hex(),opcode=op,dst=regs&15,src=regs>>4,offset=off,immediate=imm))
        last=[i for i in before if i['opcode']==0x79 and i['dst']==reg and i['offset']==0]
        drop_chain=[]
        if last:
            pointer=last[-1];prior=[i for i in before if i['site']<pointer['site']and i['opcode']==0x79 and i['dst']==pointer['src']and i['offset']==7]
            if prior:drop_chain=[prior[-1],pointer]
        family='tagged_io_error_custom_drop'if drop_chain else'formatting_trait_dispatch'
        labels=[x['symbol']for x in by_owner[r['owner']]['normalized_matches']]
        if not drop_chain:assert labels and all('fmt' in label for label in labels),(hex(pc),labels)
        contexts=[x for x in local['direct_call_contexts']if x['indirect_callsite']==pc]
        rows.append(dict(site=pc,owner=r['owner'],target_register=reg,family=family,
            original_operand_evidence=drop_chain if drop_chain else before[-6:],
            local_register_provenance=r['provenance'],
            local_analysis_status='input_dependent_symbolic'if r['expressions']is not None else'analysis_widened_unknown',
            original_name_is_known=False,candidate_body_labels=labels,
            static_direct_caller_contexts=contexts,
            target_status='fixed_in_listed_direct_call_contexts_only'if contexts else'unresolved_dynamic_or_analysis_widened',
            unrestricted_target_set_proved=False))
    assert {r['site']for r in rows}=={r['site']for r in boundary['indirect_calls']}
    # Independently check the fixed-table constant at each one-hop caller.
    contexts=local['direct_call_contexts'];assert len(contexts)==60
    known_callers=[c for c in boundary['calls']if c['target']==0x1adfb0]
    assert len(known_callers)==30 and {c['site']for c in known_callers}=={c['direct_callsite']for c in contexts}
    for c in known_callers:
        pc=c['site'];op,regs=raw[pc-16:pc-14]
        val=struct.unpack_from('<I',raw,pc-12)[0]|struct.unpack_from('<I',raw,pc-4)[0]<<32
        assert op==0x18 and regs==3 and val==0x1bd8a0,(pc,op,regs,val)
    pointer=next(x for x in boundary['pointer_relocations']if x['site']==0x1bd8b8)
    assert pointer['target']==0xa880
    assert {c['indirect_callsite']for c in contexts}=={0x1ae098,0x1ae230}
    assert all(c['targets']==[0xa880]and c['exhaustive_for_this_callsite']for c in contexts)
    pointer_taken=[x for x in boundary['pointer_relocations']if x['target']==0x1adfb0]
    mapping=next(x for x in frontier['unambiguous_data_prefixes']if x['original']=='0x1bd8a0')
    sources=[source,local_path,boundary_path,inventory_path,frontier_path,HERE/'trace.py',Path(__file__),
        ROOT/'work/fees-compat/toolchains/v1.44/rust/lib/rustlib/src/rust/library/std/src/io/error/repr_bitpacked.rs',
        ROOT/'work/fees-compat/toolchains/v1.44/rust/lib/rustlib/src/rust/library/std/src/io/error.rs']
    report=dict(scope=__doc__,input_sha256={str(p.relative_to(ROOT)):sha(p)for p in sources},
        counts=dict(sites=len(rows),families=dict(collections.Counter(r['family']for r in rows)),locally_constant_sites=local['counts']['all_paths_constant'],
                    sites_with_fixed_direct_contexts=2,direct_context_edges=60,unrestricted_target_sets_unproved=144,
                    local_analysis_status=dict(collections.Counter(r['local_analysis_status']for r in rows))),
        fixed_context_proof=dict(caller_function=0xc680,callee_function=0x1adfb0,known_direct_calls=30,indirect_sites=[0x1ae098,0x1ae230],
            vtable_argument=0x1bd8a0,method_offset=24,relocated_method_slot=0x1bd8b8,target=0xa880,
            raw_table_prefix=raw[0x1bd8a0:0x1bd8c0].hex(),
            all_known_direct_call_arguments_checked_against_original_bytes=True,
            callee_function_pointer_references=pointer_taken,
            existing_data_frontier_mapping=dict(original=mapping['original'],candidate=mapping['candidate'],uses=len(mapping['uses']),candidate_sha256=frontier['candidate_sha256']),
            limitation='This resolves both indirect sites when reached from those30 static call instructions. It is not proof that no computed/indirect call can enter the callee with another vtable.'),
        method_limits=['The register analysis retains both sides of every conditional, widens unsupported arithmetic and merges to unknown, and invalidates caller-clobbered registers and all modeled stack slots after calls.',
                       'Input-dependent and heap-loaded vtables are not treated as constant. No candidate label or prefix match is used to prove an original target.',
                       'CALL_REG target register is the immediate field for the original SBFv0 encoding. Targets are reported as original linked text addresses before VM base relocation.',
                       'Candidate symbols label normalized body counterparts only; they are not authenticated original names.'],sites=rows)
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['counts'],indent=2))

if __name__=='__main__':main()
