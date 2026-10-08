"""Read only the 38 explicit native candidates; never traverse private state."""
from pathlib import Path
import datetime
import hashlib
import json

base = Path(__file__).parent / 'seal-22dade'
manifest = base / 'SAFE_CANDIDATES.json'
outer = base / 'READBACK.json'
sha = lambda data: hashlib.sha256(data).hexdigest()
assert sha(manifest.read_bytes()) == '4456e4fab0ba7766964daa64cb70123e49779d4a23116792e6b2468dc22e7dfc'
assert sha(outer.read_bytes()) == 'cdc3573672865b0a1eab7866a642775447d9ee6201e91dfe5784912551fb2b33'
entries = json.loads(manifest.read_text())['files']
assert len(entries) == 38
read = []
for entry in entries:
    relative = Path(entry['candidate_path'])
    assert not relative.is_absolute() and '..' not in relative.parts
    path = base / 'publication-candidates' / relative
    raw = Path(entry['raw_path'])
    data = path.read_bytes()
    assert entry['transformation'] == 'none' and data == raw.read_bytes()
    assert len(data) == entry['bytes'] and sha(data) == entry['sha256']
    read.append({'path': str(relative), 'bytes': len(data), 'sha256': sha(data)})
out = Path(__file__).parent / 'ROOT_NATIVE_READBACK.json'
assert not out.exists()
out.write_text(json.dumps({'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'source': '22dade7996f13634202250ef5e1c05dc976214a5', 'candidate_count': len(read),
    'all_explicit_raw_and_candidate_bytes_sha_exact': True, 'files': read,
    'root_images_viewed': ['run-02/durable-original-ack-independent-current-1440.png',
                           'run-02/new-actor-original-command-isolated-390.png'],
    'image_scope': 'Visible safe control state/history at selected scroll positions only; not whole-page proof',
    'first_dynamic_raw': 'LOST_NOT_RECONSTRUCTED', 'run01_admitted': 'SECOND_ACCIDENTAL_EXECUTION',
    'run02': 'BOUNDED_NATIVE_PASS', 'full_native': 'RUNNING_SEPARATE_PACKET',
    'whole_M6_3': 'NOT_ACCEPTED', 'actual_external_model_calls_by_this_readback': 0}, indent=2) + '\n')
print(json.dumps({'readback_sha256': sha(out.read_bytes()), 'candidate_count': len(read)}))
