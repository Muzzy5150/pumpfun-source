"""Describe an already-built transaction; never construct, sign, or submit one."""
from pathlib import Path
import base64,hashlib,json
from solders.transaction import VersionedTransaction
R=Path(__file__).resolve().parents[4]
def receipt_fields(tx,main_program):
    raw=bytes(tx)
    parsed=VersionedTransaction.from_bytes(raw)
    verified=parsed.verify_with_results()
    required=parsed.message.header.num_required_signatures
    idl=json.loads((R/'evidence/upstream/pump.json').read_text())
    assert idl['address']==str(main_program)
    names={bytes(x['discriminator']).hex():x['name']for x in idl['instructions']}
    instructions=[]
    for index,ix in enumerate(parsed.message.instructions):
        if ix.program_id_index>=len(parsed.message.account_keys):
            continue
        if str(parsed.message.account_keys[ix.program_id_index])!=str(main_program):
            continue
        data=bytes(ix.data)
        instructions.append({'index':index,'program':str(main_program),
            'discriminator_hex':data[:8].hex(),'name':names.get(data[:8].hex()),
            'data_hex':data.hex(),'account_indices':list(ix.accounts)})
    return {'transaction_base64':base64.b64encode(raw).decode(),
        'transaction_sha256':hashlib.sha256(raw).hexdigest(),
        'signature_verification':{'required':required,'provided':len(parsed.signatures),
            'results':verified,'all_verified':len(parsed.signatures)==required and required>0 and all(verified)},
        'instruction_attribution':{'main_program':str(main_program),'scope':'top_level',
            'main_instructions':instructions}}
