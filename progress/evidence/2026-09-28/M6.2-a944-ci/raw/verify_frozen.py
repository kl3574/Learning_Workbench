"""Read-only replay of this completed private CI evidence package; never contacts GitHub."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import zipfile

BASE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


manifest = json.loads((BASE / 'MANIFEST.json').read_bytes())
expected = {'MANIFEST.json'}
for entry in manifest['files']:
    rel = PurePosixPath(entry['path'])
    assert not rel.is_absolute() and '..' not in rel.parts
    data = (BASE / rel).read_bytes()
    assert len(data) == entry['bytes'] and sha(data) == entry['sha256'], str(rel)
    expected.add(str(rel))
actual = {p.relative_to(BASE).as_posix() for p in BASE.rglob('*')
          if p.is_file() and '__pycache__' not in p.relative_to(BASE).parts}
assert actual == expected, (sorted(actual - expected), sorted(expected - actual))
receipt = json.loads((BASE / 'TASK_RECEIPT.json').read_bytes())
assert receipt['status'] == 'complete'
assert receipt['actual_job_logs_verified'] == 12 and receipt['apt_exact_installations'] == 6
assert receipt['run_attempts'] == 1 and not receipt['rerun_or_dispatch']
evidence = json.loads((BASE / 'FINAL_JOB_EVIDENCE.json').read_bytes())
assert len(evidence['jobs']) == 12
for job in evidence['jobs']:
    assert sha((BASE / job['log_path']).read_bytes()) == job['log_sha256']
    assert job['checkout']['sha'] == {
        'push': evidence['head'], 'pull_request': evidence['pr_actual_checkout'],
    }[job['event']]
members = 0
for artifact in evidence['artifacts']:
    archive = BASE / 'artifacts' / f"{artifact['event']}-{artifact['id']}.zip"
    assert sha(archive.read_bytes()) == artifact['sha256']
    if artifact['server_digest']:
        assert artifact['server_digest'] == 'sha256:' + artifact['sha256']
    by_name = {x['path']: x for x in artifact['members']}
    with zipfile.ZipFile(archive) as stream:
        assert {x.filename for x in stream.infolist() if not x.is_dir()} == set(by_name)
        for name, entry in by_name.items():
            raw = stream.read(name)
            assert len(raw) == entry['bytes'] and sha(raw) == entry['sha256']
            assert (BASE / 'extracted' / archive.stem / name).read_bytes() == raw
            members += 1
print(json.dumps({'status': 'PASS', 'manifest_members': len(manifest['files']),
                  'job_logs': 12, 'apt_exact_installations': 6,
                  'archives': len(evidence['artifacts']), 'archive_members': members,
                  'network_requests': 0, 'product_tests': 0}))
