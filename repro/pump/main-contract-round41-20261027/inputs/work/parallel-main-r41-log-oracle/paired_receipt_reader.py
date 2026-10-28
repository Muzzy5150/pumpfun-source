"""Stream each paired row, one retained suite at a time."""
import gzip,json,re
delim=re.compile(r'[{}"\\]')

def records(path):
    # Decode one suite at a time, then use the exact retained-pair traversal.
    # This supports either original/candidate dictionary insertion order.
    def pairs(value,path=''):
        if isinstance(value,dict):
            if isinstance(value.get('original'),dict)and isinstance(value.get('candidate'),dict):yield path,value
            for k,v in value.items():
                if k not in ('original','candidate'):yield from pairs(v,path+'/'+k)
        elif isinstance(value,list):
            for j,v in enumerate(value):yield from pairs(v,path+'/'+str(j))
    class Reader:
        def __init__(self,f):self.f=f;self.buf='';self.pos=0
        def fill(self):
            if self.pos==len(self.buf):self.buf=self.f.read(65536);self.pos=0
            assert self.buf,'unexpected EOF'
        def get(self):self.fill();c=self.buf[self.pos];self.pos+=1;return c
        def nonspace(self):
            c=self.get()
            while c.isspace():c=self.get()
            return c
        def string(self):
            chars=['"'];escaped=False
            while True:
                c=self.get();chars.append(c)
                if escaped:escaped=False
                elif c=='\\':escaped=True
                elif c=='"':return json.loads(''.join(chars))
        def object(self):
            chunks=['{'];depth=1;string=False
            while True:
                self.fill();start=self.pos
                while True:
                    m=delim.search(self.buf,self.pos)
                    if m is None:
                        chunks.append(self.buf[start:]);self.pos=len(self.buf);break
                    at=m.start();c=m.group();self.pos=at+1
                    if c=='\\'and string:
                        if self.pos==len(self.buf):
                            chunks.append(self.buf[start:]);self.pos=len(self.buf);self.fill();start=self.pos
                        self.pos+=1;continue
                    if c=='"':string=not string
                    elif not string:
                        if c=='{':depth+=1
                        elif c=='}':
                            depth-=1
                            if depth==0:
                                chunks.append(self.buf[start:self.pos]);return json.loads(''.join(chunks))
    with gzip.open(path,'rt',encoding='utf-8')as f:
        # Find only the root-level suites property in a small metadata prefix.
        depth=0;string=False;escaped=False;token=[]
        while True:
            ch=f.read(1);assert ch,'missing top-level suites tree'
            if string:
                if escaped:escaped=False;token.append(ch)
                elif ch=='\\':escaped=True;token.append(ch)
                elif ch=='"':
                    string=False
                    if depth==1 and ''.join(token)=='suites':
                        ch=f.read(1)
                        while ch.isspace():ch=f.read(1)
                        assert ch==':'
                        ch=f.read(1)
                        while ch.isspace():ch=f.read(1)
                        assert ch=='{';break
                else:token.append(ch)
            elif ch=='"':string=True;token=[]
            elif ch in '{[':depth+=1
            elif ch in '}]':depth-=1
        reader=Reader(f);ordinal=0
        while True:
            c=reader.nonspace()
            if c=='}':return
            assert c=='"';name=reader.string();assert reader.nonspace()==':'
            assert reader.nonspace()=='{';suite=reader.object()
            for sub,row in pairs(suite):
                ordinal+=1;yield ordinal,name+sub,row
            del suite
            c=reader.nonspace()
            if c=='}':return
            assert c==','
