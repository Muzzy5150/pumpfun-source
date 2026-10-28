import sys, re
sys.path.insert(0, sys.argv[1]); import irtool
def run(name, F):
    F.write(name + '.ll')
    irtool.llc(name + '.ll', name + '.o')
    sec, code = irtool.obj_function(name + '.o', 'validate_new_mint')
    return irtool.compare(code, 0x68bd8, name)
P = 'QuoteControl17validate_new_mint'
names = irtool.IRFunc('vnm0.ll', P).names()
for i, n in enumerate(names[:-1]):
    F = irtool.IRFunc('vnm0.ll', P)
    F.move('bb33', after=n)
    run(f'pos{i:02d}_after_{n[:30]}', F)
