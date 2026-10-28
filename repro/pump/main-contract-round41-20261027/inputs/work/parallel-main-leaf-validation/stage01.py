from pathlib import Path
import hashlib
import json
import shutil

root = Path(__file__).resolve().parents[2]
work = Path(__file__).resolve().parent
base = root / 'work/parallel-main-integration/round27-source/programs/pump'
source = work / 'source01'
assert not source.exists()
shutil.copytree(base, source)
path = source / 'src/migrate_v2.rs'
text = path.read_text()
old = 'fn quote_account_size(a:&AccountInfo)->Result<usize>{use anchor_spl::token_2022::spl_token_2022::{extension::ExtensionType,state::Account};if *a.owner!=anchor_spl::token_2022::ID{return Ok(165)}let types=quote_extensions(a)?;let mut required=ExtensionType::get_required_init_account_extensions(&types);required.push(ExtensionType::ImmutableOwner);Ok(ExtensionType::try_calculate_account_len::<Account>(&required)?)}'
new = '''fn quote_account_size(a:&AccountInfo)->Result<usize>{
 if *a.owner!=anchor_spl::token_2022::ID{return Ok(165)}
 required_quote_account_len(&a.try_borrow_data()?).ok_or_else(||ProgramError::InvalidAccountData.into())
}

pub fn required_quote_account_len(data:&[u8])->Option<usize>{
 let mut size=170usize;
 if data.len()==82{return Some(size)}
 if data.len()<167 || data[82..165].iter().any(|byte|*byte!=0) || data[165]!=1{return None}
 let mut cursor=166usize;
 let mut seen=0u32;
 while data.len()-cursor>=2 {
  let kind=u16::from_le_bytes([data[cursor],data[cursor+1]]);
  if kind==0{break}
  if data.len()-cursor<4{return None}
  let length=u16::from_le_bytes([data[cursor+2],data[cursor+3]]) as usize;
  cursor=cursor.checked_add(4)?.checked_add(length)?;
  if cursor>data.len(){return None}
  let payload=match kind {1=>8,9=>0,14=>1,26=>0,_=>continue};
  let mask=1u32<<kind;
  if seen&mask!=0{return None}
  seen|=mask;
  size=size.checked_add(4)?.checked_add(payload)?;
 }
 Some(size)
}'''
assert text.count(old) == 1
path.write_text(text.replace(old, new))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
hashes = lambda d: {str(p.relative_to(d)): sha(p) for p in sorted(d.rglob('*')) if p.is_file()}
a, b = hashes(base), hashes(source)
assert [k for k in a if a[k] != b[k]] == ['src/migrate_v2.rs']
(work / 'PLAN01.json').write_text(json.dumps({'baseline': str(base), 'source': str(source), 'baseline_files': a, 'source_files': b, 'hypothesis': 'Replace only the migration required-account-size parser with original-backed primitive-tag scanning, including PausableConfig tag26. Keep the later fee-presence parser untouched as a causal control.', 'counterexample': {'path': str(work / 'sizes-before01.json.gz'), 'sha256': sha(work / 'sizes-before01.json.gz'), 'case': 'pausable_config'}}, indent=2) + '\n')
print(sha(path))
