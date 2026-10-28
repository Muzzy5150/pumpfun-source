"""Four explicit WSOL curve-quote variants of the collection boundary probes."""
import importlib.util
from pathlib import Path
P=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('collection_boundary_cases',P/'probe_collection_boundary.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
names={'native-size0-amount0-delta0','native-size0-amount1-delta-1','native-size8-amount1-delta-1','native-size8-amount1-delta0'}
selected=[dict(c,name='wsol/'+c['name'],quote='So11111111111111111111111111111111111111112')for c in m.cases()if c['name']in names]
assert len(selected)==4
m.cases=lambda:iter(selected)
if __name__=='__main__':m.main()
