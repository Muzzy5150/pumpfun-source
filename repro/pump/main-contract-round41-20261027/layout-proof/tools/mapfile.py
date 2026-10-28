"""Parse an lld -Map file into output sections, input sections and symbols."""
import re
from pathlib import Path

LINE = re.compile(r'^\s*([0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)\s+(\d+) (.*)$')


def parse(path):
    """Return a list of input-section records for every output section.

    Each record: {'out', 'address', 'size', 'align', 'file', 'member', 'section', 'symbols'}.
    `file` is the object or archive path; `member` the archive member (or None).
    """
    records, out = [], None
    for line in Path(path).read_text().splitlines()[1:]:
        m = LINE.match(line)
        if not m:
            continue
        vma, _, size, align, rest = m.groups()
        depth = len(rest) - len(rest.lstrip(' '))
        rest = rest.strip()
        if depth == 0:
            out = rest
        elif depth == 8:
            if ':(' in rest and rest.endswith(')'):
                owner, section = rest[:-1].rsplit(':(', 1)
                member = None
                if owner.endswith(')') and '(' in owner:
                    owner, member = owner[:-1].split('(', 1)
                records.append({'out': out, 'address': int(vma, 16), 'size': int(size, 16), 'align': int(align),
                                'file': owner, 'member': member, 'section': section, 'symbols': []})
            else:
                records.append({'out': out, 'address': int(vma, 16), 'size': int(size, 16), 'align': int(align),
                                'file': None, 'member': None, 'section': rest, 'symbols': []})
        elif depth == 16 and records:
            records[-1]['symbols'].append(rest)
    return records


def owner_pattern(rec):
    """Qualified lld file pattern for an input section (object basename or archive:member)."""
    base = Path(rec['file']).name
    return base + ':' + rec['member'] if rec['member'] else base
