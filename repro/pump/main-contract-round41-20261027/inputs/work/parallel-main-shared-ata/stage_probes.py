from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base={}
for family in ['buy','sell']:
 p=R/f'scripts/pump_{family}_v2_differential.py';s=p.read_text();base[str(p.relative_to(R))]=sha(p)
 old="f.Pubkey.default() if spec.get('system_owner') else ac.owner"
 assert s.count(old)==1;s=s.replace(old,"f.Pubkey.from_string(spec['owner']) if 'owner' in spec else f.Pubkey.default() if spec.get('system_owner') else ac.owner")
 (W/f'{family}_fixture.py').write_text(s)
(W/'FIXTURE-DERIVATION.json').write_text(json.dumps({'purpose':'Admit explicitly supplied Account.owner mutations only; transaction construction/signature verification and captured dependencies unchanged.','original_sha256':base,'derived_sha256':{p.name:sha(p)for p in W.glob('*_fixture.py')}},indent=2)+'\n')
