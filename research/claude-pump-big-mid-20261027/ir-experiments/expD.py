import sys, re
sys.path.insert(0, sys.argv[1]); import irtool
s = open('inc0.ll').read()
US = '@_ZN14pump_recovered16token_incentives18volume_accumulator15update_schedule17h494df6465044c441E'
E65 = '%"_ZN4core3ptr52drop_in_place$LT$solana_instruction..Instruction$GT$17h4e293d3fd367c515E.exit65"'
def run(name, t):
    open(name + '.ll', 'w').write(t)
    irtool.llc(name + '.ll', name + '.o')
    sec, code = irtool.obj_function(name + '.o', 'incentives7execute')
    irtool.compare(code, 0x746a8, name)
    irtool.dis(name + '.o', sec, name + '.dis')
def rep(t, a, b):
    assert t.count(a) == 1, a[:80]
    return t.replace(a, b)
t = s
# explicit sret call
t = rep(t, '  %mint = alloca [32 x i8], align 8\n', '  %mint = alloca [32 x i8], align 8\n  %usr = alloca [16 x i8], align 8\n')
m = re.search(r'  %3 = call \{ i64, ptr \} ' + re.escape(US) + r'\((.*)\) #30\n', t)
args = m.group(1)
t = t.replace(m.group(0), '  call void @us_sret(ptr noalias nocapture noundef nonnull sret([16 x i8]) align 8 dereferenceable(16) %usr, ' + args + ') #30\n')
t = rep(t, '  %4 = extractvalue { i64, ptr } %3, 0\n  %5 = icmp eq i64 %4, 2\n  br i1 %5, label %bb26, label %bb20\n',
        '  %4 = load i64, ptr %usr, align 8\n  %5 = icmp eq i64 %4, 2\n  br i1 %5, label %bb26, label %userr\nuserr:\n  %usp.a = getelementptr inbounds i8, ptr %usr, i64 8\n  %usp = load ptr, ptr %usp.a, align 8\n  br label %bb20\n')
t = rep(t, '  %.pn = phi { i64, ptr } [ %7, %bb22 ], [ %67, ' + E65 + ' ], [ %3, %bb23 ]\n', '')
t = rep(t, '  %_0.sroa.0.1 = phi i64 [ %_85.0, %bb22 ], [ %_117.0, ' + E65 + ' ], [ %4, %bb23 ]\n',
        '  %_0.sroa.0.1 = phi i64 [ %_85.0, %bb22 ], [ %_117.0, ' + E65 + ' ], [ %4, %userr ]\n')
t = rep(t, '  %_0.sroa.5.1 = extractvalue { i64, ptr } %.pn, 1\n', '  %_0.sroa.5.1 = phi ptr [ %xa7p, %bb22 ], [ %xa67p, ' + E65 + ' ], [ %usp, %userr ]\n')
t = rep(t, '  %_85.0 = extractvalue { i64, ptr } %7, 0\n', '  %_85.0 = extractvalue { i64, ptr } %7, 0\n  %xa7p = extractvalue { i64, ptr } %7, 1\n')
t = rep(t, '  %_117.0 = extractvalue { i64, ptr } %67, 0\n', '  %_117.0 = extractvalue { i64, ptr } %67, 0\n  %xa67p = extractvalue { i64, ptr } %67, 1\n')
t = t.replace('\ndeclare ', '\ndeclare void @us_sret(ptr, ptr, i64, i64, i64, ptr, i64, i64, i64)\ndeclare ', 1)
run('expD', t)
