"""pump-mid analysis helpers: ELF sections, candidate symbols, normalized slots, call graphs.

Analysis only. Never writes or patches executables.
"""
import gzip, hashlib, json, re, struct, subprocess
from pathlib import Path

OBJDUMP = str(Path.home() / '.cache/solana/v1.52/platform-tools/llvm/bin/llvm-objdump')
WT = next(p for p in Path(__file__).resolve().parents if (p / 'evidence/original/pump/deployed.so').is_file())
ORIG = WT / 'evidence/original/pump/deployed.so'


def sections(blob):
    shoff, = struct.unpack_from('<Q', blob, 0x28)
    shentsize, shnum, shstrndx = struct.unpack_from('<HHH', blob, 0x3a)
    hdrs = [struct.unpack_from('<IIQQQQIIQQ', blob, shoff + i * shentsize) for i in range(shnum)]
    strtab = hdrs[shstrndx]
    name = lambda off: blob[strtab[4] + off:blob.index(b'\0', strtab[4] + off)].decode()
    return {name(h[0]): {'addr': h[3], 'offset': h[4], 'size': h[5]} for h in hdrs}


def body(image, secs, address, size):
    text = secs['.text']; off = address - text['addr'] + text['offset']
    return image[off:off + size]


def normalize(raw, address, secs):
    masked = bytearray(raw); ops = []; i = 0
    while i < len(raw):
        op, regs, offset, imm = struct.unpack_from('<BBhi', raw, i)
        if op == 0x18:
            value = struct.unpack_from('<I', raw, i + 4)[0] | struct.unpack_from('<I', raw, i + 12)[0] << 32
            t = [n for n, s in secs.items() if s['addr'] > 0 and s['addr'] <= value < s['addr'] + s['size']]
            if t:
                masked[i + 4:i + 8] = bytes(4); masked[i + 12:i + 16] = bytes(4)
                ops.append({'offset': i, 'kind': 'elf-pointer', 'value': value, 'sections': t})
            i += 16
        else:
            if op == 0x85 and regs >> 4 == 1 and imm != -1:
                masked[i + 4:i + 8] = bytes(4)
                ops.append({'offset': i, 'kind': 'direct-call', 'target': address + i + 8 + imm * 8})
            i += 8
    return bytes(masked), ops


def candidate_functions(path):
    text = subprocess.check_output([OBJDUMP, '-t', str(path)], text=True)
    funcs = []
    for line in text.splitlines():
        m = re.match(r'^([0-9a-f]+) .* F \.text\s+([0-9a-f]+)\s+(?:\.hidden\s+)?(\S+)$', line)
        if m:
            a, n, name = int(m.group(1), 16), int(m.group(2), 16), m.group(3)
            if n:
                funcs.append((a, n, name))
    return sorted(funcs)


def demangle(names):
    p = subprocess.run(['c++filt'], input='\n'.join(names), capture_output=True, text=True)
    return p.stdout.splitlines()


def read_json(p):
    b = Path(p).read_bytes()
    return json.loads(gzip.decompress(b) if b[:2] == b'\x1f\x8b' else b)


def calls(raw, address):
    out = []
    for i in range(0, len(raw), 8):
        op, regs, off, imm = struct.unpack_from('<BBhi', raw, i)
        if op == 0x85 and regs >> 4 == 1 and imm != -1:
            out.append(address + i + 8 + imm * 8)
        elif op == 0x85 and imm != -1 and regs >> 4 == 0:
            out.append(('syscall', imm & 0xffffffff))
    return out


def slots(norm):
    return [norm[i:i + 8] for i in range(0, len(norm), 8)]


def disasm(path, start, size):
    out = subprocess.check_output([OBJDUMP, '-d', '--no-show-raw-insn', f'--start-address={start}', f'--stop-address={start+size}', str(path)], text=True)
    lines = []
    for line in out.splitlines():
        m = re.match(r'^\s*([0-9a-f]+):\s+(.*)$', line)
        if m:
            lines.append((int(m.group(1), 16), m.group(2).strip()))
    return lines


def vread(blob, secs, vaddr, n):
    for name, s in secs.items():
        if s['addr'] and s['addr'] <= vaddr < s['addr'] + s['size']:
            off = vaddr - s['addr'] + s['offset']
            return blob[off:off + n]
    return None
