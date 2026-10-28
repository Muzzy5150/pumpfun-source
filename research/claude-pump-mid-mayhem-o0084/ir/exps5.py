import sys
sys.path.insert(0, '/Users/shawwalters/Documents/Codex/2026-10-24/claude-mayhem-work/pm-o84/tools')
from exps3 import unl, OVF, LOW, HIGH, CMP
EXPS = [('n1-ovf-high', lambda b: unl(unl(b, OVF), HIGH)), ('n2-ovf-cmp', lambda b: unl(unl(b, OVF), CMP)),
        ('n3-high-cmp', lambda b: unl(unl(b, HIGH), CMP)), ('n4-ovf-high-cmp', lambda b: unl(unl(unl(b, OVF), HIGH), CMP))]
