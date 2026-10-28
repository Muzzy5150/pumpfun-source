import re
A = "  %18 = tail call { i128, i1 } @llvm.umul.with.overflow.i128(i128 %0, i128 %_4.i237)\n  %_42.0.i = extractvalue { i128, i1 } %18, 0\n"
def ren(b):
    return re.sub(r'%18\b', '%umul18', b)
def mv(b, after):
    b = b.replace(A, ''); a = ren(A); b = ren(b)
    assert b.count(after) == 1, after
    return b.replace(after, after + a)
def sink_umul(b): return mv(b, "bb16.i:                                           ; preds = %bb6\n")
def after_mul(b): return mv(b, "  %19 = mul nuw nsw i128 %17, 1000000000000000\n")
def after_div(b): return mv(b, "  %_44.i = udiv i128 %19, %15\n")
EXPS = [('i1-sink-umul', sink_umul), ('i2-after-mul', after_mul), ('i3-after-div', after_div)]
