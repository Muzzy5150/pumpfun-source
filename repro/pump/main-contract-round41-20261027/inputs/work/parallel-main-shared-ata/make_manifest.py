from pathlib import Path
import json,sys
R=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent;sys.path.insert(0,str(R/'scripts'))
import pump_validate_all as corpus
names=['buy_v2','sell_v2','fee_sweeps','multi_hop_curve_partial']
rows=[{'name':n,'script':(p if p.startswith('repro/') else 'scripts/'+p),'count':corpus.EXPECTED_CASES[n]}for n,p in corpus.SUITES if n in names]
rows.insert(0,{'name':'ata_owner_precedence','script':str((W/'probe_owners.py').relative_to(R)),'count':92})
(W/'manifest.json').write_text(json.dumps(rows,indent=2)+'\n')
print(sum(r['count']for r in rows),[r['name']for r in rows])
