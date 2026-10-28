"""Strict post-fix scheduler guard-order regression on deduplicated typed inputs.

The inconsistent stored range is parser-admitted synthetic account state;
historical reachability through successful instructions is not established.
Run through the captured upgradeable-loader wrapper.
"""
from pathlib import Path
import argparse,base64,gzip,hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
import pump_incentives_admin_differential as fixture
from solders.transaction import VersionedTransaction
from pump_diagnostic_audit import audit

def canonical_state(row):
    result={}
    for label,account in row['before'].items():
        if account is None:continue
        address=str(account.get('address',label));a={k:account[k]for k in ['owner','lamports','executable','rent_epoch']if k in account}
        if 'data_base64'in account:a['data_hex']=base64.b64decode(account['data_base64']).hex()
        elif 'data'in account:a['data_hex']=account['data']
        if address in result:assert result[address]==a
        result[address]=a
    return result

def normalized_logs(result):
    logs=[]
    for line in result['logs']:
        if re.fullmatch(r'Program \S+ consumed \d+ of \d+ compute units',line):continue
        line=re.sub(r'(Program log: AnchorError) thrown in .*?:\d+\.',r'\1.',line)
        line=re.sub(r'^(Program log: panicked at) [^\n]*?:\d+:\d+:',r'\1 <source>:',line)
        logs.append(line)
    return logs

def compare_results(original,candidate):
    differences=[key for key in ['before','after','error','events','inner','return']if original[key]!=candidate[key]]
    if normalized_logs(original)!=normalized_logs(candidate):differences.append('logs_except_source_coordinates_and_compute_usage')
    return differences

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists()
    sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    selection=HERE/'selected-cases.json';definitions=json.loads(selection.read_text())['cases']
    inputs={str(f.resolve()):sha(f)for f in [Path(__file__),selection,Path(fixture.__file__)]}
    original_hash=sha(fixture.ORIGINAL);candidate_hash=sha(a.candidate);rows=[];signatures=0
    assert original_hash=='7a19affaa2c6187e04a5fe0ea298cee81fa5eb8c24cfcc30d85f615e89f7b02d'
    for definition in definitions:
        case=definition['case'];original,candidate=fixture.run(case),fixture.run(case,a.candidate)
        assert original['transaction_base64']==candidate['transaction_base64']
        tx_bytes=base64.b64decode(original['transaction_base64']);assert hashlib.sha256(tx_bytes).hexdigest()==definition['transaction_sha256']
        state=canonical_state(original);assert hashlib.sha256(json.dumps(state,sort_keys=True,separators=(',',':')).encode()).hexdigest()==definition['prestate_sha256']
        for side in [original,candidate]:
            tx=VersionedTransaction.from_bytes(base64.b64decode(side['transaction_base64']));assert all(tx.verify_with_results());signatures+=len(tx.signatures)
            account=side['before'][str(fixture.G)];assert account['owner']==str(fixture.PROGRAM)and account['lamports']>0
            data=bytes.fromhex(account['data']);assert len(data)==600 and data[:8]==fixture.DISC['GlobalVolumeAccumulator']
        diff=compare_results(original,candidate);rows.append({'case':case,'original':original,'candidate':candidate,'different_fields':diff})
        print(case['name'],original['error'],candidate['error'],diff,flush=True)
    assert original_hash==sha(fixture.ORIGINAL)and candidate_hash==sha(a.candidate)
    assert inputs=={str(f.resolve()):sha(f)for f in [Path(__file__),selection,Path(fixture.__file__)]}
    diagnostics=audit({'scheduler_guard_order':rows})
    report={'scope':__doc__,'case_count':len(rows),'cases':rows,'original_sha256':original_hash,'candidate_sha256':candidate_hash,'input_sha256':inputs,'verified_signatures':signatures,'mismatches':[r['case']['name']for r in rows if r['different_fields']],'diagnostics':diagnostics,'log_normalization':'Ignore only runtime compute-usage lines and natural source positions in AnchorError/panic prefixes; preserve every message, invocation, failure, data/event and return record.'}
    a.output.write_bytes(gzip.compress(json.dumps(report,separators=(',',':')).encode(),mtime=0))
    print({'cases':len(rows),'mismatches':report['mismatches'],'diagnostic_mismatches':len(diagnostics['mismatches'])},flush=True)
    assert not report['mismatches']and not diagnostics['mismatches']
if __name__=='__main__':main()
