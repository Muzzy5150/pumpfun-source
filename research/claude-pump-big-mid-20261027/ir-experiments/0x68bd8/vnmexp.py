import sys, re
sys.path.insert(0, sys.argv[1]); import irtool
s = open('vnm0.ll').read()
def run(name, t):
    open(name + '.ll', 'w').write(t)
    irtool.llc(name + '.ll', name + '.o')
    sec, code = irtool.obj_function(name + '.o', 'validate_new_mint')
    irtool.compare(code, 0x68bd8, name)
    irtool.dis(name + '.o', sec, name + '.dis')
def rep(t, a, b):
    assert t.count(a) == 1, a[:100]
    return t.replace(a, b)
br = '  br i1 %_57, label %bb27, label %bb33\n'
# A: unlikely error
t = rep(s, br, '  br i1 %_57, label %bb27, label %bb33, !prof !999999\n')
t = t + '\n!999999 = !{!"branch_weights", i32 1, i32 2000}\n'
run('vnmA', t)
# A2: likely error (reverse)
t = rep(s, br, '  br i1 %_57, label %bb27, label %bb33, !prof !999999\n') + '\n!999999 = !{!"branch_weights", i32 2000, i32 1}\n'
run('vnmA2', t)
# B: inverted condition
t = rep(s, '  %_57 = icmp ugt i64 %_8.i, 255\n' + br, '  %_57 = icmp ult i64 %_8.i, 256\n  br i1 %_57, label %bb33, label %bb27\n')
run('vnmB', t)
