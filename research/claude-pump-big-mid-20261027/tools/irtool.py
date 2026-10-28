#!/usr/bin/env python3
"""IR-first experiments for pump-big-mid: reproduce one function's machine code with llc (v1.44 platform-tools,
the toolchain that compiled the module) and compare it with the original window.

  irtool.py stub <module.ll> <fn regex> <out.ll>     keep the matched definition, stub every other body
  irtool.py llc  <in.ll> <out.o>                      llc -O3 (sbf, pic, function sections, trap-unreachable)
  irtool.py cmp  <obj.o> <fn regex> <orig_start> [--dis out.txt]
                                                      positional + difflib comparison vs the original window
                                                      (all call and lddw immediates masked on both sides)
As a module: F = IRFunc(path, regex); F.blocks; F.move(); F.write(path) etc.
"""
import difflib, re, struct, subprocess, sys
from pathlib import Path

CPW = Path('/Users/shawwalters/Documents/Codex/2026-10-24/claude-pump-work')
SDK = Path.home() / '.cache/solana/v1.44/platform-tools'
LLC = SDK / 'llvm/bin/llc'
OBJDUMP = Path.home() / '.cache/solana/v1.52/platform-tools/llvm/bin/llvm-objdump'
LLC_FLAGS = ['-O3', '-mtriple=sbf', '-mcpu=generic', '-mattr=+store-imm,+jmp-ext', '-relocation-model=pic',
             '-function-sections', '-data-sections', '-trap-unreachable', '-no-trap-after-noreturn', '-filetype=obj']


def split_functions(text):
    """Yield (kind, chunk) where kind is 'define' for a function definition chunk, else 'other'."""
    out = []; pos = 0
    for m in re.finditer(r'^define [^\n]*\{\n', text, re.M):
        if m.start() < pos:
            continue
        out.append(('other', text[pos:m.start()]))
        end = text.index('\n}\n', m.end()) + 3
        out.append(('define', text[m.start():end]))
        pos = end
    out.append(('other', text[pos:]))
    return out


def stub(src, pat, dst):
    text = Path(src).read_text()
    rx = re.compile(pat)
    parts = []; kept = []
    for kind, chunk in split_functions(text):
        if kind == 'define':
            header = chunk[:chunk.index('\n') + 1]
            name = re.search(r'@("[^"]+"|[\w.$]+)\(', header).group(1)
            if rx.search(name):
                kept.append(name); parts.append(chunk)
            else:
                parts.append(header + '  unreachable\n}\n')
        else:
            parts.append(chunk)
    Path(dst).write_text(''.join(parts))
    return kept


def llc(src, obj, extra=()):
    r = subprocess.run([str(LLC), *LLC_FLAGS, *extra, str(src), '-o', str(obj)], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stderr[:4000])
    return r.stderr


def elf_sections(blob):
    shoff, = struct.unpack_from('<Q', blob, 0x28)
    shentsize, shnum, shstrndx = struct.unpack_from('<HHH', blob, 0x3a)
    hdrs = [struct.unpack_from('<IIQQQQIIQQ', blob, shoff + i * shentsize) for i in range(shnum)]
    st = hdrs[shstrndx]
    nm = lambda o: blob[st[4] + o:blob.index(b'\0', st[4] + o)].decode()
    return {nm(h[0]): blob[h[4]:h[4] + h[5]] for h in hdrs}


def obj_function(obj, pat):
    secs = elf_sections(Path(obj).read_bytes())
    ks = [k for k in secs if k.startswith('.text.') and re.search(pat, k)]
    assert len(ks) == 1, ks
    return ks[0], secs[ks[0]]


def masked(raw):
    out = []; i = 0
    while i < len(raw):
        op = raw[i]
        if op == 0x18:
            out.append(raw[i:i + 4] + b'\0' * 12); i += 16
        elif op == 0x85 and (raw[i + 1] >> 4) == 1:
            out.append(raw[i:i + 4] + b'\0' * 4); i += 8
        elif op == 0x85:  # unresolved external calls in an object (imm -1 + relocation); syscalls are hashes when linked
            out.append(raw[i:i + 4] + b'\0' * 4); i += 8
        else:
            out.append(raw[i:i + 8]); i += 8
    return out


def orig_raw(start):
    sys.path.insert(0, str(CPW / 'harness'))
    from score import original_windows
    w = next(x for x in original_windows() if x['start'] == start)
    return w['raw']


def compare(code, start, label=''):
    o = masked(orig_raw(start)); c = masked(code)
    pos = sum(1 for a, b in zip(o, c) if a != b) + abs(len(o) - len(c))
    sm = difflib.SequenceMatcher(None, o, c, autojunk=False)
    seq = sum(max(i2 - i1, j2 - j1) for t, i1, i2, j1, j2 in sm.get_opcodes() if t != 'equal')
    print(f'{label}: {len(code)} B (orig {sum(len(x) for x in o)} B)  positional-diff={pos}  seq-diff={seq}  ratio={sm.ratio():.4f}')
    return pos, seq


def dis(obj, section, path):
    t = subprocess.check_output([str(OBJDUMP), '-d', '--no-show-raw-insn', f'--section={section}', str(obj)], text=True)
    Path(path).write_text(t)


class IRFunc:
    """Block-level view of one function in a module (for IR edit experiments)."""
    def __init__(self, path, pat):
        s = Path(path).read_text()
        m = re.search(r'^define [^\n]*' + pat + r'[^\n]*\{\n', s, re.M)
        st = m.start(); en = s.index('\n}\n', m.end()) + 3
        self.pre, self.post = s[:st], s[en:]
        lines = s[st:en].split('\n')
        self.header = lines[0]
        self.blocks = []
        cur = ['%entry', []]; self.blocks.append(cur)
        for l in lines[1:]:
            if l in ('}', ''):
                continue
            m2 = re.match(r'^("[^"]+"|[\w.$-]+):', l)
            if m2:
                cur = [m2.group(1), [l]]; self.blocks.append(cur)
            else:
                cur[1].append(l)
        if not self.blocks[0][1]:
            self.blocks.pop(0)

    def names(self):
        return [b[0] for b in self.blocks]

    def idx(self, name):
        r = [i for i, b in enumerate(self.blocks) if b[0] == name]
        assert len(r) == 1, (name, r)
        return r[0]

    def move(self, name, after=None, before=None):
        b = self.blocks.pop(self.idx(name))
        if after is not None:
            self.blocks.insert(self.idx(after) + 1, b)
        else:
            self.blocks.insert(self.idx(before), b)

    def text(self):
        t = self.header + '\n' + '\n'.join('\n'.join(b[1]) for b in self.blocks) + '\n}\n'
        # numbered values must appear in order; name them so blocks can be reordered
        return re.sub(r'%(\d+)\b', lambda m: '%v' + m.group(1), t)

    def write(self, path):
        Path(path).write_text(self.pre + self.text() + self.post)


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'stub':
        print('kept:', stub(sys.argv[2], sys.argv[3], sys.argv[4]))
    elif cmd == 'llc':
        llc(sys.argv[2], sys.argv[3])
    elif cmd == 'cmp':
        sec, code = obj_function(sys.argv[2], sys.argv[3])
        compare(code, int(sys.argv[4], 0), sec[:80])
        if '--dis' in sys.argv:
            dis(sys.argv[2], sec, sys.argv[sys.argv.index('--dis') + 1])
