import importlib.util, sys
sys.path.insert(0, '/Users/shawwalters/Documents/Codex/2026-10-24/claude-mayhem-work/pm-o84/tools')
from exps2 import vs_late
OVF = "  br i1 %_50.1.i, label %bb10, label %bb30.i\n"
LOW = "  br i1 %_60.not.i, label %bb10, label %bb38.i\n"
HIGH = "  br i1 %_69.1.i, label %bb10, label %bb3.i\n"
CMP = "  br i1 %or.cond.i, label %bb10, label %bb9\n"
VT = "  br i1 %.not.i, label %bb10, label %bb21.i, !prof !62\n"
def unl(b, line):
    assert b.count(line) == 1, line
    return b.replace(line, line.rstrip('\n') + ', !prof !62\n')
def k1(b): return unl(b, OVF)
def k2(b): return unl(unl(unl(unl(b, OVF), LOW), HIGH), CMP)
def k3(b): return b.replace(VT, VT.replace(', !prof !62', ''))
def k4(b): return unl(vs_late(b), OVF)
EXPS = [('k1-ovf-unlikely', k1), ('k2-all-unlikely', k2), ('k3-vt-plain', k3), ('k4-vslate-ovf-unlikely', k4)]
