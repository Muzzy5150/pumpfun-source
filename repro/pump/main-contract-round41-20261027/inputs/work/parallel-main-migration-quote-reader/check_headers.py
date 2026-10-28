"""Signed migration probes with preexisting quote-account header boundaries."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import pump_migrate_v2_probe as p
parser=argparse.ArgumentParser();parser.add_argument('--candidate',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
specs=[]
for stable,quote22 in [(False,False),(True,False),(True,True)]:
    quote=p.Pubkey.from_bytes(bytes([217])*32) if stable else p.WSOL
    token=p.T22 if quote22 else p.TOKEN
    authority=p.pda([b'pool-authority',bytes(p.MINT)],p.P)
    def case(length,amount,state=1):
        data=bytearray(max(165,length));data[:32]=bytes(quote);data[32:64]=bytes(authority);data[64:72]=amount.to_bytes(8,'little');data[108]=state
        if not stable:data[109:113]=(1).to_bytes(4,'little');data[113:121]=(2039280).to_bytes(8,'little')
        return {'boost':True,'stable':stable,'quote22':quote22,'mutations':{'pool_authority_quote_account':{'owner':str(token),'lamports':10000000,'patches':[(0,data.hex())],'length':length}}}
    for length in [0,63,64,71,72,108,164,165,166]:
        for amount in [0,1]:specs.append((f'header/{stable}/{quote22}/{length}/{amount}',case(length,amount)))
    for state in [0,2,3,255]:specs.append((f'state/{stable}/{quote22}/{state}',case(165,1,state)))
rows=[]
for name,case in specs:
    original=p.run(case);candidate=p.run(case,args.candidate)
    for value in [original,candidate]:value['events']=[line for line in value['logs']if line.startswith('Program data:')]
    fields=['error','before','after','events','inner','return']
    rows.append({'name':name,'case':case,'mismatched_fields':[key for key in fields if original[key]!=candidate[key]],'original':original,'candidate':candidate})
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
report={'scope':__doc__+' These are full signed instruction paths; invalid headers may fail an earlier ATA validation before either amount reader.','case_count':len(rows),'candidate_sha256':sha(args.candidate),'original_sha256':sha(ROOT/'evidence/original/pump/deployed.so'),'fixture_sha256':sha(Path(__file__)),'base_fixture_sha256':sha(ROOT/'scripts/pump_migrate_v2_probe.py'),'cases':rows,'mismatches':[i for i,row in enumerate(rows)if row['mismatched_fields']]}
args.output.write_bytes(gzip.compress(json.dumps(report,separators=(',',':')).encode(),mtime=0));print(len(rows),[(row['name'],row['original']['error'],row['candidate']['error'],row['mismatched_fields'])for row in rows if row['mismatched_fields']])
if report['mismatches']:raise SystemExit(1)
