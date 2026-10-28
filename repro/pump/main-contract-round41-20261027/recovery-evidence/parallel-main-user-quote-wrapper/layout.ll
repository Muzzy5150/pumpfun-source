; ModuleID = 'payment_layout.384f4a48df03c27c-cgu.0'
source_filename = "payment_layout.384f4a48df03c27c-cgu.0"
target datalayout = "e-m:e-p:64:64-i64:64-n32:64-S128"
target triple = "sbf"

@_ZN14payment_layout7OFFSETS17h1e63fb389949cd44E = hidden constant <{ ptr, ptr, ptr, ptr, ptr, ptr, ptr, ptr, ptr, ptr }> <{ ptr @_ZN14payment_layout8v2_curve17hfb1edebc716eefebE, ptr @_ZN14payment_layout9v2_system17hce7f8d9485cb40c8E, ptr @_ZN14payment_layout7v2_user17hd73eaa766e4fa0efE, ptr @_ZN14payment_layout8v3_curve17h97431658a8c14d60E, ptr @_ZN14payment_layout9v3_system17hd5a8b75a7a36e76eE, ptr @_ZN14payment_layout7v3_user17hd482039403b7c84bE, ptr @_ZN14payment_layout15v2_quote_source17h600ae80ddcacafa6E, ptr @_ZN14payment_layout20v2_quote_destination17h5ccc76ddb9079d6bE, ptr @_ZN14payment_layout15v3_quote_source17hb6fafcd692aca951E, ptr @_ZN14payment_layout20v3_quote_destination17hb4d33458e781b3a2E }>, align 8
@_ZN14payment_layout6GETTER17h6e8e3ea3ab9c4c0bE = hidden constant <{ ptr }> <{ ptr @_ZN14payment_layout10curve_info17hae7d97324f67db16E }>, align 8
@llvm.compiler.used = appending global [2 x ptr] [ptr @_ZN14payment_layout6GETTER17h6e8e3ea3ab9c4c0bE, ptr @_ZN14payment_layout7OFFSETS17h1e63fb389949cd44E], section "llvm.metadata"

; payment_layout::v2_curve
; Function Attrs: mustprogress nofree norecurse nosync nounwind willreturn memory(none)
define internal noundef i64 @_ZN14payment_layout8v2_curve17hfb1edebc716eefebE() unnamed_addr #0 {
start:
  ret i64 320
}

; payment_layout::v2_system
; Function Attrs: mustprogress nofree norecurse nosync nounwind willreturn memory(none)
define internal noundef i64 @_ZN14payment_layout9v2_system17hce7f8d9485cb40c8E() unnamed_addr #0 {
start:
  ret i64 416
}

; payment_layout::v2_user
; Function Attrs: mustprogress nofree norecurse nosync nounwind willreturn memory(none)
define internal noundef i64 @_ZN14payment_layout7v2_user17hd73eaa766e4fa0efE() unnamed_addr #0 {
start:
  ret i64 344
}

; payment_layout::v3_curve
; Function Attrs: mustprogress nofree norecurse nosync nounwind willreturn memory(none)
define internal noundef i64 @_ZN14payment_layout8v3_curve17h97431658a8c14d60E() unnamed_addr #0 {
start:
  ret i64 40
}

; payment_layout::v3_system
; Function Attrs: mustprogress nofree norecurse nosync nounwind willreturn memory(none)
define internal noundef i64 @_ZN14payment_layout9v3_system17hd5a8b75a7a36e76eE() unnamed_addr #0 {
start:
  ret i64 112
}

; payment_layout::v3_user
; Function Attrs: mustprogress nofree norecurse nosync nounwind willreturn memory(none)
define internal noundef i64 @_ZN14payment_layout7v3_user17hd482039403b7c84bE() unnamed_addr #0 {
start:
  ret i64 64
}

; payment_layout::curve_info
; Function Attrs: mustprogress nofree norecurse nosync nounwind willreturn memory(argmem: read)
define internal noundef nonnull align 8 dereferenceable(48) ptr @_ZN14payment_layout10curve_info17hae7d97324f67db16E(ptr noalias nocapture noundef readonly align 8 dereferenceable(168) %x) unnamed_addr #1 {
start:
  %_0 = load ptr, ptr %x, align 8, !nonnull !2, !align !3, !noundef !2
  ret ptr %_0
}

; payment_layout::v2_quote_source
; Function Attrs: mustprogress nofree norecurse nosync nounwind willreturn memory(none)
define internal noundef i64 @_ZN14payment_layout15v2_quote_source17h600ae80ddcacafa6E() unnamed_addr #0 {
start:
  ret i64 360
}

; payment_layout::v2_quote_destination
; Function Attrs: mustprogress nofree norecurse nosync nounwind willreturn memory(none)
define internal noundef i64 @_ZN14payment_layout20v2_quote_destination17h5ccc76ddb9079d6bE() unnamed_addr #0 {
start:
  ret i64 336
}

; payment_layout::v3_quote_source
; Function Attrs: mustprogress nofree norecurse nosync nounwind willreturn memory(none)
define internal noundef i64 @_ZN14payment_layout15v3_quote_source17hb6fafcd692aca951E() unnamed_addr #0 {
start:
  ret i64 80
}

; payment_layout::v3_quote_destination
; Function Attrs: mustprogress nofree norecurse nosync nounwind willreturn memory(none)
define internal noundef i64 @_ZN14payment_layout20v3_quote_destination17hb4d33458e781b3a2E() unnamed_addr #0 {
start:
  ret i64 56
}

attributes #0 = { mustprogress nofree norecurse nosync nounwind willreturn memory(none) "target-cpu"="generic" "target-features"="+store-imm,+jmp-ext" }
attributes #1 = { mustprogress nofree norecurse nosync nounwind willreturn memory(argmem: read) "target-cpu"="generic" "target-features"="+store-imm,+jmp-ext" }

!llvm.module.flags = !{!0}
!llvm.ident = !{!1}

!0 = !{i32 8, !"PIC Level", i32 2}
!1 = !{!"rustc version 1.79.0-dev"}
!2 = !{}
!3 = !{i64 8}
