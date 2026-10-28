from pathlib import Path
import shutil,hashlib,json
P=Path(__file__).parent;root=P.parents[1];base=root/'work/parallel-main-integration/round17-source/programs/pump';dst=P/'source02';assert not dst.exists();shutil.copytree(base,dst)
a=base/'src/trade_v3.rs';before=root/'work/parallel-main-v3-validity/byte-source/src/trade_v3.rs';assert a.read_bytes()==before.read_bytes()
s=(P/'source/src/trade_v3.rs').read_text();start=s.index('pub fn net_quote(');end=s.index('// Token-2022',start);part=s[start:end];part=part.replace('protocol_fee=fee(quote,pb)?;','protocol_fee=crate::legacy_sell::fee_cpi::fee(quote,pb)?;').replace('creator_fee=fee(quote,creator_bps)?;','creator_fee=crate::legacy_sell::fee_cpi::fee(quote,creator_bps)?;');s=s[:start]+part+s[end:];(dst/'src/trade_v3.rs').write_text(s)
sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest();(P/'STAGING02.json').write_text(json.dumps({'base':str(base),'source':str(dst),'changes':['src/trade_v3.rs'],'trade_v3_sha256':sha(dst/'src/trade_v3.rs'),'unchanged_shared_fee_sha256':sha(dst/'src/fee_cpi.rs'),'reason':'Use frozen Round17 existing public shared fee API for two real net-budget calls; no context-owned source edits.'},indent=2)+'\n')
