from pathlib import Path
import shutil, hashlib, json
r=Path.cwd();p=r/'work/parallel-main-claim-boundary-review';base=r/'work/parallel-main-integration/round33-source/programs/pump';out=p/'source01';assert not out.exists();shutil.copytree(base,out)
f=out/'src/token_incentives/claim_token_incentives.rs';s=f.read_text();old='''        &[
            ctx.accounts.event_authority.to_account_info(),
            ctx.accounts.program.to_account_info(),
        ],''';new='''        &[ctx.accounts.event_authority.to_account_info()],''';assert s.count(old)==1;s=s.replace(old,new);f.write_text(s)
h=lambda q:hashlib.sha256(q.read_bytes()).hexdigest()
(p/'STAGING01.json').write_text(json.dumps({'scope':'Single original-backed event CPI AccountInfo-count restoration; no other main source changes','baseline':str(base),'baseline_source_hashes':{str(q.relative_to(base)):h(q) for q in sorted(base.rglob('*')) if q.is_file()},'source_hashes':{str(q.relative_to(out)):h(q) for q in sorted(out.rglob('*')) if q.is_file()},'original':'0x75308/5920B','original_event_call':'0x76880, invoke_signed, r4=1','before':'2 AccountInfo entries (event_authority, program)','after':'1 AccountInfo entry (event_authority)'},indent=2)+'\n')
