"""Reach the creator executable gate using already-loaded SPL program accounts."""
from pathlib import Path
import hashlib,importlib.util,inspect
P=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('collection_precedence',P/'probe-precedence.py');base=importlib.util.module_from_spec(s);s.loader.exec_module(base)
text=inspect.getsource(base.fixture.run)
old="creator=P if c.get('executable') else U.pubkey()"
new="creator=TOKEN if c.get('actual_executable')=='token' else TOKEN22 if c.get('actual_executable')=='token22' else (P if c.get('executable') else U.pubkey())"
assert text.count(old)==1;text=text.replace(old,new);ns=dict(base.fixture.__dict__);exec(compile(text,str(Path(__file__)), 'exec'),ns);execute=ns['run']
def run(c,binary=None):
 ns['IX']=next(x for x in base.fixture.J['instructions']if x['name']==('collect_creator_fee'if c['version']=='legacy'else'collect_creator_fee_v2'))
 return execute(c,binary)
def cases():
 for version in ['legacy','v2']:
  for which in ['token','token22']:
   for amount in [0,1]:
    yield {'name':f'{version}-actual-{which}-amount{amount}','version':version,'native':890880+amount,'actual_executable':which}
 for amount in [0,1]:
  yield {'name':f'v2-tokenquote-actual-token22-invalid-source-amount{amount}','version':'v2','quote':str(base.fixture.QUOTE),'tokens':amount,'actual_executable':'token22','source_missing':True}
base.run=run;base.cases=cases
if __name__=='__main__':base.main()
