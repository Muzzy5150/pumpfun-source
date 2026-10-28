import sys, re
sys.path.insert(0, sys.argv[1]); import irtool
def run(name, F):
    F.write(name + '.ll')
    irtool.llc(name + '.ll', name + '.o')
    sec, code = irtool.obj_function(name + '.o', 'validate_new_mint')
    return irtool.compare(code, 0x68bd8, name)
P = 'QuoteControl17validate_new_mint'
names = irtool.IRFunc('vnm0.ll', P).names()
i20 = names.index('bb20'); i27 = names.index('bb27'); i33 = names.index('bb33')
g20 = names[i20:i27]; g27 = names[i27:i33]
# F1: eq-err group before bb26, then bb26, bb33, gt-err
F = irtool.IRFunc('vnm0.ll', P)
for g in g20: F.move(g, before='bb26')
F.move('bb33', after='bb26')
run('F1_eqerr_gt_ret_gterr', F)
