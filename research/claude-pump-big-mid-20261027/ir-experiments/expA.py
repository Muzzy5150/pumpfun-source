import sys, re
sys.path.insert(0, sys.argv[1]); import irtool
s = open('inc0.ll').read()
E65 = '%"_ZN4core3ptr52drop_in_place$LT$solana_instruction..Instruction$GT$17h4e293d3fd367c515E.exit65"'
def variant(name, edits):
    t = s
    for a, b in edits:
        assert t.count(a) == 1, a
        t = t.replace(a, b)
    open(name + '.ll', 'w').write(t)
    irtool.llc(name + '.ll', name + '.o')
    sec, code = irtool.obj_function(name + '.o', 'incentives7execute')
    irtool.compare(code, 0x746a8, name)
    irtool.dis(name + '.o', sec, name + '.dis')
# A: scalar phi for the payload instead of the aggregate phi
variant('expA', [
  ('  %4 = extractvalue { i64, ptr } %3, 0\n', '  %4 = extractvalue { i64, ptr } %3, 0\n  %xa3p = extractvalue { i64, ptr } %3, 1\n'),
  ('  %_85.0 = extractvalue { i64, ptr } %7, 0\n', '  %_85.0 = extractvalue { i64, ptr } %7, 0\n  %xa7p = extractvalue { i64, ptr } %7, 1\n'),
  ('  %_117.0 = extractvalue { i64, ptr } %67, 0\n', '  %_117.0 = extractvalue { i64, ptr } %67, 0\n  %xa67p = extractvalue { i64, ptr } %67, 1\n'),
  ('  %.pn = phi { i64, ptr } [ %7, %bb22 ], [ %67, ' + E65 + ' ], [ %3, %bb23 ]\n', ''),
  ('  %_0.sroa.5.1 = extractvalue { i64, ptr } %.pn, 1\n', '  %_0.sroa.5.1 = phi ptr [ %xa7p, %bb22 ], [ %xa67p, ' + E65 + ' ], [ %xa3p, %bb23 ]\n'),
])
