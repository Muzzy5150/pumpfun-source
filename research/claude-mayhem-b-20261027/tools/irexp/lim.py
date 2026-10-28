import re

def renumber(lines):
    return [re.sub(r'%(\d+)\b', lambda m: '%v' + m.group(1), l) for l in lines]

def idx(lines, pred):
    r = [k for k, l in enumerate(lines) if pred(l)]
    assert len(r) == 1, (len(r),)
    return r[0]

def branchphi(phi_of='offset', gp_sep=True):
    def fn(lines):
        lines = renumber(lines)
        i = idx(lines, lambda l: l.strip().startswith('%.v.i.i = select i1 %or.cond74.i.i, i64 520, i64 576'))
        j = idx(lines, lambda l: l.strip().startswith('%v5 = getelementptr inbounds nuw i8, ptr %accounts.i, i64 %.v.i.i'))
        k = idx(lines, lambda l: l.strip().startswith('%limit.sroa.0.0.i.i = load i64, ptr %v5'))
        assert j == i + 1 and k == i + 2
        load_tail = lines[k].split('ptr %v5', 1)[1]
        new = ['  br i1 %or.cond74.i.i, label %lim.n, label %lim.s', '', 'lim.n:']
        if phi_of == 'offset':
            new += ['  br label %lim.j', '', 'lim.s:', '  br label %lim.j', '', 'lim.j:',
                    '  %.v.i.i = phi i64 [ 176, %lim.n ], [ 232, %lim.s ]']
            if gp_sep:
                new += ['  %gp.lim = getelementptr inbounds nuw i8, ptr %accounts.i, i64 344',
                        '  %v5 = getelementptr inbounds nuw i8, ptr %gp.lim, i64 %.v.i.i']
            else:
                new += ['  %v5 = getelementptr inbounds nuw i8, ptr %accounts.i, i64 %.v.i.i']
            new += ['  %limit.sroa.0.0.i.i = load i64, ptr %v5' + load_tail]
        else:  # phi of loaded values
            new += ['  %lim.a = getelementptr inbounds nuw i8, ptr %accounts.i, i64 520',
                    '  %lim.va = load i64, ptr %lim.a' + load_tail, '  br label %lim.j', '', 'lim.s:',
                    '  %lim.b = getelementptr inbounds nuw i8, ptr %accounts.i, i64 576',
                    '  %lim.vb = load i64, ptr %lim.b' + load_tail, '  br label %lim.j', '', 'lim.j:',
                    '  %limit.sroa.0.0.i.i = phi i64 [ %lim.va, %lim.n ], [ %lim.vb, %lim.s ]']
        lines[i:k + 1] = new
        # successors of bb1.i now come from lim.j
        out = []
        for l in lines:
            if 'phi ' in l and '%bb1.i ]' in l:
                l = l.replace('%bb1.i ]', '%lim.j ]')
            out.append(l)
        return out
    return fn

EXPS = [('lim-base', lambda l: renumber(l)), ('lim-phioff-gp', branchphi('offset', True)),
        ('lim-phioff', branchphi('offset', False)), ('lim-phival', branchphi('value'))]

def selgp(form):
    def fn(lines):
        lines = renumber(lines)
        i = idx(lines, lambda l: l.strip().startswith('%.v.i.i = select i1 %or.cond74.i.i, i64 520, i64 576'))
        k = i + 2
        load_tail = lines[k].split('ptr %v5', 1)[1]
        new = ['  %.v.i.i = select i1 %or.cond74.i.i, i64 176, i64 232']
        if form == 'gp-first':
            new += ['  %gp.lim = getelementptr inbounds nuw i8, ptr %accounts.i, i64 344',
                    '  %v5 = getelementptr inbounds nuw i8, ptr %gp.lim, i64 %.v.i.i']
        else:
            new += ['  %sel.lim = getelementptr inbounds nuw i8, ptr %accounts.i, i64 %.v.i.i',
                    '  %v5 = getelementptr inbounds nuw i8, ptr %sel.lim, i64 344']
        new += ['  %limit.sroa.0.0.i.i = load i64, ptr %v5' + load_tail]
        lines[i:k + 1] = new
        return lines
    return fn

EXPS = [('sel-gpfirst', selgp('gp-first')), ('sel-selfirst', selgp('sel-first')), ('lim-phioff-gp', branchphi('offset', True))]

import itertools
TG = {
    'rem': ('%v3 = getelementptr inbounds nuw i8, ptr %ctx, i64 16', '%_57.0.i = load ptr, ptr %v3'),
    't600': ('%v6 = getelementptr inbounds nuw i8, ptr %accounts.i, i64 600', '%trader.i.i = load ptr, ptr %v6'),
    'a160': ('%v7 = getelementptr inbounds nuw i8, ptr %accounts.i, i64 160', '%trader_quote_ata.i.i = load ptr, ptr %v7'),
    'p616': ('%v8 = getelementptr inbounds nuw i8, ptr %accounts.i, i64 616', '%token_program.i.i = load ptr, ptr %v8'),
}
def perm_then(order, inner):
    def fn(lines):
        lines = inner(lines)  # renumbered already
        picked = []
        for k in order:
            for frag in TG[k]:
                i = idx(lines, lambda l, f=frag: l.strip().startswith(f))
                picked.append(lines.pop(i))
        a = idx(lines, lambda l: l.strip() == 'lim.j:')
        # insert after the limit load in lim.j
        b = idx(lines, lambda l: l.strip().startswith('%limit.sroa.0.0.i.i = load'))
        lines[b + 1:b + 1] = picked
        return lines
    return fn

EXPS = []
for p in itertools.permutations(['rem', 't600', 'a160', 'p616']):
    EXPS.append(('bp-' + '-'.join(p), perm_then(p, branchphi('offset', True))))
