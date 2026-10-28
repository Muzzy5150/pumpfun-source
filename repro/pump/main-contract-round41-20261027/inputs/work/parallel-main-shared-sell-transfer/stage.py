from pathlib import Path
import json,shutil,hashlib,difflib
p=Path(__file__).parent;base=Path('work/parallel-main-integration/round20-source/programs/pump');d=p/'source';assert not d.exists();shutil.copytree(base,d)
context=Path('work/parallel-main-sell-v2-transfer-helper/source02/src');proposal=json.loads(Path('work/parallel-main-sell-v2-transfer-helper/v3-caller-proposal.json').read_text());h=lambda f:hashlib.sha256(f.read_bytes()).hexdigest();assert h(context/'v2_user_token_transfers.rs')==proposal['helper_sha256']
for name in ['sell_v2.rs','v2_user_token_transfers.rs']:shutil.copyfile(context/name,d/'src'/name)
f=d/'src/trade_v3.rs';s=f.read_text();assert s.count(proposal['old_v3_caller'])==1;f.write_text(s.replace(proposal['old_v3_caller'],proposal['new_v3_caller']))
(p/'STAGING.json').write_text(json.dumps({'base':str(base),'source':str(d),'own_change':'src/trade_v3.rs','own_source_sha256':h(f),'imported_context_files':{name:h(d/'src'/name)for name in ['sell_v2.rs','v2_user_token_transfers.rs']},'intended_original':'0x8fe18/2080B','real_callers':['SellV2 at0x1460e0','SellV3 at0x14b260'],'scope':'Only import context frozen module/SellV2caller and add genuine existing SellV3 transfer delegation. No zero-amount guard, no shared math edits, no fee-wrapper or net-budget control changes.'},indent=2)+'\n')
(p/'v3-caller.patch').write_text(''.join(difflib.unified_diff((base/'src/trade_v3.rs').read_text().splitlines(True),f.read_text().splitlines(True),fromfile='a/src/trade_v3.rs',tofile='b/src/trade_v3.rs')))
