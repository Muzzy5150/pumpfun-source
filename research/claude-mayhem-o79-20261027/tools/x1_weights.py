# branch-weight subsets on the g1d price-check region
import itertools, re
BR = {
 'eqov':  ('  br i1 %_318.1, label %bb6, label %bb90', 'E'),   # error first
 'eqfit': ('  br i1 %or.cond, label %bb5, label %bb6', 'O'),   # ok first
 'vq':    ('  br i1 %.not71, label %bb8, label %bb82', 'O'),
 'vt0':   ('  br i1 %_5.i, label %bb12, label %bb2.i', 'E'),
 'csub':  ('  br i1 %_38.not.i, label %bb12, label %bb23.i', 'E'),
 'cadd':  ('  br i1 %_47.1.i, label %bb12, label %bb32.i', 'E'),
 'cmp':   ('  br i1 %or.cond.i, label %bb12, label %bb11', 'E'),
}
def mk(keys):
    def f(body):
        for k in keys:
            line, kind = BR[k]
            assert body.count(line + '\n') == 1, k
            body = body.replace(line + '\n', line + (', !prof !62' if kind == 'E' else ', !prof !99001') + '\n')
        return body
    return f
names = list(BR)
EXPS = []
for r in range(0, len(names) + 1):
    for combo in itertools.combinations(names, r):
        EXPS.append(('w-' + ('+'.join(combo) or 'none'), mk(combo)))
