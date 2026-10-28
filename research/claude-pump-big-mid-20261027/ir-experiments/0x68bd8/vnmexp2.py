import sys, re, itertools
sys.path.insert(0, sys.argv[1]); import irtool
s = open('vnm0.ll').read()
def run(name, t, quiet=False):
    open(name + '.ll', 'w').write(t)
    irtool.llc(name + '.ll', name + '.o')
    sec, code = irtool.obj_function(name + '.o', 'validate_new_mint')
    r = irtool.compare(code, 0x68bd8, name)
    irtool.dis(name + '.o', sec, name + '.dis')
    return r
def rep(t, a, b):
    assert t.count(a) == 1, a[:100]
    return t.replace(a, b)
W = {'u': '!999990', 'l': '!999991'}   # u: first target unlikely; l: first target likely
meta = '\n!999990 = !{!"branch_weights", i32 1, i32 2000}\n!999991 = !{!"branch_weights", i32 2000, i32 1}\n'
brs = {
 'c1': '  br i1 %1, label %bb1, label %bb6\n',
 'c2': '  br i1 %3, label %bb7, label %bb12\n',
 'c3': '  br i1 %19, label %bb13, label %bb18\n',
 'empty': '  br i1 %36, label %bb33, label %bb6.i.i\n',
 'found': '  br i1 %38, label %bb20, label %bb10.i.i\n',
 'gt': '  br i1 %_57, label %bb27, label %bb33\n',
}
def variant(name, spec):
    t = s
    for k, w in spec.items():
        t = rep(t, brs[k], brs[k][:-1] + ', !prof ' + W[w] + '\n')
    return run(name, t + meta)
variant('w_errs_unlikely', {'c1': 'u', 'c2': 'u', 'c3': 'u'})
variant('w_errs_unlikely_gt', {'c1': 'u', 'c2': 'u', 'c3': 'u', 'gt': 'u'})
variant('w_all', {'c1': 'u', 'c2': 'u', 'c3': 'u', 'gt': 'u', 'found': 'u'})
variant('w_all_empty', {'c1': 'u', 'c2': 'u', 'c3': 'u', 'gt': 'u', 'found': 'u', 'empty': 'u'})
