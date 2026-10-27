#!/usr/bin/env python3
"""IR surgery helper: apply edits to one function in a .ll, run llc, compare window."""
import re, subprocess, sys, json
sys.path.insert(0, __import__('os').path.dirname(__file__))
import cmpobj, objsec
L='/private/tmp/claude-501/-Users-shawwalters-Documents-Codex-2026-10-24-pumpfun-source/bf960843-6806-451b-a211-62c8b228d301/scratchpad/lanes/mayhem-b'
LLC='/Users/shawwalters/.cache/solana/v1.54/platform-tools/llvm/bin/llc'
def func_span(s, pat):
    m=re.search(r'\ndefine[^\n]*'+pat+r'[^\n]*\n', s); st=m.start()+1; en=s.find('\n}\n',st)+2
    return st,en
def run(ll_in, pat, edit, label, wid, secpat):
    s=open(ll_in).read()
    st,en=func_span(s,pat)
    body=s[st:en]
    nb=edit(body)
    assert nb!=body, 'edit had no effect'
    out=f'{L}/out/llc/{label}.ll'
    open(out,'w').write(s[:st]+nb+s[en:])
    r=subprocess.run([LLC,'-O3','-mtriple=sbf','-mcpu=generic','-relocation-model=pic','-function-sections','-filetype=obj',out,'-o',f'{L}/out/llc/{label}.o'],capture_output=True,text=True)
    if r.returncode: print(r.stderr[:2000]); return
    secs=objsec.sections(f'{L}/out/llc/{label}.o')
    key=[k for k in secs if secpat in k and k.startswith('.text')][0]
    open(f'{L}/out/llc/{label}.bin','wb').write(secs[key])
    cmpobj.report(f'{L}/out/llc/{label}.bin', wid)
