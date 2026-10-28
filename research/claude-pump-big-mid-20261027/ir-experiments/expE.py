import sys, re
sys.path.insert(0, sys.argv[1]); import irtool
s = open('inc0.ll').read()
E65 = '%"_ZN4core3ptr52drop_in_place$LT$solana_instruction..Instruction$GT$17h4e293d3fd367c515E.exit65"'
EOK = '%"_ZN4core3ptr52drop_in_place$LT$solana_instruction..Instruction$GT$17h4e293d3fd367c515E.exit"'
def run(name, t):
    open(name + '.ll', 'w').write(t)
    irtool.llc(name + '.ll', name + '.o')
    sec, code = irtool.obj_function(name + '.o', 'incentives7execute')
    r = irtool.compare(code, 0x746a8, name)
    irtool.dis(name + '.o', sec, name + '.dis')
    return r
def rep(t, a, b):
    assert t.count(a) == 1, a[:100]
    return t.replace(a, b)
t = s
t = rep(t, '  br i1 %5, label %bb26, label %bb20\n', '  br i1 %5, label %bb26, label %userr\nuserr:\n  %xa3p = extractvalue { i64, ptr } %3, 1\n  br label %bb21\n')
t = rep(t, '  %_85.0 = extractvalue { i64, ptr } %7, 0\n', '  %_85.0 = extractvalue { i64, ptr } %7, 0\n  %xa7p = extractvalue { i64, ptr } %7, 1\n')
t = rep(t, '  %_117.0 = extractvalue { i64, ptr } %67, 0\n', '  %_117.0 = extractvalue { i64, ptr } %67, 0\n  %xa67p = extractvalue { i64, ptr } %67, 1\n')
# redirect bb22 and exit65 to bb21
i = t.index('bb22:                                             ; preds = %start')
j = t.index('  br label %bb20\n', i)
t = t[:j] + '  br label %bb21\n' + t[j + len('  br label %bb20\n'):]
i = t.index(E65[1:] + ':')
j = t.index('  br label %bb20\n', i)
t = t[:j] + '  br label %bb21\n' + t[j + len('  br label %bb20\n'):]
# rewrite bb21 phis, delete bb20
t = rep(t, '  %_0.sroa.5.0 = phi ptr [ %_0.sroa.5.1, %bb20 ], [ undef, ' + EOK + ' ]\n',
        '  %_0.sroa.5.0 = phi ptr [ %xa7p, %bb22 ], [ %xa3p, %userr ], [ %xa67p, ' + E65 + ' ], [ undef, ' + EOK + ' ]\n')
t = rep(t, '  %_0.sroa.0.0 = phi i64 [ %_0.sroa.0.1, %bb20 ], [ 2, ' + EOK + ' ]\n',
        '  %_0.sroa.0.0 = phi i64 [ %_85.0, %bb22 ], [ %4, %userr ], [ %_117.0, ' + E65 + ' ], [ 2, ' + EOK + ' ]\n')
i = t.index('bb20:                                             ; preds = %bb23')
j = t.index('  br label %bb21\n}\n', i)
t = t[:i] + t[j + len('  br label %bb21\n'):]
run('expE', t)
# E2: phi order swapped (tag first)
a = t.index('  %_0.sroa.5.0 = phi'); b = t.index('\n', a) + 1; c = t.index('\n', b) + 1
t2 = t[:a] + t[b:c] + t[a:b] + t[c:]
run('expE2', t2)
