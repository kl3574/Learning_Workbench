"""Seal only the exact finite reviewer payload; no product commands."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
def sha(raw):
    return hashlib.sha256(raw).hexdigest()
def put_json(name, value):
    with (HERE / name).open('xb') as stream:
        stream.write((json.dumps(value, indent=2, sort_keys=True) + '\n').encode())

put_json('09-PACKAGE-ACTUAL-TOOL-RECEIPT.json', {
    'tool': 'exec_command', 'actual_chunk_id': 'f6ae39', 'actual_exit_code': 0,
    'shell_command': 'python3 prepare_finite_packet.py > 08-PACKAGE.stdout 2> 08-PACKAGE.stderr',
    'cwd': str(HERE), 'purpose': 'finite metadata packaging only',
    'script_sha256': sha((HERE / 'prepare_finite_packet.py').read_bytes()),
    'stdout_bytes': len((HERE / '08-PACKAGE.stdout').read_bytes()),
    'stdout_sha256': sha((HERE / '08-PACKAGE.stdout').read_bytes()),
    'stderr_bytes': len((HERE / '08-PACKAGE.stderr').read_bytes()),
    'stderr_sha256': sha((HERE / '08-PACKAGE.stderr').read_bytes()),
    'HOME_CODEX_HOME_override': False, 'product_execution': False
})

payload = [
    '01-ALL-56-ORIGINAL-BINDINGS.json',
    '02-ALL-13-FULL-1564-SOURCE-MAP-CHECKS.json',
    '03-FIVE-ORIGINAL-COMMAND-STREAM-RECEIPT-BINDINGS.json',
    '04-FINAL-AND-ORIGINAL-RESULT-CROSSCHECK.json',
    '05-AUDIT.stderr', '05-AUDIT.stdout',
    '06-AUDIT-ACTUAL-TOOL-RECEIPT.json',
    '07-SAFE-ORIGINAL-COPY-BINDINGS.json',
    '08-PACKAGE.stderr', '08-PACKAGE.stdout',
    '09-PACKAGE-ACTUAL-TOOL-RECEIPT.json',
    'REPORT.md', 'REVIEW.json', 'SAFE-ORIGINAL-LINES.json',
    'audit_complete_python.py', 'prepare_finite_packet.py', 'seal_packet.py',
    'safe-originals/fixed-inputs.json',
    'safe-originals/complete-python/before.json',
    'safe-originals/complete-python/after.json',
    'safe-originals/final-new-worktree-inputs.json',
    'safe-originals/final-canonical-inputs.json',
    'safe-originals/worktree-create/receipt.json',
    'safe-originals/node-archive-reuse/receipt.json',
    'safe-originals/locked-setup/receipt.json',
    'safe-originals/node-version/receipt.json',
    'safe-originals/complete-python/receipt.json'
]
assert len(payload) == len(set(payload)) == 27
actual = sorted(str(path.relative_to(HERE)) for path in HERE.rglob('*') if path.is_file())
assert actual == sorted(payload), (actual, sorted(payload))
assert not any(path.is_symlink() for path in HERE.rglob('*'))
copy_records = json.loads((HERE / '07-SAFE-ORIGINAL-COPY-BINDINGS.json').read_bytes())['entries']
copy_by_path = {entry['path']: entry for entry in copy_records}
entries = []
for name in sorted(payload):
    raw = (HERE / name).read_bytes()
    entry = {'path': name, 'bytes': len(raw), 'sha256': sha(raw),
             'category': 'reviewer finite audit metadata', 'transformation': 'none'}
    if name in copy_by_path:
        entry.update(copy_by_path[name])
    entries.append(entry)
put_json('ALLOWLIST.json', {
    'scope': 'Independent fixed101 original complete-Python evidence provenance only',
    'payload_count': len(entries), 'entries': entries,
    'full_raw_stdout_included': False,
    'private_artifact_bodies_included': False,
    'numeric_skips_not_PASS': True,
    'Standards_new_blocking': 0, 'Spec_new_blocking': 0,
    'M6_3': 'NOT_ACCEPTED', 'M7': 'NOT_UNLOCKED'
})
with (HERE / 'SHA256SUMS').open('xb') as stream:
    stream.write(''.join(entry['sha256'] + '  ' + entry['path'] + '\n' for entry in entries).encode())
put_json('SEAL.json', {
    'payload_count': len(entries), 'sidecar_count': 3,
    'ALLOWLIST_sha256': sha((HERE / 'ALLOWLIST.json').read_bytes()),
    'SHA256SUMS_sha256': sha((HERE / 'SHA256SUMS').read_bytes()),
    'source_head': '101cee47d8e746dddac81fb6e8829069fcabff09',
    'original_manifest_sha256': 'dfae73881cddf96d636f36458f0c6971e76b2089f9ce6b5df33f81c9a8cb4ba2',
    'original_FINAL_sha256': '363a05abc90fbe512d7f5905d12dea29d5081dbf796e39b304604ed9c5e14b17',
    'reviewer_product_tests_rerun': False
})
for entry in entries:
    data = (HERE / entry['path']).read_bytes()
    assert len(data) == entry['bytes'] and sha(data) == entry['sha256']
actual = sorted(str(path.relative_to(HERE)) for path in HERE.rglob('*') if path.is_file())
assert actual == sorted(payload + ['ALLOWLIST.json', 'SHA256SUMS', 'SEAL.json'])
print(json.dumps({'payload_count': len(entries), 'sidecar_count': 3,
                  'files': {name: {'bytes': len((HERE / name).read_bytes()),
                                   'sha256': sha((HERE / name).read_bytes())}
                            for name in ['REPORT.md', 'REVIEW.json', 'ALLOWLIST.json', 'SEAL.json']},
                  'pathset_exact': True, 'all_payloads_self_readback_exact': True}, sort_keys=True))
