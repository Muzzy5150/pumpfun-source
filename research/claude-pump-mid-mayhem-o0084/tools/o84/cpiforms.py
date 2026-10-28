"""Helpers to build O0084 source variants around the SellV2 CPI statement (base: base-w23)."""
F = 'src/instructions/pump_interface_v2.rs'
BASE = '/Users/shawwalters/Documents/Codex/2026-10-24/claude-mayhem-work/o84/base-w23/programs/mayhem/'
SRC = open(BASE + F).read()
BUMPLINE = ' let bump=[ctx.bumps.sol_vault];let seeds:&[&[u8]]=&[b"sol-vault",&bump];\n'
_i = SRC.index(' let cpi_result:Result<()> = {let outcome=crate::pump_v2::cpi::sell_v2(')
_j = SRC.index('\n', _i)
CPILINE = SRC[_i:_j]
CALL = CPILINE[len(' let cpi_result:Result<()> = {let outcome='):CPILINE.index('; if outcome.is_ok()')]
INLINE = '&[&[b"sol-vault",&[ctx.bumps.sol_vault]]]'
CALL_INLINE = CALL.replace('&[seeds]', INLINE)
QLINE = ' cpi_result?;\n'
assert SRC.count(BUMPLINE) == 1 and SRC.count(QLINE) == 1 and CALL.count('&[seeds]') == 1
ERR = 'error!(BuyError::PumpCpiFailed)'

def reps(cpi_line, bump_line='\n', q_line=QLINE):
    r = [[F, BUMPLINE, bump_line], [F, CPILINE, cpi_line]]
    if q_line != QLINE:
        r.append([F, QLINE, q_line])
    return r
