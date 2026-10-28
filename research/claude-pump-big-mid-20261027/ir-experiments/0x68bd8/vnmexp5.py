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
print('g20', len(g20), 'g27', len(g27))
# E1: move eq-err group after ret
F = irtool.IRFunc('vnm0.ll', P)
for g in g20: F.move(g, after=F.names()[-1])
run('E1_eqerr_after_ret', F)
# E2: move gt-err group after ret
F = irtool.IRFunc('vnm0.ll', P)
for g in g27: F.move(g, after=F.names()[-1])
run('E2_gterr_after_ret', F)
# E3: both
F = irtool.IRFunc('vnm0.ll', P)
for g in g20 + g27: F.move(g, after=F.names()[-1])
run('E3_both_after_ret', F)
# E4: ret after bb26 but gt-err before eq-err
F = irtool.IRFunc('vnm0.ll', P)
F.move('bb33', after='bb26')
for g in g27[::-1]: F.move(g, after='bb33')
run('E4_ret_gterr_eqerr', F)
