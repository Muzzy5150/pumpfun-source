#!/usr/bin/env python3
"""Read-only artifact replay of the fixed main-Pump data-order transformation.

This is not fresh source/build admission. The admitted certificate is preserved;
its absolute paths are never edited or followed to bypass archive relocation.
"""
from pathlib import Path
from contextlib import contextmanager
import argparse, hashlib, importlib.util, inspect, json, shutil, struct, sys, tempfile, threading
sys.dont_write_bytecode = True
ORIGINAL_SHA = '7a19affaa2c6187e04a5fe0ea298cee81fa5eb8c24cfcc30d85f615e89f7b02d'
FIXED_ROLES = (
    dict(role='borsh_array_location',original=0x1bd930,owner=0x101448,bytes=1640,offset=1616,footprint=24),
    dict(role='debug_argument_table',original=0x1bd948,owner=0x10c20,bytes=88,offset=56,footprint=32),
)
TOOLS_LOCK = threading.RLock()
ARTIFACT_KEYS = {'original_elf','baseline_elf','baseline_map','final_elf','final_map','admitted_certificate'}
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

class VerificationError(ValueError):
    pass

def require(ok, message):
    if not ok: raise VerificationError(message)

def load_tools(directory, expected):
    directory=Path(directory).resolve()
    require(set(expected) and all('/' not in n and '\\' not in n for n in expected),'invalid tool names')
    for name,h in expected.items():require(sha(directory/name)==h,'tool hash mismatch: '+name)
    sys.path.insert(0,str(directory))
    spec=importlib.util.spec_from_file_location('archive_sealed_data_order',directory/'pump_data_order.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    require(module.implementation_hashes()==expected,'tool implementation closure differs')
    require(sha(inspect.getsourcefile(module.normalize))==expected['pump_compare_function_bytes.py'],'loaded normalizer differs')
    require(tuple(module.ROLES)==FIXED_ROLES and module.ORIGINAL_SHA==ORIGINAL_SHA,'fixed roles differ from sealed implementation')
    return module

@contextmanager
def tools_context(directory, expected, original_path):
    # Isolated module names/path prevent one replay from retaining a deleted
    # temporary import root or accidentally using a caller's loaded helpers.
    with TOOLS_LOCK, tempfile.TemporaryDirectory(prefix='pump-archive-tools-')as temp:
        root=Path(temp);staged=root/'scripts';staged.mkdir()
        origin=root/'evidence/original/pump/deployed.so';origin.parent.mkdir(parents=True)
        shutil.copyfile(original_path,origin)
        require(sha(origin)==ORIGINAL_SHA,'temporary original copy differs')
        for name,h in expected.items():
            source=Path(directory)/name
            require(sha(source)==h,'tool hash mismatch: '+name)
            shutil.copyfile(source,staged/name)
            require(sha(staged/name)==h,'temporary tool copy differs: '+name)
        names={Path(name).stem for name in expected if name.endswith('.py')}
        saved={name:sys.modules.get(name)for name in names}
        for name in names:sys.modules.pop(name,None)
        old_path=list(sys.path)
        try:
            yield load_tools(staged,expected)
        finally:
            sys.path[:]=old_path
            for name,value in saved.items():
                sys.modules.pop(name,None)
                if value is not None:sys.modules[name]=value


def check_bindings(paths, expected):
    require(set(paths)==ARTIFACT_KEYS and set(expected)==ARTIFACT_KEYS,'exact six artifact bindings required')
    for name,p in paths.items():
        require(set(expected[name])=={'sha256','bytes'},'invalid artifact binding: '+name)
        require(Path(p).is_file(),'missing artifact: '+name)
        require(sha(p)==expected[name]['sha256'] and Path(p).stat().st_size==expected[name]['bytes'],'artifact hash/length mismatch: '+name)
    require(expected['original_elf']['sha256']==ORIGINAL_SHA,'original main-Pump ELF differs')

def derive_roles(helper, original, image, map_path):
    rows=helper.map_rows(map_path)
    text=[r for r in rows if r['out']=='.text']
    data=[r for r in rows if r['out']=='.data.rel.ro']
    roles=[]
    def norm(elf,address,size):return helper.normalize(elf.read(address,size),address,elf.sections)[0]
    def lddw(raw):
        require(len(raw)==16 and raw[0]==0x18 and raw[8]==0,'role reference is not LDDW')
        return struct.unpack_from('<I',raw,4)[0]|struct.unpack_from('<I',raw,12)[0]<<32
    for role in FIXED_ROLES:
        wanted=norm(original,role['owner'],role['bytes'])
        matches=[r for r in text if r['size']==role['bytes'] and norm(image,r['address'],r['size'])==wanted]
        require(len(matches)==1,'original role owner absent or ambiguous: '+role['role'])
        function=matches[0]
        require(lddw(original.read(role['owner']+role['offset'],16))==role['original'],'fixed original LDDW target differs')
        target=lddw(image.read(function['address']+role['offset'],16))
        hits=[(i,r)for i,r in enumerate(data)if r['address']==target and r['size']==role['footprint']]
        require(len(hits)==1,'role target is not one complete map input: '+role['role'])
        i,r=hits[0]
        require(r['align']==8,'role input alignment differs')
        roles.append(dict(role,candidate=target,candidate_owner=function['address'],data_index=i,input_owner=helper.owner(r),input_section=r['section']))
    def location(elf,address):
        pointer,n,line,column=struct.unpack('<QQII',elf.read(address,24))
        require(elf.relocations().get(address)==8 and pointer&0xffffffff==0,'Location pointer relocation differs')
        require(n==len('src/de/mod.rs'),'Location path length differs')
        return elf.read(pointer>>32,n).decode('utf-8'),line,column
    require(location(original,FIXED_ROLES[0]['original'])==('src/de/mod.rs',637,21),'original Location fields differ')
    require(location(image,roles[0]['candidate'])==('src/de/mod.rs',637,21),'candidate Location fields differ')
    for elf,addr in [(original,FIXED_ROLES[1]['original']),(image,roles[1]['candidate'])]:
        require(elf.read(addr+8,16)==struct.pack('<QQ',8,8),'vtable scalar fields differ')
    for off,original_target,size in [(0,0xaef0,8),(24,0xa8f0,48)]:
        def method(elf,address):
            raw=struct.unpack('<Q',elf.read(address,8))[0]
            require(elf.relocations().get(address)==8 and raw&0xffffffff==0,'vtable method relocation differs')
            return raw>>32
        require(method(original,FIXED_ROLES[1]['original']+off)==original_target,'original vtable method differs')
        target=method(image,roles[1]['candidate']+off)
        require(any(r['address']==target and r['size']==size for r in text),'vtable target has no exact-size map owner')
        require(norm(original,original_target,size)==norm(image,target,size),'vtable method body differs')
    return roles

def verify_archive(*, original_elf, baseline_elf, baseline_map, final_elf, final_map,
                   admitted_certificate, bindings, bindings_sha256, tools_directory):
    """Verify explicit archived artifacts; return proof, never admit a new build.

    `bindings_sha256` is the trust anchor supplied by the checkpoint/package
    manifest, not computed from an untrusted bindings file by this function.
    """
    require(__debug__,'archive verification requires Python assertions enabled')
    require(sha(bindings)==bindings_sha256,'archive bindings digest differs')
    manifest=json.loads(Path(bindings).read_text())
    require(set(manifest)=={'schema','artifacts','tools'} and manifest['schema']==1,'unsupported archive bindings')
    paths={k:Path(v).resolve()for k,v in dict(original_elf=original_elf,baseline_elf=baseline_elf,baseline_map=baseline_map,final_elf=final_elf,final_map=final_map,admitted_certificate=admitted_certificate).items()}
    check_bindings(paths,manifest['artifacts'])
    with tools_context(tools_directory,manifest['tools'],paths['original_elf'])as helper:
        return verify_bound(helper,paths,manifest,bindings,bindings_sha256,tools_directory)

def verify_bound(helper,paths,manifest,bindings,bindings_sha256,tools_directory):
    cert=json.loads(paths['admitted_certificate'].read_text())
    require(set(cert)=={'schema','payload'} and cert['schema']==1,'unsupported admitted certificate')
    payload=cert['payload']
    require(payload['implementation']==manifest['tools'],'certificate implementation differs')
    old_base=Path(payload['baseline_build'])
    for key,suffix in [('baseline_elf','unstripped.so'),('baseline_map','link/link.map')]:
        require(payload['bindings'].get(str(old_base/suffix))==manifest['artifacts'][key]['sha256'],'archive baseline differs from admitted certificate: '+key)
    original=helper.Elf(paths['original_elf']);baseline=helper.Elf(paths['baseline_elf']);final=helper.Elf(paths['final_elf'])
    before=derive_roles(helper,original,baseline,paths['baseline_map'])
    after=derive_roles(helper,original,final,paths['final_map'])
    require(before==payload['roles'],'admitted role descriptor differs from independently observed baseline')
    require(before[0]['data_index']==before[1]['data_index']+1 and before[1]['candidate']+32==before[0]['candidate'],'baseline pair is not reversed and adjacent')
    require(after[1]['data_index']==after[0]['data_index']+1 and after[0]['candidate']+24==after[1]['candidate'],'final pair is not corrected and adjacent')
    require([(r['input_owner'],r['input_section'])for r in before]==[(r['input_owner'],r['input_section'])for r in after],'role input identity changed')
    # Explicit path adapter for the sealed full-file checker. This small object
    # is a transformation replay context, NOT a rewritten/new certificate.
    # We do not call load_certificate, derive_payload, or check_request here.
    with tempfile.TemporaryDirectory(prefix='pump-data-order-archive-')as temp:
        temp=Path(temp)
        for group in ['baseline','final']:
            (temp/group/'link').mkdir(parents=True)
            for key,name in [(group+'_elf','unstripped.so'),(group+'_map','link/link.map')]:
                destination=temp/group/name;shutil.copyfile(paths[key],destination)
                require(sha(destination)==manifest['artifacts'][key]['sha256'],'temporary artifact copy differs')
        replay_context={'payload':{'baseline_build':str(temp/'baseline'),'roles':before}}
        transform=helper.verify_transform(replay_context,temp/'final')
    check_bindings(paths,manifest['artifacts'])
    require(sha(bindings)==bindings_sha256,'archive bindings changed during verification')
    for name,h in manifest['tools'].items():require(sha(Path(tools_directory)/name)==h,'tool changed during verification: '+name)
    require(transform['baseline_sha256']==manifest['artifacts']['baseline_elf']['sha256'] and transform['candidate_sha256']==manifest['artifacts']['final_elf']['sha256'],'transformation ELF binding differs')
    return {'status':'passed','scope':__doc__,'fresh_admission':False,'certificate_paths_rewritten':False,'original_certificate_sha256':manifest['artifacts']['admitted_certificate']['sha256'],'bindings_sha256':bindings_sha256,'artifacts':{k:{'path':str(paths[k]),**v}for k,v in manifest['artifacts'].items()},'roles':{'baseline':before,'final':after},'transformation':transform,'tracked_typeid_equality_checked':False,'whole_original_elf_identity':False,'limits':['This independently replays archived artifact roles and full-file transformation; it does not re-run source/compiler/cache admission.','The unchanged admitted certificate remains provenance. New compilation must derive a fresh certificate from a fresh identity build.','Whole original allocation extents and original toolchain provenance remain unproved.']}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in sorted(ARTIFACT_KEYS):p.add_argument('--'+name.replace('_','-'),type=Path,required=True)
    p.add_argument('--bindings',type=Path,required=True);p.add_argument('--bindings-sha256',required=True)
    p.add_argument('--tools-directory',type=Path,default=Path(__file__).resolve().parent/'tools')
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();require(not a.output.exists(),'use a new report output')
    kwargs=vars(a).copy();output=kwargs.pop('output')
    report=verify_archive(**kwargs);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'output':str(output),'sha256':sha(output)}))
if __name__=='__main__':main()
