"""Classify the candidate-to-candidate text/data delta without changing either ELF."""
from pathlib import Path
import bisect
import collections
import gzip
import hashlib
import json
import re
import struct
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'work/parallel-main-verified-linker-validation/layout_tools'))
import correspond as C
import mapfile
from translation import Elf


def main():
    before_path = ROOT / 'work/parallel-main-integration/build-round29/unstripped.so'
    after_path = HERE / 'relink-ordered01/unstripped.so'
    before, after = C.Image(before_path), C.Image(after_path)
    old, new = Elf(before_path), Elf(after_path)
    maps = [ROOT / 'work/parallel-main-integration/build-round29/link/link.map',
            HERE / 'relink-ordered01/link.map']
    owners = []
    for path in maps:
        owners.append({r['address']: re.sub(r'^pump_recovered\.[^.]+\.rcgu\.o$', 'pump_recovered.<allocator-shim>.rcgu.o', re.sub(r'\.[0-9a-f]+-cgu', '.<hash>-cgu', re.sub(r'[0-9a-f]{16}', '<hash>', mapfile.owner_pattern(r))))
                       for r in mapfile.parse(path) if r['out'] == '.text'})
    canonical = lambda n: re.sub(r'17h[0-9a-f]{16}E', '17h<hash>E', n)
    groups = []
    for image, owner in zip([before, after], owners):
        out = collections.defaultdict(list)
        for address, body in image.funcs.items():
            key = body['key'], tuple(sorted(canonical(n) for n in body['names'])), owner[address]
            out[key].append(address)
        groups.append(out)
    assert groups[0].keys() == groups[1].keys(), 'logical function groups differ'
    mapping = {}
    ambiguous = []
    for key, left in groups[0].items():
        right = groups[1][key]
        assert len(left) == len(right)
        if len(left) > 1:
            ambiguous.append({'old': left, 'new': right, 'names': key[1]})
        mapping.update(zip(sorted(left), sorted(right)))
    starts = before.order

    def translated(address):
        index = bisect.bisect_right(starts, address) - 1
        start = starts[index]
        assert start <= address < start + before.funcs[start]['bytes']
        return mapping[start] + address - start

    counters = collections.Counter()
    alternate_calls = []
    for start, target in mapping.items():
        a, b = before.funcs[start], after.funcs[target]
        assert a['norm'] == b['norm']
        i = 0
        while i < a['bytes']:
            x, y = a['raw'][i:i+8], b['raw'][i:i+8]
            op, regs, offset, immediate = struct.unpack('<BBhi', x)
            if op == 0x18:
                av = struct.unpack_from('<I', a['raw'], i+4)[0] | struct.unpack_from('<I', a['raw'], i+12)[0] << 32
                bv = struct.unpack_from('<I', b['raw'], i+4)[0] | struct.unpack_from('<I', b['raw'], i+12)[0] << 32
                is_text = before.text['addr'] <= av < before.text['addr'] + before.text['size']
                assert bv == (translated(av) if is_text else av), (hex(start+i), 'lddw')
                assert x[:4] == y[:4] and a['raw'][i+8:i+12] == b['raw'][i+8:i+12]
                counters['translated_text_addresses' if is_text else 'unchanged_nontext_lddw'] += 1
                i += 16
                continue
            if op == 0x85 and regs >> 4 == 1 and immediate != -1:
                callee = start + i + 8 + immediate * 8
                want = (translated(callee) - (target+i+8)) // 8
                assert y[:4] == x[:4]
                actual = target + i + 8 + struct.unpack_from('<i', y, 4)[0] * 8
                if struct.unpack_from('<i', y, 4)[0] != want:
                    assert callee in before.funcs and actual in after.funcs
                    assert before.funcs[callee]['key'] == after.funcs[actual]['key'], (hex(start+i), 'call target body differs')
                    alternate_calls.append({'old_caller':start,'new_caller':target,'offset':i,'old_target':callee,'new_target':actual,'old_names':before.funcs[callee]['names'],'new_names':after.funcs[actual]['names']})
                    counters['normalized_equivalent_alternate_callee_calls'] += 1
                else:
                    counters['translated_direct_calls'] += 1
            else:
                assert x == y, (hex(start+i), 'nonrelocation instruction')
            i += 8
    rel = lambda b: collections.Counter(struct.unpack_from('<QQ', b, i) for i in range(0,len(b),16))
    tr = lambda x: translated(x) if before.text['addr'] <= x < before.text['addr']+before.text['size'] else x
    expect = collections.Counter({(tr(offset),info):count for (offset,info),count in rel(old.data('.rel.dyn')).items()})
    relocation_bijection_equal = expect == rel(new.data('.rel.dyn'))
    def relocation_roles(image, owners_, data):
        starts_ = image.order
        out = collections.Counter()
        for (offset,info),count in rel(data).items():
            if image.text['addr'] <= offset < image.text['addr']+image.text['size']:
                st = starts_[bisect.bisect_right(starts_,offset)-1]
                f = image.funcs[st]
                role = (f['key'],tuple(sorted(canonical(n)for n in f['names'])),owners_[st],offset-st,info)
            else:
                role = (offset,info)
            out[role] += count
        return out
    assert relocation_roles(before,owners[0],old.data('.rel.dyn')) == relocation_roles(after,owners[1],new.data('.rel.dyn'))
    delta = json.loads((HERE/'DATA-DELTA.json').read_text())
    section = new.sections['.data.rel.ro']
    allowed = set()
    for row in delta['typed_locations']['gained']:
        address = row['after']['file_pointer']['site']
        allowed.update(range(address-section['addr']+16,address-section['addr']+20))
    actual = {i for i,(x,y) in enumerate(zip(old.data('.data.rel.ro'),new.data('.data.rel.ro'))) if x!=y}
    assert actual <= allowed and len(actual) == 17
    result = {'scope': __doc__, 'before_sha256': hashlib.sha256(old.b).hexdigest(),
              'after_sha256': hashlib.sha256(new.b).hexdigest(),
              'normalized_function_groups_equal': True, 'function_count': len(mapping),
              'ambiguity_groups': ambiguous, 'moved_functions': sum(a!=b for a,b in mapping.items()),
              'text_delta_is_permutation_and_translated_or_equivalent_callee_operands': True,
              'alternate_normalized_equivalent_calls':alternate_calls,
              'relocations_are_exact_translated_multiset_under_one_assignment': relocation_bijection_equal,
              'relocations_equal_by_logical_function_group_and_local_offset':True,
              'changed_data_bytes_are_only_the_17_restored_line_fields': True,
              'instruction_counts': dict(counters),
              'limits': ['Logical grouping uses equal normalized bodies, canonical symbol names and archive/member identity with compiler hashes removed. Calls to alternate equal-body instances are recorded separately; this is bounded code classification, not an exact graph-identity proof.',
                         'This does not establish original whole-ELF identity or original object allocation extents.']}
    (HERE/'TEXT-AND-RELOCATION-DELTA.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
