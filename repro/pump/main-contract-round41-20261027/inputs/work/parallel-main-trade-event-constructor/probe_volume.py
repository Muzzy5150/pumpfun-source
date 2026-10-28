"""Strict existing-volume SellV3 regression; also supports input-only capture."""
from pathlib import Path
import argparse,base64,gzip,hashlib,json,runpy,sys
ROOT=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent
FROZEN=ROOT/'work/parallel-main-trade-event-witness/probe01.py'
assert hashlib.sha256(FROZEN.read_bytes()).hexdigest()==json.loads((ROOT/'work/parallel-main-trade-event-witness/MANIFEST01.json').read_text())['probe01.py']
fixture=runpy.run_path(str(FROZEN),run_name='_frozen_witness')
source=fixture['source']
needle="    tx=f.Transaction.new_signed_with_payer([*f.ixs[:-1],trade],user.pubkey(),[user],vm.latest_blockhash());assert all(tx.verify_with_results());result=vm.send_transaction(tx)"
assert source.count(needle)==1
replacement="""    tx=f.Transaction.new_signed_with_payer([*f.ixs[:-1],trade],user.pubkey(),[user],vm.latest_blockhash());assert all(tx.verify_with_results())
    before={}
    for key in set(f.msg.account_keys)|set(m.pubkey for m in metas):
        if key==program:continue
        account=vm.get_account(key)
        if account is not None:before[str(key)]={'lamports':account.lamports,'owner':str(account.owner),'data_hex':account.data.hex(),'executable':account.executable,'rent_epoch':account.rent_epoch}
    if c.get('capture_only'):return {'transaction_base64':base64.b64encode(bytes(tx)).decode(),'before':before,'volume_input':volume_input,'signature_verified':True}
    result=vm.send_transaction(tx)"""
source=source.replace(needle,replacement).replace("return {'volume_input':volume_input,","return {'before':before,'volume_input':volume_input,")
namespace=dict(fixture['h'].__dict__);exec(compile(source,str(Path(__file__)),'exec'),namespace);run=namespace['run']
def input_id(row):return hashlib.sha256((row['transaction_base64']+'\n'+json.dumps(row['before'],sort_keys=True,separators=(',',':'))).encode()).hexdigest()
def cases():
    return [{'name':name,'operation':'sell_v3','reserve_in':fixture['h'].base_in,'reserve_out':fixture['h'].base_out,'amount':500000000,'max_cost':0,'user_lamports':10**16,'volume_metrics':metrics}for name,metrics in [('zero-control',[0,0,0,0]),('nonzero-existing',[101,202,303,1699999900])]]
def main():
    p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--capture-inputs-only',action='store_true');p.add_argument('--only-new',action='store_true');a=p.parse_args()
    original=ROOT/'evidence/original/pump/deployed.so';rows=[]
    known=json.loads(gzip.decompress((ROOT/'work/parallel-main-trade-event-witness/witness01.json.gz').read_bytes()))
    for c in cases():
        if a.only_new and c['name']=='zero-control':continue
        if a.capture_inputs_only:
            o=run(original,c|{'capture_only':True})
            prior=next(x for x in known['cases']if x['case']['name']==c['name'])['original']
            assert o['transaction_base64']==prior['transaction_base64']and o['volume_input']==prior['volume_input']
            rows.append({'case':c,'original':o,'input_sha256':input_id(o)});continue
        assert a.candidate is not None
        o=run(original,c);n=run(a.candidate,c)
        assert o['signature_verified']and n['signature_verified']and o['transaction_base64']==n['transaction_base64']and o['before']==n['before']
        oe=fixture['events'](o);ne=fixture['events'](n)
        differences=[k for k in ['error','accounts','inner_instructions','event_payloads','return_data']if o[k]!=n[k]]
        assert o['error']is None and n['error']is None
        assert oe==ne and len(oe)==1
        assert [oe[0][k]for k in ['total_unclaimed_tokens','total_claimed_tokens','current_sol_volume','last_update_timestamp']]==c['volume_metrics']
        rows.append({'case':c,'original':o,'candidate':n,'different_fields':differences,'input_sha256':input_id(o),'decoded_trade_event':oe[0]})
    report={'scope':__doc__,'capture_only':a.capture_inputs_only,'case_count':len(rows),'cases':rows,'mismatches':[i for i,x in enumerate(rows)if x.get('different_fields')],'transformed_fixture_sha256':hashlib.sha256(source.encode()).hexdigest(),'frozen_witness_script_sha256':hashlib.sha256(FROZEN.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    a.output.write_bytes(gzip.compress((json.dumps(report,separators=(',',':'))+'\n').encode(),mtime=0))
    print(json.dumps({'capture_only':a.capture_inputs_only,'cases':len(rows),'mismatches':report['mismatches']}));assert not report['mismatches']
if __name__=='__main__':main()
