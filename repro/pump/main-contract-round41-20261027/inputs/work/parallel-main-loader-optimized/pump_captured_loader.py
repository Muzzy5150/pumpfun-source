"""Load main Pump with its captured upgradeable account layout in local LiteSVM.

Other programs retain each fixture's existing loader setup. ProgramData headers
are preserved, candidate ELF bytes are unchanged, and only unused allocation
is zero-filled. This is local fixture fidelity, not live-chain acceptance.
"""
from pathlib import Path
import hashlib,json,struct
from solders.litesvm import LiteSVM as BaseVM
from solders.account import Account
from solders.pubkey import Pubkey
from solders.rent import Rent
from solders.clock import Clock
ROOT=Path(__file__).resolve().parents[2]
CAPTURE=json.loads((ROOT/'evidence/original/pump/capture.json').read_text())
PROGRAM=Pubkey.from_string(CAPTURE['program']);PROGRAMDATA=Pubkey.from_string(CAPTURE['programdata']);OWNER=Pubkey.from_string(CAPTURE['owner'])
PROGRAM_BYTES=(ROOT/'evidence/original/pump/program-account.bin').read_bytes();PD_CAPTURE=(ROOT/'evidence/original/pump/programdata-account.bin').read_bytes();HEADER=PD_CAPTURE[:45];SLOT=struct.unpack_from('<Q',HEADER,4)[0]
assert len(PROGRAM_BYTES)==36 and PROGRAM_BYTES[4:]==bytes(PROGRAMDATA)
assert hashlib.sha256(PD_CAPTURE).hexdigest()==CAPTURE['programdata_sha256']
assert hashlib.sha256(PD_CAPTURE[45:]).hexdigest()==CAPTURE['payload_sha256']
LOADS=[]
_PREPARED={}
PROGRAM_SHA=hashlib.sha256(PROGRAM_BYTES).hexdigest()
HEADER_SHA=hashlib.sha256(HEADER).hexdigest()
def prepared(raw):
    digest=sha(raw)
    prior=_PREPARED.get(digest)
    if prior is not None:
        assert prior[0]==raw, "Distinct bytes under the same hash"
        return prior
    assert len(raw)<=CAPTURE['payload_bytes']
    image=HEADER+raw+bytes(CAPTURE['payload_bytes']-len(raw))
    value=(raw,image,digest,sha(image))
    _PREPARED[digest]=value
    return value

def sha(b):return hashlib.sha256(b).hexdigest()
class CapturedLiteSVM(BaseVM):
    def set_account(self,address,account):
        # Some fixtures snapshot transaction message accounts, which include
        # the executable program but omit its ProgramData dependency. Restore
        # that exact captured dependency only for the known unmodified header.
        if address==PROGRAM and account.executable and account.owner==OWNER and account.data==PROGRAM_BYTES and self.get_account(PROGRAMDATA) is None:
            super().set_account(PROGRAMDATA,Account(CAPTURE['lamports'],PD_CAPTURE,OWNER,False))
        return super().set_account(address,account)
    def set_clock(self,clock):
        # Fixture epoch/timestamps remain supplied by the fixture. The runtime
        # slot must admit the captured deployment.
        if clock.slot<=SLOT:
            clock=Clock(SLOT+1,clock.epoch_start_timestamp,clock.epoch,clock.leader_schedule_epoch,clock.unix_timestamp)
        return super().set_clock(clock)
    def _add_captured_pump(self,raw,path=None):
        raw,image,raw_sha,image_sha=prepared(raw)
        before=self.get_clock();self.warp_to_slot(SLOT+1);self.set_clock(before)
        self.set_account(PROGRAMDATA,Account(CAPTURE['lamports'],image,OWNER,False))
        self.set_account(PROGRAM,Account(Rent.default().minimum_balance(36),PROGRAM_BYTES,OWNER,True))
        program=self.get_account(PROGRAM);data=self.get_account(PROGRAMDATA)
        program_data=program.data
        actual_data=data.data
        assert program_data==PROGRAM_BYTES and program.owner==OWNER and program.executable
        # Full equality against the constructed image proves prefix, retained
        # header and zero tail for every load. Cache only immutable expectations.
        assert actual_data==image and data.owner==OWNER
        LOADS.append({'input_path':path,'elf_sha256':raw_sha,'elf_bytes':len(raw),'program_owner':str(program.owner),'program_bytes':len(program_data),'program_sha256':PROGRAM_SHA,'programdata_bytes':len(actual_data),'programdata_sha256':image_sha,'header_sha256':HEADER_SHA,'elf_prefix_unchanged':True,'zero_allocation_tail':True,'slot':self.get_clock().slot})
    def add_program_from_file(self,program_id,path):
        if program_id==PROGRAM:return self._add_captured_pump(Path(path).read_bytes(),str(Path(path).resolve()))
        return super().add_program_from_file(program_id,path)
    def add_program(self,program_id,program_bytes):
        if program_id==PROGRAM:return self._add_captured_pump(bytes(program_bytes))
        return super().add_program(program_id,program_bytes)
def install():
    import solders.litesvm
    solders.litesvm.LiteSVM=CapturedLiteSVM
