import sys
sys.path.insert(0, '/Users/shawwalters/Documents/Codex/2026-10-24/claude-mayhem-work/pm-o84/tools')
from exps3 import unl, OVF, LOW, HIGH, CMP
LIKELY = '!{!"branch_weights", i32 2000, i32 1}'
def lik(b, line):
    assert b.count(line) == 1
    b = b.replace(line, line.rstrip('\n') + ', !prof !9990001\n')
    return b.replace('\n}\n', '\n}\n', 1)
def addmd(full_body):
    return full_body
EXPS = []
def m1(b): return lik(unl(b, OVF), LOW)
def m2(b): return unl(unl(unl(b, OVF), HIGH), CMP)
def m3(b): return lik(unl(unl(unl(b, OVF), HIGH), CMP), LOW)
EXPS = [('m1-low-likely', m1), ('m2-high-cmp-unlikely', m2), ('m3-low-likely-rest-unlikely', m3)]
