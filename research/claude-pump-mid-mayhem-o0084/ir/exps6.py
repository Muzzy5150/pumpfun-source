import sys
sys.path.insert(0, '/Users/shawwalters/Documents/Codex/2026-10-24/claude-mayhem-work/pm-o84/tools')
from exps3 import unl, OVF, LOW, HIGH, CMP
EXPS = [('p1-high-only', lambda b: unl(b, HIGH)), ('p2-ovf-only', lambda b: unl(b, OVF))]
