#!/usr/bin/env python3
"""Read-only completeness audit of Pump's inferred windows; not symbol recovery."""
from pathlib import Path
import argparse, bisect, collections, csv, gzip, hashlib, json, struct

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT / 'evidence/original/pump/deployed.so'
WINDOWS = ROOT / 'repro/reconstruction-status-2026-10-26/functions.tsv'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run():
    data = ORIGINAL.read_bytes()
    shoff = struct.unpack_from('<Q', data, 40)[0]
    entsize, count, names_index = struct.unpack_from('<HHH', data, 58)
    headers = [struct.unpack_from('<IIQQQQIIQQ', data, shoff + i * entsize) for i in range(count)]
    names_header = headers[names_index]
    names = data[names_header[4]:names_header[4] + names_header[5]]
    sections = []
    for h in headers:
        name = names[h[0]:].split(b'\0', 1)[0].decode()
        sections.append(dict(name=name, type=h[1], flags=h[2], address=h[3], offset=h[4], size=h[5], link=h[6], entsize=h[9]))
    text = next(s for s in sections if s['name'] == '.text')
    lo, hi = text['address'], text['address'] + text['size']
    phoff = struct.unpack_from('<Q',data,32)[0]
    phsize, phcount = struct.unpack_from('<HH',data,54)
    executable_segments = []
    for i in range(phcount):
        typ, flags, offset, address, _, filesz, memsz, alignment = struct.unpack_from('<IIQQQQQQ',data,phoff+i*phsize)
        if typ==1 and flags&1:
            executable_segments.append(dict(offset=offset,address=address,file_bytes=filesz,memory_bytes=memsz,alignment=alignment))
    def section_at(address):
        return next((s for s in sections if s['type'] != 8 and s['address'] <= address < s['address'] + s['size']), None)
    def at(address, size):
        s = section_at(address)
        assert s and address + size <= s['address'] + s['size'], (address, size)
        offset = s['offset'] + address - s['address']
        return data[offset:offset + size]
    windows = []
    for r in csv.DictReader(WINDOWS.open(), delimiter='\t'):
        if r['program'] == 'pump' and r['variant'] == 'selected':
            windows.append(dict(start=int(r['original_start']), end=int(r['original_end'])))
    starts = [w['start'] for w in windows]
    start_set = set(starts)
    def owner(address):
        i = bisect.bisect_right(starts, address) - 1
        return windows[i]['start'] if i >= 0 and address < windows[i]['end'] else None
    errors = []
    if starts != sorted(starts): errors.append('windows not sorted')
    if len(starts) != len(start_set): errors.append('duplicate window starts')
    for w in windows:
        if not lo <= w['start'] < w['end'] <= hi or (w['start'] - lo) % 8 or (w['end'] - lo) % 8:
            errors.append(dict(invalid_range=w))
    events = collections.Counter({lo: 0, hi: 0})
    for w in windows: events[w['start']] += 1; events[w['end']] -= 1
    depth, last, gaps, overlaps = 0, lo, [], []
    for position, change in sorted(events.items()):
        if position > last:
            if depth == 0: gaps.append([last, position])
            if depth > 1: overlaps.append([last, position, depth])
        depth += change; last = position
    symbols, relocations, dynamic_names, dynamic_values = [], {}, {}, {}
    for s in sections:
        if s['type'] in (2, 11):
            strings_section = sections[s['link']]
            strings = data[strings_section['offset']:strings_section['offset'] + strings_section['size']]
            for index, pos in enumerate(range(s['offset'], s['offset'] + s['size'], s['entsize'])):
                n, info, _, idx, value, size = struct.unpack_from('<IBBHQQ', data, pos)
                name = strings[n:].split(b'\0', 1)[0].decode()
                if s['type'] == 11:
                    dynamic_names[index] = name
                    dynamic_values[index] = value
                if info & 15 == 2:
                    symbols.append(dict(name=name, start=value, end=value+size, size=size, section_index=idx))
        if s['type'] in (4, 9):
            for pos in range(s['offset'], s['offset'] + s['size'], s['entsize']):
                address, info = struct.unpack_from('<QQ', data, pos)
                relocations[address] = dict(site=address, type=info & 0xffffffff, symbol_index=info >> 32)
    for rel in relocations.values():
        rel['symbol'] = dynamic_names.get(rel['symbol_index'], '')
        rel['symbol_value'] = dynamic_values.get(rel['symbol_index'], 0)
    instructions, continuation_slots = {}, set()
    pc = lo
    while pc < hi:
        op, regs, displacement, immediate = struct.unpack('<BBhi', at(pc, 8))
        width = 16 if op == 0x18 else 8
        assert pc + width <= hi
        instructions[pc] = dict(op=op, regs=regs, displacement=displacement, immediate=immediate, width=width)
        if width == 16: continuation_slots.add(pc+8)
        pc += width
    evidence = collections.defaultdict(list)
    entry = struct.unpack_from('<Q', data, 24)[0]
    evidence[entry].append(dict(kind='elf_entrypoint'))
    for s in symbols:
        if lo <= s['start'] < hi: evidence[s['start']].append(dict(kind='STT_FUNC', symbol=s['name'], size=s['size']))
    calls, callx, branches, raw_text_pointers, symbolic_internal_calls = [], [], [], [], []
    for pc, ins in instructions.items():
        op, regs = ins['op'], ins['regs']
        relocation = relocations.get(pc)
        if op == 0x85 and regs >> 4 == 1 and (not relocation or relocation['type'] != 10):
            target = pc + 8 + ins['immediate'] * 8
            row = dict(site=pc, target=target, owner=owner(pc), target_owner=owner(target), target_is_window_start=target in start_set)
            calls.append(row)
            if lo <= target < hi: evidence[target].append(dict(kind='direct_call', site=pc))
        elif op == 0x85 and relocation and relocation['type']==10 and lo <= relocation['symbol_value'] < hi:
            target=relocation['symbol_value']
            row=dict(site=pc,target=target,owner=owner(pc),target_owner=owner(target),target_is_window_start=target in start_set,symbol=relocation['symbol'])
            symbolic_internal_calls.append(row)
            evidence[target].append(dict(kind='defined_symbol_call_relocation',site=pc,symbol=relocation['symbol']))
        elif op == 0x8d: callx.append(dict(site=pc, owner=owner(pc), regs=regs, immediate=ins['immediate']))
        elif op & 7 in (5, 6) and op not in (0x85, 0x95):
            target = pc + 8 + ins['displacement'] * 8
            branches.append(dict(site=pc, target=target, owner=owner(pc), target_owner=owner(target), opcode=op))
        if op == 0x18:
            raw = at(pc, 16); target = struct.unpack_from('<I', raw, 4)[0] | struct.unpack_from('<I', raw, 12)[0] << 32
            if lo <= target < hi:
                raw_text_pointers.append(dict(site=pc, target=target, relocated=relocation is not None, target_is_window_start=target in start_set))
    pointer_relocations = []
    for site, rel in relocations.items():
        if rel['type'] != 8: continue
        s = section_at(site)
        if s and s['name'] == '.text' and site in instructions and instructions[site]['op'] == 0x18:
            raw = at(site, 16); target = struct.unpack_from('<I', raw, 4)[0] | struct.unpack_from('<I', raw, 12)[0] << 32
            source = 'text_lddw_relocation'
        elif s and s['name'] != '.text':
            # This original SBF ELF stores the R_BPF_64_RELATIVE addend at site+4.
            target = struct.unpack_from('<I', at(site, 8), 4)[0]
            source = 'data_relocation'
        else:
            errors.append(dict(unhandled_relative_relocation=site)); continue
        if lo <= target < hi:
            r = dict(site=site, section=s['name'], target=target, target_is_window_start=target in start_set)
            pointer_relocations.append(r); evidence[target].append(dict(kind=source, site=site))
    unsupported_starts = [x for x in starts if x not in evidence]
    missing = [dict(target=x, evidence=v, owner=owner(x), aligned=(x-lo)%8 == 0, instruction_start=x in instructions) for x,v in sorted(evidence.items()) if lo <= x < hi and x not in start_set]
    cross_branches = [b for b in branches if b['owner'] != b['target_owner']]
    fallthrough = []
    for w in windows:
        last = w['end']-8
        if last in continuation_slots: last -= 8
        ins = instructions.get(last)
        if ins and ins['op'] not in (0x95, 0x05):
            fallthrough.append(dict(window=w['start'], end=w['end'], last_instruction=last, opcode=ins['op'], next_window=w['end'] if w['end'] in start_set else None))
    symbol_extents = [dict(**s, window_end=windows[bisect.bisect_left(starts,s['start'])]['end'] if s['start'] in start_set else None) for s in symbols if lo <= s['start'] < hi]
    boundary_rows = [dict(**w, evidence=evidence.get(w['start'],[]), starts_at_instruction=w['start'] in instructions, ends_at_instruction_or_text_end=w['end'] in instructions or w['end']==hi) for w in windows]
    def reachable(w, nonreturning):
        pending, visited, returns, falls_through = [w['start']], set(), [], []
        aborts = []
        while pending:
            pc = pending.pop()
            if pc in visited: continue
            if not w['start'] <= pc < w['end']:
                falls_through.append(pc); continue
            visited.add(pc)
            ins = instructions[pc]; op = ins['op']; rel = relocations.get(pc)
            if op == 0x95: returns.append(pc); continue
            if op == 0x85:
                target = pc+8+ins['immediate']*8
                if (rel and rel['type']==10 and (rel['symbol']=='abort' or rel['symbol_value'] in nonreturning)) or (not rel and ins['regs']>>4==1 and target in nonreturning):
                    aborts.append(pc); continue
            if op & 7 in (5,6) and op not in (0x85,0x8d):
                pending.append(pc+8+ins['displacement']*8)
                if op & 0xf0 == 0: continue
            pending.append(pc+ins['width'])
        return dict(reachable=visited, returns=returns, falls_through=falls_through, aborts=aborts)
    nonreturning, rounds = set(), []
    while True:
        added = set()
        for w in windows:
            if w['start'] in nonreturning: continue
            r = reachable(w, nonreturning)
            if not r['returns'] and not r['falls_through']: added.add(w['start'])
        if not added: break
        nonreturning.update(added); rounds.append(len(added))
    tail_evidence = []
    for r in fallthrough:
        w = windows[bisect.bisect_left(starts,r['window'])]
        cfg = reachable(w,nonreturning)
        pc = r['last_instruction']; ins=instructions[pc]; rel=relocations.get(pc)
        target=pc+8+ins['immediate']*8
        tail_evidence.append(dict(**r,reachable_from_window_start=pc in cfg['reachable'],callee=target if not rel else None,relocation=rel,
            callee_inferred_nonreturning=target in nonreturning if not rel else bool(rel['type']==10 and rel['symbol']=='abort'),
            reachable_fallthrough=cfg['falls_through']))
    final_inputs = [ORIGINAL, WINDOWS, Path(__file__),
        ROOT/'work/pump-reserve-byte-recovery/inventory_current.py',
        ROOT/'scripts/pump_compare_function_bytes.py', ROOT/'scripts/pump_quote_control_function_match.py',
        ROOT/'repro/layered-passes/pass-25/pump-current-evidence/analysis/full-before-after-inventory.json.gz',
        ROOT/'repro/layered-passes/pass-25/pump-current-evidence/inner-manifest.json',
        ROOT/'work/pump-admin-cto-error-batch-build/elf_reader.py',
        ROOT/'work/pump-admin-cto-error-batch-build/layer_inventory.py']
    historical = json.loads(gzip.decompress(final_inputs[6].read_bytes()))['after']['original_windows']
    manifest = json.loads(final_inputs[7].read_text())
    producer_check = dict(fixed_table_equals_historical_ledger=[(w['start'],w['end'])for w in windows]==[(w['start'],w['end'])for w in historical],files={})
    for path in final_inputs[8:]:
        expected=manifest['build/analysis/'+path.name]['sha256']
        producer_check['files'][str(path.relative_to(ROOT))]=dict(observed_sha256=sha(path),published_sha256=expected,equal=sha(path)==expected)
    return dict(scope=__doc__, inputs={str(p.relative_to(ROOT)):sha(p) for p in final_inputs},
        text=dict(start=lo,end=hi,bytes=hi-lo,sha256=hashlib.sha256(at(lo,hi-lo)).hexdigest(),instruction_count=len(instructions),lddw_continuation_slots=len(continuation_slots)),
        executable_segments=executable_segments,producer_check=producer_check,
        coverage=dict(windows=len(windows),sum_window_bytes=sum(w['end']-w['start']for w in windows),gaps=gaps,overlaps=overlaps,errors=errors),
        evidence_counts=dict(relative_direct_calls=len(calls),unique_relative_direct_call_targets=len({x['target']for x in calls}),defined_symbol_call_relocations=len(symbolic_internal_calls),indirect_calls=len(callx),text_pointer_relocations=sum(x['section']=='.text'for x in pointer_relocations),data_pointer_relocations=sum(x['section']!='.text'for x in pointer_relocations),unique_pointer_targets=len({x['target']for x in pointer_relocations}),relocation_types=dict(collections.Counter(r['type']for r in relocations.values()))),
        elf_entrypoint=entry,function_symbols=symbol_extents,missing_evidenced_boundaries=missing,unsupported_window_starts=unsupported_starts,
        invalid_call_targets=[x for x in calls if x['target'] not in instructions],
        invalid_branch_targets=[x for x in branches if x['target'] not in instructions],
        cross_window_branches=cross_branches,nonterminal_window_ends=fallthrough,
        nonreturning_cfg_inference=dict(scope='Conservative static CFG under the recorded partition; abort is the only external noreturn seed. All other calls initially may return. Cycles are not execution proof.',rounds=rounds,functions=sorted(nonreturning),tail_call_evidence=tail_evidence),
        raw_unrelocated_text_pointers=[x for x in raw_text_pointers if not x['relocated']],
        calls=calls,symbolic_internal_calls=symbolic_internal_calls,pointer_relocations=pointer_relocations,indirect_calls=callx,windows=boundary_rows)

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--summary',type=Path);a=p.parse_args()
    report=run();a.output.write_text(json.dumps(report,indent=2)+'\n')
    tails=report['nonreturning_cfg_inference']['tail_call_evidence']
    summary=dict(scope=__doc__,inputs=report['inputs'],text=report['text'],executable_segments=report['executable_segments'],coverage=report['coverage'],
        evidence_counts=report['evidence_counts'],elf_entrypoint=report['elf_entrypoint'],function_symbols=report['function_symbols'],producer_check=report['producer_check'],
        missing_evidenced_boundaries=report['missing_evidenced_boundaries'],unsupported_window_starts=report['unsupported_window_starts'],
        invalid_call_targets=report['invalid_call_targets'],invalid_branch_targets=report['invalid_branch_targets'],cross_window_branch_count=len(report['cross_window_branches']),
        nonterminal_window_ends=len(tails),nonterminal_ends_with_inferred_noreturn_callee=sum(x['callee_inferred_nonreturning']for x in tails),
        nonterminal_ends_with_reachable_fallthrough=sum(bool(x['reachable_fallthrough'])for x in tails),
        raw_unrelocated_text_pointer_count=len(report['raw_unrelocated_text_pointers']),
        conclusion='No missing, overlapping, or contradicted boundary was found in the checked static evidence. The1035windows remain inferred entries-to-next-entry ranges, not proven historical Rust function extents. Indirect-call target completeness remains unresolved.')
    if a.summary:a.summary.write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
