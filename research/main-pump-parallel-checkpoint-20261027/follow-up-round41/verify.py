"""Verify the follow-up archive and its exact captured file inventory without execution."""
from pathlib import Path, PurePosixPath
import hashlib, io, json, tarfile
P = Path(__file__).resolve().parent
manifest = json.loads((P/'MANIFEST.json').read_text())
archive = bytearray()
for row in manifest['parts']:
    data = (P/row['file']).read_bytes()
    assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256']
    archive.extend(data)
assert len(archive) == manifest['archive_bytes']
assert hashlib.sha256(archive).hexdigest() == manifest['archive_sha256']
seen = set()
with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as tar:
    for member in tar:
        path = PurePosixPath(member.name)
        assert member.isfile() and not path.is_absolute() and '..' not in path.parts
        assert member.name not in seen
        seen.add(member.name)
        data = tar.extractfile(member).read()
        expected = manifest['files'][member.name]
        assert len(data) == expected['bytes'] and hashlib.sha256(data).hexdigest() == expected['sha256']
assert seen == set(manifest['files'])
print(json.dumps({'verified': True, 'files':len(seen), 'parts':len(manifest['parts']), 'goal_complete':False}))
