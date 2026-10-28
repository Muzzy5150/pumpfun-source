"""Compare retained main-Pump invocation logs; source filenames remain visible."""
from pathlib import Path
from collections import Counter,defaultdict
import argparse,difflib,gzip,hashlib,json,re
from paired_receipt_reader import records
PUMP='6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P'
coord=re.compile(r'(programs/pump/[^ :\s]+):\d+(?::\d+)?')
path_coordinate=re.compile(r'programs/pump/[^ :\s]+:<source>')
compute=re.compile(r'^Program \S+ consumed \d+ of \d+ compute units$')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def norm(lines):return[coord.sub(r'\1:<source>',x)for x in lines if not compute.fullmatch(x)]

def scope(lines):
 # Compare every outermost Pump invocation, including Pump reached through a captured CPI harness.
 # Nested self-CPI stays inside its enclosing Pump trace; unrelated harness logs are excluded.
 stack=[];parts=[];active=None;active_depth=None
 for line in lines:
  invoke=re.fullmatch(r'Program (\S+) invoke \[(\d+)\]',line)
  finish=re.fullmatch(r'Program (\S+) (?:success|failed:.*)',line)
  if invoke:
   pid,depth=invoke.group(1),int(invoke.group(2));assert depth==len(stack)+1,(line,stack)
   stack.append(pid)
   if pid==PUMP and active is None:active=[];active_depth=len(stack)
  if active is not None:active.append(line)
  if finish:
   pid=finish.group(1);assert stack and stack[-1]==pid,(line,stack)
   if active is not None and len(stack)==active_depth:
    assert pid==PUMP;parts.append(active);active=None;active_depth=None
   stack.pop()
 assert active is None and not stack,(active,stack)
 if not parts:return None
 return [line for part in parts for line in part]

def classify(l,r):
 changes=[]
 for tag,a,b,c,d in difflib.SequenceMatcher(None,l,r,autojunk=False).get_opcodes():
  if tag!='equal':changes.append({'operation':tag,'original_index':a,'candidate_index':c,'original':l[a:b],'candidate':r[c:d]})
 left=[x for c in changes for x in c['original']];right=[x for c in changes for x in c['candidate']]
 if Counter(l)==Counter(r):kind='ordinary_message_order'
 elif [path_coordinate.sub('<source-file>',x)for x in l]==[path_coordinate.sub('<source-file>',x)for x in r]:kind='source_file_path_only'
 elif not right and len(left)==1:
  line=left[0]
  if line=='Program log: No cashback to claim':kind='missing_cashback_zero_notice'
  elif line.startswith('Program log: No changes in accumulator for user='):kind='missing_volume_no_change_notice'
  elif line.startswith('Program log: Nothing to sweep for fee bucket '):kind='missing_fee_bucket_zero_notice'
  elif line.startswith('Program log: Insufficient fees for distribution. Minimum vault balance needed: '):kind='missing_distribution_minimum_notice'
  elif line=='Program log: Creator quote token account is frozen; fees left in the vaults':kind='missing_creator_quote_frozen_notice'
  elif line=='Program log: Creator is not a system-owned wallet; fees left in the vaults':kind='missing_creator_non_system_notice'
  elif line=='Program log: No canonical pump pool for this mint; curve only':kind='missing_canonical_pool_notice'
  else:kind='other_missing_log'
 elif any(x.startswith('Program data:')for x in left+right):kind='event_payload_difference'
 else:kind='other_log_difference'
 return kind,changes

def audit_inputs(inputs, output, mismatches):
    """Read actual retained pairs; preserve all non-coordinate message content."""
    hashes = {str(path): sha(path) for path, _ in inputs}
    counts, families = Counter(), Counter()
    by_suite, examples = defaultdict(Counter), defaultdict(list)
    with gzip.open(mismatches, 'wt', encoding='utf-8') as stream:
        for path, expected in inputs:
            total = 0
            for ordinal, where, row in records(path):
                total += 1
                counts['paired_cases'] += 1
                left, right = row['original'], row['candidate']
                assert isinstance(left.get('logs'), list) and isinstance(right.get('logs'), list), where
                assert all(isinstance(line, str) for line in left['logs'] + right['logs']), where
                raw_left, raw_right = norm(left['logs']), norm(right['logs'])
                main_left, main_right = scope(raw_left), scope(raw_right)
                if not raw_left and not raw_right:
                    counts['no_raw_logs'] += 1
                    continue
                counts['raw_log_bearing_pairs'] += 1
                if main_left is None and main_right is None:
                    counts['neither_invokes_main'] += 1
                    continue
                counts['main_invocation_pairs'] += 1
                if main_left == main_right:
                    counts['equal_main_sequences'] += 1
                    continue
                counts['mismatched_main_sequences'] += 1
                if main_left is None or main_right is None:
                    kind, changes = 'main_invocation_disagreement', []
                else:
                    kind, changes = classify(main_left, main_right)
                families[kind] += 1
                by_suite[where.split('/')[0]][kind] += 1
                if kind != 'source_file_path_only':
                    counts['non_filename_mismatches'] += 1
                item = {'file': str(path), 'row': where, 'ordinal': ordinal,
                        'family': kind, 'changes': changes,
                        'original_logs': main_left, 'candidate_logs': main_right}
                stream.write(json.dumps(item, separators=(',', ':')) + '\n')
                if len(examples[kind]) < 3:
                    examples[kind].append(item)
            assert total == expected, (str(path), total, expected)
    assert all(sha(Path(path)) == digest for path, digest in hashes.items())
    report = {
        'status': 'passed' if counts['non_filename_mismatches'] == 0 else 'mismatches',
        'scope': 'Ordered outermost main-Pump invocation logs, including all nested CPI, event and return logs. No VM replay.',
        'normalization': ['Exclude compute-unit consumption lines.',
                          'Normalize source line and column numbers only; preserve filenames.'],
        'acceptance': 'Zero non-filename mismatches. Source-filename mismatches remain counted and reported as unresolved provenance.',
        'counts': dict(counts), 'families': dict(families),
        'families_by_suite': {name: dict(value) for name, value in by_suite.items()},
        'examples': dict(examples), 'source_sha256': hashes,
        'mismatches_sha256': sha(mismatches),
        'implementation_sha256': {Path(__file__).name: sha(Path(__file__)),
                                  'paired_receipt_reader.py': sha(Path(__file__).with_name('paired_receipt_reader.py'))},
    }
    output.write_text(json.dumps(report, indent=2) + '\n')
    return report

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--full', type=Path, required=True)
    parser.add_argument('--additional', type=Path, required=True)
    parser.add_argument('--expected-full', type=int, required=True)
    parser.add_argument('--expected-additional', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mismatches', type=Path, required=True)
    parser.add_argument('--allow-business-differences', action='store_true',
                        help='Analysis mode only; still report every difference.')
    args = parser.parse_args()
    report = audit_inputs([(args.full, args.expected_full),
                           (args.additional, args.expected_additional)],
                          args.output, args.mismatches)
    print(json.dumps({'status': report['status'], 'counts': report['counts'],
                      'families': report['families']}))
    return int(report['status'] != 'passed' and not args.allow_business_differences)

if __name__ == '__main__':
    raise SystemExit(main())
