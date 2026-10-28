import re
def ren(b, names):
    for n in names:
        b = re.sub(r'%' + n + r'\b', '%x' + n, b)
    return b
OLD_BB6 = """  %16 = getelementptr inbounds nuw i8, ptr %_249, i64 80
  %_24 = load i64, ptr %16, align 8, !noundef !2
  %17 = zext i64 %_24 to i128
"""
OLD_BB21 = """bb21.i:                                           ; preds = %bb6
  %18 = mul nuw nsw i128 %17, 1000000000000000
  %_40.i = udiv i128 %18, %15
  %_13.i = zext i16 %1 to i128
  %19 = tail call { i128, i1 } @llvm.umul.with.overflow.i128(i128 %0, i128 %_13.i)
"""
def vs_late(b):
    assert b.count(OLD_BB6) == 1 and b.count(OLD_BB21) == 1
    b = b.replace(OLD_BB6, '')
    new = """bb21.i:                                           ; preds = %bb6
  %_13.i = zext i16 %1 to i128
  %19 = tail call { i128, i1 } @llvm.umul.with.overflow.i128(i128 %0, i128 %_13.i)
  %16 = getelementptr inbounds nuw i8, ptr %_249, i64 80
  %_24 = load i64, ptr %16, align 8, !noundef !2
  %17 = zext i64 %_24 to i128
  %18 = mul nuw nsw i128 %17, 1000000000000000
  %_40.i = udiv i128 %18, %15
"""
    b = b.replace(OLD_BB21, new)
    return ren(b, ['16', '17', '18', '19'])
def vs_late_keep_order(b):
    assert b.count(OLD_BB6) == 1 and b.count(OLD_BB21) == 1
    b = b.replace(OLD_BB6, '')
    new = """bb21.i:                                           ; preds = %bb6
  %16 = getelementptr inbounds nuw i8, ptr %_249, i64 80
  %_24 = load i64, ptr %16, align 8, !noundef !2
  %17 = zext i64 %_24 to i128
  %18 = mul nuw nsw i128 %17, 1000000000000000
  %_40.i = udiv i128 %18, %15
  %_13.i = zext i16 %1 to i128
  %19 = tail call { i128, i1 } @llvm.umul.with.overflow.i128(i128 %0, i128 %_13.i)
"""
    b = b.replace(OLD_BB21, new)
    return ren(b, ['16', '17', '18', '19'])
EXPS = [('j0-ident', lambda b: b + ' '), ('j1-vs-late-umul-first', vs_late), ('j2-vs-late', vs_late_keep_order)]
