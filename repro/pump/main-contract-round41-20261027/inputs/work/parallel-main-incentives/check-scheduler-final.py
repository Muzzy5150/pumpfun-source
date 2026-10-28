"""Signed offline scheduler replay including all numeric compared-value diagnostics.

Ignores only natural source coordinates in AnchorError lines. Ordinary state,
errors, events, inner instructions, return data and panic messages remain checked
by the established scheduler comparator. Complete logs are retained in each row.
"""
from pathlib import Path
import sys,json,gzip,hashlib,re,argparse

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import pump_incentive_schedule_differential as schedule
import pump_incentives_admin_differential as fixture

def diagnostics(result):
    lines=[]
    for line in result['logs']:
        if line.startswith('Program log: AnchorError'):
            lines.append(re.sub(r' thrown in .*?:\d+\.', '.',line))
        elif line.startswith(('Program log: Left:', 'Program log: Right:')):
            lines.append(line)
    return lines

def cases():
    yield from schedule.cases()
    yield {'name':'within-current-day','now':21,'old_start':20,'old_end':30,
           'old_day':10,'start':20,'end':29,'day':10,'supply':0}
    yield {'name':'range-2sec','now':10,'old_start':0,'old_end':60,
           'old_day':2,'start':20,'end':100,'day':2,'supply':0}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    candidate_sha=sha(args.candidate);rows=[]
    input_paths=[Path(x).resolve() for x in [__file__,schedule.__file__,fixture.__file__]]
    input_hashes={str(x.relative_to(ROOT)):sha(x) for x in input_paths}
    for case in cases():
        original=fixture.run(case);candidate=fixture.run(case,args.candidate)
        diff=[key for key in schedule.FIELDS if original[key]!=candidate[key]]
        if schedule.panic_messages(original)!=schedule.panic_messages(candidate):diff.append('panic_message')
        if diagnostics(original)!=diagnostics(candidate):diff.append('anchor_diagnostics')
        debug=lambda result:[line for line in result['logs'] if line.startswith('Program log: GlobalVolumeAccumulator=')]
        if debug(original)!=debug(candidate):diff.append('accumulator_debug')
        assert original['transaction_base64']==candidate['transaction_base64']
        rows.append(dict(case=case,original=original,candidate=candidate,differences=diff))
    assert candidate_sha==sha(args.candidate)
    assert input_hashes=={str(x.relative_to(ROOT)):sha(x) for x in input_paths}
    record=dict(scope=__doc__,original_sha256=sha(fixture.ORIGINAL),candidate_sha256=candidate_sha,
        inputs_sha256=input_hashes,
        case_count=len(rows),mismatches=[r['case']['name'] for r in rows if r['differences']],cases=rows)
    args.output.write_bytes(gzip.compress(json.dumps(record).encode(),mtime=0))
    print(json.dumps({'cases':len(rows),'mismatch_count':len(record['mismatches']),
        'first_mismatches':record['mismatches'][:10]}))
    assert not record['mismatches']

if __name__=='__main__':main()
