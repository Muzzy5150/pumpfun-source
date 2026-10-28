from pathlib import Path
import json,struct,sys
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'));from pump_compare_function_bytes import sections,body
b=(R/'evidence/original/pump/deployed.so').read_bytes();secs=sections(b);j=json.loads((R/'work/parallel-main-integration/build-round25-final/normalized-inventory.json').read_text());windows=j['windows'];by={x['start']:x for x in windows};task=json.loads((R/'research/main-pump-parallel-checkpoint-20261027/REMAINING-WORK.json').read_text());mine=[x for x in task['tasks']if x['owner']=='build_identity'];targets={int(x['original_start'],16) for x in mine};refs={t:[]for t in targets}
for w in windows:
 for c in w.get('original_operands',[]):
  if c['kind']=='direct-call' and c['target'] in targets:
   names=[z['symbol']for z in w['normalized_matches']];refs[c['target']].append({'caller':hex(w['start']),'offset':hex(c['offset']),'matched_symbols':names})
def literal(v):
 for name,s in secs.items():
  if name in ['.rodata','.data.rel.ro'] and s['addr']<=v<s['addr']+s['size']:
   at=s['offset']+v-s['addr'];x=b[at:at+110];x=x.split(bytes([0]))[0];return x.decode('ascii',errors='replace')
rows=[]
for t in mine:
 st=int(t['original_start'],16);w=by[st];strings=[]
 for q in w.get('original_operands',[]):
  if q['kind']=='elf-pointer':
   s=literal(q['value'])
   if s and len(s)>3 and sum(c.isprintable() for c in s)>0.9*len(s):strings.append(s)
 rows.append({**t,'callers':refs[st],'strings':list(dict.fromkeys(strings))})
(R/'work/parallel-main-create-validation-next/queue-triage.json').write_text(json.dumps(rows,indent=2)+'\n')
for x in rows:
 names=[n for c in x['callers']for n in c['matched_symbols'] if '__global' in n]
 if names or x['strings']: print(x['original_start'],x['bytes'],'callers',[(c['caller'],c['offset'])for c in x['callers']], 'entry',names,'strings',x['strings'][:3])
