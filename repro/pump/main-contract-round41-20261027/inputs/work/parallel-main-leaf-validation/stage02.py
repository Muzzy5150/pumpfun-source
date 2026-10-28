from pathlib import Path
import hashlib
import json
import shutil

work = Path(__file__).resolve().parent
base = work / 'source01'
source = work / 'source02'
assert not source.exists()
shutil.copytree(base, source)
path = source / 'src/migrate_v2.rs'
text = path.read_text()
old = 'fn quote_extensions(a:&AccountInfo)->Result<Vec<anchor_spl::token_2022::spl_token_2022::extension::ExtensionType>>{use anchor_spl::token_2022::spl_token_2022::{extension::{StateWithExtensions,BaseStateWithExtensions},state::Mint};if *a.owner!=anchor_spl::token_2022::ID{return Ok(vec![])}let d=a.try_borrow_data()?;Ok(StateWithExtensions::<Mint>::unpack(&d)?.get_extension_types()?)}'
new = '''fn quote_extensions(a:&AccountInfo)->Result<Vec<u16>>{
 use anchor_spl::token_2022::spl_token_2022::{extension::{StateWithExtensions,BaseStateWithExtensions},state::Mint};
 if *a.owner!=anchor_spl::token_2022::ID{return Ok(vec![])}
 let d=a.try_borrow_data()?;
 let parsed=StateWithExtensions::<Mint>::unpack(&d)?;
 let tlv=parsed.get_tlv_data();
 let mut cursor=0usize;
 let mut types=Vec::new();
 while tlv.len()-cursor>=2 {
  let kind=u16::from_le_bytes([tlv[cursor],tlv[cursor+1]]);
  if kind==0{break}
  if tlv.len()-cursor<4{return Err(ProgramError::InvalidAccountData.into())}
  let length=u16::from_le_bytes([tlv[cursor+2],tlv[cursor+3]]) as usize;
  cursor=cursor.checked_add(4).and_then(|v|v.checked_add(length)).ok_or(ProgramError::InvalidAccountData)?;
  if cursor>tlv.len(){return Err(ProgramError::InvalidAccountData.into())}
  types.push(kind);
 }
 Ok(types)
}'''
assert text.count(old) == 1
text = text.replace(old, new)
old_type = '.contains(&anchor_spl::token_2022::spl_token_2022::extension::ExtensionType::TransferFeeConfig)'
assert text.count(old_type) == 1
path.write_text(text.replace(old_type, '.contains(&1)'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
hashes = lambda d: {str(p.relative_to(d)): sha(p) for p in sorted(d.rglob('*')) if p.is_file()}
a, b = hashes(base), hashes(source)
assert [k for k in a if a[k] != b[k]] == ['src/migrate_v2.rs']
(work / 'PLAN02.json').write_text(json.dumps({'baseline': str(base), 'source': str(source), 'baseline_files': a, 'source_files': b, 'hypothesis': 'After the size-only control passes both AMM calls, preserve primitive TLV tags for the later transfer-fee-presence query rather than failing old enum conversion on PausableConfig tag26. Base Mint unpack and TLV bounds stay unchanged.', 'counterexample': {'path': str(work / 'sizes-after01.json.gz'), 'sha256': sha(work / 'sizes-after01.json.gz'), 'case': 'pausable_config'}}, indent=2) + '\n')
print(sha(path))
