"""Audit program invocation order from paired logs, including failed transactions."""
import re
PATTERN=re.compile(r'^Program (\S+) invoke \[(\d+)\]$')
def audit_invocations(report):
    bad=[];count=0
    def walk(value,path=''):
        nonlocal count
        if isinstance(value,dict):
            if isinstance(value.get('original'),dict) and isinstance(value.get('candidate'),dict):
                count+=1
                seq=lambda side:[m.groups()for line in side.get('logs',[])if(m:=PATTERN.match(line))]
                a,b=seq(value['original']),seq(value['candidate'])
                if a!=b:bad.append({'path':path,'case':value.get('case'),'original':a,'candidate':b})
            for key,item in value.items():
                if key not in ('original','candidate'):walk(item,path+'/'+key)
        elif isinstance(value,list):
            for i,item in enumerate(value):walk(item,path+'/'+str(i))
    walk(report)
    return {'paired_cases':count,'mismatches':bad}
