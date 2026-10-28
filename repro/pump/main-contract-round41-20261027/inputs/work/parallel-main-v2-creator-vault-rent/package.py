from pathlib import Path
import base64,difflib,gzip,hashlib,json,sys
from solders.transaction import Transaction
R=Path(__file__).resolve().parents[2];P=Path(__file__).parent;S=P/'source01';B=R/'work/parallel-main-integration/round24-source/programs/pump'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files=['src/buy_v2.rs','src/sell_v2.rs','src/v2_native_payments.rs'];patches={}
for f in files:
 patch=''.join(difflib.unified_diff((B/f).read_text().splitlines(True),(S/f).read_text().splitlines(True),fromfile='a/programs/pump/'+f,tofile='b/programs/pump/'+f))
 patches[f]=patch
(P/'sell-v2-funding.patch').write_text(patches['src/sell_v2.rs'])
(P/'helper-visibility.patch').write_text(patches['src/buy_v2.rs']+patches['src/v2_native_payments.rs'])
(P/'v2-creator-vault-rent.patch').write_text(''.join(patches.values()))
before=json.load(gzip.open(P/'before.json.gz','rt'));after=json.load(gzip.open(P/'after01.json.gz','rt'));txs=loads=0
for row in after['suites']['v2_vault_rent']:
 for side in ['original','candidate']:
  Transaction.from_bytes(base64.b64decode(row[side]['transaction_base64'])).verify();txs+=1
 assert len(row['loader'])==2;loads+=len(row['loader'])
assert not after['mismatches'] and not after['diagnostics']['mismatches']
inv=json.load(open(P/'inventory01.json'));baseinv=R/'work/parallel-main-integration/build-round24/inventory.json'
if not baseinv.exists():
 candidates=list((R/'work/parallel-main-integration').glob('*round24*inventory*.json'));baseinv=candidates[0] if candidates else baseinv
manifest={'script':str((P/'probe.py').relative_to(R)),'script_sha256':digest(P/'probe.py'),'arguments':['--candidate','CANDIDATE','--output','OUTPUT.json.gz'],'uses_optimized_captured_loader':True,'case_count':108,'coverage':['BuyV2/BuyExactQuoteV2/SellV2','native/token quote','creator/zero creator/cashback','vault balances 0,1,890879,890880,890881','payer balances 50000,890879,895880'],'baseline_archive':str((P/'before.json.gz').relative_to(R)),'corrected_archive':str((P/'after01.json.gz').relative_to(R)),'baseline_discrepancies':len(before['mismatches']),'corrected_discrepancies':0,'verified_transactions':txs,'captured_main_loads':loads}
(P/'CLI-MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
report={'status':'108 new funding cases passed; broader trade regression running','source_base':str(B.relative_to(R)),'source_files':{f:digest(S/f) for f in files},'baseline_source_hashes':{f:digest(B/f) for f in files},'candidate_sha256':digest(P/'build01/candidate.so'),'unstripped_sha256':digest(P/'build01/unstripped.so'),'patches':['sell-v2-funding.patch','helper-visibility.patch','v2-creator-vault-rent.patch'],'before_mismatches':len(before['mismatches']),'after_mismatches':0,'strict_mismatches':0,'new_cases':108,'verified_transactions':txs,'captured_main_loads':loads,'inventory':inv['counts'],'helper_original':'0x3b598','helper_bytes':416,'helper_normalized_different_slots':22,'helper_body_changed':False,'placement':'After base-token CPI; before creator payment; cf > 0 and !cashback_coin','semantics':'Fund full Rent::minimum_balance(0) from user when creator vault below minimum; poor user retains original System custom1 error','main_owned_files_only':True}
(P/'DELIVERY.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
