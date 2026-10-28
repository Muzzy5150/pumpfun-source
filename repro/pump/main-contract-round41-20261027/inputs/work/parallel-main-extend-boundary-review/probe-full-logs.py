"""The unchanged 308 extension inputs, with plain log and diagnostic comparison."""
from pathlib import Path
import importlib.util
P=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('extend_log_overlay',P/'probe-logs.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
m.cases=m.f.cases
m.__doc__=__doc__
if __name__=='__main__':m.main()
