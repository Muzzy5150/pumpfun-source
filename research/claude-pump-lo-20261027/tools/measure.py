#!/usr/bin/env python3
"""Measure per-window normalized/raw matches with the frontier packet's own normalizer.
usage: measure.py <wt> <packet-rel> <unstripped.so> [out.json]
Compares against the packet's inventory.json.gz (baseline): gains/losses."""
import sys, json, gzip, hashlib, collections
from pathlib import Path
WT=Path(sys.argv[1]); PKT=WT/sys.argv[2]; CAND=Path(sys.argv[3]); OUTP=Path(sys.argv[4]) if len(sys.argv)>4 else None
sys.path.insert(0,str(PKT/'inputs/scripts'))
from pump_compare_function_bytes import normalize, body
from pump_quote_control_function_match import sections, candidate_functions
OBJ=str(Path.home()/'.cache/solana/v1.44/platform-tools/llvm/bin/llvm-objdump')
def read(p):
    b=p.read_bytes(); return json.loads(gzip.decompress(b) if b[:2]==b'\x1f\x8b' else b)
sha=lambda b: hashlib.sha256(b).hexdigest()
ob=(WT/'evidence/original/pump/deployed.so').read_bytes(); cb=CAND.read_bytes(); os_,cs=sections(ob),sections(cb)
base=read(PKT/'inventory.json.gz')
rawmap=collections.defaultdict(list); normmap=collections.defaultdict(list)
for a,n,name in candidate_functions(CAND,OBJ,'.'):
    raw=body(cb,cs,a,n); nm,_=normalize(raw,a,cs)
    e=dict(start=a,symbol=name); rawmap[(n,sha(raw))].append(e); normmap[(n,sha(nm))].append(e)
rows=[]; N=R=T=0
for w in base['windows']:
    a,n=w['start'],w['bytes']; raw=body(ob,os_,a,n); nm,_=normalize(raw,a,os_)
    assert sha(raw)==w['raw_sha256']
    nmatch=normmap.get((n,sha(nm)),[]); rmatch=rawmap.get((n,sha(raw)),[])
    rows.append(dict(start=a,bytes=n,normalized=bool(nmatch),raw=bool(rmatch),symbols=[x['symbol'] for x in nmatch][:3]))
    N+=bool(nmatch); R+=bool(rmatch); T+=n if nmatch else 0
bn={w['start'] for w in base['windows'] if w['normalized_matches']}; br={w['start'] for w in base['windows'] if w['raw_match']}
cn={r['start'] for r in rows if r['normalized']}; cr={r['start'] for r in rows if r['raw']}
res=dict(candidate_unstripped_sha256=sha(cb),normalized=N,raw=R,matched_text_bytes=T,unmatched=len(rows)-N,
  baseline=dict(normalized=len(bn),raw=len(br),candidate=base['candidate_sha256']),
  normalized_gains=[hex(x) for x in sorted(cn-bn)],normalized_losses=[hex(x) for x in sorted(bn-cn)],
  raw_gains=[hex(x) for x in sorted(cr-br)],raw_losses=[hex(x) for x in sorted(br-cr)])
print(json.dumps(res,indent=1))
if OUTP: OUTP.write_text(json.dumps(dict(summary=res,windows=rows),indent=1))
