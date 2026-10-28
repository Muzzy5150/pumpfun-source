import sys, re
sys.path.insert(0, sys.argv[1]); import irtool
def run(name, F):
    F.write(name + '.ll')
    irtool.llc(name + '.ll', name + '.o')
    sec, code = irtool.obj_function(name + '.o', 'validate_new_mint')
    r = irtool.compare(code, 0x68bd8, name)
    irtool.dis(name + '.o', sec, name + '.dis')
    return r
P = 'QuoteControl17validate_new_mint'
F = irtool.IRFunc('vnm0.ll', P); print(F.names())
F = irtool.IRFunc('vnm0.ll', P); F.move('bb33', after='bb26'); run('o1_ret_after_gt', F)
F = irtool.IRFunc('vnm0.ll', P); F.move('bb33', before='bb26'); run('o2_ret_before_gt', F)
F = irtool.IRFunc('vnm0.ll', P)
# move err_gt group (bb27 and its to_string tails) to the very end
names = F.names(); i = names.index('bb27'); grp = names[i:names.index('bb33')]
for g in grp: F.move(g, after=F.names()[-1])
run('o3_errgt_last', F)
