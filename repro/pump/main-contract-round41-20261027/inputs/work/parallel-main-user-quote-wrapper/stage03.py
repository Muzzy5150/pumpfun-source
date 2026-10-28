from pathlib import Path
import hashlib,json,shutil
R=Path.cwd();P=R/'work/parallel-main-user-quote-wrapper';base=P/'source02';out=P/'source03';assert not out.exists();shutil.copytree(base,out)
helper=out/'src/user_quote_payments.rs';body=helper.read_text();helper.unlink()
p=out/'src/lib.rs';p.write_text(p.read_text()+'\n// Shared user-signed quote payment helpers.\npub mod user_quote_payments {\n'+''.join('    '+line if line.strip() else line for line in body.splitlines(True))+'}\n')
p=out/'src/trade_v3.rs';s=p.read_text();old='#[path="user_quote_payments.rs"]\npub mod user_quote_payments;';new='pub use crate::user_quote_payments;';assert s.count(old)==1;s=s.replace(old,new);p.write_text(s)
sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
j={'status':'bounded physical source-placement control','base':'source02','source':'source03','hypothesis':'Both original wrapper unwrap Locations encode programs/pump/src/lib.rs, so physically inline module in lib.rs without artificial lines or columns. Preserve callsite API by re-export in trade.','original_locations':[{'address':'0x1bdeb0','path':'programs/pump/src/lib.rs','line':1477,'column':42},{'address':'0x1bdec8','path':'programs/pump/src/lib.rs','line':1478,'column':40}],'native_body':'0x8df98 has no own Location/data operands','hashes':{x:sha(out/x)for x in ['src/lib.rs','src/trade_v3.rs','src/buy_v2.rs','Cargo.lock']},'removed_file':'src/user_quote_payments.rs'}
(P/'HYPOTHESIS03.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j['hashes'],indent=2))
