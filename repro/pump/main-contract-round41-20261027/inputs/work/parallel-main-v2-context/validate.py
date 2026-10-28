import argparse, base64, gzip, hashlib, json, multiprocessing, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))

def initialize():
    import pump_captured_loader as loader
    loader.install()
    import buy_extended, sell_extended

def fixtures():
    import buy_extended as buy, sell_extended as sell
    return buy, sell

def cases():
    buy, sell = fixtures()
    rows = [('buy', c) for c in buy.cases()] + [('sell', c) for c in sell.cases()]
    for kind, module in [('buy_v2',buy),('buy_exact_quote_in_v2',buy),('sell_v2',sell)]:
        category = 'sell' if kind == 'sell_v2' else 'buy'
        for token_quote in [False, True]:
            for length in [49,80,81,82,83,114,115,123,124,125,132,133,140,141,149,150,157,158,165,166]:
                for amount in [0,500000000]:
                    rows.append((category, {'name':f'historical_{kind}_{token_quote}_{length}_{amount}', 'kind':kind,'token_quote':token_quote,'amount':amount,'account_mutations':{'bonding_curve':{'length':length}}}))
            for size in [200,256]:
                for amount in [0,500000000]:
                    rows.append((category, {'name':f'long_tail_{kind}_{token_quote}_{size}_{amount}', 'kind':kind,'token_quote':token_quote,'amount':amount,'account_mutations':{'bonding_curve':{'append_hex':bytes((i%251)+1 for i in range(size-166)).hex()}}}))
            for name,index in [('associated_base_bonding_curve',6),('associated_base_user',9)]:
                key=module.f.ixs[-1].accounts[index].pubkey
                owner=module.INITIAL[key].owner
                opposite=module.TOKEN if owner==module.TOKEN22 else module.TOKEN22
                for mode,mutation in [('owner',{'owner':str(opposite)}),('mint',{'bytes':[[0,module.INITIAL[key].data[0]^255]]}),('authority',{'bytes':[[32,module.INITIAL[key].data[32]^255]]})]:
                    for fault in ['none','zero','readonly','wrong_program']:
                        c={'name':f'ata_{kind}_{token_quote}_{name}_{mode}_{fault}','kind':kind,'token_quote':token_quote,'amount':1,'account_mutations':{name:mutation}}
                        if fault=='zero':c['amount']=0
                        if fault=='readonly':c['readonly']=['creator_vault']
                        if fault=='wrong_program':c['wrong_keys']=['program']
                        rows.append((category,c))
            for name in ['base_mint','quote_mint','associated_base_user','associated_base_bonding_curve']:
                if name in ['base_mint','quote_mint']:
                    owner=str(module.TOKEN if name=='base_mint' else module.TOKEN22)
                    c={'name':f'owner_{kind}_{token_quote}_{name}','kind':kind,'token_quote':token_quote,'account_mutations':{name:{'owner':owner}}}
                else:c={'name':f'noncanonical_{kind}_{token_quote}_{name}','kind':kind,'token_quote':token_quote,'wrong_keys':[name]}
                rows.append((category,c))
    return rows

def execute(item):
    category, c, candidate = item
    import pump_captured_loader as loader
    buy,sell = fixtures()
    module = buy if category=='buy' else sell
    start=len(loader.LOADS)
    o=module.run(c);n=module.run(c,Path(candidate))
    loads=loader.LOADS[start:]
    assert len(loads)==2, len(loads)
    assert o['signatures_verified'] and n['signatures_verified']
    diff=[k for k in ['error','accounts','events','inner','return_data'] if o[k]!=n[k]]
    return {'category':category,'case':c,'original':o,'candidate':n,'different_fields':diff,'loader':loads}

def main():
    p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--workers',type=int,default=4);a=p.parse_args()
    initialize();jobs=cases();rows=[]
    with multiprocessing.get_context('spawn').Pool(a.workers,initializer=initialize) as pool:
        for row in pool.imap(execute,[(k,c,str(a.candidate.resolve())) for k,c in jobs]):
            rows.append(row)
            if row['different_fields']:print(json.dumps({'case':row['case'],'different_fields':row['different_fields'],'original':row['original']['error'],'candidate':row['candidate']['error']}),flush=True)
            if len(rows)%25==0:print(f'{len(rows)}/{len(jobs)}',flush=True)
    from pump_diagnostic_audit import audit
    diagnostics=audit({'v2':rows})
    report={'case_count':len(rows),'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'fixture_sha256':{str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in [Path(__file__),Path(__file__).with_name('buy_extended.py'),Path(__file__).with_name('sell_extended.py')]},'cases':rows,'mismatches':[i for i,r in enumerate(rows) if r['different_fields']],'diagnostics':diagnostics}
    a.output.write_bytes(gzip.compress(json.dumps(report).encode()))
    print(json.dumps({'cases':len(rows),'mismatches':len(report['mismatches']),'strict_log_mismatches':len(diagnostics['mismatches']),'captured_loads':sum(len(r['loader']) for r in rows)}),flush=True)
    return bool(report['mismatches'] or diagnostics['mismatches'])

if __name__=='__main__':raise SystemExit(main())
